import json
import os
import sys

# Reconfigure stdout to use utf-8
sys.stdout.reconfigure(encoding='utf-8')

def inspect_notebook(filename):
    print(f"=== Inspecting {filename} ===")
    if not os.path.exists(filename):
        print("File does not exist.")
        return
    with open(filename, "r", encoding="utf-8") as f:
        nb = json.load(f)
    print(f"Total cells: {len(nb.get('cells', []))}")
    code_cells = [c for c in nb.get('cells', []) if c.get('cell_type') == 'code']
    print(f"Code cells: {len(code_cells)}")
    for idx, c in enumerate(code_cells):
        src = "".join(c.get('source', []))
        print(f"Cell {idx}: length {len(src)} chars")
        # Print first 200 characters of each cell (safely encoded)
        snippet = src[:200]
        print(snippet.encode('ascii', errors='replace').decode('ascii') + "...")
        # Search for excel exports
        if any(x in src for x in ["to_excel", "to_csv", "xlsx", "csv", "df = ", "pd.read"]):
            lines = src.split("\n")
            for line_no, line in enumerate(lines):
                if any(x in line for x in ["to_excel", "to_csv", "xlsx", "csv", "df = ", "pd.read"]):
                    print(f"  Line {line_no}: {line.strip().encode('ascii', errors='replace').decode('ascii')}")

print("Inspecting CRYPTO.ipynb")
inspect_notebook("CRYPTO.ipynb")
print("\nInspecting CRYPTOARB.ipynb")
inspect_notebook("CRYPTOARB.ipynb")
