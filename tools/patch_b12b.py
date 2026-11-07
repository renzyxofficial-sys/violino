p='plugin/ui/app.js'
a=open(p,encoding='utf-8').read()
o="""  if (!root.firstElementChild) { adopt(next); root.appendChild(next); } else morph(root.firstElementChild, next);
}"""
assert a.count(o)==1
a=a.replace(o,"""  if (!root.firstElementChild) { adopt(next); root.appendChild(next); } else morph(root.firstElementChild, next);
  // troca de aba: o morph reaproveita o contêiner, então a animação de entrada é reiniciada à mão
  const tabNow = L.tab ?? (S && S.prefs && S.prefs.tab) ?? 'perf';
  if (L.lastTab !== tabNow) {
    L.lastTab = tabNow;
    const el = root.querySelector('.tabin');
    if (el) { el.style.animation = 'none'; void el.offsetWidth; el.style.animation = ''; }
  }
}""")
open(p,'w',encoding='utf-8').write(a)
print('ok')
