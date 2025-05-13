"""
LLM Response Evaluator - Main Application (Modularized Version)

A Streamlit application for evaluating and comparing LLM responses 
to medical and scientific questions.
# Help for fast implementation by Claude 3.7 Somnet
"""
import streamlit as st
import random

# Import from local modules
from ui import (set_page_config, apply_custom_css, display_sidebar, get_rater_name,
               display_question, display_model_response, display_evaluation_complete,
               create_rating_tabs, display_rating_section, get_preference_details,
               display_session_management)
from data import (load_response_data, anonymize_models, save_ratings,
                 get_current_question_data, initialize_question_order, initialize_session_state,
                 save_session_state, load_session_state)
from utils import RATING_CRITERIA, navigate_question, initialize_model_ratings

def main():
    """Main application function"""
    # Setup UI
    set_page_config()
    apply_custom_css()
    st.title("🧠 LLM Response Evaluator")
    
    # Initialize session state
    initialize_session_state()
    
    # Sidebar
    with st.sidebar:
        # Get rater name if not set
        if not st.session_state.rater_name:
            st.session_state.rater_name = get_rater_name()
            if not st.session_state.rater_name:
                st.warning("Please enter your name to begin rating")
                return
            
            # Try to load session for this rater
            if load_session_state():
                st.success(f"Welcome back, {st.session_state.rater_name}! Your previous session was loaded.")
            else:
                st.info(f"Welcome, {st.session_state.rater_name}! Starting a new evaluation session.")
        
        # Load data if not loaded
        if "df" not in st.session_state:
            st.session_state.df = load_response_data()
            
            # Exit if no data is loaded
            if st.session_state.df is None:
                st.error("Failed to load data. Please check the file path.")
                return
                
            # Create question order if it doesn't exist
            if not st.session_state.question_order:
                st.session_state.question_order = initialize_question_order(st.session_state.df)
            
            # Anonymize models
            anonymize_models(st.session_state.df)
        
        # Display navigation controls
        nav_previous, nav_next, do_save = display_sidebar(
            st.session_state.current_question_idx + 1,
            len(st.session_state.question_order)
        )
        
        # Session management
        should_reset, should_save_manual = display_session_management()
        if should_reset:
            st.session_state.clear()
            st.success("Session has been reset. The page will reload.")
            st.rerun()
            return
            
        if should_save_manual:
            if save_session_state():
                st.success("Your progress has been saved!")
            else:
                st.error("Failed to save progress.")
        
        if nav_previous:
            navigate_question("previous")
            # Save session state when navigating
            save_session_state()
            st.rerun()
        elif nav_next:
            navigate_question("next")
            # Save session state when navigating
            save_session_state()
            st.rerun()
        elif do_save:
            filename = save_ratings()
            if filename:
                # Also save session state
                if save_session_state():
                    st.success(f"Ratings saved to {filename} and session state preserved")
                else:
                    st.success(f"Ratings saved to {filename}")
            else:
                st.error("No ratings to save")
    
    # Skip if evaluation is complete
    if st.session_state.evaluation_complete:
        # Save session state one last time to mark as complete
        save_session_state()
        
        if display_evaluation_complete():
            # Clear session state and restart
            st.session_state.clear()
            st.rerun()
        return
    
    # Skip if no name entered
    if not st.session_state.rater_name:
        return
        
    # Get current question data
    question_key, question, category, question_data = get_current_question_data()
    if question_key is None:
        st.error(f"No data found for the current question")
        return
    
    # Display question
    display_question(question, category)
    
    # Get model columns and create tabs for each model
    model_columns = [col for col in question_data.columns if col.endswith('_response')]
    
    # Shuffle the order of model responses
    model_order = list(range(len(model_columns)))
    
    # Only shuffle if this is the first time seeing this question
    if question_key not in st.session_state.ratings:
        random.shuffle(model_order)
    
    # Get anonymized model names
    model_names = []
    for idx in model_order:
        if idx < len(model_columns):
            col = model_columns[idx]
            model_name = col.replace('_response', '')
            model_names.append(st.session_state.model_mapping[model_name])
    
    # Initialize ratings for this question if they don't exist
    initialize_model_ratings(question_key, model_names)
    
    # Create tabs for ratings
    tab1, tab2 = create_rating_tabs()
    
    with tab1:
        # Individual response ratings
        for i, idx in enumerate(model_order):
            if idx >= len(model_columns):
                continue
                
            col = model_columns[idx]
            model_name = col.replace('_response', '')
            anonymous_name = st.session_state.model_mapping[model_name]
            
            with st.expander(f"{anonymous_name}", expanded=True):
                st.markdown(f"<div class='model-response'>{question_data[col].iloc[0]}</div>", unsafe_allow_html=True)
                display_rating_section(anonymous_name, question_key, RATING_CRITERIA)
    
    with tab2:
        # Model comparison section
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
                
                # Display the model response
                display_model_response(
                    question_data[col].iloc[0], 
                    anonymous_name, 
                    is_preferred
                )
                
                if st.button(f"Select {anonymous_name} as Best", key=f"best_{question_key}_{anonymous_name}"):
                    st.session_state.ratings[question_key]['preferred_model'] = anonymous_name
                    st.rerun()
            
            idx += 1
        
        # Preference details section
        st.divider()
        continue_next = get_preference_details(question_key)
        if continue_next:
            navigate_question("next")
            # Save session state when navigating
            save_session_state()
            st.rerun()

# Run the app
if __name__ == "__main__":
    main()
