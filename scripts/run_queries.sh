#!/bin/bash

# Script to run the model query script and handle remote connection cleanup
# Author: Christoph Reich
# Date: May 21, 2025

# Default values ------------------------------------------------------------------------
MODELS="openai,anthropic,google,deepseek,perplexity,github,xai"
N_ROWS=""
REPEAT=1
QUESTIONS_FILE="./data/questions/FAQ_HF_CMP_Patient_20250519.csv"
CLOSE_TUNNEL=false
LOG_OUTPUT=true

# Print usage information invoked by --help   -------------------------------------------
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Run model queries and optionally close VSCode remote tunnel connection when finished."
    echo
    echo "Options:"
    echo "  -m, --models MODELS     Comma-separated list of models to query (default: $MODELS)"
    echo "  -n, --n_rows N          Number of questions to process (for testing, default: all)"
    echo "  -r, --repeat N          Number of times to repeat each question (default: $REPEAT)"
    echo "  -f, --file FILE         Path to CSV file with questions (default: $QUESTIONS_FILE)"
    echo "  -c, --close-tunnel      Close VSCode tunnel connection after completion"
    echo "  --no-log                Don't save output to log file (output to console only)"
    echo "  -h, --help              Display this help message and exit"
    echo
    echo "Example:"
    echo "  $0 -m openai,google -n 5 -r 3 -f ./data/sample_questions.csv -c"
    echo "  This will query 5 questions 3 times each using OpenAI and Google models,"
    echo "  loading questions from the specified file, then close the VSCode tunnel connection."
}

# Parse command-line options ----------------------------------------------------------
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -m|--models)
            MODELS="$2"
            shift 2
            ;;
        -n|--n_rows)
            N_ROWS="$2"
            shift 2
            ;;
        -r|--repeat)
            REPEAT="$2"
            shift 2
            ;;
        -f|--file)
            QUESTIONS_FILE="$2"
            shift 2
            ;;
        -c|--close-tunnel)
            CLOSE_TUNNEL=true
            shift
            ;;
        --no-log)
            LOG_OUTPUT=false
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Ensure we're in the project root directory
cd "$(dirname "$0")/.." || { echo "Error: Could not change to project root directory"; exit 1; }

# Setup logging if enabled
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE=""

if [ "$LOG_OUTPUT" = true ]; then
    # Create logs directory if it doesn't exist
    mkdir -p ./logs
    LOG_FILE="./logs/query_run_${TIMESTAMP}.log"
    echo "Logging output to: $LOG_FILE"
    echo "To monitor progress: tail -f $LOG_FILE"
fi

echo "============================================="
echo "Starting Model Query Execution"
echo "============================================="
echo "Models: $MODELS"
if [ -n "$N_ROWS" ]; then
    echo "Number of rows: $N_ROWS"
else
    echo "Processing all questions"
fi
echo "Repeat: $REPEAT"
echo "Questions file: $QUESTIONS_FILE"
echo "Close tunnel after completion: $CLOSE_TUNNEL"
echo "============================================="

# Initialize command
CMD="python scripts/run_model_queries.py --models $MODELS --repeat $REPEAT --questions_file $QUESTIONS_FILE"

# Add n_rows if specified
if [ -n "$N_ROWS" ]; then
    CMD="$CMD --n_rows $N_ROWS"
fi

# Run the command
echo "Executing: $CMD"
echo "Started at: $(date)"
start_time=$(date +%s)

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate || { echo "Error: Could not activate virtual environment"; exit 1; }
fi

# Run the command with or without logging
if [ "$LOG_OUTPUT" = true ] && [ -n "$LOG_FILE" ]; then
    echo "Redirecting output to log file: $LOG_FILE"
    eval "$CMD" > "$LOG_FILE" 2>&1
else
    eval "$CMD"
fi
exit_status=$?

end_time=$(date +%s)
duration=$((end_time - start_time))
hours=$((duration / 3600))
minutes=$(( (duration % 3600) / 60 ))
seconds=$((duration % 60))

echo "============================================="
echo "Execution completed with status: $exit_status"
echo "Duration: ${hours}h ${minutes}m ${seconds}s"
echo "Finished at: $(date)"
echo "============================================="

# Close VSCode tunnel if requested
if [ "$CLOSE_TUNNEL" = true ]; then
    echo "Attempting to close VSCode tunnel connection..."
    
    # Check if code CLI is available
    if command -v code &> /dev/null; then
        echo "Closing VSCode tunnel..."
        code tunnel close
        echo "VSCode tunnel closed."
    else
        echo "VSCode CLI not found. Unable to close tunnel automatically."
        echo "To close the tunnel manually, run: code tunnel close"
    fi
fi

exit $exit_status
