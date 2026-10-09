import os as _os
ROOT = _os.environ.get('PAC_ROOT') or _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/opt/pw-browsers/chromium', args=['--allow-file-access-from-files'])
        pg = await b.new_page(); await pg.goto(f'file://{ROOT}/pac-print/out/PAC_items.html'); await pg.wait_for_timeout(800)
        r = await pg.evaluate('''()=>{const bad=[];document.querySelectorAll('.card').forEach(c=>{const co=c.querySelector('.cost');const tx=c.querySelector('.itx .tx');if(!co||!tx)return;const t=co.getBoundingClientRect().top;const m=tx.getBoundingClientRect().bottom;if(m>t-2||c.scrollHeight>c.clientHeight+1)bad.push([c.querySelector('h1').textContent,Math.round((m-t)*10)/10])});return [document.querySelectorAll('.card').length,bad]}''')
        print(r[0], r[1]); await b.close()
asyncio.run(main())
