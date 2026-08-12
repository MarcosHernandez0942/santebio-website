# Auditoría técnica del proyecto — `demo_capsulas_nopal`

## 1. Resumen ejecutivo

- **Fecha/hora:** 2026-08-12 (re-auditoría de solo lectura).
- **Rama/commit:** `initMarc` @ `502b608` ("Agregar cursor personalizado con forma de nopal"). `git status --porcelain` limpio salvo `AUDITORIA_TECNICA.md`.
- **Alcance:** rediseño para "SanteBio" (cápsulas de nopal), con un hallazgo estructural atípico: `clone/` es una **réplica estática completa del sitio WordPress/WooCommerce real del cliente** (`capsulasdenopal.com`), usada como punto de partida, y el `Dockerfile` de la raíz **construye y despliega ese clon, no el rediseño nuevo** (`site/`).
- **Componentes:** `site/` = React 19.2.8 + Vite 8.2.0; `clone/server.js` = servidor HTTP Node.js nativo de 34 líneas sin framework.
- **Puntuación matemática:** **5.8 / 100.**
- **Nivel:** **Riesgo crítico (0-39.9).**
- **Hallazgos por severidad:** Alta: 1 · Media: 3 · Baja: 1 · Informativa: 2.
- **Conclusión:** el hallazgo más relevante de este proyecto no es de seguridad clásica sino de **integridad del pipeline de despliegue**: el Docker actual publica el sitio clonado de terceros (con su pixel de Facebook Ads activo) en vez del rediseño que el proyecto declara construir.

## 2. Alcance y limitaciones

**Revisado:** `site/`, `clone/` (solo lectura, sin ejecutar `server.js`), Dockerfile/docker-compose/.dockerignore de la raíz.
**No realizado:** build/ejecución de Docker o de `clone/server.js`.
**No verificable:** legalidad del contenido clonado (fuera de alcance de una auditoría técnica); si `capsulasdenopal.com` es el mismo cliente (README lo afirma, no verificado independientemente).

## 3. Tablero general

| Grupo | Peso | Aplicable | Calificación | Nivel |
|---|---|---|---|---|
| 1. Arquitectura | 10% | Sí | 0.0 | Riesgo crítico |
| 2. Backend | 10% | Sí | 0.0 | Riesgo crítico |
| 3. Frontend (68/100 aplicable) | 8% | Sí | 20.6 | Riesgo crítico |
| 4. PostgreSQL | 10% | Sí | 0.0 | Riesgo crítico |
| 5. Auth/RBAC | 12% | Sí | 0.0 | Riesgo crítico |
| 6. Seguridad (34/100 aplicable) | 15% | Sí | 8.8 | Riesgo crítico |
| 7. Pruebas | 10% | Sí | 0.0 | Riesgo crítico |
| 8. CI/CD | 8% | Sí | 7.5 | Riesgo crítico |
| 9. Docker (82/100 aplicable) | 7% | Sí | 0.0 | Riesgo crítico |
| 10. Observabilidad | 5% | Sí | 0.0 | Riesgo crítico |
| 11. Documentación (44/100 aplicable) | 5% | Sí | 45.5 | Riesgo crítico |
| **TOTAL** | **100%** | — | **5.8** | **Riesgo crítico** |

## 4. Hallazgos críticos y altos

| ID | Severidad | Grupo | Hallazgo | Evidencia | Impacto | Recomendación |
|---|---|---|---|---|---|---|
| NP-H1 | Alta | 9. Docker | El `Dockerfile` construye y publica `clone/` (sitio de terceros), no `site/` (el rediseño) | `Dockerfile` completo: `FROM nginx:alpine`, `COPY clone/ /usr/share/nginx/html/` | Si la intención es lanzar el rediseño, el pipeline actual no lo logra; además publica contenido de terceros con su pixel de tracking activo | Corregir el `Dockerfile` para construir `site/` (`npm run build` + copiar `dist/`) |
| NP-M1 | Media | 6. Seguridad | `clone/` contiene un Pixel de Meta/Facebook activo de un tercero | `clone/index.html` (`fbq('init','1600549497670830')`) | Cualquier despliegue del clon (incluso de prueba) envía datos de visitantes a la cuenta de Facebook Ads del cliente | No desplegar `clone/` como si fuera producción; considerar removerlo del repo una vez usado como referencia |
| NP-M2 | Media | 6. Seguridad | Endpoints AJAX del clon apuntan a la infraestructura WooCommerce real del cliente | `clone/index.html` (`admin-ajax.php`, `wc-ajax`, 47 referencias a `capsulasdenopal.com`) | Interacciones de carrito/checkout en una copia local intentarían alcanzar producción real del cliente | Ídem NP-M1 |
| NP-M3 | Media | 11. Documentación | El README no advierte que el Docker actual despliega el clon en vez del rediseño | `README.md:8` describe `clone/` correctamente pero no menciona la discrepancia del `Dockerfile` | Riesgo de que se despliegue el sitio equivocado sin darse cuenta | Documentar explícitamente esta discrepancia |
| NP-B1 | Baja | 9. Docker | Sin usuario no-root, sin healthcheck | `Dockerfile` de 5 líneas | Root en el contenedor | Agregar `USER`/`HEALTHCHECK` cuando se corrija NP-H1 |
| NP-I1 | Informativa | 9. Docker | `clone/` no contiene PHP ejecutable, solo assets estáticos | Confirmado: `find clone/wp-content -iname "*.php"` vacío | Sin superficie de ataque "WordPress clásico" ejecutable en este repo | — |
| NP-I2 | Informativa | 3. Frontend | `site/` (el rediseño real) no tiene ningún formulario ni backend propio | Confirmado por grep de `<form>` sin resultados | — | — |

## 5. Resultados detallados por grupo

### 5.1-5.2 Arquitectura y Backend (0.0 cada uno)

Sin backend Flask en ninguno de los dos componentes (`site/` es puramente estático; `clone/server.js` es un servidor Node.js estático sin framework). Todos los controles **❌ No implementado**.

### 5.3 Frontend React/Vite (20.6 sobre 68 aplicables, evaluando `site/`)

| ID | Control | Estado | Peso | Puntos | Evidencia | Riesgo | Recomendación |
|---|---|---|---|---|---|---|---|
| G3.1 | Versiones controladas | ⚠️ Parcial | 10 | 5.0 | React 19.2.8/Vite 8.2.0 | — | Fijar versiones exactas |
| G3.2 | TypeScript | ❌ No implementado | 10 | 0.0 | JS/JSX puro | — | Migrar a TS |
| G3.3 | Organización | ⚠️ Parcial | 10 | 5.0 | `Hero`, `VideoBackground`, `SplitVideoSection`, `IntroVideo`, `Reveal` | — | Mantener |
| G3.7 | ESLint/Prettier | ⚠️ Parcial | 8 | 4.0 | `oxlint` declarado (`site/package.json:9`) | Reglas no detalladas en esta revisión | Confirmar configuración real |
| G3.8 | Tests | ❌ No implementado | 10 | 0.0 | Sin evidencia | — | Vitest |
| G3.9 | Loading/error states | ❌ No implementado | 10 | 0.0 | Sin formularios en `site/` (ver NP-I2) | — | — |
| G3.10 | Build reproducible/CSP/secretos | ❌ No implementado | 10 | 0.0 | Ver NP-H1 — `site/` nunca se construye realmente en Docker | Ver NP-H1 | Ver NP-H1 |

*(G3.4, G3.5, G3.6 marcados No aplica — sin formularios/auth en `site/`.)*

### 5.4 PostgreSQL (0.0) / 5.5 Auth (0.0)

Sin BD ni autenticación en ningún componente — todos **❌ No implementado**.

### 5.6 Seguridad y cifrado (8.8 sobre 34 aplicables)

| ID | Control | Estado | Peso | Puntos | Evidencia | Riesgo | Recomendación |
|---|---|---|---|---|---|---|---|
| G6.1 | TLS en tránsito | ❌ No implementado | 12 | 0.0 | `nginx:alpine` con config por defecto, sin TLS | — | TLS en producción real |
| G6.2 | Headers de seguridad | ❌ No implementado | 8 | 0.0 | Config nginx por defecto, sin headers custom | — | Agregar headers |
| G6.5 | Protección XSS | ⚠️ Parcial | 6 | 3.0 | `site/` sin `dangerouslySetInnerHTML`; `clone/` es HTML de terceros no evaluable como código propio | Ver NP-M1/M2 para riesgos del clon | — |
| G6.10 | SAST/DAST/escaneo | ❌ No implementado | 8 | 0.0 | Sin herramientas | — | Integrar escaneo |

### 5.7 Pruebas (0.0) / 5.10 Observabilidad (0.0)

Sin backend/BD que probar u observar — todos los controles aplicables (solo frontend en G7) **❌ No implementado**.

### 5.8 CI/CD (7.5)

Mismo patrón: G8.4 (lockfile de `site/`) ⚠️ Parcial=7.5; resto ❌/❓.

### 5.9 Docker, Kubernetes y despliegue (0.0 sobre 82 aplicables)

| ID | Control | Estado | Peso | Puntos | Evidencia | Riesgo | Recomendación |
|---|---|---|---|---|---|---|---|
| G9.1 | Dockerfile multi-stage | ❌ No implementado | 12 | 0.0 | 5 líneas triviales, single-stage, no builda `site/` | Ver NP-H1 | Ver NP-H1 |
| G9.2 | Usuario no-root | ❌ No implementado | 12 | 0.0 | Ver NP-B1 | Ver NP-B1 | Ver NP-B1 |
| G9.3 | Healthchecks | ❌ No implementado | 8 | 0.0 | Sin evidencia | — | — |
| G9.4 | Límites de recursos | ❌ No implementado | 8 | 0.0 | Sin evidencia | — | — |
| G9.7 | Kubernetes/Helm | ❌ No implementado | 15 | 0.0 | Sin manifiestos | — | — |
| G9.8 | NGINX/Ingress real | ❌ No implementado | 10 | 0.0 | Nginx sirve el contenido equivocado (ver NP-H1) | Ver NP-H1 | Ver NP-H1 |
| G9.9 | Ambientes separados/IaC | ❌ No implementado | 9 | 0.0 | Sin IaC | — | — |
| G9.10 | Despliegue progresivo/DR | ❌ No implementado | 8 | 0.0 | Sin evidencia | — | — |

### 5.11 Documentación (45.5 sobre 44 aplicables)

| ID | Control | Estado | Peso | Puntos | Evidencia | Riesgo | Recomendación |
|---|---|---|---|---|---|---|---|
| G11.1 | README completo | ✅ Implementado | 20 | 20.0 | Explica `clone/` correctamente | Ver NP-M3 (omisión específica) | Ver NP-M3 |
| G11.2 | Arquitectura/ADR | ❌ No implementado | 12 | 0.0 | Sin ADR sobre la decisión de clonar el sitio | — | Documentar decisión |
| G11.4 | Backup/despliegue documentado | ⚠️ Parcial | 12 | 6.0 | `docker compose up --build` documentado; no advierte NP-H1 | Ver NP-M3 | Ver NP-M3 |

## 6. Validaciones ejecutadas

| Validación | Comando/método | Resultado | Observaciones |
|---|---|---|---|
| Confirmación de contenido de `clone/` | Lectura de `clone/index.html`, búsqueda de `generator`/`wp-json`/`fbq` | Confirmado: WordPress/WooCommerce/Elementor + pixel de FB reales | Sin abrir/ejecutar nada, solo lectura |
| Confirmación de ausencia de PHP | `find clone/wp-content clone/wp-includes -iname "*.php"` | Vacío | Confirma NP-I1 |
| Lectura de `Dockerfile` | Lectura completa (5 líneas) | Confirma NP-H1 | — |
| Historial y estado de git | `git log --oneline -15`, `git status --porcelain` | `initMarc`, 15 commits, limpio | — |

## 7. Riesgos priorizados

| Prioridad | ID | Severidad | Esfuerzo | Riesgo | Acción |
|---|---|---|---|---|---|
| 1 | NP-H1 | Alta | Medio | Docker despliega el clon, no el rediseño | Corregir Dockerfile para construir `site/` |
| 2 | NP-M1 | Media | Bajo | Pixel de FB de terceros activo | No desplegar `clone/` como producción |
| 3 | NP-M2 | Media | Bajo | Endpoints reales del cliente embebidos | Ídem |
| 4 | NP-M3 | Media | Bajo | README no advierte la discrepancia | Documentar |

## 8. Plan de remediación

**Fase 1 — Inmediata:** confirmar con el equipo si el Docker actual (que sirve `clone/`) es intencional o un error; si es error, corregir a construir `site/`. *Complejidad:* baja-media.
**Fase 2 — Corto plazo:** eliminar o aislar claramente `clone/` del pipeline de build una vez que `site/` esté listo para reemplazarlo. *Complejidad:* baja.
**Fase 3 — Mediano plazo:** cuando `site/` esté completo, aplicar el mismo Dockerfile multi-stage usado en proyectos hermanos (`demo_autos_1`/`demo_casas_1`).

## 9. Mejoras rápidas

1. Verificar con el equipo si `Dockerfile` debería construir `site/` en vez de `clone/`.
2. No exponer `clone/` en ningún entorno accesible públicamente.
3. Documentar en el README la discrepancia actual del pipeline de Docker.
4. Agregar `USER` no-root cuando se corrija el Dockerfile.

## 10. Controles no verificables

| Control | Motivo | Evidencia necesaria |
|---|---|---|
| Si `capsulasdenopal.com` es efectivamente el mismo cliente de este proyecto | No verificable desde el código | Confirmación del equipo/contrato |
| Estado real de vigencia de las versiones de WordPress/WooCommerce/Elementor declaradas | Fuera de alcance, no son ejecutables en este repo | Auditoría del sitio de origen si se requiere |

## 11. Controles no aplicables

| Control | Justificación |
|---|---|
| Router/rutas protegidas, sesión segura (G3.4/6) | `site/` es una landing sin formularios ni auth |
| CORS, SQLi, CSRF, uploads, rate limiting, webhooks, cifrado en reposo (G6.3/4/6/7/9/11/12) | Sin backend/BD propios |
| Todos los controles de G7.1/2/3/7 | Sin backend/BD que probar |
| Modelo de datos/roles, privacidad, ARCO, incidentes (G11.3/5/6/7) | Sin BD ni PII propia recolectada en `site/` |

## 12. Conclusión

**Estado:** `demo_capsulas_nopal` obtiene **5.8/100 — Riesgo crítico**, la calificación más baja de los sitios de marketing del portafolio, por el hallazgo específico NP-H1.
**Fortalezas:** `site/` (el rediseño) está razonablemente bien construido en su propio alcance; sin PHP ejecutable en el clon.
**Riesgos principales:** el pipeline de Docker despliega el sitio equivocado, con tracking de terceros activo.
**Siguiente paso recomendado:** aclarar y corregir NP-H1 antes de cualquier despliegue, dado que es el hallazgo con mayor probabilidad de causar confusión operativa real.
