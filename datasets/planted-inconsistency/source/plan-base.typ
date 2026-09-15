#import "sheet.typ": *

// Main floor, 32 m by 20 m, 640 m². Rooms are shared by E-101 and E-102.
#let plan(heading, notes, body) = {
  text(size: 12pt, weight: "bold")[#heading]
  v(4pt)
  box(width: m(34), height: m(21.5), {
    place(top + left, dx: m(1), dy: m(0.5), box(width: m(32), height: m(20), {
      room(0, 0, 18, 12, "Reading room")
      room(18, 0, 14, 12, "Children's area")
      room(0, 12, 10, 8, "Lobby")
      room(10, 12, 10, 8, "Program room")
      room(20, 12, 7, 8, "Staff workroom")
      room(27, 12, 5, 4, "Electrical room")
      room(27, 16, 5, 4, "Washrooms")
      // Exterior walls drawn heavier.
      at(0, 0, rect(width: m(32), height: m(20), stroke: 3pt + ink))
      // Doors and openings.
      door(1.0, 0)
      door(30.0, 0)
      door(3.5, 20)
      door(4.0, 12)
      door(10, 15.0, horizontal: false)
      door(20, 15.0, horizontal: false)
      door(27, 13.0, horizontal: false)
      door(27, 17.5, horizontal: false)
      door(18, 5.0, horizontal: false)
      at(0.6, -0.9, text(size: 6pt)[REAR EXIT])
      at(29.2, -0.9, text(size: 6pt)[REAR EXIT])
      at(2.6, 20.3, text(size: 6pt)[MAIN ENTRY])
      body
      room-label(7.3, 11.0, "Reading room", 216)
      room-label(22.4, 10.9, "Children's area", 168)
      room-label(3.4, 16.0, "Lobby", 80)
      room-label(12.6, 15.9, "Program room", 80)
      room-label(21.6, 15.9, "Staff workroom", 56)
      room-label(27.3, 12.4, "Electrical room", 20)
      room-label(28.3, 18.9, "Washrooms", 20)
    }))
  })
  v(6pt)
  grid(
    columns: (1fr, 1fr), gutter: 12pt,
    block(notes),
    block(width: m(12), height: m(2.4), {
      scale-bar(0.5, 1.0)
      north-arrow(11.5, 0)
    }),
  )
}
