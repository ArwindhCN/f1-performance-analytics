"""
Builds the Tableau version of the F1 project: tableau/F1_Dashboard.twbx
  - 14 data files (CSV + Tableau .hyper extracts), same calculations as the notebook
  - 15 worksheets, 4 dashboards (F1 in 60 seconds, F1 Dashboard, Deep dive, Ethics)
  - a 14-point Story "How F1 works" that explains each F1 idea before its finding
  - dashboard actions: click a circuit or a season to filter, hover a team to highlight its cars
Numbers in titles and captions come from facts.json (written by the notebook); the builder checks its own
data against them. Run after make_notebook.sh:  python build_tableau.py
"""
import json
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

import numpy as np
import pandas as pd
from tableauhyperapi import (Connection, CreateMode, HyperProcess, Inserter, NULLABLE, SqlType, TableDefinition,
                             TableName, Telemetry)

HERE = Path(__file__).resolve().parent
C = HERE / "data" / "clean"
OUT = HERE / "tableau"
OUT.mkdir(exist_ok=True)
FACTS = json.loads((HERE / "facts.json").read_text())


def F(k):
    return FACTS[k]["text"]


res = pd.read_csv(C / "results.csv")
rl = pd.read_csv(C / "race_level.csv")
lt = pd.read_csv(C / "lap_times.csv")
ps = pd.read_csv(C / "pit_stops.csv")
races = pd.read_csv(C / "races.csv")
cfin = pd.read_csv(C / "constructor_final.csv")
lab = races.set_index("raceId")[["race_label", "year", "circuit_short"]]
DATA = {}                                         # data-source name -> (csv file name, DataFrame)

# ================================================================== data files
# 1. race trace: every car's position on every lap (lap 0 = grid)
who = res.set_index(["raceId", "driverId"])[["code", "driver", "constructor"]]
tr = lt.merge(lab, left_on="raceId", right_index=True).join(who, on=["raceId", "driverId"])
grid0 = (res[["raceId", "driverId", "grid"]].dropna().rename(columns={"grid": "position"}).assign(lap=0)
         .merge(lab, left_on="raceId", right_index=True).join(who, on=["raceId", "driverId"]))
tr = pd.concat([grid0, tr]).rename(columns={"race_label": "race", "circuit_short": "circuit", "constructor": "team"})
DATA["trace"] = ("race_trace.csv", tr[["race", "year", "circuit", "driver", "code", "team", "lap", "position"]]
                 .sort_values(["race", "driver", "lap"]))

# 2. results: one row per driver per race
r = res[["year", "race_label", "circuit_short", "driver", "constructor", "grid", "position", "points", "is_dnf"]].rename(
    columns={"race_label": "race", "circuit_short": "circuit", "constructor": "team"})
r["dnf"] = r.pop("is_dnf").astype(int)
r["dnf_pct"] = r["dnf"] * 100
DATA["results"] = ("results.csv", r)

# 3. constructor points share
cs = cfin.rename(columns={"constructor": "team", "points_share": "share"})[["year", "team", "points", "share", "position"]].copy()
cs["share"] *= 100
DATA["share"] = ("constructor_share.csv", cs)

# 4. grid-finish correlation per circuit (40+ classified finishes), with 95% range
gf = res.dropna(subset=["grid", "position"])
rows = []
for c, d in gf.groupby("circuit_short"):
    if len(d) >= 40:
        rr = d["grid"].corr(d["position"])
        z, se = np.arctanh(rr), 1 / np.sqrt(len(d) - 3)
        rows.append({"circuit": c, "r": rr, "low": np.tanh(z - 1.96 * se), "high": np.tanh(z + 1.96 * se),
                     "finishes": len(d), "races": d["raceId"].nunique()})
circ = pd.DataFrame(rows).sort_values("r", ascending=False)
DATA["circuit"] = ("circuit_r.csv", circ)

# 5. undercut: position change around each first pit stop (long format for a slope chart)
first = ps[ps["stop"] == 1][["raceId", "driverId", "lap"]].rename(columns={"lap": "L"})
pos = lt.set_index(["raceId", "driverId", "lap"])["position"]
for k, off in {"b": -1, "p2": 2, "p10": 10}.items():
    first[k] = pos.reindex(pd.MultiIndex.from_arrays([first["raceId"], first["driverId"], first["L"] + off])).to_numpy()
u = first.dropna().copy()
u["pct"] = u.groupby("raceId")["L"].rank(method="average", pct=True)
u["timing"] = pd.cut(u["pct"], [0, 1 / 3, 2 / 3, 1], labels=["Early", "Middle", "Late"], include_lowest=True).astype(str)
u = u.merge(lab, left_on="raceId", right_index=True).merge(res[["raceId", "driverId", "constructor"]], on=["raceId", "driverId"])
und = pd.concat([u.assign(moment="Lap before the stop", step=-1, change=0.0),
                 u.assign(moment="2 laps after", step=2, change=u["b"] - u["p2"]),
                 u.assign(moment="10 laps after", step=10, change=u["b"] - u["p10"])])
und = und.rename(columns={"circuit_short": "circuit", "constructor": "team"})[
    ["year", "circuit", "team", "timing", "moment", "step", "change"]]
DATA["undercut"] = ("undercut.csv", und)

# 6. teammate duel (both cars classified)
tm = rl.dropna(subset=["quali_pos"])
tm = tm[tm["raceId"].isin(ps["raceId"].unique())]
tm = tm[tm.groupby(["raceId", "constructorId"])["driverId"].transform("size") == 2]
tm = tm.sort_values(["raceId", "constructorId", "quali_pos"]).assign(k=lambda d: d.groupby(["raceId", "constructorId"]).cumcount())
fa = tm[tm["k"] == 0].set_index(["raceId", "constructorId"])
sl = tm[tm["k"] == 1].set_index(["raceId", "constructorId"])
pr = pd.DataFrame({"year": sl["year"], "circuit": sl["circuit_short"], "team": sl["constructor"],
                   "stop_diff": sl["n_stops"] - fa["n_stops"], "both": sl["is_classified"] & fa["is_classified"],
                   "slower_wins": (sl["position"] < fa["position"]).astype(int)}).reset_index(drop=True)
pr = pr[pr["both"]].drop(columns="both")
pr["who_extra"] = np.select([pr["stop_diff"] > 0, pr["stop_diff"] < 0],
                            ["Slower qualifier made the extra stop", "Teammate made the extra stop"], "Same number of stops")
pr["slower_wins_pct"] = pr["slower_wins"] * 100
DATA["pairs"] = ("teammate_pairs.csv", pr)

# 7. calendar map
cal = (races.groupby(["circuitId", "circuit_short", "country", "lat", "lng"]).agg(races=("raceId", "nunique")).reset_index()
       .rename(columns={"circuit_short": "circuit"}).merge(circ[["circuit", "r"]], on="circuit", how="left"))
cal["tag"] = "Circuit"
DATA["calendar"] = ("calendar.csv", cal[["circuit", "country", "lat", "lng", "races", "r", "tag"]])

# 8. win chance by starting position
g = res.dropna(subset=["grid"])
gw = g.groupby("grid").agg(starts=("raceId", "size"), win=("is_win", "mean"), podium=("is_podium", "mean")).reset_index()
gw = gw[gw["grid"] <= 20].astype({"grid": int})
gw["win_pct"], gw["podium_pct"] = gw.pop("win") * 100, gw.pop("podium") * 100
gw["group"] = np.where(gw["grid"] <= 2, "Front row (1st-2nd)", "Rest of the grid")
DATA["gridwin"] = ("grid_win.csv", gw)

# 9. points per finishing position (how scoring works)
pts = res[res["position"].between(1, 10)].groupby("position")["points"].median().reset_index().astype({"position": int})
pts["who"] = np.where(pts["position"] == 1, "Winner", "Others")
DATA["points"] = ("points_by_position.csv", pts)

# 10. pit strategy by season (same rule as notebook cell T.2)
st2 = rl[rl["raceId"].isin(ps["raceId"].unique()) & rl["is_classified"] & (rl["n_stops"] >= 1)].copy()
st2["stops"] = st2["n_stops"].clip(upper=3).astype(int).map({1: "1 stop", 2: "2 stops", 3: "3+ stops"})
strat = (st2.groupby(["year", "stops"]).size() / st2.groupby("year").size() * 100).rename("share").reset_index()
DATA["strategy"] = ("strategy.csv", strat)


# 11. why cars retire (same rule as notebook cell T.3)
def dnf_cause(status):
    s = status.lower()
    if any(k in s for k in ["collision", "accident", "spun", "damage", "debris"]):
        return "Crash or contact"
    if any(k in s for k in ["puncture", "tyre", "wheel"]):
        return "Tyre or wheel"
    if any(k in s for k in ["retired", "withdrew", "illness", "disqualified", "excluded", "seat"]):
        return "Other or not stated"
    return "Car failure"


cz = (res[res["is_dnf"]].assign(cause=lambda d: d["status"].map(dnf_cause)).groupby(["year", "cause"]).size()
      / res.groupby("year").size() * 100).rename("rate").reset_index()
DATA["causes"] = ("dnf_causes.csv", cz)

# 12. driver x circuit heatmap (same rule as notebook cell A4.5)
top10 = res.groupby("driver")["points"].sum().nlargest(10).index
cn = res.groupby("circuit_short")["raceId"].nunique()
hm = (res[res["driver"].isin(top10) & res["circuit_short"].isin(cn[cn >= 8].index) & res["is_classified"]]
      .groupby(["driver", "circuit_short"])["position"].agg(["mean", "size"]).reset_index())
hm = hm[hm["size"] >= 3].rename(columns={"circuit_short": "circuit", "mean": "avg_finish", "size": "finishes"})
DATA["heat"] = ("driver_circuit.csv", hm)

# 13. wins and the car
champ = cfin.loc[cfin["position"] == 1, ["year", "constructorId"]].rename(columns={"constructorId": "champ_id"})
wn = res[res["position"] == 1].merge(champ, on="year")
wn["car"] = np.where(wn["constructorId"] == wn["champ_id"], "Champion team's car", "Other car")
top_w = wn["driver"].value_counts().head(10).index
wl = wn[wn["driver"].isin(top_w)].groupby(["driver", "car"]).size().rename("wins").reset_index()
DATA["wins"] = ("wins_by_car.csv", wl)

# 14. the 2024 title fight (for the misleading / honest pair)
tf = cfin[cfin["year"] == 2024].sort_values("position").head(2).rename(columns={"constructor": "team"})[["team", "points"]]
DATA["title"] = ("title_2024.csv", tf)

# ---- cross-check with the notebook's facts (same numbers or the build stops)
checks = {"T.win_p1": f"{gw.loc[gw['grid'] == 1, 'win_pct'].iloc[0]:.0f}%",
          "T.one_2018": f"{strat.query('year == 2018 and stops == \"1 stop\"')['share'].iloc[0]:.0f}%",
          "T.fail_2024": f"{cz.query('year == 2024 and cause == \"Car failure\"')['rate'].iloc[0]:.1f}%",
          "T.n_circuits": f"{len(cal)}", "A1.top_r": f"{circ['r'].iloc[0]:.2f}",
          "A3.rate_extra": f"{pr.loc[pr['stop_diff'] > 0, 'slower_wins_pct'].mean():.0f}%"}
for k, v in checks.items():
    assert F(k) == v, f"{k}: notebook {F(k)} vs Tableau data {v}"
for name, (csv, df) in DATA.items():
    df.to_csv(OUT / csv, index=False)

# ================================================================== workbook XML
RED, INK, DARK, GREY, LIGHT = "#c8102e", "#1a1a1a", "#4d4d4d", "#9a9a9a", "#d0d0d0"
REMOTE = {"integer": 20, "real": 5, "string": 129}
AGG = {"integer": "Sum", "real": "Sum", "string": "Count"}
GEO = {("calendar", "lat"): "[Geographical].[Latitude]", ("calendar", "lng"): "[Geographical].[Longitude]"}


def dtype(s):
    if pd.api.types.is_integer_dtype(s):
        return "integer"
    if pd.api.types.is_float_dtype(s):
        return "real"
    return "string"


COLOURS = {
    "trace": ("driver", lambda df: {**{d: LIGHT for d in sorted(df["driver"].dropna().unique())},
                                    "Lewis Hamilton": RED, "Nico Rosberg": INK}),
    "share": ("team", lambda df: {**{t: LIGHT for t in sorted(df["team"].unique())},
                                  "McLaren": RED, "Mercedes": INK, "Red Bull": DARK, "Ferrari": GREY}),
    "undercut": ("timing", lambda df: {"Early": RED, "Middle": GREY, "Late": DARK}),
    "pairs": ("who_extra", lambda df: {"Slower qualifier made the extra stop": RED, "Same number of stops": GREY,
                                       "Teammate made the extra stop": DARK}),
    "calendar": ("tag", lambda df: {"Circuit": RED}),
    "gridwin": ("group", lambda df: {"Front row (1st-2nd)": RED, "Rest of the grid": GREY}),
    "points": ("who", lambda df: {"Winner": RED, "Others": GREY}),
    "strategy": ("stops", lambda df: {"1 stop": RED, "2 stops": DARK, "3+ stops": LIGHT}),
    "causes": ("cause", lambda df: {"Car failure": RED, "Crash or contact": DARK, "Tyre or wheel": GREY,
                                    "Other or not stated": LIGHT}),
    "wins": ("car", lambda df: {"Champion team's car": RED, "Other car": GREY}),
    "title": ("team", lambda df: {"McLaren": RED, "Ferrari": GREY}),
}


def datasource(name):
    csv, df = DATA[name]
    types = {c: dtype(df[c]) for c in df.columns}
    cols = "\n".join(f"            <column datatype='{t}' name={quoteattr(c)} ordinal='{i}' />" for i, (c, t) in enumerate(types.items()))
    meta = "\n".join(f"""          <metadata-record class='column'>
            <remote-name>{escape(c)}</remote-name>
            <remote-type>{REMOTE[t]}</remote-type>
            <local-name>[{escape(c)}]</local-name>
            <parent-name>[{csv}]</parent-name>
            <remote-alias>{escape(c)}</remote-alias>
            <ordinal>{i}</ordinal>
            <local-type>{t}</local-type>
            <aggregation>{AGG[t]}</aggregation>
            <contains-null>true</contains-null>
          </metadata-record>""" for i, (c, t) in enumerate(types.items()))
    geo = "\n".join(f"      <column datatype='real' name='[{c}]' role='measure' semantic-role='{role}' type='quantitative' />"
                    for (ds, c), role in GEO.items() if ds == name)
    style = ""
    if name in COLOURS:
        field, fn = COLOURS[name]
        maps = "".join(f"<map to='{col}'><bucket>{escape(chr(34) + v + chr(34))}</bucket></map>" for v, col in fn(df).items())
        style = (f"      <style><style-rule element='mark'><encoding attr='color' field='[none:{field}:nk]' type='palette'>"
                 f"{maps}</encoding></style-rule></style>")
    return f"""    <datasource caption='{name}' inline='true' name='federated.{name}' version='18.1'>
      <connection class='federated'>
        <named-connections>
          <named-connection caption='{name}' name='textscan.{name}'>
            <connection class='textscan' directory='Data/csv' filename='{csv}' password='' server='' />
          </named-connection>
        </named-connections>
        <relation connection='textscan.{name}' name='{csv}' table='[{csv.replace(".csv", "#csv")}]' type='table'>
          <columns character-set='UTF-8' header='yes' locale='en_US' separator=','>
{cols}
          </columns>
        </relation>
        <metadata-records>
{meta}
        </metadata-records>
      </connection>
      <aliases enabled='yes' />
{geo}
      <extract count='-1' enabled='true' units='records'>
        <connection authentication='auth-none' author-locale='en_US' class='hyper' dbname='Data/Extracts/{name}.hyper' default-settings='hyper' schema='Extract' sslmode='' tablename='Extract' update-time='11/05/2026 12:00:00 AM' username='tableau_internal_user'>
          <relation name='Extract' table='[Extract].[Extract]' type='table' />
        </connection>
      </extract>
{style}
    </datasource>"""


# field spec: (column, datatype, role, type, derivation, kind)
def D(c, dt="string", kind="nk"):                 # dimension
    t = {"nk": "nominal", "ok": "ordinal", "qk": "quantitative"}[kind]
    return (c, dt, "dimension", t, "none", kind)


def M(c, dt="real", agg="sum"):                   # measure
    return (c, dt, "measure", "quantitative", agg, "qk")


def inst(f):
    return f"[{f[4]}:{f[0]}:{f[5]}]"


def ref(ds, f):
    return f"[federated.{ds}].{inst(f)}"


def worksheet(name, ds, fields, rows, cols, mark, title, color=None, size=None, text=None, lod=None,
              filt=None, sort=None, axes=(), geo=False):
    """rows/cols/color/size/text/lod: field specs from `fields`. axes: (shelf, field, title, extra attributes)."""
    dep_cols = "\n".join(
        f"            <column datatype='{dt}' name='[{c}]' role='{role}' "
        + (f"semantic-role='{GEO[(ds, c)]}' " if (ds, c) in GEO else "") + f"type='{t}' />"
        for c, dt, role, t, d, k in fields)
    dep_inst = "\n".join(f"            <column-instance column='[{c}]' derivation='{'None' if d == 'none' else d.capitalize()}' "
                         f"name='[{d}:{c}:{k}]' pivot='key' type='{t}' />" for c, dt, role, t, d, k in fields)
    view_extra = ""
    if filt:
        f, member = filt
        view_extra += (f"          <filter class='categorical' column='{ref(ds, f)}'>\n"
                       f"            <groupfilter function='member' level='{inst(f)}' member={quoteattr(chr(34) + member + chr(34))} "
                       f"user:ui-domain='database' user:ui-enumeration='inclusive' user:ui-marker='enumerate' />\n"
                       f"          </filter>\n")
    if sort:
        dim, meas, direction = sort
        view_extra += f"          <sort class='computed' column='{ref(ds, dim)}' direction='{direction}' using='{ref(ds, meas)}' />\n"
    if filt:
        view_extra += f"          <slices><column>{ref(ds, filt[0])}</column></slices>\n"
    rules = []
    for shelf, f, atitle, extra in axes:
        if extra:
            rules.append(f"<encoding attr='space' class='0' field='{ref(ds, f)}' field-type='quantitative' {extra} "
                         f"scope='{shelf}' type='space' />")
        rules.append(f"<format attr='title' class='0' field='{ref(ds, f)}' scope='{shelf}' value={quoteattr(atitle)} />")
    style = f"<style><style-rule element='axis'>{''.join(rules)}</style-rule></style>" if rules else "<style />"
    enc = "".join(f"<{tag} column='{ref(ds, f)}' />" for tag, f in [("color", color), ("size", size), ("text", text), ("lod", lod)] if f)
    enc = f"<encodings>{enc}</encodings>" if enc else ""
    maps = "<mapsources><mapsource name='Tableau' /></mapsources>" if geo else ""
    return f"""    <worksheet name={quoteattr(name)}>
      <layout-options><title><formatted-text><run bold='true' fontsize='12'>{escape(title)}</run></formatted-text></title></layout-options>
      <table>
        <view>
          <datasources><datasource caption='{ds}' name='federated.{ds}' /></datasources>
          {maps}
          <datasource-dependencies datasource='federated.{ds}'>
{dep_cols}
{dep_inst}
          </datasource-dependencies>
{view_extra}          <aggregation value='true' />
        </view>
        {style}
        <panes>
          <pane>
            <view><breakdown value='auto' /></view>
            <mark class='{mark}' />
            {enc}
          </pane>
        </panes>
        <rows>{ref(ds, rows)}</rows>
        <cols>{ref(ds, cols)}</cols>
      </table>
    </worksheet>"""


W = {}                                            # worksheet name -> XML
# ---- the six story charts
lap, posn, drv, race, team_t = D("lap", "integer", "qk"), M("position", "integer", "avg"), D("driver"), D("race"), D("team")
W["Race trace"] = worksheet("Race trace", "trace", [lap, posn, drv, race, team_t], posn, lap, "Line",
                            f"Hook: {F('H.changes')} position changes, and the pole-sitter still won (red = Hamilton, black = Rosberg)",
                            color=drv, lod=team_t, filt=(race, "2016 Chinese GP"),
                            axes=[("rows", posn, "Position (1 = leading)", "reverse='true'"), ("cols", lap, "Lap (0 = starting grid)", "")])
cc, rr_ = D("circuit"), M("r")
W["Grid vs finish by circuit"] = worksheet("Grid vs finish by circuit", "circuit", [cc, rr_], cc, rr_, "Circle",
                                           f"Act 1: {F('A1.top_circuit')} locks the order in (grid-finish link r by circuit)",
                                           sort=(cc, rr_, "DESC"), axes=[("cols", rr_, "Link between grid and finish (r)", "")])
step, chg, timing = D("step", "integer", "qk"), M("change", "real", "avg"), D("timing")
W["Undercut"] = worksheet("Undercut", "undercut", [step, chg, timing], chg, step, "Line",
                          f"Act 2: early stoppers lose {F('A2.early_lost2_round')} places, then win back {F('A2.early_back')}",
                          color=timing, axes=[("rows", chg, "Places gained (+) or lost (-)", ""),
                                              ("cols", step, "Laps relative to the first pit stop", "")])
wx, swp = D("who_extra"), M("slower_wins_pct", "integer", "avg")
W["Teammate duel"] = worksheet("Teammate duel", "pairs", [wx, swp], swp, wx, "Bar",
                               "Act 3: whoever makes the extra stop usually loses the teammate duel", color=wx,
                               axes=[("rows", swp, "Slower qualifier finishes ahead (%)", "")])
yr_s, shr, tm_s = D("year", "integer", "ok"), M("share"), D("team")
W["Points share"] = worksheet("Points share", "share", [yr_s, shr, tm_s], shr, yr_s, "Line",
                              "Act 4: three eras in ten seasons (share of all constructor points, %)", color=tm_s,
                              axes=[("rows", shr, "Share of all constructor points (%)", "")])
yr_r, dnfp = D("year", "integer", "ok"), M("dnf_pct", "integer", "avg")
W["DNF rate"] = worksheet("DNF rate", "results", [yr_r, dnfp], dnfp, yr_r, "Line",
                          f"Act 4: cars break down half as often ({F('A4.dnf_2015_r')} to {F('A4.dnf_2024_r')})",
                          axes=[("rows", dnfp, "Genuine DNF rate (%)", "")])
# ---- new charts that explain F1
lat, lng, nr, tag, ccal = M("lat", "real", "avg"), M("lng", "real", "avg"), M("races", "integer"), D("tag"), D("circuit")
W["Where F1 races"] = worksheet("Where F1 races", "calendar", [lat, lng, nr, tag, ccal], lat, lng, "Circle",
                                f"F1 travels the world: {F('T.n_circuits')} circuits in {F('T.n_countries')} countries (bigger = more races)",
                                color=tag, size=nr, lod=ccal, geo=True)
gslot, wp, grp = D("grid", "integer", "ok"), M("win_pct", "real", "avg"), D("group")
W["Win chance by grid slot"] = worksheet("Win chance by grid slot", "gridwin", [gslot, wp, grp], wp, gslot, "Bar",
                                         f"Start on pole and you win {F('T.win_p1')} of the time; the front row wins {F('T.front_row')}",
                                         color=grp, axes=[("rows", wp, "Races won from this starting slot (%)", ""),
                                                          ("cols", gslot, "Starting position (grid)", "")])
fpos, fpts, whov = D("position", "integer", "ok"), M("points", "real", "avg"), D("who")
W["Points per finish"] = worksheet("Points per finish", "points", [fpos, fpts, whov], fpts, fpos, "Bar",
                                   "How scoring works: only the top ten score, 25 points for a win", color=whov,
                                   axes=[("rows", fpts, "Points scored", ""), ("cols", fpos, "Finishing position", "")])
yr_t, sshare, stops = D("year", "integer", "ok"), M("share"), D("stops")
W["Pit strategy by season"] = worksheet("Pit strategy by season", "strategy", [yr_t, sshare, stops], sshare, yr_t, "Bar",
                                        f"Pit strategy swings between seasons: one-stop finishers {F('T.one_2016')} (2016), "
                                        f"{F('T.one_2018')} (2018), {F('T.one_2024')} (2024)", color=stops,
                                        axes=[("rows", sshare, "Share of finishers (%)", "")])
yr_c, rate, cause = D("year", "integer", "ok"), M("rate"), D("cause")
W["Why cars retire"] = worksheet("Why cars retire", "causes", [yr_c, rate, cause], rate, yr_c, "Bar",
                                 f"Cars break less, drivers still crash: car failures {F('T.fail_2015')} to {F('T.fail_2024')} of starts",
                                 color=cause, axes=[("rows", rate, "Share of all starts that ended in a DNF (%)", "")])
hd, hc, havg = D("driver"), D("circuit"), M("avg_finish", "real", "avg")
W["Driver x circuit"] = worksheet("Driver x circuit", "heat", [hd, hc, havg], hd, hc, "Square",
                                  f"The driver row matters more than the track column ({F('A4.hm_row_range')} vs "
                                  f"{F('A4.hm_col_range')} places; lower = better)", color=havg, text=havg)
wd, wcar, wwins = D("driver"), D("car"), M("wins", "integer")
W["Wins and the car"] = worksheet("Wins and the car", "wins", [wd, wcar, wwins], wd, wwins, "Bar",
                                  f"{F('A4.wins_champ_car')} of all race wins went to that season's champion team",
                                  color=wcar, sort=(wd, wwins, "DESC"), axes=[("cols", wwins, "Race wins, 2015-2024", "")])
tt, tp = D("team"), M("points")
W["Misleading (cut axis)"] = worksheet("Misleading (cut axis)", "title", [tt, tp], tp, tt, "Bar",
                                       f"MISLEADING (for ethics demonstration): {F('A5.lead')} crushed {F('A5.second')}?",
                                       color=tt, axes=[("rows", tp, f"Points (axis starts at {F('A5.base')})",
                                                        f"max='670' min='{F('A5.base')}' range-type='fixed'")])
W["Honest (axis from 0)"] = worksheet("Honest (axis from 0)", "title", [tt, tp], tp, tt, "Bar",
                                      f"Honest: {F('A5.lead')} won by {F('A5.gap')} points ({F('A5.gap_pct')})",
                                      color=tt, axes=[("rows", tp, "Points (axis starts at 0)", "max='760' min='0' range-type='fixed'")])


# ================================================================== dashboards, story, actions
def text_zone(zid, x, y, w, h, lines, size=11, bold_first=False):
    runs = []
    for i, line in enumerate(lines):
        head = bold_first and i == 0
        runs.append(f"<run{' bold=' + chr(39) + 'true' + chr(39) if head else ''} fontsize='{size + 4 if head else size}'>"
                    f"{escape(line)}&#10;</run>")
    return f"<zone h='{h}' id='{zid}' type='text' w='{w}' x='{x}' y='{y}'><formatted-text>{''.join(runs)}</formatted-text></zone>"


def sheet_zone(zid, name, x, y, w, h):
    return f"<zone h='{h}' id='{zid}' name={quoteattr(name)} w='{w}' x='{x}' y='{y}' />"


def dashboard(name, zones, w=1500, h=1000):
    return f"""    <dashboard name={quoteattr(name)}>
      <style />
      <size maxheight='{h}' maxwidth='{w}' minheight='{h}' minwidth='{w}' />
      <zones>
        <zone h='100000' id='2' type='layout-basic' w='100000' x='0' y='0'>
          {"".join(zones)}
        </zone>
      </zones>
    </dashboard>"""


DASH = {}
DASH["F1 in 60 seconds"] = dashboard("F1 in 60 seconds", [
    text_zone(3, 0, 0, 100000, 6000, ["F1 in 60 seconds: how a Formula 1 race works"], size=14, bold_first=True),
    text_zone(4, 0, 6000, 32000, 94000, [
        "The basics",
        "Race: about twenty cars race for many laps. The first car across the line wins.",
        "Teams (constructors) build their own cars and run two each. The two drivers are teammates, in the same car.",
        "Qualifying (Saturday): one very fast lap each. The fastest starts at the front. The starting order is the grid; "
        "starting first is called pole position.",
        f"Pit stop: tyres wear out, so cars stop to change them. A stop costs about {F('P.pit_median_normal')} seconds, "
        "so the car loses places.",
        "Undercut: stopping before a rival, so your new tyres are faster and you pass them when they stop.",
        "DNF: 'did not finish', the car crashed or broke down.",
        "Points: the top ten score, 25 for a win. The most points over a year wins the drivers' and the teams' championship.",
        "Use the Story tab 'How F1 works' to walk through it, or the 'F1 Dashboard' tab to explore."], size=12, bold_first=True),
    sheet_zone(5, "Where F1 races", 32000, 6000, 68000, 50000),
    sheet_zone(6, "Win chance by grid slot", 32000, 56000, 34000, 44000),
    sheet_zone(7, "Points per finish", 66000, 56000, 34000, 44000)])
main = ["Race trace", "Grid vs finish by circuit", "Undercut", "Teammate duel", "Points share", "DNF rate"]
DASH["F1 Dashboard"] = dashboard("F1 Dashboard", [
    text_zone(3, 0, 0, 62000, 5000, ["Formula 1, read as a chain of cause and effect (2015-2024)"], size=14, bold_first=True),
    "<zone h='5000' id='4' mode='dropdown' name='Race trace' param='[federated.trace].[none:race:nk]' type='filter' w='38000' x='62000' y='0' />",
    text_zone(5, 0, 5000, 100000, 3000, ["Tip: click a circuit (Act 1) or a season point (Act 4) to filter the other charts; "
                                         "click it again to reset. Hover a team line to light up its cars in the race trace."], size=11)]
    + [sheet_zone(6 + i, n, (i % 2) * 50000, 8000 + (i // 2) * 30666, 50000, 30666) for i, n in enumerate(main)])
deep = ["Pit strategy by season", "Why cars retire", "Driver x circuit", "Wins and the car"]
DASH["Deep dive"] = dashboard("Deep dive", [
    text_zone(3, 0, 0, 100000, 5000, ["Deep dive: strategy, reliability, drivers and cars"], size=14, bold_first=True)]
    + [sheet_zone(4 + i, n, (i % 2) * 50000, 5000 + (i // 2) * 47500, 50000, 47500) for i, n in enumerate(deep)])
DASH["Ethics"] = dashboard("Ethics", [
    text_zone(3, 0, 0, 100000, 5000, ["Same numbers, two stories: how a chart can lie"], size=14, bold_first=True),
    sheet_zone(4, "Misleading (cut axis)", 0, 5000, 50000, 70000),
    sheet_zone(5, "Honest (axis from 0)", 50000, 5000, 50000, 70000),
    text_zone(6, 0, 75000, 100000, 25000, [
        f"What was manipulated: only the y-axis. The left chart starts at {F('A5.base')} points, not 0. Every number is real: "
        f"{F('A5.lead')} {F('A5.lead_pts')}, {F('A5.second')} {F('A5.second_pts')}.",
        f"Why it misleads: a bar shows value by its length, so {F('A5.lead')}'s bar looks {F('A5.visual_ratio')} times taller "
        f"for a {F('A5.gap_pct')} gap. False impression: '{F('A5.lead')} crushed {F('A5.second')}'. "
        f"In fact it was {F('A5.closest')} constructors' title of the decade.",
        f"The fix: the axis starts at zero (truthful scaling, proportional ink). Lie factor about {F('A5.lie_factor')}; an honest chart is 1."],
        size=12)])

STORY = [
    ("F1 in 60 seconds", "F1 in 60 seconds: ten teams, two cars each, points for the top ten. Start here."),
    ("Where F1 races", f"F1 travels the world: {F('T.n_circuits')} circuits, {F('T.n_countries')} countries, {F('P.n_races')} races."),
    ("Race trace", f"A race is a chain of moves: {F('H.changes')} position changes in the {F('H.race')}."),
    ("Win chance by grid slot", f"Saturday matters: pole wins {F('T.win_p1')} of races, the front row {F('T.front_row')}."),
    ("Grid vs finish by circuit", f"Some tracks lock the order in: {F('A1.top_circuit')} {F('A1.top_r')}, "
                                  f"{F('A1.bottom_circuit')} only {F('A1.bottom_r')}."),
    ("Undercut", f"Pit early, gain later: early stoppers drop {F('A2.early_lost2')} places, then win back {F('A2.early_back')}."),
    ("Pit strategy by season", f"Pit strategy swings between seasons: one-stop finishers {F('T.one_2016')} in 2016, {F('T.one_2018')} in 2018."),
    ("Teammate duel", f"An extra stop is an alarm: the slower teammate wins {F('A3.rate_extra')} of duels with one, {F('A3.rate_no')} without."),
    ("Points share", "The car sets the ceiling: Mercedes, then Red Bull, then McLaren."),
    ("Why cars retire", f"Cars break less, drivers still crash: car failures fell {F('T.fail_drop')}, crashes barely changed."),
    ("Driver x circuit", f"The driver beats the track: rows differ by {F('A4.hm_row_range')} places, tracks by {F('A4.hm_col_range')}."),
    ("Wins and the car", f"{F('A4.wins_champ_car')} of all wins went to that season's champion team."),
    ("Ethics", f"Same numbers, two stories: a cut axis makes a {F('A5.gap_pct')} gap look {F('A5.visual_ratio')} times bigger."),
    ("F1 Dashboard", "Your turn: click a circuit or a season and watch the other charts change."),
]
points = "\n".join(f"                <story-point caption={quoteattr(c)} captured-sheet={quoteattr(s)} id='{i}' />"
                   for i, (s, c) in enumerate(STORY, 1))
story = f"""    <dashboard name='How F1 works' type='storyboard'>
      <layout-options><title><formatted-text><run>How F1 works: a race, read as a chain of cause and effect</run></formatted-text></title></layout-options>
      <style><style-rule element='story-point-caption'><format attr='background-color' value='#f2f2f2' /></style-rule></style>
      <size maxheight='1000' maxwidth='1500' minheight='1000' minwidth='1500' />
      <zones>
        <zone h='100000' id='2' type='layout-basic' w='100000' x='0' y='0'>
          <zone h='100000' id='1' param='vert' removable='false' type='layout-flow' w='100000' x='0' y='0'>
            <zone h='5000' id='3' type='title' w='100000' x='0' y='0' />
            <zone fixed-size='110' h='12000' id='4' is-fixed='true' paired-zone-id='5' removable='false' type='flipboard-nav' w='100000' x='0' y='5000' />
            <zone h='83000' id='5' paired-zone-id='4' removable='false' type='flipboard' w='100000' x='0' y='17000'>
              <flipboard active-id='1' nav-type='caption' show-nav-arrows='true'>
                <story-points>
{points}
                </story-points>
              </flipboard>
            </zone>
          </zone>
        </zone>
      </zones>
    </dashboard>"""


def action(i, caption, cmd, src_sheet, params, on="on-select"):
    p = "".join(f"<param name='{k}' value={quoteattr(v)} />" for k, v in params.items())
    return (f"    <action caption={quoteattr(caption)} name='[Action{i}_F1]'>\n"
            f"      <activation auto-clear='true' type='{on}' />\n"
            f"      <source dashboard='F1 Dashboard' type='sheet' worksheet={quoteattr(src_sheet)} />\n"
            f"      <command command='{cmd}'>{p}</command>\n    </action>")


actions = "\n".join([
    action(1, "Click a circuit to filter the other charts", "tsc:tsl-filter", "Grid vs finish by circuit",
           {"exclude": "Race trace,Points share", "special-fields": "all", "target": "F1 Dashboard"}),
    action(2, "Click a season to filter the other charts", "tsc:tsl-filter", "Points share",
           {"exclude": "Race trace,Grid vs finish by circuit", "special-fields": "all", "target": "F1 Dashboard"}),
    action(3, "Hover a team to light up its cars", "tsc:brush", "Points share",
           {"field-captions": "team", "target": "F1 Dashboard"}, on="on-hover"),
])

win = []
for n in W:
    win.append(f"    <window class='worksheet' name={quoteattr(n)}><cards><edge name='left'><strip size='160'>"
               f"<card type='pages' /><card type='filters' /><card type='marks' /></strip></edge></cards></window>")
for n, zones_of in [("F1 in 60 seconds", ["Where F1 races", "Win chance by grid slot", "Points per finish"]),
                    ("F1 Dashboard", main), ("Deep dive", deep), ("Ethics", ["Misleading (cut axis)", "Honest (axis from 0)"])]:
    vps = "".join(f"<viewpoint name={quoteattr(s)}><zoom type='entire-view' /></viewpoint>" for s in zones_of)
    win.append(f"    <window class='dashboard' name={quoteattr(n)}><viewpoints>{vps}</viewpoints><active id='-1' /></window>")
win.append("    <window class='dashboard' maximized='true' name='How F1 works'><viewpoints /><active id='-1' /></window>")

twb = f"""<?xml version='1.0' encoding='utf-8' ?>
<workbook original-version='18.1' source-build='2024.2.0 (20242.24.0807.0327)' source-platform='mac' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <preferences />
  <datasources>
{chr(10).join(datasource(n) for n in DATA)}
  </datasources>
  <mapsources><mapsource name='Tableau' /></mapsources>
  <actions>
{actions}
  </actions>
  <worksheets>
{chr(10).join(W.values())}
  </worksheets>
  <dashboards>
{chr(10).join(DASH.values())}
{story}
  </dashboards>
  <windows>
{chr(10).join(win)}
  </windows>
</workbook>
"""

# ================================================================== extracts and package
HYPER = {"integer": SqlType.big_int, "real": SqlType.double, "string": SqlType.text}
CONV = {"integer": int, "real": float, "string": str}
work = Path(tempfile.mkdtemp())
(work / "Data" / "Extracts").mkdir(parents=True)
(work / "Data" / "csv").mkdir(parents=True)
with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU, parameters={"log_dir": tempfile.gettempdir()}) as hp:
    for name, (csv, df) in DATA.items():
        types = {c: dtype(df[c]) for c in df.columns}
        td = TableDefinition(TableName("Extract", "Extract"), [TableDefinition.Column(c, HYPER[t](), NULLABLE) for c, t in types.items()])
        with Connection(hp.endpoint, work / "Data" / "Extracts" / f"{name}.hyper", CreateMode.CREATE_AND_REPLACE) as con:
            con.catalog.create_schema("Extract")
            con.catalog.create_table(td)
            data_rows = [[None if pd.isna(v) else CONV[types[c]](v) for v, c in zip(rec, df.columns)]
                         for rec in df.itertuples(index=False)]
            with Inserter(con, td) as ins:
                ins.add_rows(data_rows)
                ins.execute()
        (work / "Data" / "csv" / csv).write_bytes((OUT / csv).read_bytes())
(work / "F1_Dashboard.twb").write_text(twb, encoding="utf-8")
(OUT / "F1_Dashboard.twb").unlink(missing_ok=True)
with zipfile.ZipFile(OUT / "F1_Dashboard.twbx", "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(work.rglob("*")):
        if f.is_file():
            z.write(f, f.relative_to(work).as_posix())
print(f"wrote {OUT / 'F1_Dashboard.twbx'}: {len(DATA)} data sources, {len(W)} worksheets, "
      f"{len(DASH)} dashboards, a {len(STORY)}-point story")
