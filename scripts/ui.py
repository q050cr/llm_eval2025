"""
UI components and styling for the LLM Response Evaluator
"""
import streamlit as st

def set_page_config():
    """Configure the Streamlit page settings"""
    st.set_page_config(
        page_title="LLM Response Evaluator",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded"
    )

def apply_custom_css():
    """Apply custom CSS styling to the app"""
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

def display_sidebar(question_count, total_questions):
    """Display the sidebar with navigation controls
    
    Args:
        question_count: Current question number
        total_questions: Total number of questions
    
    Returns:
        tuple: (should_navigate_previous, should_navigate_next, should_save_ratings)
    """
    st.sidebar.header("Navigation")
    
    # Show rater name
    st.sidebar.write(f"Rater: {st.session_state.rater_name}")
    
    # Show progress
    progress = question_count / total_questions
    st.sidebar.progress(progress)
    st.sidebar.write(f"Question {question_count} of {total_questions}")
    
    # Navigation buttons
    col1, col2 = st.sidebar.columns(2)
    nav_previous = False
    nav_next = False
    
    with col1:
        if st.button("⬅️ Previous", disabled=question_count == 1):
            nav_previous = True
            
    with col2:
        if st.button("Next ➡️", disabled=question_count == total_questions):
            nav_next = True
    
    st.sidebar.divider()
    
    # Save ratings button
    save_ratings = False
    if st.sidebar.button("💾 Save All Ratings"):
        save_ratings = True
    
    return nav_previous, nav_next, save_ratings

def get_rater_name():
    """Get the rater's name from the sidebar
    
    Returns:
        str: The rater's name or empty string if not entered
    """
    return st.sidebar.text_input("Enter your name:", key="rater_input")

def display_question(question, category):
    """Display the question and its category
    
    Args:
        question: The question text
        category: The question category
    """
    st.markdown(f"<span class='category-tag'>{category}</span>", unsafe_allow_html=True)
    st.markdown(f"<div class='question-box'><h3>{question}</h3></div>", unsafe_allow_html=True)

def display_model_response(response, model_name, is_selected=False):
    """Display a model's response
    
    Args:
        response: The text response from the model
        model_name: The anonymized model name
        is_selected: Whether this model is selected as preferred
    """
    container_class = 'model-response selected-model' if is_selected else 'model-response'
    st.markdown(f"<h4>{model_name}</h4>", unsafe_allow_html=True)
    st.markdown(f"<div class='{container_class}'>{response}</div>", unsafe_allow_html=True)

def display_evaluation_complete():
    """Display completion message when evaluation is finished"""
    st.header("🎉 Evaluation Complete!")
    st.write("Thank you for completing the evaluation! Your ratings have been recorded.")
    return st.button("Start Over")

def create_rating_tabs():
    """Create tabs for individual ratings and model comparison
    
    Returns:
        tuple: (tab1, tab2) The two tab objects
    """
    return st.tabs(["Rate Individual Responses", "Compare & Select Best Response"])

def display_rating_section(anonymous_name, question_key, criteria_dict):
    """Display rating sliders for a model response
    
    Args:
        anonymous_name: The anonymized model name
        question_key: The unique question identifier
        criteria_dict: Dictionary mapping criteria names to descriptions
    """
    st.markdown("<div class='rating-section'>", unsafe_allow_html=True)
    for criterion, description in criteria_dict.items():
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

def get_preference_details(question_key):
    """Collect details about the preferred model
    
    Args:
        question_key: The unique question identifier
        
    Returns:
        bool: Whether to continue to the next question
    """
    preferred = st.session_state.ratings[question_key].get('preferred_model', '')
    if not preferred:
        return False
        
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
    
    return st.button("Continue to Next Question", key=f"continue_{question_key}")

def display_session_management():
    """Display session management options in the sidebar
    
    Returns:
        tuple: (should_reset, should_save_manual)
    """
    st.sidebar.divider()
    st.sidebar.header("Session Management")
    
    # Save session button
    save_clicked = st.sidebar.button("💾 Save Current Progress")
    
    # Reset session button
    reset_clicked = st.sidebar.button("🗑️ Reset Session", type="secondary")
    
    should_reset = False
    if reset_clicked:
        confirm = st.sidebar.checkbox("Confirm reset - this will erase your progress!")
        if confirm:
            should_reset = True
    
    return should_reset, save_clicked
