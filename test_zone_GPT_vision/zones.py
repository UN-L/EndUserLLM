import re
import random
from matplotlib import patches
from openai import OpenAI
import os
import base64
import subprocess

import matplotlib.pyplot as plt
import matplotlib.ticker as plticker
import matplotlib.colors as mcolors

from PIL import Image

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
          "role": "system",
          "content": [
            {
              "type": "text",
              "text": "You are a helpful assistant for detect part of an image. All you have to do is answer the question by giving the area coordinates by zone. Be really precise about the coordinates"
            }
          ]
        },
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
      max_tokens= 1000,
      temperature=0,
      top_p=0
    
  ).choices[0].message.content


#Open files
div=16 #number of grid divisions
tikz_file = "onlydog.tex"
compile(tikz_file)
convertToImg(tikz_file.replace('.tex', '.pdf'))
image = Image.open(tikz_file.replace('.tex', '.jpg'))
my_dpi=300.

#Set up figure
fig=plt.figure(figsize=(float(image.size[0])/my_dpi,float(image.size[1])/my_dpi),dpi=my_dpi)
ax=fig.add_subplot(111)
fig.subplots_adjust(left=0,right=1,bottom=0,top=1)

# Set the gridding interval
interval=image.size[0]/div
loc = plticker.MultipleLocator(base=interval)
ax.xaxis.set_major_locator(loc)
ax.yaxis.set_major_locator(loc)

# Add the grid
ax.grid(which='major', axis='both', linestyle='-', linewidth=0.5)

# Add the image
ax.imshow(image)
fig.savefig('temp.png', dpi=300)

###Find image zones with GPT-Vision

#Parameters
tmp_img='temp.png'
prompt="There is a "+str(div)+"x"+str(div)+" grid on the image. Gives area coordinates for different parts of the image precisely knowing that the grid begin on the top left corner at [0,0]. Answer just the renctangles coordinates of the differents parts in this format: <name of the zone> -> [x,y] to [x,y]"
description = callGPTvision(tmp_img, prompt)
print(description)

#Add rectangles with a label to the final result
splitDes=description.split("\n")
for line in splitDes:
  colour=random.choice(list(mcolors.TABLEAU_COLORS)).split(':')[1] #Choose a random color

  splitLine=re.split(r' -> ', line)#Parse GPT-Vision result
  zone_name=splitLine[0]
  coords=re.findall(r'\d+', splitLine[1])
  stX=int(coords[0])#[X,0] to [0,0]
  stY=int(coords[1])#[0,X] to [0,0]
  ndX=int(coords[2])#[0,0] to [X,0]
  ndY=int(coords[3])#[0,0] to [0,X]

  ax.add_patch(patches.Rectangle((stX*interval, stY*interval), (ndX-stX)*interval+interval, (ndY-stY)*interval+interval, ec=colour, facecolor='none', zorder=10)) #add rectangle
  ax.text(stX*interval, stY*interval,zone_name,color=colour,ha='left',va='top', fontsize=6) #add label

fig.savefig('res.png', dpi=300)
