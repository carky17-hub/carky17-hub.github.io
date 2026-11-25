"""Shared form markup for launch campaign attribution."""
UTM_FIELDS=('utm_source','utm_medium','utm_campaign','utm_content','utm_term')
def fields():
    options=(('','선택 안 함'),('blog','블로그'),('cafe','카페'),('instagram','인스타'),('threads','스레드'),('store_qr','매장 QR'),('other','기타'))
    return '<div data-launch-attribution><label>어디에서 알게 되셨나요? (선택)<select name="acquisitionChannel">'+''.join(f'<option value="{k}">{v}</option>' for k,v in options)+'</select></label>'+''.join(f'<input type="hidden" name="{k}" value="">' for k in UTM_FIELDS)+'</div>'
