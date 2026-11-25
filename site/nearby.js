'use strict';
// GPS coordinates are kept only in the active page's memory. No location-based URL or upload.
(function(){
const neighbors={
 '서울특별시':['경기도','인천광역시'], '인천광역시':['서울특별시','경기도'],
 '경기도':['서울특별시','인천광역시','강원특별자치도','충청남도','충청북도'],
 '강원특별자치도':['경기도','충청북도','경상북도'],
 '충청북도':['경기도','강원특별자치도','충청남도','대전광역시','세종특별자치시','경상북도','전북특별자치도'],
 '충청남도':['경기도','충청북도','대전광역시','세종특별자치시','전북특별자치도'],
 '대전광역시':['충청남도','충청북도','세종특별자치시'],
 '세종특별자치시':['충청남도','충청북도','대전광역시'],
 '전북특별자치도':['충청남도','충청북도','경상북도','경상남도','전남광주통합특별시','전라남도'],
 '전남광주통합특별시':['전북특별자치도','경상남도'],
 '전라남도':['전북특별자치도','경상남도','광주광역시'], '광주광역시':['전라남도','전남광주통합특별시'],
 '경상북도':['강원특별자치도','충청북도','전북특별자치도','경상남도','대구광역시','울산광역시'],
 '경상남도':['경상북도','대구광역시','울산광역시','부산광역시','전북특별자치도','전남광주통합특별시','전라남도'],
 '대구광역시':['경상북도','경상남도'], '울산광역시':['경상북도','경상남도','부산광역시'], '부산광역시':['울산광역시','경상남도'], '제주특별자치도':[]
};
const rad=n=>n*Math.PI/180;
function valid(lat,lng){return Number.isFinite(lat)&&Number.isFinite(lng)&&Math.abs(lat)<=90&&Math.abs(lng)<=180}
function km(a,b,c,d){const h=Math.sin(rad(c-a)/2)**2+Math.cos(rad(a))*Math.cos(rad(c))*Math.sin(rad(d-b)/2)**2;return 6371.0088*2*Math.asin(Math.sqrt(Math.max(0,Math.min(1,h))))}
function nearest(lat,lng,index){if(!valid(lat,lng)||!index||index.version!==1||!Array.isArray(index.groups))throw Error('위치 데이터 확인 필요');let best='',distance=Infinity;for(const group of index.groups){const [region,points]=group;if(!region||region==='지역 미확인'||!Array.isArray(points))continue;for(const point of points){if(!Array.isArray(point)||!valid(point[0],point[1]))continue;const d=km(lat,lng,point[0],point[1]);if(d<distance){best=region;distance=d}}}if(!best)throw Error('위치 데이터가 없습니다');return {region:best,distance,regions:new Set([best,...(neighbors[best]||[])])}}
window.EGNearby={km,nearest,valid};
})();
