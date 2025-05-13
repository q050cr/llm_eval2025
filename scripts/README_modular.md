# LLM Response Evaluator - Modular Structure

This document explains the modular structure of the LLM Response Evaluator Streamlit application.

## File Structure

The application has been modularized into the following files:

- `streamlit_app_modular.py`: The main entry point of the application that uses the modular structure
- `streamlit_app.py`: The original, non-modular application (kept for reference)
- `ui.py`: Contains UI-related components and helper functions
- `data.py`: Handles data loading, processing, and saving
- `utils.py`: Contains utility functions and constants

## Key Features

### Session Persistence

The application now supports session persistence, allowing users to:

- Continue evaluations across multiple sessions
- Automatically save progress when navigating between questions
- Manually save progress using the session management panel
- Reset the session if needed

Session data is stored in JSON files under the `outputs/sessions/` directory, with filenames based on the rater's name.

## Module Descriptions

### ui.py

This module contains UI-related components and helper functions:

- `set_page_config()`: Configures the Streamlit page settings
- `apply_custom_css()`: Applies custom CSS styles to the application
- `display_sidebar()`: Creates and manages the navigation sidebar
- `get_rater_name()`: Gets the rater's name from user input
- `display_question()`: Shows the question and its category
- `display_model_response()`: Shows a model's response with appropriate styling
- `display_evaluation_complete()`: Shows the completion message
- `create_rating_tabs()`: Creates tabs for individual ratings and comparisons
- `display_rating_section()`: Shows rating sliders for model responses
- `get_preference_details()`: Collects data about the preferred model

### data.py

This module handles data loading, processing, and saving operations:

- `load_response_data()`: Loads response data from CSV files
- `anonymize_models()`: Creates anonymous mapping for model names
- `save_ratings()`: Saves ratings to a CSV file
- `get_current_question_data()`: Gets data for the current question
- `initialize_question_order()`: Creates a randomized order of questions
- `initialize_session_state()`: Sets up session state variables

### utils.py

This module contains utility functions and constants:

- `RATING_CRITERIA`: Dictionary mapping criteria names to descriptions
- `navigate_question()`: Handles navigation between questions
- `initialize_model_ratings()`: Sets up ratings structure for models

## How to Use

To use the modular version of the application, simply run:

```bash
streamlit run scripts/streamlit_app_modular.py
```
