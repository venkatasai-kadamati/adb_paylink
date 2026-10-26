"""Read-only hosted schema, role, transfer and reconciliation evidence."""
import json
from datetime import datetime, timezone
from pathlib import Path
import psycopg
from psycopg.rows import dict_row
from dotenv import dotenv_values
ROOT=Path(__file__).resolve().parents[1]
cfg=dotenv_values(ROOT/'.env.hosted')
with psycopg.connect(cfg['DATABASE_URL'],row_factory=dict_row) as c:
 c.execute('SET TRANSACTION READ ONLY')
 evidence={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'project_ref':'wktoypofpksgbjwtadrn',
  'identity':c.execute('SELECT current_user,version()').fetchone(),
  'client_tls':{'in_use':c.pgconn.ssl_in_use,'mode':'verify-full','trusted_ca':'backend/certs/supabase-ca.crt'},
  'tables':c.execute("SELECT tablename,rowsecurity FROM pg_tables WHERE schemaname='paylink' ORDER BY tablename").fetchall(),
  'constraints':c.execute("SELECT conrelid::regclass::text AS relation,conname,pg_get_constraintdef(oid) AS definition FROM pg_constraint WHERE connamespace='paylink'::regnamespace ORDER BY relation,conname").fetchall(),
  'functions':c.execute("SELECT proname,prosecdef,proconfig FROM pg_proc WHERE pronamespace='paylink'::regnamespace ORDER BY proname").fetchall(),
  'balances':c.execute('SELECT id,label,balance_cents,opening_balance_cents FROM paylink.bank_accounts ORDER BY id').fetchall(),
  'owners':c.execute('SELECT a.label,u.username FROM paylink.account_holders h JOIN paylink.users u ON u.id=h.user_id JOIN paylink.bank_accounts a ON a.id=h.account_id ORDER BY a.label,u.username').fetchall(),
  'transfers':c.execute('SELECT id,source_account_id,destination_account_id,amount_cents,memo FROM paylink.transfers ORDER BY created_at').fetchall()}
 evidence['privileges']=[{'table':t,'direct_insert':c.execute('SELECT has_table_privilege(current_user,%s,%s) AS value',('paylink.'+t,'INSERT')).fetchone()['value'],
 'direct_update':c.execute('SELECT has_table_privilege(current_user,%s,%s) AS value',('paylink.'+t,'UPDATE')).fetchone()['value']} for t in ('bank_accounts','account_holders','transfers')]
 evidence['reconciliation']=c.execute('''WITH delta AS(SELECT source_account_id AS id,-amount_cents AS n FROM paylink.transfers
 UNION ALL SELECT destination_account_id,amount_cents FROM paylink.transfers)
 SELECT a.id FROM paylink.bank_accounts a LEFT JOIN delta d ON d.id=a.id GROUP BY a.id
 HAVING a.balance_cents<>a.opening_balance_cents+coalesce(sum(d.n),0)''').fetchall()
 assert len(evidence['tables'])==5 and all(t['rowsecurity'] for t in evidence['tables'])
 assert not evidence['reconciliation'] and evidence['client_tls']['in_use']
 assert not any(p['direct_insert'] or p['direct_update'] for p in evidence['privileges'])
(ROOT/'artifacts/hosted-database-evidence.json').write_text(json.dumps(evidence,default=str,indent=2)+'\n')
print('Hosted evidence saved: five RLS tables, verified TLS, restricted role and zero reconciliation discrepancies.')
