# UI contract for 012

## Demo page: the Elapsed figure

- `#elapsed` shows `MM:SS` of the value from `S1Clock.valueAt(view.clock, anchor, now)` (data model, "Clock anchor").
- It ticks only while `view.clock.running` and an anchor exists. The one `setInterval` (250 ms divided by the replay speed, 250 ms live) is started when a run is attached and cleared when the run ends or the view resets. It writes `#elapsed` only; it never calls the full render and never touches run state.
- It starts at 00:00 before `run.started`, holds during a human wait, and stops at `run.terminated`.
- Fixed views (`?golden=`, `?run=`) and finished runs never tick.
- `window.__s1.clock` exposes `{ anchor, shownMs }` for the browser tests.

## Demo page: the termination card

- The eyebrow's elapsed part shows `view.clock.workMs` after `run.terminated`, and `view.clock.workAtHandoffMs` while Handoff waits. `summary.elapsed_ms` is no longer read by the card.

## Settings page: seat change

1. The presenter picks a model. The page posts `/api/seats/{seat}` as today.
2. On success the status line reads "Applied: the next run uses <label>. Checking <label>." (or the live-run form, "Applied to the live run: the next dispatch uses <label>. Checking <label>.").
3. The page posts `/api/preflight/recheck` with the model key. On the reply, the status line's second sentence becomes the model row's detail ("<label> answered in 812 ms." or "<label> did not answer (NotFoundError). Pre-flight is red."). The header dot takes `header.status`, `header.glyph`, and `header.title`.
4. If the recheck request itself fails, the second sentence reads "The pre-flight recheck did not run: <error>." The seat change stands.
5. No timer and no polling. A second seat change while a recheck is pending is allowed. Each reply updates the line and the dot in the order the replies arrive, and the last reply wins.

## Pre-flight page

- One row per stored row plus the `family` row, in the order of `GET /api/preflight`, using the existing `check-row` component.
- The page's own dot and title come from `header` in the payload. `preflight.js` no longer works out the title itself.
- The confirmation "All checks pass" shows when `passed == applicable`, as today.
