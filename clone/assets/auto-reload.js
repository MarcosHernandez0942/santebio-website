/* Auto-recarga la pagina cuando detecta un cambio (ej. el desarrollador
   edito el sitio) o cuando la sesion vencio y assets/auth.js ya la
   limpio. Como clone/server.js es un servidor estatico plano sin
   ETag/Last-Modified, se compara el contenido crudo de la pagina
   *y de todos sus .css/.js cargados* contra si mismos cada cierto
   tiempo -- no solo el HTML, porque la mayoria de los cambios reales
   pasan en archivos compartidos (shop.css, auth.js, etc.), no en el
   propio HTML de cada pagina. */
(function () {
  var snapshot = null;
  var urls = null;

  function elementoEditandoTexto() {
    var el = document.activeElement;
    if (!el) return false;
    var tag = el.tagName;
    return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
  }

  function esMismoOrigen(url) {
    try {
      return new URL(url, location.href).origin === location.origin;
    } catch (e) {
      return false;
    }
  }

  function urlsARevisar() {
    var lista = [location.pathname + location.search];
    document.querySelectorAll('link[rel="stylesheet"][href]').forEach(function (el) {
      var href = el.getAttribute('href');
      if (esMismoOrigen(href)) lista.push(new URL(href, location.href).pathname);
    });
    document.querySelectorAll('script[src]').forEach(function (el) {
      var src = el.getAttribute('src');
      if (esMismoOrigen(src)) lista.push(new URL(src, location.href).pathname);
    });
    return lista;
  }

  function obtenerFirma() {
    // "cache: no-store" solo le dice al NAVEGADOR que no use su propio
    // cache -- no le dice nada a un proxy/CDN que pudiera estar
    // enfrente del sitio en un despliegue real (VPS con Nginx,
    // Cloudflare, etc.), que puede seguir devolviendo una copia vieja
    // sin enterarse. Por eso se agrega ademas un parametro distinto en
    // cada revision (timestamp): la URL completa nunca se repite, asi
    // que ningun cache -- del navegador, de un proxy o de un CDN --
    // tiene una copia guardada para esa URL exacta y esta obligado a
    // pedirla de nuevo al servidor de origen.
    var sello = Date.now();
    return Promise.all(urls.map(function (url) {
      var urlSinCache = url + (url.indexOf('?') === -1 ? '?' : '&') + '_sb=' + sello;
      return fetch(urlSinCache, { cache: 'no-store' })
        .then(function (r) { return r.text(); })
        .catch(function () { return null; });
    })).then(function (textos) { return textos.join(' '); });
  }

  function revisarCambios() {
    if (document.hidden || elementoEditandoTexto()) return;
    obtenerFirma().then(function (firma) {
      if (snapshot === null) { snapshot = firma; return; }
      if (firma !== snapshot) window.location.reload();
    });
  }

  /* La lista de archivos a vigilar se arma hasta que la pagina termino
     de cargar por completo (evento "load"), no al momento en que este
     script se ejecuta -- si se hiciera antes, como los <script> se
     ejecutan uno por uno en el orden en que aparecen en el HTML, no
     se verian los <script>/<link> que vienen despues de este mismo
     tag en el documento (ej. auth.js, opiniones.js quedaban fuera). */
  function iniciar() {
    urls = urlsARevisar();
    setInterval(revisarCambios, 10000);
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden) revisarCambios();
    });
  }
  if (document.readyState === 'complete') iniciar();
  else window.addEventListener('load', iniciar);
})();
