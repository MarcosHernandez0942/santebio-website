/* Helpers compartidos para opiniones/calificaciones -- usado en
   opiniones.html (opinion general del sitio), cuenta.html (calificar
   un producto de un pedido) y admin.html (mostrar las estrellas). */
var SanteBioOpiniones = (function () {
  function crearEstrellaPicker(contenedor, valorInicial) {
    var valor = valorInicial || 0;
    contenedor.innerHTML = '';
    for (var i = 1; i <= 5; i++) {
      var span = document.createElement('span');
      span.textContent = '★';
      span.dataset.valor = i;
      contenedor.appendChild(span);
    }

    function pintar() {
      contenedor.querySelectorAll('span').forEach(function (s) {
        s.classList.toggle('is-activa', parseInt(s.dataset.valor, 10) <= valor);
      });
    }

    contenedor.querySelectorAll('span').forEach(function (s) {
      s.addEventListener('click', function () {
        valor = parseInt(s.dataset.valor, 10);
        pintar();
      });
    });

    pintar();
    return { getValor: function () { return valor; } };
  }

  function estrellasHtml(n) {
    return '★★★★★☆☆☆☆☆'.slice(5 - n, 10 - n);
  }

  return { crearEstrellaPicker: crearEstrellaPicker, estrellasHtml: estrellasHtml };
})();
