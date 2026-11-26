"""사장님 제공 사진 승인 반영 도구 (관리자용, 네트워크 없음).

사용:
  python3 tools/add_owner_photo.py p03247 사진1.jpg 사진2.jpg --credit "매장명 제공" --caption "매장 실내"
        --rights --portrait [--visitor]

- 구글폼 '사진 사용·개인정보 동의'에 체크한 신청만 --rights 를 붙인다.
- 사진에 사람 얼굴이 알아볼 수 있게 나오면 동의를 따로 받은 경우에만 --portrait 를 붙인다.
- 1200px WebP 로 변환(EXIF·위치정보 제거), 픽셀 해시로 중복을 막고, 매장당 최대 10장.
"""
import argparse, datetime, hashlib, io, json, pathlib, sys
from PIL import Image, ImageOps

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / 'source'
MAX_SIDE = 1200


def pixel_hash(im):
    # 크기·포맷이 달라도 같은 사진이면 같은 값이 나오도록 16x16 흑백 평균 해시를 쓴다.
    g = im.convert('L').resize((16, 16), Image.LANCZOS)
    px = list(g.tobytes()); avg = sum(px) / len(px)
    bits = ''.join('1' if v >= avg else '0' for v in px)
    return hashlib.sha1(bits.encode()).hexdigest()[:12]


def convert(path):
    im = Image.open(path)
    im = ImageOps.exif_transpose(im).convert('RGB')
    im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    buf = io.BytesIO(); q = 82
    while True:
        buf.seek(0); buf.truncate(); im.save(buf, 'WEBP', quality=q, method=6)
        if buf.tell() <= 600_000 or q <= 50: break
        q -= 8
    return im, buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('place'); ap.add_argument('files', nargs='+')
    ap.add_argument('--credit', required=True); ap.add_argument('--caption', default='매장 사진')
    ap.add_argument('--rights', action='store_true'); ap.add_argument('--portrait', action='store_true')
    ap.add_argument('--visitor', action='store_true'); ap.add_argument('--ad', action='store_true')
    a = ap.parse_args()
    if not (a.rights and a.portrait):
        sys.exit('게시 권한(--rights)과 인물 확인(--portrait)이 둘 다 확인된 사진만 올릴 수 있어요.')
    table = SRC / ('visitor-photos.json' if a.visitor else 'owner-photos.json')
    rows = json.loads(table.read_text(encoding='utf-8'))
    allrows = json.loads((SRC / 'owner-photos.json').read_text(encoding='utf-8')) + json.loads((SRC / 'visitor-photos.json').read_text(encoding='utf-8'))
    out = SRC / 'public-photos'; out.mkdir(exist_ok=True)
    seen = {r['id'].rsplit('-', 1)[-1] for r in allrows}
    count = sum(r['placeId'] == a.place for r in allrows)
    today = datetime.date.today().isoformat(); added = []
    for f in a.files:
        if count >= 10: print('매장당 10장 한도 — 나머지 생략'); break
        im, data = convert(f); h = pixel_hash(im)
        if h in seen: print('중복 사진 생략:', f); continue
        pid = f'{a.place}-{h}'; name = pid + '.webp'
        (out / name).write_bytes(data); seen.add(h); count += 1
        r = {'id': pid, 'placeId': a.place, 'filename': name, 'caption': a.caption[:150], 'credit': a.credit[:100],
             'approved': True, 'rightsConfirmed': True, 'portraitConfirmed': True, 'publishedOn': today}
        if a.visitor: r.update(visitConfirmed=True, advertising=bool(a.ad))
        else: r['ownerConfirmed'] = True
        rows.append(r); added.append(name)
        print(f'추가: {name} {im.size[0]}x{im.size[1]} {len(data)//1024}KB')
    table.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'{len(added)}장 반영 → source/public-photos/, {table.name}')


if __name__ == '__main__':
    main()
