# LLM Evaluation 2025

## Project Overview
This project evaluates various Large Language Models (LLMs) on medical question answering tasks, with a focus on heart failure and cardiomyopathy information. The evaluation compares responses from multiple models including OpenAI, Anthropic, Google, DeepSeek, Perplexity, and XAI.

## Project Structure

```
llm_eval2025/
├── configs/           # Configuration files
├── data/              # Input question datasets
│   └── questions/     # CSV files with patient questions
├── logs/              # Log files from evaluation runs  
├── notebooks/         # Jupyter notebooks for exploration and testing
│   └── test/          # API testing notebooks
├── outputs/           # Model outputs and processed data
│   └── chats/         # CSV files with model responses
├── scripts/           # Python scripts for running evaluations
│   └── test/          # Script testing files
└── requirements.txt   # Python dependencies
```

## Key Scripts

- `scripts/run_model_queries.py`: Main script for running queries against multiple LLM APIs
- `scripts/run_queries.sh`: Shell script wrapper for running the Python query script with specific configurations
- `scripts/prep_app_data.py`: Processes and combines model responses for use in evaluation app
- `scripts/rerun_failed_anthropic.py`: Utility to rerun failed queries for the Anthropic model

## Data Flow

1. Questions are loaded from CSV files in the `data/questions/` directory
2. The `run_model_queries.py` script sends these questions to various LLM APIs
3. Raw responses are saved as pickle files in `outputs/chats/`
4. Responses are then processed and converted to CSV format
5. The `prep_app_data.py` script combines responses from successful runs and performs quality checks
6. Final processed data is saved to `outputs/chats/app_data_prepared_[timestamp].csv`

## Getting Started

### Prerequisites

- Python 3.11+
- API keys for the evaluated models (OpenAI, Anthropic, Google, etc.)

### Installation

1. Clone the repository
2. Install dependencies: Ensure `pyproject.toml` and `uv.lock` are present, then run `uv init`
3. Set up API keys as environment variables or in an environment file `.env`

### Running Evaluations

```bash
# Run all model evaluations (Python script)
python scripts/run_model_queries.py

# Alternative: Use the shell script wrapper
./scripts/run_queries.sh

# Process data for the app
python scripts/prep_app_data.py
```

## Data Processing

The `prep_app_data.py` script:
- Combines responses from the main model runs with XAI model responses
- Checks for API errors and missing values
- Creates a consolidated dataset for analysis
- Flags any errors for further investigation

## Contact

For questions or issues, please contact the project maintainers.
