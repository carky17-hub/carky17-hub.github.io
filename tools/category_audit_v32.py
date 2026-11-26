"""Inspect raw main gzip and export ambiguous decisions OUTSIDE repository."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from category32 import read_raw,scan,write_review,apply_overrides

def main():
    a=argparse.ArgumentParser();a.add_argument('--root',type=Path,default=ROOT);a.add_argument('--review-csv',type=Path,required=True);a.add_argument('--write-overrides',action='store_true');o=a.parse_args();root=o.root.resolve();out=o.review_csv.expanduser().resolve()
    if out.is_relative_to(root):raise SystemExit('CSV must be outside repository (e.g. Desktop).')
    if out.exists():raise SystemExit('CSV exists; choose a new path to preserve manual notes.')
    src=root/'source';raw=read_raw(src);overrides,review=scan(raw);dest=src/'category-overrides.json'
    if o.write_overrides and dest.exists():raise SystemExit('Existing override file preserved. Review and replace explicitly after source changes.')
    report=apply_overrides(raw,src,overrides);write_review(out,review)
    if o.write_overrides:dest.write_text(json.dumps(overrides,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({**report,'reviewCount':len(review),'csv':str(out)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
