// No Kakao key/network. Test the actual map sheet photo helper with a DOM stub.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
class El { constructor(tag){this.tagName=tag;this.children=[];this.events={};} append(...args){this.children.push(...args)} addEventListener(k,f){this.events[k]=f} remove(){this.removed=true} }
const window={},document={createElement:t=>new El(t),getElementById:()=>null,addEventListener:()=>{}};
const file=path.resolve(__dirname,'../site/kakao-map.js');const code=fs.readFileSync(file,'utf8');assert(code.includes('function selectRows(list){'));
const ctx={window,document,URL,console};vm.runInNewContext(code.replace('function selectRows(list){','window.testMapPhoto=mapPhoto;function selectRows(list){'),ctx);
const photo=window.testMapPhoto;assert.equal(typeof photo,'function');assert.equal(photo({name:'a'}),null);
const t={name:'a',tourPhoto:{src:'https://tong.visitkorea.or.kr/a.jpg',license:'3',caption:'test'}};
let f=photo(t);assert.equal(f.children[0].src,t.tourPhoto.src);assert(f.children[1].textContent.includes('공공누리 3유형'));assert.equal(f.children[1].children[1].href,'https://www.data.go.kr/data/15135102/openapi.do');f.children[0].events.error();assert(f.removed);
assert.equal(photo({...t,tourPhoto:{...t.tourPhoto,src:'https://evil.test/a.jpg'}}),null);assert.equal(photo({...t,tourPhoto:{...t.tourPhoto,license:'2'}}),null);
f=photo({...t,ownerPhoto:{src:'/approved-photos/local.jpg',label:'사장님 제공',credit:'매장'}});assert.equal(f.children[0].src,'/approved-photos/local.jpg');assert(f.children[1].textContent.includes('사장님 제공'));
console.log('v2.5 map thumbnail: local priority, licensed URL, credit and error fallback PASS');
