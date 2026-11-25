import gzip,json,re,sys,csv,collections
src=sys.argv[1]; out_csv=sys.argv[2]
rows=json.load(gzip.open(src))
CAFE=re.compile(r'커피|카페|까페|cafe|caffe|coffee|베이커리|bakery|제과|디저트|dessert|브런치|베이글|도넛|도너츠|케이크|케익|cake|티하우스|찻집|다방|로스터|roaster|roastery|젤라또|gelato|빙수|와플|마카롱|빵집|크로플|스콘|에스프레소|espresso|라떼|latte',re.I)
REST=re.compile(r'식당|국밥|고기|갈비|삼겹|횟집|수산|치킨|피자|pizza|버거|burger|파스타|pasta|스시|초밥|라멘|우동|소바|분식|김밥|족발|보쌈|곱창|막창|냉면|칼국수|국수|찌개|백반|한식|중식|일식|양식|짬뽕|짜장|반점|돈까스|돈가스|덮밥|포차|이자카야|비스트로|bistro|레스토랑|restaurant|그릴|grill|bbq|바베큐|스테이크|steak|타코|taco|쌀국수|팟타이|카레|(?<!베이)(?<!케이)커리|curry|샤브|훠궈|마라|순대|떡볶이|해장국|소고기|한우|정육|횟|밥상|밥집|키친|kitchen|다이닝|dining|펍|pub|맥주|호프|와인바|술집',re.I)
PETCARE=re.compile(r'(애견|펫|pet|도그|dog|강아지|고양이|캣|cat|멍|댕).*(호텔|유치원|돌봄|스테이|stay|하우스)|(호텔|유치원|스테이).*(애견|펫|도그|강아지|멍|댕)',re.I)
LODGE=re.compile(r'펜션|리조트|resort|글램핑|캠핑장|풀빌라|게스트하우스|모텔|민박|한옥스테이|호스텔|콘도',re.I)
moved=collections.Counter(); audit=[]
def setsv(p,old,new):
  sv=[new if s==old else s for s in p['services']]; sv=list(dict.fromkeys(sv)); p['services']=sv
  if p.get('category')==old: p['category']=new
for p in rows:
  sv=p.get('services') or []; n=p.get('name','') or ''; srcn=p.get('source','') or ''
  food='식약처' in srcn
  c=bool(CAFE.search(n)); r=bool(REST.search(n))
  if food and '식당' in sv and c and not r and '카페' not in sv:
    setsv(p,'식당','카페'); moved['식당→카페']+=1; audit.append((p['id'],n,'식당→카페','자동'))
  elif food and '카페' in sv and r and not c and '식당' not in sv:
    setsv(p,'카페','식당'); moved['카페→식당']+=1; audit.append((p['id'],n,'카페→식당','자동'))
  elif food and ('식당' in sv or '카페' in sv) and c and r:
    for add in ('카페','식당'):
      if add not in p['services']: p['services'].append(add)
    moved['카페+식당 둘다']+=1; audit.append((p['id'],n,'카페+식당','자동(둘 다 해당)'))
  if '숙소' in sv and PETCARE.search(n) and not LODGE.search(n) and '농림축산식품부' in srcn and '문화정보원' not in srcn:
    setsv(p,'숙소','호텔·유치원'); moved['숙소→호텔·유치원']+=1; audit.append((p['id'],n,'숙소→호텔·유치원','자동'))
  if '호텔·유치원' in p['services'] and LODGE.search(n) and not re.search(r'호텔|유치원|돌봄',n) and '숙소' not in p['services']:
    p['services'].append('숙소'); moved['애견펜션 숙소 추가']+=1; audit.append((p['id'],n,'호텔·유치원+숙소','자동(펜션·민박명)'))
json.dump(rows,gzip.open(src,'wt',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
with open(out_csv,'w',newline='',encoding='utf-8-sig') as f:
  w=csv.writer(f);w.writerow(['id','업체명','변경/현재분류','처리']);w.writerows(audit)
print(dict(moved), 'audit',len(audit), collections.Counter(a[3] for a in audit))
