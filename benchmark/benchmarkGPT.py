import os
import sys
from yaml import Loader, load_all


from datetime import datetime
import logging
import pandas as pd

from benchmark_func import parse_benchmark_file, benchmark
###INITIALIZATIONS###

if len(sys.argv) <=1:
   exit(0) 

api_key = os.getenv('OPENAI_API_KEY')
if (api_key == ""):
  print("The api_key client option must be set either by passing api_key to the client or by setting the OPENAI_API_KEY environment variable")
  exit(1)


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

for test in load_all(benchmark_file_content, Loader=Loader): #For each test in the yaml do the modification
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
  
  with open(TikZ_file, "r") as f:
        TikZ_file_content = f.read()

  message = [
    {"role": "system", "content": "You are a helpful assistant for programming and customizing code. All you have to do is answer the question by writing the entire code with the modifications. To modify the code, use the comments. DO NOT answer anything other than the entire code. If you make mistakes, don't apologize, just send the entire code with the modifications"},
    {"role": "user", "content": TikZ_file_content},
    {"role": "user", "content": test['prompt']},
  ]
  #Call the benchmark with all parameters
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