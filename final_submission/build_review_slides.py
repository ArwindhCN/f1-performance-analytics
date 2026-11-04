"""
Builds F1_Review_Presentation.pptx: the presentation laid out along the case-study marking sections
(Section 1: problem, dataset, cleaning; Section 2: tools, visualizations, dashboard, misleading chart, findings;
Section 3: recommendations), using the story charts. Every number comes from facts.json.
Run after make_notebook.sh:  python build_review_slides.py
"""
import json
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
FACTS = json.loads((HERE / "facts.json").read_text())
SL, CH = HERE / "charts" / "slides", HERE / "charts"


def F(k):
    return FACTS[k]["text"]


INK, INK2, MUTED, RED = RGBColor(0x1A, 0x1A, 0x1A), RGBColor(0x4D, 0x4D, 0x4D), RGBColor(0x76, 0x76, 0x76), RGBColor(0xC8, 0x10, 0x2E)
WHITE, CARD, DARK, SOFT, ROW = (RGBColor(0xFF, 0xFF, 0xFF), RGBColor(0xF2, 0xF2, 0xF2), RGBColor(0x11, 0x11, 0x11),
                                RGBColor(0xBB, 0xBB, 0xBB), RGBColor(0xFA, 0xFA, 0xFA))
FONT = "Arial"
N = 16

# The visualization register used on the slides (V-numbers), in story order.
VIS = {1: ("Bump chart with pit-stop markers", "Matplotlib"), 2: ("2D histogram with mean line", "Seaborn"),
       3: ("Lollipop with 95% ranges", "Seaborn"), 4: ("Slope chart with error bars", "Matplotlib"),
       5: ("Strip plot with mean and CI", "Seaborn"), 6: ("Point plot vs expected trend", "Seaborn"),
       7: ("Dodged point plot with CIs", "Seaborn"), 8: ("Step histograms and bar chart", "Seaborn"),
       9: ("Small-multiple area charts", "Plotly"), 10: ("Trend line with reference line", "Matplotlib"),
       11: ("Stacked bars with podium outline", "Matplotlib"), 12: ("Interactive line chart", "Plotly"),
       13: ("Annotated heatmap", "Seaborn"), 14: ("Scatter with regression band", "Seaborn"),
       15: ("Misleading vs corrected bar pair", "Matplotlib")}

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


# ------------------------------------------------------------------ helpers
def text(slide, x, y, w, h, runs, size=14, color=INK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         spacing=None):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    for i, para in enumerate(runs if isinstance(runs, list) else [runs]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if spacing:
            p.space_after = Pt(spacing)
        for t, o in (para if isinstance(para, list) else [(para, {})]):
            r = p.add_run()
            r.text = t
            r.font.name = FONT
            r.font.size = Pt(o.get("size", size))
            r.font.bold = o.get("bold", bold)
            r.font.italic = o.get("italic", False)
            r.font.color.rgb = o.get("color", color)
    return tb


def card(slide, x, y, w, h, fill=CARD):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.adjustments[0] = 0.06
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    s.line.fill.background()
    s.shadow.inherit = False
    return s


def picture(slide, path, x, y, maxw, maxh, center=False):
    iw, ih = Image.open(path).size
    sc = min(maxw / iw, maxh / ih)
    w, h = iw * sc, ih * sc
    if center:
        x += (maxw - w) / 2
    slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))
    return x, w, h


def vis_caption(slide, n, x, y, w, obs=None, obs_h=1.0):
    kind, tool = VIS[n]
    text(slide, x, y, w, 0.3, [[(f"Visualization {n} · ", {"bold": True, "color": RED, "size": 12}),
                                (f"{kind} · {tool}", {"size": 12, "color": INK2})]])
    if obs:
        text(slide, x, y + 0.32, w, obs_h, [[("Observation: ", {"bold": True}), (obs, {})]], size=14)


def stat(slide, x, y, w, value, label, color=RED, vsize=36):
    text(slide, x, y, w, 0.65, value, size=vsize, bold=True, color=color)
    text(slide, x, y + 0.68, w, 0.7, label, size=13, color=INK2)


def call_card(slide, x, y, w, h, body, head="The call you would make"):
    card(slide, x, y, w, h)
    text(slide, x + 0.22, y + 0.16, w - 0.44, h - 0.25, [[(head, {"bold": True, "size": 13, "color": RED})],
                                                         [(body, {"size": 14})]], spacing=3)


def call_strip(slide, y, body, head="The call you would make: "):
    card(slide, 0.6, y, 12.13, 0.58)
    text(slide, 0.82, y + 0.15, 11.7, 0.35, [[(head, {"bold": True, "color": RED}), (body, {})]], size=14)


def table(slide, x, y, w, rows, widths, size=13, row_h=0.42):
    shp = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(row_h * len(rows)))
    tb = shp.table
    for j, cw in enumerate(widths):
        tb.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = tb.cell(i, j)
            c.fill.solid()
            c.fill.fore_color.rgb = CARD if i == 0 else (WHITE if i % 2 else ROW)
            c.margin_left = c.margin_right = Inches(0.08)
            c.margin_top = c.margin_bottom = Inches(0.04)
            tf = c.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            r = p.add_run()
            r.text = str(val)
            r.font.name, r.font.size = FONT, Pt(size)
            r.font.bold = i == 0 or (j == 0 and len(row) > 2)
            r.font.color.rgb = INK
    return tb


def frame(tag, title, num, cell=None, dark=False):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = DARK if dark else WHITE
    text(s, 0.6, 0.38, 12.1, 0.3, tag.upper(), size=12, bold=True, color=RED)
    text(s, 0.6, 0.7, 12.1, 1.25, title, size=28, bold=True, color=WHITE if dark else INK)
    fc = SOFT if dark else MUTED
    text(s, 0.6, 7.02, 7.5, 0.3, "Arwindh C N · CB.SC.U4CSE24207 · 23CSE353 Data Visualisation", size=10, color=fc)
    text(s, 8.2, 7.02, 4.53, 0.3, (f"Notebook cell {cell} · " if cell else "") + f"{num} / {N}", size=10, color=fc,
         align=PP_ALIGN.RIGHT)
    return s


def notes(slide, t):
    """Speaker notes: one paragraph per WHAT / WHY line, extra spaces removed."""
    lines = [" ".join(l.split()) for l in t.strip().split("\n\n")]
    slide.notes_slide.notes_text_frame.text = "\n".join(lines)


# Dark race-trace graphic for the title slide, drawn from the hook race's lap data.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
DECO = SL / "deco_bump_dark.png"
_lt, _res = pd.read_csv(HERE / "data" / "clean" / "lap_times.csv"), pd.read_csv(HERE / "data" / "clean" / "results.csv")
_hid = int(_res.loc[_res["race_label"] == F("H.race"), "raceId"].iloc[0])
_hr = _res[_res["raceId"] == _hid].set_index("driverId")
_tr = _lt[_lt["raceId"] == _hid].pivot(index="lap", columns="driverId", values="position")
_tr.loc[0] = _hr["grid"]
_tr = _tr.sort_index()
_ham, _ros = (_hr.index[_hr["driverRef"] == n][0] for n in ("hamilton", "rosberg"))
_fig, _ax = plt.subplots(figsize=(7.2, 5.0), facecolor="#111111")
_ax.set_facecolor("#111111")
for _d in _tr.columns:
    if _d not in (_ham, _ros):
        _ax.plot(_tr.index, _tr[_d], color="#3A3A3A", lw=1.3)
_ax.plot(_tr.index, _tr[_ros], color="#FFFFFF", lw=2.4)
_ax.plot(_tr.index, _tr[_ham], color="#C8102E", lw=3)
_ax.invert_yaxis()
_ax.axis("off")
SL.mkdir(parents=True, exist_ok=True)
_fig.savefig(DECO, dpi=200, bbox_inches="tight", pad_inches=0.05, facecolor="#111111")
plt.close(_fig)

# ------------------------------------------------------------------ simple speaker notes: WHAT and WHY
NOTES = [
f"""WHAT: My project looks at 10 years of Formula 1 races: {F('P.n_races')} races from 2015 to 2024.

WHY: Most people only see who won. I want to show why they won. A race is a chain of cause and effect.""",

f"""WHAT: A race result depends on many things: the car, the driver, the starting position, pit stops and the track.

WHY: A results table only shows who won, not why. So in my Primary Review I set six questions, O1 to O6. Each part of my story answers one of them.""",

f"""WHAT: I used the Ergast F1 dataset: 14 linked tables. I kept 2015 to 2024: {F('P.n_races')} races, {F('P.n_drivers')} drivers and {F('P.n_constructors')} teams.

WHY: The lap table is the most important one. It shows where every car was on every lap, so I can follow a race move by move.""",

f"""WHAT: I cleaned the data in 5 steps: read the files, kept 2015 to 2024, joined the tables using ID numbers, fixed wrong codes, and merged everything into one table.

WHY: Without cleaning, the numbers would be wrong. For example, a car that finished one lap behind is not a retirement. My row counts match my Primary Review workbook.""",

f"""WHAT: I used three tools. Matplotlib for detailed story charts. Seaborn for statistics. Plotly for interactive charts and the dashboard.

WHY: Each tool does one job best. I also avoided basic bar and pie charts. Plotly replaced Power BI so the whole analysis stays reproducible in a single notebook.""",

f"""WHAT: Each line is one car, showing its position on every lap. Dots are pit stops. This race had {F('H.changes')} position changes, the most of all {F('H.n_races')} races.

WHY: Hamilton, in red, started {F('H.ham_grid')}nd, made {F('H.ham_stops')} stops and finished {F('H.ham_finish')}th. Rosberg, in black, started first and won. A race is a story of moves, not just a result.""",

f"""WHAT: These charts compare where drivers start and where they finish. The link score is {F('A1.pooled_r')} out of 1, which is strong. Pole position won {F('A1.pole_win')} of all races.

WHY: The link changes by track. Monaco is {F('A1.top_r')} because its streets are too narrow to overtake. So at Monaco, Saturday's qualifying decides the race.""",

f"""WHAT: This chart shows a driver's position before and after the first pit stop. Early stoppers drop about {F('A2.early_lost2')} places, then win back {F('A2.early_back')}.

WHY: Late stoppers win back only {F('A2.late_back')}. So stopping first pays off: that is the undercut working.""",

f"""WHAT: I compared teammates, because they drive the same car. People think a driver who is far behind gambles on extra pit stops. The left chart shows no link at all.

WHY: The right chart shows the truth. With an extra stop, a driver beats the teammate only {F('A3.rate_extra')} of the time, not {F('A3.rate_no')}. An extra stop is a warning sign that something went wrong, not a plan.""",

f"""WHAT: These charts show each team's share of all points, and how often cars broke down. Mercedes led first, then Red Bull, then McLaren. Breakdowns fell from {F('A4.dnf_2015')} to {F('A4.dnf_2024')}.

WHY: The car matters most. Good strategy can only help within the limit the car sets.""",

f"""WHAT: Left: {F('A4.wins_champ_car')} of all race wins went to the best team of that season. Right: drivers stay at the same level at almost every track.

WHY: The car and the driver matter more than the track. Steady lap times barely help, and I show that honestly.""",

f"""WHAT: This is my interactive dashboard, made with Plotly. You can filter by season, team, driver and track, and every chart updates.

WHY: Anyone can explore the data and ask their own questions without writing code. It is one file and works offline.""",

f"""WHAT: Here I set the filter to Monaco. The start-to-finish link rises from {F('A1.pooled_r')} to {F('D.mon_r')}. The 2024 Monaco race had only {F('D.mon_last_changes')} position changes.

WHY: At street tracks the race is mostly decided on Saturday. So a team should focus on qualifying there.""",

f"""WHAT: Both charts use the same real numbers: McLaren {F('A5.lead_pts')}, Ferrari {F('A5.second_pts')}. The left chart starts its axis at {F('A5.base')}, so McLaren's bar looks {F('A5.visual_ratio')} times taller.

WHY: The real gap is only {F('A5.gap_pct')}. Cutting the axis tricks the eye. The honest chart starts at zero, and so do all my bar charts.""",

f"""WHAT: This table answers my six questions from the Primary Review.

WHY: Most results matched what I expected. Two did not: an extra pit stop is a warning sign, not a gamble, and the driver matters more than the track.""",

f"""WHAT: My four tips for a team: focus on qualifying at tracks like Monaco, stop early when you can, treat an extra stop as a warning, and plan around the car.

WHY: The {F('H.changes')} position changes in my first race were not random. They were cause and effect. One limit: my data shows links, not proof. Thank you.""",
]

# F1 BASICS: the one Formula 1 idea each slide needs, said before the slide is explained.
BASICS = [
"Formula 1, or F1, is the top level of car racing. About twenty cars race around a track for many laps, and the first car to cross the finish line wins.",
"A season has around twenty races in different countries. Each race is called a Grand Prix. Drivers and teams collect points in every race to win the championship.",
"In F1, a team is called a constructor. Each team builds its own car and runs two cars. The two drivers in the same team are called teammates, and they drive the same car.",
"The grid is the starting order of the race. DNF means 'did not finish': the car crashed or broke down. A car that finishes one lap behind the leader still finished, so it is not a DNF.",
"A lap is one full trip around the track. A car's position is its place in the race order: first, second, third and so on. My charts follow these positions lap by lap.",
"Pole position means starting first. A pit stop is when a car drives into a side lane, called the pit lane, to change its tyres. It costs time, so the car usually loses a few places.",
"Qualifying happens on Saturday. Each driver tries one very fast lap, and the fastest driver starts at the front on Sunday. Overtaking means passing another car on the track.",
f"Tyres wear out during a race, so every car must stop at least once to change them. A stop costs around {F('P.pit_median_normal')} seconds. The undercut means stopping before your rival, so your new tyres make you faster while the rival is still on old tyres.",
"Teammates drive the same car, so comparing them is fair. An extra pit stop means stopping one more time than the teammate, often because of damage, a flat tyre or a crash.",
"Each team builds its own car, so some cars are simply faster. The top ten cars in each race get points. The team with the most points in a year wins the constructors' championship.",
"Every year there are two championships: one for drivers and one for teams. A driver in the fastest car usually wins the most races.",
"A season is one year of races. A circuit is the track where a race happens, and every circuit is different: some are fast and wide, some are slow and narrow.",
"Monaco is a tiny country in the south of France. Its race runs through narrow city streets with walls on both sides, so overtaking is almost impossible.",
"The constructors' championship adds up all the points a team scores in a year. In 2024, McLaren and Ferrari finished very close to each other.",
"Strategy is the team's plan during the race, mainly when to make pit stops. Reliability means how often a car finishes without breaking down.",
"The strategist sits on the pit wall, the team's control desk next to the track. This person decides when each car stops and how to react during the race.",
]
assert len(BASICS) == len(NOTES) == 16
NOTES = [f"F1 BASICS: {b}\n\n{n}" for b, n in zip(BASICS, NOTES)]

# ------------------------------------------------------------------ 1 title
s = prs.slides.add_slide(BLANK)
s.background.fill.solid()
s.background.fill.fore_color.rgb = DARK
picture(s, DECO, 7.0, 0.7, 5.8, 3.9)
text(s, 0.6, 0.6, 6.2, 0.3, "FINAL REVIEW · DATA VISUALISATION CASE STUDY", size=12, bold=True, color=RED)
text(s, 0.6, 1.2, 6.3, 2.2, "Formula 1, read as a chain of cause and effect", size=40, bold=True, color=WHITE)
text(s, 0.6, 3.55, 6.2, 0.9, "Drivers, constructors, race strategy and performance trends, 2015–2024", size=18,
     color=SOFT)
text(s, 0.6, 4.45, 6.2, 0.8, [[("Arwindh C N", {"bold": True, "size": 16, "color": WHITE})],
                               [("CB.SC.U4CSE24207  ·  23CSE353 Data Visualisation", {"size": 14, "color": SOFT})]],
     spacing=2)
tiles = [(F("P.n_races"), "races analysed"), ("10", "seasons, 2015–2024"), (F("P.n_laps"), "lap-by-lap records"),
         (f"{len(VIS)} + 1", "visualizations + dashboard")]
for i, (v, lab) in enumerate(tiles):
    x = 0.6 + i * 3.08
    card(s, x, 5.45, 2.88, 1.3, fill=RGBColor(0x22, 0x22, 0x22))
    text(s, x + 0.2, 5.58, 2.5, 0.6, v, size=30, bold=True, color=RED if i == 0 else WHITE)
    text(s, x + 0.2, 6.2, 2.5, 0.4, lab, size=13, color=SOFT)
notes(s, NOTES[0])

# ------------------------------------------------------------------ 2 problem and objectives
s = frame("Section 1 · Problem statement and objectives",
          "Why do races end the way they do? Six questions, one story", 2)
text(s, 0.6, 2.05, 6.2, 4.8, [
    [("Problem background", {"bold": True, "color": RED, "size": 13})],
    [("A Formula 1 result depends on many linked factors: the car, the driver, qualifying, pit stops, the track and "
      "reliability. A results table shows who won, not why.", {})],
    [("Problem statement", {"bold": True, "color": RED, "size": 13})],
    [("Which factors really shape a race result, by how much, and which only appear to?", {})],
    [("Why it matters", {"bold": True, "color": RED, "size": 13})],
    [("A strategist has seconds to decide. Knowing which levers are real, and which are myths, changes the call.", {})],
    [("Approach", {"bold": True, "color": RED, "size": 13})],
    [("One story in five acts, told to one reader: the strategist on the pit wall.", {})]], spacing=6)
card(s, 7.2, 2.05, 5.53, 4.8)
text(s, 7.45, 2.22, 5.1, 0.35, "Analytical objectives (from the Primary Review)", size=14, bold=True)
objs = [("O1", "Driver performance across seasons", "Act 4"), ("O2", "Constructor performance across seasons", "Act 4"),
        ("O3", "Qualifying position vs final position", "Act 1"), ("O4", "Pit-stop strategy vs race outcome", "Acts 2–3"),
        ("O5", "Driver performance across circuits", "Act 4"), ("O6", "DNF and retirement patterns over time", "Act 4")]
for i, (o, t, a) in enumerate(objs):
    y = 2.75 + i * 0.66
    text(s, 7.45, y, 0.6, 0.4, o, size=15, bold=True, color=RED)
    text(s, 8.05, y, 3.4, 0.6, t, size=14)
    text(s, 11.45, y, 1.1, 0.4, a, size=12, color=INK2, align=PP_ALIGN.RIGHT)
notes(s, NOTES[1])

# ------------------------------------------------------------------ 3 dataset
s = frame("Section 1 · Dataset description", f"Ten seasons, {F('P.n_races')} races, every car on every lap", 3,
          cell="P.12")
text(s, 0.6, 2.05, 5.5, 4.8, [
    [("Source", {"bold": True, "color": RED, "size": 13})],
    [(f"Ergast-lineage Formula 1 dataset (the data behind the Jolpica F1 API): 14 linked CSV tables, "
      f"{F('P.first_year')}–2024.", {})],
    [("Coverage", {"bold": True, "color": RED, "size": 13})],
    [(f"2015–2024: {F('P.n_races')} races, {F('P.n_drivers')} drivers, {F('P.n_constructors')} constructors, "
      f"{F('P.n_circuits')} circuits.", {})],
    [("Data quality concerns", {"bold": True, "color": RED, "size": 13})],
    [(f"{F('P.n_unclassified')} drivers have no finishing position; \"+1 Lap\" looks like a retirement but is not; "
      f"{F('P.n_pitlane')} pit-lane starts are coded as grid 0; missing values are written as \\N.", {})]], spacing=6)
table(s, 6.5, 2.05, 6.23, [
    ["Table", "Rows", "One row is"],
    ["results", F("P.n_results"), "one driver in one race"],
    ["qualifying", F("P.n_quali"), "one driver's qualifying session"],
    ["pit_stops", F("P.n_stops"), "one pit stop (lap, pit-lane time)"],
    ["lap_times", F("P.n_laps"), "one car on one lap (position, time)"],
    ["standings (final)", f"{F('P.n_dfinal')} / {F('P.n_cfinal')}", "a driver's / team's final season table"],
    ["races, circuits", f"{F('P.n_races')} / {F('P.n_circuits')}", "calendar and track details"]],
    [1.8, 1.25, 3.18], size=13, row_h=0.5)
text(s, 6.5, 5.75, 6.23, 0.9, "All tables link through ID numbers (raceId, driverId, constructorId), so the joins are "
     "exact even when a team changes its name.", size=13, color=INK2)
notes(s, NOTES[2])

# ------------------------------------------------------------------ 4 cleaning
s = frame("Section 1 · Data cleaning and preprocessing",
          "Fourteen raw tables cleaned into one driver-race dataset", 4, cell="P.1–P.12")
steps = [("14 raw CSVs", f"{F('P.first_year')}–2024; missing values written as \\N"),
         ("Keep 2015–2024", f"{F('P.n_races')} of {F('P.raw_races')} races"),
         ("Join on IDs", "never on names: teams rename (Toro Rosso → RB)"),
         ("Fix and flag", "grid 0 → missing; lapped car ≠ DNF"),
         ("Merge and check", "one driver-race table; every count = workbook")]
for i, (hd, body) in enumerate(steps):
    x = 0.6 + i * 2.47
    card(s, x, 2.05, 2.2, 1.35, fill=CARD)
    text(s, x + 0.15, 2.17, 1.9, 0.35, f"{i + 1}. {hd}", size=14, bold=True)
    text(s, x + 0.15, 2.55, 1.9, 0.8, body, size=12, color=INK2)
    if i < 4:
        a = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x + 2.24), Inches(2.62), Inches(0.19), Inches(0.22))
        a.fill.solid()
        a.fill.fore_color.rgb = RED
        a.line.fill.background()
table(s, 0.6, 3.7, 6.3, [
    ["Before → after", "Raw", "Clean"],
    ["Race-result rows", F("P.raw_results"), F("P.n_results")],
    ["Races", F("P.raw_races"), F("P.n_races")],
    ["Lap records", F("P.raw_laps"), F("P.n_laps")],
    ["Columns (results → merged)", F("P.raw_cols"), F("P.clean_cols")],
    ["Pit-stop time", "text (m:ss)", "seconds"]], [3.0, 1.65, 1.65], size=13, row_h=0.47)
card(s, 7.2, 3.7, 5.53, 3.1)
text(s, 7.42, 3.85, 5.1, 2.9, [
    [("Key decisions", {"bold": True, "color": RED, "size": 13})],
    [("Two flags, not one: ", {"bold": True}), (f"{F('P.n_unclassified')} unclassified vs {F('P.n_dnf')} genuine DNFs. "
      f"{F('P.n_dnf_classified')} cars retired late but still got a position.", {})],
    [("Pit time from milliseconds: ", {"bold": True}), (f"{F('P.n_long_stops')} stops of 60 s or more (red flags, "
      f"repairs); normal median {F('P.pit_median_normal')} s.", {})],
    [("Verified: ", {"bold": True}), ("every row count matches the Primary Review workbook.", {})]], size=14, spacing=6)
notes(s, NOTES[3])

# ------------------------------------------------------------------ 5 tools
s = frame("Section 2 · Tools and visualization approach", "Three tools, each doing the job it does best", 5)
tools = [("Matplotlib", "Precise, hand-annotated story charts", "V1 bump chart · V4 slope chart · V10 DNF trend · "
          "V11 wins bars · V15 misleading pair", "Exact control of every mark, label and axis, which the ethics demo needs."),
         ("Seaborn", "Statistics with confidence ranges", "V2 density · V3 lollipop · V5 strip plot · V6–V8 point "
          "plots · V13 heatmap · V14 regression", "Bootstrap confidence intervals and grouping in one call."),
         ("Plotly", "Interaction", "V9 points-share eras · V12 season points · the five-act dashboard",
          "Hover, filters and one offline HTML file anyone can explore.")]
thumbs = [SL / "H2_bump_chart_hook_race.png", SL / "A4_5_driver_circuit_heatmap.png", SL / "A4_1_points_share_eras.png"]
for i, (t, role, charts, why) in enumerate(tools):
    x = 0.6 + i * 4.1
    card(s, x, 2.05, 3.93, 3.4)
    text(s, x + 0.22, 2.18, 3.5, 2.1, [[(t, {"bold": True, "size": 20})], [(role, {"bold": True, "color": RED, "size": 13})],
                                       [(charts, {"size": 13})], [(why, {"size": 13, "color": INK2})]], spacing=4)
    picture(s, thumbs[i], x + 0.22, 4.3, 3.5, 1.05, center=True)
text(s, 0.6, 5.62, 12.13, 0.7, [[("Beyond basic charts: ", {"bold": True, "color": RED}),
                                ("bump chart, lollipop with 95% ranges, slope chart, dodged point plots, small multiples, "
                                 "annotated heatmap, misleading-vs-honest pair and a linked dashboard. One colour rule "
                                 "throughout: greys for context, red for the thing to look at.", {})]], size=14)
text(s, 0.6, 6.45, 12.13, 0.4, "Plotly replaced Power BI so the whole analysis stays reproducible in a single notebook.",
     size=14, bold=True)
notes(s, NOTES[4])

# ------------------------------------------------------------------ 6 hook
s = frame("Section 2 · Visualizations · Hook", f"{F('H.changes')} position changes in one race, and the pole-sitter "
          "still won", 6, cell="H.2")
x, w, h = picture(s, SL / "H2_bump_chart_hook_race.png", 0.6, 2.0, 8.4, 4.4)
vis_caption(s, 1, 0.6, 2.0 + h + 0.1, 8.4)
text(s, 9.35, 2.05, 3.38, 2.75, [[("Observation", {"bold": True, "color": RED, "size": 13})],
                                 [(f"The {F('H.race')} had the most position changes of all {F('H.n_races')} races. "
                                   f"Hamilton (red) started {F('H.ham_grid')}nd, made {F('H.ham_stops')} stops and "
                                   f"finished {F('H.ham_finish')}th. Rosberg (black), same car, won from pole.", {})]],
     size=14, spacing=4)
call_card(s, 9.25, 4.95, 3.48, 1.85, "Do not read a race from the result. Read it from the moves.")
notes(s, NOTES[5])

# ------------------------------------------------------------------ 7 act 1
s = frame("Section 2 · Visualizations · Act 1", f"Saturday decides more than you think: {F('A1.top_circuit')} locks "
          "the order in", 7, cell="A1.1–A1.2")
x, w, h = picture(s, SL / "A1_1_grid_vs_finish_pooled.png", 0.6, 2.0, 6.0, 3.4)
vis_caption(s, 2, 0.6, 5.5, 6.0, f"strong link between grid and finish (r = {F('A1.pooled_r')}); pole won "
            f"{F('A1.pole_win')} of races.", 1.0)
x, w, h = picture(s, SL / "A1_2_circuit_lollipop.png", 6.85, 2.0, 5.88, 3.4, center=True)
vis_caption(s, 3, 6.85, 5.5, 5.88, f"{F('A1.top_circuit')} {F('A1.top_r')}; {F('A1.bottom_circuit')} "
            f"{F('A1.bottom_r')}, but only {F('A1.bottom_races')} races, so its range is wide.", 1.0)
notes(s, NOTES[6])

# ------------------------------------------------------------------ 8 act 2
s = frame("Section 2 · Visualizations · Act 2", f"Early stoppers lose {F('A2.early_lost2_round')} places, then win "
          f"back {F('A2.early_back')} of them", 8, cell="A2.1–A2.3")
x, w, h = picture(s, SL / "A2_2_undercut_slope.png", 0.6, 2.0, 8.4, 4.4)
vis_caption(s, 4, 0.6, 2.0 + h + 0.1, 8.4)
text(s, 9.35, 2.05, 3.38, 2.75, [[("Observation", {"bold": True, "color": RED, "size": 13})],
                                 [(f"Across {F('A2.n')} first pit stops, early stoppers go {F('A2.early_chg2')} then "
                                   f"{F('A2.early_chg10')}; late stoppers {F('A2.late_chg2')} then {F('A2.late_chg10')}. "
                                   f"Same pattern without the stops in laps 1–5.", {})]], size=14, spacing=4)
call_card(s, 9.25, 4.95, 3.48, 1.85, "If the car can survive two or three exposed laps, stop first.")
notes(s, NOTES[7])

# ------------------------------------------------------------------ 9 act 3
s = frame("Section 2 · Visualizations · Act 3", "The myth is dead, the alarm is real: an extra stop means trouble", 9,
          cell="A3.3–A3.5")
picture(s, SL / "A3_3_gap_vs_stopdiff.png", 0.6, 2.0, 5.95, 2.85)
vis_caption(s, 6, 0.6, 4.95, 5.95, f"the myth says drivers far behind their teammate gamble on extra stops. "
            f"No link: r = {F('A3.r_gap')}.", 0.95)
picture(s, SL / "A3_4_teammate_duel.png", 6.78, 2.0, 5.95, 2.85)
vis_caption(s, 7, 6.78, 4.95, 5.95, f"with an extra stop the slower teammate wins {F('A3.rate_extra')} of duels, "
            f"not {F('A3.rate_no')} (z = {F('A3.z')}).", 0.95)
call_strip(s, 6.28, "treat an unplanned stop as an alarm, not a strategy, and protect the other car's result.")
notes(s, NOTES[8])

# ------------------------------------------------------------------ 10 act 4a
s = frame("Section 2 · Visualizations · Act 4", "The car sets the ceiling: three eras in ten seasons", 10,
          cell="A4.1–A4.2")
picture(s, SL / "A4_1_points_share_eras.png", 0.6, 2.0, 7.0, 2.9)
vis_caption(s, 9, 0.6, 4.95, 7.0, f"Mercedes {F('A4.mer_2015')} of points (2015) → {F('A4.mer_2023')} (2023); "
            f"Red Bull up to {F('A4.rbr_2023')}; McLaren {F('A4.mcl_2015')} → {F('A4.mcl_2024')}.", 0.95)
picture(s, SL / "A4_2_dnf_rate.png", 7.85, 2.0, 4.88, 2.9, center=True)
vis_caption(s, 10, 7.85, 4.95, 4.88, f"genuine DNFs {F('A4.dnf_2015')} → {F('A4.dnf_2024')}; "
            f"{F('A4.dnf_best_team')} {F('A4.dnf_best')}.", 0.95)
call_strip(s, 6.28, "plan the season around the car: every edge from Acts 1–3 lives inside its ceiling.")
notes(s, NOTES[9])

# ------------------------------------------------------------------ 11 act 4b
s = frame("Section 2 · Visualizations · Act 4", "Wins follow the car, and the driver matters more than the track", 11,
          cell="A4.3–A4.6")
picture(s, SL / "A4_3_wins_by_driver.png", 0.6, 2.0, 5.95, 2.85)
vis_caption(s, 11, 0.6, 4.95, 5.95, f"{F('A4.wins_champ_car')} of all wins went to that season's champion team; "
            f"Hamilton {F('A4.ham_champ_wins')} of {F('A4.ham_wins')} in the champion car.", 0.95)
picture(s, SL / "A4_5_driver_circuit_heatmap.png", 6.78, 2.0, 5.95, 2.85)
vis_caption(s, 13, 6.78, 4.95, 5.95, f"driver rows differ by {F('A4.hm_row_range')} places, circuit columns by "
            f"only {F('A4.hm_col_range')}.", 0.95)
call_strip(s, 6.28, f"lap-time consistency barely predicts points (r = {F('A4.cons_r')}, Visualization 14), and "
           f"other methods give {F('A4.cons_r_race')} to {F('A4.cons_r_med')}.", head="Honest anti-climax: ")
notes(s, NOTES[10])

# ------------------------------------------------------------------ 12 dashboard
s = frame("Section 2 · Interactive dashboard (Plotly)", "One interactive page: four filters, five acts, every chart "
          "linked", 12, cell="D.1")
picture(s, CH / "D_dashboard_overview.png", 0.6, 2.0, 5.9, 4.85)
text(s, 6.85, 2.05, 5.88, 4.8, [
    [("Components: ", {"bold": True}), ("5 headline tiles (races, grid–finish r, early-stopper change, teammate duel, "
      "DNF rate), a race selector with the lap-by-lap chart, and 8 linked charts arranged as the five acts.", {})],
    [("Filters: ", {"bold": True}), ("season, constructor, driver and circuit in one row; every chart re-draws for the "
      "same selection.", {})],
    [("Interactions: ", {"bold": True}), ("hover for exact values; the chosen team or driver turns red; a toggle switches "
      "the Act 5 chart between misleading and honest; the view is saved in the link.", {})],
    [("Honesty built in: ", {"bold": True}), ("small selections are labelled \"small sample\"; grey lines show the "
      "all-data result behind a filtered one.", {})],
    [("Delivery: ", {"bold": True}), (f"one HTML file ({F('D.size_mb')} MB) that works offline, generated by the "
      f"notebook.", {})]], size=14, spacing=8)
notes(s, NOTES[11])

# ------------------------------------------------------------------ 13 dashboard insights
s = frame("Section 2 · Dashboard insights and data storytelling",
          f"Filter to Monaco and the story sharpens: r rises from {F('A1.pooled_r')} to {F('D.mon_r')}", 13, cell="D.2")
picture(s, CH / "D_dashboard_monaco.png", 0.6, 2.0, 6.0, 4.85)
table(s, 6.95, 2.0, 5.78, [
    ["KPI", "All races", "Circuit = Monaco"],
    ["Races", F("P.n_races"), F("D.mon_races")],
    ["Grid–finish correlation r", F("A1.pooled_r"), F("D.mon_r")],
    ["Early stoppers after 10 laps", F("A2.early_chg10"), f"{F('D.mon_und10')} (n = {F('D.mon_und_n')})"],
    ["Slower teammate wins (extra vs none)", f"{F('A3.rate_extra')} vs {F('A3.rate_no')}",
     f"{F('D.mon_extra')} vs {F('D.mon_no')} (only {F('D.mon_n_extra')} extra)"],
    ["Genuine DNF rate", F("D.all_dnf"), F("D.mon_dnf")]], [2.6, 1.4, 1.78], size=13, row_h=0.46)
text(s, 6.95, 4.95, 5.78, 1.9, [
    [("What? ", {"bold": True, "color": RED}), (f"At Monaco the start order mostly holds; the "
      f"{F('D.mon_last_race')} had {F('D.mon_last_changes')} position changes against {F('H.changes')} in the hook race.", {})],
    [("So what? ", {"bold": True, "color": RED}), ("At street circuits the race is largely decided on Saturday.", {})],
    [("Now what? ", {"bold": True, "color": RED}), ("All-in on qualifying at Monaco; keep risk for overtaking tracks.", {})]],
    size=14, spacing=5)
notes(s, NOTES[12])

# ------------------------------------------------------------------ 14 misleading
s = frame("Section 2 · Misleading visualization and ethical redesign",
          f"Same numbers, two stories: a cut axis turns a {F('A5.gap_pct')} gap into a bar {F('A5.visual_ratio')}× taller",
          14, cell="A5.1–A5.3")
x, w, h = picture(s, SL / "A5_3_misleading_vs_honest.png", 0.6, 2.0, 12.13, 3.2, center=True)
vis_caption(s, 15, x, 2.0 + h + 0.05, w)
items = [("Misleading chart", f"Y-axis starts at {F('A5.base')}, not 0. The real numbers ({F('A5.lead')} "
          f"{F('A5.lead_pts')}, {F('A5.second')} {F('A5.second_pts')}) look like a rout."),
         ("False impression", f"\"{F('A5.lead')} crushed {F('A5.second')}.\" In fact it was {F('A5.closest')} "
          f"constructors' title of the decade: {F('A5.gap')} points."),
         ("Corrected chart and principle", f"Zero baseline and values on the bars. Truthful scaling and proportional ink: "
          f"lie factor about {F('A5.lie_factor')} → 1.")]
for i, (hd, body) in enumerate(items):
    x0 = 0.6 + i * 4.1
    card(s, x0, 5.6, 3.93, 1.3)
    text(s, x0 + 0.2, 5.72, 3.55, 1.15, [[(hd, {"bold": True, "size": 13, "color": RED})], [(body, {"size": 13})]],
         spacing=3)
notes(s, NOTES[13])

# ------------------------------------------------------------------ 15 key findings
s = frame("Section 2 · Key findings and insights", "Two expectations were overturned: extra stops and circuit "
          "specialists", 15)
table(s, 0.6, 2.0, 12.13, [
    ["Objective", "What the data shows", "As expected?", "Visual"],
    ["O1 Drivers across seasons", f"Hamilton {F('A4.ham_wins')} wins, Verstappen {F('A4.ver_wins')}; titles follow "
     f"the car eras", "Partly", "V11, V12"],
    ["O2 Constructors across seasons", f"Three eras: Mercedes {F('A4.mer_2015')} (2015) → Red Bull "
     f"{F('A4.rbr_2023')} (2023) → McLaren champion 2024", "Yes", "V9"],
    ["O3 Qualifying vs finish", f"Strong link, r = {F('A1.pooled_r')}; {F('A1.top_circuit')} {F('A1.top_r')}, "
     f"{F('A1.bottom_circuit')} {F('A1.bottom_r')}", "Yes, varies by track", "V2, V3"],
    ["O4 Pit strategy vs outcome", f"Early stops win back {F('A2.early_back')} places vs {F('A2.late_back')}; extra "
     f"stop: {F('A3.rate_extra')} vs {F('A3.rate_no')}", "No: a symptom, not a gamble", "V4, V6, V7"],
    ["O5 Drivers across circuits", f"Driver rows differ by {F('A4.hm_row_range')} places, circuits by "
     f"{F('A4.hm_col_range')}", "No: specialists are rare", "V13"],
    ["O6 DNFs over time", f"Genuine DNFs fell from {F('A4.dnf_2015')} to {F('A4.dnf_2024')}", "Yes", "V10"]],
    [3.0, 5.65, 2.25, 1.23], size=13, row_h=0.62)
text(s, 0.6, 6.45, 12.13, 0.45, "Every result is a correlation in historical records, not an experiment.",
     size=13, color=INK2)
notes(s, NOTES[14])

# ------------------------------------------------------------------ 16 recommendations
s = frame("Section 3 · Recommendations and conclusion", f"The {F('H.changes')} position changes were a chain of "
          "cause and effect", 16, dark=True)
text(s, 0.6, 2.05, 6.3, 4.0, [
    [("Recommendations for the pit wall", {"bold": True, "color": RED, "size": 13})],
    [("1. ", {"bold": True, "color": WHITE}), (f"Weight qualifying effort by circuit: all-in at {F('A1.top_circuit')}, "
      f"{F('A1.second_circuit')} and {F('A1.third_circuit')}.", {"color": WHITE})],
    [("2. ", {"bold": True, "color": WHITE}), (f"If the car can survive a few exposed laps, stop first: early stoppers "
      f"win back {F('A2.early_back')} places, late ones {F('A2.late_back')}.", {"color": WHITE})],
    [("3. ", {"bold": True, "color": WHITE}), ("Treat an unplanned extra stop as an alarm and protect the other car's "
      "result.", {"color": WHITE})],
    [("4. ", {"bold": True, "color": WHITE}), (f"Plan the season around the car: {F('A4.wins_champ_car')} of wins went "
      f"to the champion team.", {"color": WHITE})]], size=14, spacing=9)
text(s, 7.3, 2.05, 5.43, 4.0, [
    [("Main conclusion", {"bold": True, "color": RED, "size": 13})],
    [("Saturday sets the order, pit timing trades places, an extra stop signals trouble, and the car sets the ceiling.",
      {"color": WHITE, "size": 15})],
    [("Limitations", {"bold": True, "color": RED, "size": 13})],
    [(f"Correlation, not causation. No tyre, weather or safety-car data. Small samples are flagged "
      f"({F('A1.bottom_circuit')}: {F('A1.bottom_races')} races).", {"color": SOFT})]], size=14, spacing=9)
card(s, 0.6, 5.45, 12.13, 1.2, fill=RGBColor(0x22, 0x22, 0x22))
text(s, 0.85, 5.62, 11.7, 0.9, [[("Back to the hook: ", {"bold": True, "color": WHITE}),
                                (f"Rosberg won from pole, {F('H.n_sc_stops')} cars pitted on lap {F('H.sc_lap')}, "
                                 f"Hamilton's {F('C.extra_stops')} extra stops were the alarm, and the 2016 Mercedes took "
                                 f"{F('A4.mer_2016')} of all points.", {"color": SOFT})]], size=14)
notes(s, NOTES[15])

out = HERE / "F1_Review_Presentation.pptx"
prs.core_properties.author = prs.core_properties.last_modified_by = "Arwindh C N"
prs.core_properties.title = "Formula 1 Performance Analytics"
prs.save(out)
print("wrote", out.name, len(prs.slides), "slides")

# A readable copy of the speaker notes, for practising away from PowerPoint.
md = ["# Speaker notes · F1_Review_Presentation.pptx", "",
      "F1 BASICS = the F1 idea to explain first. WHAT = what the slide shows. WHY = why it matters.",
      "Read them aloud in that order while pointing at the chart.", ""]
for i, sl in enumerate(prs.slides, 1):
    title = [sh.text_frame.text for sh in sl.shapes if sh.has_text_frame][1]
    md += [f"## Slide {i}: {title}", ""] + [f"**{l.split(':', 1)[0]}:**{l.split(':', 1)[1]}"
                                            for l in sl.notes_slide.notes_text_frame.text.split("\n")] + [""]
(HERE / "Speaker_Notes.md").write_text("\n".join(md), encoding="utf-8")
print("wrote Speaker_Notes.md")
