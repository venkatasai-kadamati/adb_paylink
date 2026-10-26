# PayLink handoff for ChatGPT Desktop

Open the cloned `adb_paylink` folder in your local coding workspace. Suggested first prompt:

> Continue this PayLink project locally on my Mac. Read README.md, docs/HANDOFF.md, and docs/local-macos.md. Use the existing checkout. Inspect the actual machine and Git status, set up the local app, then verify the frontend, backend, and PostgreSQL together. Preserve credentials and existing data. Do not attempt cloud deployment unless I ask. Review the midterm report and submission guide with me after the app works.

## Current implementation

- Next.js/React/TypeScript frontend; FastAPI/Argon2id/cookie-session backend.
- Five PostgreSQL domain tables in the private `paylink` schema: users, banks, bank_accounts, account_holders, transfers.
- Ownership bridge supports joint accounts. Transfer function uses integer cents, deterministic row locking, atomic updates, and initiator-scoped idempotency.
- Registration, sign-in, account creation, recipient lookup, transfer review/confirmation, history, CSV, insights, and mobile layout are implemented.
- Report, normalization analysis, editable ER diagrams, team ownership proposal, four milestones, future milestones 5–7, and video script are in docs/.

## Verified evidence and limits

Linux validation: production build, 19 database/API tests, and nine grouped Chromium workflow checks passed. Evidence is in artifacts/. SQL query-plan benchmark fixtures were rolled back, and balance reconciliation found zero discrepancies. The source contains macOS-compatible setup/browser helpers; the Mac itself still needs validation after cloning.

Public deployment and hosted Supabase validation were not performed. The previous session did not expose Supabase/Vercel/Render tools or usable credentials. Organization requested: primary-org; suggested hosted project name: paylink. Do not claim a live website or hosted DB connection exists. The user has now chosen local development first.

## Preserve these boundaries

- `.env`, frontend/.env.local, dependency folders, caches, server logs, and PID files are ignored and must remain uncommitted.
- Fresh local setup generates its own credentials; none need to be copied from the cloud.
- Demo credentials are public, local-only synthetic fixtures. Seed helper refuses hosted database URLs.
- Browser/integration tests use the local teaching database; do not repoint their administrative fixtures to a hosted project.
- Sai/Siddhardth contribution assignments are proposed review ownership, not verified historical authorship. Keep the assistance disclosure and confirm actual contributions before academic submission.
- Existing screenshots and test outputs describe the earlier Linux run; refresh them only after executing checks on the current machine.
