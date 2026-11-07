import os
os.chdir(r"C:\Users\TheoH\violino")
t=open('tools/b4_transport.txt',encoding='utf-8').read()
o='''      <button onClick="{{toggleLib}}" class="tpb lg-icon" title="Classical library (Mutopia) and Import MIDI" style="padding: 0 11px; background: {{t.fill}};">♫ Library</button>
'''
assert t.count(o)==1; t=t.replace(o,'')
t=t.replace('<span style="font-size: 12px; font-weight: 600; color: {{t.secondary}}; padding: 0 4px;">4 / 4</span>','<span style="font-size: 12px; font-weight: 600; color: {{t.secondary}}; padding: 0 4px; white-space: nowrap;">4 / 4</span>')
open('tools/b4_transport.txt','w',encoding='utf-8').write(t)
b=open('plugin/ui/build_ui.py',encoding='utf-8').read()
i=b.index('TRANSPORT = """'); j=b.index('"""', i+15)
b=b[:i]+'TRANSPORT = """'+t+b[j:]
anchor="sub('<button aria-label=\"Settings\"'"
assert b.count(anchor)==1
b=b.replace(anchor,'''sub('<span style="display: flex; align-items: center; gap: 6px; padding: 0 6px; font-size: 12px; color: {{t.secondary}};">', '<button onClick="{{toggleLib}}" title="Classical library (Mutopia) and Import MIDI" style="height: 44px; padding: 0 16px; border: 0; border-radius: 22px; color: {{t.text}}; font-size: 13px; font-weight: 600; cursor: pointer; white-space: nowrap; {{t.glass}}">♫ Library</button><span style="display: flex; align-items: center; gap: 6px; padding: 0 6px; font-size: 12px; color: {{t.secondary}};">')
'''+anchor,1)
open('plugin/ui/build_ui.py','w',encoding='utf-8').write(b)
print('ok')
