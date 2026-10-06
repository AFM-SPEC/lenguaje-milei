# El lenguaje de Milei

Explorador de los tweets, respuestas y retweets de Javier Milei (@JMilei) entre octubre de 2015 y octubre de 2026, clasificados en tres niveles de lenguaje: convencional, confrontativo y procaz.

- 23.098 tweets y 16.532 respuestas, incluidos en `index.html`.
- 200.097 retweets en `data/`, un archivo por año (o parte de año), que la página carga al abrirse.

La clasificación es automática, con listas de palabras armadas a partir del vocabulario de los tweets. La sección «Cómo se clasificó» de la página explica el método, sus límites y las fuentes.

## Fuentes

- Tweets y respuestas: búsqueda día por día a través de FxTwitter, archivopolitico.com y capturas del Wayback Machine.
- Retweets: capturas del Wayback Machine (de cada retweet y del perfil), resueltas con el servicio público de tweets incrustados de X. La cobertura es despareja: hay pocos antes de 2020 y en 2023.

## Ver en local

```
python3 -m http.server
```

y abrir http://localhost:8000.
