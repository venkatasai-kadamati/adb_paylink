"""Export reviewable Markdown into standalone HTML, PDF, and DOCX."""
from pathlib import Path
from browser_support import launch_chromium
import subprocess
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser=launch_chromium(p)
    for name in ['midterm-report','submission_guide','database-design']:
        docs=ROOT/'docs'
        subprocess.run(['pandoc',name+'.md','-s','--embed-resources','--css','report.css','-o',name+'.html'],cwd=docs,check=True)
        subprocess.run(['pandoc',name+'.md','-o',name+'.docx'],cwd=docs,check=True)
        page=browser.new_page()
        page.set_content((docs/(name+'.html')).read_text(),wait_until='load')
        page.pdf(path=str(docs/(name+'.pdf')),format='A4',print_background=True,display_header_footer=True,
                 header_template='<span></span>',footer_template='<div style="font-size:8px;color:#9aa8b6;text-align:center;width:100%;font-family:Arial">PayLink · CS 5600 · <span class="pageNumber"></span> / <span class="totalPages"></span></div>')
        page.close()
        print('Exported:',name,'(HTML, PDF, DOCX)')
    browser.close()
