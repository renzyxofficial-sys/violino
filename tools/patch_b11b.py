p='plugin/ui/build_ui.py'
b=open(p,encoding='utf-8').read()
o='''      <div aria-label="Score tools" style="position: absolute; right: 14px; top: 12px; display: flex; gap: 3px; align-items: center;">
        <sc-for list="{{scoreTools}}" as="b"><button onClick="{{b.pick}}" title="{{b.title}}" class="scb" style="background: {{b.bg}}; color: {{b.fg}};">{{b.label}}</button></sc-for>
        <span style="width: 8px;"></span>
        <sc-for list="{{scoreDurs}}" as="b">'''
n='''      <div aria-label="Score tools" style="position: absolute; left: 14px; top: 12px; display: flex; gap: 3px; align-items: center;">
        <sc-for list="{{scoreTools}}" as="b"><button onClick="{{b.pick}}" title="{{b.title}}" class="scb" style="background: {{b.bg}}; color: {{b.fg}};">{{b.label}}</button></sc-for>
        <span style="width: 8px;"></span>
        ACCPLACE
      </div>
      <div aria-label="Note values" style="position: absolute; right: 14px; top: 12px; display: flex; gap: 3px; align-items: center;">
        <sc-for list="{{scoreDurs}}" as="b">'''
assert b.count(o)==1; b=b.replace(o,n)
acc='''<sc-for list="{{scoreAcc}}" as="b"><button onClick="{{b.pick}}" title="{{b.title}}" class="scb" style="background: {{b.bg}}; color: {{b.fg}}; font-family: 'Segoe UI Symbol', serif; font-size: 15px;">{{b.label}}</button></sc-for>'''
o2='''
        <span style="width: 8px;"></span>
        '''+acc
assert b.count(o2)==1; b=b.replace(o2,'')
b=b.replace('ACCPLACE',acc)
open(p,'w',encoding='utf-8').write(b)
print('ok')
