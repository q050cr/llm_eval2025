#!/usr/bin/env python3
"""
This script allows querying multiple language models in parallel with configurable 
repetition for statistical analysis. It supports various models including OpenAI, 
Google, Anthropic, DeepSeek, Perplexity, GitHub Copilot, X.AI, and local Ollama models.
    python run_model_queries.py [--models MODEL1,MODEL2,...] [--n_rows N] [--repeat N] [--questions_file PATH]
Arguments:
    --models: Comma-separated list of models to query (default: openai,anthropic,google,deepseek,perplexity,github)
    --n_rows: Number of questions to process for testing (default: all questions)
    --repeat: Number of times to repeat each question for statistical analysis (default: 1)
    --questions_file: Path to CSV file with questions (default: ./data/questions/FAQ_HF_CMP_Patient_20250519.csv)
Environment Variables:
    The script requires API keys to be set as environment variables in a .env file:
    - OPENAI_API_KEY: For OpenAI models (gpt-4o)
    - DEEPSEEK_API_KEY: For DeepSeek models
    - GOOGLE_API_KEY: For Google models (gemini)
    - ANTHROPIC_API_KEY: For Anthropic models (claude)
    - PERPLEXITY_API_KEY: For Perplexity models
    - GITHUB_PAT: For GitHub Copilot models
    - XAI_API_KEY: For X.AI/Grok models
Input:
    - CSV file with questions (must contain columns: index, category, question, select)
    - Only rows where select='yes' will be processed
Output:
    Files are saved to ./outputs/chats/ directory:
    - responses_TIMESTAMP.csv: DataFrame with all model responses
    - raw_responses_TIMESTAMP.pkl: Pickle file with detailed response data
    - raw_responses_TIMESTAMP.json: JSON backup if pickle fails
Notes:
    - The script implements rate limiting for certain APIs (Anthropic, GitHub)
    - Includes error handling and retry logic for API failures
    - Questions can be repeated multiple times for statistical analysis

Script for parallel querying of LLMs for clinical decision support evaluation.
Based on chatlas_query.ipynb notebook.

Usage:
    python run_model_queries.py [--models MODEL1,MODEL2,...] [--n_rows N] [--repeat N]
"""

import pdb
import os
import argparse
import anthropic
import pandas as pd
import pickle
import time
import threading
import sys
from dotenv import load_dotenv
from chatlas import ChatGoogle, ChatAnthropic, ChatOllama, ChatGithub
from tqdm import tqdm
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from tenacity import retry, wait_exponential, stop_after_attempt
from collections import defaultdict

# Load environment variables from .env file
load_dotenv()

# Import custom classes
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.utils import ChatPerplexityDirect, DeepseekChat, OpenAIChat, XAIChat


# Force GitHub model calls to run one at a time
github_lock = threading.Lock()
anthropic_lock = threading.Lock()


def initialize_model(model_name):
    """
    Helper function to initialize a model based on the name and environment variable.
    Returns a model instance or raises an informative error.
    """
    system_prompt = ""  # simulating raw user access

    if model_name == 'openai':
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise EnvironmentError("Missing OPENAI_API_KEY")
        # https://platform.openai.com/docs/models, custom OpenAI class
        return OpenAIChat(model="gpt-4o-2024-11-20", system_prompt=system_prompt, api_key=api_key)

    elif model_name == 'deepseek':
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            raise EnvironmentError("Missing DEEPSEEK_API_KEY")
        # Use custom DeepseekChat class with OpenAI client
        return DeepseekChat(model="deepseek-chat", system_prompt=system_prompt, api_key=api_key)

    elif model_name == 'google':
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise EnvironmentError("Missing GOOGLE_API_KEY")
        # https://aistudio.google.com/
        return ChatGoogle(model="gemini-2.5-pro-preview-05-06", system_prompt=system_prompt, api_key=api_key)

    elif model_name == 'anthropic':
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise EnvironmentError("Missing ANTHROPIC_API_KEY")
        # https://aistudio.google.com/
        return ChatAnthropic(model="claude-3-7-sonnet-20250219", system_prompt=system_prompt, api_key=api_key)

    elif model_name == 'perplexity':
        api_key = os.getenv('PERPLEXITY_API_KEY')
        if not api_key:
            raise EnvironmentError("Missing PERPLEXITY_API_KEY")
        # ["sonar", "sonar-pro", "r1-1776"], https://docs.perplexity.ai/models/model-cards
        # Use custom Perplexity Class
        return ChatPerplexityDirect(api_key=api_key, model="sonar-pro", system_prompt=system_prompt)

    elif model_name == 'github':
        api_key = os.getenv('GITHUB_PAT')
        if not api_key:
            raise EnvironmentError("Missing GITHUB_PAT")
        # https://aistudio.google.com/
        return ChatGithub(model="grok-3", system_prompt=system_prompt, api_key=api_key)

    elif model_name == 'xai':
        api_key = os.getenv('XAI_API_KEY')
        if not api_key:
            raise EnvironmentError("Missing XAI_API_KEY")
        # Use custom XAIChat class with X.AI's API
        return XAIChat(model="grok-3", system_prompt=system_prompt, api_key=api_key)

    elif model_name == 'ollama':
        # ollama list
        return ChatOllama(model="deepseek-r1:14b", system_prompt=system_prompt)

    else:
        raise ValueError(f"Unsupported model: {model_name}")


@retry(wait=wait_exponential(min=2, max=60), stop=stop_after_attempt(5))
def call_model_with_retry(instance, question):
    return instance.chat(question, echo="none")


def query_single_model(question, model_key, instance):
    try:
        if not instance:
            return model_key, "Initialization failed", None

        # Serialize GitHub requests
        if model_key == "github":
            with github_lock:
                response = call_model_with_retry(instance, question)
        
        elif model_key == "anthropic":
            with anthropic_lock:
                # Add a small delay between Anthropic requests to prevent rate limiting
                time.sleep(1.2)  # ~50 requests per minute = ~1.2 seconds per request
                response = call_model_with_retry(instance, question)
        
        else:
            response = call_model_with_retry(instance, question)

        return model_key, response.content, response

    except Exception as e:
        return model_key, f"Error: {str(e)}", None


def query_models_parallel(questions_df, models_to_run, store_full_response=True):
    """
    Query selected models in parallel and return a DataFrame with responses.

    Args:
        questions_df (pd.DataFrame): Must have 'index', 'category', 'question'. Optional: 'query_id'.
        models_to_run (list): Models to query. Options: 'openai', 'google', 'perplexity', 'github', 'ollama'.
        store_full_response (bool): If True, store a serializable version of response data, not just content.

    Returns:
        pd.DataFrame: Responses from each model for each question.
        dict: Raw response data in a serializable format (if store_full_response=True)
    """
    responses_dict = defaultdict(dict)
    raw_responses = {} if store_full_response else None

    # Initialize models
    model_instances = {}
    for model in models_to_run:
        try:
            model_instances[model] = initialize_model(model)
            print(f"Initialized model: {model}")
        except Exception as e:
            print(f"[Warning] Failed to initialize {model}: {e}")
            model_instances[model] = None

    futures = []

    with ThreadPoolExecutor(max_workers=6) as executor:
        for _, row in questions_df.iterrows():
            question = row['question']
            query_id = row.get('query_id', 0)
            idx = row['index']

            # Unique key for each question and query_id
            entry_key = (idx, query_id)

            # Initialize the entry only once per unique (index, query_id)
            if 'meta_initialized' not in responses_dict[entry_key]:
                responses_dict[entry_key].update({
                    'index': idx,
                    'question': question,
                    'category': row['category'],
                    'subcategory1': row['subcategory1'],
                    'subcategory2': row['subcategory2'],
                    'query_id': query_id,
                    'meta_initialized': True  # prevents duplicate updates
                })

            if store_full_response:
                raw_responses.setdefault(idx, {}).setdefault(query_id, {})

            for model_key in models_to_run:
                instance = model_instances.get(model_key)
                futures.append((
                    executor.submit(query_single_model,
                                    question, model_key, instance),
                    entry_key, model_key, idx, query_id
                ))

        for future, entry_key, model_key, idx, query_id in tqdm(futures, desc="Parallel querying"):
            model, content, full_response = future.result()

            # Add model response to correct row
            responses_dict[entry_key][f"{model_key}_response"] = content

            if store_full_response and full_response:
                # Store serializable data instead of full response object (not pickleable)
                response_data = {
                    'content': full_response.content if hasattr(full_response, 'content') else None,
                    'model': getattr(full_response, 'model', model_key),
                    'created_at': getattr(full_response, 'created_at', datetime.now().isoformat())
                }
                
                # Extract usage statistics if available (for OpenAI, etc.)
                if hasattr(full_response, 'raw_response') and hasattr(full_response.raw_response, 'usage'):
                    usage = full_response.raw_response.usage
                    if usage:
                        response_data['usage'] = {
                            'prompt_tokens': getattr(usage, 'prompt_tokens', None),
                            'completion_tokens': getattr(usage, 'completion_tokens', None),
                            'total_tokens': getattr(usage, 'total_tokens', None)
                        }
                
                # Store the serializable dictionary
                raw_responses[idx][query_id][model_key] = response_data

    # Remove the helper key and turn into DataFrame
    for entry in responses_dict.values():
        entry.pop('meta_initialized', None)

    result_df = pd.DataFrame(responses_dict.values())
    return (result_df, raw_responses) if store_full_response else result_df


def prepare_repeated_questions(questions_df, n_repeats):
    """
    Prepare a dataframe with repeated questions for statistical analysis.
    
    Args:
        questions_df (pd.DataFrame): Original questions dataframe
        n_repeats (int): Number of times to repeat each question
        
    Returns:
        pd.DataFrame: Dataframe with repeated questions and query_id
    """
    if n_repeats <= 1:
        return questions_df
        
    # Repeat each question n_queries times
    questions_df_rep = questions_df.loc[questions_df.index.repeat(
        n_repeats)].reset_index(drop=True)

    # Add query_id column to differentiate between repetitions
    questions_df_rep['query_id'] = questions_df_rep.groupby('index').cumcount() + 1

    # Reorder columns to place 'query_id' after 'index'
    cols = questions_df_rep.columns.tolist()
    cols.insert(1, cols.pop(cols.index('query_id')))
    questions_df_rep = questions_df_rep[cols]
    
    return questions_df_rep


def main():
    parser = argparse.ArgumentParser(description="Run LLM Evaluation for Clinical Questions")
    parser.add_argument("--models", type=str, default="openai,anthropic,google,deepseek,perplexity,github",
                      help="Comma-separated list of models to query")
    parser.add_argument("--n_rows", type=int, default=None,
                      help="Number of questions to process (for testing). If not specified, all questions are used.")
    parser.add_argument("--repeat", type=int, default=1,
                      help="Number of times to repeat each question for statistical analysis")
    parser.add_argument("--questions_file", type=str, default="./data/questions/FAQ_HF_CMP_Patient_20250519.csv",
                      help="Path to CSV file with questions (default: ./data/questions/FAQ_HF_CMP_Patient_20250519.csv)")
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Parse models to run
    models_to_run = [model.strip() for model in args.models.split(',')]
    print(f"Running with models: {models_to_run}")

    # Load questions
    questions_file = args.questions_file
    print(f"Loading questions from: {questions_file}")
    questions_df = pd.read_csv(questions_file)
    questions_df = questions_df[questions_df['select'] == 'yes']
    
    # Limit number of questions if specified
    if args.n_rows:
        questions_df = questions_df.iloc[:args.n_rows]
        
    # Prepare repeated questions if needed
    if args.repeat > 1:
        questions_df = prepare_repeated_questions(questions_df, args.repeat)
        print(f"Prepared {len(questions_df)} questions with {args.repeat} repetitions each")
    else:
        print(f"Loaded {len(questions_df)} questions")
    
    # Run queries
    start_time = time.time()
    
    responses_df, raw_responses = query_models_parallel(
        questions_df=questions_df,
        models_to_run=models_to_run,
        store_full_response=True
    )
    
    execution_time = time.time() - start_time
    execution_minutes = execution_time / 60
    execution_hours = execution_minutes / 60

    # Print execution time
    if execution_hours >= 1:
        print(
            f"Query execution completed in {execution_time:.2f} seconds ({execution_minutes:.2f} minutes, {execution_hours:.2f} hours)")
    else:
        print(
            f"Query execution completed in {execution_time:.2f} seconds ({execution_minutes:.2f} minutes)")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Make sure output directory exists
    os.makedirs("./outputs/chats", exist_ok=True)
    
    # Save raw responses to pickle file
    try:
        with open(f"./outputs/chats/raw_responses_{timestamp}.pkl", "wb") as f:
            pickle.dump(raw_responses, f)
        print(f"Raw responses saved to ./outputs/chats/raw_responses_{timestamp}.pkl")
    except Exception as e:
        print(f"Warning: Failed to pickle raw responses: {e}")
        
        # Save as JSON instead
        try:
            import json
            with open(f"./outputs/chats/raw_responses_{timestamp}.json", "w") as f:
                json.dump(raw_responses, f, default=str)
            print(f"Raw responses saved as JSON instead to ./outputs/chats/raw_responses_{timestamp}.json")
        except Exception as json_error:
            print(f"Error: Could not save raw responses as JSON either: {json_error}")
            print("Raw response data was not saved.")

    # Save processed responses to CSV
    output_file = f"./outputs/chats/responses_{timestamp}.csv"
    responses_df.to_csv(output_file, index=False)
    print(f"Responses saved to {output_file}")


if __name__ == "__main__":
    main()
