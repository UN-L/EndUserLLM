import os
import sys
import re
import subprocess
import logging
from datetime import datetime
import shutil

from transformers import AutoModelForCausalLM, CodeGenTokenizerFast as Tokenizer #Moondream1
from PIL import Image

from openai import OpenAI

if(not os.path.exists('logs')):
  os.mkdir('logs')

#Set up logger
dirlogs = "logs/agent_logs_" + datetime.today().strftime("%d-%m-%Y:%H:%M:%S")
logfile = dirlogs+'/outputs.log'
os.mkdir(dirlogs)
logger = logging.getLogger("agent")
logger.addHandler(logging.FileHandler(logfile))
logger.addHandler(logging.StreamHandler())
logging.root.setLevel(logging.NOTSET)

#Set up moondream
model_id = "vikhyatk/moondream1"
model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True)
tokenizer = Tokenizer.from_pretrained(model_id)

# OpenAI API Key
api_key = os.getenv('OPENAI_API_KEY')

### Inputs 
if(len(sys.argv) <= 1):
  logger.error("No arguments")
  exit()


def compile(file):
  command = 'pdflatex -shell-escape -interaction=nonstopmode -file-line-error '+file+' | grep ".*:[0-9]*:.*"'
  return subprocess.run(command, shell=True, stdout=subprocess.PIPE, text=True)

def convertToImg(pdf):
  command_convert = 'convert -density 300 -trim ' + pdf + ' -quality 100 ' + pdf.replace(".pdf", ".jpg")
  subprocess.run(command_convert, shell=True, text=True)

def callMoondream(img, prompt):
  image = Image.open(img)
  enc_image = model.encode_image(image)
  return model.answer_question(enc_image, 'Is this image corresponds to this goal: "' + prompt + '"?', tokenizer)

prompt_goal = sys.argv[1]

sys_goal = "You are a helpful assistant for programming and customizing code. All you have to do is answer the question by writing the entire code with the modifications. DO NOT answer anything other than the entire code. If you make mistakes, don't apologize, just send the entire code with the modifications"
tikz_file = "onlydog.tex"
#Change the color of the dog's eyes to red
#LLMmodel="gpt-4-1106-preview"

LLMmodel="gpt-3.5-turbo"
mnPrompt='Is this image corresponds to this goal: \\"'+prompt_goal+'\\"?'
logger.info("===INITIALIZATION===")
logger.info("Goal: " + prompt_goal)
logger.info("Input file: " + tikz_file)
logger.info("Model: " + LLMmodel)
logger.info("System goal: "+ sys_goal)
logger.info("Moondream's prompt: "+ mnPrompt)
logger.info("")
logger.info("===PROCESSING===")

#### asking the question (GPT-4)
# content of tikz_file (string)
with open(tikz_file, "r") as f:
    tikz_file_content = f.read()
    prompt = tikz_file_content + "\n\n" + prompt_goal
messages=[
    {"role": "system", "content": sys_goal},
    {"role": "user", "content": prompt},
]

iter=1
while True:
  
  logger.info("======= "+ str(iter) + " =======")
  client = OpenAI(
      api_key=api_key
  )

  response = client.chat.completions.create(
    model=LLMmodel,
    messages=messages,
    temperature=0
  )

  logger.info("Response:")
  logger.info(response)

  strAnswer = response.choices[0].message.content
  response.choices
  logger.info("Answer:")
  logger.info(strAnswer)
  messages.append({"role": "assistant", "content": strAnswer})

  # write the result in a file
  resFile = tikz_file.replace(".tex", "_modified.tex")
  f = open(resFile, "w")
  reg=r'\`\`\`.*'
  if re.search(reg, strAnswer):
    f.write(re.split(reg, strAnswer)[1])
  else:
    f.write(strAnswer)
  f.close()

  #compile the TikZ
  command = 'pdflatex -shell-escape -interaction=nonstopmode -file-line-error '+resFile+' | grep ".*:[0-9]*:.*"'
  result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, text=True)
  
  nbChars = 0
  for msg in messages:
    nbChars += len(msg['content'])
  
  if (nbChars > 10000): #free space in messages so as not to exceed the token limit
    logger.info("RESET TOKENS")
    messages = [
      {"role": "system", "content": sys_goal},
      {"role": "user", "content": prompt_goal},
      {"role": "assistant", "content": strAnswer},
    ]
    
  if result.stdout == "": # If no compilation errors
    logger.info("Convert the pdf...")
    convertToImg(resFile.replace(".tex", ".pdf"))
    shutil.copyfile(resFile, dirlogs+"/iteration"+str(iter)+".tex")
    shutil.copyfile(resFile.replace(".tex", ".pdf"), dirlogs+"/iteration"+str(iter)+".pdf")
    logger.info("Analyzing results...")
    return_msg = callMoondream(resFile.replace(".tex", ".jpg"), prompt_goal)
    logger.info("Moondream : " + return_msg)

    if (re.search(r'^Yes', return_msg)): #If yes, the programme stops
      break
    else: #If no, the correction is sent
      messages.append({"role": "user", "content": return_msg})
    
  else: # Send automatically compilaton errors 
    logger.info("There are errors :")
    logger.info(result.stdout)
    logger.info("Sending errors ...")
    messages.append({"role": "user", "content": "There are errors when compiling. Please fix them:\n"+result.stdout})

  iter+=1
logger.info("====DONE====")
