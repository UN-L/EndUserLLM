
import base64
import os
import re
import subprocess
from time import sleep

from openai import OpenAI

from difflib import SequenceMatcher
from PIL import Image
from datetime import datetime
import logging
from statistics import mean, stdev
from threading import Thread

from tabulate import tabulate #For the table at the end
from colorama import Fore, Back, Style

###INITIALIZATIONS###

api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(
  api_key=api_key
)

#Setting up the logger
if(not os.path.exists('logs')):
  os.mkdir('logs')

dirlogs = "logs/agent_logs_" + datetime.today().strftime("%d-%m-%Y:%H:%M:%S")
logfile = dirlogs+'/outputs.log'
os.mkdir(dirlogs)
logger = logging.getLogger("agent")
logger.addHandler(logging.FileHandler(logfile))
logger.addHandler(logging.StreamHandler())
logging.root.setLevel(logging.NOTSET)

##LaTeX management
def compile(file): #Run the latex command to compile in pdf
  command = 'pdflatex -shell-escape -interaction=nonstopmode -file-line-error '+file+' | grep ".*:[0-9]*:.*"'
  return subprocess.run(command, shell=True, stdout=subprocess.PIPE, text=True)

def convertToImg(pdf): #Run the convert command to convert the pdf into jpg
  command_convert = 'convert -density 300 -trim ' + pdf + ' -quality 100 ' + pdf.replace(".pdf", ".jpg")
  subprocess.run(command_convert, shell=True, text=True)


##Scoring
  
#Count the number of keywords in a description and return this number
def compute_description_score(des, keys):
  score=0
  for x in keys:
    if x in des: 
      score+=1
  return score

#compare the commented code with the reference code (target) and return the percentage of common code
def compute_comment_score(com):
  with open("target.tex", "r") as f:
    f2 = f.read()

  return SequenceMatcher(None, com, f2).ratio()*100

#Calculates the percentage difference between 2 pixels
def percentPix(pix1, pix2):
  return (abs(pix1-pix2)*100)/255

#Compares each pixel between the original image and the modified image in a defined area. Returns False if the modifications are incorrect, else True.
#img1: original image
#img2: modify image
#ref_image: reference mask to compare results
#start: area start coordinates
#end: area end coordinates
#   start-------+
#    |          |
#    +---------end
#limit: pixel difference threshold (in %)
def compute_modification_score(img1, img2, ref_image, start, end, limit):
  res = Image.new('RGB', img1.size)
  pixels = res.load()
  for i in range(start[0], end[0]):
      for j in range(start[1], end[1]):
          if img1.getpixel([i, j]) != img2.getpixel([i, j]):
              if (percentPix(img2.getpixel([i, j])[0], img1.getpixel([i, j])[0])>limit 
                  or percentPix(img2.getpixel([i, j])[1], img1.getpixel([i, j])[1])>limit 
                  or percentPix(img2.getpixel([i, j])[2], img1.getpixel([i, j])[2])>limit):
                  pixels[i, j]=(255, 255, 255) #Colors the current pixel if the same two pixels in the images are different
          if (res.getpixel([i, j]) != ref_image.getpixel([i, j])):
            return False
  return True

##Setting up GPT
def callGPT(messages, model, temp, top_p, n):
  return client.chat.completions.create(
    model=model,
    messages=messages,
    temperature=temp,
    top_p=top_p,
    n=n
  )

#Setting up GPT vision
def encode_image(image_path): #Function to encode the image
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
    
def callGPTvision(messages, temp, top_p, n):
  return client.chat.completions.create(
      model= "gpt-4-vision-preview",
      messages= messages,
      max_tokens= 2048,
      temperature=temp,
      top_p=top_p,
      n=n
  )

###PARAMETERS###

keywords=["dog", "face", "brown", "white", "head", "ears", "eyes", "nose", "tongue", "background", "muzzle"]
nb_keys=len(keywords)
prompt_goal="Change the color of the dog's eyes to red"
tikz_img_path = "onlydog.jpg"
tikz_img = Image.open(tikz_img_path)
tikz_file = "onlydog.tex"
ref_img_path= "ref.png"
ref_img= Image.open(ref_img_path)
tmp_file = "tmp.tex"
comments_model = "gpt-4-1106-preview"
modifications_model = "gpt-3.5-turbo"
#modifications_model = "gpt-4-1106-preview"
temp = 1
top_p = 0.8
area_start=[180,222]
area_end=[294,376]
nb_answer=10

prompts=[
   "Describes the image.",
   "Describes the image as accurately and as fully as possible.",
   "Explore the elements in the image, paying attention to any distinctive shapes or features.",
   "Describe the details present in the central area of the illustration, emphasizing any notable patterns or textures.",
   "Examine the visual, focusing on elements that contribute to the overall balance and symmetry.",
   "Identify and elaborate on the characteristics found in the image, highlighting any variations in color and form."
]

def benchmark(prompt):

  ###PROCESSING###
  with open(tikz_file, "r") as f:
    tikz_file_content = f.read()

  base64_image = encode_image("onlydog.jpg")

  # message=[ #Test creating comments directly with GPT-Vision
  #         {
  #         "role": "user",
  #         "content": [
  #           {
  #             "type": "text",
  #             "text": 
  #             """You are a helpful assistant for commenting code. All you have to do is answer the question by commenting the code block provided.\n
  #             """+tikz_file_content+"""\n
  #             Comments the code blocks in relation the image and what this represents in the context of the image. You will be very precise! And you must give the entire code with comments inside.\n
  #             """ + prompt
  #           },
  #           {
  #             "type": "image_url",
  #             "image_url": {
  #               "url": f"data:image/jpeg;base64,{base64_image}"
  #             }
  #           }
  #         ]
  #       }
  #     ]
  # comments = callGPTvision(message, temp, top_p, nb_answer)
  # comments_scores=[]
  # best_comments_scores=0
  # best_comments=""
  # for com in comments.choices:
  #   comment = re.split(r'\`\`\`.*', com.message.content)[1] #extract code

  #   score= compute_comment_score(comment)
  #   #score = compute_description_score(comment, keywords)
  #   comments_scores.append(score)
  #   if (score > best_comments_scores): 
  #     best_comments_scores = score
  #     best_comments = comment
      
  ##Generating descriptions
  messages=[
        {
          "role": "user",
          "content": [
            {
              "type": "text",
              "text": prompt
            },
            {
              "type": "image_url",
              "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
              }
            }
          ]
        }
      ]
  descriptions = callGPTvision(messages, temp, top_p, nb_answer)
  descriptions_scores=[]
  best_descriptions_scores=0
  best_description=""

  for des in descriptions.choices:
    description = des.message.content

    score = compute_description_score(description, keywords)
    if (score > best_descriptions_scores): #Select the best description
      best_descriptions_scores=score
      best_description = description
    descriptions_scores.append(score)

  ##Generating comments for the TikZ code
  messages=[
    {"role": "system", "content": "You are a helpful assistant for commenting code. All you have to do is answer the question by commenting the code block provided"},
    {"role": "user", "content": tikz_file_content},
    {"role": "user", "content": "Here is the description of the code result: "+ best_description},
    {"role": "user", "content": "Comments the code blocks in relation the description and what this represents in the context of the description. You will be very precise! And you must give the entire code with comments inside"},
  ]
  comments = callGPT(messages, comments_model, temp, top_p, nb_answer)
  comments_scores=[]
  best_comments_scores=0
  best_comments=""
  for com in comments.choices:
    comment = re.split(r'\`\`\`.*', com.message.content)[1] #extract code

    score= compute_comment_score(comment) #Score with ratio
    #score = compute_description_score(comment, keywords) #Score with keywords
    comments_scores.append(score)
    if (score > best_comments_scores): #Select the best comments
      best_comments_scores = score
      best_comments = comment

  ##Generating modifications
  messages=[
    {"role": "system", "content": "You are a helpful assistant for programming and customizing code. All you have to do is answer the question by writing the entire code with the modifications. To modify the code, use the comments. DO NOT answer anything other than the entire code. If you make mistakes, don't apologize, just send the entire code with the modifications"},
    {"role": "user", "content": best_comments},
    {"role": "user", "content": prompt_goal},
  ]
  codes_high = callGPT(messages, modifications_model, 1, 0.8, nb_answer) #Test with high "creativity"
  modification_score_high=0
  codes_low = callGPT(messages, modifications_model, 0.2, 0.1, nb_answer) #Test with low "creativity"
  modification_score_low=0

  for raw_high, raw_low in zip(codes_high.choices, codes_low.choices): #For each answer, detect if the image corresponds to the goal (if the dog has red eyes)
    try:
      code_high = re.split(r'\`\`\`.*', raw_high.message.content)[1] #extract code
      code_low = re.split(r'\`\`\`.*', raw_low.message.content)[1] #extract code
    except:
      code_high = raw_high.message.content
      code_low = raw_low.message.content

    f = open(tmp_file, "w") #High "creativity"
    f.write(code_high)
    f.close()
    compile(tmp_file)
    convertToImg(tmp_file.replace('.tex', '.pdf'))
    tmp_img = Image.open(tmp_file.replace('.tex', '.jpg'))

    if (compute_modification_score(tmp_img, tikz_img, ref_img, area_start, area_end, 2)):
       modification_score_high += 1

    f = open(tmp_file, "w") #Low "creativity"
    f.write(code_low)
    f.close()
    compile(tmp_file)
    convertToImg(tmp_file.replace('.tex', '.pdf'))
    tmp_img = Image.open(tmp_file.replace('.tex', '.jpg'))

    if (compute_modification_score(tmp_img, tikz_img, ref_img, area_start, area_end, 2)):
       modification_score_low += 1
    
  logger.info("=================================================================================") #Write benchmark results
  logger.info("Prompt: " + prompt)
  logger.info("")
  logger.info("Best description: " + best_description)
  logger.info("Best comments:\n" + best_comments)
  logger.info("Average description score: " + str(mean(descriptions_scores))+"/"+str(nb_keys))
  logger.info("Average comments score: " + str(mean(comments_scores))+"%")
  #logger.info("Average comments score: " + str(mean(comments_scores))+"/"+str(nb_keys))
  logger.info("Comments standard deviation : " + str(stdev(comments_scores)))
  logger.info("Modification score (high creativity): " + str(modification_score_high)+"/"+str(nb_answer))
  logger.info("Modification score (low creativity): " + str(modification_score_low)+"/"+str(nb_answer))
  logger.info("")
  return [mean(descriptions_scores), mean(comments_scores), stdev(comments_scores), modification_score_high, modification_score_low]

#for prompt in prompts:
#  thread = Thread(target = benchmark, args = (prompt, ))
#  thread.start()
#  sleep(10)


##Create a benchmark summary table in the terminal
categories = ['scores']

AVG_des=[]
AVG_com=[]
com_std=[]
mod_high=[]
mod_low=[]
for i, prompt in enumerate(prompts):
  categories.append('prompt'+str(i))
  res=benchmark(prompt)
  AVG_des.append(res[0])
  AVG_com.append(round(res[1], 1))
  com_std.append(round(res[2], 2))
  mod_high.append(res[3])
  mod_low.append(res[4])


# For color cells
def colorize_cell(value, max, mark=""):
    pourcentage=(value/max)*100
    if pourcentage >= 90:
        return Back.GREEN + Fore.BLACK + str(value) + mark + Style.RESET_ALL
    elif pourcentage >= 50:
        return Back.YELLOW + Fore.BLACK + str(value) + mark + Style.RESET_ALL
    else:
        return Back.RED + Fore.WHITE + str(value) + mark + Style.RESET_ALL

# Build the results table
table_data = [categories] 
table_data.append(['Average description'] + [colorize_cell(val, nb_keys, '/'+str(nb_keys)) for val in AVG_des])
table_data.append(['Average comments'] + [colorize_cell(val, 100, '%') for val in AVG_com])
table_data.append(['Comments std'] + [val for val in com_std])
table_data.append(['Modification score (high creativity)'] + [colorize_cell(val, nb_answer, '/'+str(nb_answer)) for val in mod_high])
table_data.append(['Modification score (low creativity)'] + [colorize_cell(val, nb_answer, '/'+str(nb_answer)) for val in mod_low])

# Display table
table = tabulate(table_data, headers="firstrow", tablefmt="grid")
logger.info(table)
