// Node web-standard Request/Response; optional actual Workers runtime via --workerd.
import fs from 'node:fs';import assert from 'node:assert/strict';import path from 'node:path';import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),file=path.join(root,'worker/eodigagae-api.bundle.js');
const origin='https://eodigagae.com',base='https://worker.test';let call,dispose=async()=>{};
if(process.argv.includes('--workerd')){
 const {Miniflare}=await import('miniflare');const mf=new Miniflare({modules:true,scriptPath:file,compatibilityDate:'2026-11-01',kvNamespaces:['ANALYTICS_KV'],bindings:{ANALYTICS_ENABLED:'true',ANALYTICS_REPORT_TOKEN:'test-token'}});call=(url,init)=>mf.dispatchFetch(base+url,init);dispose=()=>mf.dispose();
}else{
 const code=fs.readFileSync(file,'utf8');assert(!/^\s*import\s/m.test(code));const worker=(await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'))).default;
 const data=new Map(),kv={async get(k,o){return data.has(k)?o?.type==='json'?JSON.parse(data.get(k)):data.get(k):null},async put(k,v){data.set(k,v)},async list(o){return{keys:[...data.keys()].filter(k=>k.startsWith(o.prefix)).map(name=>({name})),list_complete:true}}};const env={ANALYTICS_ENABLED:'true',ANALYTICS_REPORT_TOKEN:'test-token',ANALYTICS_KV:kv};call=(url,init)=>worker.fetch(new Request(base+url,init),env);
}
try{
 const event=(rows,o=origin)=>call('/analytics-image',{method:'POST',headers:{Origin:o,'Content-Type':'text/plain'},body:JSON.stringify(rows)});
 const good={host:'tong.visitkorea.or.kr',img_load:3,img_error:1};assert.equal((await event([good])).status,200);
 assert.equal((await event([{...good,host:'evil.test'}])).status,400);assert.equal((await event([{...good,url:'https://tong.visitkorea.or.kr/secret'}])).status,400);assert.equal((await event([{...good,host:'tong.visitkorea.or.kr/a'}])).status,400);assert.equal((await event([{...good,img_error:-1}])).status,400);assert.equal((await event([good],'https://evil.test')).status,403);
 assert.equal((await call('/analytics-image-report')).status,401);const result=await call('/analytics-image-report',{headers:{Authorization:'Bearer test-token'}});assert.equal(result.status,200);const x=await result.json();assert.deepEqual(x.totals[good.host],{img_load:3,img_error:1,error_rate:.25});assert(!JSON.stringify(x).includes('/secret'));console.log('image analytics PASS',process.argv.includes('--workerd')?'workerd':'Node mock');
}finally{await dispose()}
