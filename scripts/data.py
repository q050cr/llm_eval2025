"""
Data handling module for LLM Response Evaluator
"""
import os
import glob
import random
import datetime
import json
import pandas as pd
from collections import defaultdict
import streamlit as st

def save_session_state():
    """Save the current session state to a JSON file
    
    This allows the app to restore state between restarts
    """
    # Create dictionary with the data we want to save
    session_data = {
        "current_question_idx": st.session_state.current_question_idx,
        "ratings": st.session_state.ratings,
        "model_mapping": st.session_state.model_mapping,
        "question_order": st.session_state.question_order,
        "evaluation_complete": st.session_state.evaluation_complete,
        "rater_name": st.session_state.rater_name
    }
    
    # Create session directory if it doesn't exist
    os.makedirs("outputs/sessions", exist_ok=True)
    
    # Generate filename based on rater name
    safe_name = st.session_state.rater_name.lower().replace(" ", "_")
    filename = f"outputs/sessions/session_{safe_name}.json"
    
    # Convert defaultdict to dict for JSON serialization
    if isinstance(session_data["ratings"], defaultdict):
        session_data["ratings"] = dict(session_data["ratings"])
    
    # Save to file
    try:
        with open(filename, 'w') as f:
            json.dump(session_data, f)
        return True
    except Exception as e:
        st.error(f"Error saving session: {str(e)}")
        return False

def load_session_state():
    """Load session state from a JSON file if it exists
    
    Returns:
        bool: True if session was loaded successfully, False otherwise
    """
    # Check if we've already loaded a session
    if "session_loaded" in st.session_state and st.session_state.session_loaded:
        return False
        
    # Get rater name (should be set before calling this function)
    if not st.session_state.rater_name:
        return False
        
    # Generate filename based on rater name
    safe_name = st.session_state.rater_name.lower().replace(" ", "_")
    filename = f"outputs/sessions/session_{safe_name}.json"
    
    # Check if file exists
    if not os.path.exists(filename):
        return False
        
    # Load session data
    try:
        with open(filename, 'r') as f:
            session_data = json.load(f)
            
        # Restore session state
        st.session_state.current_question_idx = session_data["current_question_idx"]
        st.session_state.ratings = defaultdict(dict, session_data["ratings"])
        st.session_state.model_mapping = session_data["model_mapping"]
        st.session_state.question_order = session_data["question_order"]
        st.session_state.evaluation_complete = session_data["evaluation_complete"]
        
        # Mark as loaded
        st.session_state.session_loaded = True
        return True
    except Exception as e:
        st.error(f"Error loading session: {str(e)}")
        return False

@st.cache_data
def load_response_data():
    """Load response data from CSV files
    
    Returns:
        DataFrame or None: The loaded data or None if no files found
    """
    csv_files = glob.glob(os.path.join('outputs', 'chats', 'responses_*.csv'))
    
    if not csv_files:
        st.error("No response CSV files found in the outputs/chats directory.")
        return None
    
    # Sort by date (newest first)
    csv_files.sort(reverse=True)
    
    # Use the most recent file by default
    df = pd.read_csv(csv_files[0])
    
    return df

#%% 
def anonymize_models(df):
    """Create anonymous mapping for model names
    
    Args:
        df: DataFrame containing model responses
        
    Returns:
        list: List of model column names in the DataFrame
    """
    model_columns = [col for col in df.columns if col.endswith('_response')]
    models = [col.replace('_response', '') for col in model_columns]
    
    # Create a random mapping if it doesn't exist
    if not st.session_state.model_mapping:
        random_order = list(range(1, len(models) + 1))
        random.shuffle(random_order)
        st.session_state.model_mapping = {model: f"Model {letter}" 
                                          for model, letter in zip(models, random_order)}
    
    return model_columns

def save_ratings():
    """Save the ratings to a CSV file
    
    Returns:
        str or None: The filename of the saved CSV or None if no ratings to save
    """
    ratings_list = []
    
    for question_id, model_ratings in st.session_state.ratings.items():
        # Extract identifiers from the question_id
        parts = question_id.split('_')
        
        # Handle different formats of question_id
        if len(parts) == 4:  
            # Format: "row_index_index_query_id_version" (4 parts)
            row_index = int(parts[0])
            # We'll get actual values from the dataframe
        elif len(parts) == 3:
            # Format: "row_index_query_id_version" (3 parts)
            row_index = int(parts[0])
            # We'll get actual values from the dataframe
        else:
            # Unknown format, skip
            continue
        
        # Get question data using row index
        try:
            question_data = st.session_state.df.iloc[row_index:row_index+1]
            if question_data.empty:
                continue
        except IndexError:
            continue
            
        # Extract question data and ensure we get the correct index and query_id values
        question = question_data['question'].iloc[0]
        category = question_data['category'].iloc[0]
        index_value = question_data['index'].iloc[0]
        query_id_value = question_data['query_id'].iloc[0]
        
        for model, ratings in model_ratings.items():
            if model == "preferred_model" or model == "comfort_level" or model == "preference_reason":
                continue
                
            # Get the original model name from the anonymous name
            real_model = None
            for orig, anon in st.session_state.model_mapping.items():
                if anon == model:
                    real_model = orig
                    break
            
            if not real_model:
                continue
                
            model_response = question_data[f'{real_model}_response'].iloc[0]
            
            # Add all ratings for this model and question
            rating_row = {
                'rater_name': st.session_state.rater_name,
                'index': int(index_value),              # Unique question identifier
                'query_id': int(query_id_value),        # Repetition identifier (1-3)
                'row_index': row_index,                 # Original row index (for debugging)
                'category': category,
                'question': question,
                'model': real_model,
                'response': model_response,
                'date': datetime.datetime.now().strftime("%Y-%m-%d"),
                'time': datetime.datetime.now().strftime("%H:%M:%S"),
            }
            
            # Add each rating criterion
            for criterion, score in ratings.items():
                rating_row[criterion] = score
                
            # Add preferred model info
            preferred_model = st.session_state.ratings[question_id].get('preferred_model', '')
            if preferred_model:
                for orig, anon in st.session_state.model_mapping.items():
                    if anon == preferred_model:
                        rating_row['preferred_model'] = orig
                        break
            
            rating_row['preference_reason'] = st.session_state.ratings[question_id].get('preference_reason', '')
            rating_row['comfort_level'] = st.session_state.ratings[question_id].get('comfort_level', '')
            
            ratings_list.append(rating_row)
    
    # Create DataFrame and save to CSV
    if ratings_list:
        ratings_df = pd.DataFrame(ratings_list)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Add rater name to filename
        safe_name = st.session_state.rater_name.lower().replace(" ", "_")
        
        # Make sure directory exists
        os.makedirs("outputs/evaluation", exist_ok=True)
        
        filename = f"outputs/evaluation/evaluation_results_{safe_name}_{timestamp}.csv"
        
        ratings_df.to_csv(filename, index=False)
        return filename
    
    return None

def get_current_question_data():
    """Get data for the current question
    
    Returns:
        tuple: (question_key, question, category, question_data) or (None, None, None, None) if not found
    """
    if "df" not in st.session_state:
        return None, None, None, None
        
    # Unpack the question order tuple with all identifiers
    current_info = st.session_state.question_order[st.session_state.current_question_idx]
    if len(current_info) == 4:
        # New format: (row_idx, index, query_id, version)
        row_idx, index_val, query_id, version = current_info
    else:
        # Old format: (row_idx, version) - for backward compatibility
        row_idx, version = current_info
    
    # Get the question using the row index
    try:
        question_row = st.session_state.df.iloc[row_idx:row_idx+1]
        if question_row.empty:
            return None, None, None, None
            
        question = question_row['question'].iloc[0]
        category = question_row['category'].iloc[0]
        
        # For the new format, use both index and query_id in the key
        if len(current_info) == 4:
            # Create a unique question key using all identifiers
            question_key = f"{row_idx}_{index_val}_{query_id}_{version}"
        else:
            # Backward compatibility
            query_id = question_row['query_id'].iloc[0]
            question_key = f"{row_idx}_{query_id}_{version}"
        
        return question_key, question, category, question_row
    except IndexError:
        return None, None, None, None

def initialize_question_order(df):
    """Initialize random question order
    
    Args:
        df: DataFrame containing questions
        
    Returns:
        list: List of tuples (row_idx, index, query_id, version)
        where:
        - row_idx: the DataFrame row index
        - index: the 'index' column value (unique question identifier)
        - query_id: the 'query_id' column value (repetition identifier 1-3)
        - version: always 1 (for tracking different versions of the same question)
    """
    # Create a list of tuples with (row_idx, index, query_id, version)
    # This ensures we track both the actual row index and the index/query_id columns
    question_order = []
    for row_idx, row in df.iterrows():
        question_order.append((
            row_idx,              # DataFrame row index
            int(row['index']),    # Question unique identifier
            int(row['query_id']), # Repetition identifier (1-3)
            1                     # Version (always 1)
        ))
    
    # Shuffle the order
    random.shuffle(question_order)
    return question_order

def initialize_session_state():
    """Initialize session state variables if they don't exist"""
    if "current_question_idx" not in st.session_state:
        st.session_state.current_question_idx = 0

    if "ratings" not in st.session_state:
        st.session_state.ratings = defaultdict(dict)

    if "model_mapping" not in st.session_state:
        st.session_state.model_mapping = {}

    if "question_order" not in st.session_state:
        st.session_state.question_order = []

    if "evaluation_complete" not in st.session_state:
        st.session_state.evaluation_complete = False

    if "rater_name" not in st.session_state:
        st.session_state.rater_name = ""
