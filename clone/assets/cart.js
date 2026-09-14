/* Carrito propio del sitio (sin backend): guarda el estado en
   localStorage para que persista entre index.html, tienda.html y
   carrito.html. Nada aquí se conecta a capsulasdenopal.com. */
(function (global) {
  var STORAGE_KEY = 'santebio_cart';
  var CHECKOUT_KEY = 'santebio_checkout_data';
  var BUYNOW_KEY = 'santebio_buynow';

  function getCart() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      return [];
    }
  }

  function saveCart(cart) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cart));
    updateCartBadges();
  }

  function addToCart(product) {
    var cart = getCart();
    var existing = cart.find(function (item) { return item.id === product.id; });
    if (existing) {
      existing.qty += product.qty || 1;
    } else {
      cart.push({
        id: product.id,
        name: product.name,
        price: product.price,
        image: product.image,
        qty: product.qty || 1,
      });
    }
    saveCart(cart);
  }

  function updateQty(id, qty) {
    var cart = getCart();
    var item = cart.find(function (i) { return i.id === id; });
    if (!item) return;
    item.qty = Math.max(1, qty);
    saveCart(cart);
  }

  function removeFromCart(id) {
    var cart = getCart().filter(function (i) { return i.id !== id; });
    saveCart(cart);
  }

  function clearCart() {
    saveCart([]);
  }

  function cartCount() {
    return getCart().reduce(function (sum, i) { return sum + i.qty; }, 0);
  }

  function cartTotal() {
    return getCart().reduce(function (sum, i) { return sum + i.qty * i.price; }, 0);
  }

  function formatMXN(n) {
    return '$' + n.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' MXN';
  }

  function saveCheckoutData(data) {
    localStorage.setItem(CHECKOUT_KEY, JSON.stringify(data));
  }

  function getCheckoutData() {
    try {
      var raw = localStorage.getItem(CHECKOUT_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function clearCheckoutData() {
    localStorage.removeItem(CHECKOUT_KEY);
  }

  /* "Comprar ahora" = compra directa: no se mezcla con el resto del
     carrito para el checkout (solo ese producto pasa a datos/pago),
     pero SI se agrega al carrito normal de una vez -- asi, si el
     cliente abandona el pago a la mitad, el producto no se pierde: se
     queda guardado en el carrito junto con lo demas que ya tuviera. */
  function iniciarCompraDirecta(producto) {
    addToCart(producto);
    try {
      localStorage.setItem(BUYNOW_KEY, JSON.stringify({
        id: producto.id,
        name: producto.name,
        price: producto.price,
        image: producto.image,
        qty: 1,
      }));
    } catch (e) {}
  }

  function getCompraDirecta() {
    try {
      var raw = localStorage.getItem(BUYNOW_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function cancelarCompraDirecta() {
    try { localStorage.removeItem(BUYNOW_KEY); } catch (e) {}
  }

  /* Lo que hay que mostrar/cobrar en datos.html y pago.html: si viene
     de un "Comprar ahora" (compra directa), es solo ese producto: si
     no, es el carrito completo de siempre. */
  function itemsCheckout() {
    var directa = getCompraDirecta();
    return directa ? [directa] : getCart();
  }

  function totalCheckout() {
    return itemsCheckout().reduce(function (sum, i) { return sum + i.qty * i.price; }, 0);
  }

  /* datos.html deja editar el pedido (cantidad/quitar) igual que antes
     se hacia en el carrito -- estas dos funciones deciden solo si el
     id que se esta editando es el de una compra directa en curso o un
     producto normal del carrito, para que datos.html no tenga que
     duplicar esa logica. */
  function actualizarCantidadCheckout(id, qty) {
    if (qty <= 0) { quitarDeCheckout(id); return; }
    var directa = getCompraDirecta();
    if (directa && String(directa.id) === String(id)) {
      directa.qty = qty;
      try { localStorage.setItem(BUYNOW_KEY, JSON.stringify(directa)); } catch (e) {}
      // El mismo producto tambien vive en el carrito normal (se agrego
      // ahi desde iniciarCompraDirecta) -- se mantiene la cantidad
      // sincronizada por si el cliente abandona el pago a la mitad.
      updateQty(id, qty);
    } else {
      updateQty(id, qty);
    }
  }

  function quitarDeCheckout(id) {
    var directa = getCompraDirecta();
    if (directa && String(directa.id) === String(id)) {
      cancelarCompraDirecta();
    }
    removeFromCart(id);
  }

  /* Se llama tras crear el pedido exitosamente: si fue compra directa
     solo se quita ESE producto del carrito (sin tocar lo demas que el
     cliente ya tuviera ahi); si fue el carrito completo, se vacia
     entero, igual que antes. */
  function finalizarCompra() {
    var directa = getCompraDirecta();
    if (directa) {
      removeFromCart(directa.id);
      cancelarCompraDirecta();
    } else {
      clearCart();
    }
  }

  /* Estrategia pedida por el cliente: al dar "Comprar ahora" ya no se
     manda al carrito -- si es invitado/nuevo usuario va directo a
     llenar sus datos de envio (datos.html); si ya tiene sesion
     iniciada y ya tiene una direccion guardada, se salta datos.html
     por completo y se va directo a pago.html con esa primera
     direccion ya seleccionada (puede volver a datos.html para
     cambiarla si quiere otra). Si tiene sesion pero aun no guarda
     ninguna direccion, no hay nada que precargar: pasa por datos.html
     como cualquier invitado. */
  function irACheckoutDirecto() {
    var usuarioActual = global.SanteBioAuth && global.SanteBioAuth.getUsuarioActual();
    if (!usuarioActual) {
      global.location.href = 'datos.html';
      return;
    }
    global.SanteBioAuth.llamarApi('listar_direcciones', {}, global.SanteBioAuth.getToken())
      .then(function (res) {
        if (res && res.direcciones && res.direcciones.length > 0) {
          var d = res.direcciones[0];
          saveCheckoutData({
            nombre: usuarioActual.nombre,
            telefono: usuarioActual.telefono,
            email: usuarioActual.correo,
            calle: d.calle,
            colonia: d.colonia,
            cp: d.cp,
            ciudad: d.ciudad,
            estado: d.estado,
            referencias: d.referencias || '',
          });
          global.location.href = 'pago.html';
        } else {
          global.location.href = 'datos.html';
        }
      })
      .catch(function () {
        global.location.href = 'datos.html';
      });
  }

  function updateCartBadges() {
    var count = cartCount();
    document.querySelectorAll('.sb-cart-badge').forEach(function (el) {
      el.textContent = count;
      el.style.display = count > 0 ? 'flex' : 'none';
    });
  }

  document.addEventListener('DOMContentLoaded', updateCartBadges);

  global.SanteBioCart = {
    getCart: getCart,
    addToCart: addToCart,
    updateQty: updateQty,
    removeFromCart: removeFromCart,
    clearCart: clearCart,
    cartCount: cartCount,
    cartTotal: cartTotal,
    formatMXN: formatMXN,
    updateCartBadges: updateCartBadges,
    saveCheckoutData: saveCheckoutData,
    getCheckoutData: getCheckoutData,
    clearCheckoutData: clearCheckoutData,
    iniciarCompraDirecta: iniciarCompraDirecta,
    getCompraDirecta: getCompraDirecta,
    cancelarCompraDirecta: cancelarCompraDirecta,
    itemsCheckout: itemsCheckout,
    totalCheckout: totalCheckout,
    actualizarCantidadCheckout: actualizarCantidadCheckout,
    quitarDeCheckout: quitarDeCheckout,
    finalizarCompra: finalizarCompra,
    irACheckoutDirecto: irACheckoutDirecto,
  };
})(window);
