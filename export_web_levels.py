"""Export the original deterministic Python puzzles for GitHub Pages."""
import json
from pathlib import Path
from generation import generate_level

levels = []
for number in range(101):
    level = generate_level(number)
    levels.append({"level": number, "grid_size": level["grid_size"], "target": level["target"], "pieces": [p.cells for p in level["pieces"]], "solution": level["solution"]})
destination = Path(__file__).parent / "docs" / "levels.js"
destination.write_text("const LEVELS = " + json.dumps(levels, separators=(",", ":")) + ";\n", encoding="utf-8")
print(f"Exported {len(levels)} original puzzles")
