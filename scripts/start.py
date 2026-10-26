"""Detach only PayLink services and wait for the complete proxy/API/database path."""
from pathlib import Path
import os
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
(ROOT/'artifacts').mkdir(exist_ok=True)

def healthy(url):
    try:
        with urllib.request.urlopen(url, timeout=3) as r:return r.status==200
    except Exception:return False

hosted='--hosted' in sys.argv
if hosted:
    if not (ROOT/'.env.hosted').is_file():raise SystemExit('Configure ignored .env.hosted first.')
else:
    subprocess.run([sys.executable,'scripts/local_db.py'],check=True)

env=os.environ.copy()
if hosted:env['PAYLINK_ENV_FILE']=str(ROOT/'.env.hosted')
for name,url,command in [
 ('backend','http://127.0.0.1:8000/api/health',[sys.executable,'-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8000']),
 ('frontend','http://localhost:3000',['npm','--prefix','frontend','start'])]:
    if not healthy(url):
        with (ROOT/f'artifacts/{name}.log').open('ab') as log:
            process=subprocess.Popen(command,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
        (ROOT/f'artifacts/{name}.pid').write_text(str(process.pid))
for _ in range(40):
    if healthy('http://127.0.0.1:8000/api/health') and healthy('http://localhost:3000/api/health'):
        print('PayLink frontend, backend, and database are connected: http://localhost:3000')
        break
    time.sleep(1)
else:raise SystemExit('Startup failed; inspect artifacts/backend.log and artifacts/frontend.log.')
