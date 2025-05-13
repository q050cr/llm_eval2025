"""
Utility functions for LLM Response Evaluator
"""
import streamlit as st

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

def navigate_question(direction):
    """Navigate to the next or previous question
    
    Args:
        direction: String, either "next" or "previous"
    """
    if direction == "next":
        if st.session_state.current_question_idx < len(st.session_state.question_order) - 1:
            st.session_state.current_question_idx += 1
        else:
            st.session_state.evaluation_complete = True
    else:  # previous
        if st.session_state.current_question_idx > 0:
            st.session_state.current_question_idx -= 1

def initialize_model_ratings(question_key, model_names):
    """Initialize ratings structure for models
    
    Args:
        question_key: Unique question identifier
        model_names: List of model names to initialize
    """
    if question_key not in st.session_state.ratings:
        st.session_state.ratings[question_key] = {}
        
    for model in model_names:
        if model not in st.session_state.ratings[question_key]:
            st.session_state.ratings[question_key][model] = {}
