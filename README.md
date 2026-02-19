# AI Choreography Generator & Validator

This project explores the use of Large Language Models (LLMs), specifically Google's Gemini models, to generate, validate, and analyze dance choreography. It employs a feedback loop to refine generated choreographies against physical constraints.

## Project Structure

- **`creative_generation.ipynb`**: The main notebook for generating choreography. It interfaces with Gemini models to produce dance descriptions and convert them into structured JSON. It includes an iterative refinement process using `validator.py` to correct physical violations.
- **`validator.py`**: A Python script that validates choreography JSON files against a set of rules (e.g., stage boundaries, collision avoidance, speed limits). It can be run independently or imported as a module.
- **`Analysis.ipynb`**: A notebook for analyzing the generated valid choreographies. It calculates metrics (speed, spatial usage, partner interaction) and generates visualizations (timelines, heatmaps, error analysis).
- **`valid_choreography/`**: Directory containing the final, validated choreography JSON files.
- **`outputs/`**: Directory where analysis plots and reports are saved.
- **`base_choreography_prompt/` & `modified_choreography_prompt/`**: Directories for storing intermediate outputs and logs from different prompting strategies.

## Setup

To run this project, you need Python installed along with the following libraries:

```bash
pip install numpy matplotlib google-generativeai huggingface_hub
```

*Note: You will need a Google Gemini API key to run the generation notebook.*

## Usage

### 1. Generating Choreography

1.  Open `creative_generation.ipynb` in Jupyter Notebook or Google Colab.
2.  Set your API key in the `API_KEY` variable.
3.  Run the cells to start the generation process. The script will:
    -   Generate a natural language description of a dance.
    -   Convert it to JSON format.
    -   Validate the JSON using `validator.py`.
    -   If violations are found (e.g., collisions, speed limits), it feeds the errors back to the LLM to request a correction.
    -   Save the final valid choreography in the appropriate directory.

### 2. Validating Choreography

You can validate a choreography JSON file directly using the command line:

```bash
python validator.py path/to/choreography.json
```

This will print a report of any violations found (collisions, out-of-bounds, speed limits, etc.).

### 3. Analyzing Results

Open `Analysis.ipynb` to visualize and analyze the generated choreographies.
This notebook reads files from `valid_choreography/` and produces:
-   Event timelines for each dancer.
-   Spatial trajectories and heatmaps.
-   Statistical analysis of speed, spread, and other metrics.
-   Convergence plots showing the refinement process.

## Methodology

The project uses a **Generation -> Validation -> Refinement** loop:
1.  **Generation**: The LLM creates a choreography based on a prompt (e.g., "contemporary dance for 3 dancers").
2.  **Structured Output**: The text is converted into a JSON format representing a 25x25 grid stage.
3.  **Validation**: `validator.py` checks for physical realism:
    -   **Grid Size**: 25x25.
    -   **Time Step**: 1 second.
    -   **Max Speed**: 4 grid units/second.
    -   **No Collisions**: Dancers cannot occupy the same cell.
    -   **No Excessive Pauses**: Dancers cannot be stationary for > 60 seconds.
4.  **Refinement**: If the choreography is invalid, the error report is sent back to the LLM, which attempts to fix the specific violations.
