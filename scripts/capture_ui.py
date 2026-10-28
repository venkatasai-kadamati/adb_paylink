from pathlib import Path
from browser_support import launch_chromium
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser=launch_chromium(p)
    page=browser.new_page(viewport={'width':1440,'height':1120},device_scale_factor=1,timezone_id='America/Chicago')
    page.goto('http://localhost:3000')
    expect(page.get_by_role('heading',name='Welcome back.')).to_be_visible()
    page.screenshot(path=str(ROOT/'artifacts/01-sign-in.png'),full_page=True)
    page.get_by_role('button',name='Sign in as Sai (User 1)').click()
    expect(page.get_by_role('heading',name='Hello, Sai.')).to_be_visible()
    expect(page.get_by_text('Everyday checking',exact=True)).to_be_visible()
    page.screenshot(path=str(ROOT/'artifacts/02-overview.png'),full_page=True)
    page.get_by_role('button',name='Insights',exact=True).click()
    expect(page.get_by_role('heading',name='A week in motion')).to_be_visible()
    page.screenshot(path=str(ROOT/'artifacts/03-insights.png'),full_page=True)
    browser.close()
print('Captured live sign-in, overview, and insights screenshots.')
