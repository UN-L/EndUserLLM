This is the first benchmarking test for the first preprocess.

This script performs a benchmark of the entire "pre-preprocessing" process, involving three distinct steps:

- Description generation with a VLM (GPT-Vision).
- Comments generation employing a LLM (GPT-4).
- Modifications generation using another LLM (GPT-3).

In each step, the VLM and LLM generate 10 responses, and an oracle evaluates and selects the best answer for the next step:

- VLM -> 10 descriptions generated -> Select the best description.
- LLM -> 10 commented codes generated -> Select the best commented code.
- LLM (again) -> 10 modified codes generated -> Test each modified code and assign a final score.

The script display a table that resume the benchmark:
- "Average description" corresponds to the average number of keywords in the description.
- "Average comments" corresponds to the average percentage of commented code between the target code (the code we want to get closer to) and the generated commented code.
- "Comment std" corresponds to the standard deviation of generated commented code. The higher the standard deviation, the less constant the LLM.
- "Modification score" represents to the number of modifications that lead to the correct result (i.e. when the dog's eyes are red). "High creativity" for a temperature of 1 and a Top-p of 0.8 and "Low creativity" for a temperature of 0.2 and a Top-p of 0.1.

You can run the script directly, as it contains an example only for red eyes because GPT-3 has trouble to modify eyes color. A good result in this test suggests potential success in other parts of the image.

