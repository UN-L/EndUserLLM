
import base64
import glob
import logging
import os
import re
import subprocess
import sys

from openai import OpenAI
from PIL import Image

from benchmark_func import convertToImg, compile, generate_mask

###INITIALIZATIONS###
if len(sys.argv) <=1:
   exit(0) 

if(not os.path.exists('masks')):
  os.mkdir('masks')

dirlogs = "masks/"
logfile = dirlogs+'mutations.log'
logger = logging.getLogger("agent")
logger.addHandler(logging.FileHandler(logfile))
logger.addHandler(logging.StreamHandler())
logging.root.setLevel(logging.NOTSET)


###PARAMETERS###

tikz_file = sys.argv[1]

with open(tikz_file, "r") as f:
  tikz_file_content = f.read()


compile(tikz_file)
convertToImg(tikz_file.replace('.tex', '.pdf'))
tikz_img = Image.open(tikz_file.replace('.tex', '.png'))

tikz_lines = open(tikz_file, "r")
pattern = r'\\fill\s*\[([^\]]+)\]'

def replace_callback(match): #Changes color to red (or blue if already red)
    color = match.group(1)
    if color.lower() == 'red':
        return '\\fill [Blue]'
    else:
        return '\\fill [Red]'

#Rewrite the TikZ file with the commented lines
count=0
for i, l in enumerate(tikz_lines): #for each line of the TikZ file
  commented_line=""
  if re.findall(pattern, l): #if line contain "/fill"
    count+=1
    modified_line = re.sub(pattern, replace_callback, l) #Replace color
    logger.info("mask"+str(count))
    logger.info(l)
    logger.info(modified_line)
    tmp_tikz_lines = open(tikz_file, "r")
    tmp_code=""
    for j, m in enumerate(tmp_tikz_lines): #Replace the line with new color
      if i==j:
        m=modified_line
      tmp_code= tmp_code + m
    
    tmp = open("tmp_mask.tex", "w") #Rewrite the TikZ file the modified line
    tmp.write(tmp_code)
    tmp_tikz_lines.close()
    tmp.close()

    compile("tmp_mask.tex")
    convertToImg("tmp_mask.pdf")
    zone_img = Image.open("tmp_mask.png")
    generate_mask(zone_img.convert("RGB"), tikz_img.convert('RGB')).save("masks/mask"+str(count)+".png") 

for f in glob.glob("tmp_mask.*"):
    os.remove(f)