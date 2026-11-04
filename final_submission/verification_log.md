# Verification log - seed findings recomputed

Arwindh C N | CB.SC.U4CSE24207 | 23CSE353 Data Visualisation

Every "Recomputed" value is produced by `verify_seeds.py` (run after `f1_prep.py`) from the 14 raw CSVs
in `data/raw/`. The same calculations are repeated, cell by cell, in `F1_Story_Notebook.ipynb`.
Rule followed: if a seed does not reproduce, the real number is used and the story changes.

**Result: 25 of 25 checks reproduce.** S6 reproduces only after an undocumented choice is made explicit (drop driver-races with fewer than 10 laps); its sensitivity is reported in the notebook (Cell A4.6).

| ID | Finding | Seed | Recomputed | Match | Note |
|---|---|---|---|---|---|
| D1 | Races in 2015-2024 | 209 | 209 | Yes |  |
| D2 | Median pit-lane time (s) | ~23.7 | 23.73 (stops < 60 s) / 23.98 (all 7,544 stops) | Yes | 23.7 s holds for normal stops. 484 stops of 60 s+ (red flags, repairs) lift the all-stop median to 24.0 s. Raw 'duration' text is m:ss for these, so we use the milliseconds column. |
| S1a | Grid vs finish, pooled Pearson r | ~0.75 | 0.746 (n = 3,518) | Yes | Classified finishers with a real grid slot (pit-lane starts excluded). |
| S1b | Monaco r (highest) | ~0.88 | 0.878 (n = 151, 9 races) | Yes |  |
| S1c | Median circuit r (40+ classified finishes) | ~0.74 | 0.744 across 27 circuits | Yes |  |
| S1d | Lowest circuit r | ~0.52 Hockenheim | 0.524 Hockenheim (n = 50, 3 races) | Yes | Seed doc said 'four appearances'; the data has 3 races (2016, 2018, 2019). Small sample - must be flagged. |
| S2a | First stops usable (lap before, +2, +10 all known) | 3,490 | 3,490 | Yes |  |
| S2e | Undercut, early third: places at +2 laps, then at +10 laps | -4.0 then -1.7 | -4.03 then -1.67 (n = 1,032) | Yes |  |
| S2m | Undercut, middle third: places at +2 laps, then at +10 laps | -3.0 then -1.6 | -2.98 then -1.64 (n = 1,291) | Yes |  |
| S2l | Undercut, late third: places at +2 laps, then at +10 laps | -3.3 then -2.2 | -3.32 then -2.26 (n = 1,167) | Yes | Late +10 is -2.26: rounds to -2.3, seed said -2.2. |
| S2r | Places won back between +2 and +10 laps (early vs late) | 2.4 vs 1.1 | 2.35 vs 1.07 | Yes |  |
| S3a | Corr(qualifying gap, StopDiff) | ~-0.01 | +0.021 (n = 2,085 pairs) | Yes (both ~0) | Sign differs but both are effectively zero: the 'gamble' hypothesis is dead either way. |
| S3b | Slower qualifier beats teammate WITH an extra stop | 12.2% (n = 287) | 12.2% (n = 286) | Yes | 'Both finished' = both classified (have a finishing position). |
| S3c | Slower qualifier beats teammate WITHOUT an extra stop | 34.0% (n = 1,245) | 34.2% (n = 1,236) | Yes | n differs by 9 because we drop 2021 Belgian GP (no pit data, stops unknown). |
| S3d | Two-proportion z | ~-7.3 | -7.31 | Yes |  |
| S3e | Median finishing gap to teammate (extra vs none) | +3 vs +1 | +3 vs +1 | Yes |  |
| S3f | Sensitivity: 'both finished' by status (no late retirements) | - | 11.0% (n = 272) vs 33.7% (n = 1,192), z = -7.41 | n/a | Stricter definition gives the same story. |
| S3s | Bucket small gap (1-3 grid places): with vs without extra stop | 12.7% vs 41.2% | 12.8% (n = 172) vs 41.3% (n = 823) | Yes | Seed bucket edges were not documented; 1-3 / 4-7 / 8+ places reproduces them. |
| S3m | Bucket medium gap (4-7 grid places): with vs without extra stop | 11.8% vs 23.1% | 11.8% (n = 68) vs 23.4% (n = 269) | Yes |  |
| S3l | Bucket large gap (8+ grid places): with vs without extra stop | 10.9% vs 13.6% | 10.9% (n = 46) vs 13.9% (n = 144) | Yes | Large-gap bucket: only a 3-point difference and just 46 extra-stop pairs - direction holds, strength does not. |
| S4a | Mercedes points share 2015 -> 2023 | 36.6% -> 16.6% | 36.6% -> 16.6% | Yes |  |
| S4b | Red Bull points share 2015 -> 2023 | 9.7% -> 35.0% | 9.7% -> 35.0% | Yes |  |
| S4c | McLaren points share 2015 -> 2024 | 1.4% -> 25.0% | 1.4% -> 25.0% | Yes |  |
| S5a | Genuine DNF rate 2015 -> 2024 | 21.4% -> 11.3% | 21.4% -> 11.3% | Yes | Not a smooth fall: 2017 = 23.8%, 2022 = 16.8%. |
| S5b | Lowest genuine DNF rate (team, 60+ starts) | Mercedes ~7.4% | Mercedes 7.4% (418 starts) | Yes |  |
| S6 | Lap-time variability (CV) vs season points | r ~ -0.18 (n = 201) | r = -0.184 (n = 201) | Yes | Reproduces only if driver-races with < 10 laps are dropped (the seed did not say). Keeping them: r = -0.162 (n = 202); median race instead of mean: r = -0.400. Weak AND fragile - reported as such. |

## Definitions used
- **Classified** = has a finishing position. **Genuine DNF** = status is anything other than "Finished" or "+N Lap(s)".
  74 cars are both (retired late but still classified).
- **Pit-lane start** (grid = 0) is treated as missing grid.
- **Undercut**: first stops only; position on lap L-1, L+2, L+10; thirds = within-race percentile rank of the first-stop lap.
- **Teammate pair**: same constructor, same race, both with a qualifying position, race has pit data. Slower qualifier =
  worse qualifying position. StopDiff = stops(slower) - stops(faster). "Extra stop" = StopDiff > 0.
- **Points share** = team's final championship points / all teams' final points that season (last round of season).
