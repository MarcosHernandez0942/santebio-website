/* Carrito propio del sitio (sin backend): guarda el estado en
   localStorage para que persista entre index.html, tienda.html y
   carrito.html. Nada aquí se conecta a capsulasdenopal.com. */
(function (global) {
  var STORAGE_KEY = 'santebio_cart';
  var CHECKOUT_KEY = 'santebio_checkout_data';

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
  };
})(window);
