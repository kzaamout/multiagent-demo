# Feature Specification: Demo-day readiness (slice S7)

**Feature Branch**: `008-demo-day-readiness`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "Slice S7, Demo-day readiness, exactly as written in docs/roadmap.md "S7. Demo-day readiness", with docs/spec-input.md 0.7 sections 2.2 header, 2.4 Pre-flight, 2.8 Access, 2.9 Hosting and run modes, 8 leave-behind, 9 M6, 10 criteria 9 and 10, 11 subdomain and avatars, and design brief section 10. Owner decisions 2026-09-17: the ten defaults, listed under Assumptions. The leave-behind command waits for S6. Work happens in the worktree on the existing branch 008-demo-day-readiness."

**Governing documents**: `docs/spec-input.md` 0.7 (2.2, 2.4, 2.8, 2.9, 8, 9 M6, 10, 11), `.specify/memory/constitution.md` 1.2.0 (VIII, XV, XVII, and the non-goals on per-user accounts, credentials from the UI, and AgentCore for the demo), `docs/roadmap.md` S7 entry, `docs/design-brief.md` 10, `design/README.md` (pre-flight indicator with three states, Login as a POST, pre-flight states pending, one-fail, all-pass), `specs/007-introduction-replay/contracts/introduction.md` (the routes S7 must keep public).

## Purpose of the slice

Before every meeting the presenter opens one page, presses one button, and sees green. If something is wrong the page says what, in one line, before the prospect is in the room. The same result colours the dot in every header so the presenter never has to remember whether the checks were run. The app answers at the Sterling AI subdomain through a tunnel from the presenter laptop, behind one shared login, while the Introduction page stays public for anyone the sales team sends the link to. A configuration switch says whether the app runs on the laptop with local models or on a cloud host with cloud models only.

The peer slice S6 (Introduction tab and public replay) is built in parallel on `007-introduction-replay`; the Introduction page, its PDF, and the public run routes are out of scope here, and the login guard keeps them public by the list in that slice's contract. The leave-behind command needs S6's Introduction PDF and is deferred until S6 lands. Illustrated avatars have not been delivered, so the initials stay.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pre-flight goes green and every header shows it (Priority: P1)

The presenter opens Pre-flight and presses Run pre-flight. Each row turns green with one line of detail, or red with one line saying what failed. When every applicable check passes, a large confirmation reads "All checks pass" with the run mode, the count, and the time. The result is stored, so reopening the page or restarting the server shows the last result, and the dot beside Pre-flight in every header is green when all checks passed, orange when only a non-essential check failed, red when an essential check failed, and grey when no result exists. The checks are: each cloud provider a seat uses answers a minimal model call; Ollama is reachable and every local seat model is present; Typst compiles a fixture document; the same compile exports page images; the tunnel hostname answers from outside; disk space; and `.env` completeness for the run mode.

**Why this priority**: Acceptance criterion 9 in spec section 10 and the roadmap outcome. It is the demo-day safety net (constitution VIII).

**Independent Test**: With injected check functions, run the pre-flight and assert the stored result, the page rows, the confirmation, and the header dot on Demo, Settings, and Pre-flight for all-pass, one non-essential fail (warn), one essential fail (fail), and no result (pending). The screenshot comparison passes for the pending, all-pass, and one-fail states against the export references.

**Acceptance Scenarios**:

1. **Given** no pre-flight has been run, **When** any protected page loads, **Then** the header dot is grey with "Pre-flight: not run yet" and the Pre-flight page shows eight pending rows and no confirmation.
2. **Given** every check passes, **When** the presenter presses Run pre-flight, **Then** every row is green with its detail line, the confirmation reads "All checks pass" with "Laptop mode · 8 of 8 · <date, time>", `runs/preflight.json` holds the result, and every header dot is green.
3. **Given** the tunnel hostname does not answer and everything else passes, **When** the pre-flight runs, **Then** the tunnel row is red with "Tunnel not connected", no confirmation is shown, and the header dot is orange with a title naming the failed non-essential check.
4. **Given** a cloud provider a seat uses refuses the call, **When** the pre-flight runs, **Then** that row is red with a one-line reason that never contains a credential value, and the header dot is red.
5. **Given** a stored result, **When** the server restarts and the page loads, **Then** the rows, the confirmation, and the dot render from the stored result without running anything.
6. **Given** a check cannot apply in the current mode (the tunnel with no hostname set, Ollama in Cloud mode), **When** the pre-flight runs, **Then** the row stays grey with a line saying why, counts as neither pass nor fail, and the confirmation counts only applicable checks.

---

### User Story 2 - One shared login guards the three working pages (Priority: P1)

A visitor who opens Demo, Settings, or Pre-flight without signing in is sent to the login page. They sign in with the shared username and password from `.env` and land on the page they asked for. The Introduction page, its PDF, the public replay routes, and the static assets need no login. The API routes behind the working pages refuse without the session. There is no account, no reset, no lockout: one pair of credentials in `.env`, nothing entered through the UI beyond the sign-in form.

**Why this priority**: Spec 2.8 and the roadmap evidence; without it the tunnel would expose the composer, the seat swap, and the chat endpoint to anyone with the link.

**Independent Test**: With login credentials set, unauthenticated requests to the three pages redirect to the login page and API calls answer 401; the public routes in the S6 contract answer without a session; a wrong password re-renders the login page with one line; the right one sets a session and the three pages answer. With no credentials in `.env`, nothing redirects, and the pre-flight `.env completeness` check fails on the missing login.

**Acceptance Scenarios**:

1. **Given** credentials in `.env` and no session, **When** the browser requests `/demo`, `/settings`, or `/preflight`, **Then** it is redirected to `/login` and, after signing in, returned to the page it asked for.
2. **Given** no session, **When** the browser requests `/introduction`, `/introduction.pdf`, a `/public/run/...` route, `/static/...`, or `/demo?public=1&run=<pinned id>`, **Then** the login guard does not intervene.
3. **Given** no session, **When** a client calls any other API route, **Then** it receives 401 with `{ "error": "sign in required" }`.
4. **Given** the wrong username or password, **When** the form is submitted, **Then** the login page renders again with the line "Wrong username or password." and no session is set.
5. **Given** a session, **When** the server restarts, **Then** the session is gone and the next page load asks for the login again.
6. **Given** `.env` has no `DEMO_USERNAME` or `DEMO_PASSWORD`, **When** any page loads, **Then** it is served without a login, and the pre-flight `.env completeness` row is red naming the missing names.

---

### User Story 3 - Laptop and Cloud mode (Priority: P2)

The presenter sets `RUN_MODE=laptop` (default) or `RUN_MODE=cloud` in `.env`. In Cloud mode the local models are greyed in Settings and in the composer's model list with the note "not offered in Cloud mode", a seat left on a local model blocks a live run with that reason, and the pre-flight Ollama row says local models are not used. In Laptop mode nothing changes from today. The pre-flight confirmation and `/api/meta` name the mode.

**Why this priority**: Spec 2.9; needed for the always-on cloud host, but the laptop is the demo-day path.

**Independent Test**: Build the app with `run_mode="cloud"` and assert the seat table greys every Ollama entry with the note, a live run on a local seat is refused with that reason, and the pre-flight Ollama row is not applicable; build with `run_mode="laptop"` and assert nothing is greyed for that reason.

**Acceptance Scenarios**:

1. **Given** Cloud mode, **When** Settings loads, **Then** every local model is greyed with "not offered in Cloud mode" and cannot be chosen.
2. **Given** Cloud mode and the Pricing seat still on a local model, **When** Run is pressed, **Then** the run is refused with a line naming the seat and the reason.
3. **Given** Laptop mode, **When** Settings loads, **Then** local models are listed as detected or not detected at startup, as in S5.
4. **Given** an unknown `RUN_MODE` value, **When** the server starts, **Then** it stops with a one-line error naming the two accepted values.

---

### User Story 4 - Tunnel configuration and its check (Priority: P2)

The presenter installs cloudflared, puts the tunnel token and the public hostname in `.env`, and starts the tunnel with one script. The pre-flight tunnel check fetches the login page through the public hostname and reports the answer time; with no hostname configured the check is not applicable. The hostname and the tunnel target are placeholders until the owner supplies them.

**Why this priority**: The roadmap outcome names the subdomain; the values are still open items, so the slice ships the configuration and the check with placeholders.

**Independent Test**: With an injected fetch, the tunnel check passes on a 200, fails with "Tunnel not connected" on a connection error, fails with the HTTP status on any other code, and is not applicable with no hostname. The dependency record has a cloudflared entry with a verified version.

**Acceptance Scenarios**:

1. **Given** `TUNNEL_HOSTNAME` set and the tunnel running, **When** the pre-flight runs, **Then** the tunnel row is green with "<hostname> answered in <n> ms".
2. **Given** `TUNNEL_HOSTNAME` set and the tunnel down, **When** the pre-flight runs, **Then** the row is red with "Tunnel not connected" and the header dot is orange, not red.
3. **Given** no `TUNNEL_HOSTNAME`, **When** the pre-flight runs, **Then** the row is grey with "No tunnel hostname in .env" and counts as neither pass nor fail.
4. **Given** the token in `.env`, **When** the presenter runs the tunnel script, **Then** cloudflared starts with that token and the token never appears in a tracked file or in the page.

---

### User Story 5 - Build stamp verified (Priority: P3)

Every header carries the short git hash and commit date of the running checkout. A test confirms the stamp on every page matches git.

**Why this priority**: Already built in S1; S7 verifies it, as the roadmap scope says.

**Independent Test**: Request each page and `/api/meta`, and compare the stamp with `git rev-parse --short HEAD` and `git log -1 --format=%cs`.

**Acceptance Scenarios**:

1. **Given** the server running from a git checkout, **When** any page loads, **Then** its header stamp reads "build <hash> · <date>" for the current commit.

---

### Edge Cases

- A check hangs: every check has its own timeout and reports "no answer within <n> s" rather than holding the page.
- Run pre-flight pressed twice: the second press while one runs is refused with 409 and the button stays disabled until the result arrives.
- The stored result file is unreadable or from an older shape: treated as no result (pending), never as a pass.
- A provider answers with an error mentioning a key: the detail line is the error's class name and status, never its message text.
- A seat is swapped in Settings after a pre-flight: the stored result stays; the presenter runs it again. No inference.
- `next` on the login form points off-site: ignored, the presenter lands on Demo.
- Cloud mode on a host with Ollama installed: local models stay greyed; the mode decides, not detection.
- Disk space cannot be read: the row fails with "could not read free space" and is essential.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The pre-flight MUST run these checks and report each as pass, fail, or not applicable with one line of detail: one row per cloud provider a seat uses (or whose key is present), the Ollama row, Typst test compile, page PNG export, tunnel reachability, disk space, `.env` completeness.
- **FR-002**: A cloud provider check MUST make one minimal model call through the seat's configured model and report the model and the answer time; it MUST never include a credential value in its detail.
- **FR-003**: Each check MUST be classed essential or non-essential: essential are the providers a seat uses, Ollama when a seat uses it, Typst compile, PNG export, disk space, and `.env` completeness; non-essential are the tunnel and a provider with a key but no seat.
- **FR-004**: The overall status MUST be pass when every applicable check passes, warn when only non-essential checks failed, fail when an essential check failed, and pending when no result exists.
- **FR-005**: The result MUST be stored under the runs folder as `preflight.json` and MUST drive the header dot on every protected page and the `preflight` field of `/api/meta` on every request, with no timer and no inference.
- **FR-006**: The Pre-flight page MUST render the rows, the confirmation, and its own dot from the stored result and from the result a run returns, following the export's three states.
- **FR-007**: The disk check MUST fail under 5 GB free on the drive holding the runs folder.
- **FR-008**: The `.env` completeness check MUST list the names missing for the run mode: the login pair, and the credentials of every cloud provider a seat uses.
- **FR-009**: The shared login MUST be enabled when `DEMO_USERNAME` and `DEMO_PASSWORD` are set in `.env`, compared in constant time, and MUST guard every route except the public list: `/login`, `/static/...`, `/introduction`, `/introduction.pdf`, `/public/...`, and `/demo` with `public=1` for the pinned run only.
- **FR-010**: Page requests without a session MUST redirect to `/login` with the requested path; API requests without a session MUST answer 401 with `{ "error": "sign in required" }`.
- **FR-011**: A session MUST live in server memory and end on restart; the cookie MUST be HttpOnly and SameSite Lax; no account, reset, lockout, or per-user state exists.
- **FR-012**: `RUN_MODE` MUST accept `laptop` (default) or `cloud`; in Cloud mode every Ollama model MUST be greyed with "not offered in Cloud mode" in Settings and the composer, a seat on one MUST refuse a live run with that reason, and the pre-flight Ollama row MUST be not applicable.
- **FR-013**: The tunnel MUST be configured from `.env` (`CLOUDFLARE_TUNNEL_TOKEN`, `TUNNEL_HOSTNAME`), started by one script per platform, and recorded in `docs/dependencies.md` with a verified cloudflared version.
- **FR-014**: The build stamp MUST be verified by a test against git on every page.
- **FR-015**: No em dash may appear in any new copy, detail line, or file.
- **FR-016**: Machine identifiers (check ids, `runs/preflight.json` field names, route paths) MUST stay stable once shipped; display copy may change.

### Key Entities

- **Check**: id, name, essential flag, the function that runs it; eight in the fixed order of the export.
- **CheckResult**: id, name, status (pass, fail, skip), detail, essential, elapsed.
- **PreflightResult**: run mode, time, overall status, counts, the list of CheckResults; stored as `runs/preflight.json`.
- **Session**: a random token in server memory with its creation time; carried in a cookie.
- **RunMode**: `laptop` or `cloud`, read once from `.env`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the presenter laptop in Laptop mode with the tunnel running, Run pre-flight ends green within 60 s, and every header dot is green (criterion 9).
- **SC-002**: Unauthenticated requests reach the Introduction routes and are refused on Demo, Settings, and Pre-flight, proven by a test (roadmap evidence).
- **SC-003**: The screenshot comparison passes for `login`, `preflight-pending`, `preflight-all-pass`, and `preflight-one-fail` against the export references.
- **SC-004**: With scripted checks, the four header states (pending, pass, warn, fail) render on all three protected pages from the stored result alone.
- **SC-005**: In Cloud mode every local model is greyed and a local seat refuses a live run, proven by a test.
- **SC-006**: No credential value appears in `runs/preflight.json`, `/api/meta`, `/api/preflight`, `/api/seats`, or `/api/providers`, proven by a test that plants a marker in `.env`.
- **SC-007**: All gates green, including the em-dash lint over the new copy.

## Assumptions

Owner decisions of 2026-09-17, answered "defaults" to the ten lettered questions:

1. The subdomain and tunnel target are placeholders: `TUNNEL_HOSTNAME` and `CLOUDFLARE_TUNNEL_TOKEN` in `.env.example`, values supplied by the owner later.
2. The login is a session cookie set by a POST form, not HTTP Basic authentication.
3. The credentials are plain values in `.env` (`DEMO_USERNAME`, `DEMO_PASSWORD`), compared in constant time; no hashing, since `.env` is the trust boundary (constitution XVII).
4. The pre-flight result is stored at `runs/preflight.json`; the test compile writes under `runs/preflight/`.
5. "A provider responds" means one minimal model call through the seat's configured model, costing a fraction of a cent on a cloud provider.
6. Essential: the providers a seat uses, Ollama when a seat uses it, Typst compile, PNG export, disk space, `.env` completeness. Non-essential: the tunnel, a provider with a key but no seat.
7. The run mode is `RUN_MODE=laptop|cloud` in `.env`, default laptop.
8. The tunnel runs as a remotely managed Cloudflare Tunnel: hostname routing in the Cloudflare dashboard, the token in `.env`, one script per platform to start it, a dependency record entry.
9. The disk threshold is 5 GB free.
10. The `.env` completeness check is per mode: the login pair and the keys of every cloud provider a seat uses; Cloud mode adds nothing else.

Further assumptions:

- The spec directory is numbered 008 to match the branch; 007 is the peer's S6 spec.
- File ownership with S6: S7 owns `app/preflight/`, `app/auth.py`, `app/web/pages/preflight.html`, `app/web/pages/login.html`, `app/web/static/js/preflight.js`, the tunnel scripts, and the S7 tests; shared files (`app/main.py`, `app/config.py`, `app/runs/registry.py`, `app.css`, `demo.html` and `settings.html` header indicator, `capture_app.py`, `masks.py`) receive new routes, middleware, fields, placeholders, and appended rules only.
- The public route list comes from `specs/007-introduction-replay/contracts/introduction.md`; the pinned run id is `Settings.public_run_id`, which S6 adds, so the guard reads it if present and treats the public Demo as protected until then.
- The leave-behind command and avatar swap wait for S6 and the owner's delivery respectively; both are recorded in the roadmap status as deferred within the slice, not built.
- Without login credentials in `.env` the pages stay open, which is the state of every checkout today; the pre-flight reports it so a laptop cannot go green without a login.
