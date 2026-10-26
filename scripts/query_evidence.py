import os
from pathlib import Path
from uuid import uuid4
from dotenv import dotenv_values
import psycopg
ROOT=Path(__file__).resolve().parents[1]
C={**dotenv_values(ROOT/'.env'), **{k:v for k,v in os.environ.items() if k in ('ADMIN_DATABASE_URL','DATABASE_URL')}}
from urllib.parse import urlparse
if urlparse(C['ADMIN_DATABASE_URL']).hostname not in ('127.0.0.1','localhost'):
    raise SystemExit('Plan fixtures are restricted to the isolated local database.')
with psycopg.connect(C['ADMIN_DATABASE_URL']) as c:
    version=c.execute('SELECT version()').fetchone()[0]
    base=c.execute('SELECT (SELECT count(*) FROM paylink.users),(SELECT count(*) FROM paylink.banks),(SELECT count(*) FROM paylink.bank_accounts),(SELECT count(*) FROM paylink.account_holders),(SELECT count(*) FROM paylink.transfers)').fetchone()
    reconciliation=c.execute('''WITH delta AS(SELECT source_account_id AS id,-amount_cents AS n FROM paylink.transfers UNION ALL SELECT destination_account_id,amount_cents FROM paylink.transfers)
     SELECT a.id FROM paylink.bank_accounts a LEFT JOIN delta d ON d.id=a.id GROUP BY a.id HAVING a.balance_cents<>a.opening_balance_cents+coalesce(sum(d.n),0)''').fetchall()
    evidence=[f'Database: {version}','Hosting: local PostgreSQL; hosted Supabase unverified.',f'Core row counts (users,banks,accounts,holders,transfers): {base}',f'Reconciliation discrepancies: {len(reconciliation)}','']
    # Actual isolated plan measurement; no changes survive the transaction.
    a,b=c.execute('SELECT id FROM paylink.bank_accounts ORDER BY id LIMIT 2').fetchall()
    u=c.execute('SELECT user_id FROM paylink.account_holders WHERE account_id=%s LIMIT 1',(a[0],)).fetchone()[0]
    benchmark='''SELECT id,amount_cents,created_at FROM paylink.transfers WHERE source_account_id=%s ORDER BY created_at DESC,id DESC LIMIT 20'''
    c.execute('SAVEPOINT benchmark')
    c.execute('''INSERT INTO paylink.transfers(initiated_by,source_account_id,destination_account_id,amount_cents,memo,idempotency_key,created_at)
      SELECT %s,%s,%s,100,'rolled-back plan fixture',gen_random_uuid(),now()-g*interval '1 minute' FROM generate_series(1,20000) g''',(u,a[0],b[0]))
    c.execute('ANALYZE paylink.transfers')
    evidence+=['20,000 synthetic transfer rows, transaction-only; not financial history.','WITH composite source/time index:']
    evidence += [r[0] for r in c.execute('EXPLAIN (ANALYZE,BUFFERS) '+benchmark,(a[0],)).fetchall()]
    c.execute('DROP INDEX paylink.transfers_source_time_idx')
    evidence+=['','WITHOUT composite source/time index (transactional DROP, rolled back):']
    evidence += [r[0] for r in c.execute('EXPLAIN (ANALYZE,BUFFERS) '+benchmark,(a[0],)).fetchall()]
    c.execute('ROLLBACK TO SAVEPOINT benchmark')
    evidence+=['','Fixture inserts and index drop rolled back. Index restored. No balances changed.']
    assert c.execute("SELECT to_regclass('paylink.transfers_source_time_idx')").fetchone()[0]
    assert not reconciliation
(ROOT/'artifacts/query-evidence.txt').write_text('\n'.join(evidence)+'\n')
print('\n'.join(evidence))
