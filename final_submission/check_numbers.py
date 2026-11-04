"""
Checks that every number in the report, slides (with speaker notes), viva sheet and notebook prose
comes from facts.json or verification_log.md. Prints anything else for a human to review.
Run:  python check_numbers.py
"""
import json
import re
from pathlib import Path

import nbformat
from docx import Document
from pptx import Presentation

HERE = Path(__file__).resolve().parent
FACTS = json.loads((HERE / "facts.json").read_text())
NUM = re.compile(r"(?<![\w.])[-+−]?\d[\d,]*(?:\.\d+)?%?")


def norm(tok):
    t = tok.replace("−", "-").replace(",", "").rstrip("%").lstrip("+")
    try:
        v = float(t)
    except ValueError:
        return None
    return f"{abs(v):g}"


known = set()
for f in FACTS.values():
    for tok in NUM.findall(str(f["text"])):
        known.add(norm(tok))
    if isinstance(f["value"], (int, float)):
        known.add(norm(str(round(f["value"], 4))))
for tok in NUM.findall((HERE / "verification_log.md").read_text()):
    known.add(norm(tok))
# Definitions, rules and labels, not results: years, F1 rules (25 points, 90% distance), thresholds used
# in the method (10 laps, 40+ finishes, 60 s, 60 starts, 95% CI, IQR 1.5), cell/figure/slide numbers.
ALLOWED = {str(y) for y in range(2014, 2027)} | {str(i) for i in range(0, 13)} | {
    "14", "16", "17", "20", "21", "22", "24", "25", "26", "40", "50", "60", "90", "95", "100", "1.5", "1.96", "8"}

sources = {}
doc = Document(HERE / "F1_Final_Report.docx")
txt = [p.text for p in doc.paragraphs]
for t in doc.tables:
    for row in t.rows:
        txt += [c.text for c in row.cells]
sources["report"] = txt
for deck, label in [("F1_Final_Presentation.pptx", "slides"), ("F1_Review_Presentation.pptx", "review slides")]:
    if not (HERE / deck).exists():
        continue
    txt = []
    for sl in Presentation(HERE / deck).slides:
        for sh in sl.shapes:
            if sh.has_text_frame:
                txt.append(sh.text_frame.text)
            if getattr(sh, "has_table", False) and sh.has_table:
                txt += [cell.text for row in sh.table.rows for cell in row.cells]
        txt.append(sl.notes_slide.notes_text_frame.text)
    sources[label] = txt
sources["viva"] = (HERE / "Viva_Cheatsheet.md").read_text().splitlines()
nb = nbformat.read(HERE / "F1_Story_Notebook.ipynb", as_version=4)
sources["notebook prose"] = [c.source for c in nb.cells if c.cell_type == "markdown"]

bad = 0
for name, chunks in sources.items():
    seen = set()
    for chunk in chunks:
        chunk = re.sub(r"Cells? [A-Z]\.?\d*(?:\.\d+)?(?:–[A-Z]?\d*\.?\d+)?", "", chunk)   # cell labels
        chunk = re.sub(r"\b[A-Z]\d\.\d+\b|\bP\.\d+\b|\b[HCDFS]\.\d\b", "", chunk)
        chunk = re.sub(r"^\d+(\.\d+)? |Figure \d+|\*\*\d+\.|\d+:\d+\.\d+|1950", "", chunk)   # labels, examples
        for tok in NUM.findall(chunk):
            n = norm(tok)
            if n is None or n in known or n in ALLOWED or (name, n) in seen:
                continue
            seen.add((name, n))
            i = chunk.find(tok)
            print(f"[{name}] {tok!r}: ...{chunk[max(0, i - 60):i + 40]!r}...")
            bad += 1
print(f"\n{bad} number(s) not traced to facts.json / verification_log.md (review each above)")
