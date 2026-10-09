import os as _os
ROOT = _os.environ.get('PAC_ROOT') or _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, asyncio
from playwright.async_api import async_playwright
async def main(names):
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/opt/pw-browsers/chromium', args=['--allow-file-access-from-files'])
        for n in names:
            pg = await b.new_page(); await pg.goto(f'file://{ROOT}/pac-print/out/{n}.html'); await pg.wait_for_timeout(600)
            r = await pg.evaluate('''()=>{const bad=[];document.querySelectorAll('.card').forEach(c=>{const co=c.querySelector('.cost');const pw=c.querySelector('.pw');if(!co||!pw)return;const t=co.getBoundingClientRect().top;let m=0;pw.querySelectorAll('.tx, .dish, .dish *').forEach(e=>{m=Math.max(m,e.getBoundingClientRect().bottom)});const nm=false;if(m>t+2||c.scrollHeight>c.clientHeight+1)bad.push([c.querySelector('h1').textContent,Math.round((m-t)*100)/100,nm])});return [document.querySelectorAll('.card').length,bad]}''')
            print(n, r[0], len(r[1]), r[1][:25])
        await b.close()
asyncio.run(main(sys.argv[1:]))
