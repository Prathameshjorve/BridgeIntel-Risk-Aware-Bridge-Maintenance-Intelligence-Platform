from pathlib import Path
import pandas as pd

path = Path(
    "backend/2025hwybronefiledel/"
    "2025HwyBridgesDelimitedAllStates.txt"
)

df = pd.read_csv(
    path,
    sep=",",
    quotechar="'",
    dtype=str,
    low_memory=False
)

print("DATASET:", df.shape)

# Check whether each bridge identifier is unique
id_cols = ["STATE_CODE_001", "STRUCTURE_NUMBER_008"]
print("\nDuplicate bridge identifiers:")
print(df.duplicated(id_cols).sum())

# Check record types
for col in ["RECORD_TYPE_005A", "BRIDGE_CONDITION"]:
    print(f"\n{col} distribution:")
    print(df[col].value_counts(dropna=False).head(20))

# Inspect component condition ratings
condition_cols = [
    "DECK_COND_058",
    "SUPERSTRUCTURE_COND_059",
    "SUBSTRUCTURE_COND_060",
    "CULVERT_COND_062",
    "LOWEST_RATING",
]

for col in condition_cols:
    print(f"\n{col} distribution:")
    print(df[col].value_counts(dropna=False).sort_index().to_string())

# Check overall condition against component ratings
for col in condition_cols[:4]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

component_cols = condition_cols[:4]
df["CALCULATED_LOWEST"] = df[component_cols].min(
    axis=1, skipna=True
)

print("\nCalculated lowest rating distribution:")
print(df["CALCULATED_LOWEST"].value_counts(dropna=False).sort_index())

print("\nOverall condition versus lowest rating:")
print(pd.crosstab(
    df["BRIDGE_CONDITION"],
    df["LOWEST_RATING"],
    dropna=False
))

print("\nValidation complete. Original dataset unchanged.")