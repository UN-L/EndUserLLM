import re
import subprocess
from openai import OpenAI
from PIL import Image


def compile(file): #Run the latex command to compile in pdf
  command = 'pdflatex -shell-escape -interaction=nonstopmode -file-line-error '+file+' | grep ".*:[0-9]*:.*"'
  return subprocess.run(command, shell=True, stdout=subprocess.PIPE, text=True)

def convertToImg(pdf): #Run the command to convert the pdf into png
  command_convert = 'convert -density 300 -trim ' + pdf + ' -quality 100 ' + pdf.replace(".pdf", ".png")
  subprocess.run(command_convert, shell=True, text=True)

def generate_mask(img1, img2):
  res = Image.new('RGB', img1.size)
  pixels = res.load()
  for i in range(img1.size[0]):
      for j in range(img1.size[1]):
          if img1.getpixel((i, j)) != img2.getpixel((i, j)): #Make a mask with img1 and img2
              r1,g1,b1=img1.getpixel((i, j))
              r2,g2,b2=img2.getpixel((i, j))
              if (r2 != r1
                  or g2 != g1
                  or b2 != b1):
                  pixels[i, j]=(255, 255, 255)
  return res

#Compares each pixel between the original image and the modified image in a defined area. Returns the percentage of pixels in common.
#img1: original image
#img2: modified image
def computeScore(img1, img2, mask):
  res = Image.new('RGB', img1.size)
  pixels = res.load()
  score=0
  for i in range(img1.size[0]): #parkour each pixels of the images
      for j in range(img1.size[1]):
          if img1.getpixel((i, j)) != img2.getpixel((i, j)): #Make a mask with img1 and img2
              r1,g1,b1=img1.getpixel((i, j))
              r2,g2,b2=img2.getpixel((i, j))
              if (r2 != r1
                  or g2 != g1
                  or b2 != b1):
                  pixels[i, j]=(255, 255, 255)
          if (res.getpixel([i, j]) != mask.getpixel([i, j])): #Compares the two masks
            score+=1   
  return 100-(score/(img1.size[0]*img1.size[1]))*100 #Calculate the percentage

#/!\DEPRECATED
#Parse a file containing the tests to be done and returns a list of dicts with the test parameters.
#
#Here is an example of one test in the file:
# >>>Dog red eyes
# file::onlydog.tex
# model::gpt-3.5-turbo
# prompt::Change the color of the dog's eyes to red
# temperature::1
# top_p::0.8
# n::30
# mask::mask.png
# pattern::fill [BlueGrey900] (56, 0) circle [radius=20];
# <<<
#
#Section must begin with >>> with a label
#The section must end with <<<
#Values must be in this format: <parameter>::<value> between start and end
def parse_benchmark_file(file_path):
  file_lines = open(file_path, "r")
  result=[]
  section={}
  current_section_name=""
  for l in file_lines:
    if l != '\n':
      l=l.replace('\n', '')
      if re.findall('>>>', l):#Start of section
        section={}
        current_section_name = l.replace('>>>', '')
        section['label'] = current_section_name
      elif re.findall('<<<', l): #End of section
        if(len(section) != 0): result.append(section)
      else:
        splitted_line = l.split(r"::")
        try:
          section[splitted_line[0]]=float(splitted_line[1])
        except:
          section[splitted_line[0]]=splitted_line[1]

  return result

  
def callGPT(api_key, message, model, temp, top_p, n=1):

  client = OpenAI(
    api_key=api_key
  )
  messages=message

  return client.chat.completions.create(
    model=model,
    messages=messages,
    temperature=temp,
    top_p=top_p,
    n=n
  )


def benchmark(api_key, TikZ_file, model, message, pattern, mask_path, temp=1, top_p=0.8, n=1):

  codes = callGPT(api_key, message, model, temp, top_p, n)
  score=0
  fail_score=0
  code_score=0

  for com in codes.choices:
    
    try:
      code = re.split(r'\`\`\`.*', com.message.content)[1] #extract code
    except:
      code = com.message.content

    if pattern.lower() in code.lower(): code_score+=1 #Verify if the pattern in the yaml is in the modified code

    tmp_file = "tmp.tex"
    f = open(tmp_file, "w")
    f.write(code)
    f.close()

    if compile(tmp_file).stdout == "": #If there are no compilation errors
      convertToImg(tmp_file.replace('.tex', '.pdf'))
      tmp_img = Image.open(tmp_file.replace('.tex', '.png'))
      
      compile(TikZ_file)
      convertToImg(TikZ_file.replace(".tex", ".pdf"))
      tikz_img = Image.open(TikZ_file.replace('.tex', '.png'))

      mask = Image.open(mask_path)

      if (computeScore(tmp_img.convert("RGB"), tikz_img.convert("RGB"), mask.convert("RGB"))>99.9): # Compare the two masks and gives the percentage of pixels in common. If there are more then 99.9% common pixels the two images match
          print("Match")
          score += 1
      else:
          print("No match")
    else: 
      fail_score+=1
      print("Fail")

  return (score, fail_score, code_score)