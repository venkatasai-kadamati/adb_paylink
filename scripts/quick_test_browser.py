"""Verify both public synthetic-profile shortcuts without changing account data."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from browser_support import launch_chromium

ROOT=Path(__file__).resolve().parents[1]
BASE=os.getenv('PAYLINK_PUBLIC_URL','https://paylink-radiant690s-projects.vercel.app').rstrip('/')
steps=[]; errors=[]; completed=False
try:
 with sync_playwright() as p:
    browser=launch_chromium(p)
    contexts=[browser.new_context(viewport={'width':1440,'height':1100}) for _ in range(2)]
    pages=[c.new_page() for c in contexts]
    for page in pages:page.on('pageerror',lambda e:errors.append(str(e)))
    page=pages[0];page.goto(BASE,wait_until='networkidle')
    expect(page.get_by_text('QUICK TEST SIGN-IN',exact=True)).to_be_visible()
    for name in ['Sign in as Sai (User 1)','Sign in as Siddhardth (User 2)']:
        expect(page.get_by_role('button',name=name,exact=True)).to_be_visible()
    page.screenshot(path=str(ROOT/'artifacts/quick-test-01-login.png'),full_page=True)
    steps.append('Login page offers User 1 Sai and User 2 Siddhardth before the regular form')
    assert page.request.get(BASE+'/api/accounts').status==401
    assert page.request.post(BASE+'/api/auth/demo',data={'username':'another_user'}).status==422
    assert page.request.post(BASE+'/api/auth/demo',data={'username':'sai'},headers={'Origin':'https://evil.example'}).status==403
    steps.append('Other usernames rejected; unauthenticated access and cross-origin requests blocked')
    snapshots=[]
    for page,username,name,label in zip(pages,['sai','siddhardth'],['Sai','Siddhardth'],['User 1','User 2']):
        page.goto(BASE,wait_until='networkidle')
        with page.expect_response(lambda r:r.url.endswith('/api/auth/demo')) as response:
            page.get_by_role('button',name=f'Sign in as {name} ({label})',exact=True).click()
        assert response.value.status==200
        assert response.value.request.post_data_json=={'username':username}
        expect(page.get_by_role('heading',name=f'Hello, {name}.')).to_be_visible(timeout=30000)
        assert page.request.get(BASE+'/api/me').json()['username']==username
        cookie=next(c for c in page.context.cookies() if c['name']=='paylink_session')
        assert cookie['httpOnly'] and cookie['sameSite']=='Strict'
        if BASE.startswith('https:'):assert cookie['secure']
        snapshots.append(page.request.get(BASE+'/api/accounts').json())
        page.reload()
        expect(page.get_by_role('heading',name=f'Hello, {name}.')).to_be_visible()
        page.screenshot(path=str(ROOT/f'artifacts/quick-test-02-{username}.png'),full_page=True)
        steps.append(f'{label} {name} opens with one click and no password; signed session survives reload')
    assert pages[0].request.get(BASE+'/api/me').json()['username']=='sai'
    assert pages[1].request.get(BASE+'/api/me').json()['username']=='siddhardth'
    assert pages[0].request.get(BASE+'/api/recipients?q=siddhardth').json()[0]['username']=='siddhardth'
    assert pages[1].request.get(BASE+'/api/recipients?q=sai').json()[0]['username']=='sai'
    steps.append('Isolated sessions retain the correct profile and can find each other as recipients')
    for page,accounts in zip(pages,snapshots):assert page.request.get(BASE+'/api/accounts').json()==accounts
    page=pages[0];page.get_by_role('button',name='Sign out',exact=True).click()
    expect(page.get_by_role('heading',name='Welcome back.')).to_be_visible()
    assert page.request.get(BASE+'/api/me').status==401
    assert pages[1].request.get(BASE+'/api/me').json()['username']=='siddhardth'
    assert page.request.post(BASE+'/api/auth/login',data={'username':'sai','password':'wrong'}).status==401
    steps.append('Sign-out stays isolated; normal password validation and account balances preserved')
    page.set_viewport_size({'width':390,'height':844})
    expect(page.get_by_role('button',name='Sign in as Sai (User 1)')).to_be_visible()
    expect(page.get_by_role('button',name='Sign in as Siddhardth (User 2)')).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=str(ROOT/'artifacts/quick-test-03-mobile.png'),full_page=True)
    assert not errors,errors
    steps.append('390px mobile login has no overflow; no browser JavaScript errors')
    completed=True
    browser.close()
finally:
    (ROOT/'artifacts/quick-test-browser-results.json').write_text(json.dumps({
        'completed':completed,'url':BASE,'timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'passed':steps,'javascript_errors':errors,'account_data_unchanged':completed},indent=2)+'\n')
    for step in steps:print('PASS:',step)
