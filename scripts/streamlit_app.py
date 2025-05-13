"""
LLM Response Evaluator - Main Application

A Streamlit application for evaluating and comparing LLM responses 
to medical and scientific questions.
"""
import streamlit as st
import pandas as pd
import glob
import os
import random
import datetime
from collections import defaultdict

# Set page configuration
st.set_page_config(
    page_title="LLM Response Evaluator",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Define CSS styles
st.markdown("""
<style>
    .model-response {
        background-color: #f0f2f6;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
    }
    .question-box {
        background-color: #e6f3ff;
        border-left: 4px solid #0068c9;
        padding: 15px;
        border-radius: 4px;
        margin-bottom: 20px;
    }
    .category-tag {
        background-color: #0068c9;
        color: white;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.8em;
        margin-right: 10px;
    }
    .rating-section {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 20px;
    }
    .selected-model {
        border: 2px solid #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

# Create session state variables if they don't exist
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

# Define rating criteria
RATING_CRITERIA = {
    "Appropriateness": "How well the answer addresses the specific question asked",
    "Comprehensibility": "How easy the answer is to understand",
    "Completeness": "How thoroughly the answer addresses all aspects of the question",
    "Redundancy": "Whether the answer contains unnecessary repetition (lower is better)",
    "Confabulation": "Whether the answer contains made-up information (lower is better)",
    "Readability": "How well-structured and clear the answer is",
    "Educational Value": "How informative and educational the answer is",
    "Clinical Value": "How useful the answer is for clinical decision support, risk communication, or actionability",
    "Tone/Empathy": "How appropriate the tone is and how much empathy it conveys"
}

# Function to load all response data
@st.cache_data
def load_response_data():
    csv_files = glob.glob(os.path.join('outputs', 'responses_*.csv'))
    
    if not csv_files:
        st.error("No response CSV files found in the outputs directory.")
        return None
    
    # Sort by date (newest first)
    csv_files.sort(reverse=True)
    
    # Use the most recent file by default
    df = pd.read_csv(csv_files[0])
    
    return df

# Function to anonymize models and create a mapping
def anonymize_models(df):
    model_columns = [col for col in df.columns if col.endswith('_response')]
    models = [col.replace('_response', '') for col in model_columns]
    
    # Create a random mapping if it doesn't exist
    if not st.session_state.model_mapping:
        random_order = list(range(1, len(models) + 1))
        random.shuffle(random_order)
        st.session_state.model_mapping = {model: f"Model {letter}" 
                                          for model, letter in zip(models, random_order)}
    
    return model_columns

# Function to save ratings to CSV
def save_ratings():
    ratings_list = []
    
    for question_id, model_ratings in st.session_state.ratings.items():
        question_data = st.session_state.df[st.session_state.df['query_id'] == int(question_id.split('_')[0])]
        if question_data.empty:
            continue
            
        question = question_data['question'].iloc[0]
        category = question_data['category'].iloc[0]
        
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
                'question_id': question_id.split('_')[0],
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
        filename = f"outputs/evaluation_results_{timestamp}.csv"
        ratings_df.to_csv(filename, index=False)
        return filename
    
    return None

# Function to navigate to next/previous question
def navigate_question(direction):
    if direction == "next":
        if st.session_state.current_question_idx < len(st.session_state.question_order) - 1:
            st.session_state.current_question_idx += 1
        else:
            st.session_state.evaluation_complete = True
    else:  # previous
        if st.session_state.current_question_idx > 0:
            st.session_state.current_question_idx -= 1

# Main app
def main():
    st.title("🧠 LLM Response Evaluator")
    
    # Sidebar
    with st.sidebar:
        st.header("Navigation")
        
        if "df" not in st.session_state:
            st.session_state.df = load_response_data()
            
            # Exit if no data is loaded
            if st.session_state.df is None:
                st.error("Failed to load data. Please check the file path.")
                return
                
            # Create question order if it doesn't exist
            if not st.session_state.question_order:
                question_ids = st.session_state.df['query_id'].unique()
                st.session_state.question_order = [(q_id, 1) for q_id in question_ids]
                random.shuffle(st.session_state.question_order)
            
            # Anonymize models
            anonymize_models(st.session_state.df)
        
        # Get rater name
        if not st.session_state.rater_name:
            st.session_state.rater_name = st.text_input("Enter your name:", key="rater_input")
            if not st.session_state.rater_name:
                st.warning("Please enter your name to begin rating")
                return
        else:
            st.write(f"Rater: {st.session_state.rater_name}")
        
        # Show progress
        progress = (st.session_state.current_question_idx + 1) / len(st.session_state.question_order)
        st.progress(progress)
        st.write(f"Question {st.session_state.current_question_idx + 1} of {len(st.session_state.question_order)}")
        
        # Navigation buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Previous", disabled=st.session_state.current_question_idx == 0):
                navigate_question("previous")
                
        with col2:
            if st.button("Next ➡️", disabled=st.session_state.current_question_idx == len(st.session_state.question_order) - 1):
                navigate_question("next")
        
        st.divider()
        
        # Save ratings button
        if st.button("💾 Save All Ratings"):
            filename = save_ratings()
            if filename:
                st.success(f"Ratings saved to {filename}")
            else:
                st.error("No ratings to save")
    
    # Skip if evaluation is complete
    if st.session_state.evaluation_complete:
        st.header("🎉 Evaluation Complete!")
        st.write("Thank you for completing the evaluation! Your ratings have been recorded.")
        if st.button("Start Over"):
            st.session_state.clear()
            st.rerun()
        return
    
    # Skip if no name entered
    if not st.session_state.rater_name:
        return
        
    # Get current question
    current_q_id, current_version = st.session_state.question_order[st.session_state.current_question_idx]
    question_data = st.session_state.df[st.session_state.df['query_id'] == current_q_id]
    
    if question_data.empty:
        st.error(f"No data found for question ID {current_q_id}")
        return
        
    # Display question
    question = question_data['question'].iloc[0]
    category = question_data['category'].iloc[0]
    
    # Create a unique key for the question considering versions
    question_key = f"{current_q_id}_{current_version}"
    
    st.markdown(f"<span class='category-tag'>{category}</span>", unsafe_allow_html=True)
    st.markdown(f"<div class='question-box'><h3>{question}</h3></div>", unsafe_allow_html=True)
    
    # Get model columns and create tabs for each model
    model_columns = [col for col in question_data.columns if col.endswith('_response')]
    
    # Shuffle the order of model responses
    model_order = list(range(len(model_columns)))
    
    # Only shuffle if this is the first time seeing this question
    if question_key not in st.session_state.ratings:
        random.shuffle(model_order)
    
    # Create tabs for each rating section
    tab1, tab2 = st.tabs(["Rate Individual Responses", "Compare & Select Best Response"])
    
    with tab1:
        # Setup for ratings
        for i, idx in enumerate(model_order):
            if idx >= len(model_columns):
                continue
                
            col = model_columns[idx]
            model_name = col.replace('_response', '')
            anonymous_name = st.session_state.model_mapping[model_name]
            
            with st.expander(f"{anonymous_name}", expanded=True):
                st.markdown(f"<div class='model-response'>{question_data[col].iloc[0]}</div>", unsafe_allow_html=True)
                
                # Initialize ratings for this model if they don't exist
                if question_key not in st.session_state.ratings:
                    st.session_state.ratings[question_key] = {}
                if anonymous_name not in st.session_state.ratings[question_key]:
                    st.session_state.ratings[question_key][anonymous_name] = {}
                
                # Create rating sliders
                st.markdown("<div class='rating-section'>", unsafe_allow_html=True)
                for criterion, description in RATING_CRITERIA.items():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{criterion}** - *{description}*")
                    with col2:
                        current_rating = st.session_state.ratings[question_key][anonymous_name].get(criterion, 3)
                        rating = st.select_slider(
                            f"Rate {criterion}",
                            options=[1, 2, 3, 4, 5],
                            value=current_rating,
                            key=f"{question_key}_{anonymous_name}_{criterion}",
                            label_visibility="collapsed"
                        )
                        st.session_state.ratings[question_key][anonymous_name][criterion] = rating
                st.markdown("</div>", unsafe_allow_html=True)
    
    with tab2:
        st.subheader("Select the Most Helpful Response")
        
        # Display all responses side by side
        columns = st.columns(min(len(model_columns), 3))
        idx = 0
        
        for col_idx, model_idx in enumerate(model_order):
            if model_idx >= len(model_columns):
                continue
                
            col = model_columns[model_idx]
            model_name = col.replace('_response', '')
            anonymous_name = st.session_state.model_mapping[model_name]
            
            with columns[idx % len(columns)]:
                # Check if this is the preferred model
                is_preferred = st.session_state.ratings[question_key].get('preferred_model', '') == anonymous_name
                container_class = 'model-response selected-model' if is_preferred else 'model-response'
                
                st.markdown(f"<h4>{anonymous_name}</h4>", unsafe_allow_html=True)
                st.markdown(f"<div class='{container_class}'>{question_data[col].iloc[0]}</div>", unsafe_allow_html=True)
                
                if st.button(f"Select {anonymous_name} as Best", key=f"best_{question_key}_{anonymous_name}"):
                    st.session_state.ratings[question_key]['preferred_model'] = anonymous_name
                    st.rerun()
            
            idx += 1
        
        # Additional questions about preferred model
        st.divider()
        
        preferred = st.session_state.ratings[question_key].get('preferred_model', '')
        if preferred:
            st.write(f"You selected **{preferred}** as the most helpful response.")
            
            # Ask reason for preference
            reasons = [
              "Clearer explanation",
              "More complete content",
              "Easier to understand (lay language)",
              "More empathetic tone",
              "Best reflects clinical practice",
              "Safest advice"
            ]
            selected_reason = st.session_state.ratings[question_key].get('preference_reason', '')
            st.session_state.ratings[question_key]['preference_reason'] = st.radio(
              "Why did you prefer this answer?",
              options=reasons,
              index=reasons.index(selected_reason) if selected_reason in reasons else 0,
              key=f"reason_{question_key}"
            )
            
            # Ask about comfort level
            comfort = st.session_state.ratings[question_key].get('comfort_level', '')
            st.session_state.ratings[question_key]['comfort_level'] = st.radio(
                "Would you feel comfortable if a patient relied on this answer?",
                options=["Yes, fully comfortable", "Somewhat comfortable", "Not comfortable"],
                index=0 if not comfort else ["Yes, fully comfortable", "Somewhat comfortable", "Not comfortable"].index(comfort),
                key=f"comfort_{question_key}"
            )
            
            if st.button("Continue to Next Question", key=f"continue_{question_key}"):
                navigate_question("next")

# Run the app
if __name__ == "__main__":
    main()