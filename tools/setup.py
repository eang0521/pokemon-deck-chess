#!/usr/bin/env python3
"""One-time setup: fetch the open-source Pokemon Auto Chess repo (only the folders the build needs).

Needs git, Python 3 with openpyxl + pillow + playwright (pip install openpyxl pillow playwright; playwright install chromium).
"""
import os, subprocess, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(ROOT, 'keldaancommunity', 'pokemonautochess')
URL = 'https://github.com/keldaanCommunity/pokemonautochess'
PATHS = ['app/public/dist/client/locales/en', 'app/public/src/assets/icons', 'app/public/src/assets/item{tps}',
         'app/public/src/assets/portraits', 'app/public/src/assets/types', 'app/public/src/assets/ui']
def run(*a, cwd=None): subprocess.run(a, cwd=cwd, check=True)
if os.path.isdir(os.path.join(DEST, '.git')) or os.path.exists(os.path.join(DEST, 'app')):
    print('upstream already present:', DEST); sys.exit(0)
os.makedirs(os.path.dirname(DEST), exist_ok=True)
run('git', 'clone', '--depth', '1', '--filter=blob:none', '--sparse', URL, DEST)
run('git', 'sparse-checkout', 'set', '--no-cone', *['/' + p + '/' for p in PATHS], cwd=DEST)
print('done:', DEST)
