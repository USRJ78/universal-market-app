import os
import json
import re

notebooks = [f for f in os.listdir(".") if f.endswith(".ipynb")]
print(f"Found {len(notebooks)} notebooks.")

for nb_name in sorted(notebooks):
    try:
        with open(nb_name, "r", encoding="utf-8") as f:
            nb = json.load(f)
        print(f"\n==================== {nb_name} ====================")
        code_cells = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
        print(f"Code cells: {len(code_cells)}")
        
        # Look for functions, main classes, or comments describing logic
        for idx, cell in enumerate(code_cells):
            src = "".join(cell.get("source", []))
            lines = src.split("\n")
            
            # Look for def, class, or imports
            defs = [l.strip() for l in lines if l.strip().startswith("def ") or l.strip().startswith("class ")]
            if defs:
                print(f"  Cell {idx} defines:")
                for d in defs[:5]:
                    print(f"    {d}")
            
            # Print cell comments or title-like strings if any
            comments = [l.strip() for l in lines if l.strip().startswith("#")][:3]
            if comments:
                print(f"    Comments: {comments}")
    except Exception as e:
        print(f"Error reading {nb_name}: {e}")
