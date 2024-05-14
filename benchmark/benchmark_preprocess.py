import os
import re
import sys
import base64
import pandas as pd
from yaml import Loader, load_all

from openai import OpenAI

from datetime import datetime
import logging
from PIL import Image

from benchmark_func import convertToImg, parse_benchmark_file, benchmark, compile
###INITIALIZATIONS###

if len(sys.argv) <=1:
   exit(0) 

api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(
  api_key=api_key
)


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


#Calculates the percentage difference between 2 pixels
def percentPix(pix1, pix2):
    return (abs(pix1-pix2)*100)/255

#Compares each pixel between the original image and the modified image. Returns a mask that shows the pixels that are different between the two images.
#img1: original image
#img2: modify image
#limit: pixel difference threshold (in %)
def mask_BW(img1, img2):
  res = img2
  res=res.convert('L').convert("RGB")
  pixels = res.load()
  for i in range(img1.size[0]):
      for j in range(img1.size[1]):
          if img1.getpixel((i, j)) != img2.getpixel((i, j)):
              r1,g1,b1=img1.getpixel((i, j))
              r2,g2,b2=img2.getpixel((i, j))
              if (r2 != r1
                  or g2 != g1
                  or b2 != b1):
                  pixels[i, j]=(255,0,0)
  return res



#Setting up the logger
if(not os.path.exists('logs')):
  os.mkdir('logs')

dirlogs = "logs/benchmark_" + datetime.today().strftime("%d-%m-%Y:%H:%M:%S")
logfile = dirlogs+'/outputs.log'
os.mkdir(dirlogs)
logger = logging.getLogger("agent")
logger.addHandler(logging.FileHandler(logfile))
logger.addHandler(logging.StreamHandler())
logging.root.setLevel(logging.NOTSET)

with open(sys.argv[1], "r") as f:
  benchmark_file_content = f.read()

resuts={}

for test in load_all(benchmark_file_content, Loader=Loader):
  ###PARAMETERS###

  TikZ_file=test['file']
  n= test['n']
  logger.info("")
  logger.info("===PARAMETERS===")
  logger.info("Prompt: " + test['prompt'])
  logger.info("Input file: " + TikZ_file)
  logger.info("Model: " + test['model'])
  logger.info("Temperature: "+ str(test['temperature']))
  logger.info("Top_P: "+ str(test['top_p']))
  logger.info("")

  ###MUTATIONS###
  with open(TikZ_file, "r") as f:
    tikz_file_content = f.read()

  compile(TikZ_file)
  convertToImg(TikZ_file.replace('.tex', '.pdf'))
  tikz_img = Image.open(TikZ_file.replace('.tex', '.png'))

  tikz_lines = open(TikZ_file, "r")
  pattern = r'\\fill\s*\[([^\]]+)\]'

  def replace_callback(match): #Changes color to red or blue if already red
      color = match.group(1)
      if color.lower() == 'red':
          return '\\fill [blue]'
      else:
          return '\\fill [red]'

  def make_messages(image_path): #Create an image prompt
    base64_image=encode_image(image_path)
    return [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "What is the parts in red in the image correspond to without mentioning \"parts in red\"? Answer something like \"These parts refer to...\"."
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

  commented_code_lines=""

  #Rewrite the TikZ file with the commented lines
  for i, l in enumerate(tikz_lines): #for each line of the TikZ file
    commented_line=""
    if re.findall(pattern, l): #if line contain "/fill"
      modified_line = re.sub(pattern, replace_callback, l) #Replace color
      
      tmp_tikz_lines = open(TikZ_file, "r")
      tmp_code=""
      for j, m in enumerate(tmp_tikz_lines): #Replace the line with new color
        if i==j:
          m=modified_line
        tmp_code= tmp_code + m
      
      tmp = open("tmp_zone.tex", "w") #Rewrite the TikZ file the modified line
      tmp.write(tmp_code)
      tmp_tikz_lines.close()
      tmp.close()

      compile("tmp_zone.tex")
      convertToImg("tmp_zone.pdf")
      zone_img = Image.open("tmp_zone.png")
      mask_BW(zone_img.convert('RGB'), tikz_img.convert('RGB')).save("zone.png") 

      answer=callGPTvision(make_messages("zone.png"), 0.2, 0.1, 1).choices[0].message.content #Ask the VLM to identify the zone
      commented_line=l.rstrip()+' %'+answer+'\n' #Turn answer into comment
      
      print(commented_line)

    else: commented_line=l
    commented_code_lines=commented_code_lines+commented_line

  ##BENCHMARK##
  message=[
    {"role": "system", "content": "You are a helpful assistant for programming and customizing code. All you have to do is answer the question by writing the entire code with the modifications. To modify the code, use the comments. DO NOT answer anything other than the entire code. If you make mistakes, don't apologize, just send the entire code with the modifications"},
    {"role": "user", "content": commented_code_lines},
    {"role": "user", "content": test['prompt']},
  ]

  score, fail_score, code_score = benchmark(api_key, TikZ_file, test['model'], message, test['pattern'], test['mask'], 
                                              float(test['temperature']), float(test['top_p']), int(test['n']) )

  logger.info("")
  logger.info("Successes: " + str(score)+"/"+str(n))
  logger.info("No matches: " + str(n-score-fail_score)+"/"+str(n))
  logger.info("Code matches: " + str(code_score)+"/"+str(n))
  logger.info("Compilation failures: " + str(fail_score)+"/"+str(n))
  logger.info("")
  resuts[test['label']]={'Successes': score, 'No matches': n-score-fail_score, 'Code matches': code_score, 'Compilation failures': fail_score}
  
logger.info("LaTeX table: ")
logger.info(pd.DataFrame(resuts).to_latex())