These scripts are designed to perform a benchmark of GPT's performance in code modification.

It consists of four files for this benchmark:

- `benchmark_func`: contains all the necessary functions to execute the benchmark
- `benchmarkGPT`: runs the benchmark on GPT alone
- `benchmark_preprocess`: runs the benchmark on GPT with preprocessing
- `mask_maker`: allows you to generate simple masks with a TikZ file as input by making mutations in the code.

`mask_maker` take a TikZ file like `dog.tex` as in input and returns masks in the repertory `masks` in the form of a black and white image representing one of the image areas. This area corresponds to an area that has been modified in the code. These masks allow the oracle to compare two results.

To execute `benchmarkGPT` and `benchmark_preprocess`, you need to provide a YAML file as the program input. For example:
`python3 benchmarkGPT benchmark.yaml`
In the YAML file, you will need specify the parameters for each test separated by `---`. For example:

```yaml
label: Dog red eyes
file: onlydog.tex
model: gpt-3.5-turbo
prompt: Changes eye color to red
temperature: 1
top_p: 0.8
n: 30
mask: masks/dog_mask7.png
pattern: fill [Red] (56, 0)

---

label: Bee red abdomen
file: bee.tex
model: gpt-3.5-turbo
prompt: Changes abdomen color to red
temperature: 1
top_p: 0.8
n: 30
mask: masks/bee_mask5.png
pattern: fill [Red] (-256, -160 + \i*80)
```

In this file, each YAML block represents an individual test. The keys and their values indicate the test details:

- `label`: a descriptive label for the test
- `file`: the TikZ file on which the test should be performed
- `model`: the GPT model to use
- `prompt`: the prompt text for GPT, describing the modification to be made
- `temperature`: the temperature for generating GPT outputs
- `top_p`: the top_p for generating GPT outputs
- `n`: the number of results to generate (i.e. the number of test)
- `mask`: to determine whether or not modifications have been made
- `pattern`: the modification in the code we want to find

You can find the YAML example that was used to run the first tests.

`benchmarkGPT` and `benchmark_preprocess` will return a log file with results of the tests. The results are in this form:
```yaml
Successes: 24/30.0
No matches: 4/30.0
Code matches: 20/30.0
Compilation failures: 2/30.0
```
- `Successes` : the number of times GPT has successfully made the change
- `No mathches` : the number of times GPT has failed to make the change
- `Code matches` : The number of times the modification corresponds to the desired modification in the code (less important than "successes" as it only takes into consideration a specific area of the code. The oracle may not be relevant).
- `Failures` : the number of times the code was not compiled

It return also a LaTeX table.