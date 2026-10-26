# PayLink validation evidence

Current evidence was collected on this Apple Silicon Mac on October 25, 2026 (America/Chicago). The earlier Linux run is historical and has been replaced by Mac results and live hosted acceptance. All application screenshots are real Chromium captures. The public app is <https://paylink-radiant690s-projects.vercel.app>, backed by Render and Supabase project wktoypofpksgbjwtadrn in primary-org.

## Current checks

| Check | Result | Evidence |
|---|---|---|
| Production Next.js build and TypeScript | Passed on Node 24.22.1 | artifacts/build-results.txt |
| Mac database and API integration | 25 passed; one framework deprecation warning | artifacts/test-results.txt |
| Local Chromium workflow on Mac | 12 groups passed; no JavaScript errors | artifacts/browser-results.json and browser-run.txt |
| Public Chromium workflow on Mac | Nine groups passed; no JavaScript errors | artifacts/hosted-browser-results.json and hosted-browser-run.txt |
| Local balance reconciliation after fixture cleanup | Zero discrepancies | artifacts/query-evidence.txt |
| Hosted balance reconciliation | Zero discrepancies | artifacts/hosted-browser-results.json and hosted-database-evidence.json |
| Hosted database | PostgreSQL 17.11; five private relations; restricted role; TLS verify-full | Supabase project and hosted-database-evidence.json |
| Supabase security advisor | No findings at validation time | artifacts/hosted-advisors.json |
| Hosted performance advisor | Informational unused-index notices on small dataset | artifacts/hosted-advisors.json; no speculative index removal |
| Public API and proxy health | Connected | /api/health through the public Vercel origin |
| Backup restore, crash recovery, sustained load | Not run | Future milestones 5 and 7 |

The isolated Mac test database uses Homebrew PostgreSQL 16.15 on 127.0.0.1:54322. Python is 3.12.16. These tests exercise real SQL and concurrency without mocking the database. The additional hosted FK-lock regression passed with both transactions rolled back and every balance, holder and transfer row unchanged; see artifacts/hosted-lock-check.json. A final release check verified explicit Chicago session initialization after the pooler ignored startup options; see hosted-release-check.json.

No seeded/admin fixture suite or artificial query-plan benchmark was directed at hosted Supabase.

The tests cover atomic debit/credit, eight concurrent same-key calls, conflicting payloads, competing spending, opposing transfers, ownership, active state, invalid amounts, direct-update denial, FK/balance constraints, joint-owner spending, rollback after debit, and destination-credit-limit rollback. New tests cover concurrent joint-owner grants, an account-opening/ownership-limit race, schema and role privileges, registration, exact email lookup, API authorization, internal-transfer insight totals, and CSV formula escaping.

## Public acceptance scope

The hosted script created private synthetic profiles via the browser, opened simulated accounts, and added Siddhardth as an equal joint owner. In two isolated browser sessions it sent $12.34, independently queried the exact event and both account deltas through a read-only restricted database connection, checked retries and rejection paths, reloaded history, downloaded a real CSV, and spent shared funds as the second owner. It also checked insights, 390px mobile layout, reconciliation, and browser errors.

The retained representative event is 38cf87a4-4f82-44ab-bea1-3011579a6a2c. Its captured source balance moved from 100000 to 98766 cents and destination from 100000 to 101234 cents. Subsequent successful payments, including a joint-owner movement, can change the current balances. Use the snapshots in hosted-browser-results.json for those exact before/after assertions; use recording-demo.sql and the receipt ID from a new recorded payment for live demonstration.

Private profile passwords, database credentials, and session cookies are not in Git. The public local-demo password and demo buttons are disabled on the hosted frontend. Hosted synthetic recording data remains intentionally available. Local browser test data was removed and its balance changes reversed.

Hosted correctness checks establish the tested workflow, not production-scale concurrency, backup restoration, a security certification, or arbitrary serializability. Render's free service can sleep; open health and sign in before recording.

## Screenshot index

| Files | Scope |
|---|---|
| artifacts/01-sign-in.png through 08-mobile.png | Current Mac local validation, including temporary receipts that were cleaned up |
| artifacts/hosted-01-sign-in.png | Public sign-in with local demo shortcuts disabled |
| artifacts/hosted-02-overview.png | Hosted accounts and joint-owner badge |
| artifacts/hosted-03-review.png and hosted-04-receipt.png | Actual public payment review and committed receipt |
| artifacts/hosted-05-details.png and hosted-06-recipient.png | Reloaded exact event and second user's receipt |
| artifacts/hosted-07-insights.png and hosted-08-mobile.png | Hosted SQL insights and responsive layout |
| artifacts/hosted-09-supabase.png | Actual Supabase SQL-result view, captured after query execution |

## Query plan scope

The local helper temporarily inserts 20,000 artificial event rows in a savepoint, measures an outgoing-history SELECT with and without the source/time index, and rolls back both inserts and index removal. It does not alter balances or establish hosted latency. The current Mac run recorded an index scan with three shared buffer hits and 0.009 ms execution versus a sequential scan/top-N sort with 385 hits and 1.614 ms. Read artifacts/query-evidence.txt for the exact plans. These are one-run microbenchmark results, not a claim that all application queries share that plan.
