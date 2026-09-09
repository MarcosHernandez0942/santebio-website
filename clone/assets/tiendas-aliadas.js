/* Logos oficiales de las tiendas donde se puede pagar en efectivo un
   pedido con "tiendas aliadas" (pago en tienda/Paynet, via Openpay
   BBVA). Los logos vienen del kit de marca oficial de Openpay
   (public.openpay.mx/web/descargables/.../paynet-kit.zip). Esta NO es
   la lista completa de tiendas afiliadas -- son las cadenas mas
   reconocidas, solo para mostrar visualmente que se acepta pago en
   efectivo; el pago real se valida por el codigo de barras/referencia
   que entrega Openpay al crear el pedido, no por esta lista. */
var SanteBioTiendas = (function () {
  var BASE = 'wp-content/uploads/2026/09/pagos/';

  var LOGOS = [
    { nombre: '7-Eleven', archivo: 'tienda-7eleven.png' },
    { nombre: 'Circle K', archivo: 'tienda-circlek.png' },
    { nombre: 'Extra', archivo: 'tienda-extra.png' },
    { nombre: 'Soriana', archivo: 'tienda-soriana.png' },
    { nombre: 'Walmart', archivo: 'tienda-walmart.png' },
    { nombre: 'Walmart Express', archivo: 'tienda-walmart-express.png' },
    { nombre: 'Bodega Aurrerá', archivo: 'tienda-bodega-aurrera.png' },
    { nombre: 'Farmacia Guadalajara', archivo: 'tienda-farmacia-guadalajara.png' },
    { nombre: "Waldo's", archivo: 'tienda-waldos.png' },
    { nombre: "Sam's Club", archivo: 'tienda-sams-club.png' },
  ];

  function logosHtml() {
    return LOGOS.map(function (t) {
      return '<img src="' + BASE + t.archivo + '" alt="' + t.nombre + '" loading="lazy" />';
    }).join('');
  }

  return { LOGOS: LOGOS, logosHtml: logosHtml };
})();
