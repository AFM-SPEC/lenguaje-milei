"""Suma los «me gusta» de Milei (nov 2023 – jun 2024) al CSV milei_megusta.csv y a la web.

X hizo privados los «me gusta» el 12 de junio de 2024, así que este conjunto no crece. Fuentes, del
proyecto abierto milei.nulo.lol (github.com/catdevnull/milei-twitter):
- el CSV https://milei.nulo.lol/api/datasets/likes.csv (feb – jun 2024; la fecha es la del momento en que
  su scraper vio el «me gusta»);
- sitio/src/lib/db/historicLikes/likes.tsv.br (nov 2023 – feb 2024, con fecha estimada).
El texto de cada tweet se baja aparte del servicio de tweets incrustados de X.

Entradas: BASE (lista unificada: [{id, autor, like_ts, fuente}]) y SYND (jsonl con el tweet de cada id).
Uso: python3 herramientas/importar_megusta.py BASE.json SYND.jsonl [--probar]
"""
import csv, html, json, os, re, sys, time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from actualizar import DIR_CSV, RAIZ, OFF, escribir_csv, leer_index, escribir_index_y_readme, iso, mk, num, log, ts_de
from clasificar import tramos

CSV_MG = os.path.join(DIR_CSV, 'milei_megusta.csv')
COLS_MG = ['fecha_megusta', 'autor', 'nombre_autor', 'id_tweet', 'fecha_tweet', 'texto', 'link', 'respuesta_a', 'cita_a',
           'likes_tweet', 'respuestas_tweet', 'fuente', 'disponible']
POR_ARCHIVO = 25000


def utf16(s, a, b):
    e = s.encode('utf-16-le')
    return e[2 * a:2 * b].decode('utf-16-le', errors='ignore')


def texto(t):
    s = t.get('text') or ''
    rango = t.get('display_text_range')
    if rango:
        s = utf16(s, rango[0], rango[1])
    for corto, largo in t.get('urls') or []:
        if corto:
            s = s.replace(corto, largo or corto)
    return html.unescape(s).strip()


def main(base_ruta, synd_ruta, probar):
    base = {x['id']: x for x in json.load(open(base_ruta))}
    synd = {}
    for l in open(synd_ruta):
        r = json.loads(l); synd[r['id']] = r
    filas = []
    for i, b in base.items():
        r = synd.get(i)
        t = (r or {}).get('t')
        autor, nombre = (t['user'] if t else [b['autor'], ''])
        filas.append({'fecha_megusta': iso(b['like_ts']), 'autor': autor or b['autor'], 'nombre_autor': nombre or '',
                      'id_tweet': i, 'fecha_tweet': (t['created_at'][:19] + '.000Z') if t and t.get('created_at') else '',
                      'texto': texto(t) if t else '', 'link': f"https://x.com/{autor or b['autor']}/status/{i}",
                      'respuesta_a': (t or {}).get('in_reply_to_screen_name') or '', 'cita_a': (t or {}).get('quoted') or '',
                      'likes_tweet': (t or {}).get('favorite_count', ''), 'respuestas_tweet': (t or {}).get('conversation_count', ''),
                      'fuente': 'milei.nulo.lol' if b['fuente'] == 'nulo' else 'histórico (milei.nulo.lol)',
                      'disponible': 'si' if t else ('borrado' if r else 'sin consultar')})
    filas.sort(key=lambda f: f['fecha_megusta'], reverse=True)
    c = Counter(f['disponible'] for f in filas)
    log(f'{len(filas)} me gusta: {dict(c)}')
    if probar:
        return
    escribir_csv(CSV_MG, filas, COLS_MG)
    # web: solo los que tienen el tweet (los borrados no tienen texto ni autor confiable)
    s, m, datos = leer_index()
    for e in datos.get('megusta', []):
        try: os.remove(os.path.join(RAIZ, e['f']))
        except FileNotFoundError: pass
    datos['megusta'] = []
    por_anio = {}
    for f in sorted((f for f in filas if f['disponible'] == 'si'), key=lambda f: f['fecha_megusta']):
        ts = ts_de(f['fecha_megusta'])
        por_anio.setdefault(time.gmtime(ts - OFF).tm_year, []).append((ts, f))
    for y, grupo in sorted(por_anio.items()):
        for k in range(0, len(grupo), POR_ARCHIVO):
            parte = grupo[k:k + POR_ARCHIVO]
            autores, d = {}, {'a': [], 't': []}
            for ts, f in parte:
                if f['autor'] not in autores:
                    autores[f['autor']] = len(d['a']); d['a'].append([f['autor'], f['nombre_autor']])
                ots = ts_de(f['fecha_tweet']) if f['fecha_tweet'] else None
                d['t'].append(['', ts, autores[f['autor']], f['id_tweet'], ots, f['texto'], f['respuesta_a'], f['cita_a'],
                               num(f['likes_tweet']), num(f['respuestas_tweet']), tramos(f['texto'])])
            ruta = f'data/megusta-{y}-{k // POR_ARCHIVO + 1}.json'
            with open(os.path.join(RAIZ, ruta), 'w', encoding='utf-8') as fo:
                fo.write(json.dumps(d, ensure_ascii=False, separators=(',', ':')))
            datos['megusta'].append({'f': ruta, 'n': len(d['t']), 'mk0': mk(d['t'][0][1]), 'mk1': mk(d['t'][-1][1])})
    escribir_index_y_readme(s, m, datos, int(time.time()))
    log(f"web: {sum(e['n'] for e in datos['megusta'])} me gusta en {len(datos['megusta'])} archivos")


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    main(args[0], args[1], '--probar' in sys.argv)
