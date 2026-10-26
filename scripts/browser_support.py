"""Use system Chromium in cloud, or Playwright's installed browser on macOS."""
import os
from pathlib import Path


def launch_chromium(playwright):
    executable = os.getenv('CHROMIUM_EXECUTABLE_PATH')
    if not executable and Path('/usr/bin/chromium').is_file():
        executable = '/usr/bin/chromium'
    options = {'executable_path': executable} if executable else {}
    if executable == '/usr/bin/chromium':
        options['args'] = ['--no-sandbox']
    return playwright.chromium.launch(**options)
