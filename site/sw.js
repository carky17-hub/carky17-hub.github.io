const CORE_CACHE='eg-public-v180-core';const CORE=['/offline.html','/bundle.css','/brand.svg'];
self.addEventListener('install',e=>e.waitUntil(caches.open(CORE_CACHE).then(c=>c.addAll(CORE))));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('eg-public-')&&k!==CORE_CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{const r=e.request,u=new URL(r.url);if(r.method!=='GET'||u.origin!==location.origin)return;if(r.mode==='navigate'){e.respondWith(fetch(r).catch(()=>caches.match('/offline.html')));return}if(u.search||!CORE.includes(u.pathname))return;e.respondWith(fetch(r).catch(()=>caches.match(r)))});
