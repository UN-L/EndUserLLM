import os
import sys
import re
import subprocess
import logging
from datetime import datetime
import shutil
import base64
from tree_sitter import Language, Parser

from transformers import AutoModelForCausalLM, CodeGenTokenizerFast as Tokenizer #Moondream1
from PIL import Image

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


### Inputs 
#if(len(sys.argv) <= 1):
#  logger.error("No arguments")
#  exit()


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
      max_tokens= 300
  ).choices[0].message.content

def callGPT(messages, model, temp, top_p):
  return client.chat.completions.create(
    model=model,
    messages=messages,
    temperature=temp,
    top_p=top_p,
  ).choices[0].message.content

    
#### Input data
#prompt_goal = sys.argv[1]
prompt_goal = "Change the color of the dog's eyes to red"
#sys_goal = "You are a helpful assistant for programming and customizing code. All you have to do is answer the question by just writing the lines where the code must be changed and the modified part of the code. Just write the original code and modified code. If you make mistakes, don't apologize!"
sys_goal = "You are a helpful assistant for programming and customizing code. All you have to do is answer the question by writing the entire code with the modifications. DO NOT answer anything other than the entire code. If you make mistakes, don't apologize, just send the entire code with the modifications"
tikz_file = "onlydog.tex"
#Change the color of the dog's eyes to red

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

# Setting up Tree sitter
Language.build_library(
    # Store the library in the "build" directory
    "build/latex.so",
    ["tree-sitter-latex-master"],
)
"""
#Extract code blocks
LATEX_LANGUAGE = Language("build/latex.so", "latex")

parser = Parser()
parser.set_language(LATEX_LANGUAGE)

byte_tikz_content=bytes(tikz_file_content, "utf8")
tree = parser.parse(byte_tikz_content)

def extract_code_blocks(node):
    code_blocks = []
    if node.type == 'generic_command' and node.start_point[0] != node.end_point[0]:
        code_blocks.append(node)

    for child in node.children:
        # Recursively search for code blocks in the children
        code_blocks.extend(extract_code_blocks(child))

    return code_blocks

# Assuming the root of the parsed tree is the "document" node
root_node = tree.root_node

# Extract code blocks from the entire document
all_code_blocks = extract_code_blocks(root_node)
"""
compile(tikz_file)
convertToImg(tikz_file.replace('.tex', '.pdf'))
description = callGPTvision(tikz_file.replace('.tex', '.jpg'), "Describe the image")
logger.info("description: "+ description)

"""
# Commenting each code blocks
comments=""
for code_block in all_code_blocks:
    msgToComments=[
      {"role": "system", "content": "You are a helpful assistant for commenting and documenting code. All you have to do is answer the question by commenting the code block provided"},
      {"role": "user", "content": byte_tikz_content[code_block.start_byte:code_block.end_byte].decode('utf8')},
      {"role": "user", "content": "Here is the description of the code result: "+ description},
      {"role": "user", "content": "What does this piece of code refer to in relation to the description? Comment on what each function does!"},
    ]
    comment=callGPT(msgToComments, LLMmodel, 1, 0.8)
    comments= comments + "\n" + comment
"""
msgToComments=[
      {"role": "system", "content": "You are a helpful assistant for commenting and documenting code. All you have to do is answer the question by commenting the code block provided"},
      {"role": "user", "content": tikz_file_content},
      {"role": "user", "content": "Here is the description of the code result: "+ description}, #on what each function does! And which 
      {"role": "user", "content": "Comments the code blocks in relation the description and what this represents in the context of the description. You will be very precise! And you must give the entire code with comments inside"},
    ]
comments = callGPT(msgToComments, LLMmodel, 1, 0.5)
logger.info("comments: "+ comments)

msgToModify=[
    {"role": "system", "content": sys_goal},
    #{"role": "user", "content": tikz_file_content},
    {"role": "user", "content": comments},
    #{"role": "user", "content": "Here is the code documentation: " + comments},
    {"role": "user", "content": prompt_goal},
]

iter=1
while True:
  
  logger.info("======= "+ str(iter) + " =======")

  strAnswer = callGPT(msgToModify, LLMmodel, 0.2, 0.1)

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
    shutil.copyfile(resFile, dirlogs+"/iteration"+str(iter)+".tex") #Keeps a record of each iteration by copying the .tex and .pdf files into the logs
    shutil.copyfile(resFile.replace(".tex", ".pdf"), dirlogs+"/iteration"+str(iter)+".pdf")

  else: # Send automatically compilaton errors 
    msgToModify.append({"role": "user", "content": "There are errors when compiling. Please fix them:\n"+result.stdout})
  
  nbChars = 0
  for msg in msgToModify:
    nbChars += len(msg['content'])
  
  if (nbChars > 10000): #free space in messages so as not to exceed the token limit
    logger.info("RESET TOKENS")
    msgToModify = [
      {"role": "system", "content": sys_goal},
      {"role": "user", "content": tikz_file_content},
      {"role": "user", "content": "Here is the code documentation: " + comments},
      {"role": "user", "content": prompt_goal},
    ]
  break


  iter+=1
logger.info("====DONE====")