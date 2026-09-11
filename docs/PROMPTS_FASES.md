# SEIS — Prompts de ejecución por fase

Un prompt por fase, autónomo y copiable en una sesión nueva de Claude Code sin memoria de las
sesiones anteriores. Todos exigen el mismo protocolo y terminan pidiendo un resumen apto para
revisar en el móvil.

**Cómo se usan:** pega el bloque de contexto (§0) y a continuación el prompt de la fase.
El orden de las fases está en `docs/PLAN_FASES.md`.

---

## 0 · Bloque de contexto (pégalo antes de cualquier prompt)

```
CONTEXTO DEL PROYECTO — SEIS. Léelo entero antes de actuar.

Eres el Lead Software Engineer de SEIS, un SaaS español de análisis de inversión
en subastas inmobiliarias, ya funcional y en producción de código (no desplegado).
Tu prioridad es NO ROMPER lo que funciona.

STACK
- backend/: FastAPI · SQLAlchemy 2 · Pydantic v2 · Alembic · Celery · Redis ·
  PostgreSQL (SQLite en tests).
- frontend/: Next.js 15 App Router · React 19 · TypeScript estricto · Tailwind ·
  React Hook Form + Zod · TanStack Query · Recharts · Leaflet.
  NO se usa shadcn/ui: la UI es artesanal y vive en components/ui.tsx.
- El motor experto M01-M14 está en backend/app/engine/. NO SE TOCA sin indicación
  expresa: lo valida el caso dorado §19 como test de regresión.

DOCUMENTOS QUE DEBES LEER ANTES DE PLANIFICAR
- docs/ESTADO_ACTUAL.md — índice de estado: qué existe, qué no, y qué ramas y PRs
  están vivos. Es la fuente de verdad sobre el estado.
- docs/PLAN_FASES.md — orden de fases y criterios de salida.
- CLAUDE.md — convenciones. docs/PENDIENTES.md — deuda conocida.
- 30-Decisiones/ADR/ — catorce ADRs con decisiones ya tomadas. NO las reabras sin
  motivo nuevo; si crees que una está mal, dilo y para. El ADR-0014 es de
  proceso y te obliga en CADA fase: léelo.

CONVENCIONES OBLIGATORIAS
1. Español en código, comentarios, mensajes de error, UI y commits.
2. Toda la lógica de negocio en el backend; el frontend solo presenta.
3. Cada cambio de esquema = nueva migración Alembic con `downgrade` FUNCIONAL.
4. Cada acción sensible escribe en la tabla Auditoria.
5. La suite entera debe seguir verde. Ejecuta:
     cd backend && SEIS_ENV=test python -m pytest tests -q -rs
   El frontend debe compilar limpio: cd frontend && npm run build
6. Aislamiento multi-tenant: los análisis son privados por organización; alertas y
   notificaciones, privadas por usuario. Acceder a un recurso ajeno devuelve 404,
   NUNCA 403. Todo endpoint nuevo que lea datos debe filtrar, y llevar su test.
7. Los filtros por tenant son FAIL-CLOSED: sin organización, no se devuelve nada.

PROTOCOLO, SIN EXCEPCIONES
- PRIMERO un plan de cambios fichero a fichero, y DETENTE para mi aprobación.
- Solo tras mi OK, implementa.
- Tests nuevos obligatorios, incluidos TESTS NEGATIVOS: lo que NO debe poder
  hacerse, permisos, aislamiento entre organizaciones, tokens caducados o
  reutilizados. Verifica que cada test nuevo FALLA contra el código anterior; si
  pasa en ambos, no está probando lo que crees.
- DEMOSTRACIÓN POR MUTACIÓN en todo hallazgo o corrección de severidad alta o
  media: rompe el mecanismo a mano, enseña el rojo, y revierte. Un test que nunca
  se ha visto fallar no ha demostrado nada. Es la práctica que ha encontrado los
  cuatro puntos ciegos de este proyecto; no es opcional.
- DECLARACIÓN DE ALCANCE (ADR-0014). Todo mecanismo de verificación que
  escribas —un test derivado del esquema, una limpieza por nombre de columna, un
  auditor, un matcher, un detector— lleva en su propio docstring una sección
  «QUÉ NO CUBRE», junto al código y no en un documento aparte: quien va a confiar
  en el mecanismo está leyendo el mecanismo.
  Y si puede detectar que no está en condiciones de hacer su trabajo —la
  colección que recorre está vacía, la tabla que busca no existe, falta la
  configuración que necesita—, que FALLE. Un verde que no comprobó nada es peor
  que un rojo, porque produce confianza. Cuando fallar cause más daño del que
  evita (una sonda pública, un middleware en el camino crítico), que lo diga en
  voz alta —log y contador visible— y quede escrito por qué no falla.
- Antes de cerrar el PR, actualiza la tabla «Frentes abiertos» de
  docs/ESTADO_ACTUAL.md, y escribe un ADR en 30-Decisiones/ADR/ por cada decisión
  discutible, usando 900-Plantillas/Plantilla-ADR.md.
- Si la fase toca FRONTEND: adjunta capturas del ANTES y el DESPUÉS de cada
  pantalla afectada, generadas desde `frontend/` con
  `node scripts/capturar.mjs antes|despues` (procedimiento en
  docs/REVISION_VISUAL.md). Sin ellas la revisión de diseño se hace a ciegas y no
  se acepta el PR. Referencia obligatoria en toda decisión
  visual: docs/DESIGN_SYSTEM.md.
- Termina con un RESUMEN DE CAMBIOS POR FICHERO apto para revisar en el móvil:
  una línea por fichero y, aparte, las 3 decisiones más discutibles señaladas.
  No pegues diffs largos.
```

---

## Deuda previa · Test de `init_db.main()` 🟢

```
Cierra el hueco de cobertura nº 1 de docs/PENDIENTES.md.

`init_db.main()` y `sembrar.main()` orquestan la siembra (abrir sesión, sembrar
conocimiento, sembrar administrador, cerrar) y NINGÚN test ejecuta esa
orquestación: solo las piezas por separado.

Por qué importa ahora: el ADR-0004 retiró `create_all` de staging y producción, así
que una mutación como envolver la siembra en `if creado:` deja la suite verde en
development y test, y en producción arranca una instalación SIN reglas, SIN
parámetros y SIN administrador. No se detecta hasta el despliegue.

Requisitos:
1. Test que ejecute init_db.main() de extremo a extremo contra una base vacía y
   afirme que después existen reglas, parámetros y usuario administrador.
2. Test equivalente para sembrar.main(), que duplica esa orquestación.
3. Demuéstrame que sirven: aplica a mano la mutación `if creado:` y enséñame los
   tests en rojo. Sin esa demostración no acepto el PR.

No cambies el comportamiento de la siembra. Solo tests.
```

## Deuda previa · PostgreSQL en la CI 🟢

```
Añade PostgreSQL al workflow de CI (.github/workflows/ci.yml).

Hoy la CI solo corre SQLite, así que tres caminos exclusivos de PostgreSQL no se
ejecutan en ninguna parte: `SET LOCAL statement_timeout` en la sonda de salud,
`with_for_update(skip_locked=True)` en la purga, y el motivo de
`_rollback_silencioso`. Además T5 (tests/test_migraciones.py) queda omitido
permanentemente.

Requisitos:
1. `services: postgres:16` en el job del backend, con healthcheck.
2. Definir SEIS_TEST_POSTGRES_URL apuntando a una base desechable cuyo nombre
   contenga «test» (el propio test lo exige como salvaguarda).
3. La CI debe dejar de reportar la omisión de T5.
4. No aumentes el tiempo de CI más de lo imprescindible: si conviene, un job
   aparte que corra solo los tests que necesitan PostgreSQL.

Criterio de salida: la salida de la CI muestra 0 omisiones, y los tres caminos
citados aparecen ejecutados.
```

## Fase 11-B · Despliegue real 🟡

```
FASE 11-B — DESPLIEGUE EN RENDER

La Fase 11-A dejó el repositorio listo (sondas separadas, entornos estrictos,
planificador propio, higiene de despliegue). Falta lo que depende del proveedor.

Punto de partida: el PR #6, CERRADO, contiene una semilla utilizable. Reutilízala
corrigiendo lo que quedó mal:
- `healthCheckPath` debe apuntar a /api/v1/health/listo (readiness), NO a
  /api/v1/health, que es la sonda de liveness trivial.
- Las variables deben alinearse con .env.produccion.example de la 11-A.
- JWT_SECRET del worker y del beat debe COPIARSE del backend con `fromService`:
  con `generateValue` cada servicio tendría un secreto distinto y los enlaces de
  baja firmados por el worker serían rechazados por el backend.
- El beat va en su propio servicio, nunca embebido en un worker escalable.

Requisitos:
1. render.yaml válido según la especificación de blueprints de Render.
2. Workflows de despliegue: staging automático tras CI verde, producción manual
   con environment protegido. Sin `continue-on-error`: un despliegue fallido debe
   reportarse en rojo.
3. docs/RUNBOOK.md con despliegue, rollback, restauración de backup, rotación de
   secretos e incidentes. REPITE en él los dos avisos del README: el .env anterior
   a la 11-A impide arrancar la pila (hace falta PROXIES_DE_CONFIANZA=ninguno) y
   los puertos publicados escuchan en loopback por defecto.
4. Documenta qué configuro yo a mano y en qué orden.

No inventes URLs ni dominios: usa variables del repositorio.
```

## Fase 17-A · Captación, andamiaje 🟢

```
FASE 17-A — ANDAMIAJE DEL CONECTOR DE CAPTACIÓN

Esta fase NO ajusta el parser contra el portal real: eso es la 17-B y espera a que
yo aporte HTML real. Aquí se construye todo lo demás, que es la mayor parte.

Contexto: hoy la única forma de que entre una subasta es que alguien la teclee
(api/captacion.py es un POST manual). No existe app/ingesta/. Sin caudal, las
alertas y el scoring de la Fase 12 —construidos y probados— vigilan el vacío.

Requisitos:
1. app/ingesta/ con contratos tipados de lo captado (Pydantic), separando el
   PARSEO (texto → contrato) de la INGESTA (contrato → base de datos). El parser
   no toca la base y la ingesta no sabe de HTML: es lo que permitirá ajustar
   selectores en la 17-B sin tocar la persistencia.
2. Diseño defensivo: un ítem ilegible no rompe el lote. Cuenta y registra qué no
   se pudo parsear y por qué; un HTML corrupto devuelve lista vacía con aviso,
   nunca una excepción.
3. Dedupe REAL: aplica UniqueConstraint(fuente_codigo, identificador_externo) a la
   tabla subasta —hoy UniqueConstraint está importado en models.py y sin aplicar a
   ninguna tabla— con su migración Alembic reversible. Ojo: identificador_externo
   es nullable y las altas manuales lo dejan vacío; comprueba que eso no colisiona.
4. Transaccionalidad por lote: un ítem corrupto no tumba a los demás; reingerir el
   mismo lote no duplica filas.
5. Parámetros T3 `ingesta.boe.*` para todo lo que puede cambiar sin desplegar:
   selectores, tamaño de página, cadencia máxima (respeta 1 petición/segundo).
6. Vigilancia de fuentes: tarea beat que crea Notificacion al superadministrador si
   una fuente activa lleva más de 24 h sin ítems nuevos. Reutiliza el modelo
   Notificacion, que YA EXISTE (Fase 12); no crees otro.
7. Fixtures en backend/tests/fixtures/boe/ con HTML SINTÉTICO —construido por ti,
   marcado claramente como no verificado contra el portal real— y tests del parser
   contra ellas, incluido el HTML corrupto.
8. Si expones un endpoint para procesar HTML, que acepte SOLO el HTML ya
   descargado, nunca una URL que el backend vaya a buscar: evita SSRF por diseño,
   que es un vector que la Fase 16 auditará.

Criterio de salida: reingerir dos veces el mismo lote no duplica; un ítem corrupto
no impide ingerir los demás; una fuente en silencio 24 h genera notificación al
superadministrador; y el parser está aislado de forma que la 17-B solo tenga que
tocar selectores.
```

## Fase 17-B · Ajuste del parser real 🔴 (necesita que yo capture HTML)

```
FASE 17-B — AJUSTE DEL PARSER CONTRA EL PORTAL REAL

Adjunto el HTML real capturado de subastas.boe.es. Ajusta app/ingesta/boe.py para
parsear EXACTAMENTE estas estructuras, sin tocar la capa de ingesta ni la
persistencia: el andamiaje de la 17-A las separó justo para esto.

Requisitos:
1. Extrae: identificador, tipo de bien, valor de subasta, puja mínima, importe del
   depósito, provincia y localidad, fecha de conclusión y URL de la ficha.
2. Todo selector o etiqueta susceptible de cambiar va a parámetros T3
   `ingesta.boe.*`, no incrustado en el código.
3. Sustituye las fixtures sintéticas por estas reales, REDUCIDAS a unos pocos
   resultados para que el repositorio no engorde.
4. Mantén el diseño defensivo: informa de cuántos ítems no se pudieron parsear y
   por qué, sin lanzar.
5. Mide y dime el porcentaje de campos extraídos correctamente sobre la muestra.

Criterio de salida: ≥ 90 % de los campos críticos extraídos sobre la muestra real;
un HTML corrupto sigue devolviendo lista vacía sin excepción.
```

## Fase 14 · RGPD 🟢

```
FASE 14 — CONSENTIMIENTOS Y DERECHOS RGPD

Requisitos:
1. Migración reversible: aceptación de términos con VERSIÓN y FECHA, y
   consentimientos independientes por canal de comunicación. El registro de la
   Fase 10 incorpora las casillas: términos obligatorio, el resto opcional y
   desmarcado por defecto.
2. GET /cuenta/exportar: descarga con todos los datos del usuario y, si es
   propietario, los de su organización.
3. DELETE /cuenta: marca para borrado en 14 días, con enlace de cancelación
   firmado; una tarea diaria ejecuta los vencidos y ANONIMIZA la auditoría.
4. Apóyate en app/services/purga_service.py, de la Fase 11-A: ya resolvió la parte
   difícil, que es que NINGUNA de las claves foráneas declara `ondelete`. Un
   borrado desordenado aborta la transacción en PostgreSQL y —peor— en SQLite pasa
   en verde dejando filas huérfanas, es decir, datos personales que sobreviven a un
   borrado dado por completo. Reutiliza ese orden, no lo reinventes.
5. Tests: consentimientos con versión y fecha; export completo; ciclo de borrado
   con cancelación dentro de la gracia; y verificación de que no quedan huérfanos.

Los textos legales los redacta un abogado: si generas borradores, marca entre
corchetes cada decisión que debe tomar él y lístalas al final.
```

## Fase 13 · Stripe 🟡

```
FASE 13 — SUSCRIPCIONES CON STRIPE

Ya existe plan: lee docs/FASE_13_PLAN_EJECUCION.md y docs/FASE_13_MAPA_IMPACTO_STRIPE.md
antes de planificar, y señálame dónde te apartas de ellos y por qué.

Requisitos:
1. Migración reversible: tabla Suscripcion por organización. Los planes y sus
   límites viven en parámetros T3, editables por el superadministrador.
2. Endpoints de Checkout y Customer Portal, y webhook con verificación de firma e
   IDEMPOTENCIA: registra los event_id procesados. Un reintento de Stripe no puede
   duplicar efectos.
3. Enforcement con una dependencia `exigir_limite(recurso)`. Al chocar: 402 con
   mensaje en español y el plan necesario. El límite de «alertas» engancha en el
   CRUD de alertas de la Fase 12, que ya existe: compruébalo antes de darlo por
   aplicado.
4. Sin claves configuradas, el módulo entero queda desactivado y el producto
   funciona como hoy. Test que lo demuestre.
5. Tests de transiciones de estado (alta→activa→cancelada→gratis;
   impago→morosa→gracia→gratis), de webhook duplicado ignorado, y NEGATIVO: un
   miembro no propietario no puede gestionar la facturación.

Dime explícitamente qué configuro yo en el panel de Stripe.
```

## Fase 16 · Auditoría de seguridad 🟢

```
FASE 16 — AUDITORÍA DE SEGURIDAD

PARTE 1 — SOLO ANÁLISIS, NO TOQUES CÓDIGO.

Audita el repositorio con mentalidad de atacante contra OWASP Top 10 y contra
estos vectores concretos de SEIS:
- Autorización: ¿algún endpoint filtra datos entre organizaciones o escala roles?
- Conector de ingesta: ¿SSRF si alguien cambia los parámetros T3 de ingesta?
- Webhooks de Stripe y de Telegram: verificación de origen y de firma.
- Enlaces firmados (verificación, reseteo, baja): ¿reutilizables? ¿enumerables?
- Generación de PDF y exportaciones: inyección de contenido.
- Dependencias con CVE conocidas (requirements.txt y package.json).
- El límite por origen: ¿la política de proxies de app/core/red.py se puede evadir?

Entrega docs/AUDITORIA_SEGURIDAD.md clasificado por severidad, con explotación
hipotética y corrección propuesta para cada hallazgo. Marca como «no aplicable» lo
que dependa de módulos aún no construidos, en vez de inventarlo. DETENTE AHÍ.

PARTE 2 — solo tras mi aprobación del informe: aplica las correcciones aprobadas,
añade rate limiting global extendiendo app/core/rate_limit.py (que ya implementa
ventana deslizante y degradación si Redis cae; NO lo reescribas), cabeceras de
seguridad, y un test por cada hallazgo de severidad alta.
```

## Fase 0' · Sistema de diseño 🟢

```
SISTEMA DE DISEÑO DE SEIS

Antes de escribir nada, lee docs/HERRAMIENTAS.md, donde está el análisis del
frontend actual y la decisión pendiente sobre shadcn/ui.

Produce docs/DESIGN_SYSTEM.md con: dirección estética argumentada con referencias
concretas del sector (herramientas de análisis financiero profesional), escala
tipográfica, paleta y tokens, tratamiento de datos numéricos y tablas densas,
estados de carga y de error, densidad de información y reglas de gráficos.

LA TIPOGRAFÍA NO SE ELIGE POR GUSTO. Hoy la cara del producto es Georgia, la serif
que todo sistema trae por defecto (tailwind.config.ts:18): no es una elección, es
la ausencia de una. Presenta DOS O TRES opciones y deja que yo decida. Para cada
una:
  · qué transmite y por qué encaja con un producto de análisis financiero que ve
    un inversor —no «se ve moderna»: qué asocia el lector con esa forma—;
  · cómo se comporta con CIFRAS: ¿tiene cifras tabulares? ¿el cero se distingue de
    la O, el uno de la ele? Es el 80 % de lo que SEIS muestra;
  · cómo se comporta en TABLAS DENSAS, con varias filas de números comparables;
  · licencia y peso, porque se sirve al navegador.
Y acompáñalas de CAPTURAS COMPARATIVAS reales generadas con
`node scripts/capturar.mjs`, desde `frontend/` (ver docs/REVISION_VISUAL.md): la misma pantalla con
cada opción, para poder compararlas mirando y no imaginando. No decidas tú.

Requisitos duros:
- Cada regla debe ser verificable, no una opinión: «tabular-nums en toda cifra
  comparable en columna», no «las cifras deben verse bien».
- Parte del frontend REAL y señala qué componente concreto de components/ui.tsx
  incumple cada regla, con fichero y línea.
- No propongas una reescritura completa: propón el orden en que migrar.

A partir de este documento, ningún prompt de frontend se ejecuta sin referenciarlo.
```

## Fase 15 · Landing y onboarding 🟢

```
FASE 15 — LANDING PÚBLICA, ONBOARDING Y AYUDA

REFERENCIA OBLIGATORIA: docs/DESIGN_SYSTEM.md. Si una decisión visual no está en
ese documento, pregúntame antes de improvisarla.

Requisitos:
1. Landing pública en la raíz. Hoy `/` vive bajo app/(app)/ y está protegida por
   sesión: propón cómo separarlo (app bajo /app, o subdominio) y ESPERA mi
   decisión antes de mover nada.
2. Onboarding: checklist de primeros pasos persistida por usuario, visible en el
   dashboard, que desaparece al completarse.
3. /ayuda a partir de los manuales en markdown. Aviso: MANUAL_DE_USUARIO.md NO
   EXISTE (solo MANUAL_DE_PRUEBAS.md, que es de instalación). Dímelo en el plan en
   vez de inventar contenido de usuario.
4. Correos de bienvenida y de activación, respetando los consentimientos de la 14.
5. Tests: las rutas privadas SIGUEN exigiendo sesión tras mover el guard. Es el
   cambio con más superficie de regresión de la fase.

Criterio de salida: Lighthouse ≥ 90 en rendimiento y accesibilidad; ninguna ruta
privada queda accesible sin sesión.
```

## Fase 19 · Analítica 🟡

```
FASE 19 — ANALÍTICA Y PANEL DE NEGOCIO

Requisitos:
1. Plausible en modo sin cookies (evita el banner y simplifica el RGPD), cargado
   solo en producción y por variable de entorno.
2. Eventos del embudo disparados en los puntos exactos: registro_completado,
   email_verificado, primera_alerta, primera_ingesta, primer_analisis,
   suscripcion_iniciada.
3. Widget de feedback: modal con texto libre y pantalla actual; guarda en tabla
   nueva (migración reversible) y notifica al superadministrador reutilizando
   Notificacion.
4. Página /panel solo para superadministrador, con el embudo y el MRR leído de la
   tabla Suscripcion de la Fase 13.
5. Tests del feedback, de los agregados del panel y NEGATIVO: un usuario normal no
   accede a /panel.
```

## Fase 20 · Guion de QA 🟢 (la ejecución es 🔴)

```
Redacta docs/QA_LANZAMIENTO.md: un guion de QA de extremo a extremo, ejecutable
por una persona, que recorra registro → verificación → alerta → ingesta → análisis
→ informe PDF → pago de prueba → cancelación → borrado de cuenta.

Requisitos:
- Cada paso con acción exacta, dato de entrada concreto y resultado esperado
  observable. Nada de «comprobar que funciona».
- Marca qué pasos exigen varios navegadores y cuáles móvil.
- Incluye los casos negativos que más duelen en producción: enlace de verificación
  caducado, pago rechazado, y acceso por URL directa a un recurso de otra
  organización (debe dar 404).
- Deriva el guion del repositorio real, no de lo que crees que hace.
```

---

## Apéndice · Qué tengo que capturar yo del BOE, y en qué formato

Instrucciones para el humano, no para el modelo. El sandbox web **no puede descargar
`subastas.boe.es`**: el proxy de egreso deniega ese dominio (comprobado). Sin estos ficheros, la
Fase 17-B no puede empezar.

### Qué capturar

| # | Página | Para qué |
|---|---|---|
| 1 | **Listado de resultados** de una búsqueda con varios resultados y **paginación visible** | Extraer el bucle de ítems y el paginado |
| 2 | **Ficha de detalle** de una subasta de **vivienda** | El caso mayoritario |
| 3 | Ficha de detalle de **otra tipología** (local, garaje o finca rústica) | Detectar campos que aparecen y desaparecen según el bien |
| 4 | *(Opcional pero útil)* Un listado **sin resultados** | El caso vacío, que es donde más parsers se rompen |

Con 1 y 2 se puede empezar. 3 evita la mitad de las sorpresas.

### Cómo capturarlo

**Con ordenador (lo mejor):**

```bash
curl -sS -A "SEIS/1.0 (contacto: tu-email)" "<URL>" -o listado.html
```

**Desde el móvil, si no hay otra:** abre la página, «Compartir → Guardar como archivo» o usa una
app de *view-source*. Lo importante es que sea el **HTML crudo**, no una captura de pantalla ni
un PDF: de una imagen no se puede extraer un selector.

### Cómo entregarlo

- Ficheros con extensión `.html`, en un mensaje o en una rama, con **nombre que incluya la
  fecha**: `listado_2026-09-08.html`, `detalle_vivienda_2026-09-08.html`.
- Acompaña cada uno de **la URL exacta** y la fecha y hora de captura. Sin la URL no se puede
  reproducir la búsqueda ni verificar después si el portal cambió.
- **No lo edites a mano** ni lo formatees: un HTML «arreglado» deja de parecerse al que llegará
  en producción, que es justo lo que hay que parsear.
- Si pesa mucho, no lo recortes tú: el modelo reduce la fixture conservando la estructura. Un
  recorte manual suele romper el anidamiento y hace fallar los selectores por un motivo falso.

### Antes de capturar

Revisa `robots.txt` y los términos de uso del portal, y ten presente que las fichas contienen
datos personales de deudores. Son publicidad legal y por tanto públicos, pero **no hay que
almacenarlos en el repositorio más allá de lo imprescindible**: la fixture debe reducirse a lo
necesario para probar el parser.
