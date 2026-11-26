'use strict';
// 어디가개 영업 상태 계산기 — 공공데이터의 운영시간·휴무일 문자열을 해석해 한국시간 기준 현재 상태를 계산
(function(){
const D={'일':0,'월':1,'화':2,'수':3,'목':4,'금':5,'토':6};
const ORDER=[1,2,3,4,5,6,0];
// 관공서의 공휴일에 관한 규정 제2·3조 (대통령령 제36290호, 2026 개정)
// https://www.law.go.kr/LSW/lsInfoP.do?ancYnChk=0&lsId=002404
// 우주항공청 2026·2027 월력요항 + 2026 노동절·제헌절 개정. 확인일 2026-11-26.
// https://astro.kasi.re.kr/kor/life/post/calendarData?year=2026
// https://astro.kasi.re.kr/kor/life/post/calendarData?year=2027
// 일반 일요일은 기존 요일 영업표로 처리; 명명된 공휴일·대체공휴일·선거일만 아래 배열에 둔다.
const HOLIDAYS=Object.freeze({2026:['01-01','02-16','02-17','02-18','03-01','03-02','05-01','05-05','05-24','05-25','06-03','06-06','07-17','08-15','08-17','09-24','09-25','09-26','10-03','10-05','10-09','12-25'],2027:['01-01','02-06','02-07','02-08','02-09','03-01','05-01','05-03','05-05','05-13','06-06','07-17','07-19','08-15','08-16','09-14','09-15','09-16','10-03','10-04','10-09','10-11','12-25','12-27']});
const FESTIVALS={2026:{seol:['02-16','02-17','02-18'],chuseok:['09-24','09-25','09-26']},2027:{seol:['02-06','02-07','02-08','02-09'],chuseok:['09-14','09-15','09-16']}};
const md=d=>String(d.getUTCMonth()+1).padStart(2,'0')+'-'+String(d.getUTCDate()).padStart(2,'0');
const holiday=d=>!!HOLIDAYS[d.getUTCFullYear()]?.includes(md(d));
function kstNow(d){return new Date((d||new Date()).getTime()+9*3600000)}
function range(a,b){const i=ORDER.indexOf(a),j=ORDER.indexOf(b),out=[];if(i<0||j<0)return out;for(let k=i;;k=(k+1)%7){out.push(ORDER[k]);if(k===j||out.length>7)break}return out}
function days(t){t=String(t||'').replace(/법정공휴일|공휴일|휴일|당일|요일|\d+\s*월\s*\d+\s*일/g,' ');if(/매일|연중|월~일|365/.test(t))return [0,1,2,3,4,5,6];const out=new Set();const re=/([월화수목금토일])\s*~\s*([월화수목금토일])|([월화수목금토일])/g;let m;while((m=re.exec(t))){if(m[1])range(D[m[1]],D[m[2]]).forEach(x=>out.add(x));else out.add(D[m[3]])}return [...out]}
const cache=new Map();
function parseHours(h){h=String(h||'').trim();if(!h)return null;if(cache.has(h))return cache.get(h);let res=null;
 if(!/하절기|동절기|\d+\s*~\s*\d+\s*월|\d+월/.test(h)){
  const sched={},vary=new Set();let pend=[],pendHoliday=false,holidayHours=null,holidayVary=false;let ok=false;
  for(const seg of h.split(/,\s*/)){const tm=seg.match(/(\d{1,2}):(\d{2})\s*~\s*(\d{1,2}):(\d{2})/);const dayPart=tm?seg.slice(0,tm.index):seg;const ds=days(dayPart);const hs=/공휴일/.test(dayPart);
   if(!tm){if(/변동/.test(seg)){ds.concat(pend).forEach(x=>vary.add(x));holidayVary=holidayVary||hs||pendHoliday;pend=[];pendHoliday=false}else{pend=pend.concat(ds);pendHoliday=pendHoliday||hs}continue}
   let all=pend.concat(ds);const isHoliday=pendHoliday||hs;pend=[];pendHoliday=false;if(!all.length&&!isHoliday&&!ok&&h.trim()===seg.trim())all=[0,1,2,3,4,5,6];if(!all.length&&!isHoliday)continue;
   const s=+tm[1]*60+ +tm[2],e=+tm[3]*60+ +tm[4];if(+tm[1]>23||+tm[2]>59||+tm[3]>24||+tm[4]>59||e>1440)continue;all.forEach(x=>sched[x]=[s,e]);if(isHoliday)holidayHours=[s,e];ok=true}
  if(ok||holidayVary)res={sched,vary,holidayHours,holidayVary};}
 cache.set(h,res);return res}
function closedToday(c,now){c=String(c||'');if(!c||/연중무휴/.test(c))return false;const dow=now.getUTCDay(),nth=Math.ceil(now.getUTCDate()/7);
 if(now.getUTCMonth()===0&&now.getUTCDate()===1&&/1월\s*1일/.test(c))return true;
 const f=FESTIVALS[now.getUTCFullYear()],date=md(now);
 if(f){const norm=c.replace(/설날/g,'설').replace(/한가위/g,'추석');for(const [name,arr] of [['설',f.seol],['추석',f.chuseok]]){const other=name==='설'?'추석':'설';const combo=norm.match(new RegExp('(?:'+name+'\\s*[,·ㆍ/및과와]\\s*'+other+'|'+other+'\\s*[,·ㆍ/및과와]\\s*'+name+')\\s*(당일|연휴)'));const single=norm.match(new RegExp(name+'\\s*(당일|연휴)'));const kind=combo?.[1]||single?.[1];if(kind&&(kind==='연휴'?arr.includes(date):arr[1]===date))return true;if(!kind&&new RegExp('(?:^|[,\\s])'+name+'(?:$|[,\\s])').test(norm)&&arr[1]===date)return true;}}
 if(/공휴일\s*다음\s*날/.test(c)&&holiday(new Date(now.getTime()-86400000)))return true;
 if(holiday(now)&&/공휴일(?!\s*다음\s*날)/.test(c))return true;
 const wk=c.match(/([\d,\s]+)째\s*주\s*([월화수목금토일~,\s]+)/);if(wk){const ns=wk[1].match(/\d/g).map(Number);if(ns.includes(nth)&&days(wk[2]).includes(dow))return true}
 const w=c.match(/매주\s*((?:[월화수목금토일](?:요일)?)(?:\s*[,·/~]\s*[월화수목금토일](?:요일)?)*)/);if(w&&days(w[1]).includes(dow))return true;
 return false}
const hm=m=>{m=((m%1440)+1440)%1440;return String(Math.floor(m/60)).padStart(2,'0')+':'+String(m%60).padStart(2,'0')};
function schedule(ph,day){const h=holiday(day),dow=day.getUTCDay();if(h&&ph.holidayVary)return {vary:true};if(h&&ph.holidayHours)return {t:ph.holidayHours};if(ph.vary.has(dow))return {vary:true};return {t:ph.sched[dow]}}
function status(p,d){const now=kstNow(d),dow=now.getUTCDay(),cur=now.getUTCHours()*60+now.getUTCMinutes();const closed=String(p?.closedDays||'');
 if(closedToday(closed,now))return {state:'dayoff',text:'오늘 휴무'};
 if(!HOLIDAYS[now.getUTCFullYear()]&&/공휴일|설날|설[,·\s]|추석|명절/.test(closed+' '+String(p?.hours||'')))return {state:'unknown',text:'공휴일 운영시간 확인 필요'};
 const ph=parseHours(p&&p.hours);if(!ph)return {state:'unknown',text:''};
 // 전날 밤샘 영업이 이어지는 경우
 const prev=new Date(now.getTime()-86400000),y=schedule(ph,prev).t;if(y&&!closedToday(closed,prev)&&y[1]<y[0]&&cur<y[1])return {state:'open',text:'영업 중 · '+hm(y[1])+' 종료'};
 const slot=schedule(ph,now);if(slot.vary)return {state:'unknown',text:'오늘 운영시간 변동'};
 const t=slot.t;if(!t){const known=Object.keys(ph.sched).length;return known>=1?{state:'dayoff',text:'오늘 휴무'}:{state:'unknown',text:''}}
 let [s,e]=t;if(s===e||(s===0&&e>=1440))return {state:'open',text:'24시간 영업'};
 const over=e<s;const inside=over?cur>=s:(cur>=s&&cur<e);
 if(inside)return {state:'open',text:'영업 중 · '+hm(e)+' 종료'};
 if(cur<s)return {state:'before',text:'영업 전 · '+hm(s)+' 오픈'};
 return {state:'closed',text:'영업 종료'}}
function pill(p){const s=status(p);return s.text?`<span class="open-pill ${s.state}" title="등록된 운영시간 기준 · 방문 전 확인">${s.text}</span>`:''}
function fill(root){(root||document).querySelectorAll('[data-hours],[data-closed]').forEach(el=>{const s=status({hours:el.dataset.hours,closedDays:el.dataset.closed});el.className='open-pill '+s.state;el.textContent=s.text||(el.dataset.hours?(/하절기|동절기|\d+\s*월/.test(el.dataset.hours)?'계절별 운영 · 아래 시간 참고':'운영시간 아래 참고'):'운영시간 확인 필요');el.title='등록된 운영시간 기준 · 방문 전 확인';})}
window.EGHours={status,pill,fill,parseHours,holidays:HOLIDAYS};
if(document.readyState!=='loading')fill();else document.addEventListener('DOMContentLoaded',()=>fill());
})();
