p='plugin/ui/build_ui.py'
b=open(p,encoding='utf-8').read()
def rep(o,n,c=1):
    global b
    assert b.count(o)==c,(b.count(o),o[:70]); b=b.replace(o,n)
rep('''  <sc-if value="{{isPerf}}">
    <div style="position: absolute; left: 0; right: 0; top: 0; bottom: 150px;">''','''  <sc-if value="{{isPerf}}">
    <div class="tabin" style="position: absolute; left: 0; right: 0; top: 0; bottom: 150px;">''')
rep('''  <sc-if value="{{isFx}}">
    <div style="position: absolute; left: 280px; top: 124px; width: 766px; height: 580px;">''','''  <sc-if value="{{isFx}}">
    <div class="tabin" style="position: absolute; left: 280px; top: 124px; width: 766px; height: 580px;">''')
rep('''  <sc-if value="{{isScore}}">
    <div style="position: absolute;''','''  <sc-if value="{{isScore}}">
    <div class="tabin" style="position: absolute;''')
rep('''@keyframes popIn{{''','''@keyframes tabIn{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:none}}}}
.tabin{{animation:tabIn .28s cubic-bezier(.2,.8,.2,1) both}}
@keyframes popIn{{''')
open(p,'w',encoding='utf-8').write(b)
print('ok')
