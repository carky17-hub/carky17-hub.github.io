// eodigagae-api bundle (worker.js + google.js) v1.8 — KV quota

// KV-based daily cap (dashboard-deployable; approximate under heavy concurrency)
async function reserveKV(env,name,cap){if(!env.QUOTA_KV)return false;const day=new Date(Date.now()+9*3600000).toISOString().slice(0,10);const k=name+':'+day;const n=Number(await env.QUOTA_KV.get(k))||0;if(n>=cap)return false;await env.QUOTA_KV.put(k,String(n+1),{expirationTtl:172800});return true}
const {googleRoute}=(()=>{
// Global quota per SKU. No external content persistence.
const str=v=>typeof v==='string'&&v.length>0&&v.length<=300&&!/[\x00-\x1f\x7f]/.test(v);
const idOK=v=>typeof v==='string'&&/^[A-Za-z0-9_-]{5,512}$/.test(v);
const norm=v=>String(v||'').normalize('NFKC').toLowerCase().replace(/대한민국|한국|republic of korea|south korea/gi,'').replace(/[^\p{L}\p{N}]/gu,'');
function street(v){const m=String(v||'').normalize('NFKC').match(/([가-힣\d·.]+(?:대로|로|길))\s*(\d+(?:-\d+)?)(?!\d)/);return m?norm(m[1])+':'+m[2]:''}
const province=v=>norm(v).replace(/특별자치시$|특별자치도$|특별시$|광역시$|도$/u,'');
function matches(name,district,address,p,sido){const n=norm(name),a=norm(address),b=norm(p.formattedAddress),s=street(address),t=street(p.formattedAddress);return !!(n&&n===norm(p.displayName?.text)&&a&&b&&s&&s===t&&norm(district)&&b.includes(norm(district))&&a.includes(norm(district))&&province(sido)&&a.startsWith(province(sido))&&b.startsWith(province(sido)));}
const b64=a=>btoa(String.fromCharCode(...a)).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
const un64=s=>Uint8Array.from(atob(s.replace(/-/g,'+').replace(/_/g,'/').padEnd(Math.ceil(s.length/4)*4,'=')),c=>c.charCodeAt(0));
async function key(secret){return crypto.subtle.importKey('raw',new TextEncoder().encode(secret),{name:'HMAC',hash:'SHA-256'},false,['sign','verify'])}
async function token(name,secret){const body=b64(new TextEncoder().encode(JSON.stringify({name,exp:Date.now()+10*60000})));const sig=await crypto.subtle.sign('HMAC',await key(secret),new TextEncoder().encode(body));return body+'.'+b64(new Uint8Array(sig))}
async function decode(t,secret){if(typeof t!=='string'||t.length>2400)return null;try{const [b,s,...rest]=t.split('.');if(rest.length||!await crypto.subtle.verify('HMAC',await key(secret),un64(s),new TextEncoder().encode(b)))return null;const d=JSON.parse(new TextDecoder().decode(un64(b)));return d.exp>Date.now()&&/^places\/[A-Za-z0-9_-]+\/photos\/[A-Za-z0-9_-]+$/.test(d.name)?d.name:null}catch{return null}}
async function googleRoute(req,env,origin,response){const u=new URL(req.url),route=u.pathname.slice(1);const reply=(b,s=200)=>response(b,s,origin);if(req.method!=='GET')return reply({error:'method'},405);if(env.GOOGLE_APPROVED!=='true'||!env.GOOGLE_SERVER_KEY)return reply({error:'disabled'},503);
 const caps={search:[env.GOOGLE_SEARCH_DAILY_LIMIT||'100',100],details:[env.GOOGLE_DETAILS_DAILY_LIMIT||'25',25],photos:[env.GOOGLE_PHOTOS_DAILY_LIMIT||'25',25]};
 async function reserve(kind){const [raw,max]=caps[kind];const n=Number(raw);if(!Number.isSafeInteger(n)||n<1||n>max)throw Object.assign(Error('cap'),{status:503});if(!await reserveKV(env,'google-'+kind,n))throw Object.assign(Error('quota'),{status:429})}
 async function call(kind,path,mask,body){await reserve(kind);const r=await fetch('https://places.googleapis.com/v1/'+path,{method:body?'POST':'GET',headers:{'X-Goog-Api-Key':env.GOOGLE_SERVER_KEY,...(mask?{'X-Goog-FieldMask':mask}:{}),...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{}),redirect:'error',signal:AbortSignal.timeout(10000)});if(!r.ok){console.log('google-upstream',r.status,(await r.text()).slice(0,300));throw Object.assign(Error('upstream'),{status:502})}return r.json()}
 try{if(route==='google-photo'){if(env.GOOGLE_PHOTOS_ENABLED!=='true')return reply({error:'disabled'},503);const name=await decode(u.searchParams.get('token'),env.GOOGLE_SERVER_KEY);if(!name)return reply({error:'token'},400);const d=await call('photos',name+'/media?maxWidthPx=640&maxHeightPx=640&skipHttpRedirect=true');const url=new URL(d.photoUri);if(url.protocol!=='https:'||!(url.hostname==='googleusercontent.com'||url.hostname.endsWith('.googleusercontent.com')||url.hostname.endsWith('.ggpht.com'))||url.username||url.password)throw Error('photo uri');return reply({photoUri:url.href})}
 const name=u.searchParams.get('name'),district=u.searchParams.get('district'),sido=u.searchParams.get('sido'),address=u.searchParams.get('address');if(![name,district,sido,address].every(str)||!street(address))return reply({status:'unmatched'});let id=u.searchParams.get('id');if(id&&!idOK(id))return reply({error:'id'},400);
 if(!id){const d=await call('search','places:searchText','places.id',{textQuery:name+' '+address,languageCode:'ko',regionCode:'KR',pageSize:5});id=d.places?.[0]?.id;if(!idOK(id))return reply({status:'unmatched'})}
 const photoOn=env.GOOGLE_PHOTOS_ENABLED==='true'&&u.searchParams.get('photos')==='1';const d=await call('details','places/'+id+'?languageCode=ko&regionCode=KR','id,displayName,formattedAddress,rating,userRatingCount,googleMapsUri,attributions'+(photoOn?',photos':''));if(!matches(name,district,address,d,sido))return reply({status:'unmatched'});
 const photos=[];if(photoOn)for(const ph of (d.photos||[])){if(photos.length>=3)break;if(!/^places\/[A-Za-z0-9_-]+\/photos\/[A-Za-z0-9_-]+$/.test(ph.name||'')||!ph.googleMapsUri)continue;photos.push({token:await token(ph.name,env.GOOGLE_SERVER_KEY),authorAttributions:ph.authorAttributions||[],googleMapsUri:ph.googleMapsUri,flagContentUri:ph.flagContentUri})}
 return reply({status:'matched',rating:d.rating,userRatingCount:d.userRatingCount,googleMapsUri:d.googleMapsUri,attributions:d.attributions||[],photos});
 }catch(e){console.log('google-error',e.status||'',e.message);return reply({error:'unavailable'},e.status||503)}
}

return {googleRoute};})();
// Search-only proxy. No response-content persistence. Every upstream request is counted.
const ORIGINS=new Set(['https://eodigagae.com','https://www.eodigagae.com']);
const routes=new Set(['local','blog','image','match']);
const response=(body,status=200,origin='')=>new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store, private','Vary':'Origin',...(origin?{'Access-Control-Allow-Origin':origin}:{})}});
const norm=s=>String(s||'').normalize('NFKC').replace(/<\/?b>/gi,'').toLowerCase().replace(/[^\p{L}\p{N}]/gu,'');
const clean=s=>typeof s==='string'&&s.length>0&&s.length<=180&&!/[\x00-\x1f\x7f]/.test(s);
export function similarity(a,b){a=norm(a);b=norm(b);if(!a||!b)return 0;if(a===b)return 1;const grams=s=>new Set(Array.from(s).slice(0,-1).map((_,i)=>s.slice(i,i+2)));const x=grams(a),y=grams(b);return 2*[...x].filter(v=>y.has(v)).length/(x.size+y.size||1)}
export function matchLocal(items,name,district,address){
 const dn=norm(district),an=norm(address);if(!dn||!an||an.length<8)return 'unknown';
 const scores=items.map(r=>{const n=similarity(name,r.title),addresses=[r.address,r.roadAddress].filter(Boolean);const region=addresses.some(a=>norm(a).includes(dn));const addr=addresses.reduce((m,a)=>Math.max(m,similarity(a,address)),0);const number=String(address).match(/\d+(?:-\d+)?\s*$/)?.[0]?.trim();const sameNumber=number&&addresses.some(a=>String(a).match(/\d+(?:-\d+)?\s*$/)?.[0]?.trim()===number);return {n,addr,region,ok:n>=.9&&region&&addr>=.8&&!!sameNumber}});
 if(scores.filter(s=>s.ok).length===1)return 'matched';if(scores.some(s=>s.ok||s.n>=.7&&s.region))return 'ambiguous';return 'unmatched';
}
export default {async fetch(req,env){const u=new URL(req.url),origin=req.headers.get('Origin')||'',ref=req.headers.get('Referer');if(!ORIGINS.has(origin))return response({error:'origin'},403);try{if(!ref||new URL(ref).origin!==origin)return response({error:'referer'},403,origin)}catch{return response({error:'referer'},403,origin)}
 const route=u.pathname.slice(1);if(['google-detail','google-photo'].includes(route))return googleRoute(req,env,origin,response);if(req.method!=='GET'||!routes.has(route))return response({error:'route'},405,origin);
 if(env.NAVER_SEARCH_APPROVED!=='true'||!env.NAVER_CLIENT_ID||!env.NAVER_CLIENT_SECRET)return response({error:'disabled'},503,origin);
 if(route==='match'&&env.NAVER_MATCH_APPROVED!=='true')return response({error:'disabled'},503,origin);
 if(route==='image'&&env.NAVER_IMAGE_APPROVED!=='true')return response({error:'disabled'},503,origin);
 const q=(u.searchParams.get('q')||'').trim(),name=(u.searchParams.get('name')||'').trim(),district=(u.searchParams.get('district')||'').trim(),address=(u.searchParams.get('address')||'').trim();if(!clean(q)||route==='match'&&![name,district,address].every(clean))return response({error:'query'},400,origin);
 const cap=Number(env.DAILY_LIMIT||100);if(!Number.isSafeInteger(cap)||cap<1||cap>1000)return response({error:'disabled'},503,origin);
 try{
  async function call(kind,params){if(!await reserveKV(env,'naver',cap))throw Object.assign(Error('limit'),{status:429});const url=new URL('https://naverapihub.apigw.ntruss.com/search/v1/'+kind);url.search=new URLSearchParams({query:q,format:'json',...params});const r=await fetch(url,{headers:{'X-NCP-APIGW-API-KEY-ID':env.NAVER_CLIENT_ID,'X-NCP-APIGW-API-KEY':env.NAVER_CLIENT_SECRET},redirect:'error',signal:AbortSignal.timeout(8000)});if(!r.ok)throw Object.assign(Error('upstream'),{status:502});return r.json()}
  if(route==='image'){const safety=await call('adult',{});if(String(safety.adult)!=='0')return response({error:'search term blocked'},422,origin)}
  const kind=route==='match'?'local':route;
  const d=await call(kind,{display:kind==='blog'?'3':kind==='image'&&u.searchParams.get('single')==='1'?'1':'5',start:'1',sort:kind==='blog'?'date':kind==='local'?'random':'sim'});
  if(!Array.isArray(d.items)||!Number.isSafeInteger(d.total)||d.total<0)throw Object.assign(Error('format'),{status:502});
  if(route==='match')return response({status:matchLocal(d.items,name,district,address)},200,origin);
  // Original result order and fields. No filtering, blending, ranking, or image copying.
  return response(d,200,origin)
 }catch(e){console.log('naver-error',e.status||'',e.message);return response({error:'unavailable'},e.status||503,origin)}}};
