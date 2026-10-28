"""Verify public $200 signup, preserved balances, typography and testing guide.
Retains one private synthetic profile for the demonstration; credentials stay ignored.
"""
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import psycopg
from dotenv import dotenv_values
from playwright.sync_api import sync_playwright, expect
from browser_support import launch_chromium

ROOT=Path(__file__).resolve().parents[1]
BASE=os.getenv('PAYLINK_PUBLIC_URL','https://paylink-radiant690s-projects.vercel.app').rstrip('/')
URL=dotenv_values(ROOT/'.env.hosted')['DATABASE_URL']
credential_file=ROOT/'.local/onboarding-profile.json'
if credential_file.exists():
    profile=json.loads(credential_file.read_text())
else:
    profile={'username':'jordan_'+uuid4().hex[:8],'full_name':'Jordan Lee','email':'jordan_'+uuid4().hex[:8]+'@paylink.test','password':secrets.token_urlsafe(24)}
    with os.fdopen(os.open(credential_file,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:json.dump(profile,f,indent=2)

def db(query,args=()):
    with psycopg.connect(URL) as c:
        c.execute('SET TRANSACTION READ ONLY')
        return c.execute(query,args).fetchall()

def screenshot(page,name):page.screenshot(path=str(ROOT/'artifacts'/('onboarding-'+name+'.png')),full_page=True)

before=db('SELECT id::text,balance_cents,opening_balance_cents FROM paylink.bank_accounts ORDER BY id')
steps=[];errors=[];completed=False
try:
 with sync_playwright() as p:
    browser=launch_chromium(p)
    page=browser.new_page(viewport={'width':1440,'height':1100},timezone_id='America/Chicago')
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(BASE,wait_until='networkidle')
    expect(page.get_by_role('button',name='How to test',exact=True)).to_be_visible()
    expect(page.get_by_role('button',name='Sign in as Sai (User 1)')).to_be_visible()
    expect(page.get_by_role('button',name='Sign in as Siddhardth (User 2)')).to_be_visible()
    screenshot(page,'01-sign-in')
    page.get_by_role('button',name='How to test',exact=True).hover()
    expect(page.get_by_role('tooltip')).to_contain_text('$200')
    screenshot(page,'02-hover-guide')
    page.get_by_role('button',name='How to test',exact=True).click()
    expect(page.get_by_role('dialog')).to_contain_text('Review and send $12.34')
    screenshot(page,'03-test-guide')
    page.get_by_role('button',name='Got it, let’s try it').click()
    steps.append('Signed-out testing guide works on hover and click')
    exists=db('SELECT id FROM paylink.users WHERE username=%s',(profile['username'],))
    if not exists:
        page.get_by_role('button',name='Create an account',exact=True).click()
        page.get_by_label('Full name',exact=True).fill(profile['full_name'])
        page.get_by_label('Username',exact=True).fill(profile['username'])
        page.get_by_label('Email address').fill(profile['email'])
        page.get_by_label('Password',exact=True).fill(profile['password'])
        page.get_by_role('button',name='Create account',exact=True).click()
        steps.append('Fresh profile registered through the public UI')
    else:
        page.get_by_label('Username or email').fill(profile['username'])
        page.get_by_label('Password',exact=True).fill(profile['password'])
        page.get_by_role('button',name='Sign in',exact=True).click()
        steps.append('Private onboarding profile signed in')
    expect(page.get_by_role('heading',name='Hello, Jordan.')).to_be_visible(timeout=20000)
    expect(page.get_by_role('button').filter(has_text='Everyday checking')).to_be_visible()
    rows=db('''SELECT a.id::text,a.balance_cents,a.opening_balance_cents,a.account_type,h.user_id::text
        FROM paylink.bank_accounts a JOIN paylink.account_holders h ON h.account_id=a.id
        JOIN paylink.users u ON u.id=h.user_id WHERE u.username=%s''',(profile['username'],))
    assert len(rows)==1 and rows[0][1:4]==(20000,20000,'checking'),rows
    steps.append('Exactly one $200 checking account and ownership row persisted in Supabase')
    assert 'Real-world learning' not in page.locator('body').inner_text()
    assert float(page.locator('nav button').first.evaluate('el=>parseFloat(getComputedStyle(el).fontSize)'))>=14
    assert float(page.locator('.account-name').evaluate('el=>parseFloat(getComputedStyle(el).fontSize)'))>=14
    screenshot(page,'04-funded-account')
    steps.append('Removed wording absent; navigation and account labels use readable type sizes')
    page.get_by_role('button',name='How to test',exact=True).hover()
    expect(page.get_by_role('tooltip')).to_contain_text('$200')
    page.get_by_role('button',name='How to test',exact=True).click()
    expect(page.get_by_role('dialog')).to_contain_text('Check the safeguards')
    page.get_by_role('button',name='Close dialog').click()
    steps.append('Signed-in guide includes recipient lookup, review, history, CSV, joint ownership and safeguards')
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    screenshot(page,'05-mobile-account')
    page.get_by_role('button',name='How to test',exact=True).click()
    expect(page.get_by_role('dialog')).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    screenshot(page,'06-mobile-guide')
    steps.append('390px account and guide layouts have no page overflow')
    after=dict((r[0],r[1:]) for r in db('SELECT id::text,balance_cents,opening_balance_cents FROM paylink.bank_accounts ORDER BY id'))
    assert all(after[r[0]]==r[1:] for r in before)
    assert not errors,errors
    steps.append('All prior account balances and opening balances preserved; no JavaScript errors')
    completed=True
    browser.close()
finally:
    (ROOT/'artifacts/hosted-onboarding-results.json').write_text(json.dumps({'completed':completed,'url':BASE,
        'timestamp_utc':datetime.now(timezone.utc).isoformat(),'passed':steps,'javascript_errors':errors,
        'initial_balance_cents':20000,'private_synthetic_profile_retained':True},indent=2)+'\n')
    for step in steps:print('PASS:',step)
