// Standalone Worker module. No upstream calls; only QUOTA_KV. Mount before other routes.
export async function analyticsRoute(request, env) {
  const url = new URL(request.url), path = url.pathname;
  const routes = ['/analytics-event','/analytics-image','/analytics-summary','/analytics-image-report'];
  if (!routes.includes(path)) return null;
  const origin = request.headers.get('Origin');
  const allowed = origin === 'https://eodigagae.com';
  const report = path === '/analytics-summary' || path === '/analytics-image-report';
  const reply = (data, status=200) => new Response(data === null ? null : JSON.stringify(data), {status, headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff','Vary':'Origin',...(allowed?{'Access-Control-Allow-Origin':origin,'Access-Control-Allow-Methods':'GET, POST, OPTIONS','Access-Control-Allow-Headers':'Content-Type, Authorization'}:{})}});
  if ((origin && !allowed) || (!report && !allowed)) return reply({error:'origin'},403);
  if (request.method === 'OPTIONS') return allowed ? reply(null,204) : reply({error:'origin'},403);
  if (env.ANALYTICS_ENABLED !== 'true' || !env.QUOTA_KV) return reply({error:'disabled'},503);
  const kv=env.QUOTA_KV, prefix='eg:analytics:v27:', day=(offset=0)=>new Date(Date.now()+9*3600000-offset*86400000).toISOString().slice(0,10);
  const events=['search','suggestion','phone','directions','save','consult','photo'];
  const empty=()=>({events:{},hosts:{},observations:0,requests:0});
  const cap=(v,def,max)=>/^[0-9]+$/.test(String(v??''))?Math.min(max,Number(v)):def;
  const limit=cap(env.ANALYTICS_DAILY_LIMIT,5000,5000), requests=cap(env.ANALYTICS_DAILY_REQUEST_LIMIT,300,700);
  // Compare hashes of tokens (fixed length), never persist or log either token.
  async function equal(a,b){if(!a||!b||a.length>512||b.length>512)return false;const enc=new TextEncoder();const [x,y]=await Promise.all([crypto.subtle.digest('SHA-256',enc.encode(a)),crypto.subtle.digest('SHA-256',enc.encode(b))]);let diff=0;const u=new Uint8Array(x),v=new Uint8Array(y);for(let i=0;i<u.length;i++)diff|=u[i]^v[i];return diff===0}
  if(report){
    if(request.method!=='GET')return reply({error:'method'},405);
    const auth=request.headers.get('Authorization')||'';
    const token=auth.startsWith('Bearer ')?auth.slice(7):url.searchParams.get('token');
    if(!await equal(token,env.ADMIN_TOKEN))return reply({error:'unauthorized'},401);
    const n=cap(url.searchParams.get('days'),7,30);if(n<1)return reply({error:'days'},400);
    try{const days={},totals=empty();for(let i=0;i<n;i++){const d=day(i),r=await kv.get(prefix+d,{type:'json'});if(!r)continue;days[d]=r;totals.observations+=r.observations;totals.requests+=r.requests;for(const [k,v] of Object.entries(r.events))totals.events[k]=(totals.events[k]||0)+v;for(const [h,v] of Object.entries(r.hosts)){const t=totals.hosts[h]||={img_load:0,img_error:0};t.img_load+=v.img_load;t.img_error+=v.img_error}}
      for(const v of Object.values(totals.hosts))v.error_rate=v.img_load+v.img_error?v.img_error/(v.img_load+v.img_error):null;
      return reply({days,totals,retentionDays:90,accuracy:'best_effort_KV',limits:{observations:limit,requests},unit:'events_not_unique_people_or_urls'});
    }catch{return reply({error:'unavailable'},503)}
  }
  if(request.method!=='POST')return reply({error:'method'},405);
  if(!/^text\/plain(?:\s*;|$)/i.test(request.headers.get('Content-Type')||''))return reply({error:'content_type'},415);
  if(request.headers.get('DNT')==='1'||request.headers.get('Sec-GPC')==='1')return reply(null,204);
  // Bounded stream read: do not accept arbitrary request bodies or record them.
  let body='';try{const reader=request.body?.getReader();if(!reader)return reply({error:'body'},400);let bytes=0;const decoder=new TextDecoder('utf-8',{fatal:true});while(true){const {done,value}=await reader.read();if(done)break;bytes+=value.length;if(bytes>2048){await reader.cancel();return reply({error:'body'},413)}body+=decoder.decode(value,{stream:true})}body+=decoder.decode()}catch{return reply({error:'body'},400)}
  let batch=[], count=1;
  if(path==='/analytics-event'){if(!events.includes(body))return reply({error:'event'},400)}else{
    try{batch=JSON.parse(body)}catch{return reply({error:'event'},400)}
    const validHost=h=>typeof h==='string'&&h.length<=100&&/^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*visitkorea\.or\.kr$/.test(h);
    if(!Array.isArray(batch)||batch.length<1||batch.length>12||batch.some(x=>!x||Object.keys(x).sort().join(',')!=='host,img_error,img_load'||!validHost(x.host)||!['img_load','img_error'].every(k=>Number.isSafeInteger(x[k])&&x[k]>=0&&x[k]<=100)||x.img_load+x.img_error<1)||new Set(batch.map(x=>x.host)).size!==batch.length)return reply({error:'event'},400);
    count=batch.reduce((s,x)=>s+x.img_load+x.img_error,0);if(count>100)return reply({error:'event'},400);
  }
  try{const key=prefix+day(),r=await kv.get(key,{type:'json'})||empty();
    if(r.observations+count>limit||r.requests+1>requests||new Set([...Object.keys(r.hosts),...batch.map(x=>x.host)]).size>16)return reply({error:'limit'},429);
    if(path==='/analytics-event')r.events[body]=(r.events[body]||0)+1;
    else for(const x of batch){const t=r.hosts[x.host]||={img_load:0,img_error:0};t.img_load+=x.img_load;t.img_error+=x.img_error}
    r.observations+=count;r.requests++;
    // KV is eventually consistent and allows only one write/same key/sec. Best effort, never retry.
    await kv.put(key,JSON.stringify(r),{expirationTtl:90*86400});return reply(null,204);
  }catch{return reply({error:'unavailable'},503)}
}
