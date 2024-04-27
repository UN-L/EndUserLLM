# LLM and VLM-assisted code modification

This repository explores the possibilities of end-user, multi-modal programming with generative AI, specifically focusing on GPT. The primary goal is to investigate whether non-programmers can create non-trivial applications, such as games, using natural language instructions with GPT. This repository focuses exclusively on modifying simple elements on vector images compiled in TikZ 


## Usage

**Note: These scripts are designed to run on Linux and have been tested on python 3.10**

First of all, to use this repository, you'll need the LaTeX compiler and the `pdflatex` command to compile TikZ files.

Ensure you have Python 3 installed on your Linux system and install the required dependencies:

```bash
pip install -r requirements.txt
```

You will need an OpenAI API key and set it as an environment variable before run scripts:

```bash
export OPENAI_API_KEY=api-key
```

Make sure you have the following prerequisites installed:

- ImageMagick (convert command)

If you have problems with ImageMagick's security policy, add the following line in `/etc/ImageMagick-6/policy.xml` before `<policymap>`
```XML
<policy domain="coder" rights="read | write" pattern="PDF"/>
```

## Directory structure

- `feedback_loop`: contains the script for generating code modifications with the feedback loop.
- `preprocess_LLM`: the first GPT preprocessing test with comments.
- `benchmark_preprocess`: contains the benchmark for testing each step of the preprocessing.
- `preprocess_mutations`: contains the script with the preprocessing that makes mutations in the code.
- `test_zone_GPT_vision`: a small test of how GPT-Vision can find the different zones of an image.
- `benchmark_GPT`: a benchmark of GPT with and without preprocessing to test if the preprocessing with mutations is efficient.