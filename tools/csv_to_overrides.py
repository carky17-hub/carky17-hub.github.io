"""Convert reviewed v2.5 CSV to operator overrides. Dry-run by default; no API calls."""
import argparse,csv,json,pathlib,re,sys,os,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
HEAD=['contentId','관광공사명','관광공사 주소','후보 placeId','후보업체명','후보업체 주소','거리(m,정확좌표)','이름 유사도(%)','관광공사 허용사진','후보 자체/관광사진','후보수','결정(placeId/new/skip)']
CID=re.compile(r'[0-9]{1,12}'); PID=re.compile(r'p[0-9]+')
def parse_csv(path,encoding='utf-8-sig'):
    decisions={}; candidates={}; blanks=0
    with path.open(encoding=encoding,newline='') as f:
        reader=csv.reader(f);header=next(reader,[])
        if [x.strip() for x in header]!=HEAD:raise ValueError('CSV header differs from v2.5 review export; use original CSV')
        for i,row in enumerate(reader,2):
            if not row or not any(x.strip() for x in row):continue
            if len(row)!=len(HEAD):raise ValueError(f'line {i}: wrong column count')
            cid,target,pick=(row[j].strip() for j in (0,3,11))
            if not CID.fullmatch(cid) or (target and not PID.fullmatch(target)):raise ValueError(f'line {i}: invalid contentId/candidate ID')
            candidates.setdefault(cid,set()).add(target)
            if not pick:blanks+=1;continue
            if pick not in ('new','skip') and not PID.fullmatch(pick):raise ValueError(f'line {i}: invalid decision (use exact p123/new/skip)')
            if cid in decisions and decisions[cid]!=pick:raise ValueError(f'line {i}: conflicting decisions for {cid}')
            decisions[cid]=pick
    for cid,pick in decisions.items():
        if PID.fullmatch(pick) and pick not in candidates[cid]:raise ValueError(f'{cid}: decision not in exported candidates; regenerate CSV or review separately')
    return decisions,blanks

def pairs(items):
    out={}
    for k,v in items:
        if k in out:raise ValueError('duplicate JSON key: '+k)
        out[k]=v
    return out

def merge(old,new,replace=False):
    if not isinstance(old,dict):raise ValueError('existing overrides must be an object')
    for k,v in old.items():
        if not isinstance(k,str) or not CID.fullmatch(k) or not isinstance(v,str) or not(v in ('new','skip') or PID.fullmatch(v)):raise ValueError('invalid existing decision: '+str(k))
    out=dict(old)
    for k,v in new.items():
        if k in out and out[k]!=v and not replace:raise ValueError(f'existing decision conflict: {k}; use --replace-existing only after review')
        out[k]=v
    used={}
    for k,v in out.items():
        if PID.fullmatch(v):
            if v in used:raise ValueError(f'duplicate placeId {v}: {used[v]}, {k}')
            used[v]=k
    return out

def validate(root,decisions,merged):
    # Use exactly the same policy as v2.5 build. No silent fallback if missing.
    sys.path.insert(0,str(root))
    from source_data import load_source
    from tourapi import read,region
    from tour24 import eligible,compatible
    from tour25 import load_overrides
    src=root/'source'; records=read(src)['records']; places=load_source(src/'places-all.json')
    known={str(r['contentId']) for r in records}
    missing=set(decisions)-known
    if missing:raise ValueError('CSV contentId no longer in current snapshot: '+', '.join(sorted(missing)))
    # v2.5 validator takes a source directory; validate in temporary isolated directory.
    with tempfile.TemporaryDirectory() as d:
        p=pathlib.Path(d);(p/'tour-match-overrides.json').write_text(json.dumps(merged),encoding='utf-8')
        load_overrides(p,records,places,eligible,compatible,region)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('csv',type=pathlib.Path);ap.add_argument('--root',type=pathlib.Path,default=ROOT);ap.add_argument('--encoding',choices=['utf-8-sig','cp949'],default='utf-8-sig');ap.add_argument('--apply',action='store_true');ap.add_argument('--replace-existing',action='store_true');a=ap.parse_args()
    try:
        root=a.root.resolve();dst=root/'source/tour-match-overrides.json';decisions,blanks=parse_csv(a.csv,a.encoding)
        old=json.loads(dst.read_text(encoding='utf-8-sig'),object_pairs_hook=pairs) if dst.exists() else {}
        merged=merge(old,decisions,a.replace_existing);validate(root,decisions,merged)
        changed=sum(old.get(k)!=v for k,v in decisions.items());print(json.dumps({'decisions':len(decisions),'blank_rows':blanks,'changed':changed,'total':len(merged),'apply':a.apply},ensure_ascii=False))
        if a.apply and changed:
            # Atomic replace only after all validation. Existing output is not changed on errors.
            fd,tmp=tempfile.mkstemp(prefix='.tour-overrides-',dir=dst.parent)
            try:
                with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(dict(sorted(merged.items())),f,ensure_ascii=False,indent=2);f.write('\n')
                os.replace(tmp,dst)
            finally:
                if os.path.exists(tmp):os.unlink(tmp)
        elif not a.apply:print('DRY RUN: no files written; add --apply to save')
    except (ValueError,OSError,ImportError,KeyError) as e:sys.exit('STOP: '+str(e))
if __name__=='__main__':main()
