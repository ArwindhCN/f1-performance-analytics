"""Builds Viva_Cheatsheet.md from facts.json: 20 likely questions, short answers, and the notebook cell that proves each."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FACTS = json.loads((HERE / "facts.json").read_text())


def F(k):
    return FACTS[k]["text"]


VER = [l for l in (HERE / "verification_log.md").read_text().splitlines() if l.startswith("| ") and "|---" not in l][1:]
N_CHECKS = sum(1 for l in VER if l.split("|")[5].strip() != "n/a")
N_OK = sum(1 for l in VER if l.split("|")[5].strip().startswith("Yes"))


QA = [
    ("What is your project, in one sentence?",
     f"Ten seasons of F1 data ({F('P.n_races')} races, 2015–2024) told as one story in five acts, so the reader sees a race "
     f"as a chain of cause and effect: Saturday sets the order, pit stops trade places, an extra stop is an alarm, and the "
     f"car sets the ceiling.", "Title cell; H.1–C.1"),
    ("What data did you use, and how did you clean it?",
     f"The 14 Ergast-lineage CSVs, filtered to 2015–2024: {F('P.n_results')} race entries, {F('P.n_stops')} pit stops, "
     f"{F('P.n_laps')} lap times. \\N → missing; grid 0 (pit-lane start) → missing; Q times → seconds; pit time from the "
     f"milliseconds column; joins on IDs only; final standings = last round. Every row count is asserted equal to the "
     f"Primary Review workbook.", "P.1–P.12"),
    ("Why rebuild from the raw CSVs instead of your Excel workbook?",
     "The workbook's constructor sheet has names but no constructor ID, and joining on names is unsafe (Toro Rosso → "
     "AlphaTauri → RB have different IDs). The rebuild matches every workbook row count.", "P.10"),
    ("What is a genuine DNF, and why is \"+1 Lap\" not one?",
     f"A genuine DNF is any status other than \"Finished\" or \"+N Lap(s)\". A lapped car still finished. "
     f"{F('P.n_dnf')} genuine DNFs vs {F('P.n_unclassified')} unclassified: the {F('P.n_dnf_classified')} difference are "
     f"cars that retired late but covered 90% of the race, so they kept a position. Hence two flags.", "P.3, P.12"),
    ("Why the 2016 Chinese GP as the hook?",
     f"Chosen by a rule: sum of places gained or lost lap to lap. It ranks first of {F('H.n_races')} races "
     f"({F('H.changes')}; the median race has {F('H.median_changes')}), it has {F('H.dnfs')} DNFs so every line is "
     f"complete, and every act appears in it.", "H.1, H.2"),
    ("How strongly does the grid predict the finish?",
     f"Pooled r = {F('A1.pooled_r')} over {F('A1.n')} classified finishes. Pole won {F('A1.pole_win')} of races; "
     f"{F('A1.top3_win')} of winners started top three.", "A1.1"),
    ("Why is Monaco top, and why not trust Hockenheim's rank?",
     f"{F('A1.top_circuit')} r = {F('A1.top_r')}: a narrow street circuit, overtaking almost impossible. "
     f"{F('A1.bottom_circuit')} r = {F('A1.bottom_r')} but only {F('A1.bottom_races')} races ({F('A1.bottom_n')} finishes); "
     f"its 95% range is {F('A1.bottom_lo')}–{F('A1.bottom_hi')}. Median circuit r = {F('A1.median_r')} "
     f"({F('A1.n_circuits')} circuits with 40+ finishes).", "A1.2"),
    ("How did you measure the undercut?",
     f"First stops only. Position on lap L−1, L+2, L+10 from lap_times; thirds of each race's first-stop laps. "
     f"Early {F('A2.early_chg2')} then {F('A2.early_chg10')} (wins back {F('A2.early_back')}); late {F('A2.late_chg2')} "
     f"then {F('A2.late_chg10')} (wins back {F('A2.late_back')}). n = {F('A2.n')}. Robust when stops in laps 1–5 are dropped.",
     "A2.1–A2.3"),
    ("What is the derived teammate link and StopDiff?",
     f"Two drivers, same constructor, same race, both with a qualifying position ({F('A3.n_pairs')} pairs). The one who "
     f"qualified behind is the slower qualifier. StopDiff = his stops − the faster teammate's stops. It chains Qualifying, "
     f"Pit Stops and Results.", "A3.1"),
    ("What assumption did you test in Act 3?",
     f"\"A driver far behind the teammate gambles on extra stops.\" Correlation of qualifying gap with StopDiff: "
     f"r = {F('A3.r_gap')} (p = {F('A3.r_gap_p')}). No link, so the assumption is dead.", "A3.3"),
    ("What is the main Act 3 finding?",
     f"With an extra stop the slower qualifier beats the teammate {F('A3.rate_extra_1')} of the time (n = {F('A3.n_extra')}); "
     f"without, {F('A3.rate_no_1')} (n = {F('A3.n_no')}); z = {F('A3.z')}. Median finishing gap {F('A3.med_gap_extra')} vs "
     f"{F('A3.med_gap_no')}.", "A3.4"),
    ("Is the extra stop the cause of the lost result?",
     f"No. It is a symptom of trouble (damage, puncture, spin, bad safety-car timing). Evidence: whoever makes the extra stop "
     f"loses (slower qualifier wins {F('A3.beat_when_mate_extra')} when the teammate made it), and "
     f"{F('A3.early_stop_extra')} of extra-stop drivers first stopped in laps 1–3 vs {F('A3.early_stop_no')}. It is a "
     f"correlation, used as a warning light, not a lever.", "A3.5"),
    ("Does the Act 3 result hold for every qualifying gap?",
     f"Direction yes: small {F('A3.small_extra')} vs {F('A3.small_no')}, medium {F('A3.medium_extra')} vs "
     f"{F('A3.medium_no')}, large {F('A3.large_extra')} vs {F('A3.large_no')}. But the large bucket has only "
     f"{F('A3.large_n_extra')} extra-stop pairs and p = {F('A3.large_p')}: not significant there.", "A3.4"),
    ("What does \"the car sets the ceiling\" mean in numbers?",
     f"Mercedes {F('A4.mer_2015')} of points (2015) → {F('A4.mer_2023')} (2023); Red Bull {F('A4.rbr_2015')} → "
     f"{F('A4.rbr_2023')}; McLaren {F('A4.mcl_2015')} → {F('A4.mcl_2024')}. Biggest three-season swing: "
     f"{F('A4.swing_team')} {F('A4.swing_dir')} {F('A4.swing_pp')} points ({F('A4.swing_from')}–{F('A4.swing_to')}). "
     f"{F('A4.wins_champ_car')} of wins went to the season's champion team.", "A4.1, A4.3"),
    ("How has reliability changed?",
     f"Genuine DNF rate {F('A4.dnf_2015')} (2015) → {F('A4.dnf_2024')} (2024), with rises in 2017 ({F('A4.dnf_2017')}) "
     f"and 2022 ({F('A4.dnf_2022')}), both new-rules years. Best team: {F('A4.dnf_best_team')} {F('A4.dnf_best')}.", "A4.2"),
    ("Driver or circuit: which matters more?",
     f"Driver (with car). In the heatmap, driver rows differ by {F('A4.hm_row_range')} places, circuit columns by "
     f"{F('A4.hm_col_range')}.", "A4.5"),
    ("Did any earlier finding fail to reproduce?",
     f"{N_OK} of {N_CHECKS} checks reproduce, three only after a choice was made explicit. Consistency vs points gives r = "
     f"{F('A4.cons_r')} only if driver-races under 10 laps are dropped; keeping them gives {F('A4.cons_r_all')}; median "
     f"race gives {F('A4.cons_r_med')}; per-race filter {F('A4.cons_r_race')}. Weak and fragile, reported as such. Also, "
     f"Hockenheim has {F('A1.bottom_races')} races in the data, not 4 as the old document said.", "A4.6; verification_log.md"),
    ("Why three tools, and why not Power BI?",
     "Matplotlib: precise hand-annotated story charts and exact axis control. Seaborn: statistics with bootstrap "
     "confidence ranges. Plotly: interactivity and the dashboard. Plotly replaced Power BI so the whole analysis stays "
     "reproducible in a single notebook.", "S.1, A4.1, D.1"),
    ("Explain your misleading chart.",
     f"2024 constructor points, {F('A5.lead')} {F('A5.lead_pts')} vs {F('A5.second')} {F('A5.second_pts')}. Y-axis cut at "
     f"{F('A5.base')} makes the bar {F('A5.visual_ratio')}× taller for a {F('A5.gap_pct')} gap. False impression: "
     f"\"crushed\"; reality: {F('A5.closest')} title of the decade. Fix: axis from 0. Principle: truthful scaling / "
     f"proportional ink; lie factor ≈ {F('A5.lie_factor')}.", "A5.1–A5.3"),
    ("How do you know the numbers in the report and slides match the notebook?",
     "The notebook records every number with fact() and saves facts.json with the producing cell. Markdown, report, slides "
     "and this sheet are generated from that file. make_notebook.sh runs the notebook twice from a fresh kernel and checks "
     "facts.json is identical. Limits remain: correlation is not causation, and there is no tyre, weather or safety-car "
     "data.", "F.1; make_notebook.sh"),
]

lines = ["# Viva cheat sheet", "",
         "Arwindh C N · CB.SC.U4CSE24207 · 23CSE353 Data Visualisation", "",
         "Twenty likely questions with short answers. **Proof** names the notebook cell (F1_Story_Notebook.ipynb) that "
         "computes each number; cell labels are printed in the cell output and in every chart footer.", ""]
for i, (q, a, cell) in enumerate(QA, 1):
    lines += [f"**{i}. {q}**", "", a, "", f"*Proof: Cell {cell}*" if not cell.startswith(("Title", "verification"))
              else f"*Proof: {cell}*", ""]
(HERE / "Viva_Cheatsheet.md").write_text("\n".join(lines), encoding="utf-8")
print("wrote Viva_Cheatsheet.md with", len(QA), "questions")
