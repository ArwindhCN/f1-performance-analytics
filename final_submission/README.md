# Formula 1 Performance Analytics, 2015–2024 · Final Review

Arwindh C N · CB.SC.U4CSE24207 · 23CSE353 Data Visualisation

## Deliverables
| File | What it is |
|---|---|
| `F1_Story_Notebook.ipynb` | The analysis, written as a story in five acts. Executed top to bottom with outputs saved. |
| `F1_Dashboard.html` | Interactive Plotly dashboard (one self-contained file, works offline). |
| `F1_Final_Report.docx` | Descriptive report with embedded charts. |
| `F1_Final_Presentation.pptx` | 11 slides, one story beat each, with speaker notes. |
| `Viva_Cheatsheet.md` | 20 likely questions, short answers, and the notebook cell that proves each. |
| `verification_log.md` | Every earlier ("seed") finding recomputed from the raw data. |
| `charts/` | Every chart as PNG (and the two Plotly charts as HTML); `charts/slides/` holds title-free copies for the slides. |

## How the numbers stay consistent
Each number used in prose is recorded in the notebook with `fact()` and saved to `facts.json` together with the cell that
produced it. The notebook's markdown, the report, the slides and the viva sheet are all generated from that file, and
`check_numbers.py` confirms that every number in them traces back to it.

## Reproduce
```
./make_all.sh
```
This runs `f1_prep.py` (cleaning), `verify_seeds.py`, `make_notebook.sh` (builds the notebook and runs it twice from a
fresh kernel, checking `facts.json` is identical), then `build_report.py`, `build_slides.py`, `build_viva.py` and
`check_numbers.py`. Python packages: pandas, numpy, scipy, matplotlib, seaborn, plotly, kaleido, python-docx,
python-pptx, nbformat, nbconvert. Plotly PNG export needs a Chromium browser (Chrome or Brave).

Raw data: `data/raw/` (14 Ergast-lineage CSVs). Clean tables: `data/clean/`.
