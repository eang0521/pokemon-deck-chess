#!/usr/bin/env python3
"""PAC sync: regenerate the website data, the print files and the rulebook from ONE set of sources.

    python tools/sync.py                 everything (data, site, print, rulebook)
    python tools/sync.py data site       only the named steps
    python tools/sync.py print --print-out "D:/path/to/print folder"

Steps:  items   items workbook + items_core.json            (pac-sim/build_items.py)
        cards   pick-card workbook + pool_cards.json         (pac-sim/export_extra.py)
        data    website data (build/data.js, data.json)       (pac-digital/export_data.py)
        site    copy data.js into the website (js/data.js)
        print   card / item / reference PDFs                  (pac-print/build*.py + render.py)
        rulebook  Draft Rulebook PDF                         (rulebook/build_rulebook.py)
        check   JS-vs-Python engine parity (needs node)       (optional, not in 'all')
Sources of truth: pac-sim/items.py, pac-sim/engine.py + duel.py + itemfx.py (rules/balance),
pac-core-cards-draft.xlsx (core card text), pac-data/ (PAC data + tweaks), rulebook/rules.md (rules text).
"""
import argparse, glob, os, shutil, subprocess, sys, time
TOOLS = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(TOOLS)                        # website = repo root (index.html, js/, css/)
env = dict(os.environ, PAC_ROOT=TOOLS)
ap = argparse.ArgumentParser()
ap.add_argument('steps', nargs='*')
ap.add_argument('--print-out', help='folder to copy the finished print PDFs/xlsx into')
a = ap.parse_args()
ALL = ['items', 'cards', 'data', 'site', 'print', 'rulebook']
steps = a.steps or ALL
for s in steps:
    if s not in ALL + ['check']: sys.exit('unknown step ' + s)
def py(script, *args, cwd=None):
    d = os.path.join(TOOLS, os.path.dirname(script))
    print('>>', script, *args, flush=True)
    subprocess.run([sys.executable, os.path.basename(script), *args], cwd=cwd or d, env=env, check=True)
if not os.path.isdir(os.path.join(TOOLS, 'keldaancommunity', 'pokemonautochess', 'app')) and any(s in steps for s in ('items', 'cards', 'data', 'print')):
    sys.exit('Run  python tools/setup.py  first (fetches the PAC art + text).')
PRINT = ['PAC_core', 'PAC_items', 'PAC_unique', 'PAC_legendary', 'PAC_additional', 'PAC_hatch', 'PAC_reference', 'PAC_synergies']
t0 = time.time()
if 'items' in steps: py('pac-sim/build_items.py')
if 'cards' in steps: py('pac-sim/export_extra.py')
if 'data' in steps: py('pac-digital/export_data.py')
if 'site' in steps:
    for src, dst in (('pac-digital/build/data.js', 'js/data.js'),):
        os.makedirs(os.path.dirname(os.path.join(SITE, dst)), exist_ok=True)
        shutil.copy(os.path.join(TOOLS, src), os.path.join(SITE, dst)); print('site <-', dst)
if 'print' in steps:
    py('pac-print/build.py', 'core', 'items'); py('pac-print/build3.py'); py('pac-print/build2.py')
    names = [n + s for n in PRINT for s in ('', '_BACKS')]
    py('pac-print/render.py', *names)
    out = a.print_out
    if out:
        os.makedirs(out, exist_ok=True)
        for n in names: shutil.copy(os.path.join(TOOLS, 'pac-print/out', n + '.pdf'), out)
        for x in ('pac-items-core.xlsx', 'pac-pick-cards-draft.xlsx'): shutil.copy(os.path.join(TOOLS, x), out)
        print('print files copied to', out)
if 'rulebook' in steps:
    py('rulebook/build_rulebook.py')
    if a.print_out:
        for f in glob.glob(os.path.join(TOOLS, 'rulebook', '*.pdf')): shutil.copy(f, a.print_out)
if 'check' in steps:
    py('pac-digital/parity_gen.py')
    subprocess.run(['node', os.path.join(TOOLS, 'pac-digital/parity_run.js'), '200'], env=env, check=True)
print(f'sync done in {time.time()-t0:.0f}s: {", ".join(steps)}')
