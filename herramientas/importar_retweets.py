"""Suma retweets de un conjunto externo al CSV de retweets y a la web, sin duplicar.

Formato aceptado: el CSV público de milei.nulo.lol (https://milei.nulo.lol/api/datasets/retweets.csv,
del proyecto github.com/catdevnull/milei-twitter, que registra los retweets de Milei cada media hora
desde febrero de 2024) con las columnas retweetAt, postedAt, posterId, posterHandle, postId, textPreview.
Trae la hora exacta del retweet; no trae el nombre del autor ni sus métricas.

Uso: python3 herramientas/importar_retweets.py ARCHIVO.csv [--probar]
"""
import csv, os, re, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from actualizar import (COLS_RT, CSV_RT, leer_csv, escribir_csv, leer_index, sumar_retweets_web,
                        escribir_index_y_readme, log)
import time


def iso_z(s):  # 2026-10-06T16:45:20.000Z
    return s[:19] + '.000Z' if s else ''

def fila(r):
    txt = (r['textPreview'] or '').strip()
    # las respuestas traen las menciones al principio: se sacan, como en el resto de los datos
    lead = re.match(r'^(?:@\w+\s+)+', txt)
    resp = ''
    if lead and txt[lead.end():].strip():
        resp = re.match(r'@(\w+)', txt).group(1)
        txt = txt[lead.end():].strip()
    autor = r['posterHandle'] or ''
    return {'id_retweet': '', 'fecha_retweet': iso_z(r['retweetAt']), 'autor_original': autor, 'nombre_autor': '',
            'id_original': r['postId'], 'fecha_original': iso_z(r['postedAt']), 'texto': txt,
            'link_original': f"https://x.com/{autor}/status/{r['postId']}", 'respuesta_a': resp, 'cita_a': '',
            'likes_original': '', 'respuestas_original': '', 'fecha_aproximada': ''}

def main(ruta, probar):
    externos = [r for r in csv.DictReader(open(ruta, encoding='utf-8'))
                if re.match(r'\d{4}-\d\d-\d\dT', r.get('retweetAt') or '') and (r.get('postId') or '').isdigit()]
    filas_rt = leer_csv(CSV_RT)
    ya = {r['id_original'] for r in filas_rt}
    nuevos, vistos = [], set()
    for r in externos:
        if r['postId'] in ya or r['postId'] in vistos:
            continue
        vistos.add(r['postId']); nuevos.append(fila(r))
    log(f'{len(externos)} retweets en el archivo, {len(nuevos)} nuevos')
    print('  por año:', sorted(Counter(r['fecha_retweet'][:4] for r in nuevos).items()))
    if probar or not nuevos:
        return
    escribir_csv(CSV_RT, sorted(filas_rt + nuevos, key=lambda r: r['fecha_retweet'], reverse=True), COLS_RT)
    s, m, datos = leer_index()
    sumar_retweets_web(datos, nuevos)
    escribir_index_y_readme(s, m, datos, int(time.time()))


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    main(args[0], '--probar' in sys.argv)
