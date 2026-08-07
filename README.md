# SanteBio - Cápsulas de Nopal

Proyecto de rediseño para el sitio de cápsulas de nopal SanteBio (cliente Tyakxa).

## Contenido

- `clone/` — Réplica exacta del sitio en vivo (capsulasdenopal.com) tal como estaba, usada como punto de partida. Incluye HTML, CSS, JS e imágenes descargadas del sitio real.
- `site/` — Rediseño nuevo (React + Vite), con el mismo patrón de video de fondo usado en los proyectos `infinity` y `lacampinafrancesa`. Ver `site/README.md` para cómo agregar los video clips.
- `Dockerfile` / `docker-compose.yml` — Sirve el contenido de `clone/` con nginx dentro de un contenedor Docker.

## Uso local sin Docker

```
node clone/server.js
```

Abre `http://localhost:4930`.

## Uso con Docker

```
docker compose up --build
```

Abre `http://localhost:8080`.
