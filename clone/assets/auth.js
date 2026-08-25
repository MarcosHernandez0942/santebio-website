/* Cliente del API real de SanteBio (capsulas_nopal_santebio/api), mismo
   patron de un solo endpoint con campo "accion" que ya se usa en gaseti
   y visas_y_pasaportes_america. En produccion, cuando el sitio se
   despliegue en un dominio real, esta URL debe apuntar a donde quede
   corriendo ese servidor (o a una ruta /api/ que un proxy reenvie ahi). */
var SanteBioAuth = (function () {
  var BASE_URL = 'http://localhost:4931';
  var TOKEN_KEY = 'santebio_token';
  var USUARIO_KEY = 'santebio_usuario';
  var ADMIN_TOKEN_KEY = 'santebio_admin_token';
  var ADMIN_USUARIO_KEY = 'santebio_admin_usuario';

  var sesionYaExpiro = false;

  /* Si el token que se mando ya no es valido (p. ej. la sesion expiro
     tras 8 horas, ver api/auth.py), el servidor responde 401 "No
     autorizado." -- eso antes se quedaba mostrado como un error
     críptico en cada panel ("No se pudieron cargar tus direcciones:
     No autorizado"), dando la impresion de que los datos se habian
     perdido. Ahora se detecta ese caso, se limpia la sesion vencida y
     se recarga una vez para que la pagina vuelva a mostrar el login. */
  function manejarSesionExpirada(token) {
    if (sesionYaExpiro) return;
    if (token === localStorage.getItem(TOKEN_KEY)) {
      sesionYaExpiro = true;
      cerrarSesion();
      window.location.reload();
    } else if (token === localStorage.getItem(ADMIN_TOKEN_KEY)) {
      sesionYaExpiro = true;
      cerrarSesionAdmin();
      window.location.reload();
    }
  }

  function llamarApi(accion, datos, token) {
    return fetch(BASE_URL + '/api/accion', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(Object.assign({ accion: accion, token: token || null }, datos || {})),
    })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (data) {
          if (r.status === 401 && token) manejarSesionExpirada(token);
          if (typeof data.ok === 'boolean') return data;
          if (!r.ok) return { ok: false, error: data.error || 'Error del servidor (' + r.status + ').' };
          return Object.assign({ ok: true }, data);
        });
      })
      .catch(function () {
        return { ok: false, error: 'No se pudo conectar con el servidor. Intenta de nuevo.' };
      });
  }

  function registrarUsuario(datos) {
    return llamarApi('registro_usuario', datos).then(function (res) {
      if (res.ok) {
        localStorage.setItem(TOKEN_KEY, res.token);
        localStorage.setItem(USUARIO_KEY, JSON.stringify(res.usuario));
      }
      return res;
    });
  }

  function iniciarSesionUsuario(datos) {
    return llamarApi('login_usuario', datos).then(function (res) {
      if (res.ok) {
        localStorage.setItem(TOKEN_KEY, res.token);
        localStorage.setItem(USUARIO_KEY, JSON.stringify(res.usuario));
      }
      return res;
    });
  }

  function iniciarSesionAdmin(datos) {
    return llamarApi('login_admin', datos).then(function (res) {
      if (res.ok) {
        localStorage.setItem(ADMIN_TOKEN_KEY, res.token);
        localStorage.setItem(ADMIN_USUARIO_KEY, datos.usuario);
      }
      return res;
    });
  }

  function actualizarPerfil(datos) {
    return llamarApi('actualizar_perfil', datos, getToken()).then(function (res) {
      if (res.ok) {
        localStorage.setItem(TOKEN_KEY, res.token);
        localStorage.setItem(USUARIO_KEY, JSON.stringify(res.usuario));
      }
      return res;
    });
  }

  function solicitarCambioPassword(datos) {
    return llamarApi('solicitar_cambio_password', datos, getToken());
  }

  function confirmarCambioPassword(datos) {
    return llamarApi('confirmar_cambio_password', datos);
  }

  function cerrarSesion() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USUARIO_KEY);
  }

  function cerrarSesionAdmin() {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
    localStorage.removeItem(ADMIN_USUARIO_KEY);
  }

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function getUsuarioActual() {
    try {
      var raw = localStorage.getItem(USUARIO_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function getAdminToken() {
    return localStorage.getItem(ADMIN_TOKEN_KEY);
  }

  function getAdminUsuario() {
    return localStorage.getItem(ADMIN_USUARIO_KEY);
  }

  return {
    llamarApi: llamarApi,
    registrarUsuario: registrarUsuario,
    iniciarSesionUsuario: iniciarSesionUsuario,
    iniciarSesionAdmin: iniciarSesionAdmin,
    actualizarPerfil: actualizarPerfil,
    solicitarCambioPassword: solicitarCambioPassword,
    confirmarCambioPassword: confirmarCambioPassword,
    cerrarSesion: cerrarSesion,
    cerrarSesionAdmin: cerrarSesionAdmin,
    getToken: getToken,
    getUsuarioActual: getUsuarioActual,
    getAdminToken: getAdminToken,
    getAdminUsuario: getAdminUsuario,
  };
})();
