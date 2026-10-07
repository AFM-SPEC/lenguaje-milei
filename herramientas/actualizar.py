"""Suma los tweets, respuestas y retweets nuevos de @JMilei y publica la web.

Busca en X a través de FxTwitter (gratis, sin clave) desde lo último cargado hasta
ahora: tweets y respuestas por día, con 3 días de solapamiento para refrescar las
métricas y atrapar lo que X indexa tarde; retweets por hora, con un día de
solapamiento (X solo deja buscar los retweets de la última semana, por eso hay que
correrlo seguido). Clasifica lo nuevo con las mismas listas (clasificar.py),
actualiza los tres CSV de la carpeta de arriba del repo, index.html y data/, y hace
commit + push para que GitHub Pages publique.

Si FxTwitter no responde, corta sin escribir nada: la próxima corrida retoma desde
el mismo punto.

Uso: python3 herramientas/actualizar.py             (actualiza y publica)
     python3 herramientas/actualizar.py --sin-push  (actualiza sin publicar)
     python3 herramientas/actualizar.py --probar    (busca e informa, no escribe)
"""
import csv, fcntl, html, json, os, re, subprocess, sys, time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clasificar import tramos

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_CSV = os.path.dirname(RAIZ)  # ~/Downloads/Claude
CSV_TW, CSV_RESP, CSV_RT = (os.path.join(DIR_CSV, f) for f in ('milei_tweets.csv', 'milei_respuestas.csv', 'milei_retweets.csv'))
COLS = ['id', 'fecha', 'texto', 'link', 'replyTo', 'quoteTo', 'replies', 'retweets', 'likes', 'views']
COLS_RT = ['id_retweet', 'fecha_retweet', 'autor_original', 'nombre_autor', 'id_original', 'fecha_original', 'texto',
           'link_original', 'respuesta_a', 'cita_a', 'likes_original', 'respuestas_original', 'fecha_aproximada']
OFF = 3 * 3600  # hora de Argentina (UTC−3)
DIA, HORA = 86400, 3600
POR_ARCHIVO = 25000  # retweets por archivo de data/
PAUSA = 1.2
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


def log(*a):
    print(time.strftime('%Y-%m-%d %H:%M:%S'), *a, flush=True)

def iso(ts):
    return time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(ts))

def ts_de(fecha):
    import calendar
    return calendar.timegm(time.strptime(fecha[:19], '%Y-%m-%dT%H:%M:%S'))

def mk(ts):
    g = time.gmtime(ts - OFF)
    return g.tm_year * 12 + g.tm_mon - 1

def num(v):
    return int(v) if v not in ('', None) else None

def medianoche(ts):  # 00:00 de Argentina del día de ts
    return (ts - OFF) // DIA * DIA + OFF

def es_respuesta(reply_to):
    return any(h.strip() and h.strip().lower() != 'jmilei' for h in reply_to.split(','))

def fecha_larga(ts):
    g = time.gmtime(ts - OFF)
    return f'{g.tm_mday} de {MESES[g.tm_mon - 1]} de {g.tm_year}'

def miles(n):
    return f'{n:,}'.replace(',', '.')


# ---------- búsqueda ----------
def pedir(q, cursor=None):
    args = ['curl', '-s', '-m', '45', '-A', 'Mozilla/5.0', '-G', 'https://api.fxtwitter.com/2/search', '--data-urlencode', 'q=' + q]
    if cursor:
        args += ['--data-urlencode', 'cursor=' + cursor]
    for intento in range(6):
        out = subprocess.run(args, capture_output=True, text=True).stdout
        try:
            d = json.loads(out)
            if d.get('code') == 200:
                return d
        except ValueError:
            pass
        time.sleep(5 * (intento + 1))
    raise RuntimeError(f'FxTwitter no responde: {q}')

def buscar(q):
    res, vistos, cur = [], set(), None
    for _ in range(80):
        d = pedir(q, cur)
        time.sleep(PAUSA)
        nuevos = [x for x in d.get('results') or [] if x['id'] not in vistos]
        for x in nuevos:
            vistos.add(x['id']); res.append(x)
        nc = (d.get('cursor') or {}).get('bottom')
        if not nuevos or not nc or nc == cur:
            break
        cur = nc
    return res

def sn(x, k):
    v = x.get(k)
    return (v.get('screen_name') or '') if isinstance(v, dict) else ''

def texto_de(x):
    """Texto completo sin las menciones del principio cuando es una respuesta (como en el resto de los datos)."""
    txt = html.unescape(x.get('text') or '').strip()
    reply = []
    if x.get('replying_to'):
        lead = re.match(r'^(?:@\w+\s*)+', txt)
        reply = re.findall(r'@(\w+)', lead.group()) if lead else []
        if not reply and sn(x, 'replying_to'):
            reply = [sn(x, 'replying_to')]
        if lead and txt[lead.end():].strip():
            txt = txt[lead.end():].strip()
    return txt, reply

def fila_propia(x):
    txt, reply = texto_de(x)
    ts = int(x['created_timestamp'])
    return {'id': x['id'], 'fecha': iso(ts), 'texto': txt, 'link': f"https://x.com/JMilei/status/{x['id']}",
            'replyTo': ', '.join(reply), 'quoteTo': sn(x.get('quote') or {}, 'author'),
            'replies': x.get('replies', ''), 'retweets': x.get('reposts', x.get('retweets', '')),
            'likes': x.get('likes', ''), 'views': x.get('views') or ''}

def fila_retweet(x, ts_rt):
    txt, reply = texto_de(x)
    autor = x['author']['screen_name']
    ots = int(x['created_timestamp'])
    return {'id_retweet': '', 'fecha_retweet': iso(ts_rt), 'autor_original': autor, 'nombre_autor': x['author'].get('name') or '',
            'id_original': x['id'], 'fecha_original': iso(ots), 'texto': txt, 'link_original': f"https://x.com/{autor}/status/{x['id']}",
            'respuesta_a': sn(x, 'replying_to') or (reply[0] if reply else ''), 'cita_a': sn(x.get('quote') or {}, 'author'),
            'likes_original': x.get('likes', ''), 'respuestas_original': x.get('replies', ''), 'fecha_aproximada': 'si'}


# ---------- conjunto abierto de milei.nulo.lol ----------
NULO_CSV = 'https://milei.nulo.lol/api/datasets/retweets.csv'  # github.com/catdevnull/milei-twitter

def fila_nulo(r):
    """Fila del CSV de milei.nulo.lol (retweetAt, postedAt, posterId, posterHandle, postId, textPreview) → formato del CSV."""
    txt = (r['textPreview'] or '').strip()
    lead = re.match(r'^(?:@\w+\s+)+', txt)  # las respuestas traen las menciones al principio
    resp = ''
    if lead and txt[lead.end():].strip():
        resp = re.match(r'@(\w+)', txt).group(1)
        txt = txt[lead.end():].strip()
    autor = r['posterHandle'] or ''
    z = lambda f: f[:19] + '.000Z' if f else ''
    return {'id_retweet': '', 'fecha_retweet': z(r['retweetAt']), 'autor_original': autor, 'nombre_autor': '',
            'id_original': r['postId'], 'fecha_original': z(r['postedAt']), 'texto': txt,
            'link_original': f"https://x.com/{autor}/status/{r['postId']}", 'respuesta_a': resp, 'cita_a': '',
            'likes_original': '', 'respuestas_original': '', 'fecha_aproximada': ''}

def leer_nulo(ruta):
    return [r for r in csv.DictReader(open(ruta, encoding='utf-8'))
            if re.match(r'\d{4}-\d\d-\d\dT', r.get('retweetAt') or '') and (r.get('postId') or '').isdigit()]


# ---------- lectura y escritura ----------
def leer_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def escribir_csv(path, filas, cols):
    tmp = path + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(filas)
    os.replace(tmp, path)

def leer_index():
    s = open(os.path.join(RAIZ, 'index.html'), encoding='utf-8').read()
    m = re.search(r'(<script type="application/json" id="datos">)(.*?)(</script>)', s, re.S)
    return s, m, json.loads(m.group(2))

def git(*a, check=True):
    r = subprocess.run(['git', '-C', RAIZ, *a], capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f'git {" ".join(a)}: {r.stderr.strip() or r.stdout.strip()}')
    return r


def sumar_retweets_web(datos, nuevos_rt):
    """Agrega filas de retweets (formato del CSV) a data/retweets-AAAA-N.json y al manifiesto de datos['rt'].
    Con hora exacta pero sin ID del retweet, la fila lleva un 1 al final para que la página no muestre «≈»."""
    por_anio = {}
    for r in sorted(nuevos_rt, key=lambda r: r['fecha_retweet']):
        ts = ts_de(r['fecha_retweet'])
        por_anio.setdefault(time.gmtime(ts - OFF).tm_year, []).append(r)
    for y, grupo in sorted(por_anio.items()):
        while grupo:
            partes = [e for e in datos['rt'] if re.search(rf'retweets-{y}-(\d+)\.json$', e['f'])]
            ult = max(partes, key=lambda e: int(re.search(r'-(\d+)\.json$', e['f']).group(1))) if partes else None
            if ult and ult['n'] < POR_ARCHIVO:
                e = ult; d = json.load(open(os.path.join(RAIZ, e['f']), encoding='utf-8'))
            else:
                k = int(re.search(r'-(\d+)\.json$', ult['f']).group(1)) + 1 if ult else 1
                e = {'f': f'data/retweets-{y}-{k}.json', 'n': 0, 'mk0': 0, 'mk1': 0}; datos['rt'].append(e)
                d = {'a': [], 't': []}
            lugar, grupo = grupo[:POR_ARCHIVO - e['n']], grupo[POR_ARCHIVO - e['n']:]
            autores = {a[0]: i for i, a in enumerate(d['a'])}
            for r in lugar:
                if r['autor_original'] not in autores:
                    autores[r['autor_original']] = len(d['a']); d['a'].append([r['autor_original'], r['nombre_autor']])
                fila = [r['id_retweet'], ts_de(r['fecha_retweet']), autores[r['autor_original']], r['id_original'],
                        ts_de(r['fecha_original']) if r['fecha_original'] else None, r['texto'], r['respuesta_a'], r['cita_a'],
                        num(r['likes_original']), num(r['respuestas_original']), tramos(r['texto'])]
                if not r['id_retweet'] and not r['fecha_aproximada']:
                    fila.append(1)
                d['t'].append(fila)
            d['t'].sort(key=lambda r: r[1])
            with open(os.path.join(RAIZ, e['f']), 'w', encoding='utf-8') as f:
                f.write(json.dumps(d, ensure_ascii=False, separators=(',', ':')))
            e.update(n=len(d['t']), mk0=mk(d['t'][0][1]), mk1=mk(d['t'][-1][1]))


def precisar_retweets(datos, filas_rt, exactos):
    """Pone la hora exacta (exactos: {id_original: fecha ISO}) a los retweets que la tenían estimada, en el CSV y en la web."""
    n = 0
    for r in filas_rt:
        if r['fecha_aproximada'] and not r['id_retweet'] and r['id_original'] in exactos:
            r['fecha_retweet'] = exactos[r['id_original']]; r['fecha_aproximada'] = ''; n += 1
    if not n:
        return 0
    for e in datos['rt']:
        ruta = os.path.join(RAIZ, e['f']); d = json.load(open(ruta, encoding='utf-8')); tocado = False
        for fila in d['t']:
            if not fila[0] and len(fila) < 12 and fila[3] in exactos:
                fila[1] = ts_de(exactos[fila[3]]); fila.append(1); tocado = True
        if tocado:
            d['t'].sort(key=lambda f: f[1])
            with open(ruta, 'w', encoding='utf-8') as f:
                f.write(json.dumps(d, ensure_ascii=False, separators=(',', ':')))
            e.update(n=len(d['t']), mk0=mk(d['t'][0][1]), mk1=mk(d['t'][-1][1]))
    return n


def escribir_index_y_readme(s, m, datos, ahora):
    """Guarda los datos en index.html y actualiza las fechas y cifras de la página y del README."""
    hoy = fecha_larga(ahora)
    s = s[:m.start(2)] + json.dumps(datos, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + s[m.end(2):]
    s = re.sub(r'Datos actualizados al [^<]*?\.(?=</p>)', f'Datos actualizados al {hoy}.', s)
    s = re.sub(r'(entre el 1 de octubre de 2015 y el )\d+ de \w+ de \d{4}', rf'\g<1>{hoy}', s)
    open(os.path.join(RAIZ, 'index.html'), 'w', encoding='utf-8').write(s)
    n_tw = sum(1 for r in datos['t'] if not es_respuesta(r[3]))
    n_rt = sum(e['n'] for e in datos['rt'])
    rd = os.path.join(RAIZ, 'README.md'); t = open(rd, encoding='utf-8').read()
    g = time.gmtime(ahora - OFF)
    t = re.sub(r'entre octubre de 2015 y \w+ de \d{4}', f'entre octubre de 2015 y {MESES[g.tm_mon - 1]} de {g.tm_year}', t)
    t = re.sub(r'- [\d.]+ tweets y [\d.]+ respuestas', f'- {miles(n_tw)} tweets y {miles(len(datos["t"]) - n_tw)} respuestas', t)
    t = re.sub(r'- [\d.]+ retweets', f'- {miles(n_rt)} retweets', t)
    open(rd, 'w', encoding='utf-8').write(t)
    log(f'escrito: {len(datos["t"])} tweets y respuestas, {n_rt} retweets en la web')


def main(probar, publicar):
    # que la Mac no se duerma mientras corre (la tarea diaria lo lanza sin caffeinate)
    subprocess.Popen(['/usr/bin/caffeinate', '-i', '-w', str(os.getpid())])
    lock = open(os.path.join(RAIZ, '.git', 'actualizar.lock'), 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log('ya hay otra actualización corriendo'); return
    if publicar and not probar:
        r = git('pull', '--ff-only', '-q', check=False)
        if r.returncode:
            log('aviso: no se pudo traer lo último de GitHub:', r.stderr.strip())

    s, m, datos = leer_index()
    ahora = int(time.time())
    ult_propio = max(r[1] for r in datos['t'])
    ult_rt = 0
    for e in datos['rt']:
        d = json.load(open(os.path.join(RAIZ, e['f']), encoding='utf-8'))
        if d['t']:
            ult_rt = max(ult_rt, max(r[1] for r in d['t']))
    ini_propio = medianoche(ult_propio) - 3 * DIA
    ini_rt = ult_rt // HORA * HORA - DIA
    if ahora - ini_rt > 8 * DIA:
        log(f'aviso: el último retweet cargado es del {iso(ult_rt)[:10]}; X solo deja buscar la última semana, '
            'así que puede quedar un hueco de retweets')
        ini_rt = max(ini_rt, (ahora - 9 * DIA) // HORA * HORA)
    log(f'tweets y respuestas desde {iso(ini_propio)[:16]} | retweets desde {iso(ini_rt)[:16]} (UTC)')

    # tweets y respuestas, día por día
    propios = {}
    for a in range(ini_propio, ahora, DIA):
        res = buscar(f'from:JMilei since_time:{a} until_time:{a + DIA}')
        for x in res:
            if sn(x, 'author').lower() == 'jmilei' and not x.get('reposted_by'):
                propios[x['id']] = fila_propia(x)
    # retweets, hora por hora (la búsqueda filtra por la hora del retweet)
    rts = {}
    for a in range(ini_rt, ahora, HORA):
        b = min(a + HORA, ahora)
        for x in buscar(f'from:JMilei include:nativeretweets filter:nativeretweets since_time:{a} until_time:{b}'):
            if sn(x, 'reposted_by').lower() != 'jmilei' or x['id'] in rts:
                continue
            lo = max(a, int(x['created_timestamp']))
            rts[x['id']] = fila_retweet(x, (lo + max(lo, b)) // 2)  # mitad de la hora en que lo retuiteó
    log(f'búsqueda: {len(propios)} tweets y respuestas, {len(rts)} retweets')

    # ---- CSV ----
    viejos = {r['id']: r for r in leer_csv(CSV_TW) + leer_csv(CSV_RESP)}
    nuevos_p = [i for i in propios if i not in viejos]
    viejos.update(propios)  # la búsqueda tiene prioridad: texto completo y métricas al día
    todos = sorted(viejos.values(), key=lambda r: r['fecha'], reverse=True)
    filas_rt = leer_csv(CSV_RT)
    desde = iso(ini_rt - 3 * DIA)
    ya = {r['id_original'] for r in filas_rt if r['fecha_retweet'] >= desde}
    nuevos_rt = [r for i, r in rts.items() if i not in ya]
    # los lunes, además, lo que registró milei.nulo.lol en los últimos 10 días (hora exacta)
    exactos_nulo = {}
    if time.gmtime(ahora - OFF).tm_wday == 0:
        tmp = os.path.join(RAIZ, '.git', 'nulo_retweets.csv')
        r = subprocess.run(['curl', '-s', '-m', '600', '-A', 'Mozilla/5.0', '-o', tmp, '-w', '%{http_code}', NULO_CSV],
                           capture_output=True, text=True)
        if r.stdout == '200':
            todos_ids = {f['id_original'] for f in filas_rt} | {f['id_original'] for f in nuevos_rt}
            desde_n = iso(ahora - 10 * DIA)
            extra = []
            for f in map(fila_nulo, leer_nulo(tmp)):
                if f['fecha_retweet'] >= desde_n and f['id_original'] not in todos_ids:
                    todos_ids.add(f['id_original']); extra.append(f)
            nuevos_rt += extra
            exactos_nulo = {f['id_original']: f['fecha_retweet'] for f in map(fila_nulo, leer_nulo(tmp))}
            log(f'milei.nulo.lol: {len(extra)} retweets que la búsqueda no trajo')
        else:
            log(f'aviso: no se pudo bajar el CSV de milei.nulo.lol (HTTP {r.stdout})')
    log(f'nuevos: {len(nuevos_p)} tweets y respuestas, {len(nuevos_rt)} retweets')
    if probar:
        for i in nuevos_p[:10]:
            print('  ', propios[i]['fecha'][:16], propios[i]['texto'][:100].replace('\n', ' '))
        return
    escribir_csv(CSV_TW, [r for r in todos if not es_respuesta(r['replyTo'])], COLS)
    escribir_csv(CSV_RESP, [r for r in todos if es_respuesta(r['replyTo'])], COLS)
    filas_rt = sorted(filas_rt + nuevos_rt, key=lambda r: r['fecha_retweet'], reverse=True)
    escribir_csv(CSV_RT, filas_rt, COLS_RT)

    # ---- web: tweets y respuestas (dentro de index.html) ----
    pos = {r[0]: i for i, r in enumerate(datos['t'])}
    for i, r in propios.items():
        fila = [r['id'], ts_de(r['fecha']), r['texto'], r['replyTo'], r['quoteTo'], num(r['replies']),
                num(r['retweets']), num(r['likes']), num(r['views'])]
        if i in pos:
            vieja = datos['t'][pos[i]]
            sp = vieja[9] if vieja[2] == r['texto'] else tramos(r['texto'])
            datos['t'][pos[i]] = fila + [sp]
        else:
            datos['t'].append(fila + [tramos(r['texto'])])
    datos['t'].sort(key=lambda r: r[1])
    datos['own'] = [{'n': len(datos['t']), 'mk0': mk(datos['t'][0][1]), 'mk1': mk(datos['t'][-1][1])}]

    sumar_retweets_web(datos, nuevos_rt)
    if exactos_nulo:
        filas_rt = leer_csv(CSV_RT)
        n_prec = precisar_retweets(datos, filas_rt, exactos_nulo)
        if n_prec:
            escribir_csv(CSV_RT, sorted(filas_rt, key=lambda r: r['fecha_retweet'], reverse=True), COLS_RT)
            log(f'milei.nulo.lol: {n_prec} retweets pasan a tener hora exacta')

    escribir_index_y_readme(s, m, datos, ahora)
    g = time.gmtime(ahora - OFF)

    if not publicar:
        return
    git('add', 'index.html', 'data', 'README.md')
    if git('diff', '--cached', '--quiet', check=False).returncode == 0:
        log('sin cambios para publicar'); return
    git('commit', '-q', '-m', f'Actualizar datos al {time.strftime("%d/%m/%Y", g)} '
        f'(+{len(nuevos_p)} tweets y respuestas, +{len(nuevos_rt)} retweets)')
    git('push', '-q', 'origin', 'HEAD')
    log('publicado en GitHub Pages')


if __name__ == '__main__':
    try:
        main('--probar' in sys.argv, '--sin-push' not in sys.argv)
    except Exception as e:
        log('ERROR:', e)
        sys.exit(1)
