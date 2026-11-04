# Viva cheat sheet

Arwindh C N · CB.SC.U4CSE24207 · 23CSE353 Data Visualisation

Twenty likely questions with short answers. **Proof** names the notebook cell (F1_Story_Notebook.ipynb) that computes each number; cell labels are printed in the cell output and in every chart footer.

**1. What is your project, in one sentence?**

Ten seasons of F1 data (209 races, 2015–2024) told as one story in five acts, so the reader sees a race as a chain of cause and effect: Saturday sets the order, pit stops trade places, an extra stop is an alarm, and the car sets the ceiling.

*Proof: Title cell; H.1–C.1*

**2. What data did you use, and how did you clean it?**

The 14 Ergast-lineage CSVs, filtered to 2015–2024: 4,219 race entries, 7,544 pit stops, 227,123 lap times. \N → missing; grid 0 (pit-lane start) → missing; Q times → seconds; pit time from the milliseconds column; joins on IDs only; final standings = last round. Every row count is asserted equal to the Primary Review workbook.

*Proof: Cell P.1–P.12*

**3. Why rebuild from the raw CSVs instead of your Excel workbook?**

The workbook's constructor sheet has names but no constructor ID, and joining on names is unsafe (Toro Rosso → AlphaTauri → RB have different IDs). The rebuild matches every workbook row count.

*Proof: Cell P.10*

**4. What is a genuine DNF, and why is "+1 Lap" not one?**

A genuine DNF is any status other than "Finished" or "+N Lap(s)". A lapped car still finished. 715 genuine DNFs vs 641 unclassified: the 74 difference are cars that retired late but covered 90% of the race, so they kept a position. Hence two flags.

*Proof: Cell P.3, P.12*

**5. Why the 2016 Chinese GP as the hook?**

Chosen by a rule: sum of places gained or lost lap to lap. It ranks first of 209 races (844; the median race has 275), it has 0 DNFs so every line is complete, and every act appears in it.

*Proof: Cell H.1, H.2*

**6. How strongly does the grid predict the finish?**

Pooled r = 0.75 over 3,518 classified finishes. Pole won 53% of races; 88% of winners started top three.

*Proof: Cell A1.1*

**7. Why is Monaco top, and why not trust Hockenheim's rank?**

Monaco r = 0.88: a narrow street circuit, overtaking almost impossible. Hockenheim r = 0.52 but only 3 races (50 finishes); its 95% range is 0.29–0.70. Median circuit r = 0.74 (27 circuits with 40+ finishes).

*Proof: Cell A1.2*

**8. How did you measure the undercut?**

First stops only. Position on lap L−1, L+2, L+10 from lap_times; thirds of each race's first-stop laps. Early -4.0 then -1.7 (wins back 2.4); late -3.3 then -2.3 (wins back 1.1). n = 3,490. Robust when stops in laps 1–5 are dropped.

*Proof: Cell A2.1–A2.3*

**9. What is the derived teammate link and StopDiff?**

Two drivers, same constructor, same race, both with a qualifying position (2,085 pairs). The one who qualified behind is the slower qualifier. StopDiff = his stops − the faster teammate's stops. It chains Qualifying, Pit Stops and Results.

*Proof: Cell A3.1*

**10. What assumption did you test in Act 3?**

"A driver far behind the teammate gambles on extra stops." Correlation of qualifying gap with StopDiff: r = +0.02 (p = 0.34). No link, so the assumption is dead.

*Proof: Cell A3.3*

**11. What is the main Act 3 finding?**

With an extra stop the slower qualifier beats the teammate 12.2% of the time (n = 286); without, 34.2% (n = 1,236); z = -7.3. Median finishing gap +3 vs +1.

*Proof: Cell A3.4*

**12. Is the extra stop the cause of the lost result?**

No. It is a symptom of trouble (damage, puncture, spin, bad safety-car timing). Evidence: whoever makes the extra stop loses (slower qualifier wins 64% when the teammate made it), and 27% of extra-stop drivers first stopped in laps 1–3 vs 9%. It is a correlation, used as a warning light, not a lever.

*Proof: Cell A3.5*

**13. Does the Act 3 result hold for every qualifying gap?**

Direction yes: small 13% vs 41%, medium 12% vs 23%, large 11% vs 14%. But the large bucket has only 46 extra-stop pairs and p = 0.6: not significant there.

*Proof: Cell A3.4*

**14. What does "the car sets the ceiling" mean in numbers?**

Mercedes 36.6% of points (2015) → 16.6% (2023); Red Bull 9.7% → 35.0%; McLaren 1.4% → 25.0%. Biggest three-season swing: Ferrari fell 18 points (2017–2020). 67% of wins went to the season's champion team.

*Proof: Cell A4.1, A4.3*

**15. How has reliability changed?**

Genuine DNF rate 21.4% (2015) → 11.3% (2024), with rises in 2017 (23.8%) and 2022 (16.8%), both new-rules years. Best team: Mercedes 7.4%.

*Proof: Cell A4.2*

**16. Driver or circuit: which matters more?**

Driver (with car). In the heatmap, driver rows differ by 4.6 places, circuit columns by 1.7.

*Proof: Cell A4.5*

**17. Did any earlier finding fail to reproduce?**

25 of 25 checks reproduce, three only after a choice was made explicit. Consistency vs points gives r = -0.18 only if driver-races under 10 laps are dropped; keeping them gives -0.16; median race gives -0.40; per-race filter +0.03. Weak and fragile, reported as such. Also, Hockenheim has 3 races in the data, not 4 as the old document said.

*Proof: Cell A4.6; verification_log.md*

**18. Why three tools, and why not Power BI?**

Matplotlib: precise hand-annotated story charts and exact axis control. Seaborn: statistics with bootstrap confidence ranges. Plotly: interactivity and the dashboard. Plotly replaced Power BI so the whole analysis stays reproducible in a single notebook.

*Proof: Cell S.1, A4.1, D.1*

**19. Explain your misleading chart.**

2024 constructor points, McLaren 666 vs Ferrari 652. Y-axis cut at 645 makes the bar 3.0× taller for a 2.1% gap. False impression: "crushed"; reality: the closest title of the decade. Fix: axis from 0. Principle: truthful scaling / proportional ink; lie factor ≈ 93.

*Proof: Cell A5.1–A5.3*

**20. How do you know the numbers in the report and slides match the notebook?**

The notebook records every number with fact() and saves facts.json with the producing cell. Markdown, report, slides and this sheet are generated from that file. make_notebook.sh runs the notebook twice from a fresh kernel and checks facts.json is identical. Limits remain: correlation is not causation, and there is no tyre, weather or safety-car data.

*Proof: Cell F.1; make_notebook.sh*
