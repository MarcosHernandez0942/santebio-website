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
    return Promise.all(urls.map(function (url) {
      return fetch(url, { cache: 'no-store' })
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
