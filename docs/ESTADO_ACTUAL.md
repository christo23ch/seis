# SEIS — Estado actual del proyecto (auditoría con evidencia)

**Fecha:** 2026-09-08
**Rama auditada:** `main` (`5242cb1`) — ver §0, hay una segunda rama divergente
**Método:** lectura del código + ejecución real de la suite de tests y del build.
Ningún veredicto de este documento procede de la documentación previa: todos se
apoyan en un fichero, una función o la salida de un comando reproducible.

---

## 0 · Hallazgo previo: el repositorio tiene dos líneas de trabajo divergentes

Antes de auditar nada hay que resolver esto, porque condiciona todo lo demás.

| Rama | HEAD | Contenido |
|---|---|---|
| `main` | `5242cb1` | 39 commits. Fases 9, 9.5, 10 y 12 completas + vault de Obsidian |
| `claude/wizardly-wright-nkscpg` | `ba6badc` | 10 commits. Fase 9 + **una segunda implementación de la Fase 10** + Fase 11 (infra) |

Las dos ramas implementaron la Fase 10 **por separado y de forma distinta**. La de
`main` es mejor en al menos un punto de seguridad relevante: ante un email ya
registrado, `main` responde **201 idéntico** (y avisa por correo al titular),
mientras que la rama divergente responde **400**, lo que convierte `/auth/registro`
en un oráculo de enumeración de cuentas.

**Consecuencias operativas:**

1. `main` es la fuente de verdad. Todo el resto de este informe audita `main`.
2. La **Fase 11 (infraestructura de producción) existe, pero solo en la rama
   divergente**: `render.yaml`, `docs/RUNBOOK.md`, `docs/RENDER_DEPLOYMENT.md`,
   `.github/workflows/{ci,deploy-staging,deploy-production}.yml` e integración
   opcional de Sentry **no están en `main`**. Es trabajo hecho y perdido de vista.
3. Fusionar esa rama sin más **regresionaría la seguridad del registro**. Si se
   quiere recuperar la Fase 11, hay que hacer *cherry-pick* selectivo de los
   ficheros de infraestructura, nunca un merge completo.

---

## 1 · Inventario fase por fase

Criterio de veredicto:
- **✅ Implementado y testeado** — hay código y hay tests que lo ejercitan.
- **🟨 Implementado sin tests** — hay código, no hay tests específicos.
- **📋 Solo planificado** — hay documento de plan, no hay código.
- **⬜ Inexistente** — ni código ni plan.

| Fase | Veredicto | Evidencia concreta |
|---|---|---|
| **1-8** · Motor experto + producto mono-tenant | ✅ | `backend/app/engine/modules/m01…m14_informe.py` (14 módulos, 1:1 con la especificación). Tests: `test_golden_caso19.py` (14), `test_precios.py` (9), `test_vetos.py` (7) = **30 tests de regresión del motor** |
| **9** · Multi-tenancy | ✅ | `models.Organizacion`; `Usuario.organizacion_id`, `.rol_org`, `.es_superadmin`; `Analisis.organizacion_id`; `deps.require_superadmin` / `require_propietario`; `analisis_service.listar_analisis`/`obtener_analisis` filtran (L96-97, L122). Tests: `test_multitenant.py` (10) |
| **9.5** · Reparación de migraciones | ✅ | Consolidación a `0005_esquema_base.py` + `0006_self_service.py`; ambas con `downgrade` funcional. Tests: `test_migraciones.py` (13, 1 omitido justificadamente). CI dedicada: `.github/workflows/migraciones.yml`. Docs: `FASE_95_PLAN_EJECUCION.md`, `FASE_95_INFORME_CIERRE.md`, `PLAN_REPARACION_MIGRACIONES.md` |
| **10** · Alta self-service | ✅ | `services/registro_service.py`; `api/auth.py` → `/registro`, `/verificar`, `/reenviar-verificacion`, `/recuperar`, `/resetear`, `/cambiar-password`; `models.TokenConsumido`; `core/rate_limit.py`. Frontend: `/registro`, `/verificar`, `/recuperar`, `/resetear`. Tests: `test_registro.py` (45) + `test_seguridad_arranque.py` (27) = **72** |
| **11** · Infraestructura de producción | ⬜ **en `main`** | No existen `render.yaml`, `RUNBOOK.md`, Sentry ni workflows de CI/deploy. La única CI es `migraciones.yml`. *(El código sí existe en la rama divergente — ver §0)* |
| **12** · Notificaciones multicanal + scoring | ✅ | `models.{Alerta,Notificacion,PreferenciasNotificacion,CodigoTelegram}`; `app/notificadores/{base,email,telegram,registro}.py`; `services/notificaciones_service.py`; `tasks/notificaciones_tasks.py`; `engine/scoring_expres.py::puntuar_subasta`; `api/notificaciones.py` (+`router_alertas`) y `api/captacion.py`. Frontend: `/alertas`, `/subastas`, `/baja`. Tests: `test_notificaciones.py` (18), incluidos aislamiento del matcher entre organizaciones y alerta ajena → 404 |
| **13** · Monetización (Stripe) | 📋 | `docs/FASE_13_PLAN_EJECUCION.md` y `docs/FASE_13_MAPA_IMPACTO_STRIPE.md`. Cero código: `grep -rln "stripe\|Suscripcion" backend/app/` no devuelve nada |
| **14** · RGPD | ⬜ | Sin modelo de consentimiento, sin export, sin borrado de cuenta |
| **15** · Landing / onboarding / ayuda | ⬜ | La raíz `/` sigue bajo `(app)` y protegida por login. No hay `MANUAL_DE_USUARIO.md` |
| **16** · Endurecimiento de seguridad | ⬜ | No existe `docs/AUDITORIA_SEGURIDAD.md`. El rate limiting es solo de auth, no global |
| **17** · Escalado de la captación (BOE real) | ⬜ | **No existe `app/ingesta/` ni conector alguno.** `api/captacion.py` es un `POST` manual: las subastas solo entran si alguien las envía a mano |
| **18** · WhatsApp | ⬜ | Condicional a métricas de la 12 (correcto que no esté) |
| **19** · Analítica y panel | ⬜ | Sin instrumentación ni tabla de feedback |
| **20** · Beta y lanzamiento | ⬜ | — |

### Resultado real de la validación (ejecutado, no supuesto)

```
backend:  161 passed, 1 skipped   (24s)
frontend: npm run build → ✓ compilado, 20 rutas, sin errores de tipos
```

Desglose de los 162 tests recogidos:

| Fichero | Tests | | Fichero | Tests |
|---|---|---|---|---|
| `test_registro.py` | 45 | | `test_precios.py` | 9 |
| `test_seguridad_arranque.py` | 27 | | `test_vetos.py` | 7 |
| `test_notificaciones.py` | 18 | | `test_api.py` | 6 |
| `test_golden_caso19.py` | 14 | | `test_conocimiento.py` | 6 |
| `test_migraciones.py` | 13 | | `test_auth.py` | 5 |
| `test_multitenant.py` | 10 | | `test_pdf_async.py` | 2 |

**Volumen:** backend `app/` 5.289 líneas · backend `tests/` 2.697 líneas (ratio
test:código ≈ 0,51) · frontend 3.292 líneas **con cero tests**.

---

## 2 · Verificación del aislamiento multi-tenant, endpoint por endpoint

La API expone **41 endpoints**. Estos son los que devuelven o crean datos de
análisis, revisados uno a uno:

| Endpoint | ¿Filtra por `organizacion_id`? | Evidencia |
|---|---|---|
| `POST /analisis` | ✅ Sella el tenant | `routes.py:28-29` → `crear_analisis(..., organizacion_id=user.organizacion_id)` |
| `POST /analisis/simular` | ✅ N/A por diseño | No persiste ni lee de BD; ejecuta el motor en memoria |
| `POST /analisis/async` | ✅ Sella el tenant | `routes.py:43-44` → pasa `organizacion_id` a la tarea Celery |
| `GET /analisis` | ✅ | `routes.py:67` → `listar_analisis(..., organizacion_id=...)`; el filtro real está en `analisis_service.py:96-97` |
| `GET /analisis/{id}` | ✅ 404, no 403 | `routes.py:73` + `analisis_service.py:122-123` (devuelve `None` si el tenant no coincide) |
| `GET /analisis/{id}/informe` | ✅ | `routes.py:85` |
| `GET /analisis/{id}/informe.pdf` | ✅ | `routes.py:94` |
| `GET /analisis/{id}/checklist` | ✅ | `routes.py:106` |
| **`GET /tareas/{tarea_id}`** | ❌ **NO FILTRA** | `routes.py:51-62`. Solo exige `get_current_user`. Devuelve `r.result` de Celery sin comprobar de qué organización era la tarea |

### El hallazgo: `GET /tareas/{tarea_id}`

Es el único endpoint que devuelve datos derivados de un análisis sin comprobar el
tenant. `analizar_task` retorna `{"id": analisis_id, "semaforo": ...}`
(`tasks/celery_app.py:35`), de modo que un usuario de la organización A que
conozca un `tarea_id` de la organización B obtiene **el identificador del análisis
ajeno y su semáforo**.

- **Severidad honesta: media-baja.** El `tarea_id` es un UUID4 de Celery: no es
  enumerable ni adivinable, y conocer el `analisis_id` no da acceso al análisis
  (ese endpoint sí filtra y responde 404).
- **Pero rompe el invariante** que el resto del sistema mantiene, y
  `test_multitenant.py` **no tiene ni un solo test sobre `/tareas`**
  (`grep -c "tareas" test_multitenant.py` → 0).
- **Corrección:** comprobar la organización del análisis resultante antes de
  devolver, o registrar el `organizacion_id` junto al `tarea_id`.

### Riesgo latente: el filtro es *fail-open*

`analisis_service.py:96` y `:122` filtran solo `if organizacion_id is not None`.
`Usuario.organizacion_id` es **nullable** (`models.py:242`) y
`usuario_service.crear_usuario` lo acepta como `None`. Un usuario sin
organización **vería todos los análisis de todas las organizaciones**.

Hoy **no es explotable**: las dos vías de alta asignan siempre organización
(`api/auth.py:227` usa la del admin como respaldo; `scripts/init_db.py:36-38`
crea la organización por defecto). Pero la postura defensiva es la contraria a la
deseable: ante la duda, debería no devolver nada en vez de devolverlo todo.

### Correcto por diseño (no es un fallo)

`GET /captacion` no filtra por organización: las subastas captadas son un corpus
**compartido** entre tenants (CLAUDE.md §4). Matiz a tener presente: `datos_brutos`
guarda el payload íntegro de quien la captó, y es visible para todos.

Las alertas y notificaciones son privadas **por usuario** (no por organización) y
lo cumplen: `notificaciones.py:135-139` (`_alerta_propia` → 404 si es ajena), con
test `test_alerta_ajena_devuelve_404`.

---

## 3 · Deuda técnica

### 3.1 Vulnerabilidades de dependencias — lo más urgente

`npm audit --omit=dev` → **4 vulnerabilidades en dependencias de producción
(1 crítica, 3 altas)**; 5 contando desarrollo.

| Paquete | Severidad | Impacto destacado |
|---|---|---|
| **next 15.1.6** | 🔴 **CRÍTICA** | 31 advisories, entre ellos *Authorization Bypass in Middleware* (GHSA-f82v-jwr5-mffw), *RCE in React flight protocol* (GHSA-9qr9-h5gf-34mp), varios SSRF y envenenamiento de caché |
| `postcss` | Alta | Path traversal / lectura arbitraria de `.map` vía `sourceMappingURL` |
| `sharp` (<0.35) | Alta | CVEs heredadas de libvips |
| `browserslist` | Alta | Crecimiento de memoria sin límite → OOM |

**El arreglo es barato:** `next@15.5.25` resuelve las cuatro y **no es un salto
semver-mayor**. Es trabajo de sandbox, sin máquina local.

Backend: `pip-audit` → **limpio**. El único aviso (`setuptools` PYSEC-2026-3447)
es del entorno virtual, no de una dependencia declarada en `requirements.txt`.

### 3.2 Ausencias en calidad de frontend

- **Cero tests de frontend.** 3.292 líneas de TypeScript/TSX sin una sola prueba.
  `package.json` solo declara `dev`, `build`, `start`.
- **Cero linting.** No existe ninguna configuración de ESLint, y además
  `next.config.mjs` fija `eslint: { ignoreDuringBuilds: true }`. Lo único que
  protege el frontend hoy es el chequeo de tipos que hace `next build`.

### 3.3 Cobertura de CI insuficiente

La única CI es `.github/workflows/migraciones.yml`, que ejecuta **solo**
`test_migraciones.py` (13 tests). **Los otros 149 tests y el build del frontend no
se ejecutan en ninguna CI.** La red de seguridad existe, pero no está enchufada.

### 3.4 Tests omitidos

Uno, y **está bien justificado** (no es deuda oculta):
`test_migraciones.py:630` — requiere un PostgreSQL real vía
`SEIS_TEST_POSTGRES_URL`; el propio mensaje documenta que se ejecutó y pasó contra
`postgis/postgis:16-3.4`. Recomendación: levantarlo como *service container* en CI
para que deje de depender de una ejecución manual.

### 3.5 TODOs, código muerto y migraciones

- **TODO/FIXME/HACK: cero** en `backend/app`, `frontend/app`, `frontend/lib`,
  `frontend/components`. Limpio de verdad.
- **Código muerto:** `models.py:327` — `UniqueConstraint  # noqa` es una sentencia
  sin efecto, solo para silenciar el linter por un import sin uso. Anecdótico.
- **Migraciones:** las dos tienen `downgrade` funcional, y las 22 tablas de los
  modelos están cubiertas (21 en `0005`, `token_consumido` en `0006`). Sin deriva
  entre modelos y esquema.

### 3.6 Deuda heredada declarada por el propio proyecto

`docs/PENDIENTES.md` deja dos asuntos abiertos de la Fase 10, que confirmo que
siguen sin resolver: **la IP de origen bajo Docker** (el rate limiting puede estar
viendo la IP del proxy en vez de la del cliente) y **la purga de `token_consumido`**
(la tabla crece sin límite: no hay tarea que elimine los tokens caducados).

---

## 4 · Discrepancias con el brief que me diste

Me pediste que te corrigiera en vez de adaptarme. Tres puntos:

1. **shadcn/ui: no se usa.** `frontend/package.json` no tiene ni shadcn ni Radix.
   Toda la UI es artesanal y vive en **un único fichero**,
   `frontend/components/ui.tsx`. Es un dato central para el trabajo de diseño que
   quieres abordar.
2. **PostGIS está aprovisionado pero no se usa.** `docker-compose.yml` levanta
   `postgis/postgis:16-3.4`, pero el esquema guarda `lat`/`lng` como
   `Numeric(9,6)` (`models.py:74-75`); el propio fichero lo documenta como
   migración pendiente. No hay ninguna columna `geometry` ni consulta espacial.
3. **El vault de Obsidian sí existe y está en el repositorio**, no perdido: vive
   en la **raíz** (`.obsidian/` + `01-Home`, `30-Decisiones`, `900-Plantillas`…),
   con **38 notas**, **15 plantillas** (incluida `Plantilla-ADR.md`) y 2 ADRs ya
   escritos. Ya hay incluso una nota `999-Meta/Integracion-con-Git.md`. Cualquier
   propuesta de flujo debe partir de lo que ya está montado, no reinventarlo.

---

## 5 · Estimación honesta de avance

**~60 % del código · ~50 % del camino hasta el primer cliente de pago.**

A favor (lo que está sólido):
- El motor determinista M01-M14 está completo y blindado con 30 tests de regresión.
- Multi-tenancy correcto en todos los endpoints de análisis salvo uno.
- Fases 9, 9.5, 10 y 12 realmente terminadas y probadas: 162 tests, ratio
  test:código de 0,51 en backend, y disciplina real de migraciones.

En contra (por qué no es más):
- **El producto todavía no puede cumplir su promesa central.** Vende «te avisamos
  de las subastas que encajan contigo», pero **no hay ingesta automática**: sin el
  conector BOE (Fase 17, ni empezada), las subastas solo entran si alguien las
  teclea. Las alertas funcionan; lo que falta es el caudal de subastas que alertar.
- **No hay nada desplegado.** Sin Fase 11 en `main`: sin CI real, sin runbook, sin
  IaC, sin monitorización.
- **No se puede cobrar.** Fase 13 solo en papel, y depende de trámites lentos
  (figura fiscal) que no dependen del código.
- **Sin cobertura legal.** Fase 14 sin empezar: hoy no se puede operar con datos
  de usuarios reales en la UE con garantías.
- El frontend, que es lo que ve el cliente, es la parte menos protegida: sin tests,
  sin lint y con una CVE crítica.

Las fases que quedan (11, 13, 14, 15, 16, 17, 19, 20) concentran justamente el
trabajo que **no es solo código**: pagos, legal, despliegue y ajuste empírico
contra un portal real.
