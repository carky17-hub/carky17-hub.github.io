/* v2.3: fresh navigation and code; no cached third-party or business data. */
const CORE_CACHE='eg-public-v230-core';
self.addEventListener('install',e=>e.waitUntil(caches.open(CORE_CACHE).then(c=>c.add('/offline.html')).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('eg-public-')&&k!==CORE_CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{const r=e.request,u=new URL(r.url);if(r.method!=='GET'||u.origin!==location.origin)return;
 if(r.mode==='navigate'){e.respondWith(fetch(r,{cache:'no-cache'}).catch(()=>caches.match('/offline.html')));return}
 if(/\.(?:js|css)$/.test(u.pathname)){e.respondWith(fetch(r,{cache:'no-cache'}));return}
 if(u.pathname==='/offline.html')e.respondWith(fetch(r).catch(()=>caches.match('/offline.html')));
});
