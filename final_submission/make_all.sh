#!/bin/zsh
# Rebuild every deliverable from the 14 raw CSVs in data/raw/.
set -e
cd "$(dirname "$0")"
PY=../.venv/bin/python
$PY f1_prep.py            # clean tables -> data/clean/
$PY verify_seeds.py       # seed findings -> verification_log.md
./make_notebook.sh        # F1_Story_Notebook.ipynb (run twice), charts/, facts.json, F1_Dashboard.html
$PY build_report.py       # F1_Final_Report.docx
$PY build_slides.py       # F1_Final_Presentation.pptx (11-slide story deck)
$PY build_review_slides.py  # F1_Review_Presentation.pptx (16 slides, marking-scheme order)
$PY build_viva.py         # Viva_Cheatsheet.md
$PY check_numbers.py      # every number traced to facts.json
