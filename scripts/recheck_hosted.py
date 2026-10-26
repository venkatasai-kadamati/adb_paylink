"""Non-mutating release check apart from creating an authenticated session."""
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import httpx
ROOT=Path(__file__).resolve().parents[1]
BASE='https://paylink-radiant690s-projects.vercel.app'
profiles=json.loads((ROOT/'.local/recording-users.json').read_text())
today=datetime.now(ZoneInfo('America/Chicago')).date()
with httpx.Client(base_url=BASE,timeout=60,headers={'Origin':BASE}) as c:
 assert c.get('/api/health').json()['database']=='connected'
 r=c.post('/api/auth/login',json={k:profiles[0][k] for k in ('username','password')})
 assert r.status_code==200
 assert 'HttpOnly' in r.headers['set-cookie'] and 'Secure' in r.headers['set-cookie']
 assert c.get('/api/me').json()['username']=='sai'
 accounts=c.get('/api/accounts').json()
 assert any(a['holder_count']==2 for a in accounts)
 insights=c.get('/api/insights').json()
 assert [d['day'] for d in insights['weekly']]==[(today-timedelta(days=i)).isoformat() for i in range(6,-1,-1)],insights['weekly']
 rows=c.get('/api/transfers').json()
 assert any(t['id']=='38cf87a4-4f82-44ab-bea1-3011579a6a2c' for t in rows)
 assert c.get('/api/activity.csv').status_code==200
 result={'checked_at_chicago':datetime.now(ZoneInfo('America/Chicago')).isoformat(),'url':BASE,'passed':True,
 'checks':['Public proxy/API/database health','Private profile authentication and Secure HttpOnly cookie','Retained receipt and shared ownership','Latest code America/Chicago calendar buckets','History and CSV reads'],'application_commit':'e541eb6e180c1b6445aee210a1ff34277f91649d'}
(ROOT/'artifacts/hosted-release-check.json').write_text(json.dumps(result,indent=2)+'\n')
print('Hosted release check passed, including Chicago calendar boundaries and persisted receipt.')
