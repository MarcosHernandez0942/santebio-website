/* Autocompletar ciudad/estado y sugerir colonias segun el codigo
   postal, usando la API publica y gratuita de codigos postales de
   Mexico cp.terio.dev (con CORS abierto, sin necesitar llave). Si el
   CP no se encuentra o falla la consulta, no pasa nada: el usuario
   sigue pudiendo llenar todo a mano como antes.
   Se comparte entre datos.html y el formulario de direcciones de
   cuenta.html, cada uno con sus propios IDs de campo (parametro
   "ids"), para no duplicar esta logica dos veces. */
var SanteBioCP = (function () {
  function wire(ids) {
    var cpInput = document.getElementById(ids.cp);
    var cpHint = document.getElementById(ids.hint);
    var cpDebounceTimer;
    var lastLookedUpCp = null;

    function setColoniaField(colonias, currentValue) {
      var oldField = document.getElementById(ids.colonia);
      var newField;
      if (colonias && colonias.length > 0) {
        newField = document.createElement('select');
        newField.id = ids.colonia;
        newField.name = ids.colonia;
        newField.required = true;
        var placeholder = document.createElement('option');
        placeholder.value = '';
        placeholder.textContent = colonias.length > 1 ? 'Selecciona tu colonia...' : colonias[0];
        if (colonias.length > 1) newField.appendChild(placeholder);
        colonias.forEach(function (c) {
          var opt = document.createElement('option');
          opt.value = c;
          opt.textContent = c;
          if (c === currentValue || colonias.length === 1) opt.selected = true;
          newField.appendChild(opt);
        });
        // Si la colonia guardada no coincide exactamente con ninguna de
        // las que regresa la API para este CP (p. ej. cambio de nombre
        // con el tiempo), se agrega igual como opcion seleccionada en
        // vez de perderla en silencio dejando el campo vacio.
        if (currentValue && colonias.indexOf(currentValue) === -1) {
          var opcionActual = document.createElement('option');
          opcionActual.value = currentValue;
          opcionActual.textContent = currentValue;
          opcionActual.selected = true;
          newField.insertBefore(opcionActual, newField.firstChild);
        }
      } else {
        newField = document.createElement('input');
        newField.type = 'text';
        newField.id = ids.colonia;
        newField.name = ids.colonia;
        newField.required = true;
        newField.placeholder = 'Ingresa tu código postal primero';
        newField.value = currentValue || '';
      }
      oldField.parentElement.replaceChild(newField, oldField);
    }

    function lookupCP(cp) {
      if (cp === lastLookedUpCp) return;
      lastLookedUpCp = cp;
      if (cpHint) cpHint.textContent = 'Buscando colonias...';
      fetch('https://cp.terio.dev/v1/codigos-postales/' + cp)
        .then(function (r) {
          if (!r.ok) throw new Error('cp no encontrado');
          return r.json();
        })
        .then(function (data) {
          var registros = (data && data.datos) || [];
          if (registros.length === 0) throw new Error('sin resultados');
          document.getElementById(ids.ciudad).value = registros[0].ciudad || registros[0].municipio || '';
          document.getElementById(ids.estado).value = registros[0].estado || '';
          var currentColoniaValue = document.getElementById(ids.colonia).value;
          var colonias = registros.map(function (r) { return r.asentamiento; });
          setColoniaField(colonias, currentColoniaValue);
          if (cpHint) {
            cpHint.textContent = colonias.length > 1
              ? colonias.length + ' colonias encontradas para este código postal.'
              : '';
          }
        })
        .catch(function () {
          if (document.getElementById(ids.colonia).tagName === 'SELECT') {
            document.getElementById(ids.ciudad).value = '';
            document.getElementById(ids.estado).value = '';
            setColoniaField(null, '');
          }
          if (cpHint) cpHint.textContent = '';
        });
    }

    cpInput.addEventListener('input', function () {
      clearTimeout(cpDebounceTimer);
      var cp = cpInput.value.trim();
      if (!/^[0-9]{5}$/.test(cp)) {
        if (cpHint) cpHint.textContent = '';
        return;
      }
      cpDebounceTimer = setTimeout(function () { lookupCP(cp); }, 350);
    });

    if (/^[0-9]{5}$/.test(cpInput.value.trim())) {
      lookupCP(cpInput.value.trim());
    }

    return { lookupCP: lookupCP };
  }

  return { wire: wire };
})();
