import os as _os
ROOT = _os.environ.get('PAC_ROOT') or _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, asyncio
from playwright.async_api import async_playwright
async def main(names):
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path='/opt/pw-browsers/chromium', args=['--allow-file-access-from-files'])
        for n in names:
            pg = await b.new_page()
            await pg.goto(f'file://{ROOT}/pac-print/out/{n}.html')
            await pg.wait_for_timeout(800)
            await pg.pdf(path=f'{ROOT}/pac-print/out/{n}.pdf', width='8.5in', height='11in', print_background=True, margin=dict(top='0', bottom='0', left='0', right='0'), prefer_css_page_size=True)
            await pg.close()
        await b.close()
asyncio.run(main(sys.argv[1:]))
