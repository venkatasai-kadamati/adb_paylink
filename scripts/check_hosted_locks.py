"""Hosted FK-lock regression. All synthetic grant/transfer writes roll back."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4
import json
import psycopg
from dotenv import dotenv_values
ROOT=Path(__file__).resolve().parents[1]
URL=dotenv_values(ROOT/'.env.hosted')['DATABASE_URL']

def snapshot():
 with psycopg.connect(URL) as c:
  return {'balances':c.execute('SELECT id::text,balance_cents FROM paylink.bank_accounts ORDER BY id').fetchall(),
   'holders':c.execute('SELECT user_id::text,account_id::text FROM paylink.account_holders ORDER BY user_id,account_id').fetchall(),
   'transfers':c.execute('SELECT id::text FROM paylink.transfers ORDER BY id').fetchall()}
with psycopg.connect(URL) as c:
 sai,sid=[c.execute('SELECT id FROM paylink.users WHERE username=%s',(n,)).fetchone()[0] for n in ('sai','siddhardth')]
 savings=c.execute("SELECT a.id FROM paylink.bank_accounts a JOIN paylink.account_holders h ON h.account_id=a.id WHERE h.user_id=%s AND a.label='Rainy day fund'",(sai,)).fetchone()[0]
 source=c.execute("SELECT a.id FROM paylink.bank_accounts a JOIN paylink.account_holders h ON h.account_id=a.id WHERE h.user_id=%s AND a.label='Everyday checking'",(sid,)).fetchone()[0]
 shared=c.execute("SELECT id FROM paylink.bank_accounts WHERE label='Shared expenses'").fetchone()[0]
before=snapshot()
def transfer():
 with psycopg.connect(URL) as c:
  with c.transaction(force_rollback=True):
   c.execute('SET LOCAL statement_timeout=2000')
   c.execute('SELECT paylink.execute_transfer(%s,%s,%s,1,%s,%s)',(sid,source,shared,'rolled-back FK lock verification',uuid4()))
with psycopg.connect(URL) as c:
 with c.transaction(force_rollback=True):
  c.execute('SET LOCAL statement_timeout=5000')
  c.execute('SELECT paylink.add_account_holder(%s,%s,%s)',(sai,savings,'siddhardth'))
  with ThreadPoolExecutor(1) as worker:worker.submit(transfer).result(timeout=5)
assert snapshot()==before
(ROOT/'artifacts/hosted-lock-check.json').write_text(json.dumps({'passed':True,'target':'Supabase paylink',
 'check':'Open joint-owner grant does not block unrelated transfer FK key-share check',
 'writes_rolled_back':True,'balances_ownership_and_transfer_rows_unchanged':True},indent=2)+'\n')
print('Hosted FK lock compatibility passed; both transactions rolled back; all data unchanged.')
