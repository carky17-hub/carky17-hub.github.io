"""Optional Playwright checks for the two source modules using a deterministic DOM fixture."""
from pathlib import Path
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1]
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
 page.set_content('''<meta name="viewport" content="width=device-width,initial-scale=1"><main><form id="searchForm"><input id="query"></form><div id="searchSuggestions"></div><div id="searchStatus"></div><div class="nearby-bar"><button data-nearby aria-pressed="false">내 주변</button></div><select id="region"><option value="서울특별시">서울</option><option value="">전국</option></select><div id="cats"><button data-cat="카페" aria-pressed="true">카페</button></div><div id="cards"></div></main><div class="mobile-nav">옛 내비</div>''')
 page.add_style_tag(path=str(R/'site/tabbar.css'))
 page.evaluate('''()=>{window.clicks=0;document.querySelector('[data-nearby]').onclick=e=>{clicks++;e.target.setAttribute('aria-pressed','true')};window.widen=0;document.querySelector('#region').onchange=()=>widen++;}''')
 page.add_script_tag(path=str(R/'site/tabbar.js'))
 page.locator('#eg33-tabbar').wait_for()
 assert page.locator('#eg33-tabbar > *').count()==4
 assert not page.locator('.mobile-nav').is_visible()
 page.locator('[data-eg-tab=near]').click();assert page.evaluate('clicks')==1
 assert page.locator('[data-eg-tab=near]').get_attribute('aria-pressed')=='true'
 page.evaluate("document.body.classList.add('eg-map-full')");assert not page.locator('#eg33-tabbar').is_visible()
 page.evaluate("document.body.classList.remove('eg-map-full')")
 page.set_viewport_size({'width':768,'height':844});assert not page.locator('#eg33-tabbar').is_visible()
 page.set_viewport_size({'width':390,'height':844})
 page.evaluate('''()=>{window.EGSearch={norm:v=>String(v||'').trim(),decode:v=>v,suggest:()=>[]};window.fetch=async()=>({ok:true,json:async()=>({regions:[['서울 카페','/cafe/seoul/','서울특별시',null,null,'카페',30],['서울 식당','/restaurant/seoul/','서울특별시',null,null,'식당',20]]})});}''')
 page.add_script_tag(path=str(R/'site/search-ui.js'))
 page.evaluate("document.querySelector('#cards').innerHTML='<div id=searchEmpty>0곳</div>'")
 page.get_by_role('button',name='전국으로 넓혀 보기').wait_for();page.get_by_text('서울 식당 · 20곳').wait_for()
 page.get_by_role('button',name='전국으로 넓혀 보기').click();assert page.evaluate('widen')==1
 assert page.locator('#region').input_value()==''
 assert page.locator('.eg33-empty-options').count()==1
 browser.close()
print('v3.3 Chromium fixture PASS (mobile/desktop/map, nearby delegation, empty chips/widen)')
