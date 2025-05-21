## Basic usage (runs all questions once with all models)

./scripts/run_queries.sh

## Script Usage

The script accepts the following command-line options:

- `-m, --models MODELS`: Comma-separated list of models to query (e.g., "openai,google"). Default is defined in the `$MODELS` environment variable.
- `-n, --n_rows N`: Number of questions to process. Useful for testing. If not specified, all available questions will be processed.
- `-r, --repeat N`: Number of times to repeat each question. Default is defined in the `$REPEAT` environment variable.
- `-f, --file FILE`: Path to the CSV file containing questions. Default is defined in the `$QUESTIONS_FILE` environment variable.
- `-c, --close-tunnel`: Close the VSCode tunnel connection after completion of all queries.
- `--no-log`: Don't save output to a log file. Output will be directed to the console only.
- `-h, --help`: Display the help message and exit.

### Default params:

- **Models:** All available (openai,anthropic,google,deepseek,perplexity,github,xai)
- **Questions:** All in the default CSV file *./data/questions/FAQ_HF_CMP_Patient_20250519.csv*
- **Repeat:** 1 (each question is asked once)
- **Log:** Output is saved to a log file
- **VSCode tunnel:** Remains open after completion


## Run with specific models

./scripts/run_queries.sh --models openai,google,anthropic

## Test with just a few questions

./scripts/run_queries.sh --n_rows 5

## Repeat each question multiple times for statistical analysis

./scripts/run_queries.sh --repeat 3

## Close the VSCode tunnel connection after completion

./scripts/run_queries.sh --close-tunnel

## Combine options

./scripts/run_queries.sh --models openai,google --n_rows 5 --repeat 2 --file ./data/sample_questions.csv
