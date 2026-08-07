# SanteBio — sitio rediseñado (React + Vite)

Scaffold nuevo para el rediseño de SanteBio, siguiendo el mismo patrón de video usado en `infinity` y `lacampinafrancesa`.

## Uso

```
npm install
npm run dev
```

## Cómo agregar los video clips

Cuando descargues los clips del cliente, colócalos en `public/videos/` con este nombre (mismo patrón que `infinity/paso5_video_prompts.json`):

```
public/videos/escena1_nopal_16x9.mp4   (horizontal, escritorio)
public/videos/escena1_nopal_9x16.mp4   (vertical, celular — opcional)
```

El componente `VideoBackground` (`src/components/VideoBackground.jsx`) ya está conectado a esas rutas desde `Hero.jsx`. Si el archivo `_9x16` todavía no existe, el video de escritorio se usa como respaldo automático en móvil — no rompe nada mientras subes los clips.

Para agregar más escenas (ej. una sección de "cómo se usa" o beneficios con video), usa `SplitVideoSection.jsx` con nuevos archivos `escena2_..._16x9.mp4`, etc.

## Estructura

- `src/components/VideoBackground.jsx` — el `<video>` de fondo con fallback móvil
- `src/components/SplitVideoSection.jsx` — sección con video + texto a un lado
- `src/components/Reveal.jsx` — animación al hacer scroll
- `src/hooks/useIsMobile.js` — detecta breakpoint móvil (760px)
