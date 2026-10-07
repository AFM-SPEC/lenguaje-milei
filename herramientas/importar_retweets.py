"""Suma retweets de un conjunto externo al CSV de retweets y a la web, sin duplicar.

Formato aceptado: el CSV público de milei.nulo.lol (https://milei.nulo.lol/api/datasets/retweets.csv,
del proyecto github.com/catdevnull/milei-twitter, que registra los retweets de Milei cada media hora
desde febrero de 2024) con las columnas retweetAt, postedAt, posterId, posterHandle, postId, textPreview.
Trae la hora exacta del retweet; no trae el nombre del autor ni sus métricas.

Uso: python3 herramientas/importar_retweets.py ARCHIVO.csv [--probar]
"""
import os, sys, time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from actualizar import (COLS_RT, CSV_RT, leer_csv, escribir_csv, leer_index, sumar_retweets_web,
                        escribir_index_y_readme, log, fila_nulo, leer_nulo, precisar_retweets)


def main(ruta, probar):
    externos = leer_nulo(ruta)
    filas_rt = leer_csv(CSV_RT)
    ya = {r['id_original'] for r in filas_rt}
    nuevos, vistos = [], set()
    for r in externos:
        if r['postId'] in ya or r['postId'] in vistos:
            continue
        vistos.add(r['postId']); nuevos.append(fila_nulo(r))
    log(f'{len(externos)} retweets en el archivo, {len(nuevos)} nuevos')
    print('  por año:', sorted(Counter(r['fecha_retweet'][:4] for r in nuevos).items()))
    exactos = {f['id_original']: f['fecha_retweet'] for f in map(fila_nulo, externos)}
    a_precisar = sum(1 for r in filas_rt if r['fecha_aproximada'] and not r['id_retweet'] and r['id_original'] in exactos)
    print(f'  con hora estimada que pasan a exacta: {a_precisar}')
    if probar or not (nuevos or a_precisar):
        return
    s, m, datos = leer_index()
    sumar_retweets_web(datos, nuevos)
    filas_rt = filas_rt + nuevos
    precisar_retweets(datos, filas_rt, exactos)
    escribir_csv(CSV_RT, sorted(filas_rt, key=lambda r: r['fecha_retweet'], reverse=True), COLS_RT)
    escribir_index_y_readme(s, m, datos, int(time.time()))


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    main(args[0], '--probar' in sys.argv)
