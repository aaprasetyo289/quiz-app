import pandas as pd

# Test reading the CSV
df = pd.read_csv('multichoice-uts-mankeb.csv')
print('Columns:', df.columns.tolist())
print('Number of rows:', len(df))
print('\nFirst row:')
print(df.iloc[0])
