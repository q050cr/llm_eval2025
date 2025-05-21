#!/bin/bash

# Script to run the model query script and handle remote connection cleanup
# Author: Christoph Reich
# Date: May 21, 2025

# Default values ------------------------------------------------------------------------
MODELS="openai,anthropic,google,deepseek,perplexity,github"
N_ROWS=""
REPEAT=1
CLOSE_TUNNEL=false

# Print usage information invoked by --help   -------------------------------------------
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Run model queries and optionally close VSCode remote tunnel connection when finished."
    echo
    echo "Options:"
    echo "  -m, --models MODELS     Comma-separated list of models to query (default: $MODELS)"
    echo "  -n, --n_rows N          Number of questions to process (for testing, default: all)"
    echo "  -r, --repeat N          Number of times to repeat each question (default: $REPEAT)"
    echo "  -c, --close-tunnel      Close VSCode tunnel connection after completion"
    echo "  -h, --help              Display this help message and exit"
    echo
    echo "Example:"
    echo "  $0 -m openai,google -n 5 -r 3 -c"
    echo "  This will query 5 questions 3 times each using OpenAI and Google models,"
    echo "  then close the VSCode tunnel connection when finished."
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
        -c|--close-tunnel)
            CLOSE_TUNNEL=true
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
echo "Close tunnel after completion: $CLOSE_TUNNEL"
echo "============================================="

# Initialize command
CMD="python scripts/run_model_queries.py --models $MODELS --repeat $REPEAT"

# Add n_rows if specified
if [ -n "$N_ROWS" ]; then
    CMD="$CMD --n_rows $N_ROWS"
fi

# Run the command
echo "Executing: $CMD"
echo "Started at: $(date)"
start_time=$(date +%s)

# Run the command
eval "$CMD"
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
