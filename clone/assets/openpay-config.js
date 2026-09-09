/* Configuracion PUBLICA de Openpay (BBVA) para el checkout.
   La llave publica SI puede vivir aqui, en el navegador -- es justo
   para lo que Openpay la diseño (solo permite crear tokens de
   tarjeta, nunca cobrar). La llave PRIVADA nunca va en este archivo
   ni en ningun otro del sitio -- esa vive solo en el servidor
   (api/.env, ver openpay_client.py).

   Mientras el cliente no tenga cuenta de Openpay, se deja vacio a
   proposito: pago.html detecta que merchantId esta vacio y muestra
   "tarjeta" y "tiendas aliadas" como no disponibles en vez de dejar
   que fallen a medias. En cuanto el cliente tenga su Merchant ID +
   llave publica (aunque sea de su cuenta de pruebas/sandbox), se
   pegan aqui abajo y el checkout empieza a funcionar solo. */
var SanteBioOpenpay = {
  merchantId: '',
  publicKey: '',
  sandbox: true,
};
