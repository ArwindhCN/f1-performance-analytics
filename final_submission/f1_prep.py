"""
F1 Performance Analytics 2015-2024 - data cleaning and merge.

Student : Arwindh C N | CB.SC.U4CSE24207 | 23CSE353 Data Visualisation

Reads the 14 raw Ergast-style CSVs in data/raw/, cleans them, and writes tidy
tables to data/clean/. Every cleaning step is numbered (P1, P2, ...) so the
report and the notebook can point to it. The "# %%" markers split this file
into notebook cells.

Run:  python f1_prep.py
"""

# %%
# P0. Imports and paths
from pathlib import Path
import re
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
RAW = HERE / "data" / "raw"
CLEAN = HERE / "data" / "clean"
CLEAN.mkdir(parents=True, exist_ok=True)
FIRST_SEASON, LAST_SEASON = 2015, 2024


def read_raw(name):
    """P1. The raw files write missing values as the two characters \\N.
    We tell pandas that \\N means 'missing' and switch off its other guesses,
    so a real value is never turned into NaN by accident."""
    return pd.read_csv(RAW / f"{name}.csv", na_values=[r"\N"], keep_default_na=False)


raw = {n: read_raw(n) for n in [
    "races", "results", "drivers", "constructors", "circuits", "status",
    "qualifying", "pit_stops", "lap_times", "sprint_results",
    "driver_standings", "constructor_standings", "constructor_results", "seasons"]}
print({k: len(v) for k, v in raw.items()})

# %%
# P2. Keep seasons 2015-2024 only (209 races). The file has no 2025 data.
races = raw["races"].query("@FIRST_SEASON <= year <= @LAST_SEASON").copy()
assert raw["races"]["year"].max() == 2024, "unexpected season in source"
assert len(races) == 209, len(races)
RACE_IDS = set(races["raceId"])

circuits = raw["circuits"][["circuitId", "circuitRef", "name", "location", "country", "lat", "lng"]]
circuits = circuits.rename(columns={"name": "circuit"})
# Short, readable circuit names for chart labels (official names are very long).
SHORT = {"Monte-Carlo": "Monaco", "Montmeló": "Barcelona", "Marina Bay": "Singapore",
         "Al Daayen": "Qatar", "Sakhir": "Bahrain", "Spielberg": "Austria",
         "Le Castellet": "France", "Nürburg": "Nürburgring", "Kuala Lumpur": "Malaysia",
         "Austin": "Austin (USA)"}
circuits["circuit_short"] = circuits["location"].replace(SHORT)
races = (races[["raceId", "year", "round", "circuitId", "name", "date"]]
         .rename(columns={"name": "race"})
         .merge(circuits, on="circuitId", how="left", validate="many_to_one"))
races["date"] = pd.to_datetime(races["date"])
races["race_label"] = races["year"].astype(str) + " " + races["race"].str.replace(" Grand Prix", " GP")

drivers = raw["drivers"].assign(driver=lambda d: d["forename"] + " " + d["surname"])
drivers = drivers[["driverId", "driverRef", "code", "driver"]]
constructors = raw["constructors"][["constructorId", "constructorRef", "name"]].rename(
    columns={"name": "constructor"})

# %%
# P3. Race results.
#  - Join on driverId / constructorId / statusId, never on names.
#  - grid = 0 means the car started from the pit lane -> no grid slot -> NaN.
#  - position is blank for drivers who were not classified -> stays NaN.
#  - Status: "Finished" or "+N Lap(s)" = ran to the flag (a lapped car is NOT a DNF).
#            Anything else (accident, engine, DSQ, withdrew ...) = genuine DNF.
#  - Two different flags, because they overlap:
#      is_classified = has a finishing position (used for grid-vs-finish).
#      is_dnf        = genuine DNF by status (used for reliability).
#    74 rows are both: the car retired late but had covered 90% of the race,
#    so the stewards still gave it a position (e.g. 2023 Australian GP).
LAPPED = re.compile(r"^\+\d+ Laps?$")

results = (raw["results"][lambda d: d["raceId"].isin(RACE_IDS)]
           .merge(raw["status"], on="statusId", how="left", validate="many_to_one")
           .merge(races[["raceId", "year", "round", "race", "race_label", "circuitId",
                         "circuitRef", "circuit", "circuit_short"]], on="raceId", how="left",
                  validate="many_to_one")
           .merge(drivers, on="driverId", how="left", validate="many_to_one")
           .merge(constructors, on="constructorId", how="left", validate="many_to_one"))
results["grid"] = results["grid"].replace(0, np.nan)
results["is_classified"] = results["position"].notna()
results["is_dnf"] = ~(results["status"].eq("Finished") | results["status"].str.match(LAPPED))
results["is_win"] = results["position"].eq(1)
results["is_podium"] = results["position"].le(3)
results["pos_gain"] = results["grid"] - results["position"]   # + = places gained
results = results[[
    "resultId", "raceId", "year", "round", "race", "race_label", "circuitId", "circuitRef",
    "circuit", "circuit_short", "driverId", "driverRef", "code", "driver", "constructorId",
    "constructorRef",
    "constructor", "grid", "position", "positionOrder", "points", "laps", "status",
    "is_classified", "is_dnf", "is_win", "is_podium", "pos_gain", "fastestLap", "rank"]]
assert len(results) == 4219
# Every unclassified driver is a genuine DNF (no "Finished" car lacks a position).
assert results.loc[~results["is_classified"], "is_dnf"].all()
print("unclassified:", (~results["is_classified"]).sum(),
      "| genuine DNF:", results["is_dnf"].sum(),
      "| retired but still classified:", (results["is_dnf"] & results["is_classified"]).sum())

# %%
# P4. Qualifying. Q1/Q2/Q3 are text like "1:26.572" -> seconds (float).
#     A blank Q2/Q3 just means the driver was knocked out earlier.
def to_seconds(t):
    if pd.isna(t) or t == "":
        return np.nan
    m, s = (t.split(":") if ":" in t else ("0", t))
    try:
        return int(m) * 60 + float(s)
    except ValueError:
        return np.nan


qualifying = raw["qualifying"][lambda d: d["raceId"].isin(RACE_IDS)].copy()
for col in ["q1", "q2", "q3"]:
    qualifying[col + "_s"] = qualifying[col].map(to_seconds)
qualifying["best_q_s"] = qualifying[["q1_s", "q2_s", "q3_s"]].min(axis=1)
qualifying = qualifying.rename(columns={"position": "quali_pos"})[
    ["raceId", "driverId", "constructorId", "quali_pos", "q1_s", "q2_s", "q3_s", "best_q_s"]]

# %%
# P5. Pit stops. The text column "duration" switches to "m:ss" for very long
#     (red-flag) stops, so we use the exact "milliseconds" column instead.
#     Duration = total time in the pit lane (entry to exit), not wheel-gun time.
pit_stops = raw["pit_stops"][lambda d: d["raceId"].isin(RACE_IDS)].copy()
pit_stops["duration_s"] = pit_stops["milliseconds"] / 1000
pit_stops = pit_stops[["raceId", "driverId", "stop", "lap", "duration_s"]]
PIT_RACE_IDS = set(pit_stops["raceId"])          # races that have pit data at all

# %%
# P6. Lap times: position of every driver at the end of every lap.
lap_times = raw["lap_times"][lambda d: d["raceId"].isin(RACE_IDS)][
    ["raceId", "driverId", "lap", "position", "milliseconds"]].rename(
    columns={"milliseconds": "lap_ms"})

# %%
# P7. Sprint results (2021-2024 only - the format did not exist earlier).
sprint = raw["sprint_results"][lambda d: d["raceId"].isin(RACE_IDS)].merge(
    raw["status"], on="statusId", how="left")
sprint = sprint[["raceId", "driverId", "constructorId", "grid", "position", "points", "status"]]

# %%
# P8. Standings are cumulative after every race. The season's final table is
#     the one after the LAST round of that season.
last_round = races.loc[races.groupby("year")["round"].idxmax(), ["year", "raceId"]]

driver_final = (raw["driver_standings"].merge(last_round, on="raceId")
                .merge(drivers, on="driverId", how="left")
                [["year", "driverId", "driver", "code", "points", "position", "wins"]])
constructor_final = (raw["constructor_standings"].merge(last_round, on="raceId")
                     .merge(constructors, on="constructorId", how="left")
                     [["year", "constructorId", "constructor", "points", "position", "wins"]])
constructor_final["points_share"] = (constructor_final["points"]
                                     / constructor_final.groupby("year")["points"].transform("sum"))

# %%
# P9. One merged driver-race table: results + qualifying + pit-stop summary.
stop_summary = (pit_stops.groupby(["raceId", "driverId"])
                .agg(n_stops=("stop", "size"), first_stop_lap=("lap", "min"),
                     median_stop_s=("duration_s", "median")).reset_index())
race_level = (results
              .merge(qualifying[["raceId", "driverId", "quali_pos", "best_q_s"]],
                     on=["raceId", "driverId"], how="left", validate="one_to_one")
              .merge(stop_summary, on=["raceId", "driverId"], how="left", validate="one_to_one"))
# A driver with no row in pit_stops made 0 stops - but only in races that have
# pit data. For the one race with no pit data at all we leave it unknown (NaN).
has_pit_data = race_level["raceId"].isin(PIT_RACE_IDS)
race_level.loc[has_pit_data, "n_stops"] = race_level.loc[has_pit_data, "n_stops"].fillna(0)

# %%
# P10. Cross-check against the cleaned workbook from the Primary Review.
expected = {"results": 4219, "qualifying": 4205, "pit_stops": 7544,
            "lap_times": 227123, "sprint": 360, "driver_final": 223, "constructor_final": 101}
actual = {"results": len(results), "qualifying": len(qualifying), "pit_stops": len(pit_stops),
          "lap_times": len(lap_times), "sprint": len(sprint), "driver_final": len(driver_final),
          "constructor_final": len(constructor_final)}
assert actual == expected, (actual, expected)
print("Row counts match the Primary Review workbook:", actual)

# %%
# P11. Save the clean tables.
for name, df in {"races": races, "results": results, "qualifying": qualifying,
                 "pit_stops": pit_stops, "lap_times": lap_times, "sprint": sprint,
                 "driver_final": driver_final, "constructor_final": constructor_final,
                 "race_level": race_level}.items():
    df.to_csv(CLEAN / f"{name}.csv", index=False)
print("Saved clean tables to", CLEAN)
