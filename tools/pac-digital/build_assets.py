import os as _os
ROOT = _os.environ.get('PAC_ROOT') or _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import json, os, re, shutil
from PIL import Image
A=f'{ROOT}/keldaancommunity/pokemonautochess/app/public/src/assets'
OUT=f'{ROOT}/pac-digital/dist/assets'
os.makedirs(OUT+'/p',exist_ok=True); os.makedirs(OUT+'/i',exist_ok=True); os.makedirs(OUT+'/t',exist_ok=True); os.makedirs(OUT+'/s',exist_ok=True)
d=json.load(open('build/data.json'))
def portrait(dex):
    for c in (f'{A}/portraits/{dex}/Normal.png', f'{A}/portraits/{dex.replace("-","/")}/Normal.png', f'{A}/portraits/{dex.split("-")[0]}/Normal.png'):
        if os.path.exists(c): return c
    return None
miss=[];n=0
for dex in sorted({c['dex'] for c in d['cards']}):
    p=portrait(dex)
    if not p: miss.append(dex); continue
    im=Image.open(p).convert('RGBA')
    im.save(f'{OUT}/p/{dex}.png',optimize=True); n+=1
print('portraits',n,'missing',miss[:10],len(miss))
ITEMDIR=f'{A}/item{{tps}}'
files={re.sub(r'[^A-Z0-9]','',f[:-4].upper()):f for f in os.listdir(ITEMDIR) if f.endswith('.png')}
def item_img(name,key):
    k=re.sub(r'[^A-Z0-9]','',name.upper())
    for kk in (k,re.sub(r'[^A-Z0-9]','',key)):
        if kk in files: return files[kk]
    for kk,f in files.items():
        if kk.startswith(k[:8]): return f
    return None
im_miss=[];m=0
for key,it in d['items'].items():
    f=item_img(it['name'],key)
    if not f: im_miss.append(it['name']); continue
    im=Image.open(f'{ITEMDIR}/{f}').convert('RGBA'); im.save(f'{OUT}/i/{key}.png',optimize=True); m+=1
print('items',m,'missing',im_miss)
for f in os.listdir(f'{A}/types'): shutil.copy(f'{A}/types/{f}',f'{OUT}/t/{f}')
for nme in ['HP','ATK','DEF','SPE_DEF','SPEED','PP','AP','SHIELD','CRIT_CHANCE','XP']:
    shutil.copy(f'{A}/icons/{nme}.png',f'{OUT}/s/{nme}.png')
shutil.copy(f'{ROOT}/pac-print/assets/COIN.svg',f'{OUT}/s/COIN.svg')
os.system(f'du -sh {OUT}/*')
