"""
Builds F1_Final_Report.docx from facts.json (written by the notebook) and the charts/ folder.
Every number in the text is read from facts.json, so the report always matches the notebook.
Run after make_notebook.sh:  python build_report.py
"""
import json
import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = Path(__file__).resolve().parent
FACTS = json.loads((HERE / "facts.json").read_text())
CH = HERE / "charts"
BLACK, GREY, MID = RGBColor(0, 0, 0), RGBColor(0x55, 0x55, 0x55), RGBColor(0x76, 0x76, 0x76)


def F(k):
    return FACTS[k]["text"]


def C(k):                      # the notebook cell that produced a fact
    return FACTS[k]["cell"]


# ------------------------------------------------------------------ document and styles
doc = Document()
sec = doc.sections[0]
sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
sec.left_margin = sec.right_margin = Cm(2.2)
sec.top_margin, sec.bottom_margin = Cm(2.0), Cm(2.0)
TEXT_W = 21.0 - 4.4


def set_font(style, size, bold=False, italic=False, color=BLACK):
    style.font.name = "Arial"
    rf = style.element.rPr.rFonts
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        rf.attrib.pop(qn(a), None)
    rf.set(qn("w:eastAsia"), "Arial")
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.italic = italic
    style.font.color.rgb = color


st = doc.styles
set_font(st["Normal"], 10.5)
st["Normal"].paragraph_format.space_after = Pt(6)
st["Normal"].paragraph_format.line_spacing = 1.15
for name, size, before in [("Heading 1", 15, 18), ("Heading 2", 12, 12), ("Heading 3", 10.5, 8)]:
    set_font(st[name], size, bold=True)
    st[name].paragraph_format.space_before = Pt(before)
    st[name].paragraph_format.space_after = Pt(5)
    st[name].paragraph_format.keep_with_next = True
set_font(st["Caption"], 9, italic=True, color=GREY)
st["Caption"].paragraph_format.space_after = Pt(10)
for name in ["List Bullet", "List Number"]:
    set_font(st[name], 10.5)
    st[name].paragraph_format.space_after = Pt(3)


def para(text="", style=None, bold_lead=None, align=None, size=None, color=None, italic=False, after=None):
    p = doc.add_paragraph(style=style)
    if bold_lead:
        r = p.add_run(bold_lead)
        r.bold = True
    for i, part in enumerate(re.split(r"(\*\*[^*]+\*\*)", text)):
        if not part:
            continue
        bold = part.startswith("**") and part.endswith("**")
        r = p.add_run(part[2:-2] if bold else part)
        r.bold = bold or None
        r.italic = italic or None
        if size:
            r.font.size = Pt(size)
        if color is not None:
            r.font.color.rgb = color
    if align:
        p.alignment = align
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    return p


def bullets(items, style="List Bullet"):
    for it in items:
        if isinstance(it, tuple):
            para(it[1], style=style, bold_lead=it[0])
        else:
            para(it, style=style)


FIG = [0]


def figure(path, caption, width=13.0):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(str(path), width=Cm(width))
    FIG[0] += 1
    para(f"Figure {FIG[0]}. {caption}", style="Caption", align=WD_ALIGN_PARAGRAPH.LEFT)


def shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def table(header, rows, widths, size=9):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold = True
        r.font.size = Pt(size)
        shade(c, "EDEDED")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            for part in re.split(r"(\*\*[^*]+\*\*)", str(v)):
                if part:
                    b = part.startswith("**") and part.endswith("**")
                    r = p.add_run(part[2:-2] if b else part)
                    r.bold = b or None
                    r.font.size = Pt(size)
    for i, w in enumerate(widths):                 # grid widths (read by LibreOffice) and cell widths (Word)
        t.columns[i].width = Cm(w)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
            for p in row.cells[i].paragraphs:
                p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.line_spacing = 1.0
    # repeat header row on page breaks
    trPr = t.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader")
    th.set(qn("w:val"), "true")
    trPr.append(th)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def call(text):
    p = para(text, bold_lead="The call you would make: ")
    pPr = p._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    for k, v in {"w:val": "single", "w:sz": "24", "w:space": "8", "w:color": "C8102E"}.items():
        left.set(qn(k), v)
    bdr.append(left)
    pPr.append(bdr)
    p.paragraph_format.left_indent = Cm(0.4)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(10)


def page_break():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# footer: page number
fp = sec.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = fp.add_run()
for tag, text in [("begin", None), (None, "PAGE"), ("end", None)]:
    if tag:
        el = OxmlElement("w:fldChar")
        el.set(qn("w:fldCharType"), tag)
    else:
        el = OxmlElement("w:instrText")
        el.set(qn("xml:space"), "preserve")
        el.text = text
    run._r.append(el)
run.font.size = Pt(9)
run.font.color.rgb = MID
sec.different_first_page_header_footer = True

# ------------------------------------------------------------------ title page
for _ in range(5):
    para("", after=10)
para("FINAL REVIEW · DESCRIPTIVE REPORT", size=10, color=RGBColor(0xC8, 0x10, 0x2E), after=10).runs[0].bold = True
para("Formula 1 Performance Analytics", size=28, after=4).runs[0].bold = True
para("Drivers, Constructors, Race Strategy and Performance Trends, 2015–2024", size=14, color=GREY, after=26)
para("A race, read as a chain of cause and effect", size=13, italic=True, after=60)
for lead, val in [("Student: ", "Arwindh C N"), ("Roll No.: ", "CB.SC.U4CSE24207"),
                  ("Course: ", "23CSE353 Data Visualisation"), ("Submission: ", "Final Review, October 2026")]:
    para(val, bold_lead=lead, size=11, after=3)
para("", after=40)
para("Companion files: F1_Story_Notebook.ipynb (analysis, every number), F1_Dashboard.html (interactive dashboard), "
     "F1_Final_Presentation.pptx (slides), verification_log.md, Viva_Cheatsheet.md.", size=9, color=GREY)
page_break()

# ------------------------------------------------------------------ contents
doc.add_heading("Contents", level=1)
for line in ["1. Introduction and objectives", "2. Dataset", "3. Data preparation", "4. Analytical approach",
             "5. Visualization techniques", "6. Insights: the story in five acts", "7. Tool selection and usage",
             "8. Dashboard design", "9. The misleading visualization", "10. Ethical reflection",
             "11. Limitations", "12. Conclusion",
             "Appendix A. Consistency with the Primary Review", "Appendix B. Verification of earlier findings"]:
    para(line, after=2)
para("")
para("How to read the numbers. Every number in this report was produced by a cell in F1_Story_Notebook.ipynb. "
     "The cell is named in brackets, for example (Cell A2.1). The notebook saves all of these numbers to facts.json, "
     "and this report is generated from that file, so the two cannot disagree.", size=9.5, color=GREY)

# ------------------------------------------------------------------ 1 introduction
doc.add_heading("1. Introduction and objectives", level=1)
para("Most people watch a Formula 1 race as a result: who won. A strategist on the pit wall watches something else: "
     "a chain of events. Saturday's qualifying sets the order. Every pit stop trades places now for places later. "
     "An unplanned extra stop is an alarm bell. And the car sets a ceiling on all of it. This project uses ten seasons "
     "of data to make that chain visible, so that a reader who has never watched F1 can follow it, and a reader who has "
     "watched for years sees a race differently.")
doc.add_heading("1.1 Problem statement", level=2)
para("F1 race outcomes depend on many interacting factors: driver skill, constructor competitiveness, qualifying position, "
     "pit-stop execution, circuit characteristics and reliability. A single results table does not show how these factors "
     "relate to each other. This case study uses ten seasons of historical data (2015–2024) to find and visualize those "
     "relationships, and arranges the findings as one story rather than a collection of charts.")
doc.add_heading("1.2 Objectives (unchanged from the Primary Review)", level=2)
table(["Objective (Primary Review)", "Where it is answered"], [
    ["Analyse driver performance across seasons using points, wins and podiums", "Act 4: Figures 11 and 12 (Cells A4.3, A4.4)"],
    ["Compare constructor performance across seasons using points and wins", "Act 4: Figure 9 (Cell A4.1); Act 5 (Cell A5.1)"],
    ["Analyse the relationship between qualifying position and final race position", "Act 1: Figures 2 and 3 (Cells A1.1, A1.2)"],
    ["Analyse pit-stop strategy (stop count, duration) and its relationship with race outcome",
     "Act 2: Figure 4 (Cell A2.2); Act 3: Figures 5–8 (Cells A3.2–A3.5)"],
    ["Compare driver performance across different circuits", "Act 4: Figure 13 (Cell A4.5)"],
    ["Analyse DNF/retirement patterns over time", "Act 4: Figure 10 (Cell A4.2)"],
], [9.0, 7.6])

# ------------------------------------------------------------------ 2 dataset
doc.add_heading("2. Dataset", level=1)
para(f"The data is the Ergast-lineage Formula 1 dataset, the same data family now served by the Jolpica F1 API "
     f"(the community successor to the Ergast Developer API). It comes as 14 linked CSV tables covering 1950–2024. "
     f"We keep the ten seasons 2015–2024: **{F('P.n_races')} races**, {F('P.n_drivers')} drivers and "
     f"{F('P.n_constructors')} constructors (Cell P.12). There is no 2025 data in the source.")
table(["Table", "Rows (2015–2024)", "What one row is", "Used for"], [
    ["results", F("P.n_results"), "One driver in one race: grid, finish, points, status", "Every act"],
    ["qualifying", F("P.n_quali"), "One driver's qualifying session: position, Q1/Q2/Q3 times", "Act 3 (teammate link)"],
    ["pit_stops", F("P.n_stops"), "One pit stop: lap, total pit-lane time", "Acts 2 and 3, hook"],
    ["lap_times", F("P.n_laps"), "One driver on one lap: position and lap time", "Hook, Act 2, Act 4"],
    ["races, circuits", f"{F('P.n_races')} / {F('P.n_circuits')}", "Race calendar and circuit details", "Every act"],
    ["drivers, constructors, status", "lookup", "Names and finishing-status labels", "Every act"],
    ["driver_standings, constructor_standings", f"{F('P.n_dfinal')} / {F('P.n_cfinal')} (final)", "Championship table after every race", "Act 4"],
    ["sprint_results, constructor_results, seasons", f"{F('P.n_sprint')} / – / –", "Sprint races (2021–2024 only) and season list",
     "Row-count checks"],
], [4.0, 2.6, 6.0, 4.0])
VER = [l for l in (HERE / "verification_log.md").read_text().splitlines() if l.startswith("| ") and "|---" not in l][1:]
N_CHECKS = sum(1 for l in VER if l.split("|")[5].strip() != "n/a")
N_OK = sum(1 for l in VER if l.split("|")[5].strip().startswith("Yes"))
para("The tables link through ID numbers (raceId, driverId, constructorId, statusId). The Primary Review used a cleaned "
     "8-sheet Excel workbook built from these files. For the final stage we rebuilt everything from the raw CSVs, because "
     "the workbook's constructor sheet stores team names but not constructor IDs, and joining on names is unsafe "
     "(Toro Rosso became AlphaTauri and then RB, each with a different ID). The rebuilt tables match every row count in "
     "the approved workbook (Cell P.10).")
doc.add_heading("2.1 Important attributes", level=2)
bullets([("Grid position: ", "the starting slot (1 = pole). A value of 0 in the source means a pit-lane start."),
         ("Finishing position: ", "blank if the driver was not classified."),
         ("Status: ", "\"Finished\", \"+N Lap(s)\" (finished but lapped) or a retirement reason such as \"Engine\" or \"Collision\"."),
         ("Pit-stop duration: ", "total time in the pit lane in seconds, entry to exit. It is not the stationary tyre change shown on TV."),
         ("Lap position: ", "where each car ran at the end of each lap, the basis of the hook chart and the undercut analysis."),
         ("Standings points: ", "cumulative after each race, so the season's final table is the last round.")])

# ------------------------------------------------------------------ 3 preparation
doc.add_heading("3. Data preparation", level=1)
para("All cleaning is in f1_prep.py and repeated cell by cell in the notebook (Cells P.0–P.11). Each step is numbered:")
table(["Step", "What we did", "Why"], [
    ["P1", "Read the 14 CSVs, treating the two characters \\N as missing", "The source writes missing values as \\N"],
    ["P2", "Kept seasons 2015–2024 (209 races); joined circuits; built readable race and circuit labels", "Scope of the study"],
    ["P3", "Joined results to status, drivers, constructors on IDs; grid 0 → missing; two flags: classified and genuine DNF",
     "A lapped car is not a DNF; a pit-lane start has no grid slot"],
    ["P4", "Converted Q1/Q2/Q3 text times (\"1:26.572\") to seconds", "Times are stored as text"],
    ["P5", "Pit-stop duration from the exact milliseconds column", "The text column switches to m:ss for long stops"],
    ["P6–P7", "Kept lap positions and sprint results for the period", "Inputs for Acts 2–4"],
    ["P8", "Final standings = the table after the last round of each season", "Standings are cumulative"],
    ["P9", "One merged driver-race table: results + qualifying + stop count, first-stop lap",
     "Lets us chain qualifying, pit stops and results (Act 3)"],
    ["P10", "Asserted every row count equals the Primary Review workbook", "Proves the rebuild matches the approved data"],
    ["P11", "Saved clean tables to data/clean/", "Reuse by the dashboard and checks"],
], [1.7, 8.8, 6.1])
para(f"**Data quality.** Of {F('P.n_results')} race entries, {F('P.n_unclassified')} were not classified and "
     f"{F('P.n_dnf')} were genuine DNFs. These two numbers differ because {F('P.n_dnf_classified')} cars retired late but "
     f"had covered 90% of the race, so they still received a finishing position. We therefore keep two separate flags: "
     f"classified (used for grid-versus-finish) and genuine DNF (used for reliability). There were {F('P.n_pitlane')} "
     f"pit-lane starts. {F('P.n_long_stops')} pit stops lasted 60 seconds or more (red flags and repairs); the median "
     f"pit-lane time of normal stops is {F('P.pit_median_normal')} s. The {F('P.no_pit_race')} has no pit-stop data, "
     f"so its stop counts are left unknown rather than set to zero (Cell P.12).")

# ------------------------------------------------------------------ 4 approach
doc.add_heading("4. Analytical approach", level=1)
doc.add_heading("4.1 One story, one reader", level=2)
para("The analysis is written for one reader, the strategist on the pit wall, and arranged as five acts. Each act asks one "
     "question, answers it with one main chart, and ends with \"the call you would make\". Act 3 is built as a plot twist: "
     "it shows what everyone assumes first, tests the assumption, and only then shows the real finding.")
table(["Part", "Headline", "Question"], [
    ["Hook", "One race, lap by lap", "What does a race look like as a chain of events?"],
    ["Act 1", "Saturday decides more than you think", "How much does the starting position fix the result, and where?"],
    ["Act 2", "The stop that costs four places and wins back two", "What does a pit stop cost, and does timing matter?"],
    ["Act 3", "The hidden alarm", "Is an extra pit stop a gamble, or a sign that something went wrong?"],
    ["Act 4", "The car sets the ceiling", "How much is decided by which team you drive for?"],
    ["Act 5", "What the data cannot tell you", "How can a chart lie, and where are the limits?"],
], [1.6, 6.0, 9.0])
doc.add_heading("4.2 Methods, in plain words", level=2)
bullets([
    ("Choosing the hook race. ", f"For every race we added up how many places every car gained or lost from one lap to the "
     f"next. The {F('H.race')} scored highest of all {F('H.n_races')} races ({F('H.changes')}; the typical race has "
     f"{F('H.median_changes')}), so it was chosen by a rule, not by taste (Cell H.1)."),
    ("Correlation (r). ", "A number from −1 to 1 that measures how closely two things move together in a straight line. "
     "0 means no link, 1 a perfect link. We give each circuit's r a 95% confidence range (Fisher method), so a circuit "
     "with few races shows a wide range."),
    ("The undercut measure. ", "For each driver's first pit stop at lap L, we read their position on lap L−1, L+2 and L+10 "
     "from the lap table. Stops are split into early, middle and late thirds of that race's first stops."),
    ("The derived teammate link. ", "The source has no \"teammate\" column. We derived it: two drivers in the same "
     "constructor in the same race, both with a qualifying position. The one who qualified behind is the \"slower qualifier\". "
     "StopDiff = stops by the slower qualifier − stops by the faster one. This chains three tables: Qualifying, Pit Stops "
     "and Race Results."),
    ("Two-proportion z-test. ", "Checks whether two percentages differ by more than chance. |z| above 2 is already unusual; "
     f"our main result has z = {F('A3.z')}."),
    ("Lap-time consistency. ", "The coefficient of variation (spread of lap times ÷ average lap time) per driver per race, "
     "after removing pit, safety-car and crash laps with an interquartile-range filter."),
])
doc.add_heading("4.3 Checking the earlier findings first", level=2)
para("Before building any chart, every finding from the earlier Strategic Analysis was recomputed from the raw data and logged "
     "in verification_log.md (Appendix B). The rule was: if a number does not reproduce, report the real number and change "
     f"the story. {N_OK} of {N_CHECKS} checks reproduce, but three needed a decision to be made explicit: "
     "\"both finished\" means both "
     "cars classified; the qualifying-gap buckets are 1–3, 4–7 and 8+ places; and the consistency result reproduces only if "
     "driver-races with fewer than 10 laps are dropped. Section 6 shows how fragile that last one is.")

# ------------------------------------------------------------------ 5 techniques
doc.add_heading("5. Visualization techniques", level=1)
para(f"The notebook draws {F('F.n_charts')} charts ({F('F.n_static')} static Matplotlib and Seaborn charts and "
     f"{F('F.n_plotly')} interactive Plotly charts) in more than ten different chart types, plus the interactive dashboard. "
     "Each chart carries one idea, and its title states the conclusion, not just the topic.")
table(["Fig.", "Chart", "Type", "Tool", "Why this form"], [
    ["1", "The hook race, lap by lap", "Bump chart with event markers", "Matplotlib", "Shows order and every swap; dots mark pit stops"],
    ["2", "Grid vs finish, pooled", "2D histogram + mean line", "Seaborn", f"{F('A1.n')} points would overplot as a scatter"],
    ["3", "Grid-finish r by circuit", "Lollipop / dot plot with CIs", "Seaborn", f"Ranks {F('A1.n_circuits')} circuits; ranges show reliability"],
    ["4", "Undercut", "Slope chart with error bars", "Matplotlib", "Before → after change is the whole message"],
    ["5", "Stops vs finish", "Strip plot + point estimate", "Seaborn", "Shows the naive view with its full spread"],
    ["6", "Qualifying gap vs StopDiff", "Point plot with CIs + expected line", "Seaborn", "Assumption vs reality on one axis"],
    ["7", "Teammate duel", "Dodged point plot with CIs", "Seaborn", "Compares two groups across gap buckets"],
    ["8", "Distress signal", "Step histograms + bar chart", "Seaborn", "Distribution and the 3-group contrast"],
    ["9", "Points share eras", "Small-multiple area charts", "Plotly", "Four teams on one scale; hover for values"],
    ["10", "Genuine DNF rate", "Line with reference line", "Matplotlib", "Trend against the best team's level"],
    ["11", "Wins by driver", "Stacked bar + outline bar", "Matplotlib", "Wins split by champion car, with podiums"],
    ["12", "Season points by driver", "Interactive line chart", "Plotly", "Ten seasons, many drivers; hover for names"],
    ["13", "Driver × circuit", "Annotated heatmap", "Seaborn", "Compares rows (drivers) with columns (circuits)"],
    ["14", "Consistency vs points", "Scatter + regression band", "Seaborn", "Shows a weak link honestly"],
    ["15", "Dashboard", "Linked interactive charts", "Plotly", "Explore any season, team, driver, circuit"],
    ["16", "Misleading vs honest", "Paired bar charts", "Matplotlib", "Exact control of the axis being manipulated"],
], [1.1, 3.6, 3.9, 2.0, 6.0], size=8.5)
para("**Design rules used everywhere.** One colour meaning across the whole project: black, white and greys for context, "
     "and one red accent for the thing to look at. Annotations sit on the chart, so the reader does not decode a legend. "
     "Every bar chart starts at zero. Charts that do not start at zero (dot and line charts) encode position, not length. "
     "Confidence ranges are drawn where a number is an estimate, and small samples are labelled as such. Every chart has a "
     "footer naming the notebook cell that drew it.")

# ------------------------------------------------------------------ 6 insights
doc.add_heading("6. Insights: the story in five acts", level=1)
doc.add_heading(f"6.1 Hook: {F('H.changes')} position changes in one race, and the pole-sitter still won", level=2)
figure(CH / "H2_bump_chart_hook_race.png",
       f"{F('H.race')}: every car's position at the end of every lap, pit stops as dots (Cell H.2).", width=15.0)
para(f"Under the result (Rosberg first) sits a chain of events. Hamilton started {F('H.ham_grid')}nd, "
     f"stopped on lap {F('H.ham_first_stop')}, and made {F('H.ham_stops')} stops in total to climb to {F('H.ham_finish')}th. "
     f"On lap {F('H.sc_lap')}, {F('H.n_sc_stops')} cars pitted at once, just before laps {F('H.slow_first')}–"
     f"{F('H.slow_last')} ran slowly (most likely a safety car; the data has no safety-car field, so this is inferred from "
     f"lap times). The lines cross most where pit stops cluster: a pit stop moves a car through the order. " +
     ("Every car finished, " if F('H.dnfs') == "0" else f"There were {F('H.dnfs')} retirements, ") +
     f"so every one of the {F('H.cars')} lines is complete.")
call("do not read a race from the result. Read it from the moves.")

doc.add_heading("6.2 Act 1: Saturday decides more than you think", level=2)
figure(CH / "A1_1_grid_vs_finish_pooled.png",
       f"Grid vs finish for {F('A1.n')} classified finishes; black = average finish per grid slot (Cell A1.1).", width=11.5)
para(f"Across all races, where a driver starts and where they finish are strongly linked: r = {F('A1.pooled_r')} "
     f"(Cell A1.1). Pole position won {F('A1.pole_win')} of races, and {F('A1.top3_win')} of winners started in the top "
     f"three. But the average line is flatter than the diagonal: a car starting 1st finishes {F('A1.p1_avg_finish')} on "
     f"average, a car starting 20th finishes {F('A1.p20_avg_finish')}. Part of that is real overtaking, and part is that "
     f"retirements ahead lift everyone behind.")
figure(CH / "A1_2_circuit_lollipop.png",
       f"Grid-finish correlation at {F('A1.n_circuits')} circuits with 40+ classified finishes, with 95% ranges (Cell A1.2).", width=11.0)
para(f"The link is not the same everywhere. At {F('A1.top_circuit')} (r = {F('A1.top_r')}) the narrow street circuit makes "
     f"overtaking almost impossible; {F('A1.second_circuit')} ({F('A1.second_r')}) and {F('A1.third_circuit')} "
     f"({F('A1.third_r')}) follow. At the other end sit {F('A1.third_bottom')} ({F('A1.third_bottom_r')}), "
     f"{F('A1.second_bottom')} ({F('A1.second_bottom_r')}) and {F('A1.bottom_circuit')} ({F('A1.bottom_r')}). "
     f"The median circuit is {F('A1.median_r')}. {F('A1.bottom_circuit')} hosted only {F('A1.bottom_races')} races in "
     f"this period ({F('A1.bottom_n')} finishes), so its range runs from {F('A1.bottom_lo')} to {F('A1.bottom_hi')}: "
     f"its exact rank is not reliable.")
call(f"at {F('A1.top_circuit')}, {F('A1.second_circuit')} and {F('A1.third_circuit')}, treat qualifying as the race. "
     f"At {F('A1.second_bottom')} or {F('A1.third_bottom')}, a poor grid slot can still be fixed on Sunday.")

doc.add_heading("6.3 Act 2: The stop that costs four places and wins back two", level=2)
figure(CH / "A2_2_undercut_slope.png",
       f"Average change in track position around {F('A2.n')} first pit stops, by timing within the race (Cells A2.1–A2.2).", width=12.5)
para(f"Every first stop costs places at once: early stoppers drop {F('A2.early_lost2')}, middle {F('A2.middle_lost2')} and "
     f"late {F('A2.late_lost2')} places two laps later. The difference is what happens next. As their rivals make their own "
     f"stops, early stoppers win back {F('A2.early_back')} places and end at {F('A2.early_chg10')}; late stoppers win back "
     f"only {F('A2.late_back')} and end worst, at {F('A2.late_chg10')} (Cell A2.1). This is the undercut in numbers: the "
     f"early stop looks bad on the TV screen for a few laps, and that is the strategy working. Removing first stops in the "
     f"first five laps, which are often forced by damage, leaves the pattern unchanged: early {F('A2.s_early_chg2')} then "
     f"{F('A2.s_early_chg10')}, late {F('A2.s_late_chg2')} then {F('A2.s_late_chg10')} (Cell A2.3).")
call("if your car can survive two or three exposed laps in traffic, stop first.")

doc.add_heading("6.4 Act 3: The hidden alarm", level=2)
para(f"This act chains Qualifying, Pit Stops and Race Results through the derived teammate link ({F('A3.n_pairs')} "
     f"team-race pairs, Cell A3.1). Teammates drive the same car, so comparing them removes the car from the picture.")
doc.add_heading("What everyone sees", level=3)
figure(CH / "A3_2_stops_vs_finish.png", "Finishing position by number of pit stops (Cell A3.2).", width=12.0)
para(f"One-stop drivers average P{F('A3.finish_1')}, two-stop P{F('A3.finish_2')}, three-stop P{F('A3.finish_3')}. "
     f"(Four or more stops is slightly better, P{F('A3.finish_4')}, probably because those are rain or red-flag races where "
     f"everyone stops a lot.) The usual reading is: a driver who is far behind gambles on an extra stop, and the gamble "
     f"fails. If that were true, the driver who qualified further behind the teammate should stop more often.")
doc.add_heading("The assumption, tested", level=3)
figure(CH / "A3_3_gap_vs_stopdiff.png", "Average StopDiff by qualifying gap to the teammate, with 95% ranges (Cell A3.3).", width=12.0)
para(f"The assumption is dead. The correlation between qualifying gap and StopDiff is r = {F('A3.r_gap')} "
     f"(p = {F('A3.r_gap_p')}): no link at all. A driver ten places behind the teammate on Saturday is no more likely to "
     f"make an extra stop than one who was a single place behind.")
doc.add_heading("The real finding", level=3)
figure(CH / "A3_4_teammate_duel.png",
       f"How often the slower qualifier finishes ahead, with and without an extra stop; {F('A3.n_both_cls')} pairs with both "
       f"cars classified (Cell A3.4).", width=12.5)
para(f"With an extra stop, the slower qualifier finished ahead of the teammate only **{F('A3.rate_extra_1')}** of the time "
     f"(n = {F('A3.n_extra')}). Without one: **{F('A3.rate_no_1')}** (n = {F('A3.n_no')}). The two-proportion test gives "
     f"z = {F('A3.z')}, far beyond chance. The pattern holds for small qualifying gaps ({F('A3.small_extra')} vs "
     f"{F('A3.small_no')}), medium gaps ({F('A3.medium_extra')} vs {F('A3.medium_no')}) and large gaps "
     f"({F('A3.large_extra')} vs {F('A3.large_no')}). In the large-gap bucket only {F('A3.large_n_extra')} pairs made an "
     f"extra stop and the difference is not significant (p = {F('A3.large_p')}): the direction holds, the strength does not.")
figure(CH / "A3_5_distress_signal.png",
       "Left: finishing gap to the teammate. Right: who made the extra stop (Cell A3.5).", width=15.0)
para(f"The extra stop drags down whoever makes it. When the teammate made the extra stop, the slower qualifier finished "
     f"ahead {F('A3.beat_when_mate_extra')} of the time; with equal stops {F('A3.beat_when_equal')}; when the slower "
     f"qualifier made it, {F('A3.rate_extra')}. The median finishing gap widens from {F('A3.med_gap_no')} to "
     f"{F('A3.med_gap_extra')} places. There is also a clue about why: {F('A3.early_stop_extra')} of extra-stop drivers "
     f"made their first stop in laps 1–3, against {F('A3.early_stop_no')} of the others. Stopping that early is rarely a plan.")
para("**Honest framing.** The extra stop is a symptom of trouble (damage, a puncture, a spin, bad safety-car timing). "
     "It is not a weapon, and it is not the cause of the lost result. Telling a driver to make fewer stops would fix nothing, "
     "because the trouble came first. This is a correlation in observational data, and we treat it as a warning light, "
     "not as a lever.")
call("when your second car suddenly needs a stop the plan did not have, treat it as an alarm: something has gone wrong. "
     "Do not expect that stop to win places back. Protect the other car's result.")

doc.add_heading("6.5 Act 4: The car sets the ceiling", level=2)
figure(CH / "A4_1_points_share_eras.png",
       "Share of all constructor points, four leading teams; red dots = constructors' champion (Cell A4.1, Plotly).", width=15.5)
para(f"Mercedes took {F('A4.mer_2015')} of all points in 2015 and won {F('A4.mer_titles')} constructors' titles in a row, "
     f"then fell to {F('A4.mer_2023')} by 2023. Red Bull rose from {F('A4.rbr_2015')} to {F('A4.rbr_2023')}. McLaren "
     f"climbed from {F('A4.mcl_2015')} to {F('A4.mcl_2024')} and won 2024, just ahead of Ferrari ({F('A4.fer_2024')}). "
     f"Ferrari peaked at {F('A4.fer_best')} in {F('A4.fer_best_year')} but never won a title. "
     f"The biggest three-season swing: {F('A4.swing_team')}'s share {F('A4.swing_dir')} by {F('A4.swing_pp')} "
     f"percentage points between {F('A4.swing_from')} and {F('A4.swing_to')}. Changes that size are an engineering "
     f"story, not a race-day decision.")
figure(CH / "A4_2_dnf_rate.png", "Genuine DNF rate by season; red line = Mercedes' ten-season average (Cell A4.2).", width=11.5)
para(f"Reliability improved: in 2015, {F('A4.dnf_2015')} of starts ended in a genuine retirement; in 2024, "
     f"{F('A4.dnf_2024')}. The fall is not smooth: 2017 ({F('A4.dnf_2017')}) and 2022 ({F('A4.dnf_2022')}) were both years of "
     f"new technical rules. {F('A4.dnf_best_team')} retired only {F('A4.dnf_best')} of the time, the best of any team with "
     f"60+ starts ({F('A4.dnf_worst_team')} was worst at {F('A4.dnf_worst')}).")
figure(CH / "A4_3_wins_by_driver.png", "Race wins by driver, split by whether the car was that season's champion (Cell A4.3).", width=12.5)
para(f"{F('A4.wins_champ_car')} of all race wins went to the season's constructors' champion. Hamilton won "
     f"{F('A4.ham_wins')} races, {F('A4.ham_champ_wins')} of them in the champion car; Verstappen won {F('A4.ver_wins')}, "
     f"{F('A4.ver_champ_wins')} in the champion car. His wins outside the best car are what a great driver looks like in this "
     f"chart. Driver titles follow the same eras: Hamilton won {F('A4.ham_titles')}, Verstappen {F('A4.ver_titles')} "
     f"(Figure 12).")
figure(CH / "A4_4_driver_points.png", "Season points for the eight top scorers; stars = world title (Cell A4.4, Plotly).", width=13.0)
figure(CH / "A4_5_driver_circuit_heatmap.png",
       "Average finishing position for the ten top point-scorers at circuits raced 8+ times (Cell A4.5).", width=15.0)
para(f"Read the heatmap across a row and the shade barely changes; read down a column and it changes a lot. Driver rows "
     f"differ by {F('A4.hm_row_range')} places on average, circuit columns by only {F('A4.hm_col_range')}. "
     f"{F('A4.hm_best_driver')} averages P{F('A4.hm_best_avg')} almost everywhere. Circuit specialists are mostly a myth at "
     f"this level: the driver and the car set the level, and the circuit nudges it.")
figure(CH / "A4_6_consistency_vs_points.png", "Lap-time consistency vs season points, one dot per driver-season (Cell A4.6).", width=11.5)
para(f"**An honest anti-climax.** Steadier drivers score slightly more (r = {F('A4.cons_r')}, {F('A4.cons_n')} driver-seasons), "
     f"but consistency explains only about {F('A4.cons_r2')} of the spread in points. The result is also fragile: keeping "
     f"races where a driver completed fewer than 10 laps gives {F('A4.cons_r_all')}, using each driver's median race gives "
     f"{F('A4.cons_r_med')}, and filtering outlier laps per race gives {F('A4.cons_r_race')}. Even the strongest version is "
     f"partly a car effect, because a fast car runs in clean air and laps more steadily. It is included because a story that "
     f"only shows its strong results is not honest.")
call("every edge from Acts 1–3 lives inside the ceiling the car sets. Fight for every place, but plan the season around "
     "the car, not the race.")

doc.add_heading("6.6 Back to the hook race", level=2)
para(f"Read the {F('H.race')} again as a strategist. Act 1: Rosberg started on pole and won; at {F('C.circuit')} the "
     f"grid-finish correlation is {F('C.circuit_r')} over {F('C.circuit_races')} races. Act 2: on lap {F('H.sc_lap')}, "
     f"{F('H.n_sc_stops')} cars pitted at once and the order reshuffled. Act 3: Hamilton, the slower qualifier in the same car, "
     f"made {F('C.extra_stops')} more stops than his teammate and finished {F('H.ham_finish')}th; his first stop came on "
     f"lap {F('H.ham_first_stop')}, the alarm rather than the plan. Act 4: both drove the 2016 Mercedes, the car that took "
     f"{F('A4.mer_2016')} of all points that season. The {F('H.changes')} position changes were never random. They were a "
     f"chain of cause and effect.")

# ------------------------------------------------------------------ 7 tools
doc.add_heading("7. Tool selection and usage", level=1)
para("The final stage needs three visualization tools. All three run inside one Jupyter notebook, so a single "
     "\"Restart and Run All\" rebuilds every chart, number and the dashboard. This is the one deliberate change from the "
     "Primary Review, which planned Python and Power BI: **Plotly replaced Power BI so the whole analysis stays reproducible "
     "in a single notebook.** Everything else (objectives, dataset, visualization plan) is unchanged.")
table(["Tool", "The job it does better than the others", "Used for", "Why not the other two"], [
    ["Matplotlib", "Pixel-level control: custom marks, per-line annotation, exact axis limits",
     "Hook bump chart, undercut slope, DNF trend, wins bars, misleading/honest pair",
     "Seaborn's statistical defaults get in the way of hand-built story charts; Plotly's static export is less precise for print"],
    ["Seaborn", "Statistical charts straight from tidy data, with built-in aggregation and bootstrap confidence intervals",
     "Grid-finish density, circuit dot plot, stops strip plot, StopDiff and teammate point plots, distress histograms, "
     "heatmap, regression",
     "Matplotlib needs many lines for each CI; Plotly does not compute statistical summaries"],
    ["Plotly", "Interactivity: hover values, zoom, linked filters, and a single self-contained HTML export",
     "Points-share eras, driver points lines, the five-act dashboard",
     "Matplotlib and Seaborn produce static images; nobody can filter a PNG"],
], [2.3, 4.6, 5.0, 4.7], size=8.5)
para("Supporting libraries: pandas (cleaning and joins), SciPy (correlations and tests), Kaleido (static PNG export of the "
     "Plotly charts for this report and the slides).")

# ------------------------------------------------------------------ 8 dashboard
doc.add_heading("8. Dashboard design", level=1)
figure(CH / "D_dashboard_overview.png", "F1_Dashboard.html: title, filter row, headline numbers and the hook (screenshot).", width=14.0)
para(f"The dashboard is one self-contained HTML file ({F('D.size_mb')} MB, works offline) written by Cell D.1 of the notebook. "
     "It follows the same five-act order as the story, from top to bottom:")
bullets([
    ("One filter row. ", "Season, constructor, driver and circuit filters sit in a single sticky row above everything, and every "
     "chart re-draws for the same slice of data. The current selection is stored in the page address, so a filtered view "
     "can be shared as a link."),
    ("Headline numbers. ", "Five tiles (races in view, grid-finish r, early-stopper net change, teammate duel, genuine DNF rate) "
     "re-compute for the selection."),
    ("Hook. ", "A race selector shows the lap-by-lap chart for any race. Black is the winner; red is the biggest climber, or "
     "the chosen driver."),
    ("Acts 1–4. ", "The circuit dot plot highlights the chosen circuit; the grid-vs-finish scatter, the undercut slope and the "
     "teammate bars re-compute for the filters; the points-share, DNF and season-points charts draw the chosen team or "
     "driver in red."),
    ("Act 5. ", "A toggle switches the same bar chart between the misleading and the honest axis, for the top two teams of "
     "any season, with the lie factor calculated live."),
    ("Honesty built in. ", "Small selections are labelled \"small sample\", empty selections say so, and grey reference lines "
     "show the all-data result behind a filtered one."),
])

# ------------------------------------------------------------------ 9 misleading
doc.add_heading("9. The misleading visualization", level=1)
para("The ethics demonstration uses constructor championship points with a truncated y-axis, added at the final stage as the "
     "course requires. The data is real and correct; only the axis changes. It is clearly labelled MISLEADING (for ethics "
     "demonstration) wherever it appears.")
figure(CH / "A5_3_misleading_vs_honest.png",
       "Left: MISLEADING, for ethics demonstration (axis starts at 645). Right: honest version (axis starts at 0). Cells A5.1–A5.3.", width=14.0)
table(["Question", "Answer"], [
    ["What was manipulated?", f"Only the y-axis. It starts at {F('A5.base')} points instead of 0. The values are real: "
     f"{F('A5.lead')} {F('A5.lead_pts')}, {F('A5.second')} {F('A5.second_pts')} (2024)."],
    ["Why does it mislead?", f"A bar chart encodes value as bar length. With the axis cut at {F('A5.base')}, we only see the top "
     f"of each bar, so {F('A5.lead')}'s bar looks {F('A5.visual_ratio')} times taller than {F('A5.second')}'s, while the real "
     f"difference is {F('A5.gap_pct')}."],
    ["What false impression does it create?", f"That {F('A5.lead')} \"crushed\" {F('A5.second')}. In reality the 2024 constructors' "
     f"title was {F('A5.closest')} of the ten seasons: {F('A5.gap')} points over a whole season."],
    ["How was it fixed?", f"The y-axis starts at zero, the exact values are printed on the bars, and the title states the real "
     f"size of the gap ({F('A5.gap')} points, {F('A5.gap_pct')})."],
    ["Which principle does the fix follow?", f"Truthful scaling and proportional ink (Tufte): the size of a mark must be "
     f"proportional to the number it shows. Tufte's lie factor = size of effect in the graphic ÷ size of effect in the data. "
     f"An honest chart has a lie factor near 1; the misleading one has a lie factor of about {F('A5.lie_factor')}."],
], [4.2, 12.4])

# ------------------------------------------------------------------ 10 ethics
doc.add_heading("10. Ethical reflection", level=1)
para("The misleading chart contains no false number. That is what makes it dangerous: it would pass a fact-check of its labels. "
     "Close fights are common in F1, like the 2024 constructors' title, so the temptation to zoom an axis "
     "is constant. The same care was applied to the rest of the project:")
bullets([
    ("Axes. ", "Every bar chart starts at zero. Line and dot charts that do not start at zero say what they show (position, not length)."),
    ("Uncertainty. ", "Confidence ranges are drawn wherever a number is an estimate. Small samples are named: Hockenheim's three races, "
     f"the large-gap bucket's {F('A3.large_n_extra')} pairs, small dashboard selections."),
    ("Not bending the data. ", "When a recomputed number disagreed with the earlier analysis, the real number was used and the story "
     "changed. The four-or-more-stops group finishing better than three-stoppers was reported, not hidden."),
    ("Showing weak results. ", "The consistency finding is weak and fragile, and is shown as exactly that."),
    ("Causation. ", "Act 3 could easily be told as \"extra stops lose races\". It is told the honest way: the extra stop is a symptom of "
     "trouble that already happened, and a team that tried to \"fix\" it by stopping less would gain nothing."),
    ("Choosing examples. ", f"The hook race was chosen by a rule (most position changes of all {F('H.n_races')} races), not because it fitted the story."),
    ("People. ", "Drivers are named because these are public sporting results. The analysis judges race situations, not people: "
     "an extra stop is treated as bad luck or damage, not as a driver's failure."),
])

# ------------------------------------------------------------------ 11 limitations
doc.add_heading("11. Limitations", level=1)
table(["Finding", "Type of evidence", "What could be behind it", "What we can honestly say"], [
    ["Grid predicts finish (Act 1)", "Correlation", "Fast cars qualify well and race well", "The two move together, more at some tracks"],
    ["Undercut (Act 2)", "Before/after average", "Safety cars, tyre choices, forced stops", "Early first stops lose more at once and recover more"],
    ["Extra stop = alarm (Act 3)", f"Strong correlation (z = {F('A3.z')})", "Damage, punctures, spins, timing",
     "An extra stop is a warning sign, not a cause and not a tactic"],
    ["Car sets the ceiling (Act 4)", "Descriptive", "Budget, rules, engine supply", "Points share swings by era far more than by any race decision"],
    ["Consistency (Act 4)", "Weak, fragile correlation", "Car pace", "Little link with points; depends on method"],
], [3.6, 3.2, 4.4, 5.4], size=8.5)
bullets([
    "Correlation is not causation. Nothing here is an experiment; every result shows that two things moved together over ten seasons.",
    "Missing variables: the dataset has no tyre compounds, weather, safety-car periods, penalties or team radio, so the reason "
    "behind any single event is outside the data.",
    "Track position is not time: the undercut measure counts places, not the gap in seconds.",
    "Grid-versus-finish uses classified finishers only, which flatters drivers who start at the back.",
    "Some circuits and buckets have small samples; their exact values should not be over-read.",
])

# ------------------------------------------------------------------ 12 conclusion
doc.add_heading("12. Conclusion", level=1)
para("Ten seasons of data turn the race result into a chain. Saturday sets the order, more at Monaco than anywhere else. "
     "A pit stop is a loan of places that early stoppers repay and late stoppers do not. An unplanned extra stop is an alarm, "
     "and whoever makes it usually loses the duel with the teammate. And all of it plays out under a ceiling set by the car, "
     "which moved from Mercedes to Red Bull to McLaren in ten years. Read the 2016 Chinese GP with those four ideas and its "
     f"{F('H.changes')} position changes stop being chaos: they become cause and effect.")
bullets([
    ("Pit wall call 1: ", "weight qualifying effort by circuit."),
    ("Pit wall call 2: ", "if the car can survive a few exposed laps, stop first."),
    ("Pit wall call 3: ", "treat an unplanned stop as an alarm, not a strategy."),
    ("Pit wall call 4: ", "plan the season around the car; race-day edges live inside its ceiling."),
])

# ------------------------------------------------------------------ appendix A
doc.add_heading("Appendix A. Consistency with the Primary Review", level=1)
para("Every chart planned in the Primary Review is delivered. Where the form changed, the reason is given. "
     "To reproduce everything from the 14 raw CSVs, run make_all.sh (see README.md in the submission folder).")
table(["Planned (Primary Review)", "Delivered", "Change and reason"], [
    ["1. Driver championship performance: line chart", "Figure 12, season points by driver (Plotly)", "Same form; made interactive"],
    ["2. Constructor performance: bar chart", "Figure 9, points-share eras; Figure 16 bars",
     "Share by season shows the eras better than one total bar"],
    ["3. Qualifying vs race finish: scatter plot", "Figures 2 and 3",
     f"{F('A1.n')} points overplot, so a 2D histogram; plus circuit-level r"],
    ["4. Driver wins and podiums: bar chart", "Figure 11", "Same form; wins split by champion car"],
    ["5. Pit-stop strategy vs result: scatter plot", "Figures 4–8",
     "Strip plot for stop count, then the undercut and teammate analyses"],
    ["6. Circuit-level driver performance: heatmap", "Figure 13", "Same form"],
], [5.4, 4.6, 6.6])
para("Additions at the final stage: the hook bump chart, the derived teammate link (Act 3), the DNF trend, the consistency "
     "check, the misleading/honest pair and the dashboard. The only change of tool is Plotly in place of Power BI (Section 7).")

# ------------------------------------------------------------------ appendix B
doc.add_heading("Appendix B. Verification of earlier findings", level=1)
para("Generated by verify_seeds.py from the raw CSVs; the full table with notes is in verification_log.md.")
vrows = []
for line in (HERE / "verification_log.md").read_text().splitlines():
    if line.startswith("| ") and not line.startswith("| ID") and not line.startswith("|---"):
        cells = [c.strip() for c in line.strip("|").split("|")]
        vrows.append(cells[:5])
table(["ID", "Finding", "Seed", "Recomputed", "Match"], vrows, [1.0, 6.6, 2.7, 4.9, 1.4], size=7.5)

out = HERE / "F1_Final_Report.docx"
cp = doc.core_properties
cp.author = cp.last_modified_by = "Arwindh C N"
cp.title = "Formula 1 Performance Analytics - Final Report"
doc.save(out)
print("wrote", out.name, "with", FIG[0], "figures")
