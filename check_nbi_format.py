import csv
from pathlib import Path
from collections import Counter

file_path = Path(
    "backend/2025hwybronefiledel/"
    "2025HwyBridgesDelimitedAllStates.txt"
)

if not file_path.exists():
    raise FileNotFoundError(f"Dataset not found: {file_path}")

def inspect_csv(label, quotechar):
    print(f"\n{'=' * 60}")
    print(label)
    print("=" * 60)

    with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
        if quotechar is None:
            reader = csv.reader(
                f, delimiter=",", quoting=csv.QUOTE_NONE
            )
        else:
            reader = csv.reader(
                f, delimiter=",", quotechar=quotechar
            )

        header = next(reader)
        print("Header field count:", len(header))
        print("First 15 headers:", header[:15])

        suspicious = [
            (i, name)
            for i, name in enumerate(header)
            if "052VERT" in name or "SUBMITTED_BYBRIDGE" in name
        ]
        print("Suspicious headers:", suspicious or "None")

        counts = Counter()
        examples = []

        for row_number, row in enumerate(reader, start=2):
            counts[len(row)] += 1
            if len(examples) < 3 and len(row) != len(header):
                examples.append((row_number, len(row), row[:5]))

        print("Data rows checked:", sum(counts.values()))
        print("Field counts (fields: rows):", counts)
        print("First rows with a different field count:", examples)

        for target in [
            "DECK_WIDTH_MT_052",
            "VERT_CLR_OVER_MT_053",
            "SUBMITTED_BY",
            "BRIDGE_CONDITION",
            "DECK_COND_058",
        ]:
            matches = [
                (i, name) for i, name in enumerate(header)
                if target in name
            ]
            print(f"{target}: {matches}")

inspect_csv("TEST A: Single quote as qualifier", "'")
inspect_csv("TEST B: No quote processing", None)