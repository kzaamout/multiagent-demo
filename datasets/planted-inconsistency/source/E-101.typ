#import "sheet.typ": *
#import "plan-base.typ": plan

#show: sheet.with(number: "E-101", title: "Lighting Plan, Main Floor", scale: "Graphic scale shown")

#plan("LIGHTING PLAN, MAIN FLOOR", [
  #text(weight: "bold")[SHEET NOTES]
  + Fixture types and descriptions are on the materials schedule, sheet E-000.
  + Circuit tags name the panel and circuit, for example LP-1-1. All lighting circuits are on panel LP-1, sheet E-002.
  + Exit signs and emergency battery units are on circuit LP-1-9, ahead of any local switch.
  + Switches control the lighting of the room they are in.
], {
  // Reading room: 16 troffers, circuit LP-1-1.
  for x in (2.5, 6.8, 11.2, 15.5) { for y in (2.0, 4.7, 7.4, 10.1) { troffer(x, y) } }
  tag(1.7, 2.5, "LP-1-1")
  // Children's area: 12 troffers, circuit LP-1-3.
  for x in (20.0, 23.5, 27.0, 30.5) { for y in (2.5, 5.8, 9.1) { troffer(x, y) } }
  tag(19.2, 3.0, "LP-1-3")
  // Lobby: 4 troffers and program room: 6 troffers, circuit LP-1-5.
  for x in (2.5, 7.0) { for y in (14.2, 18.2) { troffer(x, y) } }
  tag(1.7, 14.7, "LP-1-5")
  for x in (12.0, 15.0, 18.0) { for y in (14.3, 18.5) { troffer(x, y) } }
  tag(11.2, 14.8, "LP-1-5")
  // Staff workroom: 4, electrical room: 1, washrooms: 2, circuit LP-1-7.
  for x in (22.0, 25.0) { for y in (14.3, 18.5) { troffer(x, y) } }
  tag(21.2, 14.8, "LP-1-7")
  troffer(29.5, 14.6)
  tag(28.7, 15.1, "LP-1-7")
  troffer(28.7, 17.6)
  troffer(30.9, 17.6)
  tag(28.0, 18.2, "LP-1-7")
  // Exit signs: 4. Emergency battery units: 3. Circuit LP-1-9.
  exit-sign(1.5, 0.8)
  exit-sign(30.5, 0.8)
  exit-sign(4.0, 19.2)
  exit-sign(8.3, 12.8)
  tag(2.3, 0.6, "LP-1-9")
  tag(28.6, 0.6, "LP-1-9")
  tag(4.9, 19.0, "LP-1-9")
  tag(9.1, 12.6, "LP-1-9")
  ebu(9.0, 0.9)
  ebu(25.0, 0.9)
  ebu(1.3, 13.2)
  tag(9.7, 0.7, "LP-1-9")
  tag(25.7, 0.7, "LP-1-9")
  tag(2.0, 13.0, "LP-1-9")
  // Switches: 9.
  switch(0.6, 11.2)
  switch(17.4, 11.2)
  switch(18.6, 11.2)
  switch(31.4, 1.6)
  switch(0.6, 19.3)
  switch(10.6, 19.3)
  switch(20.6, 19.3)
  switch(27.6, 15.3)
  switch(27.6, 19.3)
})
