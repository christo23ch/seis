---
tipo: fase
numero: 11
estado: en-progreso
tags:
  - tipo/fase
  - fase/11
  - estado/en-progreso
  - area/infra
---

# Fase 11 — Infraestructura de producción

> **Plan canónico: `docs/FASE_11_PLAN.md`** (aprobado por el responsable el 2026-07-30). Esta nota **no lo copia**: enlaza a él y añade la capa de Obsidian. Cualquier detalle que no esté aquí está allí, y allí manda.

## Objetivo (literal del Plan Maestro)

> «Un entorno real en internet con dominio, HTTPS, copias de seguridad probadas y alarmas, más un entorno de pruebas (staging) idéntico.»

Ver [[Plan-Maestro|Plan Maestro]] §Fase 11 para el contrato completo.

## La fase está partida en 11-A y 11-B

Con el proveedor de hosting, el dominio y el proveedor de email **diferidos** (H1, H2, H6), no se puede escribir la IaC, ni los jobs de despliegue, ni un runbook que no sea ficción. Pero los bloques agnósticos del proveedor sí son ejecutables hoy, e incluyen la puerta de despliegue que ahora mismo impide exponer el producto a internet.

- **11-A — de repositorio, agnóstica del proveedor.** Ejecutable ya. Un PR.
- **11-B — dependiente del proveedor.** Bloqueada hasta que se cierren H1, H2 y H6. Otro PR.

**La Fase 11 no se declara cerrada al fusionar 11-A.** Sus criterios de salida son operativos y ninguno es alcanzable sin la 11-B.

## Requisitos

Bloques de la **Fase 11-A**. El detalle fichero a fichero de cada uno está en `docs/FASE_11_PLAN.md` §3.

| # | Requisito | Obligatorio/Opcional | Estado |
|---|---|---|---|
| A | Salud por componente: liveness intacto, readiness pública, detalle autenticado | Obligatorio | ✅ Completado |
| C′ | Higiene de despliegue portable (`.dockerignore`, ancla de entorno, `beat` propio, `.env.produccion.example`, loopback por defecto) | Obligatorio | ✅ **Cerrado** tras tres revisiones |
| D | `staging` como **cuarto entorno estricto**, no solo soportado | Obligatorio | ✅ Completado |
| E | `create_all` fuera de la ruta de producción | Obligatorio | ⬜ Pendiente |
| F′ | CI que ejecute la **suite completa** y `npm run build`, no 1 de 14 ficheros | Obligatorio | ⬜ Pendiente |
| H | IP real tras proxy — la puerta de despliegue heredada de la Fase 10 | Obligatorio | ⬜ Pendiente |
| I | Deudas heredadas con propietario «Fase 11» (reintento de Redis, purga de `token_consumido`, cuentas nunca verificadas) | Obligatorio | ⬜ Pendiente |

## Decisiones tomadas y diferidas (H0-H10)

Resumen. **Detalle completo y evidencia en `docs/FASE_11_PLAN.md` §1.**

| # | Asunto | Resolución |
|---|---|---|
| H0 | ¿Fusionar la Fase 10 o ramificar desde ella? | ✅ **Cerrado, premisa refutada.** La Fase 10 y el Vault ya estaban en `main`. Toda rama nueva sale de `main`. |
| H1 | Proveedor de hosting | ⏸ **Diferido.** No se escribe IaC de ningún proveedor; todo agnóstico. |
| H2 | Dominio y subdominios | ⏸ **Diferido.** Prohibido codificar dominios a fuego; todo por variables de entorno. |
| H3 | Presupuesto | ⏸ **Diferido.** Ninguna decisión técnica se condiciona al coste. |
| H4 | ¿Frontend en un proveedor distinto? | ✅ Mismo proveedor que el backend. |
| H5 | Sentry | ⛔ **Fuera de esta fase** — ver el apartado siguiente. |
| H6 | Proveedor de email | ⏸ **Diferido.** No se integra ninguno; sí se propaga su configuración. |
| H7 | `staging` estricto · beat separado del worker | ✅ Ambas sí. Bloques D y C′. |
| H8 | Quién aprueba el despliegue | ✅ El responsable del proyecto, disparo manual. Se materializa en 11-B. |
| H9 | Numeración de migración | ✅ **Esta fase no lleva migraciones. No se crea la `0007`.** Se refiere a la **revisión Alembic** `0007`, que sigue libre para la Fase 13; no confundir con [[ADR-0007-planificador-celery-separado-del-worker]], que es otra serie y sí existe. |
| H10 | Downtime | ✅ Corte aceptado en el primer despliegue; a partir de ahí, migraciones retrocompatibles. |
| CF | Cloudflare | ✅ El Bloque H se diseña con Cloudflare desde el inicio: no basta con leer `X-Forwarded-For`. |

## Sentry queda fuera de la fase

El **requisito 2 del prompt del Plan Maestro** pide integración de Sentry en backend y frontend, activada solo si existe `SENTRY_DSN`. **No se entrega, por decisión del responsable (H5).**

Se anota sin maquillar: **esto incumple deliberadamente ese requisito del contrato.** No es un olvido ni un «pendiente menor». La huella completa de Sentry en esta fase es **una variable `SENTRY_DSN` declarada y vacía**, documentada como sin consumidor. Queda como deuda abierta **sin fase propietaria asignada**.

Desde el Bloque C′ esa variable ya está escrita en `.env.produccion.example`, y con ella la consecuencia sin maquillar: **mientras `SENTRY_DSN` no tenga consumidor, un error 500 en producción no avisa a nadie.**

## Suite de tests

**Línea base oficial de la fase, fijada por el responsable:**

> **162 recogidos · 159 pasan · 2 fallan (los de PDF, preexistentes) · 1 omitido.**

Es la **única cifra citable** en documentación y auditorías. Las anteriores (118, 104) quedan derogadas.

**Tras el Bloque A (medido):** **172 recogidos · 169 pasan · 2 fallan · 1 omitido.** Es decir, **+10 verdes y 0 regresiones**; los 2 rojos siguen siendo los mismos de PDF y el omitido sigue siendo T5.

**Tras el Bloque D (medido):** **181 recogidos · 178 pasan · 2 fallan · 1 omitido.** Acumulado frente a la línea base: **+19 verdes y 0 regresiones**.

**Tras el Bloque C′, cifra final tras las tres revisiones (medida):** **220 recogidos · 217 pasan · 2 fallan · 1 omitido.** Acumulado frente a la línea base: **+58 verdes y 0 regresiones**. Los 2 rojos siguen siendo los de PDF y el omitido sigue siendo T5. Las medidas intermedias del bloque (212 y 233) quedan derogadas por esta.

> **El número de tests BAJÓ respecto de la medición intermedia de 233, y conviene decirlo sin adornar.** No es pérdida de cobertura: es lo contrario. Un test de inventario con **16 parámetros escritos a mano** se sustituyó por **2 tests derivados del propio `docker-compose.yml`**, y se retiró un test que fijaba como invariante una decisión de empaquetado reversible. **Menos elementos, más cobertura real** — contar tests mide el tamaño de la batería, no lo que la batería demuestra.

## Cierre del Bloque C′: qué encontraron las tres revisiones

Tres revisiones independientes (`security-reviewer`, `pr-test-analyzer`, `code-reviewer`) devolvieron **APROBADO CON RESERVAS**, con **0 CRITICAL**. Todos los hallazgos bloqueantes se corrigieron dentro del propio bloque. Lo que importa retener:

- **Dos HIGH de seguridad, ambos abiertos por este mismo bloque y cerrados en él.** (1) `.gitignore` no protegía `.env.produccion`, que es justo el nombre que la plantilla nueva invita a crear: medido con `git check-ignore`, un `git add .` rutinario —sin `-f`— habría publicado `JWT_SECRET`, `ADMIN_PASSWORD`, `POSTGRES_PASSWORD` y las credenciales de correo. (2) `smtp.starttls()` sin contexto TLS usaba `CERT_NONE` y `check_hostname=False`: cualquier certificado autofirmado completaba el handshake, y con él se capturaban las credenciales SMTP **y los enlaces de verificación y de reseteo de contraseña**, que son la toma de cualquier cuenta. Era código muerto bajo Docker hasta que este bloque propagó las credenciales SMTP al contenedor: **se cerró en el mismo movimiento que lo activó**.
- **Tres falsos verdes, reproducidos por mutación real antes de arreglarlos.** El test del planificador pasaba aunque `beat` fuese un `celery worker --beat`; los 20 tests del entorno estricto llamaban a una función privada, de modo que **borrar la línea que invoca la guardia dentro de `get_settings` dejaba la guardia muerta y todos verdes** —y el entregable del Bloque D no era que una función devolviera un error, era que **el proceso no arrancase**—; y `VERSION_REGLAS` / `VERSION_PARAMETROS` **no llegaban a ningún contenedor**, lo cual no era laguna de test sino defecto real: son las versiones que cada análisis congela por **P1 (determinismo)**, así que ajustarlas en `.env` no tenía efecto bajo Docker. En los dos primeros, la mutación aplicada hace **fallar** el test corregido; verificado.
- **Una desviación del alcance aprobado, registrada sin maquillar:** se tocó la publicación de puertos, que el plan difería a la Fase 16. Ver [[ADR-0008-loopback-por-defecto-en-los-puertos-publicados]] y `docs/FASE_11_PLAN.md` §3 bis.

## Criterio de salida (literal)

> «app accesible en `https://app.tudominio.com`, staging funcionando, un deploy automático a staging al fusionar en `main`, alarma recibida al simular una caída, y restauración documentada.»

**ABIERTO.** Ninguno de estos cuatro puntos es alcanzable sin la 11-B **y sin ejecución humana**:

- [ ] Despliegue real sirviendo la aplicación por **HTTPS**
- [ ] **Restauración de un backup ejecutada de verdad, con el tiempo anotado** — un backup no probado no existe
- [ ] **Alarma de caída recibida** al simular una caída
- [ ] **Email de verificación llegado a una bandeja real** — no basta con que el log diga «enviado»

## ADR de esta fase

- [[ADR-0006-liveness-y-readiness-separadas]] — Bloque A. Tres endpoints en vez del `/health` único que pedía el prompt.
- [[ADR-0003-staging-como-entorno-estricto]] — Bloque D. `staging` entra en `ENTORNOS_SOPORTADOS` **y** en `ENTORNOS_ESTRICTOS`; si un entorno merece existir en internet, merece secretos propios.
- [[ADR-0007-planificador-celery-separado-del-worker]] — Bloque C′. `beat` deja de ser una bandera del worker y pasa a ser servicio propio (escalar el worker duplicaba los mensajes a cada usuario), y el entorno de `backend`, `worker` y `beat` se define **una sola vez** en un ancla YAML. El mismo bloque añade `backend/.dockerignore` —`backend/Dockerfile:8` es `COPY . .`, de modo que un `.env` presente acabaría en una capa de la imagen, y **borrarlo después no lo elimina**— y el `healthcheck` del backend contra `/api/v1/health`. Las revisiones le añadieron una regla explícita: **en el ancla va lo que necesitan los tres; lo que necesita uno solo va en su bloque** — y con ella el caso ya decidido de que **las claves de Stripe de la Fase 13 no van al ancla**.
- [[ADR-0008-loopback-por-defecto-en-los-puertos-publicados]] — Bloque C′. `backend` y `frontend` pasan a `${BIND_BACKEND:-127.0.0.1}` y `${BIND_FRONTEND:-127.0.0.1}`. **Desviación del alcance aprobado**, que difería esto a la Fase 16: la premisa del diferimiento caducó dentro del propio bloque, al dejar de ser el compose «orquestación local» para convertirse en base de un despliegue portable. Con 8000 en `0.0.0.0`, `/docs` y `/openapi.json` enumeran la API sin autenticar y se puede hablar con uvicorn **saltándose el proxy inverso del Bloque H**.

Los números **0004 y 0005 siguen reservados** para los ADR de los bloques E y H, que aún no se han implementado. Ver [[contador-secuencias]].

## Deuda que deja abierta

- **Sentry (H5), sin fase propietaria.** Ver arriba.
- **Toda la Fase 11-B:** IaC del proveedor, jobs de despliegue, `docs/RUNBOOK.md`, runbooks temáticos del Vault y el ADR de elección de hosting.
- **Requisito operativo para el runbook de 11-B:** la plataforma de hosting debe apuntar su health check a `/api/v1/health`, **nunca** a `/health/listo`. Detalle y motivo en [[ADR-0006-liveness-y-readiness-separadas]].
- **Ampliar `/health/detalle` con un apartado de red** (`par_tcp`, `ip_resuelta`, política de proxies) al ejecutar el Bloque H: es la única forma práctica de verificar **en producción** que la resolución de IP no está mal configurada.
- Las tres deudas heredadas del Bloque I siguen abiertas mientras el bloque no se ejecute. Ver [[PENDIENTES-md|PENDIENTES.md]].

### Deuda nueva registrada por el Bloque C′

Resumen. **El detalle, la evidencia y el propietario de cada una viven en [[PENDIENTES-md|PENDIENTES.md]]**, sección «Deuda abierta por la Fase 11, Bloque C′»; aquí no se copian.

| # | Deuda | Propietario |
|---|---|---|
| 1 | **`worker` y `beat` cargan `ADMIN_PASSWORD` sin usarla.** Es la credencial del `es_superadmin`, que gobierna el conocimiento T2/T3 global, y solo la necesita la siembra del backend. La llevan porque `celery_app.py` invoca `get_settings()` al importarse y sin ella no arrancan en un entorno estricto: cerrarlo exige **desacoplar la guardia**, no basta con quitar la variable del ancla. | Fase 16 |
| 2 | **SMTP solo soporta STARTTLS; el puerto 465 falla en silencio.** Con `SMTP_PUERTO=465` se abre en claro contra un puerto que espera un ClientHello, salta la excepción, `email.py` se la traga y la API sigue respondiendo 200: **el correo no sale y nada lo dice**. Es el mismo fallo mudo que el bloque vino a cerrar, entrando por la puerta del puerto. | Fase 16 o la fase que fije proveedor de correo |
| 3 | **La imagen corre como `root` y sin endurecer**: ni `USER`, ni `read_only`, ni `cap_drop`, ni `no-new-privileges`, ni límites de recursos. El plan lo contemplaba con la condición explícita de anotarlo si no daba tiempo. Queda anotado. | Fase 16 |
| 4 | **`beat` no debe escalarse nunca, y nada en el código lo impide.** Hay test que prohíbe `deploy.replicas > 1` en el fichero, pero ninguno puede impedir un `--scale beat=2` en la línea de órdenes, que devuelve entera la duplicación del digest. Motivo completo en [[ADR-0007-planificador-celery-separado-del-worker]]. | Runbook de la 11-B |
| 5 | **`beat` no persiste su `celerybeat-schedule`.** El `PersistentScheduler` lo escribe en la capa efímera del contenedor: cada recreación lo pierde y una entrada nueva arranca con `last_run_at = now`, de modo que el digest horario vuelve a esperar una hora entera. En una sesión de despliegue con varias recreaciones seguidas, puede no llegar a dispararse. | Runbook de la 11-B |

Esa misma sección de `PENDIENTES.md` recoge además dos entradas de menor calado que el bloque detectó de paso: el **diagnóstico engañoso de un `unhealthy` del backend** (Compose v2 aborta señalando al `frontend`, que es quien esperaba) y la **no-idempotencia de la suite ante un `seis_dev.db` superviviente**, esta última preexistente y sin propietario asignado.

## Relacionado

- Rama: `fase-11-infraestructura`, creada desde `main` (`679fc4d`)
- Plan de ejecución: `docs/FASE_11_PLAN.md` — sustituye a `docs/FASE_11_PLAN_BORRADOR.md`
- Migración Alembic: **ninguna** (H9)
- [[Fase-10-alta-self-service]] — de ella hereda la **puerta de despliegue** (bajo `docker compose` la IP de origen no sobrevive: todo llega con la de la pasarela) y tres deudas del Bloque I
- [[ADR-0002-clave-compuesta-limitador-login]] — su efecto pleno **depende del Bloque H** de esta fase
- [[Plan-Maestro|Plan Maestro]] §Fase 11
- [[PENDIENTES-md|PENDIENTES.md]]
