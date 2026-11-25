"""Read-only local main snapshot audit; no API calls, no writes to production data."""
import argparse,copy,json,pathlib,subprocess,sys,types
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from source_data import load_source
from tour24 import shopping_report,shopping_candidate,shopping_state
from tourapi import read,integrate,report
p=argparse.ArgumentParser();p.add_argument('--baseline-ref',help='Git commit/ref before applying v2.4');p.add_argument('--output',type=pathlib.Path);a=p.parse_args()
src=ROOT/'source';records=read(src)['records'];base=load_source(src/'places-all.json');new=copy.deepcopy(base);audit=integrate(src,new);summary=report(src,new,audit)
result={'snapshot_records':len(records),'type38':shopping_report(records),'current':summary,'shopping_candidate_rows':[{'contentId':r['contentId'],'name':r['name'],'cat3':r.get('cat3'),'state':shopping_state(r)} for r in records if shopping_candidate(r)],'fuzzy_matches':[x for x in audit if x.get('matchMethod')=='name-address-distance']}
if a.baseline_ref:
    old=types.ModuleType('tourapi_baseline');old.__file__=str(ROOT/'tourapi.py');raw=subprocess.check_output(['git','show',a.baseline_ref+':tourapi.py'],cwd=ROOT);exec(compile(raw,old.__file__,'exec'),old.__dict__)
    before=copy.deepcopy(base);ba=old.integrate(src,before);prior={x['contentId']:x for x in ba};after={x['contentId']:x for x in audit};resolved=[after[k] for k,v in prior.items() if v['status']=='manual-review' and after.get(k,{}).get('status')=='matched'];changed=[{'contentId':k,'old':v.get('placeId'),'new':after.get(k,{}).get('placeId'),'newStatus':after.get(k,{}).get('status')} for k,v in prior.items() if v['status']=='matched' and (after.get(k,{}).get('placeId')!=v.get('placeId') or after.get(k,{}).get('status')!='matched')];result.update(baseline=old.report(src,before,ba),manual_review_resolved=len(resolved),resolved_records=resolved,changed_previous_matches=changed)
text=json.dumps(result,ensure_ascii=False,indent=2)
if a.output:a.output.write_text(text,encoding='utf-8')
print(text)
