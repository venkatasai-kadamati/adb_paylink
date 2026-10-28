# PayLink hosted deployment

As of October 25, 2026 (America/Chicago), the public application is deployed and verified:

| Component | Destination |
|---|---|
| App | https://paylink-radiant690s-projects.vercel.app |
| API health | https://paylink-api-xgfo.onrender.com/api/health |
| Supabase | primary-org / paylink / wktoypofpksgbjwtadrn / us-east-2 |
| Render | Venkatasai's workspace / paylink-api / srv-dbfciua9lscs739js0rg / Ohio / free |
| Vercel | radiant690's projects / paylink / prj_6Zkso4Gte1Rx5WEf0QvaPRkU2MMI / production |
| Source | venkatasai-kadamati/adb_paylink / main |

The initial hosted application commit is e20a095; 0fec3a6 adds reproducible hosted acceptance; e541eb6 explicitly initializes pooled sessions to enforce America/Chicago calendar boundaries after the pooler ignored startup timezone options. The latest deploy IDs and observed source revision are in artifacts/deployment-evidence.json. Later documentation-only commits do not change application behavior. Always inspect the current deployment before attributing a test to a newer source revision.

## Security and connection configuration

The schema is private `paylink`, containing exactly users, banks, bank_accounts, account_holders, and transfers. It is not exposed through the Supabase Data API. All five tables enable RLS. FastAPI uses a dedicated `paylink_api` login with SELECT, user registration INSERT, and execution of the three controlled functions. It has no direct balance UPDATE, ownership INSERT, or transfer INSERT privileges. The actor UUID is derived from the verified backend session; the role is a trusted service identity and must never be exposed to clients.

The Mac cannot resolve/use this project's direct IPv6 database endpoint, so the verified connection uses the dashboard-provided IPv4 session pooler at aws-0-us-east-2.pooler.supabase.com:5432. The pooler username is paylink_api.wktoypofpksgbjwtadrn. Passwords are generated privately. Connections use `sslmode=verify-full` and the official public CA in backend/certs/supabase-ca.crt. The certificate's upstream link is recorded beside it. Do not replace verification with `sslmode=require` to hide a trust failure.

Render stores DATABASE_URL and JWT_SECRET privately. Its DATABASE_URL certificate path is `/app/backend/certs/supabase-ca.crt`, copied into the image. APP_ORIGIN is the exact public Vercel origin above; COOKIE_SECURE=true. No admin connection is installed on the long-running API. The Docker command uses exec so termination signals reach Uvicorn. The service has one worker and free-plan limitations.

Vercel uses frontend as its root, Node 24, `npm ci`, and `npm run build`. BACKEND_URL points to the Render API; NEXT_PUBLIC_DEMO_ENABLED=true; Render PUBLIC_DEMO_ENABLED=true enables the two explicitly public synthetic test profiles. Production is publicly accessible. BACKEND_URL is compiled into Next.js rewrites, so changing it requires a rebuild. Database URLs, JWT secrets, and service keys must never be NEXT_PUBLIC variables.

The private synthetic recording passwords live in `.local/recording-users.json` on the Mac. The ignored `.env.hosted` contains the restricted database connection and local hosted-mode session secret. Neither belongs in Git, a submission ZIP, screenshots, or video. Public local demo-password seeding remains blocked against hosted URLs.

## Schema provisioning and future updates

The four checked-in migrations were applied to the newly created dedicated hosted project through Supabase, including FK-compatible owner allocation locks. The restricted role and policies were provisioned separately without putting its password into migration source. The synthetic bank catalog came from supabase/banks.sql. Profiles and accounts were created through the actual public UI with private passwords, then joint ownership through Accounts.

For a fresh dedicated project, select its real organization/region and obtain the dashboard's current connection details. Apply versioned schema migrations, provision the restricted role, and configure backend/frontend secrets. `scripts/migrate.py` supports an owner ADMIN_DATABASE_URL and dedicated DATABASE_URL, but this Mac deliberately does not hold the hosted owner's password. Use connected Supabase migration tools or securely provide an owner URL on a trusted setup machine. Never repoint seeded local fixture tests or query_evidence.py at hosted data.

For future code changes, push reviewed source to main and inspect Render/Vercel deployment status. Vercel Git integration auto-deploys this branch. Render was imported by public repository URL and did not deploy on the next push despite its autoDeploy flag; a manual deploy of the new revision was required. Verify a real deploy event and trigger manually when this import has no Git-provider webhook. A queued build is not success. Wait for Render live and Vercel READY, check the public `/api/health`, and rerun an appropriately scoped acceptance check. Keep the stable public origin when testing writes; unrelated preview/alias origins are not automatically trusted.

## Verified acceptance and remaining work

`scripts/hosted_browser_test.py` runs actual public browser registration/sign-in, simulated account creation, immediate joint-owner grants, $12.34 transfers, read-only database delta assertions, same-key retries, changed-payload/authorization/insufficient-funds rejection, persistence, CSV, own-account movement, insights, and mobile layout. It retains private synthetic recording rows deliberately and reads its credentials from ignored local files. `scripts/hosted_evidence.py` independently records schema, role, TLS, current rows, and reconciliation without writes.

See validation.md, hosted-browser-results.json, hosted-database-evidence.json, hosted-advisors.json, and the actual Supabase screenshot. Security advisors returned no findings; informational unused indexes on the small dataset are not grounds to remove the history indexes without workload evidence.

Render's free service can sleep. Warm the public app and API health, then sign in before recording. Backup/restore, crash recovery, sustained hosted load, a distributed limiter, invitation acceptance/revocation, and an immutable ledger remain future work. No real banks or funds are connected.

The starting_balance_200 migration changes only defaults; existing account balances are preserved. Application revision eed5ec1 introduces automatic $200 checking-account creation during registration and the refined interface.
