"""
Builds F1_Final_Presentation.pptx (11 slides, one story beat each) from facts.json and charts/slides/.
Every number on the slides and in the speaker notes is read from facts.json.
Run after make_notebook.sh:  python build_slides.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
FACTS = json.loads((HERE / "facts.json").read_text())
SL = HERE / "charts" / "slides"
CH = HERE / "charts"


def F(k):
    return FACTS[k]["text"]


INK, INK2, MUTED, RED = RGBColor(0x1A, 0x1A, 0x1A), RGBColor(0x4D, 0x4D, 0x4D), RGBColor(0x76, 0x76, 0x76), RGBColor(0xC8, 0x10, 0x2E)
WHITE, CARD, DARK, SOFT = RGBColor(0xFF, 0xFF, 0xFF), RGBColor(0xF2, 0xF2, 0xF2), RGBColor(0x11, 0x11, 0x11), RGBColor(0xBB, 0xBB, 0xBB)
FONT = "Arial"
N_SLIDES = 11

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


# ------------------------------------------------------------------ helpers
def text(slide, x, y, w, h, runs, size=14, color=INK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         spacing=None, name=None):
    """runs: a string, or a list of paragraphs; each paragraph is a string or a list of (text, {opts})."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    paras = runs if isinstance(runs, list) else [runs]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if spacing:
            p.space_after = Pt(spacing)
        parts = para if isinstance(para, list) else [(para, {})]
        for t, o in parts:
            r = p.add_run()
            r.text = t
            f = r.font
            f.name = FONT
            f.size = Pt(o.get("size", size))
            f.bold = o.get("bold", bold)
            f.italic = o.get("italic", False)
            f.color.rgb = o.get("color", color)
    return tb


def card(slide, x, y, w, h, fill=CARD, name=None):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.adjustments[0] = 0.06
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    s.line.fill.background()
    s.shadow.inherit = False
    if name:
        s.name = name
    return s


def picture(slide, path, x, y, maxw, maxh, center=False):
    iw, ih = Image.open(path).size
    scale = min(maxw / iw, maxh / ih)
    w, h = iw * scale, ih * scale
    if center:
        x += (maxw - w) / 2
    slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))
    return w, h


def stat(slide, x, y, w, value, label, color=RED, vsize=40):
    text(slide, x, y, w, 0.75, value, size=vsize, bold=True, color=color)
    text(slide, x, y + 0.78, w, 0.75, label, size=13, color=INK2)


def call_card(slide, x, y, w, h, body, head="The call you would make"):
    card(slide, x, y, w, h, name="Call card")
    text(slide, x + 0.22, y + 0.18, w - 0.44, h - 0.3,
         [[(head, {"bold": True, "size": 13, "color": RED})], [(body, {"size": 14})]], spacing=4)


def frame(tag, title, cell, num, dark=False):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = DARK if dark else WHITE
    text(s, 0.6, 0.38, 12.1, 0.3, tag.upper(), size=12, bold=True, color=RED, name="Act tag")
    text(s, 0.6, 0.7, 12.1, 1.25, title, size=28, bold=True, color=WHITE if dark else INK, name="Title")
    foot_c = SOFT if dark else MUTED
    text(s, 0.6, 7.02, 7.5, 0.3, "Arwindh C N · CB.SC.U4CSE24207 · 23CSE353 Data Visualisation", size=10, color=foot_c)
    text(s, 8.2, 7.02, 4.53, 0.3, (f"Notebook cell {cell} · " if cell else "") + f"{num} / {N_SLIDES}", size=10,
         color=foot_c, align=PP_ALIGN.RIGHT)
    return s


def notes(slide, t):
    slide.notes_slide.notes_text_frame.text = " ".join(t.split())


# ------------------------------------------------------------------ decorative dark race trace (from the data)
C = HERE / "data" / "clean"
lt = pd.read_csv(C / "lap_times.csv")
res = pd.read_csv(C / "results.csv")
hook_id = int(res.loc[res["race_label"] == F("H.race"), "raceId"].iloc[0])
hr = res[res["raceId"] == hook_id].set_index("driverId")
tr = lt[lt["raceId"] == hook_id].pivot(index="lap", columns="driverId", values="position")
tr.loc[0] = hr["grid"]
tr = tr.sort_index()
ham = hr.index[hr["driverRef"] == "hamilton"][0]
ros = hr.index[hr["driverRef"] == "rosberg"][0]
fig, ax = plt.subplots(figsize=(7.2, 5.0), facecolor="#111111")
ax.set_facecolor("#111111")
for d in tr.columns:
    if d not in (ham, ros):
        ax.plot(tr.index, tr[d], color="#3A3A3A", lw=1.3)
ax.plot(tr.index, tr[ros], color="#FFFFFF", lw=2.4)
ax.plot(tr.index, tr[ham], color="#C8102E", lw=3)
ax.invert_yaxis()
ax.axis("off")
DECO = SL / "deco_bump_dark.png"
fig.savefig(DECO, dpi=200, bbox_inches="tight", pad_inches=0.05, facecolor="#111111")
plt.close(fig)

# ------------------------------------------------------------------ 1 title
s = prs.slides.add_slide(BLANK)
s.background.fill.solid()
s.background.fill.fore_color.rgb = DARK
picture(s, DECO, 6.6, 1.2, 6.3, 5.4)
text(s, 0.6, 0.6, 6.0, 0.3, "FINAL REVIEW · 23CSE353 DATA VISUALISATION", size=12, bold=True, color=RED)
text(s, 0.6, 1.5, 6.2, 2.6, "Formula 1, read as a chain of cause and effect", size=40, bold=True, color=WHITE)
text(s, 0.6, 4.05, 5.9, 1.0, "Drivers, constructors, race strategy and performance trends, 2015–2024", size=18,
     color=SOFT)
text(s, 0.6, 5.6, 5.9, 0.9, [[("Arwindh C N", {"bold": True, "size": 16, "color": WHITE})],
                              [("Roll No. CB.SC.U4CSE24207", {"size": 14, "color": SOFT})]], spacing=2)
text(s, 6.6, 6.7, 6.3, 0.3, f"Every line is one car in the {F('H.race')}. Red = Hamilton, white = Rosberg.", size=10,
     color=SOFT, align=PP_ALIGN.RIGHT)
notes(s, f"""Most people watch a Formula 1 race as a result: who won. Today I want to show you how a strategist on the pit
wall reads a race: as a chain of cause and effect. I used ten seasons of data, {F('P.n_races')} races from 2015 to 2024,
and built one story in five acts. The picture behind the title is a real race, which we will open in a moment.
Everything you see comes from one Jupyter notebook, and every number is produced by a code cell in it.""")

# ------------------------------------------------------------------ 2 hook
s = frame("Hook · one race, lap by lap", f"{F('H.changes')} position changes in one race, and the pole-sitter still won",
          "H.2", 2)
picture(s, SL / "H2_bump_chart_hook_race.png", 0.6, 2.05, 8.9, 4.8)
stat(s, 9.85, 2.1, 2.9, F("H.changes"), f"position changes in the {F('H.race')}, the most of all {F('H.n_races')} races")
stat(s, 9.85, 3.65, 2.9, f"P{F('H.ham_grid')} → P{F('H.ham_finish')}", f"Hamilton's climb, with {F('H.ham_stops')} pit stops",
     color=INK)
call_card(s, 9.75, 5.15, 3.0, 1.65, "Do not read a race from the result. Read it from the moves.")
notes(s, f"""This is the hook. Each line is one car, and the line shows where that car was at the end of every lap.
The dots are pit stops. I chose this race by a rule, not by taste: I added up how many places every car gained or lost
from lap to lap, and the {F('H.race')} scored highest of all {F('H.n_races')} races, with {F('H.changes')}. Look at the red
line. Hamilton started {F('H.ham_grid')}nd, stopped on lap {F('H.ham_first_stop')}, made {F('H.ham_stops')} stops and
still climbed to {F('H.ham_finish')}th. On lap {F('H.sc_lap')}, {F('H.n_sc_stops')} cars stopped together, just before
the field slowed, probably for a safety car. Yet Rosberg, in black, started first and finished first. Keep this race in
mind: by the end, every part of it will make sense.""")

# ------------------------------------------------------------------ 3 act 1
s = frame("Act 1 · Saturday decides more than you think",
          f"{F('A1.top_circuit')} locks the order in. {F('A1.bottom_circuit')} lets it go.", "A1.2", 3)
picture(s, SL / "A1_2_circuit_lollipop.png", 0.6, 2.05, 8.9, 4.85, center=True)
stat(s, 9.85, 2.1, 2.9, F("A1.pooled_r"), f"link between grid and finish, all {F('A1.n')} finishes (1 = perfect)")
stat(s, 9.85, 3.65, 2.9, F("A1.top_r"), f"at {F('A1.top_circuit')}; {F('A1.bottom_circuit')} only {F('A1.bottom_r')} "
     f"(just {F('A1.bottom_races')} races)", color=INK)
call_card(s, 9.75, 5.15, 3.0, 1.65, f"At {F('A1.top_circuit')}, treat qualifying as the race. At "
          f"{F('A1.second_bottom')}, Sunday can still fix a bad grid slot.")
notes(s, f"""Act one asks: if I know where a driver starts, how well can I guess where they finish? Across all races the
link is strong. The correlation is {F('A1.pooled_r')}, where zero means no link and one means a perfect link, and pole
position won {F('A1.pole_win')} of all races. But it is not the same everywhere. Each dot here is one circuit.
{F('A1.top_circuit')} is at the top with {F('A1.top_r')}: it is a narrow street circuit, so overtaking is almost
impossible. {F('A1.bottom_circuit')} is at the bottom with {F('A1.bottom_r')}, but it only hosted {F('A1.bottom_races')}
races, which is why its grey range is so wide, so I do not over-read its exact rank. The call: at high-r tracks,
qualifying is the race.""")

# ------------------------------------------------------------------ 4 act 2
s = frame("Act 2 · the undercut",
          f"Early stoppers lose {F('A2.early_lost2_round')} places, then win back {F('A2.early_back')} of them", "A2.2", 4)
picture(s, SL / "A2_2_undercut_slope.png", 0.6, 2.05, 8.9, 4.85)
stat(s, 9.85, 2.1, 2.9, f"{F('A2.early_chg2')} → {F('A2.early_chg10')}",
     "early stoppers: places after 2 laps, then after 10 laps", vsize=34)
stat(s, 9.85, 3.65, 2.9, f"{F('A2.late_chg2')} → {F('A2.late_chg10')}", "late stoppers: they win back far less",
     color=INK, vsize=34)
call_card(s, 9.75, 5.15, 3.0, 1.65, "If the car can survive two or three exposed laps, stop first.")
notes(s, f"""Act two is about the pit stop. A stop costs about {F('P.pit_median_normal')} seconds in the pit lane.
I took every driver's first stop, {F('A2.n')} of them, and read their position the lap before, two laps after and ten
laps after. Early stoppers, in red, drop {F('A2.early_lost2')} places at once, because rivals on old tyres are still
ahead. But when those rivals make their own stops, early stoppers win back {F('A2.early_back')} places. Late stoppers win
back only {F('A2.late_back')}. This is the undercut: stopping first looks bad on TV for a few laps, and that is the
strategy working. I also checked it without the stops in the first five laps, which are often damage, and the pattern
stays the same.""")

# ------------------------------------------------------------------ 5 act 3 assumption
s = frame("Act 3 · the assumption",
          f"Myth: a driver far behind the teammate gambles on extra stops. The data says no (r = {F('A3.r_gap')})",
          "A3.3", 5)
picture(s, SL / "A3_3_gap_vs_stopdiff.png", 0.6, 2.05, 8.9, 4.85)
stat(s, 9.85, 2.1, 2.9, F("A3.r_gap"), "link between qualifying gap and extra stops: none")
stat(s, 9.85, 3.65, 2.9, F("A3.n_pairs"), "teammate pairs: same team, same race, same car", color=INK)
call_card(s, 9.75, 5.15, 3.0, 1.65, "So if extra stops are not a planned gamble, what are they?", head="The question")
notes(s, f"""Act three is the twist. It joins three tables, qualifying, pit stops and results, through a link I had to
build myself: who is my teammate. Teammates drive the same car, so comparing them takes the car out of the picture.
Most fans would say: a driver who qualified far behind the teammate gambles on an extra pit stop. If that were true, the
dots here would climb along the grey arrow. They do not. The correlation is {F('A3.r_gap')}, effectively zero, over
{F('A3.n_pairs')} pairs. A driver ten places behind on Saturday is no more likely to make an extra stop than one who was
a single place behind. So the assumption is dead. Then what is an extra stop?""")

# ------------------------------------------------------------------ 6 act 3 reveal
s = frame("Act 3 · the reveal",
          f"The hidden alarm: with an extra stop, the slower teammate wins the duel {F('A3.rate_extra')} of the time, "
          f"not {F('A3.rate_no')}", "A3.4", 6)
picture(s, SL / "A3_4_teammate_duel.png", 0.6, 2.05, 8.9, 4.85)
stat(s, 9.85, 2.1, 2.9, f"z = {F('A3.z')}", "far beyond chance; holds at small, medium and large qualifying gaps",
     vsize=34)
stat(s, 9.85, 3.65, 2.9, F("A3.beat_when_mate_extra"), "when the teammate makes the extra stop, the slower qualifier "
     "usually wins", color=INK, vsize=34)
call_card(s, 9.75, 5.15, 3.0, 1.65, "Treat an unplanned stop as an alarm, not a strategy. Protect the other car.")
notes(s, f"""Here is the real finding. Among pairs where both cars were classified, the slower qualifier finished ahead
of the teammate {F('A3.rate_no_1')} of the time when there was no extra stop, but only {F('A3.rate_extra_1')} of the time
with one. The test statistic is z = {F('A3.z')}, which is far beyond chance, and it holds at every qualifying gap. It also
works the other way: when the teammate made the extra stop, the slower qualifier won {F('A3.beat_when_mate_extra')} of
the time. And {F('A3.early_stop_extra')} of extra-stop drivers made their first stop in laps one to three, against
{F('A3.early_stop_no')} of the others. I want to be honest about what this means. The extra stop is a symptom of trouble,
like damage or a puncture. It is not a weapon and it is not the cause. One caveat: in the large-gap bucket the sample is
small and the difference is not significant.""")

# ------------------------------------------------------------------ 7 act 4 eras
s = frame("Act 4 · the car sets the ceiling", "Three eras in ten seasons: Mercedes, then Red Bull, then McLaren",
          "A4.1", 7)
w, h = picture(s, SL / "A4_1_points_share_eras.png", 0.6, 1.75, 12.1, 3.75, center=True)
y0 = 5.75
for i, (v, lab) in enumerate([(f"{F('A4.mer_2015')} → {F('A4.mer_2023')}", "Mercedes' share of all points, 2015 → 2023"),
                              (f"{F('A4.rbr_2015')} → {F('A4.rbr_2023')}", "Red Bull, 2015 → 2023"),
                              (f"{F('A4.mcl_2015')} → {F('A4.mcl_2024')}", "McLaren, 2015 → 2024: champion")]):
    x = 0.6 + i * 4.1
    text(s, x, y0, 3.9, 0.55, v, size=26, bold=True, color=RED if i == 2 else INK)
    text(s, x, y0 + 0.58, 3.9, 0.4, lab, size=13, color=INK2)
notes(s, f"""Act four zooms out from one race to ten seasons. Each panel shows one team's share of all the constructor
points in a season, and the red dots mark the champion. Mercedes took {F('A4.mer_2015')} of all points in 2015 and won
{F('A4.mer_titles')} titles in a row, then fell to {F('A4.mer_2023')} in 2023. Red Bull rose from {F('A4.rbr_2015')} to
{F('A4.rbr_2023')}. McLaren climbed from {F('A4.mcl_2015')} to {F('A4.mcl_2024')} and won in 2024. The biggest
three-season swing in the data is {F('A4.swing_team')}, whose share {F('A4.swing_dir')} by {F('A4.swing_pp')} percentage
points between {F('A4.swing_from')} and {F('A4.swing_to')}. Changes like these are decided in the factory, not on the
pit wall. I made this chart in Plotly, so in the notebook and the dashboard you can hover for the exact points.""")

# ------------------------------------------------------------------ 8 act 4 reliability
s = frame("Act 4 · the car sets the ceiling",
          f"Cars now break down half as often ({F('A4.dnf_2015_r')} → {F('A4.dnf_2024_r')})", "A4.2", 8)
picture(s, SL / "A4_2_dnf_rate.png", 0.6, 2.05, 8.9, 4.85)
stat(s, 9.85, 2.1, 2.9, F("A4.dnf_best"), f"{F('A4.dnf_best_team')}' DNF rate over ten seasons, the best of any team")
stat(s, 9.85, 3.65, 2.9, F("A4.wins_champ_car"), "of all race wins went to that season's champion team", color=INK)
call_card(s, 9.75, 5.15, 3.0, 1.65, "Plan the season around the car. Every edge from Acts 1–3 lives inside its ceiling.")
notes(s, f"""Reliability is part of the ceiling too. A genuine DNF here means the car retired; a car that finished a lap
down is not counted. In 2015, {F('A4.dnf_2015')} of starts ended in a retirement; in 2024 only {F('A4.dnf_2024')}. The
fall is not smooth: 2017 and 2022 brought new technical rules, and retirements went up both times. {F('A4.dnf_best_team')}
retired only {F('A4.dnf_best')} of the time. And {F('A4.wins_champ_car')} of all race wins went to the team that won the
constructors' title that year. The notebook also has a driver-by-circuit heatmap: the driver rows differ by
{F('A4.hm_row_range')} places, the circuit columns by only {F('A4.hm_col_range')}. And an honest anti-climax: lap-time
consistency is only weakly linked to points, r = {F('A4.cons_r')}, and that number moves a lot with the method. So the
call for act four: every edge from acts one to three lives inside the ceiling the car sets.""")

# ------------------------------------------------------------------ 9 act 5 misleading
s = frame("Act 5 · what the data cannot tell you",
          f"Same numbers, two stories: a cut axis turns a {F('A5.gap_pct')} gap into a bar {F('A5.visual_ratio')}× taller",
          "A5.3", 9)
picture(s, SL / "A5_3_misleading_vs_honest.png", 0.6, 2.0, 12.1, 3.35, center=True)
items = [("What was manipulated", f"Only the y-axis: it starts at {F('A5.base')}, not 0. Every number is real."),
         ("The false impression", f"\"{F('A5.lead')} crushed {F('A5.second')}.\" In fact it was {F('A5.closest')} "
                                  f"constructors' title of the decade: {F('A5.gap')} points."),
         ("The fix and the principle", f"Axis from zero, values on the bars. Truthful scaling and proportional ink: "
                                       f"lie factor about {F('A5.lie_factor')} → 1.")]
for i, (hd, body) in enumerate(items):
    x = 0.6 + i * 4.1
    card(s, x, 5.5, 3.9, 1.4)
    text(s, x + 0.2, 5.62, 3.5, 1.2, [[(hd, {"bold": True, "size": 13, "color": RED})], [(body, {"size": 13})]],
         spacing=3)
notes(s, f"""Act five is about honesty. The chart on the left is deliberately misleading, and it is labelled that way. It
shows the real 2024 constructor points: {F('A5.lead')} {F('A5.lead_pts')}, {F('A5.second')} {F('A5.second_pts')}. The only
change is the y-axis, which starts at {F('A5.base')} instead of zero. A bar shows value by its length, so cutting the
axis makes {F('A5.lead')}'s bar look {F('A5.visual_ratio')} times taller, when the real gap is {F('A5.gap_pct')}. Tufte's
lie factor compares the size of the effect in the picture with the size in the data; here it is about
{F('A5.lie_factor')}, where an honest chart is one. The honest version on the right starts at zero. What makes the
misleading one dangerous is that no number on it is false. That is why every bar chart in my project starts at zero, and
why I show confidence ranges and flag small samples.""")

# ------------------------------------------------------------------ 10 tools and dashboard
s = frame("Tools and dashboard", "Three tools, one notebook, one interactive dashboard", "D.1", 10)
picture(s, CH / "D_dashboard_overview.png", 0.6, 1.75, 6.9, 5.1)
rows = [("Matplotlib", "Precise, hand-annotated story charts: the race trace, the undercut, the misleading pair."),
        ("Seaborn", "Statistics with confidence ranges: correlations, teammate duel, heatmap, regression."),
        ("Plotly", "Interactivity: hover, filters and the five-act dashboard in one HTML file.")]
for i, (tool, why) in enumerate(rows):
    y = 1.8 + i * 1.28
    card(s, 7.85, y, 4.88, 1.14)
    text(s, 8.05, y + 0.14, 4.5, 0.95, [[(tool, {"bold": True, "size": 15})], [(why, {"size": 13, "color": INK2})]],
         spacing=2)
text(s, 7.85, 5.75, 4.88, 1.0, "Plotly replaced Power BI so the whole analysis stays reproducible in a single notebook.",
     size=14, bold=True, color=INK)
notes(s, f"""The course asks for three tools, and each one does a job the others cannot do as well. Matplotlib gives me
pixel-level control, which I need for the race trace and for the misleading chart, where I control the axis exactly.
Seaborn computes statistics for me, like the bootstrap confidence ranges in the teammate chart. Plotly gives
interactivity. One change from my Primary Review: I planned Power BI, but Plotly replaced Power BI so the whole analysis
stays reproducible in a single notebook. The dashboard, on the left, is one HTML file of about {F('D.size_mb')} megabytes.
It has one filter row for season, constructor, driver and circuit, and every chart re-draws for the same selection.
It follows the same five acts, and it warns you when a selection is too small to trust.""")

# ------------------------------------------------------------------ 11 closing
s = frame("Back to the hook", f"The {F('H.changes')} position changes were a chain of cause and effect", None, 11,
          dark=True)
picture(s, DECO, 8.2, 2.0, 4.6, 3.6)
lines = [("Act 1", f"Rosberg won from pole ({F('C.circuit')}: r = {F('C.circuit_r')})."),
         ("Act 2", f"On lap {F('H.sc_lap')}, {F('H.n_sc_stops')} cars pitted at once and the order reshuffled."),
         ("Act 3", f"Hamilton made {F('C.extra_stops')} more stops than his teammate: the alarm, not the plan."),
         ("Act 4", f"Both drove the 2016 Mercedes, the car with {F('A4.mer_2016')} of all points.")]
for i, (a, t) in enumerate(lines):
    y = 2.05 + i * 0.86
    text(s, 0.6, y, 1.1, 0.7, a, size=15, bold=True, color=RED)
    text(s, 1.75, y, 6.1, 0.8, t, size=15, color=WHITE)
text(s, 0.6, 5.75, 12.1, 0.9, [[("What the data cannot tell you: ", {"bold": True, "color": WHITE}),
                                ("every result is a correlation, not an experiment. There are no tyre, weather or "
                                 "safety-car fields, so the why behind an event is always outside the data.",
                                 {"color": SOFT})]], size=14)
notes(s, f"""Let us go back to the race we started with and read it as a strategist. Act one: Rosberg started on pole and
won, at a circuit where grid and finish are linked at {F('C.circuit_r')}. Act two: on lap {F('H.sc_lap')},
{F('H.n_sc_stops')} cars pitted at once and the order reshuffled. Act three: Hamilton, the slower qualifier in the same
car, made {F('C.extra_stops')} more stops than his teammate, and his first stop came on lap {F('H.ham_first_stop')}: that
was the alarm, not the plan. Act four: both drove the 2016 Mercedes, which took {F('A4.mer_2016')} of all points that
season, which is how a car starting {F('H.ham_grid')}nd could still reach the points. And the limits: all of this is
correlation, not causation, and the data has no tyre, weather or safety-car fields. The {F('H.changes')} position
changes were never random. They were a chain of cause and effect. Thank you.""")

out = HERE / "F1_Final_Presentation.pptx"
prs.core_properties.author = prs.core_properties.last_modified_by = "Arwindh C N"
prs.core_properties.title = "Formula 1 Performance Analytics"
prs.save(out)
print("wrote", out.name, len(prs.slides), "slides")
