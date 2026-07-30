# Plan de ejecución — Fase 11 · Infraestructura de producción

**Rama:** `fase-11-infraestructura`, desde `main` (679fc4d)
**Migración Alembic:** ninguna (D0)
**Contrato:** `docs/SEIS_Plan_Maestro_Fases_920.md` §Fase 11
**Estado:** ✅ **APROBADO** por el responsable del proyecto el 2026-07-30. Alcance autorizado: **Fase 11-A** (bloques H, E, A, D, C′, F′, I). La Fase 11-B no comienza hasta el cierre completo de la 11-A.
**Sustituye a:** `docs/FASE_11_PLAN_BORRADOR.md` (se retira al aprobarse este)

> **Línea base oficial de la suite, fijada por el responsable:**
> **162 recogidos · 159 pasan · 2 fallan (PDF preexistentes) · 1 omitido.**
> Es la única cifra que puede citarse en documentación y auditorías. Las
> anteriores (118, 104) quedan derogadas.

---

## 1 · Resolución de los bloqueos H0-H10

| # | Bloqueo | Resolución |
|---|---|---|
| **H0** | ¿Fusionar Fase 10 a `main` o ramificar desde `fase-10`? | ✅ **Cerrado definitivamente.** Premisa refutada con evidencia: `git merge-base --is-ancestor fase-10-alta-self-service main` → exit 0; `main` = 679fc4d «Merge pull request: Fase 10». La Fase 10 **y** el Vault de Obsidian están fusionados en `main`. La rama `fase-10-alta-self-service` **queda cerrada**. **Toda rama nueva se crea desde `main`.** |
| **H1** | Proveedor de hosting | **Diferido por decisión del responsable.** Análisis de costes entregado (Railway ~$25/mes · Render ~$45 · Hetzner+Coolify ~€11). **No se implementa IaC específica de ningún proveedor.** Toda la infraestructura se diseña **agnóstica**: variables de entorno y documentación portable. |
| **H2** | Dominio y subdominios | **Diferido.** No existe dominio definitivo. **Prohibido codificar dominios a fuego.** Todo se parametriza vía `FRONTEND_URL`, `API_URL`, `NEXT_PUBLIC_API_URL` y `SEIS_CORS_ORIGINS`. |
| **H3** | Presupuesto | **Diferido.** **No se toma ninguna decisión condicionada por el coste** (deroga la parte de D3 que hacía depender del presupuesto la estrategia de staging). |
| **H4** | ¿Frontend en Vercel? | ✅ **Mismo proveedor** que el backend. |
| **H5** | Sentry | **Fuera de esta fase.** Cero dependencias, cero código. Huella única: `SENTRY_DSN=""` declarada y documentada como pendiente. Incumple deliberadamente el requisito 2 del prompt del Plan Maestro; **se documenta sin maquillar**. |
| **H6** | Proveedor de email | **Diferido.** No se integra ningún proveedor. Toda la configuración por variables de entorno; se propagan igualmente las 7 de SES/SMTP que hoy faltan. |
| **H7** | *(a)* `SEIS_ENV=staging` · *(b)* Celery beat | ✅ *(a)* **Sí, y estricto**: entra en `ENTORNOS_SOPORTADOS` **y** en `ENTORNOS_ESTRICTOS`. *(b)* **Beat separado del worker** — se aplica también en `docker-compose.yml`, no sólo en la IaC futura (ver Bloque C′). |
| **H8** | Aprobación del deploy | ✅ **El aprobador es el responsable del proyecto.** Despliegue manual por `workflow_dispatch`. Se materializa en 11-B. |
| **H9** | Numeración de migración | ✅ **Esta fase NO lleva migraciones. No se crea la `0007`.** Si apareciera necesidad de tocar el esquema: **detención inmediata y solicitud de autorización.** |
| **H10** | Downtime | ✅ **Corte aceptado en el primer despliegue.** A partir de ahí, **todas** las migraciones deberán ser retrocompatibles. |
| **CF** | Cloudflare | ✅ **El Bloque H se diseña con Cloudflare desde el inicio.** No confiar únicamente en `X-Forwarded-For`. La solución debe funcionar correctamente tras Cloudflare **y** tras un proxy inverso genérico. |

---

## 2 · Consecuencia: la fase se parte en 11-A y 11-B

Con H1, H2 y H6 diferidos no se puede escribir la IaC, ni los jobs de deploy, ni un
RUNBOOK que no sea ficción. Pero **cinco bloques son íntegramente agnósticos del
proveedor** y contienen lo más valioso de la fase, incluida la puerta de despliegue
que hoy impide exponer el producto a Internet.

- **Fase 11-A — repositorio, agnóstica.** Ejecutable ya. Un PR.
- **Fase 11-B — dependiente del proveedor.** Bloqueada hasta H1/H2/H6. Otro PR.

**La Fase 11 no se declara cerrada al fusionar 11-A.** Sus criterios de salida son
operativos (despliegue real, backup restaurado con tiempo medido, email llegado a
una bandeja real) y ninguno es alcanzable sin 11-B.

---

## 3 · Alcance de la Fase 11-A

### Bloque A — Salud por componente · *riesgo bajo*

Tres endpoints, no uno (**D2**): el health de una plataforma se ejecuta cada pocos
segundos por réplica; si toca la BD, una base lenta provoca que la plataforma mate y
reinicie los procesos, **convirtiendo una degradación en una caída total**.

| Fichero | Acción |
|---|---|
| `backend/app/api/salud.py` *(nuevo)* | `/health/listo` (readiness): `SELECT 1` + `PING` de Redis con timeout; **503** si algo falla, cuerpo `{"estado","componentes"}`. `/health/detalle`: `Depends(require_superadmin)`, añade revisión de Alembic, versiones T2/T3, entorno y latencias. **Nunca** se devuelve el texto de la excepción (puede contener la cadena de conexión). |
| `backend/app/api/routes.py` | **Sin cambios en `health()` (líneas 20-22).** Es la sonda de liveness y sigue siendo O(1). |
| `backend/app/main.py` | Registrar el router (octavo, tras `alertas_router`). |
| `backend/app/core/config.py` | `+ health_timeout_segundos: float = 2.0`. |
| `backend/tests/test_salud.py` *(nuevo)* | `/health` 200 sin BD · `/health/listo` 200 todo arriba · **503** con Redis caído · 503 con BD caída · `/health/detalle` 401 sin token y 403 sin superadmin · **test negativo: el cuerpo de error no contiene la cadena de conexión ni fragmentos de la excepción.** |

### Bloque C′ — Higiene de despliegue portable · *riesgo bajo*

| Fichero | Acción |
|---|---|
| `backend/.dockerignore` *(nuevo)* | `.venv/`, `__pycache__/`, `*.db`, `.pytest_cache/`, `.env`, `htmlcov/`… **`backend/Dockerfile:8` es `COPY . .`**: hoy mete el venv en la imagen y **metería un `.env` si existiera**. Es tamaño de build y filtración de secretos al registry. |
| `docker-compose.yml` | (a) propagar `SES_REGION`, `SES_ACCESS_KEY`, `SES_SECRET_KEY`, `SMTP_HOST`, `SMTP_PUERTO`, `SMTP_USUARIO`, `SMTP_PASSWORD` a `backend` **y** a `worker` — cierra `PENDIENTES.md:318-326`; (b) retirar `version: "3.9"` (obsoleto). **No** se toca la publicación de puertos: es Fase 16. |
| `.env.produccion.example` *(nuevo)* | Inventario completo de variables de un despliegue real, **todas vacías**. Incluye las 7 de SES/SMTP y `SENTRY_DSN` con comentario explícito de que **aún no tiene consumidor** (H5 diferido). |
| `.env.example` | Añadir las 7 de SES/SMTP, manteniendo el tono existente. |

### Bloque D — `staging` como cuarto entorno estricto · *riesgo medio* — **TDD**

`config.py:88` hoy hace que `SEIS_ENV=staging` **aborte el arranque**. Meterlo sólo en
`ENTORNOS_SOPORTADOS` sería peor que no meterlo: crearía un entorno público en
internet **sin validación de secretos**, justo el agujero que cerró la Fase 12.
Staging es internet, e internet es producción a efectos de secretos.

| Fichero | Acción |
|---|---|
| `backend/app/core/config.py` | `ENTORNOS_SOPORTADOS += "staging"` y `ENTORNOS_ESTRICTOS += "staging"`. **Sin tocar** `_motivo_inseguro` ni `_MARCADORES_PLANTILLA`. |
| `backend/tests/test_seguridad_arranque.py` | Tests **primero**: staging + secreto débil ⇒ aborta · staging + secretos fuertes ⇒ arranca · `SEIS_ENV=stagging` (errata) ⇒ sigue abortando. **Los 27 tests existentes no se modifican.** |

### Bloque H — La puerta de despliegue: IP real tras proxy · *riesgo medio* — **TDD**

Cierra la deuda 1 de la Fase 10 (`PENDIENTES.md:95-107`), la que hoy **bloquea la
exposición del producto a Internet**. La costura ya existe y está documentada:
`backend/app/api/auth.py:116` (`_ip()`).

| Fichero | Acción |
|---|---|
| `backend/app/core/config.py` | `+ proxies_de_confianza: str = ""` — **vacío por defecto**. |
| `backend/app/api/auth.py` (o helper propio) | `_ip()` pasa a leer `X-Forwarded-For` **sólo** si hay proxies de confianza configurados. Vacío ⇒ `request.client.host`, y **jamás** se confía en una cabecera. Fallar en cerrado, como `config.py`. |
| `docker-compose.yml` | `uvicorn --proxy-headers --forwarded-allow-ips=...` sólo donde haya proxy real declarado. |
| `backend/tests/test_registro.py` | **Test capital: sin proxies de confianza, un `X-Forwarded-For` falsificado NO permite eludir el bloqueo por fuerza bruta.** Si se confiara a ciegas, el anti-fuerza-bruta de la Fase 10 pasaría de existir a ser decorativo: basta enviar una IP distinta en cada intento. |

**Decisión nueva que este plan añade (no estaba en el borrador): Cloudflare.** El paso 1
del Plan Maestro pone el dominio tras Cloudflare. Con el proxy activo, la IP real llega
en `CF-Connecting-IP` y `X-Forwarded-For` arrastra además las IPs de Cloudflare, de modo
que **leer el primer valor de XFF nos devuelve al mismo agujero**. Se resuelve en el ADR
correspondiente eligiendo explícitamente entre declarar los rangos de Cloudflare como
confianza o leer `CF-Connecting-IP`. Queda parametrizado; el valor concreto es 11-B.

### Bloque E — `create_all` fuera de la ruta de producción · *riesgo ALTO* ⚠️

`scripts/init_db.py:10` ejecuta `Base.metadata.create_all(engine)` y
`docker-compose.yml` lo encadena **después** de `alembic upgrade head`. Es el
antipatrón que **CLAUDE.md §6.9 prohíbe** en `alembic/versions/`, trasladado a la ruta
de arranque: si un modelo declara una tabla que ninguna migración crea, `create_all`
**la crea en silencio en producción**, y la deriva de esquema que el test T4 existe
para detectar queda enmascarada justo donde más caro sale.

| Fichero | Acción |
|---|---|
| `backend/scripts/init_db.py` | `create_all` condicionado a `seis_env in ("development","test")`, con comentario que cite §6.9. |
| `backend/scripts/sembrar.py` *(nuevo)* | Extrae la siembra (líneas 13-40: perfiles, reglas, parámetros, fuentes, admin bootstrap). `init_db.py` delega en él para desarrollo. En staging/producción se invoca **a mano, una vez**, no en cada deploy: un superadmin creándose en cada arranque es superficie que no debe existir por defecto. |
| `docker-compose.yml` | Ajustar el `command` del backend sin romper el flujo local de `MANUAL_DE_PRUEBAS.md`. |
| `backend/tests/test_migraciones.py` | **No se modifica su lógica.** Se exige que **T4 siga verde**: es la prueba de que retirar `create_all` no deja ningún hueco de esquema. |

> **Este bloque puede impedir que el producto arranque de cero** — exactamente el defecto
> que originó la Fase 9.5. Va **en su propio commit**, el último, para que un `git revert`
> limpio sea posible. **Verificación innegociable:** `docker compose down -v && docker
> compose up -d --build` sobre volumen destruido ⇒ `/api/v1/health` en 200.

### Bloque F′ — CI: la suite completa antes que nada · *riesgo bajo*

Hoy la CI ejecuta **1 de 14 ficheros de test** (`migraciones.yml:62`), por los 2 rojos de
PDF. Añadir jobs de deploy sobre eso sería automatizar la propagación de regresiones.

| Fichero | Acción |
|---|---|
| `.github/workflows/ci.yml` *(nuevo)* | Job `suite`: `apt-get install -y fonts-dejavu-core` + `pytest` completo. Job `frontend`: `npm ci && npm run build`. `permissions: contents: read`. |
| `.github/workflows/migraciones.yml` | Sin cambios funcionales: no se toca la barrera de la Fase 9.5. |

**Hipótesis a medir, no a asumir:** que instalar `fonts-dejavu-core` resuelve los 2 rojos
(`backend/Dockerfile:3-4` ya la instala y en Docker no se manifiestan). **Si persisten:**
no se marcan `xfail` para dejar el pipeline verde — se excluyen **por nombre, con
comentario que cite la deuda**, y la corrección de `pdf_service.py` se escala como
decisión aparte. Una exclusión nominal es honesta; un `xfail` genérico esconde.

### Bloque I — Deudas heredadas con propietario «Fase 11» · *riesgo bajo-medio*

Tres deudas que `PENDIENTES.md` asigna nominalmente a esta fase. No incluirlas dejaría
la fase sin cumplir su propio contrato.

| Deuda | Acción |
|---|---|
| **7** — el limitador no reintenta Redis (`PENDIENTES.md:139-144`) | `_cliente_redis` se cachea como `False` al primer fallo y **no se reintenta en toda la vida del proceso**: una caída de Redis degrada a memoria de forma silenciosa y permanente, y con `--workers 2` eso duplica el límite efectivo. Se añade reintento con backoff. |
| **2** — `token_consumido` crece sin purga (`:108-111`) | Tarea beat `seis.purgar` que borra los `jti` anteriores al TTL máximo (30 días cubre los tres propósitos vigentes). |
| **10** — cuentas nunca verificadas no caducan (`:154-156`) | **Requiere una decisión de diseño que surfaceo aquí:** un usuario sin verificar es propietario de una `Organizacion`; borrarlo deja la organización huérfana. Propuesta: purgar usuario **y** organización sólo si la org no tiene otros miembros ni ningún `Analisis`. Si en implementación se complica, **se difiere con nota explícita** en vez de improvisar un borrado destructivo. |

### Bloque G′ — Documentación de lo que sí se ha hecho · *riesgo bajo*

Sin `docs/RUNBOOK.md` (es 11-B: no se puede escribir un runbook de un proveedor sin elegir).

| Fichero | Acción |
|---|---|
| `40-Fases/Fase-11-infraestructura.md` *(nuevo)* | Nota de fase con `900-Plantillas/Plantilla-Fase.md`. Estado: **en curso**, no cerrado. |
| `30-Decisiones/ADR/ADR-0003…ADR-0006` *(nuevos)* | Con `Plantilla-ADR.md`, continuando desde ADR-0002: **0003** staging como entorno estricto (D1) · **0004** `create_all` fuera de producción (D8) · **0005** confianza en `X-Forwarded-For` sólo tras proxy declarado, incluida la arruga de Cloudflare (D10) · **0006** liveness ≠ readiness (D2). |
| `docs/PENDIENTES.md` | Cerrar las deudas absorbidas; **abrir** las que esta fase deja: Sentry sin propietario (H5), IaC/RUNBOOK/deploy (11-B), y la deuda 10 si se difiere. |
| `CHANGELOG.md` | Entrada `## [Fase 11-A]`, formato ya establecido. |
| `CLAUDE.md` | §3 sección de estado · §5 tabla · §2 «no confirmado» sigue sin hosting. **Regla del proyecto: ninguna afirmación no medida.** |
| `docs/FASE_11_PLAN_BORRADOR.md` | Se retira (sustituido por este). |

---

## 4 · Lo que queda en la Fase 11-B (bloqueado)

IaC del proveedor (5 servicios, secretos por referencia con `sync: false`, beat aislado
con `replicas: 1` como invariante, migraciones fuera del arranque del proceso web) ·
jobs de deploy (staging automático desde `main`, producción con Environment + disparo
manual) · `docs/RUNBOOK.md` completo · runbooks temáticos del Vault ·
`MANUAL_DE_PRUEBAS.md` §5 «Opción D» (hoy desactualizado: dice que «Redis/Celery son
opcionales», falso desde la Fase 12) · ADR de elección de hosting · ADR de migraciones
fuera del arranque · el gotcha de `NEXT_PUBLIC_API_URL` fijado en build-time
(D11: **la imagen validada en staging no es byte a byte la que va a producción**).

---

## 5 · Verificación de la Fase 11-A

**Línea base medida hoy (2026-07-30):** `162 recogidos · 159 pasan · 2 fallan · 1 se omite`
en 76 s. Los 2 rojos son los preexistentes de PDF/DejaVu; el omitido es T5. Las cifras
118 (`CLAUDE.md:83`) y 104 (`PENDIENTES.md:333`) son fotos de fases anteriores.

**Automática:**
1. `pytest -q` — suite completa; **se recuenta y se reporta el resultado real**, nunca de memoria.
2. `pytest tests/test_migraciones.py -v` — **T4 obligatoriamente verde** tras el Bloque E.
3. `pytest tests/test_salud.py tests/test_seguridad_arranque.py tests/test_registro.py -v`.
4. `cd frontend && npm run build` limpio.

**Manual con Docker (obligatoria, no opcional):**
5. `docker compose down -v && docker compose up -d --build` ⇒ `/api/v1/health` **200**.
6. `curl .../health/listo` ⇒ 200, componentes en `ok`.
7. `docker compose stop redis && curl -i .../health/listo` ⇒ **503**, `redis: "error"`, **sin fuga del texto de la excepción**.
8. `docker run --rm <imagen-backend> ls -la /srv/seis` ⇒ **sin `.venv`, sin `.env`**.
9. `SEIS_ENV=staging` + secreto débil ⇒ arranque abortado con mensaje en español.
10. `SEIS_ENV=staging` + secretos fuertes ⇒ arranca.
11. Ejecutar `100-Operacion/Runbooks/runbook-verificar-migracion-alembic-en-postgresql-real.md`: aunque esta fase no añada migración, valida que el Bloque E no rompió el ciclo `upgrade`/`downgrade`.

---

## 6 · Orden de trabajo y commits

Un commit por bloque, conventional commits en español, prefijo `(fase-11)`, **sin coautoría de IA**.

1. **A** — health *(agente: tdd-guide → code-reviewer)*
2. **C′** — higiene de despliegue *(code-reviewer)*
3. **D** — staging estricto *(tdd-guide → code-reviewer)*
4. **I** — deudas heredadas *(tdd-guide → code-reviewer)*
5. **F′** — CI con suite completa *(build-error-resolver si falla)*
6. **H** — IP tras proxy *(tdd-guide → security-reviewer)*
7. **E** — `create_all` fuera de producción ⚠️ *(tdd-guide → code-reviewer; commit aislado, el último)*
8. **G′** — documentación *(doc-updater)*
9. **security-reviewer sobre el conjunto — obligatorio antes del PR.** Esta fase toca secretos, superficie pública, cabeceras de proxy y la ruta de arranque.

---

## 7 · Criterios de salida

**De la Fase 11-A (este PR):**
- [ ] `/api/v1/health` intacto; `/health/listo` da 503 con un componente caído; `/health/detalle` exige superadmin y no filtra excepciones
- [ ] `backend/.dockerignore` existe; la imagen no contiene `.venv` ni `.env`
- [ ] Las 7 variables SES/SMTP propagadas (`PENDIENTES.md:318-326` cerrada)
- [ ] `SEIS_ENV=staging` soportado **y estricto**, con tests negativos
- [ ] `X-Forwarded-For` falsificado **no** elude el anti-fuerza-bruta, con test que lo demuestra
- [ ] `create_all` fuera de la ruta de producción, con **T4 verde**
- [ ] `docker compose down -v && up -d --build` ⇒ `/api/v1/health` 200
- [ ] CI ejecuta la suite completa + `npm run build`
- [ ] Suite y build reportados con cifras **medidas**, no citadas
- [ ] Vault (nota de fase + 4 ADRs), `CLAUDE.md`, `PENDIENTES.md`, `CHANGELOG.md` actualizados
- [ ] Ninguna afirmación no medida en la documentación de cierre
- [ ] PR único revisado por el humano

**De la Fase 11 completa (siguen abiertos, requieren 11-B y ejecución humana):**
- [ ] `https://app.<dominio>` sirve el login con HTTPS
- [ ] Staging desplegado y deploy automático desde `main`
- [ ] **Restauración de un backup ejecutada de verdad, con el tiempo anotado** — un backup no probado no existe
- [ ] Alarma recibida al simular una caída
- [ ] **Email de verificación llegado a una bandeja real** — no basta con que el log diga «enviado»
