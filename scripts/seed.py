import os
"""Opt-in, synthetic local demo data. Repeatable: existing demo data is preserved."""
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid5, NAMESPACE_URL
from dotenv import dotenv_values
from argon2 import PasswordHasher
import psycopg
ROOT=Path(__file__).resolve().parents[1]
config={**dotenv_values(ROOT/'.env'), **{k:v for k,v in os.environ.items() if k in ('ADMIN_DATABASE_URL','DATABASE_URL')}}
if '--demo' not in sys.argv: raise SystemExit('Pass --demo to explicitly enable published, local-only demo credentials.')
from urllib.parse import urlparse
if urlparse(config['ADMIN_DATABASE_URL']).hostname not in ('127.0.0.1','localhost'):
    raise SystemExit('Refusing to seed public demo passwords into a hosted database.')
uid=lambda name: uuid5(NAMESPACE_URL,'paylink.demo/'+name)
ph=PasswordHasher()
with psycopg.connect(config['ADMIN_DATABASE_URL']) as c:
    for name,route in [('Meridian Bank','110000001'),('Northstar Credit Union','110000002'),('Pacific Trust','110000003')]:
        c.execute('INSERT INTO paylink.banks(id,routing_number,name) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING',(uid(name),route,name))
    for username,name,phone in [('sai','Sai Kadamati','+15550101001'),('siddhardth','Siddhardth','+15550101002'),('maya','Maya Chen','+15550101003'),('alex','Alex Morgan','+15550101004')]:
        c.execute('INSERT INTO paylink.users(id,username,email,phone,full_name,password_hash) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
          (uid(username),username,username+'@paylink.test',phone,name,ph.hash('PaylinkDemo!2026')))
    specs=[('sai-checking','sai','Meridian Bank','Everyday checking','checking',245000,'100000004821'),
           ('sai-savings','sai','Northstar Credit Union','Rainy day fund','savings',580000,'100000009304'),
           ('joint','sai','Pacific Trust','Shared expenses','checking',125000,'100000007106'),
           ('sid-checking','siddhardth','Meridian Bank','Everyday checking','checking',180000,'100000003209'),
           ('maya-checking','maya','Northstar Credit Union','Maya checking','checking',120000,'100000002081'),
           ('alex-checking','alex','Pacific Trust','Alex checking','checking',100000,'100000008801')]
    for key,owner,bank,label,kind,balance,number in specs:
        c.execute('''INSERT INTO paylink.bank_accounts(id,bank_id,account_number,account_type,label,balance_cents,opening_balance_cents)
          VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING''',(uid(key),uid(bank),number,kind,label,balance,balance))
        c.execute('INSERT INTO paylink.account_holders(user_id,account_id) VALUES(%s,%s) ON CONFLICT DO NOTHING',(uid(owner),uid(key)))
    c.execute('INSERT INTO paylink.account_holders(user_id,account_id) VALUES(%s,%s) ON CONFLICT DO NOTHING',(uid('siddhardth'),uid('joint')))
    history=[('maya-checking','sai-checking','maya',6500,'Dinner, on me',0),
             ('sai-checking','sid-checking','sai',4200,'Coffee & catch-up',1),
             ('alex-checking','sai-checking','alex',12500,'Weekend trip',2),
             ('sai-checking','joint','sai',18000,'Shared groceries',3),
             ('sai-checking','maya-checking','sai',2800,'Lunch at the market',4),
             ('sid-checking','sai-checking','siddhardth',8500,'Utilities split',5),
             ('sai-checking','sai-savings','sai',25000,'A little for later',6)]
    for i,(source,dest,actor,amount,memo,days) in enumerate(history):
        key=uid('seed-transfer-'+str(i))
        result=c.execute('SELECT id,created_at FROM paylink.transfers WHERE initiated_by=%s AND idempotency_key=%s',(uid(actor),key)).fetchone()
        if not result:
            row=c.execute('SELECT id FROM paylink.execute_transfer(%s,%s,%s,%s,%s,%s)',(uid(actor),uid(source),uid(dest),amount,memo,key)).fetchone()
            c.execute('UPDATE paylink.transfers SET created_at=%s WHERE id=%s',
                (datetime.now(timezone.utc)-timedelta(days=days,hours=2),row[0]))
print('Synthetic demo seeded. Local usernames: sai / siddhardth. Password documented in README.')
