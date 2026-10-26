# Validation evidence and screenshot index

All current application screenshots are **real Chromium captures of the running local implementation**, not generated UI illustrations. **None is a hosted Supabase dashboard screenshot.** No public site URL, hosted migration, hosted transaction, or hosted screenshot has been verified yet. The user's live-site requirement remains open.

## Completed checks

| Check | Result | Evidence |
|---|---|---|
| Next.js production compilation and TypeScript | Passed | `artifacts/build-results.txt`; repeat build in `artifacts/install-results.txt` |
| Database/API integration | 19 passed; one framework deprecation warning | `artifacts/test-results.txt` |
| Real Chromium workflow | Completed; nine grouped checks passed, no JS errors | `artifacts/browser-results.json`, `artifacts/browser-run.txt` |
| Balance reconciliation after test cleanup | Zero discrepancies | `artifacts/query-evidence.txt` |
| Repeat installation, migration, and seed | Passed; existing demo preserved | `artifacts/install-results.txt` |
| Public website and Supabase read/write validation | **Not run: account/tool access unavailable** | `docs/deployment.md` acceptance checklist |
| Hosted Docker service build and deployment | **Not run** | Dockerfile and provider configuration supplied; not proof of deployment |
| Backup/restore and crash recovery | **Not run** | Future milestones |

The integration tests use actual PostgreSQL 15.19, not an in-memory substitute. The full local Supabase image failed to extract due to Docker storage exhaustion; the current validated database is standard PostgreSQL. The application schema uses PostgreSQL features suitable for the target Supabase platform, but compatibility is not a substitute for running the hosted acceptance checks.

The tests cover: balance conservation, insufficient funds, eight concurrent same-key requests, changed-key-payload rejection, competing spends, opposing transfers, non-owner/inactive account rejection, invalid amounts, direct UPDATE denial, FK/balance constraints, joint-owner spending, enclosing-transaction rollback, and a destination credit-limit failure after the source debit. API checks also cover authentication, origin rejection, cookie flags, masked account information, exact lookup, export, logout, and fractional-cent rejection.

The browser checks run real form input and clicks. For the $12.34 payment they query PostgreSQL independently to assert one transfer row, −1,234 source cents, and +1,234 destination cents. They then verify persistence, receipt details, a real CSV download, an own-account transfer, account allocation, the recipient session, a 390px layout with no document overflow, and registration. Browser fixture transfers/users/accounts are cleaned up and both original balances restored. Therefore screenshot receipt IDs are temporary test evidence, not rows promised to remain in the final seed database. Browser assertions were rerun after correcting test-selector timing and the mobile overflow defect.

## Screenshot index

| File | What it shows |
|---|---|
| `artifacts/01-sign-in.png` | Desktop sign-in and local synthetic demo profiles. |
| `artifacts/02-overview.png` | Account totals, joint account, actions, and actual SQL-backed recent activity. |
| `artifacts/03-insights.png` | Month totals and seven-day volume from database queries. |
| `artifacts/04-transfer-review.png` | Recipient, source, $12.34 amount, note, and review step before submission. |
| `artifacts/05-transfer-success.png` | Actual success receipt and temporary committed transfer ID. |
| `artifacts/06-transfer-details.png` | Receipt matched to the stored transfer ID. |
| `artifacts/07-recipient-receipt.png` | Siddhardth's signed-in received-payment history. |
| `artifacts/08-mobile.png` | Responsive 390px overview after the overflow correction. |
| `artifacts/report-cover.png` | PDF first-page visual inspection. |
| `artifacts/report-page3.png` | PDF ER-model/table visual inspection. |

The general account screenshots are captured after browser fixture cleanup. Transfer/recipient/mobile screenshots capture the temporary demonstration before cleanup. Dates use the browser's America/Chicago timezone for the captured demonstration.

## Query-plan evidence

The benchmark uses 20,000 artificial event rows inside a savepoint and rolls back both rows and index removal. It is restricted by the helper to the local database. It measures one outgoing-history SELECT with and without the source/time composite index. It does not change account balances, assert actual financial history, prove the plan of the combined UI-history query, or estimate hosted latency. Read `artifacts/query-evidence.txt` for exact plans, timing, and buffer counts.

## Required evidence before claiming live readiness

Follow `docs/deployment.md`: authenticate the services, provision the dedicated Supabase project/role, deploy the frontend/backend, then capture the public UI and corresponding Supabase transfer/balance rows. Record the real URL and deployment version, use two sessions, check duplicate/rejected transfers, and run the read-only reconciliation. No localhost link should be presented as the requested public website.
