"""Start PayLink's isolated local PostgreSQL, preserving credentials and data."""
import os
import platform
import secrets
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse, unquote

import psycopg
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
env = ROOT / '.env'
if not env.exists():
    admin, api = secrets.token_hex(24), secrets.token_hex(24)
    with os.fdopen(os.open(env, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as f:
        f.write(f'ADMIN_DATABASE_URL=postgresql://postgres:{admin}@127.0.0.1:54322/postgres\n'
                f'DATABASE_URL=postgresql://paylink_api:{api}@127.0.0.1:54322/postgres\n'
                f'JWT_SECRET={secrets.token_hex(48)}\nAPP_ORIGIN=http://localhost:3000\nCOOKIE_SECURE=false\nPUBLIC_DEMO_ENABLED=true\n')
frontend_env = ROOT / 'frontend/.env.local'
if not frontend_env.exists():
    frontend_env.write_text('NEXT_PUBLIC_DEMO_ENABLED=true\n')
config = {**dotenv_values(env), **{k: v for k, v in os.environ.items()
                                if k in ('ADMIN_DATABASE_URL', 'DATABASE_URL')}}
admin = urlparse(config['ADMIN_DATABASE_URL'])
if admin.hostname not in ('127.0.0.1', 'localhost'):
    raise SystemExit('Local helper refuses hosted URLs. Use the hosted migration workflow.')

def ready():
    try:
        with psycopg.connect(config['ADMIN_DATABASE_URL'], connect_timeout=2) as c:
            c.execute('SELECT 1')
        return True
    except psycopg.OperationalError:
        return False

if ready():
    print(f'Configured local PostgreSQL is ready on port {admin.port or 5432}.')
    raise SystemExit(0)

mode = os.getenv('LOCAL_DATABASE_MODE', 'native' if platform.system() == 'Darwin' else 'docker')
if mode == 'native':
    pg_bin = Path(os.getenv('POSTGRES_BIN', '/opt/homebrew/opt/postgresql@16/bin'))
    if not (pg_bin / 'initdb').exists():
        found = shutil.which('initdb')
        if not found:
            raise SystemExit('Install postgresql@16 or set POSTGRES_BIN to its bin directory.')
        pg_bin = Path(found).parent
    local = ROOT / '.local'
    local.mkdir(mode=0o700, exist_ok=True)
    cluster = local / 'postgres'
    if not (cluster / 'PG_VERSION').exists():
        password_file = local / 'initdb-password'
        with os.fdopen(os.open(password_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as f:
            f.write(unquote(admin.password or ''))
        try:
            subprocess.run([str(pg_bin / 'initdb'), '-D', str(cluster), '-U', admin.username or 'postgres',
                            '--auth=scram-sha-256', '--pwfile', str(password_file), '--encoding=UTF8',
                            '--locale=C'], check=True, stdout=subprocess.DEVNULL)
        finally:
            password_file.unlink(missing_ok=True)
    subprocess.run([str(pg_bin / 'pg_ctl'), '-D', str(cluster), '-l', str(local / 'postgres.log'),
                    '-o', f'-h 127.0.0.1 -p {admin.port or 54322} -k {local}', 'start'], check=True)
elif mode == 'docker':
    name = 'paylink-db'
    exists = subprocess.run(['docker', 'inspect', name], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL).returncode == 0
    if exists:
        subprocess.run(['docker', 'start', name], check=True, stdout=subprocess.DEVNULL)
    else:
        subprocess.run(['docker', 'run', '-d', '--name', name, '-e', 'POSTGRES_PASSWORD',
                        '-p', f'127.0.0.1:{admin.port or 54322}:5432',
                        '-v', 'paylink-db:/var/lib/postgresql/data', 'postgres:16-alpine'],
                       env=dict(os.environ, POSTGRES_PASSWORD=unquote(admin.password or '')),
                       check=True, stdout=subprocess.DEVNULL)
else:
    raise SystemExit('LOCAL_DATABASE_MODE must be native or docker.')
for _ in range(60):
    if ready():
        print(f'Local PostgreSQL is ready on port {admin.port or 54322} ({mode}).')
        break
    time.sleep(1)
else:
    raise SystemExit('Database not ready. Inspect .local/postgres.log or docker logs paylink-db.')
