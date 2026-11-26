'use strict';
(()=>{const input=document.getElementById('query'),form=document.getElementById('searchForm'),list=document.getElementById('searchSuggestions'),status=document.getElementById('searchStatus');if(!input||!form||!list||!status)return;let pending=null,timer,seq=0,active=-1,options=[],composing=false;
 function getIndex(){if(!pending)pending=fetch('/data/search-compact.json',{cache:'default',credentials:'same-origin'}).then(r=>{if(!r.ok)throw Error('index');return r.json().then(EGSearch.decode)}).catch(e=>{pending=null;throw e});return pending}
 let worker=null,workerDisabled=false,nextRequest=0;const jobs=new Map();
 function failWorker(){workerDisabled=true;worker?.terminate();worker=null;for(const j of jobs.values()){clearTimeout(j.timer);j.reject(Error('search worker'))}jobs.clear()}
 function workerSearch(raw,limit){if(workerDisabled||!('Worker'in window))return Promise.reject(Error('worker unsupported'));if(!worker){worker=new Worker('/search-worker.js');worker.onmessage=e=>{const j=jobs.get(e.data.id);if(!j)return;clearTimeout(j.timer);jobs.delete(e.data.id);if(e.data.error)j.reject(Error('search worker'));else j.resolve(e.data.results)};worker.onerror=failWorker;worker.onmessageerror=failWorker}const id=++nextRequest;return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{jobs.delete(id);reject(Error('search timeout'))},15000);jobs.set(id,{resolve,reject,timer});worker.postMessage({id,raw,limit})})}
 async function suggestions(raw,limit=8){try{return await workerSearch(raw,limit)}catch{const index=await getIndex();return EGSearch.suggest(index,raw,limit)}}
 function close(){++seq;clearTimeout(timer);list.hidden=true;input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');list.replaceChildren();options=[];active=-1;status.textContent=''}
 function setActive(i){if(!options.length)return;active=(i+options.length)%options.length;for(let j=0;j<options.length;j++)list.children[j].setAttribute('aria-selected',String(j===active));input.setAttribute('aria-activedescendant','eg-search-option-'+active);list.children[active].scrollIntoView({block:'nearest'})}
 function anchor(v,id){const a=document.createElement('a');a.href=v.path;a.textContent=v.title;const small=document.createElement('small');small.textContent=(v.typo?'유사 검색 · ':v.kind==='region'?'지역 목록 · ':'업체 · ')+v.detail;a.append(small);if(id!==undefined){a.id='eg-search-option-'+id;a.setAttribute('role','option');a.setAttribute('aria-selected','false');a.tabIndex=-1}return a}
 async function update(){const id=++seq,raw=input.value;if(EGSearch.norm(raw).length<2||composing){close();return}try{const results=await suggestions(raw);if(id!==seq||input.value!==raw||document.activeElement!==input)return;options=results;active=-1;list.replaceChildren(...options.map((v,i)=>anchor(v,i)));list.hidden=!options.length;input.setAttribute('aria-expanded',String(!!options.length));input.removeAttribute('aria-activedescendant');status.textContent=options.length?`검색 제안 ${options.length}개`:'검색 제안 없음';}catch{if(id===seq)close()}}
 function schedule(){clearTimeout(timer);if(!composing)timer=setTimeout(update,65)}
 input.addEventListener('input',schedule);input.addEventListener('focus',()=>{if(input.value)schedule()});input.addEventListener('compositionstart',()=>{composing=true;close()});input.addEventListener('compositionend',()=>{composing=false;schedule()});
 input.addEventListener('keydown',e=>{if(e.isComposing||composing)return;if(e.key==='Escape'){close();return}if(e.key==='ArrowDown'&&!list.hidden){e.preventDefault();setActive(active+1)}else if(e.key==='ArrowUp'&&!list.hidden){e.preventDefault();setActive(active<0?options.length-1:active-1)}else if(e.key==='Enter'&&!list.hidden&&active>=0){e.preventDefault();window.EGTrack?.('suggestion');location.href=options[active].path}});
 list.addEventListener('pointerdown',e=>{if(e.target.closest('a'))e.preventDefault()});document.addEventListener('pointerdown',e=>{if(!form.contains(e.target)&&!list.contains(e.target))close()});input.addEventListener('blur',()=>setTimeout(()=>{if(!list.contains(document.activeElement))close()},130));form.addEventListener('submit',close);
 // v3.3: keep existing query and active service/condition filters when widening.
 function emptyChips(box,label,items){if(!items.length)return;const h=document.createElement('h3');h.textContent=label;const links=document.createElement('div');links.className='eg33-empty-chips';for(const item of items){if(!/^\/(?!\/)[^?#]*\/$/.test(item.path))continue;const a=document.createElement('a');a.href=item.path;a.textContent=item.title;links.append(a)}if(links.childElementCount)box.append(h,links)}
 window.EGSearchEmpty=async(target,raw)=>{
  if(!target||target.dataset.eg33||location.hash==='#saved')return;target.dataset.eg33='1';raw=String(raw||'');
  const region=document.getElementById('region');const box=document.createElement('div');box.className='eg33-empty-options';
  const b=document.createElement('button');b.type='button';b.className='eg33-widen';b.textContent='전국으로 넓혀 보기';
  b.addEventListener('click',()=>{if(!region)return;region.value='';region.dispatchEvent(new Event('change',{bubbles:true}));});
  const params33=new URLSearchParams(location.search);const restricted=!!region?.value||['sigungu','dong','dongKey'].some(k=>params33.has(k))||document.querySelector('.nearby-bar [data-nearby][aria-pressed="true"]')||document.getElementById('modeLabel')?.textContent.includes('현재 지도 영역');
  if(region){b.disabled=!restricted;box.append(b)}const p=document.createElement('p');p.textContent=(restricted?'검색어와 업종·조건을 유지하고 지역 범위를 넓혀요.':'이미 전국을 검색하고 있어요. 다른 조건이나 아래 장소 목록을 확인해 보세요.')+' 아래 제안은 현재 필터와 별개의 지역 목록입니다.';box.append(p);target.append(box);
  try{
   const matches=EGSearch.norm(raw).length>=2?await suggestions(raw,16):[];
   if(!target.isConnected||input.value!==raw)return;
   const index=await getIndex();if(!target.isConnected||input.value!==raw)return;
   const regionMatches=matches.filter(x=>x.kind==='region');emptyChips(box,'비슷한 지역·검색어',regionMatches.slice(0,5));
   const selected=[...document.querySelectorAll('#cats [aria-pressed="true"]')].map(e=>e.dataset.cat).filter(c=>c&&c!=='전체');
   const rows=(index.regions||[]).filter(r=>r[6]>0&&r[5]&&r[5]!=='장례·추모'&&r[5]!=='봉안');
   const ref=regionMatches.map(x=>rows.find(r=>r[1]===x.path)).find(Boolean);
   const current=region?.value||'';const area=ref||(current?rows.find(r=>r[2]===current&&!r[3]&&!r[4]):null);
   let candidates=area?rows.filter(r=>r[2]===area[2]&&r[3]===area[3]&&r[4]===area[4]):rows.filter(r=>!r[3]&&!r[4]);
   if(!candidates.length&&current)candidates=rows.filter(r=>r[2]===current&&!r[3]&&!r[4]);
   const seen=new Set(regionMatches.map(x=>x.path));candidates=candidates.filter(r=>!seen.has(r[1])&&!selected.includes(r[5])).sort((a,b)=>b[6]-a[6]||String(a[0]).localeCompare(String(b[0]),'ko'));
   const byService=new Set();const chips=[];for(const r of candidates){const svc=Array.isArray(r[5])?r[5].join('·'):r[5];if(byService.has(svc))continue;byService.add(svc);chips.push({title:/[\d,]+곳$/.test(r[0])?r[0]:r[0]+' · '+r[6]+'곳',path:r[1]});if(chips.length===5)break}emptyChips(box,area?'다른 업종 둘러보기':'다른 지역·업종 둘러보기',chips);
   emptyChips(box,'비슷한 업체명',matches.filter(x=>x.kind==='place').slice(0,3));
  }catch{/* Nationwide button remains usable if the suggestion index fails. */}
 };
 // The old renderer calls EGSearchEmpty only for non-empty queries; also handle filter-only results.
 const emptyCards=document.getElementById('cards');if(emptyCards){const scanEmpty=()=>{const t=emptyCards.querySelector('#searchEmpty');if(t)window.EGSearchEmpty(t,input.value)};new MutationObserver(scanEmpty).observe(emptyCards,{childList:true});scanEmpty()}
})();
