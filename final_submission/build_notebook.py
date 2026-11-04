"""
Builds F1_Story_Notebook.ipynb.

Markdown cells use tokens like «A2.early_chg2». They are filled from facts.json,
which the notebook itself writes in its last cell. Build pipeline (make.sh):
  1. build (tokens unfilled) -> execute -> facts.json
  2. build again (tokens filled from facts.json) -> execute -> facts.json must be unchanged
So every number in the prose is produced by a code cell.
"""
import json
import re
import sys
from pathlib import Path
from textwrap import dedent

import nbformat as nbf

HERE = Path(__file__).resolve().parent
FACTS_PATH = HERE / "facts.json"
facts = json.loads(FACTS_PATH.read_text()) if FACTS_PATH.exists() else None
TOKEN = re.compile(r"«([A-Za-z0-9_.]+)»")
missing = set()


def fill(text):
    if facts is None:
        return text

    def rep(m):
        k = m.group(1)
        if k not in facts:
            missing.add(k)
            return m.group(0)
        return facts[k]["text"]
    return TOKEN.sub(rep, text)


cells = []


def md(t):
    cells.append(nbf.v4.new_markdown_cell(fill(dedent(t).strip())))


def code(t):
    cells.append(nbf.v4.new_code_cell(dedent(t).strip()))


# =============================================================== TITLE
md("""
# Formula 1, read as a chain of cause and effect
### Drivers, constructors, race strategy and performance trends, 2015–2024

**Arwindh C N** · Roll No. CB.SC.U4CSE24207 · 23CSE353 Data Visualisation · Final Review

Most people watch a Formula 1 race as a *result*: who won. This notebook reads a race the way the
strategist on the pit wall does: as a **chain of events**. Saturday's qualifying sets the order.
Every pit stop trades places now for places later. An unexpected extra stop is an alarm bell.
And the car sets a ceiling on all of it.

**The story in five acts**

| | Headline | Question |
|---|---|---|
| Hook | One race, lap by lap | What does a race look like as a chain of events? |
| Act 1 | Saturday decides more than you think | How much does the starting position fix the result, and where? |
| Act 2 | The stop that costs four places and wins back two | What does a pit stop really cost, and does timing matter? |
| Act 3 | The hidden alarm | Is an extra pit stop a gamble, or a sign that something went wrong? |
| Act 4 | The car sets the ceiling | How much of all this is decided by which team you drive for? |
| Act 5 | What the data cannot tell you | How can a chart lie, and where are the limits of this analysis? |

**How to read this notebook.** Each section gives the claim as a headline, the question, the code,
the chart, *what this means*, a *caveat*, and *the call you would make* on the pit wall.
Every code cell starts with a label such as `Cell A2.1`. That label is printed in the output and in the
footer of every chart, so any number in the text can be traced to the cell that produced it.
All numbers are also saved to `facts.json` in the last cell.

**Tools.** Three visualization tools, each doing the job it does best:
**Matplotlib** for precise, hand-annotated story charts; **Seaborn** for statistical charts with
confidence ranges; **Plotly** for interactive charts and the dashboard.
Plotly replaced Power BI so the whole analysis stays reproducible in a single notebook.
""")

md("""
#### F1 in one minute (for readers who have never watched a race)
- **Grand Prix**: one race. A season has 17–24 of them. About 20 cars start.
- **Constructor**: a team (Mercedes, Red Bull, Ferrari, McLaren...). Each team runs **two cars**; the two drivers are **teammates** and drive the same car.
- **Qualifying**: a timed session on Saturday. The fastest lap gets the best starting place.
- **Grid**: the starting order. **Pole position** = starting first.
- **Pit stop**: the car drives into the pit lane for new tyres. It costs about 24 seconds, which on track is several places.
- **Undercut**: stopping *before* a rival. Your new tyres are faster, so when the rival stops later you may come out ahead.
- **Safety car**: after a crash, a safety car slows the whole field. A pit stop costs less time then, so many cars stop at once.
- **Classified**: the driver gets an official finishing position (they finished, or covered at least 90% of the race).
- **DNF** ("did not finish"): the car retired (crash, engine failure, and so on).
- **Points**: the top 10 score points (25 for a win). Points decide the drivers' and constructors' championships.
""")

# =============================================================== SETUP
md("""
## Setup
`Cell S.1` loads the tools and fixes **one colour meaning for the whole project**:
black, white and greys for context, and **one red accent for the thing to look at**.
It also defines two helpers: `fact()` records every number used in the text, and
`story_fig()` gives every chart the same layout (conclusion title, plain subtitle, source footer).
""")

code(r'''
# Cell S.1 - tools, one colour meaning, and helpers used by every chart
import os, json, textwrap, warnings
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns
import plotly
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from scipy import stats
from IPython.display import display, Image

warnings.filterwarnings("ignore", category=FutureWarning)
pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 30)
CHARTS = Path("charts"); CHARTS.mkdir(exist_ok=True)

# One colour meaning for the whole project: black/white base, ONE red accent.
INK, INK2, MUTED, LIGHT, GRID, RED = "#1A1A1A", "#4D4D4D", "#767676", "#C9C9C9", "#EBEBEB", "#C8102E"
DOT = "#9A9A9A"                                  # context markers
sns.set_theme(style="whitegrid", rc={
    "font.family": ["Arial", "DejaVu Sans"], "font.size": 10.5,
    "axes.edgecolor": LIGHT, "axes.labelcolor": INK2, "axes.labelsize": 10.5,
    "xtick.color": INK2, "ytick.color": INK2, "xtick.labelsize": 9.5, "ytick.labelsize": 9.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.titlesize": 11.5, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.titlecolor": INK, "legend.frameon": False, "figure.dpi": 100})

# Plotly: interactive in Jupyter, plus a static PNG for the report and slides.
pio.renderers.default = "plotly_mimetype+notebook_connected"
for b in ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
          "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"]:
    if Path(b).exists():
        os.environ.setdefault("BROWSER_PATH", b)   # kaleido needs a Chromium browser for PNG export
        break

# ---- every number used in the text goes through fact() -----------------------
FACTS, CHART_FILES, _CELL = {}, {}, {"id": "S.1"}

def cell(cid, name):
    _CELL["id"] = cid
    print(f"── Cell {cid} · {name} ──")

def fact(key, value, fmt="{}"):
    if isinstance(value, (np.integer,)): value = int(value)
    if isinstance(value, (np.floating, float)): value = float(value)
    if isinstance(value, (np.bool_,)): value = bool(value)
    text = fmt.format(value)
    FACTS[key] = {"value": value, "text": text, "cell": _CELL["id"]}
    print(f"   [{key}] {text}")
    return value

def T(key):                      # the formatted text of a fact, for chart titles
    return FACTS[key]["text"]

# ---- one layout for every Matplotlib/Seaborn chart ----------------------------
def story_fig(title, sub, width=11.0, body=5.2, mosaic=None, **kw):
    """Figure with a conclusion title, a plain-English subtitle and a source footer."""
    mosaic = mosaic or [["main"]]
    ncol = len(mosaic[0])
    t_lines = textwrap.wrap(title, int(width * 9.0))
    s_lines = textwrap.wrap(sub, int(width * 14.5))
    head = (len(t_lines) * 21 + 10 + len(s_lines) * 14.5 + 8) / 72
    foot = 0.30
    layout = [["head"] * ncol] + mosaic + [["foot"] * ncol]
    nb = len(mosaic)
    fig, ax = plt.subplot_mosaic(layout, figsize=(width, head + body + foot),
                                 height_ratios=[head] + [body / nb] * nb + [foot],
                                 layout="constrained", **kw)
    for k in ("head", "foot"):
        ax[k].set_axis_off()
        ax[k].set_label(k)
    h = ax["head"]
    h.annotate("\n".join(t_lines), (0.012, 1), xycoords=("figure fraction", "axes fraction"),
               va="top", ha="left", fontsize=15, fontweight="bold", color=INK, linespacing=1.15)
    h.annotate("\n".join(s_lines), (0.012, 1), xycoords=("figure fraction", "axes fraction"),
               xytext=(0, -(len(t_lines) * 21 + 6)), textcoords="offset points",
               va="top", ha="left", fontsize=10.5, color=INK2, linespacing=1.3)
    ax["foot"].annotate(f"Source: Ergast-lineage Formula 1 data, 2015–2024  ·  Notebook cell {_CELL['id']}",
                        (0.012, 0), xycoords=("figure fraction", "axes fraction"),
                        va="bottom", fontsize=8, color=MUTED)
    return fig, ax

def save(fig, name):
    path = CHARTS / f"{name}.png"
    fig.savefig(path, dpi=200, bbox_inches="tight", pad_inches=0.18, facecolor="white")
    CHART_FILES[_CELL["id"]] = str(path)
    # A title-free copy for the slides, where the slide title carries the conclusion.
    hidden = [a for a in fig.axes if a.get_label() in ("head", "foot")]
    for a in hidden:
        a.set_visible(False)
    (CHARTS / "slides").mkdir(exist_ok=True)
    fig.savefig(CHARTS / "slides" / f"{name}.png", dpi=200, bbox_inches="tight", pad_inches=0.12, facecolor="white")
    for a in hidden:
        a.set_visible(True)
    plt.show()

def plotly_story(fig, title, sub, height=480, width=1150):
    fig.update_layout(
        template="simple_white", width=width, height=height,
        font=dict(family="Arial", size=12, color=INK2),
        title=dict(text=f"<b>{title}</b><br><span style='font-size:13px;color:{INK2}'>{sub}</span>",
                   x=0.01, xanchor="left", y=0.955, yanchor="top", font=dict(size=19, color=INK)),
        margin=dict(l=70, r=30, t=110, b=70), hoverlabel=dict(bgcolor="white", font_size=12),
        showlegend=False)
    fig.add_annotation(text=f"Source: Ergast-lineage Formula 1 data, 2015–2024 · Notebook cell {_CELL['id']}",
                       xref="paper", yref="paper", x=0, y=-0.17, showarrow=False, xanchor="left", yanchor="top",
                       font=dict(size=10, color=MUTED))
    return fig

def save_plotly(fig, name):
    fig.write_html(CHARTS / f"{name}.html", include_plotlyjs="cdn")
    try:
        fig.write_image(CHARTS / f"{name}.png", scale=2)
        CHART_FILES[_CELL["id"]] = str(CHARTS / f"{name}.png")
        bare = go.Figure(fig)                                     # title-free copy for the slides
        bare.update_layout(title=None, margin=dict(t=45, b=40))
        bare.layout.annotations = [a for a in bare.layout.annotations if "Source:" not in (a.text or "")]
        (CHARTS / "slides").mkdir(exist_ok=True)
        bare.write_image(CHARTS / "slides" / f"{name}.png", scale=2)
    except Exception as e:                                         # no browser for kaleido
        print("PNG export skipped:", type(e).__name__, e)
    fig.show()

print("pandas", pd.__version__, "| matplotlib", mpl.__version__, "| seaborn", sns.__version__,
      "| plotly", plotly.__version__)
''')

# =============================================================== DATA PREP
md("""
## 1 · Data preparation
**Dataset.** The Ergast-lineage Formula 1 dataset (the data family now served by the Jolpica F1 API):
14 linked CSV tables. We keep the 2015–2024 seasons: **209 races**, 53 drivers, 18 constructors.
The tables link through ID numbers (`raceId`, `driverId`, `constructorId`, `statusId`).
We always join on these IDs, never on names, because names change (Toro Rosso became AlphaTauri, then RB)
and are spelled differently across tables.

The cleaning code below is the same code as `f1_prep.py`. Each step is numbered P1–P11.
The final step checks every row count against the cleaned workbook approved in the Primary Review.
""")

prep = (HERE / "f1_prep.py").read_text().split("\n# %%\n")[1:]
prep_titles = {
    0: "Imports and paths", 1: "Read the raw files and mark missing values", 2: "Seasons 2015-2024, races, drivers, teams",
    3: "Race results: classified vs genuine DNF", 4: "Qualifying times to seconds", 5: "Pit stops",
    6: "Lap-by-lap positions", 7: "Sprint results", 8: "Final standings = last round of each season",
    9: "One merged driver-race table", 10: "Cross-check with the Primary Review workbook", 11: "Save clean tables"}
prep_notes = {
    1: "**P1.** The raw files write a missing value as `\\N`. We tell pandas that `\\N` means missing.",
    3: "**P3.** Two flags that sound alike but are not: *classified* (has a finishing position) and "
       "*genuine DNF* (status is not \"Finished\" or \"+N Lap(s)\"). A lapped car is **not** a DNF. "
       "«P.n_dnf_classified» cars are both: they retired late but had covered 90% of the race, so they still got a position. "
       "`grid = 0` means a pit-lane start, so the grid slot is set to missing.",
    5: "**P5.** Pit-stop `duration` is the *total time in the pit lane* (entry to exit), not the stationary tyre change "
       "you see on TV. The text column switches to `m:ss` for very long stops, so we use the exact milliseconds column.",
    8: "**P8.** The standings tables are *cumulative*: there is a row after every race. "
       "The season's final table is the one after the last round.",
    9: "**P9.** A driver with no pit-stop row made 0 stops, but only in races that have pit data. "
       "The 2021 Belgian GP has no pit data at all, so its stop counts stay unknown.",
}
for i, chunk in enumerate(prep):
    if i in prep_notes:
        md(prep_notes[i])
    code(f'cell("P.{i}", "{prep_titles[i]}")\n' + chunk.strip())

md("""
**Data quality summary.** «P.n_results» race entries; «P.n_unclassified» not classified; «P.n_dnf» genuine DNFs;
«P.n_pitlane» pit-lane starts; «P.n_long_stops» pit stops of 60 seconds or more (red flags and repairs).
The median pit-lane time is «P.pit_median_normal» s for normal stops (under 60 s).
""")

code(r'''
cell("P.12", "Data quality facts")
fact("P.n_results", len(results), "{:,}")
fact("P.n_races", races.shape[0])
fact("P.n_drivers", results["driverId"].nunique())
fact("P.n_constructors", results["constructorId"].nunique())
fact("P.n_unclassified", int((~results["is_classified"]).sum()), "{:,}")
fact("P.n_dnf", int(results["is_dnf"].sum()), "{:,}")
fact("P.n_dnf_classified", int((results["is_dnf"] & results["is_classified"]).sum()))
fact("P.n_pitlane", int(results["grid"].isna().sum()))
fact("P.n_stops", len(pit_stops), "{:,}")
fact("P.n_long_stops", int((pit_stops["duration_s"] >= 60).sum()))
fact("P.pit_median_normal", pit_stops.loc[pit_stops["duration_s"] < 60, "duration_s"].median(), "{:.1f}")
fact("P.pit_median_all", pit_stops["duration_s"].median(), "{:.1f}")
fact("P.n_laps", len(lap_times), "{:,}")
fact("P.n_quali", len(qualifying), "{:,}"); fact("P.n_sprint", len(sprint))
fact("P.n_dfinal", len(driver_final)); fact("P.n_cfinal", len(constructor_final))
fact("P.n_circuits", races["circuitId"].nunique())
fact("P.raw_results", len(raw["results"]), "{:,}"); fact("P.raw_races", len(raw["races"]), "{:,}")
fact("P.raw_laps", len(raw["lap_times"]), "{:,}"); fact("P.first_year", int(raw["races"]["year"].min()))
fact("P.raw_cols", raw["results"].shape[1]); fact("P.clean_cols", race_level.shape[1])
fact("P.no_pit_race", ", ".join(races.loc[~races["raceId"].isin(PIT_RACE_IDS), "race_label"]))
display(results.head(3))
''')

# =============================================================== HOOK
md("""
---
## Hook · «H.changes» position changes in one race, and the pole-sitter still won
**The question.** What does a race look like if you stop reading only the result,
and follow every car on every lap?

To pick the race, `Cell H.1` scores all «H.n_races» races by how much the running order moved.
For every car and every lap, we count how many places it gained or lost since the previous lap, then add it all up.
""")

code(r'''
cell("H.1", "Rank all races by how much the running order moved")
moves = lap_times.sort_values(["raceId", "driverId", "lap"]).copy()
moves["moved"] = moves.groupby(["raceId", "driverId"])["position"].diff().abs()
churn = (moves[moves["lap"] > 1].groupby("raceId")
         .agg(position_changes=("moved", "sum"), laps=("lap", "max"))
         .reindex(races["raceId"]).fillna({"position_changes": 0})   # 2021 Belgian GP: 1 lap only -> 0 changes
         .join(results.groupby("raceId").agg(cars=("driverId", "size"), dnfs=("is_dnf", "sum")))
         .join(races.set_index("raceId")["race_label"]))
churn["changes_per_lap"] = churn["position_changes"] / churn["laps"]
churn = churn.sort_values("position_changes", ascending=False)
display(churn.head(6).round(1))

HOOK = churn.index[0]
hook = churn.loc[HOOK]
fact("H.race", hook["race_label"])
fact("H.n_races", len(churn))
fact("H.changes", int(hook["position_changes"]), "{:,}")
fact("H.per_lap", hook["changes_per_lap"], "{:.0f}")
fact("H.median_changes", churn["position_changes"].median(), "{:.0f}")
fact("H.cars", int(hook["cars"]))
fact("H.dnfs", int(hook["dnfs"]))
fact("H.second", churn.iloc[1]["race_label"])
fact("H.second_changes", int(churn.iloc[1]["position_changes"]), "{:,}")
''')

md("""
**Why this race.** The «H.race» had the most position changes of all «H.n_races» races
(«H.changes», about «H.per_lap» per lap; the typical race has «H.median_changes»).
Every car finished (genuine retirements: «H.dnfs»), so all «H.cars» cars run from start to finish and every line in the chart is complete.
And, as the closing section shows, every act of this story happens inside it.
""")

code(r'''
cell("H.2", "Bump chart of the hook race")
hr = results[results["raceId"] == HOOK].set_index("driverId")
ham = hr.index[hr["driverRef"] == "hamilton"][0]
ros = hr.index[hr["driverRef"] == "rosberg"][0]
trace = lap_times[lap_times["raceId"] == HOOK].pivot(index="lap", columns="driverId", values="position")
trace.loc[0] = hr["grid"]                       # lap 0 = starting grid
trace = trace.sort_index()
hook_stops = pit_stops[pit_stops["raceId"] == HOOK]
lap_med = lap_times[lap_times["raceId"] == HOOK].groupby("lap")["lap_ms"].median()
slow = lap_med[lap_med > 1.25 * lap_med.median()].index      # laps run far slower than normal
sc_lap = int(slow.min()) - 1
last = int(trace.index.max())

fact("H.ham_grid", int(hr.loc[ham, "grid"])); fact("H.ham_finish", int(hr.loc[ham, "position"]))
fact("H.ham_stops", int((hook_stops["driverId"] == ham).sum()))
fact("H.ros_stops", int((hook_stops["driverId"] == ros).sum()))
fact("H.ham_first_stop", int(hook_stops.loc[hook_stops["driverId"] == ham, "lap"].min()))
fact("H.slow_first", int(slow.min())); fact("H.slow_last", int(slow.max()))
fact("H.sc_lap", sc_lap); fact("H.n_sc_stops", int((hook_stops["lap"] == sc_lap).sum()))
fact("H.laps", last)

fig, ax = story_fig(f"{T('H.changes')} position changes in one race, and the pole-sitter still won",
                    f"{T('H.race')}: where each of the {T('H.cars')} cars ran at the end of every lap "
                    "(lap 0 = starting grid). Dots are pit stops. Red = Lewis Hamilton, "
                    "black = Nico Rosberg: same team, same car.", width=12, body=6.3)
a = ax["main"]
a.axvspan(slow.min() - 0.5, slow.max() + 0.5, color=GRID, lw=0, zorder=0)
for d in trace.columns:
    if d not in (ham, ros):
        a.plot(trace.index, trace[d], color=LIGHT, lw=1.2, zorder=1, solid_joinstyle="round")
for d, col, lw in [(ros, INK, 2.4), (ham, RED, 2.6)]:
    a.plot(trace.index, trace[d], color=col, lw=lw, zorder=3, solid_joinstyle="round", solid_capstyle="round")
for s in hook_stops.itertuples():
    d, lap = int(s.driverId), int(s.lap)
    col, size, z = (RED, 50, 5) if d == ham else (INK, 50, 5) if d == ros else (DOT, 20, 2)
    a.scatter(lap, trace.loc[lap, d], s=size, color=col, edgecolor="white", linewidth=1.2, zorder=z)
for d, row in hr.iterrows():                    # finishing order on the right
    hl = d in (ham, ros)
    a.text(last + 0.9, row["positionOrder"], row["code"], va="center", fontsize=8.5,
           color=INK if hl else MUTED, fontweight="bold" if hl else "normal")
box = dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.92)
a.annotate(f"Lap {T('H.sc_lap')}: {T('H.n_sc_stops')} cars pit at once.\n"
           f"Laps {T('H.slow_first')}–{T('H.slow_last')} run slowly\n(likely a safety car).",
           xy=(slow.max() + 0.5, 3), xytext=(slow.max() + 2.5, 3.2), fontsize=9.5, color=INK, va="center",
           bbox=box, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8), zorder=6)
a.annotate(f"Lap {T('H.ham_first_stop')}: Hamilton pits,\nthe first of his {T('H.ham_stops')} stops",
           xy=(1, trace.loc[1, ham]), xytext=(9, 19.6), fontsize=9.5, color=INK, va="center", bbox=box,
           arrowprops=dict(arrowstyle="-", color=RED, lw=1), zorder=6)
a.annotate(f"Rosberg: pole to win,\n{T('H.ros_stops')} stops", xy=(last, 1), xytext=(last - 13, 2.6),
           fontsize=9.5, color=INK, va="center", bbox=box, arrowprops=dict(arrowstyle="-", color=INK, lw=1), zorder=6)
a.annotate(f"Hamilton: {T('H.ham_grid')}nd to {T('H.ham_finish')}th,\n{T('H.ham_stops')} stops",
           xy=(last, hr.loc[ham, "position"]), xytext=(last - 15, 11.5), fontsize=9.5, color=INK, va="center",
           bbox=box, arrowprops=dict(arrowstyle="-", color=RED, lw=1), zorder=6)
a.set_ylim(len(hr) + 0.7, 0.3)
a.set_yticks([1, 5, 10, 15, 20, len(hr)])
a.set_xlim(-0.6, last + 2.6)
a.set_xticks([0] + list(range(10, last + 1, 10)))
a.set_xticklabels(["Grid"] + [str(x) for x in range(10, last + 1, 10)])
a.set_xlabel("Lap"); a.set_ylabel("Position (1 = leading)")
a.grid(axis="x", visible=False)
save(fig, "H2_bump_chart_hook_race")
''')

md("""
**What this means.** Under the result («H.race»: Rosberg first) sits a chain of events.
Hamilton started «H.ham_grid»nd, stopped on lap «H.ham_first_stop», and made «H.ham_stops» stops in total to climb to «H.ham_finish»th.
On lap «H.sc_lap», «H.n_sc_stops» cars stopped together, just before laps «H.slow_first»–«H.slow_last» ran slowly.
The lines cross most where pit stops cluster: a pit stop *moves* a car through the order.

**Caveat.** One overtake counts as two position changes (one car up, one car down), and pit stops count too.
The dataset has no safety-car field, so the slow laps are *inferred* from lap times.
The data also cannot say *why* Hamilton stopped on lap «H.ham_first_stop» (race reports say first-lap damage).

**The call you would make.** Do not read a race from the result. Read it from the moves.
""")

# =============================================================== ACT 1
md("""
---
## Act 1 · Saturday decides more than you think
**The question.** If you know where a driver *starts*, how well can you guess where they *finish*?
And is that the same at every track?

`Cell A1.1` starts with the obvious view: all races pooled together.
We measure the link with the **correlation coefficient r**: 0 means no link, 1 means a perfect straight-line link.
Only classified finishers with a real grid slot are used (pit-lane starts are excluded).
""")

code(r'''
cell("A1.1", "Grid vs finish, all races pooled")
gf = results.dropna(subset=["grid", "position"]).copy()
r_pooled, p_pooled = stats.pearsonr(gf["grid"], gf["position"])
fact("A1.n", len(gf), "{:,}")
fact("A1.pooled_r", r_pooled, "{:.2f}")
fact("A1.r2", r_pooled ** 2 * 100, "{:.0f}%")
wins = results[results["position"] == 1]
fact("A1.pole_win", (wins["grid"] == 1).mean() * 100, "{:.0f}%")
fact("A1.front_row_win", (wins["grid"] <= 2).mean() * 100, "{:.0f}%")
fact("A1.top3_win", (wins["grid"] <= 3).mean() * 100, "{:.0f}%")
mean_by_grid = gf.groupby("grid")["position"].mean()
fact("A1.p1_avg_finish", mean_by_grid.loc[1], "{:.1f}")
fact("A1.p10_avg_finish", mean_by_grid.loc[10], "{:.1f}")
fact("A1.p20_avg_finish", mean_by_grid.loc[20], "{:.1f}")

fig, ax = story_fig(f"Start near the front, finish near the front (r = {T('A1.pooled_r')})",
                    "Each square counts finishes (darker = more). Black line = average finish for each starting slot. "
                    f"Red line = finishing exactly where you started. {T('A1.n')} classified finishes, 2015–2024.",
                    width=10.5, body=6.0)
a = ax["main"]
sns.histplot(data=gf, x="grid", y="position", discrete=(True, True), cmap="Greys", ax=a,
             cbar=True, cbar_kws={"label": "Number of finishes", "shrink": 0.55, "pad": 0.01})
a.plot([1, 20], [1, 20], color=RED, lw=1.8, zorder=4, solid_capstyle="round")
mbg = mean_by_grid.loc[:20]                      # slots 21-22 exist only in 22-car seasons: too few finishes
a.plot(mbg.index, mbg.values, color=INK, lw=2, marker="o", ms=4.5,
       markeredgecolor="white", markeredgewidth=1, zorder=5)
a.annotate("Finish = start", xy=(19, 19), xytext=(15.8, 21.3), fontsize=9.5, color=INK,
           arrowprops=dict(arrowstyle="-", color=RED, lw=1))
a.annotate(f"Start 1st: average finish {T('A1.p1_avg_finish')}", xy=(1, mean_by_grid.loc[1]),
           xytext=(3.2, 1.0), fontsize=9.5, color=INK, va="center",
           arrowprops=dict(arrowstyle="-", color=INK, lw=0.8))
a.annotate(f"Start 20th: average finish {T('A1.p20_avg_finish')}", xy=(20, mean_by_grid.loc[20]),
           xytext=(21.9, 11.4), fontsize=9.5, color=INK, va="center", ha="right",
           arrowprops=dict(arrowstyle="-", color=INK, lw=0.8))
mx = int(max(gf["grid"].max(), gf["position"].max()))
a.set_xlim(0.4, mx + 0.6); a.set_ylim(mx + 0.6, 0.4)
a.set_xticks([1, 5, 10, 15, 20]); a.set_yticks([1, 5, 10, 15, 20])
a.set_xlabel("Starting grid position"); a.set_ylabel("Finishing position")
a.grid(False)
save(fig, "A1_1_grid_vs_finish_pooled")
''')

md("""
**What this means.** Across «A1.n» finishes, r = «A1.pooled_r»: a strong link.
Pole position won «A1.pole_win» of all races, and «A1.top3_win» of winners started in the top three.
But the black line is flatter than the red one. Front-runners finish slightly *behind* their slot on average
(P1 averages P«A1.p1_avg_finish»), and back-markers finish *ahead* of theirs (P20 averages P«A1.p20_avg_finish»).
So Sunday can move the order. The next question is *where*.

**Caveat.** Only classified finishers are counted. Cars that retire drop out, which lifts everyone behind them.
That is part of why back-markers seem to "gain".
""")

code(r'''
cell("A1.2", "Grid-finish correlation circuit by circuit")
def circuit_r(d):
    r = d["grid"].corr(d["position"])
    n = len(d)
    z, se = np.arctanh(r), 1 / np.sqrt(n - 3)                    # Fisher 95% confidence range
    return pd.Series({"r": r, "n": n, "races": d["raceId"].nunique(),
                      "lo": np.tanh(z - 1.96 * se), "hi": np.tanh(z + 1.96 * se)})
byc = (gf.groupby(["circuitId", "circuit_short"]).apply(circuit_r, include_groups=False)
       .reset_index().query("n >= 40").sort_values("r", ascending=False).reset_index(drop=True))
display(byc.round(3))
top, bot = byc.iloc[0], byc.iloc[-1]
med = byc["r"].median()
fact("A1.n_circuits", len(byc))
fact("A1.median_r", med, "{:.2f}")
fact("A1.top_circuit", top["circuit_short"]); fact("A1.top_r", top["r"], "{:.2f}")
fact("A1.top_races", int(top["races"]))
fact("A1.second_circuit", byc.iloc[1]["circuit_short"]); fact("A1.second_r", byc.iloc[1]["r"], "{:.2f}")
fact("A1.third_circuit", byc.iloc[2]["circuit_short"]); fact("A1.third_r", byc.iloc[2]["r"], "{:.2f}")
fact("A1.bottom_circuit", bot["circuit_short"]); fact("A1.bottom_r", bot["r"], "{:.2f}")
fact("A1.bottom_races", int(bot["races"])); fact("A1.bottom_n", int(bot["n"]))
fact("A1.bottom_lo", bot["lo"], "{:.2f}"); fact("A1.bottom_hi", bot["hi"], "{:.2f}")
fact("A1.second_bottom", byc.iloc[-2]["circuit_short"]); fact("A1.second_bottom_r", byc.iloc[-2]["r"], "{:.2f}")
fact("A1.third_bottom", byc.iloc[-3]["circuit_short"]); fact("A1.third_bottom_r", byc.iloc[-3]["r"], "{:.2f}")

fig, ax = story_fig(f"{T('A1.top_circuit')} locks the order in. {T('A1.bottom_circuit')} lets it go.",
                    f"Correlation between grid and finish at each circuit ({T('A1.n_circuits')} circuits with 40+ classified "
                    "finishes, 2015–2024). Grey bar = 95% confidence range. Stems show the distance from the median circuit.",
                    width=10.5, body=7.6)
a = ax["main"]
y = np.arange(len(byc))
a.hlines(y, byc["lo"], byc["hi"], color=GRID, lw=6, zorder=1)
a.hlines(y, med, byc["r"], color=LIGHT, lw=1.4, zorder=2)
a.axvline(med, color=INK2, lw=1, zorder=2)
colors = [RED if c == top["circuit_short"] else INK for c in byc["circuit_short"]]
sns.scatterplot(x=byc["r"], y=y, hue=byc["circuit_short"], palette=dict(zip(byc["circuit_short"], colors)),
                s=70, edgecolor="white", linewidth=1.5, legend=False, ax=a, zorder=3)
a.scatter(bot["r"], len(byc) - 1, s=70, facecolor="white", edgecolor=INK, linewidth=1.6, zorder=4)
a.set_yticks(y); a.set_yticklabels(byc["circuit_short"]); a.invert_yaxis()
a.text(med + 0.006, -1.1, f"median circuit r = {T('A1.median_r')}", ha="left", fontsize=9, color=INK2)
a.annotate(f"Only {T('A1.bottom_races')} races ({T('A1.bottom_n')} finishes):\nwide range, treat with care",
           xy=(bot["r"], len(byc) - 1), xytext=(bot["r"] + 0.03, len(byc) - 4.2), fontsize=9.5, color=INK,
           arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
a.text(med - 0.01, 0, "Street circuit: overtaking is almost impossible", ha="right", va="center",
       fontsize=9.5, color=INK)
a.set_xlim(0.25, 1.0); a.set_ylim(len(byc) - 0.4, -1.8)
a.set_xlabel("Correlation between grid and finish (r)"); a.set_ylabel("")
a.grid(axis="y", visible=False)
save(fig, "A1_2_circuit_lollipop")
''')

md("""
**What this means.** At «A1.top_circuit» (r = «A1.top_r») where you start is almost where you finish:
the street circuit is too narrow to overtake. «A1.second_circuit» («A1.second_r») and «A1.third_circuit» («A1.third_r») follow.
At the other end, «A1.third_bottom» («A1.third_bottom_r»), «A1.second_bottom» («A1.second_bottom_r») and
«A1.bottom_circuit» («A1.bottom_r») leave room for Sunday to change the order.
The median circuit sits at r = «A1.median_r». Grid position is never unimportant. It is only *more* or *less* important.

**Caveat.** «A1.bottom_circuit» hosted only «A1.bottom_races» races in this period («A1.bottom_n» finishes),
so its confidence range runs from «A1.bottom_lo» to «A1.bottom_hi». Its exact rank is not reliable.
Correlation shows a link, not a cause: fast cars both qualify well *and* race well.

> **The call you would make.** At «A1.top_circuit», «A1.second_circuit» and «A1.third_circuit», treat qualifying as the race.
> At «A1.second_bottom» or «A1.third_bottom», a poor grid slot can still be fixed on Sunday, so do not risk the car on Saturday.
""")

# =============================================================== ACT 2
md("""
---
## Act 2 · The stop that costs four places and wins back two
**The question.** A pit stop costs about «P.pit_median_normal» seconds. How many places is that,
and does it matter *when* you stop?

`Cell A2.1` takes every driver's **first** pit stop and reads their position on three laps from the lap-by-lap table:
the lap *before* the stop, 2 laps after, and 10 laps after. Then it splits each race's first stops into thirds:
**early**, **middle** and **late** stoppers *in that race*.
""")

code(r'''
cell("A2.1", "Track position around each first pit stop")
first = pit_stops[pit_stops["stop"] == 1][["raceId", "driverId", "lap"]].rename(columns={"lap": "L"})
pos = lap_times.set_index(["raceId", "driverId", "lap"])["position"]
for col, off in {"p_before": -1, "p_plus2": 2, "p_plus10": 10}.items():
    first[col] = pos.reindex(pd.MultiIndex.from_arrays(
        [first["raceId"], first["driverId"], first["L"] + off])).to_numpy()
und = first.dropna(subset=["p_before", "p_plus2", "p_plus10"]).copy()
und["chg2"] = und["p_before"] - und["p_plus2"]       # negative = places lost
und["chg10"] = und["p_before"] - und["p_plus10"]
und["pct"] = und.groupby("raceId")["L"].rank(method="average", pct=True)
und["timing"] = pd.cut(und["pct"], [0, 1/3, 2/3, 1], labels=["Early", "Middle", "Late"], include_lowest=True)
und = und.merge(results[["raceId", "driverId", "constructorId", "year", "circuitId"]], on=["raceId", "driverId"])
tab = und.groupby("timing", observed=True).agg(n=("chg2", "size"), chg2=("chg2", "mean"), se2=("chg2", "sem"),
                                                chg10=("chg10", "mean"), se10=("chg10", "sem"))
tab["won_back"] = tab["chg10"] - tab["chg2"]
display(tab.round(2))
fact("A2.n", len(und), "{:,}")
for t in ["Early", "Middle", "Late"]:
    k = t.lower()
    fact(f"A2.{k}_n", int(tab.loc[t, "n"]), "{:,}")
    fact(f"A2.{k}_chg2", tab.loc[t, "chg2"], "{:+.1f}")
    fact(f"A2.{k}_chg10", tab.loc[t, "chg10"], "{:+.1f}")
    fact(f"A2.{k}_lost2", -tab.loc[t, "chg2"], "{:.1f}")
    fact(f"A2.{k}_back", tab.loc[t, "won_back"], "{:.1f}")
fact("A2.early_lost2_round", round(-tab.loc["Early", "chg2"]), "{:.0f}")
''')

code(r'''
cell("A2.2", "Undercut chart: before, +2 laps, +10 laps")
fig, ax = story_fig(f"Early stoppers lose {T('A2.early_lost2_round')} places, then win back {T('A2.early_back')} of them",
                    "Average change in track position around each driver's first pit stop "
                    f"({T('A2.n')} stops, 2015–2024). 0 = position on the lap before stopping. "
                    "Early, middle and late = first, middle and last third of that race's first stops. "
                    "Whiskers = 95% confidence range.", width=10.5, body=5.4)
a = ax["main"]
xs = [0, 1, 2]
style = {"Early": (RED, 2.8, 5), "Middle": (DOT, 2.0, 3), "Late": (INK2, 2.2, 4)}
for t, (col, lw, z) in style.items():
    ys = [0, tab.loc[t, "chg2"], tab.loc[t, "chg10"]]
    es = [0, 1.96 * tab.loc[t, "se2"], 1.96 * tab.loc[t, "se10"]]
    a.plot(xs, ys, color=col, lw=lw, zorder=z, solid_capstyle="round")
    a.errorbar(xs[1:], ys[1:], yerr=es[1:], fmt="none", ecolor=col, elinewidth=1.4, capsize=0, zorder=z)
    a.scatter(xs, ys, s=60, color=col, edgecolor="white", linewidth=1.5, zorder=z + 1)
    nudge = {"Early": -0.16, "Middle": 0.16, "Late": 0.0}[t]          # Early and Middle end almost together
    a.text(2.08, ys[2] + nudge, f"{t}: {ys[2]:+.1f}", va="center", fontsize=10, color=INK,
           fontweight="bold" if t == "Early" else "normal")
a.annotate(f"Early stoppers drop {T('A2.early_lost2')} places:\nrivals on old tyres are still ahead",
           xy=(1, tab.loc["Early", "chg2"]), xytext=(0.12, -3.55), fontsize=9.5, color=INK,
           arrowprops=dict(arrowstyle="-", color=RED, lw=1))
a.annotate(f"...then win back {T('A2.early_back')} as rivals stop.\nLate stoppers win back only {T('A2.late_back')}.",
           xy=(1.5, (tab.loc["Early", "chg2"] + tab.loc["Early", "chg10"]) / 2), xytext=(1.12, -0.55),
           fontsize=9.5, color=INK, arrowprops=dict(arrowstyle="-", color=RED, lw=1))
a.axhline(0, color=INK2, lw=1, zorder=1)
a.set_xticks(xs); a.set_xticklabels(["Lap before\nthe stop", "2 laps after", "10 laps after"])
a.set_xlim(-0.15, 2.55); a.set_ylim(-4.6, 0.5)
a.set_ylabel("Places gained (+) or lost (−)")
a.grid(axis="x", visible=False)
save(fig, "A2_2_undercut_slope")
''')

md("""
**What this means.** Every first stop costs places at once: early stoppers drop «A2.early_lost2», middle «A2.middle_lost2»,
late «A2.late_lost2». The difference is what happens next. When early stoppers' rivals make *their* stops,
early stoppers win back «A2.early_back» places and end at «A2.early_chg10». Late stoppers win back only «A2.late_back»
and end worst, at «A2.late_chg10». This is the **undercut** in numbers: the early stop looks bad on the TV screen for
a couple of laps, and that is the strategy working.

**Caveat.** This is *track position*, not time. A driver can fall a place yet close the gap in seconds.
The thirds are relative to each race, so "early" at a one-stop race differs from "early" at a three-stop race.
Some early stops are forced (damage, punctures). `Cell A2.3` checks that these do not drive the result.
""")

code(r'''
cell("A2.3", "Sensitivity: drop first stops in the first 5 laps (often damage)")
und6 = und[und["L"] > 5].copy()
und6["pct"] = und6.groupby("raceId")["L"].rank(method="average", pct=True)
und6["timing"] = pd.cut(und6["pct"], [0, 1/3, 2/3, 1], labels=["Early", "Middle", "Late"], include_lowest=True)
t6 = und6.groupby("timing", observed=True)[["chg2", "chg10"]].mean()
display(t6.round(2))
fact("A2.s_n", len(und6), "{:,}")
fact("A2.s_early_chg2", t6.loc["Early", "chg2"], "{:+.1f}"); fact("A2.s_early_chg10", t6.loc["Early", "chg10"], "{:+.1f}")
fact("A2.s_late_chg2", t6.loc["Late", "chg2"], "{:+.1f}"); fact("A2.s_late_chg10", t6.loc["Late", "chg10"], "{:+.1f}")
''')

md("""
**Robustness.** Without the stops in the first 5 laps («A2.s_n» stops left), early stoppers still go
«A2.s_early_chg2» then «A2.s_early_chg10», and late stoppers «A2.s_late_chg2» then «A2.s_late_chg10». Same pattern.

> **The call you would make.** If your car can survive two or three exposed laps in traffic, stop first.
> The places you lose on the screen are mostly a loan, and the late stopper is the one who never gets them back.
""")

# =============================================================== ACT 3
md("""
---
## Act 3 · The hidden alarm
This act chains **three tables**: Qualifying, Pit Stops and Race Results.
The link between them is derived: for every race, we find each driver's **teammate** (the other car in the same team).
Teammates drive the same car, so comparing them removes the biggest factor in F1, the car.

**The question.** When one teammate makes more pit stops than the other, what does it tell us?
We start with what most fans see, then test what they assume.
""")

code(r'''
cell("A3.1", "Build teammate pairs: slower vs faster qualifier")
tm = race_level.dropna(subset=["quali_pos"])
tm = tm[tm["raceId"].isin(PIT_RACE_IDS)]                                # stop counts must be known
tm = tm[tm.groupby(["raceId", "constructorId"])["driverId"].transform("size") == 2]
tm = tm.sort_values(["raceId", "constructorId", "quali_pos"]).assign(
    k=lambda d: d.groupby(["raceId", "constructorId"]).cumcount())
fa = tm[tm["k"] == 0].set_index(["raceId", "constructorId"])                # faster qualifier
sl = tm[tm["k"] == 1].set_index(["raceId", "constructorId"])                # slower qualifier
pairs = pd.DataFrame({
    "year": sl["year"], "circuitId": sl["circuitId"],
    "slow_id": sl["driverId"], "fast_id": fa["driverId"],
    "q_gap": sl["quali_pos"] - fa["quali_pos"],                            # places behind teammate on Saturday
    "stop_diff": sl["n_stops"] - fa["n_stops"],                            # StopDiff
    "slow_pos": sl["position"], "fast_pos": fa["position"],
    "slow_first_stop": sl["first_stop_lap"],
    "both_cls": sl["is_classified"] & fa["is_classified"]}).reset_index()
fact("A3.n_pairs", len(pairs), "{:,}")
fact("A3.n_both_cls", int(pairs["both_cls"].sum()), "{:,}")
display(pairs.head())
''')

md("""
### 3a · What everyone sees: more stops, worse finishes
""")

code(r'''
cell("A3.2", "Number of stops vs finishing position")
st = race_level[race_level["raceId"].isin(PIT_RACE_IDS) & race_level["is_classified"]].copy()
fact("A3.zero_stop_n", int((st["n_stops"] == 0).sum()))
st = st[st["n_stops"] >= 1]
st["stops"] = st["n_stops"].clip(upper=4).astype(int).map({1: "1", 2: "2", 3: "3", 4: "4+"})
order = ["1", "2", "3", "4+"]
m = st.groupby("stops")["position"].agg(["mean", "size"]).loc[order]
for s, key in zip(order, ["1", "2", "3", "4"]):
    fact(f"A3.finish_{key}", m.loc[s, "mean"], "{:.1f}")
    fact(f"A3.nstops_{key}", int(m.loc[s, "size"]), "{:,}")

fig, ax = story_fig(f"What everyone sees: one-stop drivers average P{T('A3.finish_1')}, three-stop drivers P{T('A3.finish_3')}",
                    "Finishing position by number of pit stops (classified finishers, 2015–2024). Grey dots = single "
                    "results; black = average with 95% confidence range. The easy reading: extra stops are a gamble that fails.",
                    width=10, body=5.0)
a = ax["main"]
sns.stripplot(data=st, x="stops", y="position", order=order, color=DOT, alpha=0.22, jitter=0.3, size=2.6, ax=a, zorder=1)
sns.pointplot(data=st, x="stops", y="position", order=order, color=INK, errorbar=("ci", 95), seed=0,
              markersize=8, linewidth=2.2, ax=a, zorder=3)
for i, s in enumerate(order):
    a.text(i + 0.13, m.loc[s, "mean"], f"avg P{m.loc[s, 'mean']:.1f}", va="center", fontsize=10, color=INK,
           fontweight="bold", bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.9))
a.set_xticks(range(4)); a.set_xticklabels([f"{s} stop{'s' if s != '1' else ''}\n(n = {m.loc[s, 'size']:,})" for s in order])
a.set_ylim(st["position"].max() + 0.8, 0.2); a.set_yticks([1, 5, 10, 15, 20])
a.set_xlabel(""); a.set_ylabel("Finishing position")
a.grid(axis="x", visible=False)
save(fig, "A3_2_stops_vs_finish")
''')

md("""
One-stop drivers average P«A3.finish_1»; two-stop P«A3.finish_2»; three-stop P«A3.finish_3».
Four or more stops is slightly *better* (P«A3.finish_4»), probably because those are chaotic races (rain, red flags)
where everyone stops a lot.
(Zero-stop finishes are rare, «A3.zero_stop_n» cases, mostly rain or red-flag races, so they are left out.)
The usual story: *a driver who is far behind gambles on an extra stop, and the gamble fails.*
If that were true, the driver who qualified further behind the teammate should stop more often. `Cell A3.3` tests it.
""")

md("""
### 3b · Test the assumption: does falling behind make teams gamble?
**StopDiff** = stops made by the slower qualifier − stops made by the faster teammate.
A positive StopDiff means the slower qualifier made the extra stop.
""")

code(r'''
cell("A3.3", "Qualifying gap vs StopDiff")
r_gap, p_gap = stats.pearsonr(pairs["q_gap"], pairs["stop_diff"])
fact("A3.r_gap", r_gap, "{:+.2f}")
fact("A3.r_gap_p", p_gap, "{:.2f}")
fact("A3.share_extra", (pairs["stop_diff"] > 0).mean() * 100, "{:.0f}%")
pairs["gap_bin"] = pairs["q_gap"].clip(upper=10).astype(int).astype(str).replace({"10": "10+"})
gorder = [str(i) for i in range(1, 10)] + ["10+"]

fig, ax = story_fig(f"Myth busted: a big qualifying gap does not lead to extra stops (r = {T('A3.r_gap')})",
                    "Average StopDiff for each qualifying gap, with 95% confidence range. StopDiff = stops by the slower "
                    f"qualifier minus stops by the faster teammate. {T('A3.n_pairs')} teammate pairs, 2015–2024.",
                    width=10.5, body=4.8)
a = ax["main"]
a.axhline(0, color=INK2, lw=1, zorder=1)
a.annotate("", xy=(9.1, 0.62), xytext=(0, 0.06),
           arrowprops=dict(arrowstyle="-|>", color=LIGHT, lw=2.2, mutation_scale=16), zorder=1)
a.text(3.0, 0.52, "What the \"gamble\" theory predicts", fontsize=10, color=MUTED, ha="center")
sns.pointplot(data=pairs, x="gap_bin", y="stop_diff", order=gorder, color=RED, errorbar=("ci", 95), seed=0,
              markersize=8, linewidth=2, ax=a, zorder=3)
a.text(9.2, -0.42, "What the data shows:\nflat at zero", ha="right", fontsize=10, color=INK, fontweight="bold")
a.set_xlabel("Qualifying gap to teammate (grid places)"); a.set_ylabel("StopDiff (extra stops)")
a.set_ylim(-0.6, 0.8)
a.grid(axis="x", visible=False)
save(fig, "A3_3_gap_vs_stopdiff")
''')

md("""
**The assumption is dead.** The correlation between qualifying gap and StopDiff is r = «A3.r_gap» (p = «A3.r_gap_p»): no link at all.
Drivers who qualified ten places behind their teammate do not stop more often than drivers who were one place behind.
So if extra stops are not a planned gamble, what are they?
""")

md("""
### 3c · The reveal: the extra stop is an alarm
We now look only at pairs where **both** cars were classified («A3.n_both_cls» pairs),
and ask: how often does the slower qualifier finish *ahead* of the teammate?
""")

code(r'''
cell("A3.4", "Beat-your-teammate rate, with vs without an extra stop")
bc = pairs[pairs["both_cls"]].copy()
bc["extra"] = bc["stop_diff"] > 0
bc["beat"] = (bc["slow_pos"] < bc["fast_pos"]).astype(float) * 100
bc["gap"] = bc["slow_pos"] - bc["fast_pos"]                 # + = slower qualifier finished behind
bc["group"] = np.where(bc["extra"], "With an extra stop", "No extra stop")
bc["bucket"] = pd.cut(bc["q_gap"], [0, 3, 7, 99], labels=["Small gap\n1–3 places", "Medium gap\n4–7 places",
                                                          "Large gap\n8+ places"]).astype(str)

def two_prop(d):
    x1, n1 = d.loc[d["extra"], "beat"].sum() / 100, d["extra"].sum()
    x2, n2 = d.loc[~d["extra"], "beat"].sum() / 100, (~d["extra"]).sum()
    p = (x1 + x2) / (n1 + n2)
    z = (x1 / n1 - x2 / n2) / np.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    return pd.Series({"rate_extra": 100 * x1 / n1, "n_extra": n1, "rate_no": 100 * x2 / n2, "n_no": n2,
                      "z": z, "p": 2 * stats.norm.sf(abs(z))})

overall = two_prop(bc)
BUCKETS = ["Small gap\n1–3 places", "Medium gap\n4–7 places", "Large gap\n8+ places"]
by_b = bc.groupby("bucket").apply(two_prop, include_groups=False).loc[BUCKETS]
display(pd.concat([overall.rename("All pairs").to_frame().T, by_b]).round(3))
fact("A3.rate_extra", overall["rate_extra"], "{:.0f}%"); fact("A3.rate_extra_1", overall["rate_extra"], "{:.1f}%")
fact("A3.rate_no", overall["rate_no"], "{:.0f}%"); fact("A3.rate_no_1", overall["rate_no"], "{:.1f}%")
fact("A3.n_extra", int(overall["n_extra"]), "{:,}"); fact("A3.n_no", int(overall["n_no"]), "{:,}")
fact("A3.z", overall["z"], "{:.1f}")
fact("A3.med_gap_extra", bc.loc[bc["extra"], "gap"].median(), "{:+.0f}")
fact("A3.med_gap_no", bc.loc[~bc["extra"], "gap"].median(), "{:+.0f}")
for b, key in zip(by_b.index, ["small", "medium", "large"]):
    fact(f"A3.{key}_extra", by_b.loc[b, "rate_extra"], "{:.0f}%"); fact(f"A3.{key}_no", by_b.loc[b, "rate_no"], "{:.0f}%")
    fact(f"A3.{key}_n_extra", int(by_b.loc[b, "n_extra"])); fact(f"A3.{key}_p", by_b.loc[b, "p"], "{:.2g}")

plot = pd.concat([bc.assign(bucket="All pairs"), bc])
xorder = ["All pairs"] + list(by_b.index)
fig, ax = story_fig(f"With an extra stop, the slower teammate wins the duel {T('A3.rate_extra')} of the time, not {T('A3.rate_no')}",
                    f"How often the slower qualifier finishes ahead of the teammate. {T('A3.n_both_cls')} pairs where both cars "
                    "were classified, 2015–2024. Whiskers = 95% confidence range. The gap holds at every qualifying gap.",
                    width=10.5, body=5.0)
a = ax["main"]
sns.pointplot(data=plot, x="bucket", y="beat", hue="group", order=xorder,
              hue_order=["No extra stop", "With an extra stop"], palette=[INK, RED], markers=["s", "o"],
              linestyle="none", dodge=0.32, errorbar=("ci", 95), seed=0, markersize=8, ax=a)
for i, b in enumerate(xorder):
    row = overall if b == "All pairs" else by_b.loc[b]
    a.text(i - 0.2, row["rate_no"], f"{row['rate_no']:.0f}%  ", ha="right", va="center", fontsize=10, color=INK)
    a.text(i + 0.2, row["rate_extra"], f"  {row['rate_extra']:.0f}%", ha="left", va="center", fontsize=10,
           color=INK, fontweight="bold")
a.axvline(0.5, color=GRID, lw=1.5)
a.text(0.0, 52, f"z = {T('A3.z')}", ha="center", fontsize=9.5, color=INK2)
a.set_ylim(0, 56); a.set_xlabel(""); a.set_ylabel("Slower qualifier finishes ahead (%)")
a.legend(title="", loc="upper right", fontsize=10)
a.grid(axis="x", visible=False)
save(fig, "A3_4_teammate_duel")
''')

md("""
**The reveal.** With an extra stop, the slower qualifier finished ahead of the teammate only **«A3.rate_extra_1»** of the time
(n = «A3.n_extra»). Without one, **«A3.rate_no_1»** (n = «A3.n_no»). A two-proportion test gives z = «A3.z»,
far beyond what chance produces. It holds whether the qualifying gap was small («A3.small_extra» vs «A3.small_no»),
medium («A3.medium_extra» vs «A3.medium_no») or large («A3.large_extra» vs «A3.large_no»).

**Caveat on the large-gap bucket.** There the difference is small and only «A3.large_n_extra» pairs made an extra stop
(p = «A3.large_p»). The direction holds; the strength does not. A driver who qualified 8+ places behind rarely beats
the teammate anyway.
""")

code(r'''
cell("A3.5", "The distress signal: who made the extra stop, and when")
bc["who"] = np.select([bc["stop_diff"] > 0, bc["stop_diff"] < 0], ["Slower qualifier\nmade the extra stop",
                       "Teammate made\nthe extra stop"], default="Same number\nof stops")
worder = ["Teammate made\nthe extra stop", "Same number\nof stops", "Slower qualifier\nmade the extra stop"]
w = bc.groupby("who")["beat"].agg(["mean", "size"]).loc[worder]
fact("A3.beat_when_mate_extra", w.iloc[0]["mean"], "{:.0f}%"); fact("A3.n_mate_extra", int(w.iloc[0]["size"]))
fact("A3.beat_when_equal", w.iloc[1]["mean"], "{:.0f}%"); fact("A3.n_equal", int(w.iloc[1]["size"]))
early = bc.groupby("extra")["slow_first_stop"].apply(lambda s: (s <= 3).mean() * 100)
fact("A3.early_stop_extra", early[True], "{:.0f}%"); fact("A3.early_stop_no", early[False], "{:.0f}%")

fig, ax = story_fig("The distress signal: whoever makes the extra stop usually loses the teammate duel",
                    "Left: finishing gap to the teammate (above 0 = slower qualifier finished behind). Right: how often the "
                    f"slower qualifier finishes ahead, by who made the extra stop. {T('A3.n_both_cls')} pairs, both cars classified.",
                    width=11.5, body=4.8, mosaic=[["gap", "who"]], width_ratios=[1.15, 1])
a = ax["gap"]
sns.histplot(data=bc[bc["gap"].between(-12, 15)], x="gap", hue="group", hue_order=["No extra stop", "With an extra stop"],
             palette=[INK, RED], element="step", fill=False, stat="percent", common_norm=False, discrete=True,
             linewidth=2, ax=a, legend=False)
for grp, col, med_key, yy, word in [("No extra stop", INK, "A3.med_gap_no", 0.93, "black"),
                                     ("With an extra stop", RED, "A3.med_gap_extra", 0.84, "red")]:
    mv = bc.loc[bc["group"] == grp, "gap"].median()
    a.axvline(mv, color=col, lw=1.2, ymax=0.97)
    a.text(5.2, yy, f"{grp} ({word}): median {T(med_key)}", fontsize=9.5, color=INK, va="center",
           transform=a.get_xaxis_transform())
a.set_xlabel("Finishing gap to teammate (places)"); a.set_ylabel("Share of pairs (%)")
a.set_title("With an extra stop, the gap widens", loc="left")
a.grid(axis="x", visible=False)
b = ax["who"]
sns.barplot(x=w.index, y=w["mean"], hue=w.index, palette=[INK2, DOT, RED], legend=False, width=0.5, ax=b)
for i, v in enumerate(w["mean"]):
    b.text(i, v + 2, f"{v:.0f}%", ha="center", fontsize=11, color=INK, fontweight="bold")
b.set_xticks(range(3)); b.set_xticklabels([f"{k}\n(n = {n:,})" for k, n in zip(w.index, w["size"])], fontsize=9)
b.set_ylim(0, 75); b.set_xlabel(""); b.set_ylabel("Slower qualifier finishes ahead (%)")
b.set_title("The extra stop drags down whoever makes it", loc="left")
b.grid(axis="x", visible=False)
save(fig, "A3_5_distress_signal")
''')

md("""
**What this means.** The extra stop is not about *who qualified slower*. It drags down whoever makes it.
When the *teammate* made the extra stop, the slower qualifier finished ahead «A3.beat_when_mate_extra» of the time;
with equal stops, «A3.beat_when_equal»; when the slower qualifier made it, «A3.rate_extra». The median finishing gap
widens from «A3.med_gap_no» to «A3.med_gap_extra» places.
There is also a clue about *why*: «A3.early_stop_extra» of extra-stop drivers made their first stop in laps 1–3,
against «A3.early_stop_no» of the others. Stopping that early is rarely a plan. It usually means damage or a puncture.

**Honest framing.** The extra stop is a **symptom** of trouble (damage, a puncture, a spin, bad safety-car timing).
It is **not a weapon**, and it is **not the cause** of the lost result. Telling a driver "make fewer stops" would not
fix anything; the trouble came first. This is a correlation, measured on observational data, and we treat it as a
*warning light*, not as a lever.

> **The call you would make.** When your second car suddenly needs a stop the plan did not have, treat it as an alarm:
> something has gone wrong. Do not expect that stop to win places back. Protect the other car's result.
""")

# =============================================================== ACT 4
md("""
---
## Act 4 · The car sets the ceiling
Acts 1–3 were about decisions made on a race weekend. This act zooms out to ten seasons.
**The question.** How much of a result is decided by which team you drive for?
""")

code(r'''
cell("A4.1", "Constructor points share, the four top teams (Plotly)")
share = constructor_final.pivot_table(index="year", columns="constructorId", values="points_share") * 100
pts = constructor_final.pivot_table(index="year", columns="constructorId", values="points")
champ = constructor_final[constructor_final["position"] == 1].set_index("year")["constructorId"]
TEAMS = {131: "Mercedes", 9: "Red Bull", 1: "McLaren", 6: "Ferrari"}
yrs = share.index.tolist()
fact("A4.mer_2015", share.loc[2015, 131], "{:.1f}%"); fact("A4.mer_2023", share.loc[2023, 131], "{:.1f}%")
fact("A4.rbr_2015", share.loc[2015, 9], "{:.1f}%"); fact("A4.rbr_2023", share.loc[2023, 9], "{:.1f}%")
fact("A4.mcl_2015", share.loc[2015, 1], "{:.1f}%"); fact("A4.mcl_2024", share.loc[2024, 1], "{:.1f}%")
fact("A4.fer_2024", share.loc[2024, 6], "{:.1f}%"); fact("A4.rbr_2024", share.loc[2024, 9], "{:.1f}%")
fact("A4.mer_2016", share.loc[2016, 131], "{:.1f}%")
fact("A4.mer_titles", int((champ == 131).sum())); fact("A4.rbr_titles", int((champ == 9).sum()))
fact("A4.mer_last_title", int(champ[champ == 131].index.max()))
fact("A4.fer_best", share[6].max(), "{:.1f}%"); fact("A4.fer_best_year", int(share[6].idxmax()))
fact("A4.fer_worst", share[6].min(), "{:.1f}%"); fact("A4.fer_worst_year", int(share[6].idxmin()))
swing = (share[list(TEAMS)] - share[list(TEAMS)].shift(3)).stack().rename("pp").reset_index()
big = swing.loc[swing["pp"].abs().idxmax()]
fact("A4.swing_team", TEAMS[int(big["constructorId"])]); fact("A4.swing_pp", abs(big["pp"]), "{:.0f}")
fact("A4.swing_dir", "rose" if big["pp"] > 0 else "fell")
fact("A4.swing_from", int(big["year"]) - 3); fact("A4.swing_to", int(big["year"]))

fig = make_subplots(rows=1, cols=4, shared_yaxes=True, horizontal_spacing=0.045,
                    subplot_titles=["<b>Mercedes</b>", "<b>Red Bull</b>", "<b>McLaren</b>", "<b>Ferrari</b>"])
for i, (cid, name) in enumerate([(131, "Mercedes"), (9, "Red Bull"), (1, "McLaren"), (6, "Ferrari")], start=1):
    fig.add_trace(go.Scatter(x=yrs, y=share[cid], mode="lines", line=dict(color=INK, width=2.5),
                             fill="tozeroy", fillcolor="rgba(26,26,26,0.07)",
                             customdata=np.c_[pts[cid]], name=name,
                             hovertemplate=f"<b>{name}</b> %{{x}}<br>%{{y:.1f}}% of all points<br>%{{customdata[0]:.0f}} points<extra></extra>"),
                  row=1, col=i)
    cy = [y for y in yrs if champ.loc[y] == cid]
    if cy:
        fig.add_trace(go.Scatter(x=cy, y=share.loc[cy, cid], mode="markers", hoverinfo="skip",
                                 marker=dict(color=RED, size=11, line=dict(color="white", width=2))), row=1, col=i)
    # (year, x-anchor, x-shift, y-shift) for each direct label, placed off the line
    for y, xa, xs, ys in {131: [(2015, "left", 4, 14), (2023, "center", 0, -16)],
                          9: [(2015, "left", 8, 0), (2023, "center", 0, 15)],
                          1: [(2015, "left", -4, 22), (2024, "right", -6, 12)],
                          6: [(2018, "center", 0, 15), (2020, "center", 0, -15)]}[cid]:
        fig.add_annotation(x=y, y=share.loc[y, cid], text=f"{share.loc[y, cid]:.1f}%", showarrow=False,
                           xanchor=xa, xshift=xs, yshift=ys, font=dict(size=12, color=INK), row=1, col=i)
fig.update_yaxes(range=[0, 42], ticksuffix="%", gridcolor=GRID, showgrid=True, zeroline=False)
fig.update_yaxes(title_text="Share of all constructor points", row=1, col=1)
fig.update_xaxes(tickvals=[2015, 2018, 2021, 2024], showgrid=False, range=[2014.5, 2024.6])
plotly_story(fig, "Three eras in ten seasons: Mercedes, then Red Bull, then McLaren",
             "Each team's share of all constructor championship points. Red dot = constructors' champion that season. "
             "Hover for points.",
             height=470)
save_plotly(fig, "A4_1_points_share_eras")
''')

md("""
**What this means.** Mercedes took «A4.mer_2015» of all points in 2015 and won «A4.mer_titles» constructors' titles in a row
(to «A4.mer_last_title»), then fell to «A4.mer_2023» by 2023. Red Bull rose from «A4.rbr_2015» to «A4.rbr_2023».
McLaren climbed from «A4.mcl_2015» to «A4.mcl_2024» and won 2024, just ahead of Ferrari («A4.fer_2024»).
Ferrari peaked at «A4.fer_best» in «A4.fer_best_year», fell to «A4.fer_worst» in «A4.fer_worst_year», and never won a title in this period.
The biggest three-season swing: «A4.swing_team»'s share «A4.swing_dir» by «A4.swing_pp» percentage points between
«A4.swing_from» and «A4.swing_to». Changes that size are an engineering story, not a race-day decision.

**Why Plotly here.** Four small panels with one shared axis make the eras easy to compare;
hovering gives the exact share and points for any team-season without cluttering the chart.
""")

code(r'''
cell("A4.2", "Genuine DNF rate by season")
dnf_y = results.groupby("year")["is_dnf"].mean() * 100
dnf_team = (results.groupby(["constructorId", "constructor"])["is_dnf"].agg(["mean", "size"])
            .query("size >= 60").sort_values("mean").reset_index("constructorId"))
fact("A4.dnf_2015", dnf_y.loc[2015], "{:.1f}%"); fact("A4.dnf_2024", dnf_y.loc[2024], "{:.1f}%")
fact("A4.dnf_2017", dnf_y.loc[2017], "{:.1f}%"); fact("A4.dnf_2022", dnf_y.loc[2022], "{:.1f}%")
fact("A4.dnf_2015_r", dnf_y.loc[2015], "{:.0f}%"); fact("A4.dnf_2024_r", dnf_y.loc[2024], "{:.0f}%")
fact("A4.dnf_best_team", dnf_team.index[0]); fact("A4.dnf_best", dnf_team["mean"].iloc[0] * 100, "{:.1f}%")
fact("A4.dnf_worst_team", dnf_team.index[-1]); fact("A4.dnf_worst", dnf_team["mean"].iloc[-1] * 100, "{:.1f}%")
display(dnf_team.assign(mean=lambda d: d["mean"] * 100).round(1))

fig, ax = story_fig(f"Cars break down half as often: genuine DNFs fell from {T('A4.dnf_2015_r')} to {T('A4.dnf_2024_r')}",
                    "Share of race starts that ended in a genuine DNF (a lapped car is not a DNF), all teams, 2015–2024. "
                    f"Red line = {T('A4.dnf_best_team')}'s average over the ten seasons.", width=10, body=4.6)
a = ax["main"]
a.plot(dnf_y.index, dnf_y.values, color=INK, lw=2.2, marker="o", ms=7, markeredgecolor="white", markeredgewidth=1.5, zorder=3)
a.axhline(dnf_team["mean"].iloc[0] * 100, color=RED, lw=1.8, zorder=2)
a.text(2015, dnf_team["mean"].iloc[0] * 100 + 0.7, f"{T('A4.dnf_best_team')}, ten-season average: {T('A4.dnf_best')}",
       va="bottom", fontsize=9.5, color=INK)
for yv, ha, dy in [(2015, "center", 1.6), (2024, "center", 1.6), (2017, "center", 1.6), (2022, "center", 1.6)]:
    a.text(yv, dnf_y.loc[yv] + dy, f"{dnf_y.loc[yv]:.1f}%", ha=ha, fontsize=10, color=INK, fontweight="bold")
a.annotate("New car rules in 2017 and 2022:\nretirements rise, then fall", xy=(2022, dnf_y.loc[2022] + 0.6),
           xytext=(2019.5, 25.5), fontsize=9.5, color=INK, va="center", arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
a.annotate("", xy=(2017.2, dnf_y.loc[2017]), xytext=(2019.45, 25.3), arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
a.set_ylim(0, 28); a.set_xlim(2014.6, 2024.6)
a.set_xticks(range(2015, 2025)); a.set_ylabel("Genuine DNF rate (%)")
a.yaxis.set_major_formatter(mpl.ticker.PercentFormatter(decimals=0))
a.grid(axis="x", visible=False)
save(fig, "A4_2_dnf_rate")
''')

md("""
**What this means.** In 2015, «A4.dnf_2015» of starts ended in a genuine retirement; in 2024, «A4.dnf_2024».
The fall is not smooth: 2017 («A4.dnf_2017») and 2022 («A4.dnf_2022») were both years of new technical rules.
«A4.dnf_best_team» retired only «A4.dnf_best» of the time over ten seasons, the best of any team with 60+ starts
(«A4.dnf_worst_team» was worst at «A4.dnf_worst»). A car that finishes can score; reliability is part of the ceiling.

**Caveat.** "Genuine DNF" mixes mechanical failures with crashes. The link to rule changes is a plausible
explanation, not something this data can prove.
""")

code(r'''
cell("A4.3", "Race wins by driver, and how many came in the champion team's car")
champ_by_year = constructor_final.loc[constructor_final["position"] == 1, ["year", "constructorId"]].rename(
    columns={"constructorId": "champ_id"})
wn = results[results["position"] == 1].merge(champ_by_year, on="year")
wn["in_champ_car"] = wn["constructorId"] == wn["champ_id"]
fact("A4.wins_champ_car", wn["in_champ_car"].mean() * 100, "{:.0f}%")
pods = results[results["is_podium"]].groupby("driverId").size()
wd = (wn.groupby(["driverId", "driver"]).agg(wins=("raceId", "size"), champ_wins=("in_champ_car", "sum"))
      .reset_index("driver").assign(podiums=lambda d: pods.reindex(d.index))
      .sort_values("wins", ascending=False).head(10).set_index("driver"))
display(wd)
fact("A4.n_winners", wn["driverId"].nunique())
fact("A4.top2_wins", wd["wins"].iloc[:2].sum() / len(wn) * 100, "{:.0f}%")
fact("A4.ham_wins", int(wd.loc["Lewis Hamilton", "wins"])); fact("A4.ham_champ_wins", int(wd.loc["Lewis Hamilton", "champ_wins"]))
fact("A4.ver_wins", int(wd.loc["Max Verstappen", "wins"])); fact("A4.ver_champ_wins", int(wd.loc["Max Verstappen", "champ_wins"]))

fig, ax = story_fig(f"{T('A4.wins_champ_car')} of all race wins went to the season's champion team",
                    "Race wins 2015–2024, the ten drivers with the most wins. Red = wins while driving for that season's "
                    "constructors' champion; grey = other wins. Outline = podium finishes (top three).", width=10.5, body=5.0)
a = ax["main"]
y = np.arange(len(wd))[::-1]
a.barh(y, wd["podiums"], height=0.62, color="white", edgecolor=LIGHT, linewidth=1.2, zorder=1)
a.barh(y, wd["champ_wins"], height=0.42, color=RED, zorder=2)
a.barh(y, wd["wins"] - wd["champ_wins"], left=wd["champ_wins"], height=0.42, color=DOT, zorder=2)
for yi, (name, r) in zip(y, wd.iterrows()):
    a.text(r["podiums"] + 1.5, yi, f"{r['wins']} wins ({r['champ_wins']} in champion car) · {r['podiums']} podiums",
           va="center", fontsize=9.5, color=INK)
a.set_yticks(y); a.set_yticklabels(wd.index)
a.set_xlim(0, wd["podiums"].max() * 1.75); a.set_xlabel("Number of races")
a.grid(axis="y", visible=False)
save(fig, "A4_3_wins_by_driver")
''')

md("""
**What this means.** «A4.wins_champ_car» of all wins went to whichever team won the constructors' title that year.
Hamilton won «A4.ham_wins» races, «A4.ham_champ_wins» of them in the champion car.
Verstappen won «A4.ver_wins», «A4.ver_champ_wins» in the champion car. His 2021 and 2024 wins came in a Red Bull that did *not* win the
constructors' title, which is what a truly great driver looks like in this chart: wins outside the best car.
""")

code(r'''
cell("A4.4", "Driver championship points by season (Plotly)")
top8 = driver_final.groupby("driverId")["points"].sum().nlargest(8).index
dp = driver_final[driver_final["driverId"].isin(top8)]
title_seasons = driver_final[driver_final["position"] == 1]
fact("A4.n_champions", title_seasons["driverId"].nunique())
fact("A4.n_titles", len(title_seasons))
fact("A4.ham_titles", int((title_seasons["driver"] == "Lewis Hamilton").sum()))
fact("A4.ver_titles", int((title_seasons["driver"] == "Max Verstappen").sum()))
fact("A4.ver_2023_pts", driver_final.query("year == 2023 and driver == 'Max Verstappen'")["points"].iloc[0], "{:.0f}")
fig = go.Figure()
for did, g in dp.groupby("driverId"):
    name = g["driver"].iloc[0]
    col, w = (RED, 3) if name == "Max Verstappen" else (INK, 3) if name == "Lewis Hamilton" else (LIGHT, 1.8)
    fig.add_trace(go.Scatter(x=g["year"], y=g["points"], mode="lines+markers", name=name,
                             line=dict(color=col, width=w), marker=dict(size=6, color=col),
                             hovertemplate=f"<b>{name}</b> %{{x}}<br>%{{y:.0f}} points<extra></extra>"))
    t = g[g["position"] == 1]
    if len(t):
        fig.add_trace(go.Scatter(x=t["year"], y=t["points"], mode="markers", hoverinfo="skip", showlegend=False,
                                 marker=dict(symbol="star", size=15, color=col if col != LIGHT else INK2,
                                             line=dict(color="white", width=1.5))))
    last_row = g.sort_values("year").iloc[-1]
    if name in ("Lewis Hamilton", "Max Verstappen"):
        fig.add_annotation(x=last_row["year"], y=last_row["points"], text=f"<b>{name.split()[-1]}</b>", showarrow=False,
                           xanchor="left", xshift=10, font=dict(size=13, color=INK))
fig.update_yaxes(title_text="Championship points", gridcolor=GRID, showgrid=True, rangemode="tozero")
fig.update_xaxes(tickvals=list(range(2015, 2025)), showgrid=False, range=[2014.6, 2025.4])
plotly_story(fig, f"{T('A4.n_titles')} titles, {T('A4.n_champions')} champions: Hamilton's run ended where Verstappen's began",
             "Season points for the eight top scorers of 2015–2024. Stars = world title. Black = Hamilton, red = Verstappen, "
             "grey = others (hover for names).", height=470)
fig.update_layout(showlegend=False)
save_plotly(fig, "A4_4_driver_points")
''')

md("""
Hamilton won «A4.ham_titles» titles and Verstappen «A4.ver_titles» (Rosberg took 2016).
The hand-over in 2021 matches the switch between the Mercedes and Red Bull eras in `Cell A4.1`: the driver title follows the car era.
""")

code(r'''
cell("A4.5", "Driver x circuit heatmap: average finishing position")
top10 = results.groupby("driver")["points"].sum().nlargest(10).index
cn = results.groupby("circuit_short")["raceId"].nunique()
regular = cn[cn >= 8].index
hm = (results[results["driver"].isin(top10) & results["circuit_short"].isin(regular) & results["is_classified"]]
      .groupby(["driver", "circuit_short"])["position"].agg(["mean", "size"]))
mean = hm["mean"].unstack().where(hm["size"].unstack() >= 3)
mean = mean.loc[mean.mean(axis=1).sort_values().index, mean.mean(axis=0).sort_values().index]
rows, cols = mean.mean(axis=1), mean.mean(axis=0)
fact("A4.hm_n_circuits", len(regular)); fact("A4.hm_row_range", rows.max() - rows.min(), "{:.1f}")
fact("A4.hm_col_range", cols.max() - cols.min(), "{:.1f}")
fact("A4.hm_best_driver", rows.index[0]); fact("A4.hm_best_avg", rows.iloc[0], "{:.1f}")
fact("A4.hm_second_driver", rows.index[1]); fact("A4.hm_second_avg", rows.iloc[1], "{:.1f}")
fact("A4.hm_top2_titles", int(driver_final[driver_final["position"] == 1]["driver"].isin(rows.index[:2]).sum()))

fig, ax = story_fig(f"The driver row matters more than the circuit column ({T('A4.hm_row_range')} vs {T('A4.hm_col_range')} places)",
                    f"Average finishing position (classified finishes only) for the ten top point-scorers at the "
                    f"{T('A4.hm_n_circuits')} circuits raced 8+ times in 2015–2024. Darker = better. Blank = fewer than 3 finishes. "
                    f"Rows sorted best to worst; red box = the two drivers who won {T('A4.hm_top2_titles')} of the 10 titles.", width=12, body=5.6)
a = ax["main"]
sns.heatmap(mean, annot=True, fmt=".1f", cmap="Greys_r", vmin=1, vmax=12, linewidths=2, linecolor="white",
            annot_kws={"fontsize": 8.5}, cbar_kws={"label": "Average finishing position", "shrink": 0.7, "pad": 0.01}, ax=a)
a.add_patch(mpl.patches.Rectangle((0, 0), mean.shape[1], 2, fill=False, edgecolor=RED, lw=2.5, clip_on=False))
a.set_xlabel(""); a.set_ylabel("")
a.tick_params(axis="x", rotation=40, labelsize=9); a.tick_params(axis="y", labelsize=9.5)
for lab in a.get_xticklabels(): lab.set_ha("right")
save(fig, "A4_5_driver_circuit_heatmap")
''')

md("""
**What this means.** Read across a row and the shade barely changes: «A4.hm_best_driver» averages P«A4.hm_best_avg» and
«A4.hm_second_driver» P«A4.hm_second_avg», almost everywhere. Read down a column and it changes a lot.
Row averages span «A4.hm_row_range» places; circuit averages only «A4.hm_col_range».
"Circuit specialists" are mostly a myth at this level: driver *and car* set the level, the circuit nudges it.

**Caveat.** Averages over 3–10 finishes per cell are noisy, and a driver's row mixes several cars over the years.
""")

code(r"""
cell("A4.6", "Honest anti-climax: lap-time consistency vs season points")
lt_y = lap_times.merge(races[["raceId", "year"]], on="raceId")

def cv_iqr(x):
    q1, q3 = x.quantile([0.25, 0.75])
    k = x[(x >= q1 - 1.5 * (q3 - q1)) & (x <= q3 + 1.5 * (q3 - q1))]     # drop pit, safety-car, crash laps
    return k.std() / k.mean()                                             # coefficient of variation (CV)

g = lt_y.groupby(["year", "raceId", "driverId"])["lap_ms"]
cv = pd.DataFrame({"cv": g.apply(cv_iqr), "laps": g.size()}).reset_index()

def season_link(c, how="mean"):
    s = (c.groupby(["year", "driverId"]).agg(cv=("cv", how), n=("raceId", "nunique")).reset_index()
         .query("n >= 10").merge(driver_final, on=["year", "driverId"]))
    return s, s["cv"].corr(s["points"])

# Main method: only driver-races with 10+ laps (with 2-3 laps the outlier filter cannot work),
# CV averaged over the season, driver-seasons with 10+ races.
cons, r_c = season_link(cv[cv["laps"] >= 10])
cons["cv_pct"] = cons["cv"] * 100
fact("A4.cons_n", len(cons)); fact("A4.cons_r", r_c, "{:+.2f}"); fact("A4.cons_r2", r_c ** 2 * 100, "{:.0f}%")
fact("A4.cons_rho", stats.spearmanr(cons["cv"], cons["points"])[0], "{:+.2f}")
# Sensitivity: three other reasonable choices
_, r_all = season_link(cv)                                              # keep very short races
_, r_med = season_link(cv[cv["laps"] >= 10], "median")                  # median race, not mean
mask = lt_y.groupby("raceId")["lap_ms"].transform(                      # filter outlier laps per race
    lambda x: x.between(x.quantile(.25) - 1.5 * (x.quantile(.75) - x.quantile(.25)),
                        x.quantile(.75) + 1.5 * (x.quantile(.75) - x.quantile(.25))))
g2 = lt_y[mask].groupby(["year", "raceId", "driverId"])["lap_ms"]
cv2 = pd.DataFrame({"cv": g2.agg(lambda x: x.std() / x.mean()), "laps": g2.size()}).reset_index()
_, r_race = season_link(cv2[cv2["laps"] >= 10])
fact("A4.cons_r_all", r_all, "{:+.2f}"); fact("A4.cons_r_med", r_med, "{:+.2f}"); fact("A4.cons_r_race", r_race, "{:+.2f}")
fact("A4.cons_r_med_abs", abs(r_med), "{:.2f}")
display(pd.DataFrame({"method": ["Main: races with 10+ laps, mean CV", "Keep races with <10 laps",
                                 "Median race instead of mean", "Outlier laps filtered per race"],
                      "r": [r_c, r_all, r_med, r_race]}).round(3))

fig, ax = story_fig(f"Honest anti-climax: lap-time consistency is only weakly linked to points (r = {T('A4.cons_r')})",
                    f"Each dot is one driver-season with 10+ races ({T('A4.cons_n')} in total). Left = steadier lap times "
                    "(lower coefficient of variation). Line = straight-line fit with 95% confidence band.", width=10, body=4.8)
a = ax["main"]
sns.regplot(data=cons, x="cv_pct", y="points", ax=a, ci=95, seed=0,
            scatter_kws=dict(s=26, color=DOT, edgecolor="white", linewidths=0.8, alpha=0.9),
            line_kws=dict(color=INK, lw=2))
a.text(0.98, 0.95, f"r = {T('A4.cons_r')}: consistency explains about {T('A4.cons_r2')} of the spread in points",
       transform=a.transAxes, ha="right", va="top", fontsize=10, color=INK, fontweight="bold")
a.text(0.98, 0.87, f"Fragile: other reasonable methods give r from {T('A4.cons_r_race')} to {T('A4.cons_r_med')}",
       transform=a.transAxes, ha="right", va="top", fontsize=9.5, color=INK2)
a.set_ylim(-20, cons["points"].max() * 1.12)
a.set_xlabel("Lap-time variation within a race (%, lower = steadier)"); a.set_ylabel("Season points")
save(fig, "A4_6_consistency_vs_points")
""")

md("""
**An honest anti-climax.** Steadier drivers score slightly more (r = «A4.cons_r», «A4.cons_n» driver-seasons), but consistency
explains only about «A4.cons_r2» of the spread in points. The result is also **fragile**. Keeping races where a driver did fewer
than 10 laps gives «A4.cons_r_all»; using each driver's median race instead of the mean gives «A4.cons_r_med»; filtering outlier
laps per race instead of per driver gives «A4.cons_r_race». And even the strongest version is partly a car effect: a fast car
runs in clean air, which steadies its lap times. We report it because a story that only shows its strong results is not honest.
(The earlier analysis reported r ≈ −0.18 without saying how short races were handled; the 10-lap rule reproduces it.
See `verification_log.md`.)

> **The call you would make.** Every edge from Acts 1–3 (a better grid slot, a well-timed stop, reading the alarm) lives
> inside the ceiling the car sets. Fight for every place, but plan the season around the car, not the race.
""")

# =============================================================== ACT 5
md("""
---
## Act 5 · What the data cannot tell you
### 5a · How a chart can lie: a demonstration
This is the intentionally misleading chart planned for the ethics part of the project:
**constructor championship points with a truncated y-axis**. The data is real and correct. Only the axis is changed.
""")

code(r'''
cell("A5.1", "MISLEADING chart (for ethics demonstration)")
c24 = constructor_final[constructor_final["year"] == 2024].sort_values("position").head(2)
(lead, lead_pts), (second, second_pts) = c24[["constructor", "points"]].itertuples(index=False)
gap = lead_pts - second_pts
fact("A5.lead", lead); fact("A5.second", second)
fact("A5.lead_pts", lead_pts, "{:.0f}"); fact("A5.second_pts", second_pts, "{:.0f}")
fact("A5.gap", gap, "{:.0f}"); fact("A5.gap_pct", gap / second_pts * 100, "{:.1f}%")
title_gaps = constructor_final.sort_values("position").groupby("year")["points"].apply(lambda s: s.iloc[0] - s.iloc[1])
rank = int(title_gaps.rank(method="min").loc[2024])
fact("A5.closest", "the closest" if rank == 1 else f"the {rank}th closest")
BASE = 645                                                        # the manipulated axis start
vis_lead, vis_second = lead_pts - BASE, second_pts - BASE
fact("A5.base", BASE); fact("A5.visual_ratio", vis_lead / vis_second, "{:.1f}")
fact("A5.visual_diff", (vis_lead - vis_second) / vis_second * 100, "{:.0f}%")
fact("A5.lie_factor", ((vis_lead - vis_second) / vis_second) / (gap / second_pts), "{:.0f}")

def bars(a, ylim):
    a.bar([lead, second], [lead_pts, second_pts], width=0.5, color=[RED, DOT])
    for i, v in enumerate([lead_pts, second_pts]):
        a.text(i, v + (ylim[1] - ylim[0]) * 0.015, f"{v:.0f}", ha="center", fontsize=12, fontweight="bold", color=INK)
    a.set_ylim(*ylim); a.set_ylabel("Constructor championship points, 2024")
    a.grid(axis="x", visible=False)

fig, ax = story_fig(f"{lead} crushed {second} in 2024",
                    "MISLEADING (for ethics demonstration). Same real data as the next chart. "
                    f"Only the y-axis changed: it starts at {BASE}, not 0.", width=7, body=4.6)
bars(ax["main"], (BASE, 670))
ax["main"].text(0.5, 0.55, "MISLEADING\nfor ethics demonstration", transform=ax["main"].transAxes, ha="center",
                va="center", fontsize=20, fontweight="bold", color=RED, alpha=0.85, rotation=18,
                bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=RED, lw=2.5, alpha=0.85))
save(fig, "A5_1_misleading_truncated_axis")
''')

code(r'''
cell("A5.2", "HONEST version of the same chart")
fig, ax = story_fig(f"{lead} beat {second} in 2024 by just {T('A5.gap')} points ({T('A5.gap_pct')})",
                    "Honest version. Same data, y-axis starts at 0, so bar height is proportional to points.",
                    width=7, body=4.6)
bars(ax["main"], (0, 760))
ax["main"].annotate(f"{T('A5.gap')}-point gap", xy=(0.5, lead_pts), xytext=(0.5, 715), ha="center", fontsize=10,
                    color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
save(fig, "A5_2_honest_full_axis")
''')

code(r'''
cell("A5.3", "Side by side: misleading vs honest")
fig, ax = story_fig("Same numbers, two stories: the axis decides which one you see",
                    f"Left: y-axis starts at {BASE} (MISLEADING, for ethics demonstration). Right: y-axis starts at 0 (honest). "
                    f"2024 constructor championship points.", width=11, body=4.8, mosaic=[["bad", "good"]])
bars(ax["bad"], (BASE, 670)); bars(ax["good"], (0, 760))
ax["bad"].set_title(f"MISLEADING: {lead}'s bar looks {T('A5.visual_ratio')}× taller", color=RED)
ax["good"].set_title(f"Honest: a {T('A5.gap_pct')} difference looks like one", color=INK)
ax["bad"].text(0.5, 0.62, "MISLEADING", transform=ax["bad"].transAxes, ha="center", va="center", fontsize=26,
               fontweight="bold", color=RED, alpha=0.9, rotation=18, zorder=10,
               bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=RED, lw=2, alpha=0.85))
ax["good"].set_ylabel("")
save(fig, "A5_3_misleading_vs_honest")
''')

md("""
**What was manipulated.** Only the y-axis. It starts at «A5.base» points instead of 0. The data is real:
«A5.lead» «A5.lead_pts», «A5.second» «A5.second_pts».

**Why it misleads.** A bar chart encodes value as *bar length*. When the axis is cut at «A5.base»,
we only see the top «A5.lead_pts»−«A5.base» and «A5.second_pts»−«A5.base» points of each bar. «A5.lead»'s bar becomes
«A5.visual_ratio» times taller than «A5.second»'s, while the real difference is «A5.gap_pct».

**The false impression.** "«A5.lead» crushed «A5.second»." In reality the 2024 constructors' title was «A5.closest» of the
ten seasons: «A5.gap» points over a «A5.lead_pts»-point season.

**How it was fixed.** The y-axis starts at zero, the exact values are printed on the bars, and the title states the real size
of the gap («A5.gap» points, «A5.gap_pct»).

**The principle.** *Truthful scaling* and *proportional ink* (Edward Tufte): the size of a mark must be proportional to the
number it shows. Tufte's **lie factor** = (size of the effect in the graphic) ÷ (size of the effect in the data).
An honest chart has a lie factor near 1. Here the bar difference is «A5.visual_diff» and the data difference is «A5.gap_pct»,
a lie factor of about **«A5.lie_factor»**.

**Ethical reflection.** This chart contains no false number, which is what makes it dangerous: it would pass a fact-check of
its labels. Truncated axes are tempting in F1 because so many fights are close, like the 2024 constructors' title.
The same care applies to the rest of this project. Every bar chart here starts at zero. Dot and line charts that do not
start at zero (Acts 1 and 2) encode *position*, not length, and say so. Small samples are flagged (Hockenheim, the large-gap bucket),
and the one weak finding (consistency) is shown, not hidden.
""")

md("""
### 5b · The limits of this analysis
| Finding | Type of evidence | What could be behind it | What we can honestly say |
|---|---|---|---|
| Grid predicts finish (Act 1) | Correlation | Fast cars qualify well *and* race well | Starting position and finishing position move together; more at some tracks |
| Undercut pattern (Act 2) | Before/after average | Safety cars, tyre choices, forced stops | Early first stops lose more places at once and recover more |
| Extra stop = alarm (Act 3) | Correlation, strong (z = «A3.z») | Damage, punctures, spins, bad timing | An extra stop is a *warning sign*, not a cause and not a tactic |
| Car sets the ceiling (Act 4) | Descriptive | Budget, rules, engine supply | Points share swings by team era far more than by any race decision |
| Consistency (Act 4) | Weak, fragile correlation | Car pace | Little to no link with points |

**Correlation is not causation.** None of these results comes from an experiment. Each one shows that two things move
together in ten seasons of records. The dataset also has no tyre compounds, no weather, no safety-car periods and no team
radio, so the *why* behind an event (like Hamilton's lap-1 stop in the hook race) is always outside the data.
""")

# =============================================================== CLOSING
md("""
---
## Closing · Back to the hook race
""")

code(r'''
cell("C.1", "The hook race through all four acts")
sh = gf[gf["circuitId"] == races.loc[races["raceId"] == HOOK, "circuitId"].iloc[0]]
fact("C.circuit", sh["circuit_short"].iloc[0])
fact("C.circuit_r", sh["grid"].corr(sh["position"]), "{:.2f}")
fact("C.circuit_races", sh["raceId"].nunique())
fact("C.extra_stops", FACTS["H.ham_stops"]["value"] - FACTS["H.ros_stops"]["value"])
''')

md("""
Go back to the «H.race» and read it again, this time as a strategist.

- **Act 1.** Rosberg started on pole and won. At «C.circuit» the grid-finish correlation is «C.circuit_r» over «C.circuit_races» races:
  Saturday mattered.
- **Act 2.** On lap «H.sc_lap», «H.n_sc_stops» cars pitted at once as the race slowed. Those lines crossing in the grey band
  are pit stops trading places now for places later.
- **Act 3.** Hamilton, the slower qualifier in the same car, made «C.extra_stops» more stops than his teammate and finished
  «H.ham_finish»th. The extra stops were the alarm, not the plan: his first came on lap «H.ham_first_stop».
- **Act 4.** Both drove the 2016 Mercedes, the car that took «A4.mer_2016» of all points that season.
  That is how a car from «H.ham_grid»nd on the grid still reached the points.

**The «H.changes» position changes were never random. They were a chain of cause and effect, and now you can read it.**
""")

# =============================================================== DASHBOARD
md("""
---
## Dashboard · The five acts in one interactive page
`Cell D.1` exports the tables the dashboard needs and writes **`F1_Dashboard.html`**: one self-contained file
(Plotly.js is embedded, so it works offline). Filters for season, constructor, driver and circuit sit in one row at the top
and every chart re-draws for the same slice of data. The page is laid out as the five acts.
""")

code(r'''
cell("D.1", "Build F1_Dashboard.html")
import plotly.offline
def cols(df):                                               # compact column-wise JSON
    return {c: [None if (isinstance(v, float) and np.isnan(v)) else v for v in df[c].tolist()] for c in df.columns}

lap_trace = {}                                             # {raceId: {driverId: [pos on lap 1, 2, ...]}}
for (rid, did), g in lap_times.groupby(["raceId", "driverId"]):
    p = g.set_index("lap")["position"].reindex(range(1, int(g["lap"].max()) + 1))
    lap_trace.setdefault(str(rid), {})[str(did)] = [None if pd.isna(v) else int(v) for v in p]
dash = {
    "races": cols(races[["raceId", "year", "round", "race_label", "circuitId", "circuit_short"]]),
    "drivers": cols(results.drop_duplicates("driverId")[["driverId", "code", "driver"]].sort_values("driver")),
    "constructors": cols(results.drop_duplicates("constructorId")[["constructorId", "constructor"]].sort_values("constructor")),
    "results": cols(race_level[["raceId", "year", "circuitId", "driverId", "constructorId", "grid", "position",
                                "positionOrder", "points", "is_dnf", "n_stops"]].assign(
                                    is_dnf=lambda d: d["is_dnf"].astype(int))),
    "laps": lap_trace,
    "stops": cols(pit_stops[["raceId", "driverId", "lap"]]),
    "undercut": cols(und[["raceId", "year", "circuitId", "driverId", "constructorId", "timing", "chg2", "chg10"]]
                     .assign(timing=lambda d: d["timing"].astype(str))),
    "pairs": cols(bc[["raceId", "year", "circuitId", "constructorId", "slow_id", "fast_id", "q_gap", "stop_diff", "beat"]]
                  .assign(beat=lambda d: (d["beat"] > 0).astype(int))),
    "cfinal": cols(constructor_final[["year", "constructorId", "constructor", "points", "points_share", "position"]]),
    "dfinal": cols(driver_final[["year", "driverId", "driver", "points", "position"]]),
    "circuit_r": cols(byc[["circuitId", "circuit_short", "r", "n", "races", "lo", "hi"]]),
    "facts": {k: v["text"] for k, v in FACTS.items()},
    "hook_race": int(HOOK),
}
template = Path("assets/dashboard_template.html").read_text()
html = (template.replace("/*__PLOTLYJS__*/", plotly.offline.get_plotlyjs())
                .replace("/*__DATA__*/null", json.dumps(dash, separators=(",", ":"), default=float).replace("</", "<\\/")))
Path("F1_Dashboard.html").write_text(html, encoding="utf-8")
fact("D.size_mb", Path("F1_Dashboard.html").stat().st_size / 1e6, "{:.1f}")
''')

md("""
`Cell D.2` repeats one dashboard filter in Python, so the numbers quoted from the dashboard are also produced by the notebook.
""")

code(r'''
cell("D.2", "Dashboard filter example: all races vs Circuit = Monaco")
MON = races.loc[races["circuitRef"] == "monaco", "circuitId"].iloc[0]

def dash_kpis(cid=None):
    r = results if cid is None else results[results["circuitId"] == cid]
    g = r.dropna(subset=["grid", "position"])
    e = und[und["timing"] == "Early"] if cid is None else und[(und["timing"] == "Early") & (und["circuitId"] == cid)]
    b = bc if cid is None else bc[bc["circuitId"] == cid]
    return {"races": r["raceId"].nunique(), "r": g["grid"].corr(g["position"]), "und10": e["chg10"].mean(),
            "und_n": len(e), "extra": b.loc[b["extra"], "beat"].mean(), "no": b.loc[~b["extra"], "beat"].mean(),
            "pairs": len(b), "dnf": r["is_dnf"].mean() * 100}

allk, monk = dash_kpis(), dash_kpis(MON)
display(pd.DataFrame({"All races": allk, "Circuit = Monaco": monk}).round(2))
fact("D.all_dnf", allk["dnf"], "{:.1f}%"); fact("D.all_pairs", allk["pairs"], "{:,}")
fact("D.mon_races", monk["races"]); fact("D.mon_r", monk["r"], "{:.2f}")
fact("D.mon_und10", monk["und10"], "{:+.1f}"); fact("D.mon_und_n", monk["und_n"])
fact("D.mon_extra", monk["extra"], "{:.0f}%"); fact("D.mon_no", monk["no"], "{:.0f}%")
fact("D.mon_pairs", monk["pairs"]); fact("D.mon_dnf", monk["dnf"], "{:.1f}%")
fact("D.mon_n_extra", int(bc.loc[(bc["circuitId"] == MON) & bc["extra"]].shape[0]))
mon_last = races[races["circuitId"] == MON].sort_values("date").iloc[-1]
fact("D.mon_last_race", mon_last["race_label"])
fact("D.mon_last_changes", int(churn.loc[mon_last["raceId"], "position_changes"]), "{:,}")
''')

# =============================================================== FACTS
md("""
## Facts register
`Cell F.1` saves every number used in the text to `facts.json`, with the cell that produced it.
The report, the slides and the viva sheet read their numbers from this file, so they always match this notebook.
""")

code(r'''
cell("F.1", "Save facts.json and list the charts")
fact("F.n_charts", len(CHART_FILES))
fact("F.n_plotly", sum(Path(v).with_suffix(".html").exists() for v in CHART_FILES.values()))
fact("F.n_static", FACTS["F.n_charts"]["value"] - FACTS["F.n_plotly"]["value"])
Path("facts.json").write_text(json.dumps(FACTS, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
Path("charts/index.json").write_text(json.dumps(CHART_FILES, indent=1))
print(len(FACTS), "facts saved;", len(CHART_FILES), "charts:")
for k, v in CHART_FILES.items():
    print(f"  Cell {k:5s} -> {v}")
''')

# =============================================================== WRITE
nb = nbf.v4.new_notebook()
nb["cells"] = cells
nb["metadata"] = {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                  "language_info": {"name": "python"}}
nbf.write(nb, HERE / "F1_Story_Notebook.ipynb")
if missing:
    print("MISSING FACT KEYS:", sorted(missing))
    sys.exit(1)
print(f"wrote F1_Story_Notebook.ipynb ({len(cells)} cells, facts {'filled' if facts else 'NOT filled'})")
