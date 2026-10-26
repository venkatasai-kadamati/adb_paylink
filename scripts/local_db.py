"""Start a local PostgreSQL container without printing credentials."""
import os, secrets, subprocess, time
from pathlib import Path
from dotenv import dotenv_values
ROOT=Path(__file__).resolve().parents[1]
env=ROOT/'.env'
if not env.exists():
    admin=secrets.token_hex(24); api=secrets.token_hex(24)
    env.write_text(f'ADMIN_DATABASE_URL=postgresql://postgres:{admin}@127.0.0.1:54322/postgres\nDATABASE_URL=postgresql://paylink_api:{api}@127.0.0.1:54322/postgres\nJWT_SECRET={secrets.token_hex(48)}\nAPP_ORIGIN=http://localhost:3000\nCOOKIE_SECURE=false\n')
    env.chmod(0o600)
frontend_env=ROOT/'frontend/.env.local'
if not frontend_env.exists(): frontend_env.write_text('NEXT_PUBLIC_DEMO_ENABLED=true\n')
config={**dotenv_values(env), **{k:v for k,v in os.environ.items() if k in ('ADMIN_DATABASE_URL','DATABASE_URL')}}
from urllib.parse import urlparse
admin=urlparse(config['ADMIN_DATABASE_URL'])
if admin.hostname not in ('127.0.0.1','localhost'):
    raise SystemExit('This helper only starts local databases; use migrate.py for a configured hosted project.')
name='paylink-db'
exists=subprocess.run(['docker','inspect',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
if exists:
    subprocess.run(['docker','start',name],check=True,stdout=subprocess.DEVNULL)
else:
    docker_env=dict(os.environ, POSTGRES_PASSWORD=admin.password)
    subprocess.run(['docker','run','-d','--name',name,'-e','POSTGRES_PASSWORD','-p','127.0.0.1:54322:5432',
      '-v','paylink-db:/var/lib/postgresql/data','postgres:15-alpine'],env=docker_env,check=True,stdout=subprocess.DEVNULL)
import psycopg
for _ in range(60):
    try:
        with psycopg.connect(config['ADMIN_DATABASE_URL'],connect_timeout=2) as c:
            c.execute('SELECT 1')
        print('Local PostgreSQL is ready on port 54322.')
        break
    except psycopg.OperationalError: time.sleep(1)
else: raise SystemExit('Database did not become ready. Inspect docker logs paylink-db.')
