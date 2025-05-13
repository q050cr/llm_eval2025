import pandas as pd
import glob
import os

# Find most recent response file
csv_files = glob.glob(os.path.join('outputs','chats', 'responses_*.csv'))
csv_files.sort(reverse=True)
latest_file = csv_files[0]
print(f"Loading file: {latest_file}")

# Load the data
df = pd.read_csv(latest_file)

# Print basic info
print(f"DataFrame shape: {df.shape}")
print(f"DataFrame index: {list(df.index)}")
print(f"DataFrame columns: {df.columns.tolist()}")

# Print all rows briefly
for idx, row in df.iterrows():
    print(f"Row {idx}: query_id={row['query_id']}, category={row['category']}, question={row['question'][:30]}...")
