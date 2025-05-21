#%%
import pandas as pd
import numpy as np
import os
import re
from pathlib import Path
from datetime import datetime



#%% Define file paths
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

project_root = Path('.')
main_csv_path = project_root / 'outputs/chats/responses_20250521_162812_fixed_20250521_224805.csv'
xai_csv_path = project_root / 'outputs/chats/responses_20250521_231253_xai.csv'
output_path = project_root / f'outputs/chats/app_data_prepared_{timestamp}.csv'

print(f"Loading main responses from: {main_csv_path}")
print(f"Loading XAI responses from: {xai_csv_path}")

#%% Load the main responses file
main_df = pd.read_csv(main_csv_path)

# Load the XAI responses file
xai_df = pd.read_csv(xai_csv_path)

# Check that the key columns match between datasets
print(f"\nMain data shape: {main_df.shape}")
print(f"XAI data shape: {xai_df.shape}")

#%% Verify matching index and query_id columns
index_match_count = sum(main_df['index'] == xai_df['index'])
query_id_match_count = sum(main_df['query_id'] == xai_df['query_id'])
print(f"Matching indices: {index_match_count} out of {len(main_df)}")
print(f"Matching query_ids: {query_id_match_count} out of {len(main_df)}")

# Set match_count based on index matching for the subsequent code
match_count = index_match_count

#%% If indices don't match completely, let's align them
if match_count != len(main_df):
    print("Warning: Indices don't match completely. Aligning data...")
    # Ensure the indices are the same type
    main_df['index'] = main_df['index'].astype(str)
    xai_df['index'] = xai_df['index'].astype(str)
    
    # Merge on index to ensure alignment
    merged_df = pd.merge(
        main_df, 
        xai_df[['index', 'xai_response']], 
        on='index', 
        how='left'
    )
else:
    # If indices match, we can simply add the xai_response column
    merged_df = main_df.copy()
    merged_df['xai_response'] = xai_df['xai_response']

#%% Remove the github_response column as requested
merged_df = merged_df.drop(columns=['github_response'])

#%% Check for error strings in model responses -----------------------
model_cols = [
    'openai_response', 'anthropic_response', 'google_response', 
    'deepseek_response', 'perplexity_response', 'xai_response'
]

error_pattern = 'Error|RateLimitError|APIStatusError|RetryError'
print("\nChecking for error patterns in responses:")

# Apply the check to each model column
error_counts = {}
for col in model_cols:
    error_mask = merged_df[col].str.contains(
        error_pattern, 
        case=False, 
        na=False
    )
    error_count = error_mask.sum()
    error_counts[col] = error_count
    
    if error_count > 0:
        print(f"  - {col}: {error_count} errors found")
        
        # Add a column to flag errors for this model
        error_flag_col = f"{col}_has_error"
        merged_df[error_flag_col] = error_mask
        
        # For debugging, extract a sample of the errors
        if error_count > 0:
            print(f"  - Example error in {col}:")
            sample_error = merged_df[error_mask][col].iloc[0]
            # Print just the first 100 characters
            print(f"    {sample_error[:100]}...")
    else:
        print(f"  - {col}: No errors found")

#%% Check for any missing values in required columns
print("\nChecking for missing values:")
for col in model_cols:
    missing_count = merged_df[col].isna().sum()
    if missing_count > 0:
        print(f"  - {col}: {missing_count} missing values")
    else:
        print(f"  - {col}: No missing values")

#%% Save the prepared data ---------------------------
merged_df.to_csv(output_path, index=False)
print(f"\nPrepared data saved to: {output_path}")

# Print a summary of the prepared data
print("\nSummary of prepared data:")
print(f"  - Total rows: {len(merged_df)}")
print(f"  - Columns: {', '.join(merged_df.columns)}")
print(f"  - Models included: {', '.join([col.split('_')[0] for col in model_cols])}")

#%% Check if any rows have errors across all models
all_errors_mask = np.all([merged_df[col].str.contains(error_pattern, case=False, na=False) 
                        for col in model_cols], axis=0)
all_errors_count = all_errors_mask.sum()

if all_errors_count > 0:
    print(f"\nWARNING: {all_errors_count} rows have errors in ALL model responses")
else:
    print("\nNo rows have errors in ALL model responses")


# %%
