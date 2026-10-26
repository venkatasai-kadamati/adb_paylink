# Public deployment: Supabase + Render + Vercel

**Current state:** no public deployment or hosted Supabase connection has been created or verified in this session. The requested destination is organization **primary-org**, suggested project name **paylink**. Organization membership and billing/region availability must be confirmed in the connected account. This document is a deployment recipe, not proof of deployment.

## 1. Connect the accounts

In ChatGPT's Apps settings, look for Supabase and connect/authorize the organization. Enable the app for the chat if supported. The Supabase mention/tag alone did not expose any tools in this session. If the app is not offered, use the Supabase dashboard flow below. Do not send passwords, access tokens, database URLs containing passwords, or service-role keys in chat.

Sign in to Render and Vercel and authorize access to `venkatasai-kadamati/adb_paylink`. Both can import a GitHub repository through their dashboards. No hosting-provider credentials or tools are currently injected into this environment.

The repository was empty when work began. The application, database scripts, and documents are now prepared for Git-based setup; use the current `main` branch when importing it into hosting providers. Do not upload `.env`, `.venv`, `.next`, or `node_modules`.

## 2. Create or select the Supabase project

In the Supabase dashboard, choose primary-org. Create project `paylink` (or select an existing project dedicated to this simulation). Select the desired region and generate a strong database password. Keep that password in your password manager and secure environment settings.

From the project's database **Connect** information, obtain an admin connection for migration. For machines without IPv6, use the dashboard's **session pooler**, port 5432. Use session pooling, not transaction pooling, for the initial role/migration setup. Copy the actual host, project reference, and connection syntax; do not guess a regional hostname. Percent-encode special characters in URL passwords.

On a trusted setup machine, configure ignored `.env` or securely injected process variables:

| Variable | Purpose |
|---|---|
| `ADMIN_DATABASE_URL` | Owner connection for one-time migration/provisioning only. |
| `DATABASE_URL` | Dedicated backend role connection, initially using a new strong password you choose for `paylink_api`. |
| `JWT_SECRET` | Random secret of at least 32 characters; Render can generate this. |
| `APP_ORIGIN` | Exact final Vercel HTTPS origin, without trailing slash. |
| `COOKIE_SECURE` | `true` for HTTPS deployment. |

Direct DB username: `paylink_api`. Session-pooler username: `paylink_api.<actual-project-ref>`. Both are supported by the migration helper. The URL should enable certificate validation, e.g. `sslmode=verify-full&sslrootcert=system` with a recent libpq. If the provider supplies a CA certificate, use its documented CA file and `verify-full`; never disable TLS verification to make a connection pass.

`migrate.py` reads process variables first and `.env` second. It creates the `paylink_api` role with the password in DATABASE_URL on first provisioning. It does not overwrite an existing role's password. If the role already exists with a different credential, rotate it deliberately through the provider and update the backend binding.

Run only against the selected dedicated project:

```bash
.venv/bin/python scripts/migrate.py
```

This applies the migration once, creates the private schema and role, grants limited access, and sets backend RLS policies. It does not remove existing data. Keep `paylink` out of Supabase's exposed Data API schemas. Neither an anon key nor a service-role HTTP key is needed in the frontend or backend. The app uses direct PostgreSQL from FastAPI by design.

Use SQL Editor to confirm:

```sql
select table_name from information_schema.tables
where table_schema='paylink' and table_type='BASE TABLE' order by table_name;
-- account_holders, bank_accounts, banks, transfers, users
select schemaname,tablename,rowsecurity from pg_tables where schemaname='paylink';
-- rowsecurity = true for all five
```

Populate the simulated bank catalog using `supabase/banks.sql`, then register Sai and Siddhardth through the UI with private passwords. Link accounts through the UI; each receives $1,000 in simulated funding. To demonstrate a joint account, use `supabase/joint-account.sql` after selecting the intended account explicitly. This avoids putting public demo passwords in a hosted database. The local `seed.py --demo` helper deliberately refuses hosted URLs.

## 3. Deploy FastAPI on Render

Create a Blueprint from the repository; `render.yaml` configures a Docker web service named `paylink-api`. Alternatively create the service manually with repository-root Docker context and `backend/Dockerfile`. The backend listens on Render's PORT and exposes `/api/health`.

Set securely:

- `DATABASE_URL`: dedicated Supabase role URL, certificate validation enabled.
- `JWT_SECRET`: generated stable secret, shared by all backend instances.
- `APP_ORIGIN`: the final Vercel HTTPS origin. Set it before testing writes.
- `COOKIE_SECURE=true`.

Do not put ADMIN_DATABASE_URL on the long-running Render app. Do not run local Docker setup or synthetic plan benchmarks during cloud startup. The database must already be migrated. The backend dependencies are pinned, including the binary psycopg client. This project uses one worker; the teaching rate limiter is per-process. A free service may sleep and cold-start; choose a suitable plan before recording the video.

## 4. Deploy Next.js on Vercel

Import the same GitHub repository and set **Root Directory = frontend**, framework Next.js. `frontend/vercel.json` uses `npm ci` and `npm run build`.

Set:

- `BACKEND_URL=https://<actual-render-service-host>` (no trailing slash).
- `NEXT_PUBLIC_DEMO_ENABLED=false`.

BACKEND_URL is needed **at build time** because Next.js compiles the rewrites. After changing it, redeploy the frontend. The frontend proxies `/api/*` to Render, so browser cookies remain first-party and the database URL never enters the browser bundle. Do not put `DATABASE_URL`, ADMIN_DATABASE_URL, or a Supabase service key in any NEXT_PUBLIC variable.

Set Render APP_ORIGIN to the actual stable Vercel production origin and redeploy Render as needed. Preview domains are intentionally not automatically trusted; use the stable production domain for the demonstration.

## 5. Required live acceptance checks

These are **pending** until a real deployment exists:

1. Open the public Vercel site in Chromium and capture the sign-in and overview screens.
2. Confirm the public `/api/health` response reports database connected. This establishes basic connectivity but is not sufficient alone.
3. Register two synthetic users or sign in with privately provisioned demo users; link simulated accounts. Confirm inserts in the Supabase SQL Editor.
4. Send $12.34 from Sai to Siddhardth. Query the exact transfer ID and both balances in Supabase. Confirm one debit, one credit, and one transfer row.
5. Reload both sessions; show the sender debit and recipient receipt. Submit the same idempotency key twice through an authenticated request and confirm only one transfer row.
6. Try insufficient funds and a non-owned source; confirm rejection and unchanged balances.
7. Run the read-only reconciliation query from queries.sql: zero discrepant rows.
8. Capture a real Supabase table/SQL-result screenshot alongside the live app screenshots. Hide connection strings, auth headers, passwords, and session tokens.
9. Record the tested public URL, project reference, deployment version, time, and screenshots in validation.md. Only then mark hosted deployment complete.

Do not point the seeded local pytest/browser scripts at a hosted project: they assume published local credentials and administer fixtures. Adapt them to isolated hosted test identities before running remotely. Generalize the read-only and transfer assertions without borrowing real user data.
