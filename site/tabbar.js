'use strict';
(()=>{
 const icons={home:'<path d="M3 10.5 12 3l9 7.5V21h-6v-6H9v6H3z"/>',find:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',near:'<path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',saved:'<path d="M20.8 8.4c0 5-8.8 11.5-8.8 11.5S3.2 13.4 3.2 8.4a4.6 4.6 0 0 1 8.8-2 4.6 4.6 0 0 1 8.8 2Z"/>'};
 function init(){
  if(document.getElementById('eg33-tabbar')||!document.querySelector('main')||location.pathname==='/offline.html'||location.pathname.startsWith('/naver-search/'))return;
  const body=document.body,home=!!document.getElementById('searchForm'),old=document.querySelector('.mobile-nav');
  const nav=document.createElement('nav');nav.id='eg33-tabbar';nav.className='eg33-tabbar';nav.setAttribute('aria-label','하단 주요 메뉴');
  const defs=[['home','홈','/'],['find','장소 찾기','/#explore'],['near','내 주변',null],['saved','저장','/#saved']];
  const tabs={};for(const [key,label,url] of defs){const el=document.createElement(url?'a':'button');el.dataset.egTab=key;if(url)el.href=url;else el.type='button';el.innerHTML='<svg viewBox="0 0 24 24" width="23" height="23" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+icons[key]+'</svg><span>'+label+'</span>';tabs[key]=el;nav.append(el)}
  body.append(nav);body.classList.add('eg33-tab-ready');
  // Preserve the old controls for the app's event bindings. New near tab delegates to the original hero button.
  const original=()=>document.querySelector('.nearby-bar [data-nearby]')||old?.querySelector('[data-nearby]');
  let requested=false,explored=false;const params=new URLSearchParams(location.search);const auto=home&&params.get('egnear')==='1';
  if(auto){const u=new URL(location.href);u.searchParams.delete('egnear');history.replaceState(history.state,'',u.pathname+u.search+u.hash)}
  function active(){const b=original(),near=home&&b?.getAttribute('aria-pressed')==='true';const key=location.hash==='#saved'&&home?'saved':near?'near':home&&!explored&&!location.search&&(!location.hash||location.hash==='#home')?'home':'find';for(const [k,el] of Object.entries(tabs)){el.classList.toggle('eg33-active',k===key);if(k==='near'){el.setAttribute('aria-pressed',String(!!near));if(home&&b){el.disabled=!!b.disabled;el.setAttribute('aria-label',b.disabled?'내 주변 · 위치 확인 중 또는 준비 중':near?'내 주변 검색 해제':'내 주변');}else{el.disabled=false;el.setAttribute('aria-label','내 주변')}}else if(k===key)el.setAttribute('aria-current','page');else el.removeAttribute('aria-current')} }
  function request(){if(!home){location.href='/?egnear=1#explore';return}const b=original();if(b&&!b.disabled){b.click();active()}}
  tabs.near.addEventListener('click',request);
  function sync(){active();const b=original();if(auto&&!requested&&b&&!b.disabled){requested=true;request()}}
  if(home){const b=original();if(b)new MutationObserver(sync).observe(b,{attributes:true,attributeFilter:['disabled','aria-pressed']});const markExplore=()=>{explored=true;active()};document.getElementById('searchForm')?.addEventListener('submit',markExplore);document.addEventListener('click',e=>{if(e.target.closest('#cats [data-cat],#filters [data-flag],#reset'))markExplore()});document.getElementById('region')?.addEventListener('change',markExplore)}
  window.addEventListener('hashchange',()=>{if(location.hash==='#home'||!location.hash)explored=false;active()});window.addEventListener('pageshow',active);sync();
  // Keep existing detail action bar above the tabs, never replace its actions.
  const actions=document.querySelector('.m-actions');const layout=()=>{const visible=actions&&getComputedStyle(actions).position==='fixed'&&getComputedStyle(actions).display!=='none';body.style.setProperty('--eg33-actions-height',visible?Math.ceil(actions.getBoundingClientRect().height)+'px':'0px');body.classList.toggle('eg33-has-actions',!!visible)};
  if(actions&&'ResizeObserver'in window)new ResizeObserver(layout).observe(actions);window.addEventListener('resize',layout,{passive:true});layout();
  if(window.visualViewport){const keyboard=()=>{const el=document.activeElement;const typing=el&&(el.matches('input,textarea,[contenteditable=true]'));body.classList.toggle('eg33-keyboard',!!typing&&window.innerHeight-window.visualViewport.height>150)};window.visualViewport.addEventListener('resize',keyboard,{passive:true});document.addEventListener('focusout',()=>setTimeout(keyboard,0));}
 }
 if(document.readyState==='complete')init();else document.addEventListener('DOMContentLoaded',init,{once:true});
})();
