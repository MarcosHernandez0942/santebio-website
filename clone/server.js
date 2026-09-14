const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = __dirname;
const PORT = 4930;

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.webp': 'image/webp',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.gif': 'image/gif',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
  '.otf': 'font/otf',
  // Sin estas, un <video>/<img> se sirve como application/octet-stream
  // y algunos navegadores se niegan a reproducirlo/decodificarlo --
  // eso es justo lo que se veia como videos/imagenes rotas de forma
  // intermitente (ver bitacora del 14 de septiembre).
  '.mp4': 'video/mp4',
  '.webm': 'video/webm',
  '.mov': 'video/quicktime',
  '.mp3': 'audio/mpeg',
};

http.createServer((req, res) => {
  let urlPath = decodeURIComponent(req.url.split('?')[0]);
  if (urlPath === '/') urlPath = '/index.html';
  const filePath = path.join(ROOT, urlPath);
  if (!filePath.startsWith(ROOT)) { res.writeHead(403); res.end(); return; }

  fs.stat(filePath, (statErr, stat) => {
    if (statErr || !stat.isFile()) { res.writeHead(404); res.end('Not found: ' + urlPath); return; }

    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME[ext] || 'application/octet-stream';
    const range = req.headers.range;

    // Los navegadores piden video (y a veces imagenes grandes) con
    // encabezado "Range" para poder adelantar/atrasar sin descargar
    // el archivo completo -- la version anterior de este servidor
    // ignoraba ese encabezado por completo y siempre mandaba el
    // archivo entero con 200, lo que confundia a algunos navegadores
    // (esperaban 206 Partial Content) y se veia como que el video o
    // la imagen "a veces sí, a veces no" cargaban bien.
    if (range) {
      const match = /bytes=(\d*)-(\d*)/.exec(range);
      const start = match && match[1] ? parseInt(match[1], 10) : 0;
      const end = match && match[2] ? parseInt(match[2], 10) : stat.size - 1;
      if (Number.isNaN(start) || Number.isNaN(end) || start > end || end >= stat.size) {
        res.writeHead(416, { 'Content-Range': `bytes */${stat.size}` });
        res.end();
        return;
      }
      res.writeHead(206, {
        'Content-Type': contentType,
        'Content-Length': end - start + 1,
        'Content-Range': `bytes ${start}-${end}/${stat.size}`,
        'Accept-Ranges': 'bytes',
      });
      fs.createReadStream(filePath, { start, end }).pipe(res);
      return;
    }

    res.writeHead(200, {
      'Content-Type': contentType,
      'Content-Length': stat.size,
      'Accept-Ranges': 'bytes',
    });
    fs.createReadStream(filePath).pipe(res);
  });
}).listen(PORT, () => console.log('Serving', ROOT, 'on port', PORT));
