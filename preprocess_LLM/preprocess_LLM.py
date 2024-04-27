import os
import re
import subprocess
import logging
from datetime import datetime
import shutil
import base64

from openai import OpenAI

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

# OpenAI API Key
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(
  api_key=api_key
)


def compile(file): #Run the latex command to compile in pdf
  command = 'pdflatex -shell-escape -interaction=nonstopmode -file-line-error '+file+' | grep ".*:[0-9]*:.*"'
  return subprocess.run(command, shell=True, stdout=subprocess.PIPE, text=True)

def convertToImg(pdf): #Run the latex command to convert the pdf into jpg
  command_convert = 'convert -density 300 -trim ' + pdf + ' -quality 100 ' + pdf.replace(".pdf", ".jpg")
  subprocess.run(command_convert, shell=True, text=True)

def encode_image(image_path): #Function to encode the image
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
    
def callGPTvision(image_path, prompt):
  base64_image = encode_image(image_path)

  return client.chat.completions.create(
      model= "gpt-4-vision-preview",
      messages= [
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
      ],
      max_tokens= 300,
      temperature= 0
  ).choices[0].message.content

def callGPT(messages, model, temp, top_p):
  return client.chat.completions.create(
    model=model,
    messages=messages,
    temperature=temp,
  ).choices[0].message.content

    
#### Input data
prompt_goal = "Change the color of the dog's eyes to red"
sys_goal = "You are a helpful assistant for programming and customizing code. All you have to do is answer the question by writing the entire code with the modifications. DO NOT answer anything other than the entire code. If you make mistakes, don't apologize, just send the entire code with the modifications"
tikz_file = "onlydog.tex"

#LLMmodel="gpt-4-1106-preview"
LLMmodel="gpt-3.5-turbo"


logger.info("===INITIALIZATION===")
logger.info("Goal: " + prompt_goal)
logger.info("Input file: " + tikz_file)
logger.info("Model: " + LLMmodel)
logger.info("System goal: "+ sys_goal)
logger.info("Temperature: "+ str(0.2))
logger.info("Top_P: "+ str(0.1))
logger.info("")
logger.info("===PROCESSING===")

#### asking the question (GPT)
# content of tikz_file (string)
with open(tikz_file, "r") as f:
    tikz_file_content = f.read()

print("Compiling")
compile(tikz_file)
convertToImg(tikz_file.replace('.tex', '.pdf'))
print("GPTVision")
description = callGPTvision(tikz_file.replace('.tex', '.jpg'), "Describe the image")
logger.info("description: "+ description)

msg_to_comments=[ #Prompt to write comments
      {"role": "system", "content": "You are a helpful assistant for commenting code. All you have to do is answer the question by commenting the code block provided"},
      {"role": "user", "content": tikz_file_content},
      {"role": "user", "content": "Here is the description of the code result: "+ description},
      {"role": "user", "content": "Comments the code blocks in relation the description and what this represents in the context of the description. You will be very precise! And you must give the entire code with comments inside"},
    ]
print("Comments")
comments = callGPT(msg_to_comments, "gpt-4-1106-preview", 0, 0.1)
logger.info("comments: "+ comments)

msg_to_modify=[ #Prompt to modify the code
    {"role": "system", "content": sys_goal},
    {"role": "user", "content": comments},
    {"role": "user", "content": prompt_goal},
]

strAnswer = callGPT(msg_to_modify, LLMmodel, 0.2, 0.1)

#### Results
logger.info("Answer:")
logger.info(strAnswer)

resFile = tikz_file.replace(".tex", "_modified.tex")
f = open(resFile, "w")
reg=r'\`\`\`.*'
if re.search(reg, strAnswer):
  f.write(re.split(reg, strAnswer)[1])
else:
  f.write(strAnswer)
f.close()

#compile the TikZ
result = compile(resFile)

if result.stdout == "": # If no compilation errors
  shutil.copyfile(resFile, dirlogs+"/res.tex") #Keeps a record of each iteration by copying the .tex and .pdf files into the logs
  shutil.copyfile(resFile.replace(".tex", ".pdf"), dirlogs+"/res.pdf")

else: # Send automatically compilaton errors 
  msg_to_modify.append({"role": "user", "content": "There are errors when compiling. Please fix them:\n"+result.stdout})

nbChars = 0
for msg in msg_to_modify:
  nbChars += len(msg['content'])

if (nbChars > 10000): #free space in messages so as not to exceed the token limit
  logger.info("RESET TOKENS")
  msg_to_modify = [
    {"role": "system", "content": sys_goal},
    {"role": "user", "content": tikz_file_content},
    {"role": "user", "content": "Here is the code documentation: " + comments},
    {"role": "user", "content": prompt_goal},
  ]

logger.info("====DONE====")