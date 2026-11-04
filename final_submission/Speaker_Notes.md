# Speaker notes · F1_Review_Presentation.pptx

F1 BASICS = the F1 idea to explain first. WHAT = what the slide shows. WHY = why it matters.
Read them aloud in that order while pointing at the chart.

## Slide 1: Formula 1, read as a chain of cause and effect

**F1 BASICS:** Formula 1, or F1, is the top level of car racing. About twenty cars race around a track for many laps, and the first car to cross the finish line wins.
**WHAT:** My project looks at 10 years of Formula 1 races: 209 races from 2015 to 2024.
**WHY:** Most people only see who won. I want to show why they won. A race is a chain of cause and effect.

## Slide 2: Why do races end the way they do? Six questions, one story

**F1 BASICS:** A season has around twenty races in different countries. Each race is called a Grand Prix. Drivers and teams collect points in every race to win the championship.
**WHAT:** A race result depends on many things: the car, the driver, the starting position, pit stops and the track.
**WHY:** A results table only shows who won, not why. So in my Primary Review I set six questions, O1 to O6. Each part of my story answers one of them.

## Slide 3: Ten seasons, 209 races, every car on every lap

**F1 BASICS:** In F1, a team is called a constructor. Each team builds its own car and runs two cars. The two drivers in the same team are called teammates, and they drive the same car.
**WHAT:** I used the Ergast F1 dataset: 14 linked tables. I kept 2015 to 2024: 209 races, 53 drivers and 18 teams.
**WHY:** The lap table is the most important one. It shows where every car was on every lap, so I can follow a race move by move.

## Slide 4: Fourteen raw tables cleaned into one driver-race dataset

**F1 BASICS:** The grid is the starting order of the race. DNF means 'did not finish': the car crashed or broke down. A car that finishes one lap behind the leader still finished, so it is not a DNF.
**WHAT:** I cleaned the data in 5 steps: read the files, kept 2015 to 2024, joined the tables using ID numbers, fixed wrong codes, and merged everything into one table.
**WHY:** Without cleaning, the numbers would be wrong. For example, a car that finished one lap behind is not a retirement. My row counts match my Primary Review workbook.

## Slide 5: Three tools, each doing the job it does best

**F1 BASICS:** A lap is one full trip around the track. A car's position is its place in the race order: first, second, third and so on. My charts follow these positions lap by lap.
**WHAT:** I used three tools. Matplotlib for detailed story charts. Seaborn for statistics. Plotly for interactive charts and the dashboard.
**WHY:** Each tool does one job best. I also avoided basic bar and pie charts. Plotly replaced Power BI so the whole analysis stays reproducible in a single notebook.

## Slide 6: 844 position changes in one race, and the pole-sitter still won

**F1 BASICS:** Pole position means starting first. A pit stop is when a car drives into a side lane, called the pit lane, to change its tyres. It costs time, so the car usually loses a few places.
**WHAT:** Each line is one car, showing its position on every lap. Dots are pit stops. This race had 844 position changes, the most of all 209 races.
**WHY:** Hamilton, in red, started 22nd, made 5 stops and finished 7th. Rosberg, in black, started first and won. A race is a story of moves, not just a result.

## Slide 7: Saturday decides more than you think: Monaco locks the order in

**F1 BASICS:** Qualifying happens on Saturday. Each driver tries one very fast lap, and the fastest driver starts at the front on Sunday. Overtaking means passing another car on the track.
**WHAT:** These charts compare where drivers start and where they finish. The link score is 0.75 out of 1, which is strong. Pole position won 53% of all races.
**WHY:** The link changes by track. Monaco is 0.88 because its streets are too narrow to overtake. So at Monaco, Saturday's qualifying decides the race.

## Slide 8: Early stoppers lose 4 places, then win back 2.4 of them

**F1 BASICS:** Tyres wear out during a race, so every car must stop at least once to change them. A stop costs around 23.7 seconds. The undercut means stopping before your rival, so your new tyres make you faster while the rival is still on old tyres.
**WHAT:** This chart shows a driver's position before and after the first pit stop. Early stoppers drop about 4.0 places, then win back 2.4.
**WHY:** Late stoppers win back only 1.1. So stopping first pays off: that is the undercut working.

## Slide 9: The myth is dead, the alarm is real: an extra stop means trouble

**F1 BASICS:** Teammates drive the same car, so comparing them is fair. An extra pit stop means stopping one more time than the teammate, often because of damage, a flat tyre or a crash.
**WHAT:** I compared teammates, because they drive the same car. People think a driver who is far behind gambles on extra pit stops. The left chart shows no link at all.
**WHY:** The right chart shows the truth. With an extra stop, a driver beats the teammate only 12% of the time, not 34%. An extra stop is a warning sign that something went wrong, not a plan.

## Slide 10: The car sets the ceiling: three eras in ten seasons

**F1 BASICS:** Each team builds its own car, so some cars are simply faster. The top ten cars in each race get points. The team with the most points in a year wins the constructors' championship.
**WHAT:** These charts show each team's share of all points, and how often cars broke down. Mercedes led first, then Red Bull, then McLaren. Breakdowns fell from 21.4% to 11.3%.
**WHY:** The car matters most. Good strategy can only help within the limit the car sets.

## Slide 11: Wins follow the car, and the driver matters more than the track

**F1 BASICS:** Every year there are two championships: one for drivers and one for teams. A driver in the fastest car usually wins the most races.
**WHAT:** Left: 67% of all race wins went to the best team of that season. Right: drivers stay at the same level at almost every track.
**WHY:** The car and the driver matter more than the track. Steady lap times barely help, and I show that honestly.

## Slide 12: One interactive page: four filters, five acts, every chart linked

**F1 BASICS:** A season is one year of races. A circuit is the track where a race happens, and every circuit is different: some are fast and wide, some are slow and narrow.
**WHAT:** This is my interactive dashboard, made with Plotly. You can filter by season, team, driver and track, and every chart updates.
**WHY:** Anyone can explore the data and ask their own questions without writing code. It is one file and works offline.

## Slide 13: Filter to Monaco and the story sharpens: r rises from 0.75 to 0.88

**F1 BASICS:** Monaco is a tiny country in the south of France. Its race runs through narrow city streets with walls on both sides, so overtaking is almost impossible.
**WHAT:** Here I set the filter to Monaco. The start-to-finish link rises from 0.75 to 0.88. The 2024 Monaco race had only 30 position changes.
**WHY:** At street tracks the race is mostly decided on Saturday. So a team should focus on qualifying there.

## Slide 14: Same numbers, two stories: a cut axis turns a 2.1% gap into a bar 3.0× taller

**F1 BASICS:** The constructors' championship adds up all the points a team scores in a year. In 2024, McLaren and Ferrari finished very close to each other.
**WHAT:** Both charts use the same real numbers: McLaren 666, Ferrari 652. The left chart starts its axis at 645, so McLaren's bar looks 3.0 times taller.
**WHY:** The real gap is only 2.1%. Cutting the axis tricks the eye. The honest chart starts at zero, and so do all my bar charts.

## Slide 15: Two expectations were overturned: extra stops and circuit specialists

**F1 BASICS:** Strategy is the team's plan during the race, mainly when to make pit stops. Reliability means how often a car finishes without breaking down.
**WHAT:** This table answers my six questions from the Primary Review.
**WHY:** Most results matched what I expected. Two did not: an extra pit stop is a warning sign, not a gamble, and the driver matters more than the track.

## Slide 16: The 844 position changes were a chain of cause and effect

**F1 BASICS:** The strategist sits on the pit wall, the team's control desk next to the track. This person decides when each car stops and how to react during the race.
**WHAT:** My four tips for a team: focus on qualifying at tracks like Monaco, stop early when you can, treat an extra stop as a warning, and plan around the car.
**WHY:** The 844 position changes in my first race were not random. They were cause and effect. One limit: my data shows links, not proof. Thank you.
