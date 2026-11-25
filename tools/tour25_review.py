"""Export current main's pending human review rows without building or calling APIs."""
import argparse,pathlib,sys,json
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from source_data import load_source
from tourapi import integrate,read,point,km,report
from tour24 import clean_name
from tour25 import review_csv
from owner_photos import load_owner_photos

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=pathlib.Path,default=ROOT/'internal'/'tour-match-review.csv');args=ap.parse_args()
    src=ROOT/'source';places=load_source(src/'places-all.json');audit=integrate(src,places)
    # Include rights-cleared local photo flags; do not copy any images.
    merged=load_source(src/'merged-ids.json');load_owner_photos(src,places,merged)
    n,k=review_csv(args.output,read(src)['records'],places,audit,point,km,clean_name)
    print(json.dumps({'manual_review_cases':n,'candidate_rows':k,'csv':str(args.output),'summary':report(src,places,audit)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
