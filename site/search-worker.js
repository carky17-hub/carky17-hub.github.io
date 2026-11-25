'use strict';
// Lazy first-party search. Keep fuzzy matching off the browser main thread.
importScripts('/search.js');
let indexPromise;
self.onmessage=async e=>{const {id,raw,limit}=e.data||{};try{indexPromise??=fetch('/data/search-index.json',{cache:'no-cache',credentials:'same-origin'}).then(r=>{if(!r.ok)throw Error('index');return r.json()}).catch(e=>{indexPromise=null;throw e});const index=await indexPromise;self.postMessage({id,results:EGSearch.suggest(index,String(raw||''),Math.min(8,Math.max(1,Number(limit)||8)))})}catch{self.postMessage({id,error:true})}};
