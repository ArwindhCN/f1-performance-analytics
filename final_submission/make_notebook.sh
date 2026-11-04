#!/bin/zsh
# Build and run the story notebook twice so the prose is filled from facts.json.
set -e
cd "$(dirname "$0")"
PY=../.venv/bin/python
JUP=../.venv/bin/jupyter
rm -f facts.json
$PY build_notebook.py                       # pass 1: tokens unfilled
$JUP nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=900 F1_Story_Notebook.ipynb
cp facts.json .facts_pass1.json
$PY build_notebook.py                       # pass 2: tokens filled from facts.json
$JUP nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=900 F1_Story_Notebook.ipynb
cmp -s facts.json .facts_pass1.json && rm .facts_pass1.json && echo "facts stable across runs" || { echo "FACTS CHANGED"; exit 1; }
