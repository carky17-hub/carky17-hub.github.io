"""Read compressed source JSON directly; no extraction into public site."""
import gzip,json
from pathlib import Path

def load_source(path):
    path=Path(path)
    with gzip.open(str(path)+'.gz','rt',encoding='utf-8') as stream:
        data=json.load(stream)
    if path.name=='places-all.json':
        ex=path.parent/'excluded-places.json'
        if ex.exists():
            drop={r['id'] for r in json.loads(ex.read_text(encoding='utf-8'))}
            data=[p for p in data if p.get('id') not in drop] if isinstance(data,list) else data
    return data
