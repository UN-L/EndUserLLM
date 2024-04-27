
import base64
import os
import re
import subprocess

from openai import OpenAI
from PIL import Image
###INITIALIZATIONS###

api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(
  api_key=api_key
)

#LaTeX management
def compile(file): #Run the latex command to compile in pdf
  command = 'pdflatex -shell-escape -interaction=nonstopmode -file-line-error '+file+' | grep ".*:[0-9]*:.*"'
  return subprocess.run(command, shell=True, stdout=subprocess.PIPE, text=True)

def convertToImg(pdf): #Run the convert command to convert the pdf into jpg
  command_convert = 'convert -density 300 -trim ' + pdf + ' -quality 100 ' + pdf.replace(".pdf", ".jpg")
  subprocess.run(command_convert, shell=True, text=True)


#Calculates the percentage difference between 2 pixels
def percentPix(pix1, pix2):
    return (abs(pix1-pix2)*100)/255

#Compares each pixel between the original image and the modified image. Returns a mask that shows the pixels that are different between the two images.
#img1: original image
#img2: modify image
#limit: pixel difference threshold (in %)
def mask(img1, img2, limit):
  res = img2
  res=res.convert('L').convert("RGB")
  pixels = res.load()
  for i in range(img1.size[0]):
      for j in range(img1.size[1]):
          if img1.getpixel([i, j]) != img2.getpixel([i, j]):
              if (percentPix(img2.getpixel([i, j])[0], img1.getpixel([i, j])[0])>limit 
                  or percentPix(img2.getpixel([i, j])[1], img1.getpixel([i, j])[1])>limit 
                  or percentPix(img2.getpixel([i, j])[2], img1.getpixel([i, j])[2])>limit):
                  pixels[i, j]=(255, 0, 0)
  return res

#Setting up GPT
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

tikz_file = "onlydog.tex"
res_file = "onlydog_modified.tex"
GPT4 = "gpt-4-1106-preview"
GPT3 = "gpt-3.5-turbo"

with open(tikz_file, "r") as f:
  tikz_file_content = f.read()


compile(tikz_file)
convertToImg(tikz_file.replace('.tex', '.pdf'))
tikz_img = Image.open(tikz_file.replace('.tex', '.jpg'))

tikz_lines = open(tikz_file, "r")
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
    
    tmp_tikz_lines = open(tikz_file, "r")
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
    zone_img = Image.open("tmp_zone.jpg")
    mask(zone_img, tikz_img, 2).save("zone.png") 

    answer=callGPTvision(make_messages("zone.png"), 0.2, 0.1, 1).choices[0].message.content #Ask the VLM to identify the zone
    commented_line=l.rstrip()+' %'+answer+'\n' #Turn answer into comment
    print(commented_line)

  else: commented_line=l
  commented_code_lines=commented_code_lines+commented_line

#commented_file = open("commented.tex", "w") #To see the commented code
#commented_file.write(commented_code_lines)
#commented_file.close()

prompt_goal="Changes the color of the dog's eyes to red"
messages=[
  {"role": "system", "content": "You are a helpful assistant for programming and customizing code. All you have to do is answer the question by writing the entire code with the modifications. To modify the code, use the comments. DO NOT answer anything other than the entire code. If you make mistakes, don't apologize, just send the entire code with the modifications"},
  {"role": "user", "content": commented_code_lines},
  {"role": "user", "content": prompt_goal},
]
result = callGPT(messages, GPT3, 1, 0.8, 1).choices[0].message.content #Make the modifications
try:
  code = re.split(r'\`\`\`.*', result)[1] #extract code
except:
  code = result

commented_file = open(res_file, "w")
commented_file.write(code)
commented_file.close()
compile(res_file)