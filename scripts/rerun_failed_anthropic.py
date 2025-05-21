#!/usr/bin/env python3
"""
Script to extract failed Anthropic queries from a previous results CSV,
re-run them using the existing run_model_queries.py script, and then
merge the new results back into the original CSV.

Usage:
    1) Use script directly:
    python rerun_failed_anthropic.py --input path/to/responses.csv [--output path/to/output.csv]
    2) For other models, you can specify the model name:
    python scripts/rerun_failed_anthropic.py --input ./outputs/chats/your_responses_file.csv --model openai
    3) You can also specify a custom output path:
    python scripts/rerun_failed_anthropic.py --input ./outputs/chats/your_responses_file.csv --output ./outputs/chats/final_results.csv
"""

import pdb
import os
import argparse
import pandas as pd
import subprocess
import time
from datetime import datetime

def extract_failed_queries(input_csv, model="anthropic"):
    """
    Extract rows with failed queries for the specified model and create a new CSV.
    
    Args:
        input_csv (str): Path to the input CSV file
        model (str): Model name to check for errors (default: 'anthropic')
        
    Returns:
        tuple: (Path to the filtered CSV, DataFrame with failed queries)
    """
    print(f"Reading input CSV: {input_csv}")
    df = pd.read_csv(input_csv)
    
    # Create the column name based on the model name
    response_column = f"{model}_response"
    
    # Check if the column exists
    if response_column not in df.columns:
        raise ValueError(f"Column '{response_column}' not found in CSV file.")
    
    # Find rows where the response contains error indicators
    error_mask = df[response_column].astype(str).str.contains(
        'Error|RateLimitError|APIStatusError|RetryError', 
        case=False, na=False)
    
    # Get only the rows with errors
    failed_df = df[error_mask].copy()
    
    # Get the original questions
    questions_df = failed_df[['index', 'question', 'category', 'subcategory1', 'subcategory2', 'query_id']]
    
    # Create a 'select' column which is needed by run_model_queries.py
    questions_df['select'] = 'yes'
    
    # Create a temporary CSV file for the questions
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_csv = f"./data/questions/temp_failed_{model}_{timestamp}.csv"
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(temp_csv), exist_ok=True)
    
    # Save the filtered questions to a CSV file
    questions_df.to_csv(temp_csv, index=False)
    
    print(f"Extracted {len(questions_df)} failed queries for model '{model}'")
    print(f"Saved to temporary file: {temp_csv}")
    
    return temp_csv, failed_df

def run_model_queries(questions_csv, model="anthropic"):
    """
    Run the model_queries.py script with the specified model.
    
    Args:
        questions_csv (str): Path to the CSV file with questions
        model (str): Model to query (default: 'anthropic')
        
    Returns:
        str: Path to the results CSV file
    """
    # Check that the file exists
    if not os.path.exists(questions_csv):
        raise FileNotFoundError(f"Questions CSV file not found: {questions_csv}")
    
    # Create a command to run the script
    cmd = [
        "python", 
        "scripts/run_model_queries.py",
        f"--models={model}",
        f"--questions_file={questions_csv}",  # Pass the temporary file path
        # Add additional parameters as needed
    ]

    print(f"Running command: {' '.join(cmd)}")
    
    # Run the command
    start_time = time.time()
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()
    
    # Print the output
    if stdout:
        print("Output:")
        print(stdout)
    
    # Print any errors
    if stderr:
        print("Errors:")
        print(stderr)
    
    execution_time = time.time() - start_time
    print(f"Query execution completed in {execution_time:.2f} seconds")
    
    # Check the exit code
    if process.returncode != 0:
        raise RuntimeError(f"Error running model queries script. Exit code: {process.returncode}")
    
    # Find the latest results CSV file
    outputs_dir = "./outputs/chats"
    csv_files = [f for f in os.listdir(outputs_dir) if f.startswith("responses_") and f.endswith(".csv")]
    csv_files.sort(reverse=True)  # Sort in descending order to get the most recent file
    
    if not csv_files:
        raise FileNotFoundError("No results CSV files found in the outputs directory.")
    
    latest_csv = os.path.join(outputs_dir, csv_files[0])
    print(f"Found latest results CSV: {latest_csv}")
    
    return latest_csv

def merge_results(original_csv, new_results_csv, model="anthropic", output_csv=None):
    """
    Merge the new results back into the original CSV file.
    
    Args:
        original_csv (str): Path to the original CSV file
        new_results_csv (str): Path to the new results CSV file
        model (str): Model name (default: 'anthropic')
        output_csv (str, optional): Path to save the merged CSV file
        
    Returns:
        str: Path to the merged CSV file
    """
    # Read the original and new results CSV files
    original_df = pd.read_csv(original_csv)
    new_results_df = pd.read_csv(new_results_csv)
    
    # Create the column name based on the model name
    response_column = f"{model}_response"
    
    # Check if the column exists
    if response_column not in original_df.columns or response_column not in new_results_df.columns:
        raise ValueError(f"Column '{response_column}' not found in one of the CSV files.")
    
    # Merge the results
    merged_df = original_df.copy()
    
    # Update the responses for the rows that were updated
    for _, row in new_results_df.iterrows():
        idx = row['index']
        query_id = row.get('query_id', 0)
        
        # Find the matching row in the original DataFrame
        mask = (merged_df['index'] == idx) & (merged_df['query_id'] == query_id)
        
        # Update the response
        merged_df.loc[mask, response_column] = row[response_column]
    
    # Generate the output path if not provided
    if output_csv is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.dirname(original_csv)
        filename = os.path.basename(original_csv)
        base_name, ext = os.path.splitext(filename)
        output_csv = os.path.join(output_dir, f"{base_name}_fixed_{timestamp}{ext}")
    
    # Save the merged DataFrame
    merged_df.to_csv(output_csv, index=False)
    print(f"Merged results saved to: {output_csv}")
    
    return output_csv

def main():
    parser = argparse.ArgumentParser(description="Re-run failed Anthropic queries and merge results")
    parser.add_argument("--input", required=True, help="Path to the input CSV file with API responses")
    parser.add_argument("--output", help="Path to save the merged CSV file (optional)")
    parser.add_argument("--model", default="anthropic", help="Model to retry (default: anthropic)")
    args = parser.parse_args()
    
    try:
        # 1. Extract failed queries
        questions_csv, _ = extract_failed_queries(args.input, args.model)
        
        # 2. Run the model queries script
        results_csv = run_model_queries(questions_csv, args.model)

        # 3. Merge the results
        output_csv = merge_results(args.input, results_csv, args.model, args.output)
        
        print(f"\nSuccess! Fixed results saved to: {output_csv}")
        
        # 4. Cleanup temporary files
        if os.path.exists(questions_csv):
            os.remove(questions_csv)
            print(f"Cleaned up temporary file: {questions_csv}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
