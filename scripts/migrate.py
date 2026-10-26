import os
"""Apply migrations once and provision a backend-only restricted login role."""
from pathlib import Path
from urllib.parse import urlparse, unquote
from dotenv import dotenv_values
import psycopg
from psycopg import sql
ROOT=Path(__file__).resolve().parents[1]
config={**dotenv_values(ROOT/'.env'), **{k:v for k,v in os.environ.items() if k in ('ADMIN_DATABASE_URL','DATABASE_URL')}}
api=urlparse(config['DATABASE_URL'])
if unquote(api.username or '').split('.')[0]!='paylink_api':
    raise SystemExit('DATABASE_URL must use the dedicated paylink_api role, never postgres.')
with psycopg.connect(config['ADMIN_DATABASE_URL']) as c:
    c.execute('CREATE SCHEMA IF NOT EXISTS paylink_meta')
    c.execute('CREATE TABLE IF NOT EXISTS paylink_meta.migrations(name text PRIMARY KEY, applied_at timestamptz DEFAULT now())')
    c.execute('SELECT pg_advisory_xact_lock(56005600)')
    for path in sorted((ROOT/'supabase/migrations').glob('*.sql')):
        if c.execute('SELECT 1 FROM paylink_meta.migrations WHERE name=%s',(path.name,)).fetchone(): continue
        # Strip migration transaction wrappers; outer connection commits the version marker atomically.
        text=path.read_text().replace('BEGIN;\n','',1).removesuffix('COMMIT;\n')
        if not text.strip():
            raise RuntimeError(f'Refusing to mark empty migration as applied: {path.name}')
        c.execute(text)
        c.execute('INSERT INTO paylink_meta.migrations(name) VALUES(%s)',(path.name,))
    if not c.execute("SELECT 1 FROM pg_roles WHERE rolname='paylink_api'").fetchone():
        c.execute(sql.SQL('CREATE ROLE paylink_api LOGIN PASSWORD {}').format(sql.Literal(unquote(api.password or ''))))
    c.execute('GRANT USAGE ON SCHEMA paylink TO paylink_api')
    c.execute('GRANT SELECT ON ALL TABLES IN SCHEMA paylink TO paylink_api')
    c.execute('GRANT INSERT ON paylink.users TO paylink_api')
    for table in ('users','banks','bank_accounts','account_holders','transfers'):
        if not c.execute('SELECT 1 FROM pg_policies WHERE schemaname=%s AND tablename=%s AND policyname=%s',('paylink',table,'backend_read')).fetchone():
            c.execute(sql.SQL('CREATE POLICY backend_read ON paylink.{} FOR SELECT TO paylink_api USING (true)').format(sql.Identifier(table)))
    if not c.execute("SELECT 1 FROM pg_policies WHERE schemaname='paylink' AND tablename='users' AND policyname='backend_register'").fetchone():
        c.execute('CREATE POLICY backend_register ON paylink.users FOR INSERT TO paylink_api WITH CHECK(true)')
    c.execute('GRANT EXECUTE ON FUNCTION paylink.execute_transfer(uuid,uuid,uuid,bigint,text,uuid) TO paylink_api')
    c.execute('GRANT EXECUTE ON FUNCTION paylink.open_account(uuid,uuid,text,text) TO paylink_api')
    c.execute('GRANT EXECUTE ON FUNCTION paylink.add_account_holder(uuid,uuid,text) TO paylink_api')
print('Migrations applied; backend role has read/registration and controlled function access. No direct balance updates.')
