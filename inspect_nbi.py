
from pathlib import Path
import pandas as pd

# Find text files so we can identify the extracted NBI dataset.
files = [
    p for p in Path(".").rglob("*.txt")
    if "node_modules" not in p.parts
    and ".git" not in p.parts
]

print("Text files found:")
for i, path in enumerate(files):
    print(f"{i}: {path}")

if not files:
    raise FileNotFoundError("No .txt files found in the project folder.")

# Select the correct NBI dataset if multiple text files are listed.
file_path = files[0]

print(f"\nInspecting: {file_path}")

# The FHWA delimited file uses single quotes as text qualifiers.
df = pd.read_csv(
    file_path,
    sep=",",
    quotechar="'",
    dtype=str,
    low_memory=False
)

print("\n--- DATASET OVERVIEW ---")
print("Rows:", len(df))
print("Columns:", len(df.columns))

print("\n--- COLUMN NAMES ---")
print(df.columns.tolist())

print("\n--- FIRST 5 RECORDS ---")
print(df.head().to_string())

print("\n--- IMPORTANT CONDITION FIELDS ---")
for col in [
    "STATE_CODE_001",
    "STRUCTURE_NUMBER_008",
    "YEAR_BUILT_027",
    "DATE_OF_INSPECT_090",
    "DECK_COND_058",
    "SUPERSTRUCTURE_COND_059",
    "SUBSTRUCTURE_COND_060",
    "ADT_029",
]:
    if col in df.columns:
        print(f"\n{col}:")
        print(df[col].head(10).tolist())
    else:
        print(f"\nMissing expected column: {col}")

print("\n--- MISSING VALUES: IMPORTANT FIELDS ---")
important = [
    c for c in [
        "STATE_CODE_001",
        "STRUCTURE_NUMBER_008",
        "DATE_OF_INSPECT_090",
        "DECK_COND_058",
        "SUPERSTRUCTURE_COND_059",
        "SUBSTRUCTURE_COND_060",
    ] if c in df.columns
]
print(df[important].isna().sum())

print("\nInspection complete. No source data was modified.")
