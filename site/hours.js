'use strict';
// 어디가개 영업 상태 계산기 — 공공데이터의 운영시간·휴무일 문자열을 해석해 한국시간 기준 현재 상태를 계산
(function(){
const D={'일':0,'월':1,'화':2,'수':3,'목':4,'금':5,'토':6};
const ORDER=[1,2,3,4,5,6,0];
function kstNow(d){d=d||new Date();const k=new Date(d.getTime()+(d.getTimezoneOffset()+540)*60000);return k}
function range(a,b){const i=ORDER.indexOf(a),j=ORDER.indexOf(b),out=[];if(i<0||j<0)return out;for(let k=i;;k=(k+1)%7){out.push(ORDER[k]);if(k===j||out.length>7)break}return out}
function days(t){t=String(t||'').replace(/법정공휴일|공휴일|휴일|당일|요일|\d+\s*월\s*\d+\s*일/g,' ');if(/매일|연중|월~일|365/.test(t))return [0,1,2,3,4,5,6];const out=new Set();const re=/([월화수목금토일])\s*~\s*([월화수목금토일])|([월화수목금토일])/g;let m;while((m=re.exec(t))){if(m[1])range(D[m[1]],D[m[2]]).forEach(x=>out.add(x));else out.add(D[m[3]])}return [...out]}
const cache=new Map();
function parseHours(h){h=String(h||'').trim();if(!h)return null;if(cache.has(h))return cache.get(h);let res=null;
 if(!/하절기|동절기|\d+\s*~\s*\d+\s*월|\d+월/.test(h)){
  const sched={},vary=new Set();let pend=[];let ok=false;
  for(const seg of h.split(/,\s*/)){const tm=seg.match(/(\d{1,2}):(\d{2})\s*~\s*(\d{1,2}):(\d{2})/);const dayPart=tm?seg.slice(0,tm.index):seg;const ds=days(dayPart);
   if(!tm){if(/변동/.test(seg))ds.concat(pend).forEach(x=>vary.add(x)),pend=[];else pend=pend.concat(ds);continue}
   let all=pend.concat(ds);pend=[];if(!all.length&&!ok&&h.trim()===seg.trim())all=[0,1,2,3,4,5,6];if(!all.length)continue;
   const s=+tm[1]*60+ +tm[2],e=+tm[3]*60+ +tm[4];all.forEach(x=>sched[x]=[s,e]);ok=true}
  if(ok)res={sched,vary};}
 cache.set(h,res);return res}
function closedToday(c,now){c=String(c||'');if(!c||/연중무휴/.test(c))return false;const dow=now.getDay(),nth=Math.ceil(now.getDate()/7);
 if(now.getMonth()===0&&now.getDate()===1&&/1월\s*1일/.test(c))return true;
 const wk=c.match(/([\d,\s]+)째\s*주\s*([월화수목금토일~,\s]+)/);if(wk){const ns=wk[1].match(/\d/g).map(Number);if(ns.includes(nth)&&days(wk[2]).includes(dow))return true}
 const i=c.indexOf('매주');if(i>=0&&days(c.slice(i+2).replace(/법정공휴일|공휴일/g,'')).includes(dow))return true;
 return false}
const hm=m=>{m=((m%1440)+1440)%1440;return String(Math.floor(m/60)).padStart(2,'0')+':'+String(m%60).padStart(2,'0')};
function status(p,d){const now=kstNow(d),dow=now.getDay(),cur=now.getHours()*60+now.getMinutes();const hasC=!!(p&&p.closedDays&&!/변동/.test(p.closedDays));
 if(hasC&&closedToday(p.closedDays,now))return {state:'dayoff',text:'오늘 휴무'};
 const ph=parseHours(p&&p.hours);if(!ph)return {state:'unknown',text:''};
 // 전날 밤샘 영업이 이어지는 경우
 const y=ph.sched[(dow+6)%7];if(y&&y[1]<y[0]&&cur<y[1])return {state:'open',text:'영업 중 · '+hm(y[1])+' 종료'};
 if(ph.vary.has(dow))return {state:'unknown',text:'오늘 운영시간 변동'};
 const t=ph.sched[dow];if(!t){const known=Object.keys(ph.sched).length;return known>=1?{state:'dayoff',text:'오늘 휴무'}:{state:'unknown',text:''}}
 let [s,e]=t;if(s===e||(s===0&&e>=1440))return {state:'open',text:'24시간 영업'};
 const over=e<s;const inside=over?cur>=s:(cur>=s&&cur<e);
 if(inside)return {state:'open',text:'영업 중 · '+hm(e)+' 종료'};
 if(cur<s)return {state:'before',text:'영업 전 · '+hm(s)+' 오픈'};
 return {state:'closed',text:'영업 종료'}}
function pill(p){const s=status(p);return s.text?`<span class="open-pill ${s.state}">${s.text}</span>`:''}
function fill(root){(root||document).querySelectorAll('[data-hours],[data-closed]').forEach(el=>{const s=status({hours:el.dataset.hours,closedDays:el.dataset.closed});el.className='open-pill '+s.state;el.textContent=s.text||'운영시간 확인 필요';})}
window.EGHours={status,pill,fill,parseHours};
if(document.readyState!=='loading')fill();else document.addEventListener('DOMContentLoaded',()=>fill());
})();
