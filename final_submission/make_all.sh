#!/bin/zsh
# Rebuild every output from the 14 raw CSVs in data/raw/.
set -e
cd "$(dirname "$0")"
PY=../.venv/bin/python
$PY f1_prep.py              # clean tables -> data/clean/
$PY verify_seeds.py         # recompute the earlier exploratory findings -> verification_log.md
./make_notebook.sh          # F1_Story_Notebook.ipynb (run twice), charts/, facts.json, F1_Dashboard.html
$PY build_report.py         # F1_Final_Report.docx
$PY build_review_slides.py  # F1_Review_Presentation.pptx
$PY build_tableau.py        # tableau/F1_Dashboard.twbx (story, dashboards, extracts)
$PY check_tableau.py        # Tableau consistency checks
$PY check_numbers.py        # every number traced to facts.json
for f in F1_Final_Report.docx F1_Review_Presentation.pptx; do
  /Applications/LibreOffice.app/Contents/MacOS/soffice --headless --convert-to pdf "$f" >/dev/null 2>&1 || true
done
[ -f F1_Final_Report.pdf ] && mv F1_Final_Report.pdf F1_Report.pdf
[ -f F1_Review_Presentation.pdf ] && mv F1_Review_Presentation.pdf F1_Presentation.pdf
echo "done"
