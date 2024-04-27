This script performs a pre-processing step by commented the code, identifying areas in the image before modifying the code using GPT-3. For every line containing  `/fill`, the script mutate the color to show distinct zones within the image. These zones are then given into GPT-Vision for labeling, and the resulting labels are utilized to write comments for the corresponding lines where there are mutations. This links the image areas to the code, so that the LLM can better understand the code. Following this pre-processing phase, the annotated code is then passed to GPT-3 for final modifications.

The results have been quite impressive!

You can run the script directly, as it contains an example.

You can modify the prompt and input file directly in the script.