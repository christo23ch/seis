# SEIS — Estado actual del proyecto

> **Este documento es el índice de estado del proyecto.** Ninguna fase cierra su PR sin
> actualizar la tabla de «Frentes abiertos» de abajo. Nació como auditoría puntual el
> 2026-09-08; se quedó como índice porque en esa auditoría aparecieron **tres líneas de
> trabajo que ninguna sesión sabía que existían**, y la causa no fue mala suerte: no había
> ningún documento que dijera qué ramas y qué PRs estaban vivos.

---

## Frentes abiertos

**Actualizado:** 2026-10-07 · **Rama de trabajo:** `fase/5j-2b-deposito-y-plazo` (sale de `main`, `1be0c31`, con la 5J-2a fusionada; sin PR) · **Suite (SQLite):** 1149 passed, 18 skipped, 0 failed · **Frontend:** 143 tests unitarios (vitest, `npm test`) · **E2E:** alta, simulaciones, alta de inversión, validación guiada, datos del procedimiento y presentación (1440 y 390 px) en la CI (job `e2e`), 168 comprobaciones · **Migraciones:** hasta `0016`; la siguiente libre es la `0017`
**Última fase cerrada:** 5J-2a, textos legibles y operandos de «Ver cálculo» (PR #34) · **En curso:** 5J-2b, depósito, táctica de puja y plazo reales (ADR-0024, ADR-0025, ADR-0026), que **cambia cifras** con la tabla antes/después aprobada · **Siguiente:** lo que queda del diseño B (reglas que usen los umbrales de aprobación) · **Puerta: ABIERTA**

### 🟡 Requisito de PRODUCTO registrado, sin implementar: perfil de inversor por cuestionario

Pedido por el usuario en la prueba manual del alta (2026-10-06). **No se implementa todavía:** se
diseñará junto con la rentabilidad del ICO (auditoría, punto E8). Nota del Vault:
[[feat-perfil-inversor-cuestionario]].

- Una pestaña de usuario con preguntas sobre cómo afronta las inversiones, el capital
  disponible y el riesgo que asume, que **determinan el perfil recomendado**.
- Ese perfil fija cómo se ajusta una inversión al usuario: **la misma inversión al mismo precio
  puede puntuar distinto para dos perfiles**.
- En «Datos generales» del alta aparece el **perfil recomendado, con opción de cambiarlo**.
- El informe puede incluir **los perfiles que conviene simular** para la subasta analizada.

### Estado a 2026-09-30

**Dónde está el trabajo.** Todo lo posterior a `main` vive en la rama
`checkpoint/5f6-simulaciones-informes`, publicada en `origin`, **sin PR y sin fusionar**:
`4a6f61d` (líneas de producto 1-4 y 5C-5F.6, un solo commit) y los doce commits de la 5F.7
(`9db8e70` … `4df5de8` y el de documentación que acompaña a este texto). `main` local está en
`90fab7b`, un commit de docs de la 17-C por delante de `origin/main` (`f97f620`) y sin
publicar. Para el hash vigente, `git log --oneline -1`.

**Flujo del producto, de punta a punta, tal como está hoy en el código:**

1. **Captación.** Una subasta entra por `POST /subastas` (alta manual con scoring exprés) o por
   el conector BOE de la 17-A (`app/ingesta/boe.py`), que existe pero **no está ajustado** al
   HTML real del portal (17-B).
2. **Análisis.** Desde `/subastas`, «Analizar» abre `nueva?subasta=` y `POST
   /analisis?subasta_id=…` reutiliza la subasta captada (Fase 1 de la línea de producto). El
   motor M01-M14 corre una vez; se congelan los comparables usados (`ComparableUsado`), el
   detalle de la valoración (`ComparableValorado`, `ValoracionAjustes`) y el árbol de
   parámetros efectivo (`Analisis.parametros_aplicados`). Sin comparables, el semáforo sale
   **rojo** por falta de ancla de mercado (Fase 2).
3. **Detalle.** `/app/inversiones/{id}` con ocho pestañas: Resumen, Riesgos, Estrategia de
   puja, Checklist, **Simulaciones**, **Vista previa (no oficial)**, **Informes oficiales** y
   Datos de entrada. Un aviso encima dice siempre qué configuración se está mostrando.
4. **Simular.** En «Simulaciones», «Nueva simulación» abre el editor de parámetros; «Crear
   simulación» ejecuta el motor con esos cambios y guarda una simulación **pendiente**. Se
   puede comparar con el original, **validar** (pasa a ser la configuración en uso),
   **descartar**, volver a usar una validada, o volver a la configuración original.
5. **Emitir.** En «Informes oficiales», «Emitir informe oficial» congela la configuración en
   uso en un informe **inmutable**, con su PDF. El histórico conserva todos.
6. **Permisos.** El rol lector ve todo y no ve ningún botón de escritura; el backend responde
   403 si lo intenta. Recurso de otra organización u otro análisis: 404.

**Pruebas e2e, cómo lanzarlas:**

| Suite | Linux / CI | Windows (Git Bash) |
|---|---|---|
| Simulaciones e informes (`e2e/correr_simulaciones.sh`) | `bash e2e/correr_simulaciones.sh` | `CHROMIUM_PATH="C:/Program Files/Google/Chrome/Application/chrome.exe" bash e2e/correr_simulaciones.sh` |
| Alta real (`e2e/correr.sh`) | `bash e2e/correr.sh` | `CHROMIUM_PATH="C:/Program Files/Google/Chrome/Application/chrome.exe" bash e2e/correr.sh` |

Desde la 5I, `correr_simulaciones.sh` ejecuta además `frontend/e2e/nueva-inversion.mjs` (alta de
una inversión por el formulario con solo los obligatorios) y `frontend/e2e/validacion-alta.mjs`
(validación guiada), sobre la misma pila. Los tests unitarios del frontend: `cd frontend && npm
test`.

Los dos lanzadores siguen el mismo patrón desde 5G.4-C: puertos propios (8010/3010 simulaciones,
8020/3020 alta), una base SQLite en un temporal fuera del repo, compilan el frontend en
`frontend/.next` contra su propio backend y matan sus propios procesos al terminar. **No
lanzarlos con un `next dev` en marcha sobre ese `.next`.** Variables: `PUERTO_API`,
`PUERTO_WEB`, `PY`, `CHROMIUM_PATH` (o `PLAYWRIGHT_CHROMIUM`, por compatibilidad),
`E2E_SIN_BUILD=1`, `E2E_CONSERVAR=1`. La CI los ejecuta en el job `e2e`.

**Suite de backend:** `cd backend && python -m pytest -q`. Usa su propia base en un
directorio temporal (`conftest.py`) y **no toca `seis_dev.db`**.

> **Este encabezado ya no lleva el hash de `main`, y es a propósito.** Un índice no puede
> describir su propia fusión: la línea que dice «`main` está en X» se escribe *antes* del commit
> de fusión, así que **siempre nace desfasada en un commit**. Ya pasó: esta tabla llegó a
> declarar dos PR «sin fusionar» estando ya en `main`. Para saber dónde está `main`,
> `git log --oneline -1`; este documento responde **qué queda por hacer**, que es la pregunta
> que una imagen del hash no contesta. Variante del punto 6 del [[ADR-0014]]: cada herramienta
> a su pregunta.

**Ningún PR abierto** (comprobado el 2026-09-13; [VERIFICAR: que siga sin haber PR abiertos
hoy — esta sesión no consultó GitHub]). Lo trabajado hasta el 2026-09-13 está fusionado en
`main`; lo posterior, en la rama de arriba.

> El remoto conserva ~28 ramas de fases ya cerradas. **Son historia, no trabajo pendiente**: un
> `git branch -r` no distingue una cosa de la otra, así que la lista de arriba es la que manda y
> una rama que no aparezca aquí está fusionada.

Frente de código abierto: la rama `checkpoint/5f6-simulaciones-informes`, pendiente de PR.

### ✅ Cerrado: el puente captación → análisis

**Resuelto por la Fase 1 de la línea de producto** (commit `4a6f61d`): `POST
/analisis?subasta_id=…` reutiliza la subasta captada y la interfaz la abre desde `/subastas`.
Lo que sigue es el registro original del frente.

**No existía.** `analisis_service.crear_analisis` **crea su propia fila `Subasta`**
a partir del `AnalisisInput`; no reutiliza ninguna captada. `POST /subastas`
(captación, con su scoring exprés) y `POST /analisis` (motor M01-M14) son dos
caminos que no se hablan.

**Consecuencia, y por eso es prioritario: BLOQUEA LA 17-B.** En cuanto la ingesta
automática del BOE empiece a producir subastas, serán subastas **que nadie podrá
analizar sin volver a teclear todos los datos a mano**. El caudal que la 17-A
existe para abrir desembocaría en un formulario de diez pasos.

**Dueña: la ficha de la Fase 17-B** (`PLAN_FASES.md`), que no cierra su PR sin
resolverlo — igual que ya no cierra sin decidir el modo de notificación por
defecto. No es una nota al pie: es condición de la fase.

Descubierto el 2026-09-10 recorriendo el flujo completo con un caso real de la
AEAT, no con una fixture.

### 🟡 Frente abierto de PRODUCTO, planificado: sin comparables, el motor se compara consigo mismo

> **Mitigado, no resuelto.** Desde la Fase 2 de la línea de producto, un análisis sin
> comparables sale **rojo** («Sin ancla de mercado independiente…») y el checklist lo marca
> «NO DETERMINABLE». El motor ya no aparenta una valoración; la fuente automática sigue siendo
> la 17-C. Y el «hallazgo colateral» del ITP de más abajo **está corregido** (entrada
> «Corrección del motor» del `CHANGELOG.md`, `app/engine/fiscal.py`).

En el mismo recorrido real (Santiponce, 44 m², tasada en 23.391,72 €) el motor devolvió
`VM = 23.391,72 € · método = sin_comparables · confianza = 0,0`: **el valor de mercado cayó al
valor del propio tasador de la AEAT.** El motor fue honesto —confianza 0, carencia en el ICI,
que se hundió a 20— pero no tenía ancla independiente.

**Es el caso por defecto de todo lo que entre por la 17-B**, porque nadie teclea seis
comparables por subasta cuando el conector traiga doscientas al mes.

**Registrado como fase propia: [Fase 17-C](PLAN_FASES.md) — «Fuente automática de comparables
de mercado»**, ordenada justo después de la 17-B. No se implementa todavía. La ficha lleva el
caso real como contexto motivador, cinco fuentes candidatas con coste y viabilidad legal
investigados, y las reglas no negociables (nunca inventar un comparable; trazabilidad por
comparable congelada en el snapshot, P1).

**Hallazgo colateral, INDEPENDIENTE y más urgente que la fase:** la base imponible del ITP es el
**mayor** de (valor de referencia, valor declarado, precio pagado), y SEIS lo calcula sobre la
puja (`m11_rentabilidad.py:41`). En una subasta —donde el atractivo es pujar por debajo del
valor— **eso subestima el impuesto en todo análisis que se haga hoy**. Sin dueño: pendiente de
decidir si se corrige por separado y antes.

### ✅ Cerrado: la app privada no tenía maquetación móvil (y el registro anterior era erróneo)

**Corrección, primero.** Este frente se registró el 2026-09-11 como «la tabla densa no cabe en
móvil, 765-766 px». **Ese número salía del muestrario tipográfico de la Fase 0', no del
producto.** Medido el producto real ruta por ruta el 2026-09-13, el hallazgo era otro y peor:

**El armazón de la app privada no tenía maquetación móvil, y las DOCE rutas privadas
desbordaban.** `aside.fixed.w-60` + `main.ml-60`, sin un solo punto de ruptura en ninguno de los
dos: a 390 px el contenido empezaba en el píxel 272 y la barra lateral nunca se plegaba.
`/inversiones` medía **889 px de página sobre un móvil de 390**.

**Por qué nadie lo había visto:** las capturas de `capturar.mjs` se tomaban con `fullPage`, que
**ensancha la imagen hasta el contenido** y por tanto esconde exactamente el defecto que habría
que ver. Una captura ancha parece correcta. Es la misma familia del punto 6 del [[ADR-0014]]:
la herramienta mirando, pero no a lo que hacía falta.

**Resuelto** (Fase 15): cajón por debajo de `md` con cabecera y botón —cierra al navegar, con
Escape y tocando el velo—, la tabla de `/inversiones` desplazándose **dentro de su contenedor**
en vez de arrastrar la página, y la cabecera de regla de `/reglas` partiendo línea.
**17 rutas medidas, 0 desbordan.**

**Guarda permanente:** `frontend/scripts/medir-desborde.mjs` mide `scrollWidth` en el navegador
y **sale con código 1** si alguna ruta desborda. Demostrado en rojo contra el armazón sin
arreglar: 12 detectadas. Su alcance —solo 390 px, solo el estado inicial de cada ruta, y
necesita datos para que las tablas tengan filas— va declarado en su cabecera.

### 🔴 DECISIÓN ABIERTA, esperando al responsable: la fuente recomendada de la 17-C se cae (ahora confirmado con certeza)

**Confirmado el 2026-09-14: no existe servicio web libre para el valor de referencia del
Catastro.** El 2026-09-13 esto quedaba en «muy probable» porque la red de aquella sesión
bloqueaba los dominios del Catastro. Esta sesión **sí tuvo salida** y ejecutó la prueba
decisiva: llamada real al servicio libre (200, sin bloqueo, datos del caso de Santiponce, cero
campos de valor) **más** lectura íntegra del catálogo oficial vigente (`Webservices_Libres.pdf`
v2.6): 10 métodos en total, todos descriptivos o de localización, ninguno de valor — ni
siquiera la etiqueta del esquema llamada literalmente «datos económicos del inmueble» lleva un
importe. `SECAccvr.aspx`, visitado sin identificarse, exige Cl@ve/DNIe/certificado antes de
cualquier campo. Es gratuito y público —cualquiera puede consultarlo, no solo su titular— pero
**exige una credencial PERSONAL en cada consulta**. *Público* no es *anónimo*, y para un SaaS
que analiza subastas de muchos clientes **eso no automatiza**.

**Por qué importa:** la 17-C se planificó con el valor de referencia como fuente recomendada
precisamente por ser gratis, oficial y ligada a la referencia catastral que el anuncio ya trae.
Esa premisa se sostiene en todo menos en lo que hacía falta: **no se puede llamar sin una
persona detrás.** Con eso confirmado, **la decisión de qué fuente alternativa usar es del
responsable del producto, no de la sesión** (así se pidió).

**▶️ QUÉ TIENE QUE DECIDIR EL RESPONSABLE AHORA:** con la duda técnica cerrada, la pregunta ya no
es «¿hay API?» sino «¿qué ruta alternativa?» — descarga masiva alfanumérica del Catastro
(identificación + licencia), consulta masiva por fichero de la Sede, o dato como **entrada del
usuario** (ya soportado por el ADR-0015, campo opcional + carencia declarada, pero con una
pista incómoda: si nadie va a teclear comparables subasta por subasta, un valor de referencia
que hay que teclear cae en el mismo problema). Detalle y evidencia completa en la ficha de la
Fase 17-C (`docs/PLAN_FASES.md`).

**Fusionados:** [#12](https://github.com/christo23ch/seis/pull/12) Fase 17-A ·
[#13](https://github.com/christo23ch/seis/pull/13) puerta (a) ·
[#14](https://github.com/christo23ch/seis/pull/14) puerta (b) ·
[#15](https://github.com/christo23ch/seis/pull/15) Fase 14 ·
[#11](https://github.com/christo23ch/seis/pull/11) ADR-0010 y revisión visual ·
[#16](https://github.com/christo23ch/seis/pull/16) Fase 16 (auditoría, correcciones, ADR-0014) ·
[#17](https://github.com/christo23ch/seis/pull/17) M13 en operaciones inviables.

**La puerta está abierta:** (a) test de `init_db.main()` ✅ · (b) PostgreSQL en la CI ✅ ·
(c) regla de activación de la purga, no una tarea · (d) cerrada.

**Siguiente:** cerrada la Fase 15, **el trabajo 🟢 que no necesita paneles externos se ha
agotado.** Lo que queda pide, en este orden:

1. **Figura fiscal** (autónomo o sociedad) → desbloquea la **Fase 13 (Stripe)**, que es la única
   que convierte el producto en negocio. Es trámite humano, no código.
2. **Dominio y hosting** (H11 + DA-3 Vercel sin ratificar) → desbloquea la **Fase 11-B
   (despliegue)**, y con ella todo lo que solo se puede comprobar en producción: HTTPS sirviendo,
   backup restaurado con tiempo medido, alarma recibida, correo llegado a una bandeja real.
3. **HTML real del BOE** → desbloquea la **17-B**, que no cierra sin decidir el modo de
   notificación por defecto (el puente captación→análisis ya existe).
4. **Contenido humano**: el texto comercial de la landing y `/ayuda` —hoy provisional y dicho en
   el propio fichero— y el `MANUAL_DE_USUARIO.md`, que sigue sin existir.
5. **Textos legales del abogado**, que la Fase 14 dejó con marcador de pendiente.

Lo que sí se puede hacer sin nada de lo anterior: la **Fase 19 (analítica)** necesita alta en
Plausible. La primera tarea de la **17-C** —comprobar si el valor de referencia del Catastro
tiene servicio web libre— ya está hecha (no lo tiene); lo que falta es la decisión del
responsable sobre la fuente alternativa.

6. **Abrir el PR de `checkpoint/5f6-simulaciones-informes`** hacia `main`, con la revisión
   humana de siempre. Es la única tarea de esta lista que no espera a nadie de fuera.

---

## 1 · Cómo se resolvió la divergencia de ramas

Queda escrito porque es el motivo de que este documento exista.

Había **tres** líneas de trabajo simultáneas y mutuamente desconocidas:

| Línea | Qué era | Desenlace |
|---|---|---|
| `main` | Fases 9, 9.5, 10 y 12 | Base de todo |
| `claude/wizardly-wright-nkscpg` | Una **segunda Fase 10** + una Fase 11 rudimentaria | **Descartada.** Su registro respondía 400 ante email duplicado, convirtiendo `/auth/registro` en un oráculo de enumeración de cuentas; el de `main` responde 201 idéntico |
| `fase-11-infraestructura` (PR #4) | **Fase 11-A completa**, 7.000 líneas, un mes abierta | **Fusionada.** Estaba bloqueada por un solo test rojo |

El test rojo de la 11-A merece recordarse: afirmaba `entorno == "development"` dando por hecho
que la suite corre sin `SEIS_ENV`, cierto en local y falso en la CI, que corre con
`SEIS_ENV=test`. Se corrigió el test —no el workflow—, porque quitar la variable habría
adaptado el entorno real al test y habría dejado sin ejercitar la normalización de entornos que
esa misma fase introducía.

---

## 2 · Inventario por fases

| Fase | Estado | Evidencia |
|---|---|---|
| **1-8** · Motor experto | ✅ | `engine/modules/m01…m14` + `scoring_expres.py`. 30 tests de regresión (`test_golden_caso19` 14, `test_precios` 9, `test_vetos` 7) |
| **9** · Multi-tenancy | ✅ | `Organizacion`, scoping por `organizacion_id`, `require_superadmin`/`require_propietario`. 10 tests + 5 añadidos después (ver §3) |
| **9.5** · Migraciones | ✅ | `0005_esquema_base` + `0006_self_service`, ambas con `downgrade`. 13 tests. CI propia |
| **10** · Alta self-service | ✅ | `registro_service.py`, 6 endpoints públicos, `TokenConsumido`. 45 + 38 tests |
| **11-A** · Infraestructura (agnóstica) | ✅ | Sondas separadas (`salud.py`), staging estricto, `red.py`, purga, beat separado, CI completa. 7 ADRs |
| **11-B** · Despliegue real | ⬜ | Sin `render.yaml` en el repo (comprobado 2026-09-30). Semilla en el PR #6 cerrado |
| **12** · Notificaciones + scoring | ✅ | `Alerta`, `Notificacion`, `notificadores/`, matcher, digest. 18 tests |
| **13** · Stripe | 📋 | `FASE_13_PLAN_EJECUCION.md` y su mapa de impacto. Cero código |
| **14** · RGPD | ✅ | PR #15, migración `0008_rgpd`. Falta el texto del abogado |
| **15** · Landing | ✅ | PR #23 y #24, migración `0009_onboarding` |
| **16** · Seguridad | ✅ | PR #16, `docs/AUDITORIA_SEGURIDAD.md` |
| **17-A** · Captación, andamiaje | ✅ | PR #12, `app/ingesta/boe.py`, migración `0007_dedupe_subasta` |
| **17-B** · Captación real (BOE) | ⬜ | Selectores sin ajustar: espera el HTML real del portal |
| **17-C** · Comparables automáticos | 📋 | Planificada (PR #18, #25); la fuente recomendada cae; decisión abierta |
| **0'** · Sistema de diseño | ✅ | `docs/DESIGN_SYSTEM.md` |
| **Línea de producto 1-4** | ✅ | Puente captación→análisis, corte sin ancla, `ComparableUsado` (`0010`), detalle de valoración (`0011`). Commit `4a6f61d` |
| **Línea de producto 5C-5F.7** | ✅ en rama | Catálogo, simulaciones (`0012`-`0015`), informes oficiales, API y UI. Rama `checkpoint/5f6-simulaciones-informes`, **sin fusionar** |
| **18-20** | ⬜ | — |

**Cifras medidas el 2026-09-30:** 46 ficheros `test_*.py` en `backend/tests` · suite 828 passed,
9 skipped, 0 failed (SQLite) · frontend **sin tests unitarios** (solo e2e).
[VERIFICAR: número de endpoints y líneas de `backend/app` hoy — no recontados en esta sesión.]

---

## 3 · Aislamiento multi-tenant

Los **nueve** endpoints que devuelven o crean datos de análisis filtran por
`organizacion_id`. Recurso ajeno = **404**, nunca 403.

| Endpoint | Filtra |
|---|---|
| `POST /analisis` · `/analisis/async` | ✅ sella el tenant |
| `POST /analisis/simular` | ✅ no persiste ni lee |
| `GET /analisis` · `/{id}` · `/informe` · `/informe.pdf` · `/checklist` | ✅ |
| `GET /tareas/{tarea_id}` | ✅ **corregido** — antes no comprobaba nada |

**Lo que estaba mal y ya no:**

- `GET /tareas/{tarea_id}` devolvía el resultado de cualquier tarea a cualquier usuario
  autenticado: quien conociera un `tarea_id` ajeno obtenía el id del análisis y su semáforo.
  Ahora comprueba la organización y responde 404. El texto de la excepción de una tarea
  fallida tampoco se propaga.
- El filtro era ***fail-open***: `if organizacion_id is not None`. Como la columna es nullable,
  un usuario sin organización habría visto los análisis de todas. Ahora el parámetro es
  obligatorio y sin tenant no se devuelve nada.

**Correcto por diseño:** `GET /captacion` no filtra — las subastas son corpus compartido
(CLAUDE.md §4). Alertas y notificaciones son privadas **por usuario**, y lo cumplen.

---

## 4 · Deuda técnica

### Cubierta desde la auditoría
- ~~CVE crítica en `next@15.1.6`~~ → 15.5.25. De 4 vulnerabilidades de producción (1 crítica) a 2.
- ~~La CI ejecutaba 13 de 162 tests~~ → ejecuta la suite completa y el build del frontend.
- ~~`GET /tareas` sin aislamiento~~ y ~~filtro *fail-open*~~ → cerrados, con tests.

### Cerrada después de la auditoría (comprobado en el código el 2026-09-30)
- ~~`init_db.main()` sin test~~ → `tests/test_siembra.py` (puerta a).
- ~~La CI no levanta PostgreSQL~~ → job `postgres` + `tests/test_postgres.py` (puerta b).
- ~~`/health/listo` sin límite de tasa~~ → limitado en `app/api/salud.py` (Fase 16).
- ~~`UniqueConstraint` importado y nunca aplicado~~ → aplicado en `models.py` (dedupe de
  subastas, migración `0007`, y pasos de onboarding).
- ~~El ITP se liquidaba sobre la puja~~ → `app/engine/fiscal.py`, base = mayor de los valores.
- ~~Override de tipo incorrecto = 500~~ y ~~body con campos desconocidos aceptado~~ → 422
  (5F.7.1).
- ~~La hoja `version` salía como parámetro cambiado en la comparación~~ → `de3498f`.
- ~~`pytest` borraba `seis_dev.db`~~ → `9db44b3`.
- ~~Diálogo de confirmación duplicado~~ y ~~«Volver a la configuración original» activo con
  otra escritura en curso~~ → `4df5de8`.
- ~~Herramientas de revisión visual inservibles en Windows~~ → `medir-desborde.mjs` acepta
  `CHROMIUM_PATH` (5F.7.9).
- ~~Escalera degenerada sin tratamiento en la interfaz (Frontend 9)~~ → 5G.3: escalón «Límite»
  «No utilizable», sin cifra ni línea de adjudicación; métricas y comparación dicen «No
  utilizable» (la comparación trae `escalera_degenerada` del motor).
- ~~Formato de 4 cifras distinto (Frontend 10)~~ → 5G.3: `eur` con `useGrouping: "always"`
  («7.600 €»).
- ~~Sin cotas de rango en los overrides (Backend 4, en parte)~~ → 5G.4-A: los rangos concretos
  del catálogo son vinculantes (422) en simulaciones y edición global. Siguen sin validarse las
  listas vacías y los parámetros con rango `pendiente_de_definir` (ver Backend 4).
- ~~`capital.coste_capital_anual` sin rango ni advertencia (Backend 12)~~ → 5G.4-A, ADR-0016:
  rango 0–0,15, aviso desde 0,06, advertencia e impacto definidos.
- ~~¿ROI y TIR netos del coste de capital? (Backend 13)~~ → 5G.4-A: decidido explicarlo (el
  informe y la interfaz dicen que solo descuenta el precio límite). La comparación TIR − coste
  de capital y el VAN quedan diseñados para la 5H (auditoría, E6).
- ~~Punto decimal en el informe (Backend 15)~~ → 5G.4-B: «25,0 %», «RVC 1,08».
- ~~Ninguna e2e corre en la CI (Pruebas 1)~~ → 5G.4-C: job `e2e`.
- ~~`e2e/correr.sh` no funciona en Windows (Entorno 1)~~ y ~~dos nombres para el navegador
  (Entorno 2)~~ → 5G.4-C: lanzador alineado con `correr_simulaciones.sh` y
  `frontend/scripts/navegador.mjs`.
- ~~`/app` desbordaba a 390 px con datos~~ → 5G.4-C: la tabla del panel (y la de la comparativa)
  en un contenedor con desplazamiento propio. Defecto previo a 5G.4, medido también sobre
  `9c41bbe`.
- ~~La Escalera de precios desbordaba 8 px a 390 px en Linux/macOS~~ → `b74abd0`: escalones que
  encogen por debajo de `sm`. La e2e mide ahora también con la monoespaciada ancha forzada.
- ~~Con hipoteca, el precio límite contaba dos veces la parte financiada (Backend 16)~~ → 5H.1-B
  (`5cb0634`, `1386faa`, ADR-0018): coste de capital solo sobre el capital propio.
- ~~`coste_capital()` sin definir, §19 irreproducible, «TIR ≈ 23 %» mal etiquetada, colchón de
  plazo sin implementar, sin VAN (Backend 18, en parte)~~ → 5H.1-A/C/D: VAN y diferencial
  (ADR-0017), colchón (ADR-0019), §9.1 definido y §19 regenerado con las cifras del motor.
- ~~El PDF oficial no lleva su id, fecha ni procedencia (deuda D5)~~ → 5G.1: cabecera, bloque
  inicial y pie con la identificación leída de la fila `Informe`; la vista previa de
  `/informe.pdf` lleva «VISTA PREVIA — NO OFICIAL».

### Abierta — lista consolidada

Cada punto se ha comprobado en el código el 2026-09-30, salvo los marcados [VERIFICAR].

**Backend**

1. **`riesgos.bandas_ra = []` en un override da 500.** `m12_decision.py:39` usa `next()` sin
   valor por defecto; la validación de forma acepta una lista vacía. Arreglarlo es tocar el
   motor o añadir una regla de contenido.
2. **Carrera descartar/validar.** `descartar_simulacion` no pasa por `_analisis_bloqueado`
   (`simulacion_service.py:402`), así que un descartar y un validar simultáneos sobre la misma
   simulación pueden dejarla descartada y en uso a la vez. La interfaz lo mitiga (una sola
   escritura a la vez por análisis); la API no. Además, SQLite ignora `FOR UPDATE`.
3. **`obtener_configuracion_actual` no mira el estado** de la simulación apuntada
   (`simulacion_service.py:509`). Hoy solo `validar` y `seleccionar` mueven el puntero, y los
   dos lo comprueban.
4. **Validación de contenido incompleta.** Desde 5G.4-A los rangos concretos del catálogo son
   vinculantes, pero las listas vacías, los tramos desordenados y los parámetros cuyo rango sigue
   `pendiente_de_definir` (p. ej. `rvc_min`, ratios de adjudicación) se aceptan sin aviso.
5. *(Resuelta en 5G.1: ver arriba. Se conserva el número para no renumerar.)*
6. **El listado de simulaciones no trae `version_parametros_base`**, y el aviso pide el
   detalle completo (con el `resultado` entero) solo para ese campo.
7. **Los 3 parámetros fijos `perfiles.rentista.*`** (`catalogo.py:652`…) no llevan marca de
   perfil: en un análisis de otro perfil la UI no puede señalarlos.
8. **Fechas sin zona horaria con SQLite** (en PostgreSQL sí la llevan): el navegador las lee
   como hora local.
9. **Los 422 de pydantic llegan en inglés** y con `detail` como lista. *Resuelta en el alta
   (5I-B)*: `traducir422` los lleva a cada campo en español. Sigue abierta en el resto de
   pantallas, que usan `textoDeDetalle`.
10. `GET /analisis/{id}/informe.pdf` sigue existiendo por compatibilidad aunque la UI ya no lo
    ofrece. No es un defecto; conviene decidir si se retira.
11. [VERIFICAR: si una clave editable faltara en el árbol vigente, el catálogo o la validación
    darían 500 en vez de clasificarla. Hoy las 103 claves resuelven; no reproducido.]
12. *(Resuelta en 5G.4-A: ver «Cerrada» arriba.)*
13. *(Resuelta en 5G.4-A: ver «Cerrada» arriba.)*
14. **Análisis y simulaciones ya guardados conservan el texto anterior a 5G.2** (plan de puja
    con «60,011 €» y, si la escalera era degenerada, la instrucción de cargar el límite) hasta
    que se reanalicen: su `resultado` no se regenera. Los informes oficiales ya emitidos lo
    conservan por diseño (Markdown congelado).

15. *(Resuelta en 5G.4-B: ver «Cerrada» arriba.)*
16. *(Resuelta en 5H.1-B: ver «Cerrada» arriba.)*
17. *(Resuelta en 5J-2b: `SEM-EJEC-01` 2026.10 dice el depósito según el régimen, con espacio
    antes de «%», ADR-0024.)*
18. **Puntos de la auditoría que quedan para la 5H.2** (todos cambian el caso dorado o
    necesitan decisión): calendario de la TIR con los plazos reales de M06 (E3), nueva
    definición del precio límite (E2 b), coste del depósito (E5), perfil rentista según §9.2
    (E4) y rentabilidad del ICO (E8). El calendario real (E3) resolverá además el redondeo al
    par del horizonte de la TIR que expuso la 5J-2b (ADR-0026). Estado punto a punto en
    `docs/AUDITORIA_MOTOR_ESPECIFICACION.md`.
19. **Los intereses del préstamo se calculan a plazo P50 dentro de un precio límite estresado a
    P80** (`m06_costes.py:78`): −774 € de P_límite bruto en el caso con hipoteca si se usara P80.
    Fuera de la 5H.1 (ADR-0018, alcance 1): cambia `c_v`, que es único para toda la escalera.
20. **`financiacion.ltv` no tiene validación** (`contracts.py`, `ltv: float = 0.0`): acepta
    negativos o mayores que 1. El coste de capital y el colchón ya no dan abonos (`max(0, …)`),
    pero M06 y M09 calculan con el valor tal cual. Señalado en la revisión de código de 5H.1-B.
21. **Supuestos revisables del colchón de plazo** (ADR-0019): beneficio base y no pesimista, y
    sin descontar el coste de oportunidad del plazo ya previsto. Si se quiere una lectura más
    prudente, el ADR describe la alternativa.
22. *(Resuelta en 5I.1-A: `ComparableInput.meses_antiguedad` es `ge=0` y finita; un valor
    negativo, `inf` o `nan` es un 422 con el `loc` del campo. Ver 26 y 27.)*
23. **`financiacion.ltv` vacío con hipoteca se envía como ausente y el motor usa 0 %**: igual que
    antes de 5I (entonces el vacío se convertía en 0). Valorar exigirlo cuando el tipo sea
    hipoteca.
24. **La coordenada aproximada no se guarda como tal** (5I-E): se persiste como número, y el mapa
    pinta el marcador en la capital como si fuera la ubicación real. No afecta a ningún cálculo
    (el motor no usa lat/lng); para distinguirlo haría falta un indicador persistido (con
    migración) o una nota junto al mapa.
25. **Callejero sin implementar** (5I-E): geocodificar la dirección con una API oficial
    (CartoCiudad o Catastro, nunca scraping) para tener la coordenada del inmueble y no la de
    la capital. El guion `frontend/scripts/coordenadas-provincias.mjs` ya usa CartoCiudad.
26. **Simular un análisis guardado con una antigüedad de comparable negativa da 409**
    (5I.1-A, aceptado por el responsable). Motivo: la simulación reconstruye la entrada
    guardada con el contrato (`simulacion_service.py`, `_reconstruir_input`), y desde `ge=0`
    esa entrada ya no valida (`ReconstruccionInvalidaError` ⇒ 409). Afecta a cualquier valor
    negativo que llegara a guardarse: solo −6 exacto no se guardaba (división por cero en M03);
    por debajo de −6 el peso salía negativo y el análisis podía guardarse. **La base de
    desarrollo no tiene ninguno**
    (comprobado en solo lectura el 2026-10-06: 1 análisis, 7 comparables usados, 0 negativos) y
    no hay producción. **Salida si aparece uno:** reanalizar con la antigüedad corregida, que crea
    un análisis nuevo (los snapshots son inmutables, P1). No se «corrige» al reconstruir: poner 0
    en silencio cambiaría el resultado de un snapshot.
27. **Un JSON no estándar con `NaN` o `Infinity` en un campo cuya validación falla da 500, no
    422.** FastAPI incluye el valor recibido (`input`) en el 422 y `nan`/`inf` no se pueden
    serializar a JSON, así que falla el propio manejador del error (medido en 5I.1-A con
    `subasta.valor_subasta = NaN`; no hay manejador propio de `RequestValidationError`). Un
    float sin restricciones los acepta y no llega a haber 422. Efecto de 5I.1-A: en
    `meses_antiguedad`, `inf`/`nan` por HTTP pasan de aceptarse en silencio a este 500. Solo con
    clientes que emiten JSON no estándar (p. ej. `json.dumps` de Python); un navegador envía
    `null`. Salida: un manejador de `RequestValidationError` que convierta los `input` no
    finitos en texto.

**Frontend**

1. **Sin ESLint**: no hay configuración de ESLint y `next.config.mjs` tiene
   `eslint.ignoreDuringBuilds: true`. *Tests unitarios: desde 5I hay vitest* (`npm test`, en la
   CI), de momento solo para la lógica pura del alta (`lib/formulario.ts`, `lib/schema.ts`,
   `lib/errores-validacion.ts`, `lib/coordenadas.ts`, `lib/provincias.ts`).
2. **`Button` no anuncia `aria-busy`** en su estado de carga (`components/ui.tsx`).
3. **Valores de parámetro en bruto** («0.015», con punto) en el editor y la comparación
   (`String(v)`); el editor acepta coma al escribir, pero no la usa al mostrar.
4. **Las etiquetas y formatos de los 12 campos de la comparación** están escritos en el
   frontend (`CAMPOS`, `comparacion.tsx:146`); si el backend cambia un campo, hay que tocarlos.
5. **El histórico de informes no se refresca solo** si otra persona emite uno: solo se
   invalida tras una emisión propia.
6. **`Detalle.entrada` es `any`** (`lib/types.ts:42`).
7. **Falta el favicon**: 404 en la consola de cada página.
8. [VERIFICAR: longitud de la página a 390 px con «Mostrar todos» en la comparación (~9.800 px
   medidos en 5F.7.7) y si «Usar esta configuración» sigue ocupando dos líneas — no
   re-medido.]
9. *(Resuelta en 5G.3: ver «Cerrada» arriba.)*
10. *(Resuelta en 5G.3: ver «Cerrada» arriba.)*
11. **`resultado.tsx` usa colores del semáforo para cosas que no son semáforo:** los estados del
    checklist (`ok` → `sem-verde`, `pendiente` → `sem-amarillo`) y la viñeta de las
    condiciones (`sem-amarillo`). `sem-rojo` como color de error sí es la convención de
    `ui.tsx` (`Campo`, `ErrorBox`, botón `peligro`). Falta un token de estado neutro.
12. **El editor global de `/app/parametros` no muestra el aviso del coste de capital**: es un
    editor libre de JSON sin los metadatos del catálogo. Recibe el 422 con el rango, pero no el
    aviso de 0,06.
13. **`medir-desborde.mjs` mide solo el estado inicial**: la tabla de `/app/comparativa` no
    aparece hasta seleccionar análisis, así que su contenedor de 5G.4-C no lo cubre ninguna
    medida automática.
14. **La etiqueta «P adj. …» de la Escalera de precios queda tapada por el escalón «Límite»**
    (`components/resultado.tsx`): la línea de adjudicación va antes que los escalones en el DOM
    y estos, `relative`, se pintan encima. Visto en una captura a 390 px en 5G.4; el orden del
    DOM no ha cambiado desde antes de la fase, así que es previo. Sin corregir.

**Pruebas**

1. *(Resuelta en 5G.4-C: job `e2e` en la CI.)*
2. **El botón del aviso desactivado durante otra escritura** (`4df5de8`) no se ha probado en el
   navegador; la e2e solo cubre el caso en reposo.
3. **La marca «difiere del original»** del editor no se ha visto nunca en el navegador: la base
   de prueba no tenía deriva de conocimiento.
4. [VERIFICAR: qué son los 9 tests omitidos en SQLite — en septiembre eran 8, los exclusivos de
   PostgreSQL.]
5. *(Resuelta en 5I.1-B.)* **Carrera en el paso 4 de `simulaciones.mjs`**: leía el aviso de
   configuración nada más ver «En uso», sin esperar a que su consulta se refrescara. Ahora espera
   a que el aviso diga lo esperado (`avisoQueDiga`). Se corrigieron además las demás carreras de
   la misma clase: `emitir` esperaba un `[data-markdown]` que ya existía del informe anterior; el
   paso 9 comprobaba la lista y los informes del lector sin esperar a que cargaran (y su
   comprobación negativa podía pasar sin mirar nada); el paso 2 leía `isVisible()` antes de que
   llegara el catálogo del editor; el paso 10 podía medir cero pestañas; y `pestana()` esperaba
   400 ms fijos en vez de al contenido cargado. En las e2e de la 5I (`validacion-alta.mjs`,
   `nueva-inversion.mjs`), las lecturas del foco y de la marca «aproximada» ahora esperan.
   El paso 10 exige ahora al menos 8 pestañas medidas y `emitir` comprueba el 201 antes de leer
   el id del informe. Verificación: `e2e/correr_simulaciones.sh` (que ejecuta, sobre la misma
   pila, `simulaciones.mjs`, `nueva-inversion.mjs` y `validacion-alta.mjs`) 5 veces seguidas en
   local con la versión final: 5/5 en verde, 87 comprobaciones de navegador en cada una
   (2026-10-06). Una tanda previa, antes de corregir el foco de `validacion-alta.mjs`, dio 4/5:
   el fallo fue esa lectura del foco, no `simulaciones.mjs`.
6. **`test_migraciones.py` falló una vez en 5I-E por un cierre anómalo del subproceso de
   Alembic en Windows** (código `0xC000070A`, no un fallo de esquema): pasó en las dos
   repeticiones y en la suite siguiente; esta fase no añade migraciones. Vigilar si se repite.
7. **La validación del importe del depósito va en dos tiempos** (5I-C): Zod no ejecuta el
   refinamiento del objeto `subasta` mientras otro de sus campos falla, así que «No puede
   superar el valor de subasta» aparece tras corregir el valor. Aceptado y documentado en
   `lib/schema.ts`.

**Datos del procedimiento (5J-1, ADR-0022)**

1. *(Resuelta en 5J-2b, ADR-0024: el plan de puja, el §2 y el checklist usan el depósito del
   régimen. El alta conserva su 5 % por defecto y el aviso de que no coincide; ver el punto 6.)*
2. *(Resuelta en 5J-2b, ADR-0025: la táctica depende de la forma de puja del régimen.)*
3. **Los parámetros `procedimiento.regimenes` no son simulables** (el catálogo de la 5C solo cubre
   M12 y M13) y **`defaults.yaml` sigue en `2026.07`** aunque gana una sección: subir la versión
   cambiaría `version_parametros`, que es hoja de la foto del §19.
4. **Toda la TGSS, los meses de inmovilización, la venta extrajudicial y el concursal están sin
   confirmar** en la investigación: se muestran con su aviso o como «no consta». Ninguno puede
   convertirse en bloqueo sin la validación jurídica (D8). **Desde la 5J-2b los meses de
   inmovilización mueven cifras** (plazo, tenencia, coste de capital, escalera): siguen marcados
   «sin confirmar» y el informe lo dice. La forma de puja sí está contrastada con el BOE salvo en
   la venta extrajudicial y el concursal (ADR-0025).
5. **Una base de desarrollo creada con `create_all` necesita `alembic stamp 0015` y `upgrade head`**
   para recibir las columnas de la `0016` (`MANUAL_DE_PRUEBAS.md` §1 bis).
6. **Avisos de la revisión que se dejan** (LOW): con el alta por defecto (depósito 5 %, judicial,
   «No sé») el aviso «el depósito indicado no coincide» sale siempre, ruido que desaparece cuando
   el valor por defecto se tome del parámetro (punto 1); `PROCEDIMIENTOS_CON_DEUDA`
   (`frontend/lib/schema.ts`) repite qué procedimientos usan la cantidad reclamada, regla que vive
   en el YAML; y un cliente de la API puede enviar `es_vivienda_habitual=true` con
   `vivienda_habitual_ejecutado="no"` sin validación cruzada (el formulario no lo hace).

**Presentación (5K)**

1. **La deuda de presentación que exige tocar el motor o el backend** está en
   `docs/DEUDA_PRESENTACION_MOTOR.md`. La **5J-2a** resolvió los puntos 1-13 (operandos de «Ver
   cálculo») y 15-17 (el informe y el PDF de los análisis nuevos salen sin claves internas ni
   palabras sin tilde, ADR-0023). Quedan: los **informes oficiales ya emitidos** conservan su texto
   congelado con los códigos de antes; el catálogo global (19-20); y las pantallas de reglas y
   simulaciones. El depósito del alta (18) lo resolvió la 5J-2b (ADR-0024).
   **Decidido por el responsable (2026-10-07): se dejan como están.** Los 7 textos de la foto del
   §19 (3 ítems del checklist con `C_F`/`c_v` y 4 condiciones «Subsanar: …») se redactan legibles
   en el informe, pero el dato no cambia y la foto no se regenera (ADR-0023).
2. **La pantalla Parámetros pide el catálogo del análisis más reciente** para los nombres y
   unidades (no hay endpoint global). Sin ningún análisis en la organización, las claves se
   humanizan.
3. **`tests/datos/` del frontend** (informe y resultados reales del §19, del rentista con hipoteca y
   de dos tramos fiscales) hay que regenerarlos si el motor cambia el informe o el resultado; el
   comando está en `frontend/tests/datos/LEEME.md`.
4. **`m12_decision.calcular_escalera` sigue creciendo** (pasa con mucho de 50 líneas): los
   candidatos del rentista y los tramos fiscales podrían ir en funciones propias. Anotado en la
   revisión de la 5J-2a; no se refactoriza sin autorización para tocar el motor.

**Depósito, táctica y plazo (5J-2b, ADR-0024 a ADR-0026)**

1. **«Cesión de remate solo por el ejecutante»** (SEM-EJEC-01 y riesgo de ejecución de M13) es
   inexacto con la LO 1/2025: también la tienen los acreedores posteriores (LEC 647.3,
   investigación §2.8). Fuera del alcance de la fase; exige otra versión de la regla.
2. **La TIR no tiene un tramo propio para la inmovilización** (ADR-0026, punto 5): el pago del
   resto sigue en el mes 0 y el tramo posesorio en el 45 % del horizonte. Aproximación aceptada.
   **Y su horizonte se redondea al par** (`n = round(plazo_P50)`: `round(14,5) = 14`,
   `round(15,5) = 16`), así que medio mes de plazo puede sumar o restar un mes entero a la TIR.
   **Decisión del responsable (2026-10-08): no se toca.** Deuda vinculada al calendario real de la
   TIR de la 5H.2 (auditoría E3, punto 18 de la lista de arriba).
6. **Deuda de diseño para la 5M: la TIR con hipoteca sale idéntica a la TIR sin hipoteca** (26,41 %
   en el §19). M11 la calcula sobre flujos sin apalancar (precio entero en el mes 0, intereses
   dentro de `c_v`, sin entrada del préstamo ni amortización) y la escalera fija el mismo ROI
   objetivo, así que no mide el apalancamiento (ADR-0026, punto 7). Anterior a la 5J-2b.
3. **El §19 de la especificación** (`docs/SEIS_Especificacion_Funcional_y_Tecnica.md`) conserva el
   ejemplo con las cifras de la 5H.1-D y una nota que remite a las de la 5J-2b; la salida completa
   vigente es `docs/SEIS_informe_ejemplo_caso19.md`, regenerada en esta fase.
4. **La TGSS presencial está confirmada en la norma, no en la práctica**: no se ha comprobado si
   sus subastas se celebran ya en el Portal del BOE.
5. **Los análisis guardados conservan su resultado**: hasta reanalizarlos, muestran el depósito del
   alta, la táctica anterior y el plazo sin inmovilización. Los informes oficiales, por diseño.

**Entorno**

1. *(Resuelta en 5G.4-C.)*
2. *(Resuelta en 5G.4-C.)*
3. **Las dos e2e compilan en `frontend/.next`** y regenera `next-env.d.ts`: no puede
   convivir con un `next dev` sobre esa carpeta, y `next-env.d.ts` hay que restaurarlo después.
4. **`main` local va un commit por delante de `origin/main`** (`90fab7b`, docs de la 17-C) sin
   publicar.
5. La purga en modo `borrar` sigue sin estrenarse por la ruta de la tarea: es la regla (c) de
   `PLAN_FASES.md` §2-bis, no una tarea.
6. [VERIFICAR: si siguen las 2 vulnerabilidades de producción del `postcss` que fija Next — no
   se ha ejecutado `npm audit` en esta sesión.]
7. **La duración de la suite varía con la carga de la máquina:** 27 min 20 s en una ejecución
   y 2 min 39 s y 2 min 10 s en las dos siguientes, con el mismo código (2026-10-01). Ningún
   test pasa de 4 s (`--durations=25`) y crear y borrar la base temporal cuesta ~0,23 s por
   módulo. Defender tiene la protección en tiempo real activa y consumía ~21 % de un núcleo
   durante la suite. Propuesta: ejecutar siempre con `--durations=25`; si vuelve a pasar,
   mirar qué procesos corrían a la vez y, solo entonces, pedir a un administrador que excluya
   los directorios `seis-pytest-*` del análisis en tiempo real.

---

## 5 · Discrepancias con las suposiciones de partida

1. **No se usa shadcn/ui.** Toda la UI es artesanal y vive en un único `components/ui.tsx`.
   La decisión de adoptarlo o consolidar el sistema propio se evalúa en `docs/HERRAMIENTAS.md`.
2. **PostGIS está aprovisionado pero no se usa.** `docker-compose` levanta `postgis/postgis`,
   pero el esquema guarda `lat`/`lng` como `Numeric(9,6)`. No hay ninguna columna `geometry`.
3. **El vault de Obsidian existe** y está en la raíz del repositorio: 38 notas, 15 plantillas y
   **9 ADRs** (los 7 de la Fase 11-A más los 2 previos).

---

## 6 · Avance estimado

**50 % de las fases del plan hasta el lanzamiento** (6 de 12), con el criterio explícito de
`docs/PLAN_FASES.md` §5-bis: fases hechas sobre fases del plan, **sin ponderar** por tamaño.
No es una estimación de esfuerzo restante; es un recuento que cualquiera puede rehacer.

> El «~70 % del código · ~55 % del camino» que figuraba aquí era una estimación a ojo del
> 2026-09-08. Se sustituye por el recuento porque aquella cifra no decía cómo se había
> obtenido y no se podía comprobar.

A favor: el motor está blindado; el aislamiento multi-tenant responde 404 también en las rutas
nuevas de simulaciones e informes; hay 828 tests en verde; y el flujo captación → análisis →
simulación → informe oficial existe de punta a punta, con una e2e que lo recorre.

En contra, y por este orden:
- **El caudal todavía no es real.** El conector BOE existe, pero sin ajustar al HTML real
  (17-B): las subastas entran tecleadas.
- **No hay nada desplegado.** La 11-A dejó el repositorio listo; falta la 11-B y el hosting.
- **No se puede cobrar** (Fase 13, cero código).
- **Sin comparables automáticos** (17-C), todo análisis al que nadie teclee comparables sale
  rojo por falta de ancla de mercado.
- El frontend sigue sin tests unitarios ni ESLint.

---

## 7 · Pendiente de verificar

Lo que esta actualización (2026-09-30) no pudo comprobar en el repositorio ni en `git log`:

- Que siga sin haber PR abiertos en GitHub.
- Número de endpoints y líneas de `backend/app` hoy.
- Si una clave editable ausente del árbol vigente daría 500 (backend 11).
- Longitud de la página a 390 px con «Mostrar todos» y el salto de línea de «Usar esta
  configuración» (frontend 8).
- Qué son los 9 tests omitidos en SQLite (pruebas 4).
- Si siguen las 2 vulnerabilidades del `postcss` de Next (entorno 6).
- Las subfases 5B, 5F.2 y 5F.5 y las fechas de cada subfase de la línea 5x (ver `CHANGELOG.md`).
