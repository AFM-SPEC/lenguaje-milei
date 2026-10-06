"""Agrega expresiones a la clasificación sin rehacerla entera.

Cada publicación guarda los tramos de texto que definieron su nivel (posiciones en
caracteres y nivel: 0 lema, 1 confrontativo, 2 procaz). Este script busca las
expresiones de REGLAS en los tweets y respuestas (index.html) y en los retweets
(data/*.json) y suma un tramo donde no había otro. Se puede correr varias veces:
lo que ya está marcado no se duplica.

Uso: python3 herramientas/marcar.py            (aplica y muestra el resumen)
     python3 herramientas/marcar.py --probar   (solo muestra qué cambiaría)
"""
import glob, json, os, re, sys, unicodedata
from collections import Counter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEMA, CONFRONTATIVO, PROCAZ = 0, 1, 2  # el lema cuenta según las casillas de la página

def sin_tildes(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')

# --- excepciones -------------------------------------------------------------
ECONOMIA = re.compile(r'^\W*(?:\w+\W+){0,3}?(?:la |el |los |las )?(?:inflacion|precios?|dolar|tipo de cambio|deficit|gasto)')

def domar_no_retorico(texto, m):
    """«domar la inflación», el modelo Harrod-Domar, el periodista Fabián Doman, la doma de caballos."""
    if m.group() in ('Domar', 'Doman'):
        return True
    despues = sin_tildes(texto[m.end():m.end() + 40])
    antes = sin_tildes(texto[max(0, m.start() - 15):m.start()])
    return bool(ECONOMIA.match(despues)) or despues.startswith(' y folklore') or antes.endswith('festival de ') or 'harrod' in antes

# --- reglas: (nombre, expresión, nivel, excepción) ------------------------------
REGLAS = [
    # «VLLC», abreviatura del lema «Viva la libertad, carajo» (también #VLLC, V.L.L.C.); no dentro de enlaces o @usuarios
    ('VLLC', re.compile(r'(?i)(?<![A-Za-z0-9])V\.?\s?L\.?\s?L\.?\s?C(?![A-Za-z0-9])'), LEMA,
     lambda texto, m: texto[max(0, m.start() - 1):m.start()] in ('/', '@', '_')),
    # sigla de «No odiamos lo suficiente a los periodistas»
    ('NOLSALP', re.compile(r'(?i)\bN\.?O\.?L\.?\$?S\.?A\.?(?:L\.?)?P(?![A-Za-z0-9])'), CONFRONTATIVO, None),
    # celebrar que disciplinó o humilló a un adversario
    ('domar', re.compile(r'(?i)\bdom(?:ar(?:l[oa]s?)?|ad[oa]s?|and[oa]|[oó]|aron|ador(?:a|es|as)?|a|an|e|en|é)\b'), CONFRONTATIVO, domar_no_retorico),
    ('de traste', re.compile(r'(?i)\bde\s+traste\b'), CONFRONTATIVO, None),
    ('paliza', re.compile(r'(?i)\bpalizas?\b'), CONFRONTATIVO, None),
    ('humillar', re.compile(r'(?i)\bhumill\w*'), CONFRONTATIVO, None),
    ('KO', re.compile(r'(?<!\w)K\.?O\.?(?!\w)|(?i:\bnocaut\w*|\bknock[\s-]?out\b)'), CONFRONTATIVO, None),
]

NOMBRE_NIVEL = {0: 'convencional', 1: 'confrontativo', 2: 'procaz'}

def nivel(sp):
    ks = set((sp or [])[2::3])
    return 2 if 2 in ks else 1 if 1 in ks else 0

def marcar(texto, sp, por_regla):
    sp = list(sp or [])
    tramos = [tuple(sp[i:i + 3]) for i in range(0, len(sp), 3)]
    n = 0
    for nombre, rx, nv, excluir in REGLAS:
        for m in rx.finditer(texto or ''):
            if excluir and excluir(texto, m):
                continue
            a, b = m.start(), m.end()
            if any(a < y and x < b for x, y, _ in tramos):
                continue
            tramos.append((a, b, nv)); n += 1; por_regla[nombre] += 1
    tramos.sort()
    return [v for t in tramos for v in t], n

def main(probar):
    cambios, por_regla = Counter(), Counter()
    ruta = os.path.join(RAIZ, 'index.html')
    s = open(ruta, encoding='utf-8').read()
    m = re.search(r'(<script type="application/json" id="datos">)(.*?)(</script>)', s, re.S)
    datos = json.loads(m.group(2))
    for r in datos['t']:  # [id, ts, texto, replyTo, quoteTo, rep, rt, likes, views, sp]
        antes = nivel(r[9]); sp, n = marcar(r[2], r[9], por_regla)
        if n:
            r[9] = sp; cambios[('tweets y respuestas', NOMBRE_NIVEL[antes], NOMBRE_NIVEL[nivel(sp)])] += 1
    if not probar:
        s = s[:m.start(2)] + json.dumps(datos, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + s[m.end(2):]
        open(ruta, 'w', encoding='utf-8').write(s)
    for fn in sorted(glob.glob(os.path.join(RAIZ, 'data', '*.json'))):
        d = json.load(open(fn, encoding='utf-8')); tocado = False
        for r in d['t']:  # [id_rt, ts, autor, id_orig, ts_orig, texto, resp_a, cita_a, likes, resp, sp]
            antes = nivel(r[10]); sp, n = marcar(r[5], r[10], por_regla)
            if n:
                r[10] = sp; tocado = True; cambios[('retweets', NOMBRE_NIVEL[antes], NOMBRE_NIVEL[nivel(sp)])] += 1
        if tocado and not probar:
            open(fn, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, separators=(',', ':')))
    print('marcas nuevas por regla:', dict(por_regla))
    for k, v in sorted(cambios.items()):
        print(f'  {k[0]}: {k[1]} -> {k[2]}: {v}')

if __name__ == '__main__':
    main('--probar' in sys.argv)
