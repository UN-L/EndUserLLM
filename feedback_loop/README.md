This script performs a post-processing step, automatically rectifying the Language Model (LLM) through a Vision-Language Model (VLM). The selected VLM, moondream1, is a small model capable of CPU execution, allowing moondream1 (and the VLM in general) to be tested as an oracle. This method can correct the LLM and provides automated feedback, enhancing the reliability of code modifications.

However, we've identified two significant challenges with this approach:
- The LLM applies the corrections but does not converge on the solution.

- VLMs cannot compare two images, only describe them.
So it cannot decide whether or not the result corresponds to the initial goal.


You can run the script directly, as it contains an example. But you must provide the user prompt that defines the end goal when you run the script:
`python3 feedback_loop.py "Changes the color of the dog's eyes to red"`

You can also modify the prompt and input file directly in the script.