"""Optional OFFLINE print utility. Not invoked by Netlify. Requires reportlab.
Usage: python qr_sticker.py p00138 --font /path/to/Korean.ttf --out sticker.pdf
Add --approved only after the store has consented and the live URL is tested.
"""
import argparse, re
from pathlib import Path
from urllib.parse import urlencode
from source_data import load_source

def main():
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor, white
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics import renderPDF
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('place_id');parser.add_argument('--font',required=True);parser.add_argument('--out',required=True);parser.add_argument('--approved',action='store_true');args=parser.parse_args()
    if not re.fullmatch(r'p\d+',args.place_id):parser.error('Invalid place ID')
    root=Path(__file__).resolve().parent;rows=load_source(root/'source/places-all.json');p=next((p for p in rows if p['id']==args.place_id),None)
    if not p:parser.error('Unknown current place ID')
    url='https://eodigagae.com/place/'+p['id']+'/?'+urlencode({'utm_source':'store_qr','utm_medium':'offline','utm_campaign':'launch','utm_content':p['id']})
    pdfmetrics.registerFont(TTFont('Korean',args.font));c=canvas.Canvas(args.out,pagesize=(105*mm,148*mm));c.setTitle('어디가개 매장 QR 스티커');c.setAuthor('어디가개')
    w,h=105*mm,148*mm;orange=HexColor('#F26B1D');navy=HexColor('#1F2A44');mint=HexColor('#2BB39A')
    c.setFillColor(HexColor('#FFF8F1'));c.rect(0,0,w,h,fill=1,stroke=0);c.setFillColor(orange);c.rect(0,h-30*mm,w,30*mm,fill=1,stroke=0)
    def line(t,y,size,color=navy):
        c.setFillColor(color);c.setFont('Korean',size);c.drawCentredString(w/2,y*mm,t)
    # Brand paw (vector)
    c.setFillColor(white);cx=w/2;cy=137*mm;c.ellipse(cx-4*mm,cy-3.4*mm,cx+4*mm,cy+1.7*mm,fill=1,stroke=0)
    for dx,dy in [(-5,3),(-1.8,5),(1.8,5),(5,3)]:c.circle(cx+dx*mm,cy+dy*mm,1.5*mm,fill=1,stroke=0)
    line('어디가개',122,18,white);line('이 매장은 어디가개 등록 매장',107,16)
    name=p['name'];size=13
    while pdfmetrics.stringWidth(name,'Korean',size)>91*mm and size>7:size-=1
    if pdfmetrics.stringWidth(name,'Korean',size)>91*mm:name=name[:25]+'…'
    line(name,99,size)
    qr=QrCodeWidget(url,barFillColor=navy,barBorder=4);x1,y1,x2,y2=qr.getBounds();side=64*mm;d=Drawing(side,side,transform=[side/(x2-x1),0,0,side/(y2-y1),0,0]);d.add(qr)
    c.setFillColor(white);c.roundRect((w-side)/2-2*mm,30*mm,side+4*mm,side+4*mm,3*mm,fill=1,stroke=0);renderPDF.draw(d,c,(w-side)/2,32*mm)
    line('QR을 찍고 매장 정보를 확인하세요',24,11);line('출시 알림도 신청할 수 있어요',18,10,mint);line('동반 조건은 방문 전 매장에 확인하세요.',11,7)
    if not args.approved:line('검수용 · 매장 동의 및 공개 후 사용',5,8,orange)
    c.showPage();c.save();print(url)
if __name__=='__main__':main()
