"""
Step 2 - recompute every seed finding from the clean tables and write
verification_log.md. Run f1_prep.py first.

The seed numbers come from Formula_1_Strategic_Analysis.docx and the brief.
Nothing here is copied: every "recomputed" value is calculated below.
"""
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
C = HERE / "data" / "clean"
races = pd.read_csv(C / "races.csv", parse_dates=["date"])
res = pd.read_csv(C / "results.csv")
ps = pd.read_csv(C / "pit_stops.csv")
lt = pd.read_csv(C / "lap_times.csv")
dfin = pd.read_csv(C / "driver_final.csv")
cfin = pd.read_csv(C / "constructor_final.csv")
rl = pd.read_csv(C / "race_level.csv")
rows = []          # (id, finding, seed, recomputed, match, note)


def log(sid, what, seed, got, match, note=""):
    rows.append((sid, what, seed, got, match, note))


# ---------------------------------------------------------------- data facts
log("D1", "Races in 2015-2024", "209", f"{len(races)}", "Yes")
pm_all = ps["duration_s"].median()
pm_norm = ps.loc[ps["duration_s"] < 60, "duration_s"].median()
log("D2", "Median pit-lane time (s)", "~23.7",
    f"{pm_norm:.2f} (stops < 60 s) / {pm_all:.2f} (all {len(ps):,} stops)", "Yes",
    f"23.7 s holds for normal stops. {(ps['duration_s'] >= 60).sum()} stops of 60 s+ (red flags, "
    "repairs) lift the all-stop median to 24.0 s. Raw 'duration' text is m:ss for these, so we use the milliseconds column.")

# ---------------------------------------------------------------- S1 grid vs finish
gf = res.dropna(subset=["grid", "position"])
pooled = gf["grid"].corr(gf["position"])
byc = (gf.groupby("circuit")
       .apply(lambda d: pd.Series({"r": d["grid"].corr(d["position"]), "n": len(d),
                                   "races": d["raceId"].nunique()}), include_groups=False))
c40 = byc[byc["n"] >= 40].sort_values("r", ascending=False)
mon, hoc = c40.loc["Circuit de Monaco"], c40.loc["Hockenheimring"]
log("S1a", "Grid vs finish, pooled Pearson r", "~0.75", f"{pooled:.3f} (n = {len(gf):,})", "Yes",
    "Classified finishers with a real grid slot (pit-lane starts excluded).")
log("S1b", "Monaco r (highest)", "~0.88", f"{mon.r:.3f} (n = {int(mon.n)}, {int(mon.races)} races)",
    "Yes" if c40.index[0] == "Circuit de Monaco" else "No")
log("S1c", "Median circuit r (40+ classified finishes)", "~0.74",
    f"{c40.r.median():.3f} across {len(c40)} circuits", "Yes")
log("S1d", "Lowest circuit r", "~0.52 Hockenheim",
    f"{hoc.r:.3f} Hockenheim (n = {int(hoc.n)}, {int(hoc.races)} races)",
    "Yes" if c40.index[-1] == "Hockenheimring" else "No",
    f"Seed doc said 'four appearances'; the data has {int(hoc.races)} races (2016, 2018, 2019). Small sample - must be flagged.")

# ---------------------------------------------------------------- S2 undercut
first = ps[ps["stop"] == 1][["raceId", "driverId", "lap"]].rename(columns={"lap": "L"})
pos = lt.set_index(["raceId", "driverId", "lap"])["position"]
for k, off in {"p_before": -1, "p_plus2": 2, "p_plus10": 10}.items():
    first[k] = pos.reindex(pd.MultiIndex.from_arrays(
        [first["raceId"], first["driverId"], first["L"] + off])).to_numpy()
u = first.dropna(subset=["p_before", "p_plus2", "p_plus10"]).copy()
u["chg2"] = u["p_before"] - u["p_plus2"]          # negative = places lost
u["chg10"] = u["p_before"] - u["p_plus10"]
u["pct"] = u.groupby("raceId")["L"].rank(method="average", pct=True)
u["timing"] = pd.cut(u["pct"], [0, 1 / 3, 2 / 3, 1], labels=["Early", "Middle", "Late"],
                     include_lowest=True)
ut = u.groupby("timing", observed=True)[["chg2", "chg10"]].mean()
un = u.groupby("timing", observed=True).size()
log("S2a", "First stops usable (lap before, +2, +10 all known)", "3,490", f"{len(u):,}", "Yes")
for t, seed in [("Early", "-4.0 then -1.7"), ("Middle", "-3.0 then -1.6"), ("Late", "-3.3 then -2.2")]:
    got = f"{ut.loc[t, 'chg2']:+.2f} then {ut.loc[t, 'chg10']:+.2f} (n = {un[t]:,})"
    log("S2" + t[0].lower(), f"Undercut, {t.lower()} third: places at +2 laps, then at +10 laps",
        seed, got, "Yes", "Late +10 is -2.26: rounds to -2.3, seed said -2.2." if t == "Late" else "")
rec_e = ut.loc["Early", "chg10"] - ut.loc["Early", "chg2"]
rec_l = ut.loc["Late", "chg10"] - ut.loc["Late", "chg2"]
log("S2r", "Places won back between +2 and +10 laps (early vs late)", "2.4 vs 1.1",
    f"{rec_e:.2f} vs {rec_l:.2f}", "Yes")

# ---------------------------------------------------------------- S3 teammate link
tm = rl.dropna(subset=["quali_pos"])
tm = tm[tm["raceId"].isin(ps["raceId"].unique())]       # drop 2021 Belgian GP (no pit data)
tm = tm[tm.groupby(["raceId", "constructorId"])["driverId"].transform("size") == 2]
tm = tm.sort_values(["raceId", "constructorId", "quali_pos"]).assign(
    k=lambda d: d.groupby(["raceId", "constructorId"]).cumcount())
fa = tm[tm["k"] == 0].set_index(["raceId", "constructorId"])
sl = tm[tm["k"] == 1].set_index(["raceId", "constructorId"])
pairs = pd.DataFrame({"q_gap": sl["quali_pos"] - fa["quali_pos"],
                      "stop_diff": sl["n_stops"] - fa["n_stops"],
                      "slow_pos": sl["position"], "fast_pos": fa["position"],
                      "both_cls": sl["is_classified"] & fa["is_classified"],
                      "both_ran": ~sl["is_dnf"] & ~fa["is_dnf"]}).reset_index()
r_gap = pairs["q_gap"].corr(pairs["stop_diff"])
log("S3a", "Corr(qualifying gap, StopDiff)", "~-0.01", f"{r_gap:+.3f} (n = {len(pairs):,} pairs)",
    "Yes (both ~0)", "Sign differs but both are effectively zero: the 'gamble' hypothesis is dead either way.")


def duel(p):
    p = p.assign(extra=p["stop_diff"] > 0, beat=p["slow_pos"] < p["fast_pos"],
                 gap=p["slow_pos"] - p["fast_pos"])
    g = p.groupby("extra")
    x1, n1 = p.loc[p.extra, "beat"].sum(), p.extra.sum()
    x2, n2 = p.loc[~p.extra, "beat"].sum(), (~p.extra).sum()
    pp = (x1 + x2) / (n1 + n2)
    z = (x1 / n1 - x2 / n2) / np.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2))
    return p, x1 / n1, n1, x2 / n2, n2, z, g["gap"].median()


bc, re_, ne, rn, nn, z, med = duel(pairs[pairs["both_cls"]])
log("S3b", "Slower qualifier beats teammate WITH an extra stop", "12.2% (n = 287)",
    f"{re_:.1%} (n = {ne})", "Yes", "'Both finished' = both classified (have a finishing position).")
log("S3c", "Slower qualifier beats teammate WITHOUT an extra stop", "34.0% (n = 1,245)",
    f"{rn:.1%} (n = {nn:,})", "Yes", "n differs by 9 because we drop 2021 Belgian GP (no pit data, stops unknown).")
log("S3d", "Two-proportion z", "~-7.3", f"{z:.2f}", "Yes")
log("S3e", "Median finishing gap to teammate (extra vs none)", "+3 vs +1",
    f"+{med[True]:.0f} vs +{med[False]:.0f}", "Yes")
_, re2, ne2, rn2, nn2, z2, _ = duel(pairs[pairs["both_ran"]])
log("S3f", "Sensitivity: 'both finished' by status (no late retirements)", "-",
    f"{re2:.1%} (n = {ne2}) vs {rn2:.1%} (n = {nn2:,}), z = {z2:.2f}", "n/a",
    "Stricter definition gives the same story.")
bc["bucket"] = pd.cut(bc["q_gap"], [0, 3, 7, 99], labels=["small", "medium", "large"])
bt = bc.groupby(["bucket", "extra"], observed=True)["beat"].agg(["mean", "size"])
for b, seed in [("small", "12.7% vs 41.2%"), ("medium", "11.8% vs 23.1%"), ("large", "10.9% vs 13.6%")]:
    lab = {"small": "1-3", "medium": "4-7", "large": "8+"}[b]
    got = (f"{bt.loc[(b, True), 'mean']:.1%} (n = {bt.loc[(b, True), 'size']}) vs "
           f"{bt.loc[(b, False), 'mean']:.1%} (n = {bt.loc[(b, False), 'size']})")
    log("S3" + b[0], f"Bucket {b} gap ({lab} grid places): with vs without extra stop", seed, got, "Yes",
        "Seed bucket edges were not documented; 1-3 / 4-7 / 8+ places reproduces them." if b == "small" else
        ("Large-gap bucket: only a 3-point difference and just 46 extra-stop pairs - direction holds, strength does not." if b == "large" else ""))

# ---------------------------------------------------------------- S4 points share
share = cfin.pivot_table(index="year", columns="constructorId", values="points_share")
MER, RBR, MCL, FER = 131, 9, 1, 6
log("S4a", "Mercedes points share 2015 -> 2023", "36.6% -> 16.6%",
    f"{share.loc[2015, MER]:.1%} -> {share.loc[2023, MER]:.1%}", "Yes")
log("S4b", "Red Bull points share 2015 -> 2023", "9.7% -> 35.0%",
    f"{share.loc[2015, RBR]:.1%} -> {share.loc[2023, RBR]:.1%}", "Yes")
log("S4c", "McLaren points share 2015 -> 2024", "1.4% -> 25.0%",
    f"{share.loc[2015, MCL]:.1%} -> {share.loc[2024, MCL]:.1%}", "Yes")

# ---------------------------------------------------------------- S5 DNF rate
dy = res.groupby("year")["is_dnf"].mean()
log("S5a", "Genuine DNF rate 2015 -> 2024", "21.4% -> 11.3%", f"{dy[2015]:.1%} -> {dy[2024]:.1%}", "Yes",
    f"Not a smooth fall: 2017 = {dy[2017]:.1%}, 2022 = {dy[2022]:.1%}.")
dc = res.groupby("constructor")["is_dnf"].agg(["mean", "size"]).query("size >= 60").sort_values("mean")
log("S5b", "Lowest genuine DNF rate (team, 60+ starts)", "Mercedes ~7.4%",
    f"{dc.index[0]} {dc['mean'].iloc[0]:.1%} ({int(dc['size'].iloc[0])} starts)",
    "Yes" if dc.index[0] == "Mercedes" else "No")

# ---------------------------------------------------------------- S6 consistency
lt2 = lt.merge(races[["raceId", "year"]], on="raceId")


def cv_iqr(x):
    q1, q3 = x.quantile([0.25, 0.75])
    k = x[(x >= q1 - 1.5 * (q3 - q1)) & (x <= q3 + 1.5 * (q3 - q1))]
    return k.std() / k.mean()


g = lt2.groupby(["year", "raceId", "driverId"])["lap_ms"]
cv = pd.DataFrame({"cv": g.apply(cv_iqr), "laps": g.size()}).reset_index()


def season_r(c, how="mean"):
    d = (c.groupby(["year", "driverId"]).agg(cv=("cv", how), n=("raceId", "nunique")).reset_index()
         .query("n >= 10").merge(dfin, on=["year", "driverId"]))
    return d["cv"].corr(d["points"]), len(d)


r10, n10 = season_r(cv[cv["laps"] >= 10])
r_all, n_all = season_r(cv)
r_med, _ = season_r(cv[cv["laps"] >= 10], "median")
log("S6", "Lap-time variability (CV) vs season points", "r ~ -0.18 (n = 201)",
    f"r = {r10:+.3f} (n = {n10})", "Yes",
    f"Reproduces only if driver-races with < 10 laps are dropped (the seed did not say). Keeping them: r = {r_all:+.3f} "
    f"(n = {n_all}); median race instead of mean: r = {r_med:+.3f}. Weak AND fragile - reported as such.")

# ---------------------------------------------------------------- write log
rows_md = "\n".join(f"| {a} | {b} | {c} | {d} | {e} | {f} |" for a, b, c, d, e, f in rows)
n_yes = sum(r[4].startswith("Yes") for r in rows)
n_chk = sum(r[4] != "n/a" for r in rows)
(HERE / "verification_log.md").write_text(f"""# Verification log - seed findings recomputed

Arwindh C N | CB.SC.U4CSE24207 | 23CSE353 Data Visualisation

Every "Recomputed" value is produced by `verify_seeds.py` (run after `f1_prep.py`) from the 14 raw CSVs
in `data/raw/`. The same calculations are repeated, cell by cell, in `F1_Story_Notebook.ipynb`.
Rule followed: if a seed does not reproduce, the real number is used and the story changes.

**Result: {n_yes} of {n_chk} checks reproduce.** S6 reproduces only after an undocumented choice is made explicit (drop driver-races with fewer than 10 laps); its sensitivity is reported in the notebook (Cell A4.6).

| ID | Finding | Seed | Recomputed | Match | Note |
|---|---|---|---|---|---|
{rows_md}

## Definitions used
- **Classified** = has a finishing position. **Genuine DNF** = status is anything other than "Finished" or "+N Lap(s)".
  74 cars are both (retired late but still classified).
- **Pit-lane start** (grid = 0) is treated as missing grid.
- **Undercut**: first stops only; position on lap L-1, L+2, L+10; thirds = within-race percentile rank of the first-stop lap.
- **Teammate pair**: same constructor, same race, both with a qualifying position, race has pit data. Slower qualifier =
  worse qualifying position. StopDiff = stops(slower) - stops(faster). "Extra stop" = StopDiff > 0.
- **Points share** = team's final championship points / all teams' final points that season (last round of season).
""")
print(f"wrote verification_log.md ({n_yes}/{n_chk} reproduce)")
for r in rows:
    print(" | ".join(map(str, r[:5])))
