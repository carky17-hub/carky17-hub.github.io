"""Read compressed source JSON directly; no extraction into public site."""
import gzip,json
from pathlib import Path

def load_source(path):
    path=Path(path)
    with gzip.open(str(path)+'.gz','rt',encoding='utf-8') as stream:
        return json.load(stream)
