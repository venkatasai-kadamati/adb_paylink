"""Public-app acceptance using private synthetic profiles and read-only DB assertions.

Creates/retains clearly synthetic recording data. Never invokes local seed, admin
fixtures, or the query-plan benchmark against hosted PostgreSQL.
"""
import csv
import io
import json
import os
import platform
import secrets
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
from dotenv import dotenv_values
from playwright.sync_api import sync_playwright, expect
from browser_support import launch_chromium

ROOT=Path(__file__).resolve().parents[1]
BASE=os.getenv('PAYLINK_PUBLIC_URL','https://paylink-radiant690s-projects.vercel.app').rstrip('/')
C=dotenv_values(ROOT/'.env.hosted')
if urlparse(C['DATABASE_URL']).hostname in ('localhost','127.0.0.1'):
    raise SystemExit('Hosted acceptance requires the configured hosted database.')
credential_file=ROOT/'.local/recording-users.json'
if not credential_file.exists():
    profiles=[{'username':name,'full_name':full,'email':name+'@paylink.test','password':secrets.token_urlsafe(24)}
              for name,full in [('sai','Sai Kadamati'),('siddhardth','Siddhardth')]]
    with os.fdopen(os.open(credential_file,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:
        json.dump(profiles,f,indent=2)
profiles=json.loads(credential_file.read_text())
steps=[]; errors=[]; evidence={'completed':False,'url':BASE,'platform':platform.platform(),
 'timestamp_utc':datetime.now(timezone.utc).isoformat(),'database':'Supabase PostgreSQL 17.11',
 'project_ref':'wktoypofpksgbjwtadrn','synthetic_recording_data_retained':True}

def record(s):steps.append(s);print('PASS:',s,flush=True)
def db(query,args=()):
    with psycopg.connect(C['DATABASE_URL']) as c:
        c.execute('SET TRANSACTION READ ONLY')
        return c.execute(query,args).fetchall()
def screenshot(page,name):page.screenshot(path=str(ROOT/'artifacts'/('hosted-'+name+'.png')),full_page=True)
def login(page,profile):
    page.goto(BASE,wait_until='networkidle')
    expect(page.get_by_role('heading',name='Welcome back.')).to_be_visible()
    expect(page.get_by_role('button',name='Sign in as Sai (User 1)')).to_be_visible()
    expect(page.get_by_role('button',name='Sign in as Siddhardth (User 2)')).to_be_visible()
    screenshot(page,'01-sign-in')
    exists=db('SELECT id FROM paylink.users WHERE username=%s',(profile['username'],))
    if not exists:
        page.get_by_role('button',name='Create an account',exact=True).click()
        page.get_by_label('Full name',exact=True).fill(profile['full_name'])
        page.get_by_label('Username',exact=True).fill(profile['username'])
        page.get_by_label('Email address').fill(profile['email'])
        page.get_by_label('Password',exact=True).fill(profile['password'])
        page.get_by_role('button',name='Create account',exact=True).click()
    else:
        page.get_by_label('Username or email').fill(profile['username'])
        page.get_by_label('Password',exact=True).fill(profile['password'])
        page.get_by_role('button',name='Sign in',exact=True).click()
    expect(page.get_by_role('heading',name='Hello, '+profile['full_name'].split()[0]+'.')).to_be_visible(timeout=20000)
    expect(page.get_by_text('Getting your workspace ready…')).not_to_be_visible()

def account(page,username,label,kind='checking'):
    rows=db('''SELECT a.id FROM paylink.bank_accounts a JOIN paylink.account_holders h ON h.account_id=a.id
        JOIN paylink.users u ON u.id=h.user_id WHERE u.username=%s AND a.label=%s''',(username,label))
    if rows:return str(rows[0][0])
    page.get_by_role('button',name='Link a bank account').click()
    dialog=page.get_by_role('dialog')
    dialog.locator('select[name=bank_id]').select_option(label='Meridian Bank')
    dialog.locator('select[name=account_type]').select_option(kind)
    dialog.get_by_label('Give it a name').fill(label)
    dialog.get_by_role('button',name='Create simulated account').click()
    expect(dialog).not_to_be_visible(timeout=15000)
    expect(page.get_by_role('button').filter(has_text=label)).to_be_visible()
    return str(db('''SELECT a.id FROM paylink.bank_accounts a JOIN paylink.account_holders h ON h.account_id=a.id
        JOIN paylink.users u ON u.id=h.user_id WHERE u.username=%s AND a.label=%s''',(username,label))[0][0])

try:
 with sync_playwright() as p:
    browser=launch_chromium(p)
    contexts=[browser.new_context(viewport={'width':1440,'height':1100},timezone_id='America/Chicago') for _ in profiles]
    pages=[c.new_page() for c in contexts]
    for page in pages:page.on('pageerror',lambda e:errors.append(str(e)))
    sai,sid=pages
    for page,profile in zip(pages,profiles):login(page,profile)
    record('Public registration/sign-in with private passwords; public quick-test profiles available')
    source=account(sai,'sai','Everyday checking')
    savings=account(sai,'sai','Rainy day fund','savings')
    shared=account(sai,'sai','Shared expenses')
    dest=account(sid,'siddhardth','Everyday checking')
    record('Simulated account creation persisted in Supabase')
    sai.get_by_role('button',name='Accounts',exact=True).click()
    sai.get_by_role('button',name='Add joint owner').click()
    dialog=sai.get_by_role('dialog')
    dialog.get_by_label('Account to share').select_option(shared)
    dialog.get_by_label("New owner's username").fill('siddhardth')
    dialog.get_by_role('button',name='Confirm joint owner').click()
    expect(dialog).not_to_be_visible(timeout=15000)
    assert db('SELECT count(*) FROM paylink.account_holders WHERE account_id=%s',(shared,))[0][0]==2
    sid.reload();expect(sid.get_by_role('button').filter(has_text='Shared expenses')).to_be_visible()
    record('Joint ownership created in public UI and visible in the second isolated session')
    sai.get_by_role('button',name='Overview',exact=True).click()
    screenshot(sai,'02-overview')
    before=dict(db('SELECT id::text,balance_cents FROM paylink.bank_accounts WHERE id IN(%s,%s)',(source,dest)))
    sai.get_by_role('button',name='Send money',exact=True).click()
    dialog=sai.get_by_role('dialog')
    dialog.get_by_placeholder('e.g. siddhardth').fill('siddhardth@paylink.test')
    dialog.get_by_role('button',name='Find',exact=True).click()
    last4=db('SELECT right(account_number,4) FROM paylink.bank_accounts WHERE id=%s',(dest,))[0][0]
    dialog.get_by_role('button',name='Siddhardth @siddhardth · Meridian Bank ••'+last4).click()
    dialog.get_by_role('button',name='Continue',exact=True).click()
    dialog.get_by_label('From account').select_option(source)
    dialog.get_by_role('textbox',name='Amount',exact=True).fill('999999')
    dialog.get_by_role('button',name='Review transfer').click()
    expect(dialog.get_by_role('alert')).to_contain_text('does not have enough funds')
    dialog.get_by_role('textbox',name='Amount',exact=True).fill('12.34')
    memo='Hosted acceptance '+uuid4().hex[:8]
    dialog.get_by_placeholder('A little note goes a long way').fill(memo)
    dialog.get_by_role('button',name='Review transfer').click()
    expect(dialog.get_by_role('heading',name='Review your transfer')).to_be_visible()
    screenshot(sai,'03-review')
    with sai.expect_request(lambda r:r.url.endswith('/api/transfers') and r.method=='POST') as request:
        dialog.get_by_role('button',name='Confirm & send').click()
    payload=request.value.post_data_json
    expect(dialog.get_by_role('heading',name='Transfer completed')).to_be_visible(timeout=20000)
    row=db('SELECT id::text,amount_cents FROM paylink.transfers WHERE idempotency_key=%s',(payload['idempotency_key'],))[0]
    assert row[1]==1234
    after=dict(db('SELECT id::text,balance_cents FROM paylink.bank_accounts WHERE id IN(%s,%s)',(source,dest)))
    assert after[source]==before[source]-1234 and after[dest]==before[dest]+1234
    screenshot(sai,'04-receipt')
    record('Public UI transfer committed exactly once: sender -1234, recipient +1234 cents in Supabase')
    for _ in range(2):
        retry=contexts[0].request.post(BASE+'/api/transfers',data=payload,headers={'Origin':BASE})
        assert retry.status==201 and retry.json()['id']==row[0]
    conflict=contexts[0].request.post(BASE+'/api/transfers',data={**payload,'amount_cents':1235},headers={'Origin':BASE})
    assert conflict.status==409
    nonowner=contexts[1].request.post(BASE+'/api/transfers',data={**payload,'idempotency_key':str(uuid4())},headers={'Origin':BASE})
    assert nonowner.status==409
    insufficient=contexts[0].request.post(BASE+'/api/transfers',data={**payload,'amount_cents':100000000,'idempotency_key':str(uuid4())},headers={'Origin':BASE})
    assert insufficient.status==409
    assert dict(db('SELECT id::text,balance_cents FROM paylink.bank_accounts WHERE id IN(%s,%s)',(source,dest)))==after
    record('Hosted identical retries return one ID; changed payload, non-owner and insufficient funds rejected without balance changes')
    evidence['representative_transfer']={'id':row[0],'amount_cents':1234,'source_account_id':source,'destination_account_id':dest,'before_cents':before,'after_cents':after}
    dialog.get_by_role('button',name='Back to overview').click()
    sai.reload();sai.get_by_role('button',name='Activity',exact=True).click()
    sai.get_by_role('textbox',name='Search activity').fill(memo)
    sai.get_by_role('button').filter(has_text=memo).click()
    expect(sai.get_by_role('dialog')).to_contain_text(row[0])
    screenshot(sai,'05-details')
    sai.get_by_role('button',name='Close dialog').click()
    with sai.expect_download() as download:sai.get_by_role('link',name='Export CSV').click()
    assert any(r['id']==row[0] for r in csv.DictReader(io.StringIO(Path(download.value.path()).read_text())))
    sid.reload();sid.get_by_role('button',name='Activity',exact=True).click()
    sid.get_by_role('textbox',name='Search activity').fill(memo)
    expect(sid.get_by_role('button').filter(has_text=memo)).to_be_visible()
    screenshot(sid,'06-recipient')
    record('Reloaded history, exact transfer details, real CSV download and recipient receipt verified')
    sid.get_by_role('button',name='Overview',exact=True).click()
    sid.get_by_role('button',name='Move between accounts').click()
    dialog=sid.get_by_role('dialog');dialog.get_by_label('From account').select_option(shared)
    dialog.get_by_label('To account').select_option(dest)
    dialog.get_by_role('textbox',name='Amount',exact=True).fill('1.00')
    dialog.get_by_placeholder('A little note goes a long way').fill('Hosted joint-owner acceptance')
    dialog.get_by_role('button',name='Review transfer').click();dialog.get_by_role('button',name='Confirm & send').click()
    expect(dialog.get_by_role('heading',name='Transfer completed')).to_be_visible(timeout=20000)
    dialog.get_by_role('button',name='Back to overview').click()
    record('Second owner spends shared funds through the own-account transfer UI')
    sid.get_by_role('button',name='Insights',exact=True).click()
    expect(sid.get_by_role('heading',name='A week in motion')).to_be_visible()
    screenshot(sid,'07-insights')
    sid.set_viewport_size({'width':390,'height':844})
    sid.get_by_role('button',name='Toggle navigation').click();sid.get_by_role('button',name='Overview',exact=True).click()
    expect(sid.get_by_role('heading',name='Hello, Siddhardth.')).to_be_visible()
    assert sid.evaluate('document.documentElement.scrollWidth <= innerWidth')
    screenshot(sid,'08-mobile')
    record('Hosted insights and 390px mobile layout render without overflow')
    reconciliation=db('''WITH delta AS(SELECT source_account_id AS id,-amount_cents AS n FROM paylink.transfers
      UNION ALL SELECT destination_account_id,amount_cents FROM paylink.transfers)
      SELECT a.id FROM paylink.bank_accounts a LEFT JOIN delta d ON d.id=a.id GROUP BY a.id
      HAVING a.balance_cents<>a.opening_balance_cents+coalesce(sum(d.n),0)''')
    assert not reconciliation
    assert not errors,errors
    record('Hosted reconciliation: zero discrepancies; no browser JavaScript errors')
    evidence['reconciliation_discrepancies']=0
    evidence['completed']=True
    browser.close()
finally:
    evidence['passed']=steps;evidence['javascript_errors']=errors
    (ROOT/'artifacts/hosted-browser-results.json').write_text(json.dumps(evidence,indent=2)+'\n')
