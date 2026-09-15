#import "sheet.typ": *
#import "plan-base.typ": plan

#show: sheet.with(number: "E-102", title: "Power Plan, Main Floor", scale: "Graphic scale shown")

#plan("POWER PLAN, MAIN FLOOR", [
  #text(weight: "bold")[SHEET NOTES]
  + Device descriptions are on the materials schedule, sheet E-000. Receptacles are mounted 400 mm above finished floor unless noted.
  + Circuit tags name the panel and circuit. All receptacle circuits are on panel LP-1, sheet E-002.
  + Transformer T1 and panel LP-1 are in the electrical room. Feeder F1 arrives from the existing main distribution MDP in the base building service room, outside the fit-out area. See single-line diagram E-001.
], {
  // Reading room: 10 receptacles. LP-1-2: west and north walls (5). LP-1-4: south and east walls (5).
  receptacle(0.8, 2.0)
  receptacle(0.8, 5.0)
  receptacle(0.8, 8.0)
  receptacle(5.0, 0.8)
  receptacle(9.0, 0.8)
  tag(1.4, 4.8, "LP-1-2")
  receptacle(3.0, 11.1)
  receptacle(7.0, 11.1)
  receptacle(11.0, 11.1)
  receptacle(15.0, 11.1)
  receptacle(17.2, 7.5)
  tag(11.6, 10.0, "LP-1-4")
  // Children's area: 6 receptacles, LP-1-6.
  receptacle(22.0, 0.8)
  receptacle(26.0, 0.8)
  receptacle(31.2, 4.0)
  receptacle(31.2, 8.0)
  receptacle(20.0, 11.1)
  receptacle(29.0, 11.1)
  tag(22.6, 1.3, "LP-1-6")
  // Lobby: 2 and program room: 4, LP-1-8.
  receptacle(0.8, 14.5)
  receptacle(0.8, 18.0)
  tag(1.4, 17.8, "LP-1-8")
  receptacle(13.0, 12.9)
  receptacle(17.0, 12.9)
  receptacle(13.0, 19.1)
  receptacle(17.0, 19.1)
  tag(13.6, 18.1, "LP-1-8")
  // Staff workroom: 6 receptacles, LP-1-10.
  receptacle(21.5, 12.9)
  receptacle(25.5, 12.9)
  receptacle(21.5, 19.1)
  receptacle(25.5, 19.1)
  receptacle(20.8, 17.0)
  receptacle(26.2, 17.0)
  tag(22.1, 18.1, "LP-1-10")
  // Electrical room: 1 and washrooms: 1, LP-1-12.
  receptacle(27.8, 15.5)
  receptacle(31.2, 17.2)
  tag(28.3, 15.3, "LP-1-12")
  tag(29.0, 17.0, "LP-1-12")
  // Transformer T1 and panel LP-1.
  at(29.3, 14.2, box(width: m(1.5), height: m(1.1), stroke: 1.2pt + ink, fill: rgb("#e8e8e8"),
    align(center + horizon, text(size: 6.5pt, weight: "bold")[T1])))
  at(31.35, 13.5, box(width: m(0.5), height: m(2.2), stroke: 1.2pt + ink, fill: ink))
  at(30.35, 13.45, text(size: 6.5pt, weight: "bold")[LP-1])
  // Feeder F1 from the existing MDP.
  at(32.0, 12.9, line(start: (0pt, 0pt), end: (m(1.6), 0pt), stroke: (paint: ink, thickness: 1.2pt, dash: "dashed")))
  at(32.2, 11.9, text(size: 6pt, weight: "bold")[F1 FROM MDP])
})
