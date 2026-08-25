/* Lista compartida de tiendas aliadas (pago.html y cuenta.html) donde
   el cliente puede pagar en efectivo su pedido. Datos de ejemplo -
   se reemplazaran por las tiendas reales en cuanto se tengan. */
var SanteBioTiendas = (function () {
  var EJEMPLO = [
    { nombre: 'Sucursal Centro', direccion: 'Av. Juárez 123, Centro, León, Gto. (ejemplo)' },
    { nombre: 'Sucursal Norte', direccion: 'Blvd. Adolfo López Mateos 456, Col. Norte, León, Gto. (ejemplo)' },
  ];

  function listaHtml() {
    return EJEMPLO.map(function (t) {
      return '<li><strong>' + t.nombre + '</strong> — ' + t.direccion + '</li>';
    }).join('');
  }

  return { EJEMPLO: EJEMPLO, listaHtml: listaHtml };
})();
