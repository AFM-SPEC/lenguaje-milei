"""Baja el perfil público de las cuentas con las que interactúa Milei, para las señales de automatización.

Cuentas: autores de lo que retuiteó y cuentas a las que respondió, citó o mencionó en sus tweets y
respuestas (las mismas que cuenta la sección «Con quién interactúa»). Fuente: FxTwitter (gratis, sin
clave). Guarda data/cuentas.json: {cuenta en minúsculas: fila}, con fila =
[nombre de usuario, alta (unix), seguidores, seguidos, publicaciones, me gusta, foto por defecto (0/1),
largo de la descripción, portada (0/1), tipo de verificación, fecha del chequeo (unix), estado]
con estado '' si existe, 'suspendida' (X lo informa así), 'sin dato' (FxTwitter respondió «no encontrada»,
cosa que también hace cuando X lo frena: se vuelve a consultar otro día) o 'no encontrada' (dos días
distintos sin encontrarla: borrada o con otro nombre).
Reanudable: solo consulta las que faltan, empezando por las que tienen más interacciones.

Uso: python3 herramientas/cuentas.py [--max N]
"""
import calendar, csv, json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_CSV = os.path.dirname(RAIZ)
SALIDA = os.path.join(RAIZ, 'data', 'cuentas.json')
MENC = re.compile(r'(?:^|[^\w@/])@(\w{1,15})')


def cuentas_que_interactuan():
    """{cuenta en minúsculas: nombre de usuario}, con la misma regla que la página, de más a menos interacciones."""
    out, n = {}, {}
    def add(h):
        h = (h or '').strip()
        if h and h.lower() != 'jmilei':
            out.setdefault(h.lower(), h); n[h.lower()] = n.get(h.lower(), 0) + 1
    for f in ('milei_tweets.csv', 'milei_respuestas.csv'):
        for r in csv.DictReader(open(os.path.join(DIR_CSV, f), encoding='utf-8-sig')):
            for h in r['replyTo'].split(', '): add(h)
            for h in r['quoteTo'].split(', '): add(h)
            for h in MENC.findall(r['texto']): add(h)
    for r in csv.DictReader(open(os.path.join(DIR_CSV, 'milei_retweets.csv'), encoding='utf-8-sig')):
        add(r['autor_original'])
    return dict(sorted(out.items(), key=lambda kv: -n[kv[0]]))


def perfil(h):
    no_encontrada = 0
    for intento in range(6):
        out = subprocess.run(['curl', '-s', '-m', '25', '-A', 'Mozilla/5.0', f'https://api.fxtwitter.com/{h}'],
                             capture_output=True, text=True).stdout
        try:
            j = json.loads(out)
        except ValueError:
            time.sleep(5 * (intento + 1)); continue
        ahora = int(time.time())
        if j.get('code') == 200 and j.get('user'):
            u = j['user']
            try:
                alta = calendar.timegm(time.strptime(u.get('joined', ''), '%a %b %d %H:%M:%S +0000 %Y'))
            except ValueError:
                alta = None
            return [u.get('screen_name') or h, alta, u.get('followers'), u.get('following'), u.get('tweets'), u.get('likes'),
                    1 if 'default_profile' in (u.get('avatar_url') or '') else 0, len(u.get('description') or ''),
                    1 if u.get('banner_url') else 0, (u.get('verification') or {}).get('type') or '', ahora, '']
        if j.get('code') == 404 and j.get('reason') == 'suspended':
            return [h, None, None, None, None, None, None, None, None, '', ahora, 'suspendida']
        if j.get('code') == 404:
            no_encontrada += 1
            if no_encontrada >= 2:
                return [h, None, None, None, None, None, None, None, None, '', ahora, 'sin dato']
            time.sleep(20); continue
        time.sleep(5 * (intento + 1))
    return None  # sin respuesta: se reintenta en la próxima corrida


def guardar(datos):
    tmp = SALIDA + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(json.dumps(datos, ensure_ascii=False, separators=(',', ':')))
    os.replace(tmp, SALIDA)


def actualizar(maximo=None, hilos=2, log=print):
    datos = json.load(open(SALIDA, encoding='utf-8')) if os.path.exists(SALIDA) else {}
    todas = cuentas_que_interactuan()
    ayer = time.time() - 20 * 3600
    pend = [h for k, h in todas.items() if k not in datos or (datos[k][11] == 'sin dato' and datos[k][10] < ayer)][:maximo]
    log(f'cuentas: {len(todas)} | con perfil: {len(datos)} | a consultar: {len(pend)}')
    hechas = 0
    with ThreadPoolExecutor(hilos) as ex:
        for h, fila in zip(pend, ex.map(lambda h: (time.sleep(0.4), perfil(h))[1], pend)):
            if fila:
                previa = datos.get(h.lower())
                if fila[11] == 'sin dato' and previa and previa[11] == 'sin dato':
                    fila[11] = 'no encontrada'  # segundo día distinto sin encontrarla
                datos[h.lower()] = fila
            hechas += 1
            if hechas % 500 == 0:
                guardar(datos); log(f'  {hechas} de {len(pend)}')
    guardar(datos)
    return datos


if __name__ == '__main__':
    mx = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else None
    d = actualizar(mx)
    from collections import Counter
    print('estados:', dict(Counter(f[11] or 'existe' for f in d.values())))
