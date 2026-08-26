/* Notificaciones "toast" en vivo -- avisos que aparecen mientras el
   admin o el cliente estan navegando la pagina (pedido nuevo, cambio
   de estatus). Compartido entre admin.html y cuenta.html. */
var SanteBioToast = (function () {
  function contenedor() {
    var el = document.getElementById('sb-toast-contenedor');
    if (!el) {
      el = document.createElement('div');
      el.id = 'sb-toast-contenedor';
      document.body.appendChild(el);
    }
    return el;
  }

  function mostrar(mensaje) {
    var toast = document.createElement('div');
    toast.className = 'sb-toast';
    toast.textContent = mensaje;
    contenedor().appendChild(toast);
    setTimeout(function () {
      toast.classList.add('sb-toast-saliendo');
      setTimeout(function () { toast.remove(); }, 300);
    }, 7000);
  }

  return { mostrar: mostrar };
})();
