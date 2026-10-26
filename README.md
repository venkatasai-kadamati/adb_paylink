# PayLink

A simulated peer-to-peer banking application for **CS 5600 Advanced Database Systems, Fall 2026**. Next.js + TypeScript frontend, FastAPI backend, and a five-relation PostgreSQL schema designed for Supabase. No real banks or funds.

**Live app:** <https://paylink-radiant690s-projects.vercel.app> — Next.js on Vercel, FastAPI on Render, and private PostgreSQL on Supabase primary-org/paylink. Mac validation passed 25 database/API tests, 12 local browser groups, and nine hosted browser groups. Both databases reconcile with zero discrepancies. See [current evidence](docs/validation.md) and [deployment details](docs/deployment.md). Render's free service may need to wake before recording.

Start on macOS with [the local setup guide](docs/local-macos.md). For a new ChatGPT Desktop session, use [the handoff notes](docs/HANDOFF.md).

## Deliverables

- [Midterm report](docs/midterm-report.md) · [PDF](docs/midterm-report.pdf) · [Word](docs/midterm-report.docx)
- [Submission guide: responsibilities, four milestones, future milestones, and video script](docs/submission_guide.md)
- [Editable ER diagram](docs/er-diagram.drawio) — open/import in diagrams.net and edit every entity/connector
- [ER diagram SVG](docs/er-diagram.svg) · [PNG](docs/er-diagram.png) · [Mermaid source](docs/er-diagram.mmd)
- [Normalization and data dictionary](docs/database-design.md)
- [SQL demonstrations](docs/queries.sql) · [Actual query-plan evidence](artifacts/query-evidence.txt)
- [Live-browser test evidence](artifacts/browser-results.json) · [Test results](artifacts/test-results.txt)
- [Screenshots and validation scope](docs/validation.md) · [Read-only recording SQL](docs/recording-demo.sql)

## Local development

Requires Python 3.12, Node 24, npm 11, PostgreSQL 16 (native Homebrew on macOS or Docker on Linux), and Chromium for browser checks. The checkout is already isolated; use it directly rather than creating a worktree.

```bash
cd adb_paylink
./scripts/install.sh
./scripts/start.sh
.venv/bin/python -m pytest backend/tests -q
.venv/bin/python scripts/browser_test.py
```

`install.sh` creates ignored `.env` credentials with restrictive permissions, starts an isolated PostgreSQL 16 cluster (native on macOS, Docker on Linux), applies versioned migrations, seeds only synthetic local data, and builds the frontend. Repeating the migrations and seed preserves existing demo records. PostgreSQL is bound to loopback, not the public network. Running `local_db.py` with a hosted admin URL deliberately refuses to create or modify a local container; use the hosted flow instead.

**Local test profiles only:** `sai` or `siddhardth`; local demo password: `PaylinkDemo!2026`. The sign-in page also has demo buttons. These are deliberately published local teaching credentials, **not production secrets**. The seed helper refuses to seed these passwords into a hosted project. The deployed app uses private synthetic passwords from the ignored `.local/recording-users.json` on the setup Mac and has `NEXT_PUBLIC_DEMO_ENABLED=false`. Do not publish that file.

## Architecture

Browser → Next.js same-origin `/api/*` proxy → FastAPI → dedicated `paylink_api` PostgreSQL login → private `paylink` schema. The database transaction function owns all transfer balance updates. The browser never holds a database connection or privileged key. Authentication uses Argon2id and signed, HttpOnly, SameSite cookies; HTTPS cookies are enabled for deployment. Supabase is the PostgreSQL host, not the authentication implementation; this deliberately follows the project proposal.

Five base tables: `users`, `banks`, `bank_accounts`, `account_holders`, `transfers`. Migration metadata is infrastructure, outside the application schema. Amounts use integer USD cents; the UI sends integers, and the backend rejects fractional cents. Transfers up to $1,000,000 and bounded balances prevent unsafe JSON integer conversion. Joint-account totals are deduplicated by account; do not sum account balances after joining owners.

## Verification

The Mac integration suite runs against a real database and covers atomicity, insufficient funds, same-key concurrent retries, conflicting payloads, overspending, opposing transfers, authorization, inactive accounts, constraints, shared ownership, and post-update rollback. The browser suite uses actual Chromium interactions and independently checks committed database rows and both balance deltas. It cleans up only its synthetic test records. Do not point the seeded integration/browser suite at a live project containing meaningful user data.

`query_evidence.py` temporarily inserts 20,000 plan-fixture rows and drops an index inside a savepoint, then rolls both back. **Run only on the isolated local teaching database**; the generated output is a microbenchmark, not a production latency guarantee.

See the report for known limitations and the AI-assistance disclosure draft. Team contribution assignments are proposed ownership, not a claim about work independently performed by either teammate.

For hosted acceptance from this configured Mac, run `.venv/bin/python scripts/hosted_browser_test.py` and `.venv/bin/python scripts/hosted_evidence.py`. These use private synthetic profiles and a read-only database verifier; they do not run local admin fixtures or plan benchmarks on Supabase. The Accounts screen supports immediate equal joint-owner grants; invitation acceptance and revocation remain future work.
