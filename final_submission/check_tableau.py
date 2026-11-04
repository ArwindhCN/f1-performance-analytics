"""
Consistency checks for tableau/F1_Dashboard.twbx (things a schema cannot see):
fields used by every chart exist in its data, colour values exist, dashboards/story/actions point at real sheets,
and every extract holds the same rows as its CSV.  Run:  python check_tableau.py
"""
import html
import re
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
from lxml import etree
from tableauhyperapi import Connection, HyperProcess, Telemetry

HERE = Path(__file__).resolve().parent
pkg = Path(tempfile.mkdtemp())
zipfile.ZipFile(HERE / "tableau" / "F1_Dashboard.twbx").extractall(pkg)
t = etree.parse(str(pkg / "F1_Dashboard.twb"))
root, problems = t.getroot(), []

sources = {d.get("name"): d for d in root.find("datasources")}
csv_of = {n: pkg / "Data" / "csv" / d.find(".//relation").get("name") for n, d in sources.items()}
data = {n: pd.read_csv(p) for n, p in csv_of.items()}
sheets = {w.get("name"): w for w in root.iter("worksheet")}
boards = {d.get("name"): d for d in root.find("dashboards")}

# 1. extracts exist and hold every row
with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU, parameters={"log_dir": tempfile.gettempdir()}) as hp:
    for n, d in sources.items():
        ex = d.find("extract/connection")
        path = pkg / ex.get("dbname") if ex is not None else None
        if path is None or not path.exists():
            problems.append(f"{n}: extract missing")
            continue
        with Connection(hp.endpoint, path) as con:
            rows = con.execute_scalar_query('SELECT COUNT(*) FROM "Extract"."Extract"')
        if rows != len(data[n]):
            problems.append(f"{n}: extract has {rows} rows, CSV {len(data[n])}")

# 2. colour values exist in the data
for n, d in sources.items():
    for enc in d.iter("encoding"):
        field = re.search(r"\[none:(.+):nk\]", enc.get("field")).group(1)
        values = set(data[n][field].astype(str))
        for b in enc.iter("bucket"):
            if html.unescape(b.text).strip('"') not in values:
                problems.append(f"{n}: colour for '{b.text}' but no such {field}")

# 2b. Tableau drops a palette unless its field is declared on the data source (column + column-instance)
palette_cols = {}
for n, d in sources.items():
    inst = {c.get("name") for c in d.findall("column-instance")}
    cols = {c.get("name") for c in d.findall("column")}
    palette_cols[n] = set()
    for enc in d.iter("encoding"):
        f = enc.get("field")
        if f not in inst or "[" + f.split(":")[1] + "]" not in cols:
            problems.append(f"{n}: palette field {f} not declared, Tableau would ignore its colours")
        palette_cols[n] |= {m.get("to").lower() for m in enc.iter("map")}

# 2c. the colour key in each chart title uses only that chart's palette colours
for w in root.iter("worksheet"):
    ds = w.find(".//datasource-dependencies").get("datasource")
    for run in w.find("layout-options").iter("run"):
        col = (run.get("fontcolor") or "").lower()
        if col and col != "#555555" and col not in palette_cols[ds]:
            problems.append(f"{w.get('name')}: title key colour {col} is not in its palette")

# 3. every field a chart uses is declared and exists in its data source
for name, ws in sheets.items():
    dep = ws.find(".//datasource-dependencies")
    ds = dep.get("datasource")
    declared = {c.get("name") for c in dep.iter("column-instance")}
    for c in dep.iter("column-instance"):
        if c.get("column").strip("[]") not in data[ds].columns:
            problems.append(f"{name}: {c.get('column')} not in {csv_of[ds].name}")
    refs = [ws.find(".//rows").text, ws.find(".//cols").text]
    for tag in ("color", "size", "text", "lod"):
        refs += [e.get("column") for e in ws.iter(tag) if e.get("column")]
    refs += [f.get("column") for f in ws.iter("filter")] + [s.get(a) for s in ws.iter("sort") for a in ("column", "using")]
    for r in refs:
        src, field = re.match(r"\[(.+?)\]\.(\[.+\])", r).groups()
        if src != ds or field not in declared:
            problems.append(f"{name}: uses {r} but does not declare it")

# 4. dashboards, story and actions point at real sheets
for bname, b in boards.items():
    for z in b.iter("zone"):
        if z.get("name") and z.get("name") not in sheets:
            problems.append(f"dashboard {bname}: zone for missing sheet {z.get('name')}")
    for sp in b.iter("story-point"):
        if sp.get("captured-sheet") not in sheets and sp.get("captured-sheet") not in boards:
            problems.append(f"story point {sp.get('id')}: missing sheet {sp.get('captured-sheet')}")
on_board = {b: {z.get("name") for z in boards[b].iter("zone") if z.get("name")} for b in boards}
for a in root.iter("action"):
    src = a.find("source")
    if src.get("worksheet") not in on_board.get(src.get("dashboard"), set()):
        problems.append(f"action {a.get('caption')}: source sheet not on dashboard")
    for p in a.iter("param"):
        if p.get("name") == "exclude":
            for s in p.get("value").split(","):
                if s not in sheets:
                    problems.append(f"action {a.get('caption')}: excludes unknown sheet {s}")
for w in root.find("windows"):
    if w.get("name") not in sheets and w.get("name") not in boards:
        problems.append(f"window for unknown sheet {w.get('name')}")

story = [b for b in boards.values() if b.get("type") == "storyboard"]
print(f"{len(sources)} data sources, {len(sheets)} worksheets, {len(boards) - len(story)} dashboards, "
      f"{len(story)} story with {sum(1 for _ in story[0].iter('story-point'))} points, {len(list(root.iter('action')))} actions")
print("No consistency problems found." if not problems else "PROBLEMS:\n  " + "\n  ".join(problems))
