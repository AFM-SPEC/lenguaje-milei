# El lenguaje de Milei

Explorador de los tweets, respuestas y retweets de Javier Milei (@JMilei) entre octubre de 2015 y octubre de 2026, clasificados en tres niveles de lenguaje: convencional, confrontativo y procaz.

- 23.098 tweets y 16.532 respuestas, incluidos en `index.html`.
- 229.368 retweets en `data/`, un archivo por año (o parte de año), que la página carga al abrirse.

Se actualiza todos los días con lo nuevo. Página: https://afm-spec.github.io/lenguaje-milei/

## Qué permite

- Combinar los tipos (tweets, respuestas, retweets) y los niveles de lenguaje como filtros cruzados, en cualquier combinación.
- Contar el lema «Viva la libertad, carajo» (o «VLLC») como procaz, como confrontativo o no contarlo.
- Ver el impacto de la selección: visualizaciones, me gusta, retweets y respuestas recibidas, en total, en promedio y por nivel. Me gusta, retweets y respuestas existen desde 2015; las visualizaciones, desde el 15 de diciembre de 2022, cuando X empezó a contarlas.
- Graficar por mes la cantidad de publicaciones o cualquiera de esas cifras, buscar palabras y elegir un período.

La clasificación es automática, con listas de palabras armadas a partir del vocabulario de los tweets. La sección «Cómo se clasificó» de la página explica el método, sus límites, las fuentes y la cobertura.

## Fuentes y cobertura

- Tweets y respuestas: búsqueda día por día a través de FxTwitter, archivopolitico.com y capturas del Wayback Machine. Están completos.
- Retweets: capturas del Wayback Machine (de cada retweet y del perfil), resueltas con el servicio público de tweets incrustados de X, el conjunto abierto de [milei.nulo.lol](https://milei.nulo.lol) (retweets con hora exacta desde febrero de 2024) y, desde octubre de 2026, la búsqueda de X, que encuentra los de la última semana.
- El perfil informaba 397.981 publicaciones el 6 de octubre de 2026. Los tweets y respuestas están completos; faltan retweets, casi todos los de 2015 a 2019 y los de julio de 2022 a enero de 2024. Se buscaron en todas las fuentes gratuitas conocidas (Wayback Machine, archive.today, Common Crawl, conjuntos de datos públicos, el servicio de tweets incrustados de X); X no deja buscar retweets de más de una semana, así que esos huecos no se pueden completar gratis.

## Herramientas

- `herramientas/actualizar.py`: suma los tweets, respuestas y retweets nuevos, los clasifica, actualiza los CSV, `index.html` y `data/`, y publica (commit + push). `--sin-push` para no publicar, `--probar` para solo ver qué encontraría.
- `herramientas/importar_retweets.py`: suma retweets de un conjunto externo (el CSV de milei.nulo.lol) sin duplicar.
- `herramientas/clasificar.py`: las listas de palabras y la función que marca cada texto.
- `herramientas/marcar.py`: reglas agregadas después (NOLSALP, «domar», VLLC…); aplica las reglas nuevas a todo lo publicado sin rehacer la clasificación.

## Ver en local

```
python3 -m http.server
```

y abrir http://localhost:8000.
