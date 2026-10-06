"""Clasifica textos en convencional / confrontativo / procaz con listas de términos.

Son las listas del armado original (30/09/2026), recuperadas de la sesión en que se
escribieron, más las reglas que se sumaron después en marcar.py. tramos(texto)
devuelve los tramos marcados como lista plana [inicio, fin, nivel, ...] en
caracteres (code points), con nivel 0 lema, 1 confrontativo y 2 procaz: el mismo
formato que guardan index.html y data/*.json.
"""
import re, unicodedata

from marcar import REGLAS, marcar


def norm_char(ch):
    lo = ch.lower()
    if len(lo) != 1: return ch
    if lo == 'ñ': return lo
    d = ''.join(c for c in unicodedata.normalize('NFD', lo) if unicodedata.category(c) != 'Mn')
    return d if len(d) == 1 else lo

def norm(s):  # misma longitud que el original, para mapear posiciones
    return ''.join(norm_char(c) for c in s)

PROCAZ = [
    r'\w*mierd\w*', r'\bcaraj+o+\b', r'\w*pelotud\w*', r'\w*bolu(?:d\w*|progre\w*)',
    r'\bforr(?:o|a|os|as|ito|itos)\b', r'\bcul(?:o|os|ito|iado|iados|iada)\b', r'\bort(?:o|ito)\b',
    r'\bojete\w*', r'\bsoret\w*', r'\bbost(?:a|as|ita)\b',
    r'\bcag(?:ar|o|a|as|an|ue|ada|adas|ado|ados|on|ona|ones|onazo|ando|aron|aran|arse|arle|arles|arnos|arte|arlo|arla|alos|adon|azo|andolo|andote|atintas)\b',
    r'\b(?:re)?put(?:a|as|o|os|ita|itas|isima|isimas|isimo|isimos|ear|eada|eadas|eando)\b',
    r'\bhdp\w*', r'\b(?:re)?conch(?:a|udo|uda|udos|udas)\b',
    r'\bpij(?:a|as|udo|otero)\b', r'\bverga\w*', r'\bgarch\w*', r'\bchot(?:o|a|os|as)\b', r'\bgarcas?\b',
    r'\bchupal(?:a|o)\b', r'\bchupa(?:n|r)?\s+(?:un|los)\s+huevos?\b', r'\bhuevos\b',
    r'\bcornud\w*', r'\bmal\s?parid\w*', r'\bremil\b', r'\blrpm\w*', r'\blcdt\w*', r'\bptm\b',
    r'\btrol(?:o|a|os|as)\b', r'\bmogolic\w*', r'\bpajer\w*', r'\bchupapija\w*', r'\bchupaculo\w*',
    r'\bfuck\w*', r'\bshit\w*', r'\bbitch\w*', r'(?<!alcanza )\bpelotas\b', r'\beyacul\w*', r'\bmasturb\w*', r'\borgasm\w*', r'\bbostaman\w*', r'\bcag(?:andose|adores?)\b', r'\bpute(?:o|os)\b',
]
CONFRONT = [
    r'\bcastas?\b', r'\bchorr(?:o|a|os|as|ean|ear|eo|ito|itos)\b', r'\bkukachorr\w*',
    r'\bladr(?:on|ona|ones|onas|onazo|eta|etas|i)\b', r'\bdelincuen(?:te|tes|cial|ciales)\b', r'\bcorrupt(?:o|a|os|as)\b',
    r'\bzurd(?:o|a|os|as|ito|itos|ita|itas|aje|erio|es|ada|olandia|oprogre\w*|ucho\w*)\b', r'\bprogrezurd\w*',
    r'\bkuk(?:a|as|aracho|arachos|aracha|arachas|arda|arakia|ita|itas|ismo|ada)\b',
    r'\bbasur(?:a|as|ita)\b', r'\binmund(?:o|a|os|as|icia)\b', r'\basquer\w*', r'\brepugn\w*', r'\bnefast\w*',
    r'\bsiniestr(?:o|a|os|as)\b', r'\bmiserables?\b', r'\blacras?\b', r'\bescoria\w*', r'\bratas?\b', r'\bcucarach\w*',
    r'\bgusan(?:o|os)\b', r'\bparasit\w*', r'\bchupasangres?\b', r'\bchupamedias\b', r'\bchupapauta\w*',
    r'\bidiot\w*', r'\bimbecil\w*', r'\bestupid\w*', r'\bburr(?:o|a|os|as|ada)\b', r'\bbestias?\b',
    r'\bignorant\w*', r'\bignorancia\b', r'\banalfabet\w*', r'\bmediocr\w*', r'\bfracasad\w*', r'\binutil(?:es)?\b',
    r'\bcobard\w*', r'\btraidor\w*', r'\bgolpist\w*', r'\basesin(?:o|a|os|as)\b', r'\bmentir(?:oso|osa|osos|osas)\b',
    r'\bmentiras?\b', r'\bchant(?:a|as|ada|adas|apufi|apuferio|alan)\b', r'\beconochant\w*', r'\bensobrad\w*',
    r'\bmandril\w*', r'\bpayas(?:o|os|a|as|ada|adas)\b', r'\bresentid\w*', r'\benvidios\w*', r'\bhipocrit\w*',
    r'\bpsicopat\w*', r'\bdegenerad\w*', r'\bsinverg\w*', r'\bcretin\w*', r'\btarad(?:o|a|os|as)\b', r'\bmarmotas?\b',
    r'\bbastard\w*', r'\bcanall\w*', r'\bplaner(?:o|a|os|as)\b', r'\bchoriplaner\w*', r'\bpatetic\w*',
    r'\bridicul(?:o|a|os|as)\b', r'\bpodrid(?:o|a|os|as)\b', r'\bmugr(?:e|oso|osa|osos|osas)\b', r'\bcloac\w*',
    r'\bdelirant\w*', r'\bgenocid(?:a|as)\b', r'\bfascistas?\b', r'\bfachos?\b', r'\bsubnormal\w*', r'\bcavernicol\w*',
    r'\btroglodit\w*', r'\bgil(?:es)?\b', r'\bsalames?\b', r'\botari(?:o|a|os|as)\b', r'\bñoquis?\b', r'\bvendepatri\w*',
    r'\bcipay\w*', r'\blacay\w*', r'\bexcrement\w*', r'\bvomitiv\w*', r'\basnos?\b', r'\bprostitut\w*',
    r'\bcharlatan\w*', r'\bestafador\w*', r'\bmafios(?:o|a|os|as)\b', r'\bnecios?\b', r'\bbob(?:o|a|os|as|ito|itos|in)\b',
    r'\btont(?:o|a|os|as)\b', r'\bperonch\w*', r'\baberraci\w*', r'\brastrer\w*', r'\binfames?\b', r'\bdescerebrad\w*',
    r'\bpedofil\w*', r'\bllor(?:an|en|ando|ones|on|ona|onas|iqueo)\b', r'\ba llorar\b', r'\btiembl(?:a|an|en)\b',
    r'\bcurr(?:o|os|ero|eros)\b', r'\bbrut(?:o|a|os|as)\b', r'\bstupid\w*', r'\bmorons?\b', r'\bliars?\b', r'\bchore(?:o|os|ar|an|aron)\b', r'\bburradas\b',
    r'\besclav(?:o|a|os|as)\s+mental\w*', r'\bproblemas mentales\b', r'\bdelirio\w*', r'\bporota\b', r'\bsodomit\w*',
    r'\btonteria\w*', r'\bun pomo\b', r'\bkorrupt\w*', r'\bmient(?:e|en|es)\b', r'\bmalintencionad\w*', r'\baberrant\w*', r'\bchupamedia\b',
    r'\bgilada\b', r'\bladret\w*', r'\bzurdes?\b', r'\bcurritos?\b', r'\bchanteri\w*', r'\bbob(?:ada|adas|eta)\b',
]
RP = re.compile('|'.join(f'(?:{p})' for p in PROCAZ))
RC = re.compile('|'.join(f'(?:{p})' for p in CONFRONT))
LEMA = re.compile(r'libertad[\s,.!¡…"\'”]*$')
NO_BRUTO = re.compile(r'(producto|ingresos?|margen|valor|interno|pbi|pib|peso|sueldos?|salarios?|montos?|importe|brutal)\s*$')
URL = re.compile(r'https?://\S+|\b(?:x|twitter|youtu)\.\w+/\S*|\b\w+\.(?:com|ar|org|net)/\S*')

def spans(texto):
    t = norm(texto)
    urls = [(m.start(), m.end()) for m in URL.finditer(t)]
    en_url = lambda a: any(s <= a < e for s, e in urls)
    out = []
    for m in RP.finditer(t):
        if en_url(m.start()) or t[max(0, m.start()-1):m.start()] == '@': continue
        tipo = 'p'
        if re.match(r'caraj', m.group()) and LEMA.search(t[max(0, m.start()-30):m.start()]):
            tipo = 'l'
        out.append([m.start(), m.end(), tipo])
    for m in RC.finditer(t):
        if en_url(m.start()) or t[max(0, m.start()-1):m.start()] == '@': continue
        if any(s < m.end() and m.start() < e for s, e, _ in out): continue
        if m.group().startswith('brut') and NO_BRUTO.search(t[max(0, m.start()-12):m.start()]): continue
        out.append([m.start(), m.end(), 'c'])
    return sorted(out)

K = {'l': 0, 'c': 1, 'p': 2}

def tramos(texto):
    """Tramos de las listas + los de las reglas de marcar.py, en el formato de la web."""
    sp = [x for a, b, k in spans(texto) for x in (a, b, K[k])]
    sp, _ = marcar(texto, sp, {r[0]: 0 for r in REGLAS})
    return sp
