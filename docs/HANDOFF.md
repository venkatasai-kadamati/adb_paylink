# PayLink current handoff

Use this existing checkout on main. Preserve ignored .env, .env.hosted, .local data and recording credentials. The starting source was b860fd9; current app code adds immediate equal joint ownership and verified Mac/hosted setup. No force pushes are needed.

The public app is https://paylink-radiant690s-projects.vercel.app. Next.js runs on Vercel, FastAPI on Render, and PostgreSQL 17.11 on Supabase primary-org/paylink (wktoypofpksgbjwtadrn). Hosted database connections use a restricted role, the IPv4 session pooler, and TLS verify-full with the official CA. Render is on a free plan and can sleep; warm health/login before recording.

Current Mac evidence: 26 real database/API tests, 13 local Chromium groups, and nine hosted browser groups passed. Both local and hosted reconciliation found zero discrepancies. Local PostgreSQL 16.15 is an isolated native Homebrew cluster for integration tests, not the recording destination. Linux results are historical.

Read docs/validation.md for scope, deployment.md for destinations/configuration, submission_guide.md for the four milestones and complete video script, and recording-demo.sql for read-only live SQL. The representative receipt and exact before/after snapshot are in artifacts/hosted-browser-results.json; later transfers change current balances.

Private synthetic Sai/Siddhardth passwords are in .local/recording-users.json, excluded from Git. The hosted app has no public demo shortcut. Do not seed the published local password into Supabase, expose credentials in screenshots, or run local admin fixtures/plan benchmarks remotely.

The five domain tables remain users, banks, bank_accounts, account_holders and transfers. Joint-owner addition uses one bridge row, locks target user before account, enforces the four-account limit, and grants equal visibility/spending immediately. Invitations and removal are future work. Existing transfer functions retain UUID-ordered row locks, actor-scoped idempotency, atomic debit/credit/event, and rollback.

Documents and ER sources are in docs/ with matching PDF/Word/HTML exports. Sai/Siddhardth ownership is a proposed split for review and explanation, not verified historical contribution. Preserve the accurate Codex disclosure. Actual team contribution statements and course AI-policy compliance remain the team's responsibility; do not invent them.

New signup behavior: registration creates a default $200 checking account and ownership atomically. Additional accounts also open with $200. Existing balances/history were preserved. The UI uses larger system fonts, clearer weights and contrast, professional transfer labels, and a How to test button with hover tips plus a detailed dialog.
