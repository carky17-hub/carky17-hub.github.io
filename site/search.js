'use strict';
/* v1.8: First-party public listings only. No external lookup or personal query logging. */
(()=>{
 const CHO='ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ';
 const lead=s=>String(s??'').normalize('NFC').replace(/[\u1100-\u1112]/g,c=>CHO[c.charCodeAt(0)-0x1100]);
 const norm=s=>lead(s).toLowerCase().replace(/[^\p{L}\p{N}]/gu,'');
 function initials(s){return Array.from(norm(s),c=>{const n=c.charCodeAt(0)-0xac00;return n>=0&&n<11172?CHO[Math.floor(n/588)]:c}).join('')}
 const isInitial=q=>/^[ㄱ-ㅎ]+$/.test(q);
 const SHORT={서울특별시:'서울',부산광역시:'부산',인천광역시:'인천',대구광역시:'대구',대전광역시:'대전',울산광역시:'울산',광주광역시:'광주',세종특별자치시:'세종',경기도:'경기',강원특별자치도:'강원',충청북도:'충북',충청남도:'충남',전북특별자치도:'전북',전라북도:'전북',전라남도:'전남',경상북도:'경북',경상남도:'경남',제주특별자치도:'제주'};
 const SERVICES={'카페':['카페','애견동반카페','반려동물동반카페','애견카페'],'식당':['식당','애견동반식당','반려동물동반식당'],'숙소':['숙소','애견동반숙소','애견동반펜션'],'여행지':['여행지','애견동반여행지','가볼만한곳','애견동반가볼만한곳'],'놀이터':['놀이터','애견놀이터'],'미용':['미용','애견미용','애견미용실'],'동물병원':['동물병원','동물의료센터'],'호텔·유치원':['호텔','유치원','애견호텔','애견유치원','호텔유치원'],'장례·추모':['장례','추모','반려동물장례','반려동물장례식장','장례식장','납골당']};
 const shortArea=s=>String(s||'').replace(/(?:시|군|구|동|읍|면)$/u,'');
 const unique=a=>[...new Set(a.filter(Boolean))];
 function terms(p,extra=[]){const areas=unique([p.sido,SHORT[p.sido],p.sigungu,shortArea(p.sigungu),p.dong,p.dongKey,shortArea(p.dongKey||p.dong)]),svc=unique((p.services||[]).flatMap(s=>s==='장례·추모'?unique(['장례','추모','반려동물장례',...((p.funeralServices||[]).includes('장례')||p.subType==='장례식장'?['장례식장','반려동물장례식장']:[]),...((p.funeralServices||[]).includes('봉안')||['납골시설','봉안당'].includes(p.subType)?['납골당','봉안당']:[])]):(SERVICES[s]||[s])));return unique([p.name,...areas,p.address,p.roadAddress,p.category,p.subType,p.petSize,...svc,...extra,...areas.flatMap(a=>svc.map(s=>a+s)),[...areas,...svc,p.name].join(' ')])}
 function contains(text,q){const a=norm(text);return !!a&&(a.includes(q)||isInitial(q)&&initials(a).includes(q))}
 function matches(raw,p,extra=[]){const parts=String(raw||'').trim().split(/\s+/).map(norm).filter(Boolean);if(!parts.length)return true;const t=terms(p,extra);return parts.every(q=>t.some(v=>contains(v,q)))||t.some(v=>contains(v,parts.join('')))}
 // Bounded optimal string alignment distance (adjacent swap = one typo); used for suggestions, not silent filtering.
 function distance(a,b,cap=2){a=Array.from(a);b=Array.from(b);if(Math.abs(a.length-b.length)>cap)return cap+1;let prev2=null,prev=Array.from({length:b.length+1},(_,j)=>j);for(let i=1;i<=a.length;i++){const row=[i];for(let j=1;j<=b.length;j++){let v=Math.min(row[j-1]+1,prev[j]+1,prev[j-1]+Number(a[i-1]!==b[j-1]));if(i>1&&j>1&&a[i-1]===b[j-2]&&a[i-2]===b[j-1])v=Math.min(v,prev2[j-2]+1);row[j]=v}prev2=prev;prev=row}return prev[b.length]}
 const normCache=new Map();function publicNorm(text){if(normCache.has(text))return normCache.get(text);const n=norm(text);if(normCache.size<100000)normCache.set(text,n);return n}
 function textScore(text,q){const n=publicNorm(text);if(!n)return 0;if(n===q)return 100;if(n.startsWith(q))return 86;if(n.includes(q))return 66;if(isInitial(q)){const i=initials(n);if(i===q)return 91;if(i.startsWith(q))return 75;if(i.includes(q))return 55}return 0}
 function suggest(index,raw,limit=8){const q=norm(raw);if(q.length<2||q.length>70)return [];const pieces=String(raw).trim().split(/\s+/).map(norm).filter(Boolean),candidates=[];
  for(const r of index.regions||[]){const [title,path,sido,gu,dong,service,count]=r;if(!count)continue;const label=[SHORT[sido]||sido,gu,dong].filter(Boolean).join(' ');const choices=[title,dong,gu,SHORT[sido]||sido,label];let value=Math.max(...choices.map(x=>textScore(x,q)));if(!value&&pieces.length>1&&pieces.every(x=>choices.some(v=>contains(v,x))))value=72;if(value)candidates.push({kind:'region',title,detail:label+' · '+count+'곳',path,score:value+3,region:label,choices:[title,dong,gu,SHORT[sido]||sido].filter(Boolean)});}
  for(const r of index.places||[]){const [id,name,sido,gu,dong,service]=r;const label=[SHORT[sido]||sido,gu,dong].filter(Boolean).join(' ');let value=textScore(name,q);if(!value&&pieces.length>1&&pieces.every(x=>[name,label,service].some(v=>contains(v,x))))value=68;if(value)candidates.push({kind:'place',title:name,detail:label+' · '+service,path:'/place/'+id+'/',score:value,choices:[name]});}
  // Only offer edits when literal/initial match didn't yield enough results. No automatic correction.
  if(candidates.length<3&&!isInitial(q)&&q.length>=3&&q.length<=30){const cap=q.length>=6?2:1;const known=new Set(candidates.map(x=>x.path));const fuzzy=(choices)=>{let best=Infinity;for(const v of choices){for(const t of unique([v,...String(v||'').split(/\s+/)])){const n=publicNorm(t);if(!n||Math.abs(n.length-q.length)>cap)continue;const d=distance(n,q,cap);if(d<=cap)best=Math.min(best,d*20+Math.min(19,distance(n.normalize('NFD'),q.normalize('NFD'),19)))}}return best};
   for(const r of index.regions||[]){const [title,path,sido,gu,dong,service,count]=r;if(!count||known.has(path))continue;const d=fuzzy([title,dong,gu]);if(Number.isFinite(d))candidates.push({kind:'region',title,detail:[SHORT[sido]||sido,gu,dong].filter(Boolean).join(' ')+' · '+count+'곳',path,score:42-d/4,typo:true});}
   for(const r of index.places||[]){const [id,name,sido,gu,dong,service]=r,path='/place/'+id+'/';if(known.has(path))continue;const d=fuzzy([name]);if(Number.isFinite(d))candidates.push({kind:'place',title:name,detail:[SHORT[sido]||sido,gu,dong].filter(Boolean).join(' ')+' · '+service,path,score:40-d/4,typo:true});}}
  // For equal score no paid or popularity preference. Preserve neutral funeral region/name order.
  candidates.sort((a,b)=>b.score-a.score||a.detail.localeCompare(b.detail,'ko')||a.title.localeCompare(b.title,'ko')||a.path.localeCompare(b.path));const out=[],seen=new Set();for(const a of candidates){if(seen.has(a.path))continue;seen.add(a.path);out.push(a);if(out.length>=limit)break}return out;
 }
 function decode(index){if(index.version!==2)return index;const t=index.strings,v=x=>x===-1?null:t[x];return {version:1,places:index.places.map(r=>[r[0],r[1],...r.slice(2).map(v)]),regions:index.regions.map(r=>[r[0],r[1],v(r[2]),v(r[3]),v(r[4]),Array.isArray(r[5])?r[5].map(v):v(r[5]),r[6]])}}
 const api={norm,initials,distance,matches,suggest,decode};globalThis.EGSearch=api;
})();
