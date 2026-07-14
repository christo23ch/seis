# SEIS — Plan maestro de lanzamiento · Fases 9–20
### De producto técnico completo a SaaS comercial en producción

**Punto de partida (avance actual: ~40 %).** Está construido y verificado: motor experto M01–M14 con 58 tests, API completa con JWT y roles, gobernanza del conocimiento versionada, módulo de captación y alertas, frontend Next.js 15 completo, PDF, Celery, Docker y manuales. Lo que falta es todo lo que convierte una herramienta interna en un negocio: multi-tenancy real, alta self-service, infraestructura de producción, cobro, legal, canales de notificación, y salida al mercado. Ese es el 60 % restante que aquí se planifica.

---

## 0 · Cómo usar este plan (léelo antes de ejecutar nada)

**Metodología de ejecución.** Cada fase con trabajo de código se ejecuta con **Claude Code** (terminal o app de escritorio) abierto sobre el repositorio `seis/`. El flujo por fase es siempre el mismo:

1. Crear una rama nueva (`fase-09-multitenant`, etc.).
2. Pegar el **PROMPT DE CONTEXTO MAESTRO** (sección 2) seguido del **prompt de la fase**.
3. Exigir siempre que el modelo entregue **primero un plan de cambios y lo pare para tu aprobación** antes de escribir código (los prompts ya lo piden).
4. Iterar hasta que la suite de tests esté verde y el frontend compile.
5. Revisar el diff completo tú mismo antes de fusionar. Un *pull request* por fase.

**Reglas de oro con los prompts:**
- Nunca aceptes un cambio de esquema de base de datos sin migración Alembic con `downgrade` funcional.
- Exige tests nuevos para cada funcionalidad nueva, incluidos **tests negativos** (lo que NO debe poder hacerse).
- Si el modelo se atasca dos veces en lo mismo, no insistas: pídele que explique el problema y replantea el prompt con esa información.
- Guarda cada prompt usado y su resultado: son la documentación de decisiones del proyecto.

**Modelos recomendados (criterio general).** Para fases transversales, delicadas o con estados complejos (multi-tenancy, pagos, seguridad, arquitectura de canales): **Claude Fable 5**, el modelo más capaz. Para fases bien acotadas con patrones conocidos (formularios, integraciones documentadas, páginas): **Claude Sonnet 4.6**, más rápido y económico. Para tareas mecánicas pequeñas: **Claude Haiku 4.5**. Precios y límites actualizados: https://docs.claude.com

**Duraciones.** Estimadas para una persona dedicada apoyándose en Claude Code. A tiempo parcial, multiplica por 2–3.

---

## 1 · Mapa de fases y avance

| Fase | Nombre | Tipo | Duración | Avance acumulado |
|---|---|---|---|---|
| — | Estado actual (Fases 1–8 completadas) | — | — | **40 %** |
| 9 | Multi-tenancy: aislamiento por organización | Código | 1–2 semanas | 48 % |
| 10 | Alta self-service y recuperación de cuenta | Código | 1 semana | 53 % |
| 11 | Infraestructura de producción | Mixta | 1 semana | 60 % |
| 12 | Notificaciones multicanal + scoring de alertas | Código | 2 semanas | 68 % |
| 13 | Monetización: planes, límites y Stripe | Mixta | 1–2 semanas | 75 % |
| 14 | Cumplimiento legal y RGPD | Mixta (abogado) | 1–2 sem (paralelo) | 80 % |
| 15 | Landing pública, onboarding y ayuda | Código | 1 semana | 85 % |
| 16 | Endurecimiento de seguridad | Código | 3–5 días | 89 % |
| 17 | Escalado de la captación (BOE real + fuentes) | Código | 2 semanas + continuo | 93 % |
| 18 | Canal WhatsApp (condicional) | Mixta | 2–4 semanas | 95 % |
| 19 | Analítica, soporte y métricas de negocio | Código | 3–5 días | 97 % |
| 20 | Beta cerrada y lanzamiento | Mixta | 2–4 semanas | **100 %** |

**Ruta crítica:** 9 → 10 → 11 → 13 → 20. **Paralelizables:** la 14 (legal) debe arrancar en paralelo desde la fase 9, no al final; la 11 puede solaparse con la 10; la 17 es continua desde que exista producción; la 12 puede ir en paralelo con la 13. **Puerta de decisión:** la 18 (WhatsApp) solo se ejecuta si la 12 demuestra demanda real del canal chat vía Telegram.

---

## 2 · PROMPT DE CONTEXTO MAESTRO (reutilizable)

Pega este bloque al inicio de **cada** sesión de Claude Code, antes del prompt de fase:

```
CONTEXTO DEL PROYECTO — SEIS (léelo entero antes de actuar)

Eres el Lead Software Engineer de SEIS, un SaaS de análisis experto de inversión
en subastas inmobiliarias españolas, ya funcional. Trabajas sobre el repositorio
existente; tu prioridad absoluta es NO ROMPER lo que funciona.

STACK Y ESTRUCTURA
- backend/: FastAPI + SQLAlchemy 2 + Pydantic v2 + Alembic + Celery + Redis.
  Motor experto en app/engine/ (NO tocar salvo indicación expresa: es el núcleo
  validado por tests de regresión). Modelos en app/models.py, servicios en
  app/services/, routers en app/api/ (auth.py, routes.py, conocimiento.py,
  captacion.py), seguridad JWT en app/core/security.py y deps en app/api/deps.py.
- frontend/: Next.js 15 App Router + React 19 + TypeScript estricto + Tailwind +
  React Hook Form + Zod + TanStack Query + Recharts + Leaflet. Cliente API tipado
  en lib/api.ts, tipos en lib/types.ts, auth en lib/auth.tsx, primitivas UI en
  components/ui.tsx. Toda la UI está en español.
- Base de datos: PostgreSQL en producción, SQLite en tests. Migraciones Alembic
  numeradas (0001..0003 existentes) con upgrade y downgrade funcionales.

CONVENCIONES OBLIGATORIAS
1. Código, comentarios, mensajes de error y UI: en español.
2. Toda la lógica de negocio vive en el backend; el frontend solo presenta.
3. Cada cambio de esquema = nueva migración Alembic reversible.
4. Cada acción sensible escribe en la tabla Auditoria (quien, entidad, accion, delta).
5. Tests en backend/tests/ con pytest; existen fixtures `api` (TestClient con BD
   limpia por módulo y admin sembrado) y `headers` (token admin). La suite actual
   (58 tests) DEBE seguir verde. Añade tests para todo lo nuevo, incluidos tests
   negativos de permisos.
6. El frontend debe compilar limpio: `npm run build` sin errores de tipos.

PROTOCOLO DE TRABAJO
- PRIMERO entrega un plan detallado de cambios (ficheros, modelos, endpoints,
  migraciones, tests) y DETENTE para mi aprobación. Solo tras mi OK, implementa.
- Al terminar: ejecuta `python -m pytest backend/tests -q` y `npm run build` en
  frontend/, y muestra los resultados. Termina con un resumen de qué cambió y
  qué decisiones tomaste.
```

---

## FASE 9 · Multi-tenancy — aislamiento por organización
**Duración:** 1–2 semanas · **Avance al completar: 48 %** · **Bloqueante de todo lo demás**

**Objetivo.** Que cada cuenta viva en su burbuja: hoy los análisis son visibles para cualquier usuario autenticado. Se introduce el concepto de **Organización** (aunque el 90 % sean cuentas unipersonales, esta capa evita una migración dolorosa cuando llegue el primer cliente-equipo).

**Decisiones de diseño ya tomadas (inclúyelas tal cual):**
- **Compartido entre todas las organizaciones:** las subastas captadas (el BOE es el mismo para todos) y el conocimiento T2/T3 (reglas, parámetros, perfiles — gestionados por la plataforma en el MVP).
- **Privado por organización:** análisis, resultados reales, calibración.
- **Privado por usuario (ya lo está):** alertas, favoritos, notificaciones.

**Pasos:**
1. Diseñar el modelo `Organizacion` y la pertenencia usuario→organización con rol interno (propietario, miembro).
2. Migración Alembic con **backfill**: crear una organización por cada usuario existente y asignarle sus datos; el admin actual pasa a "superadmin de plataforma" (rol nuevo, distinto del admin de organización).
3. Añadir `organizacion_id` a análisis y resultados reales; propagar el filtrado en todos los servicios y endpoints de lectura y escritura.
4. Redefinir permisos: el CRUD de conocimiento (reglas/parámetros/perfiles) queda restringido al superadmin de plataforma; la gestión de usuarios se divide (superadmin gestiona todo; propietario de organización gestiona solo su equipo).
5. Tests de aislamiento exhaustivos: dos organizaciones sembradas, verificar que ninguna ve ni modifica datos de la otra (listados, detalle por ID directo, calibración, CSV, geo, informes, PDF).
6. Frontend: el contexto de sesión incluye la organización; pantalla mínima "Mi equipo" para el propietario.

**Criterio de salida:** suite verde ampliada con ≥ 10 tests de aislamiento; acceder por ID directo a un análisis ajeno devuelve 404; la calibración solo agrega datos propios.

**Prompt de ejecución** · Modelo recomendado: **Claude Fable 5** en Claude Code (cambio transversal que toca autorización en todos los endpoints; el coste de un descuido aquí es una fuga de datos entre clientes).

```
[PEGAR CONTEXTO MAESTRO]

FASE 9 — MULTI-TENANCY POR ORGANIZACIÓN

Convierte SEIS en multi-tenant real. Diseño cerrado (no lo cuestiones, impleméntalo):
- Nueva entidad Organizacion; cada Usuario pertenece a exactamente una, con rol
  interno "propietario" o "miembro". Nuevo rol de plataforma "superadmin"
  (el admin bootstrap actual se convierte en superadmin vía backfill).
- Datos POR ORGANIZACIÓN: Analisis (y todo lo que cuelga de él) y ResultadoReal.
  La calibración (/calibracion) agrega solo datos de la organización del usuario.
- Datos GLOBALES compartidos: subastas captadas e ingesta, y el conocimiento
  T2/T3 (reglas/parametros/perfiles), cuyo CRUD pasa a exigir superadmin.
- Datos POR USUARIO (ya existentes, verifica que siguen aislados): alertas,
  favoritos, notificaciones.
- Alta de usuarios: el superadmin crea cualquier usuario; un propietario solo
  crea/activa/desactiva miembros de SU organización.

Requisitos técnicos:
1. Migración Alembic 0004 reversible con backfill: organización "por defecto"
   para los datos históricos, asignación de usuarios y análisis existentes.
2. Filtrado por organizacion_id en TODOS los servicios y endpoints de análisis:
   listar, detalle, informe, informe.pdf, checklist, export.csv, geo,
   resultado-real y calibracion. Acceso a recurso ajeno = 404 (no 403, para no
   revelar existencia).
3. deps.py: dependencia get_current_user devuelve también la organización;
   nueva dependencia require_superadmin.
4. Endpoints nuevos: GET /organizacion (datos propios y miembros, para
   propietario), POST/PATCH de miembros por el propietario.
5. Tests: módulo tests/test_multitenant.py con dos organizaciones sembradas y
   tests negativos de TODOS los endpoints listados en el punto 2, más permisos
   de conocimiento (miembro→403, propietario→403, superadmin→200).
6. Frontend: lib/types.ts y lib/auth.tsx incorporan organización; página
   /equipo para el propietario (listar, invitar por email+contraseña temporal,
   activar/desactivar); ocultar el bloque "Conocimiento" del menú a quien no
   sea superadmin.

Entrega primero el plan de cambios fichero a fichero y detente para mi aprobación.
```

---

## FASE 10 · Alta self-service y recuperación de cuenta
**Duración:** 1 semana · **Avance: 53 %**

**Objetivo.** Que cualquier persona pueda registrarse sola, verificar su email y recuperar su contraseña, sin intervención tuya.

**Pasos:**
1. Registro público: formulario email+contraseña+nombre → crea usuario **y su organización** (fase 9) en estado "pendiente de verificación".
2. Verificación por email: token firmado de un solo uso con caducidad (24 h); reenvío limitado.
3. "He olvidado mi contraseña": mismo mecanismo de token, formulario de nueva contraseña.
4. Protección de fuerza bruta: límite de intentos de login por IP+email con bloqueo temporal (usar Redis).
5. Frontend: páginas /registro, /verificar, /recuperar; estados de error claros en español.
6. (Opcional, +2 días) "Continuar con Google" (OAuth): reduce fricción de alta; déjalo para después de la beta si vas justo de tiempo.

**Criterio de salida:** un desconocido se registra, verifica, entra, cierra sesión y recupera contraseña sin tocar la base de datos; tests cubren tokens caducados, reutilizados y manipulados.

**Prompt de ejecución** · Modelo recomendado: **Claude Sonnet 4.6** (flujo estándar y bien documentado; Fable 5 solo si añades OAuth en la misma pasada).

```
[PEGAR CONTEXTO MAESTRO]

FASE 10 — ALTA SELF-SERVICE

Implementa registro público, verificación de email y recuperación de contraseña.

Requisitos:
1. POST /auth/registro (público): email, contraseña (mín. 8), nombre. Crea
   Organizacion propia + Usuario propietario con activo=False y campo nuevo
   email_verificado=False (migración 0005). Envía email de verificación
   reutilizando app/services/email_service.py.
2. Tokens de verificación y de reseteo: JWT firmados con propósito ("verificar"
   / "resetear") y caducidad 24h/1h respectivamente, de UN SOLO USO (guarda el
   jti consumido). Endpoints: POST /auth/verificar {token},
   POST /auth/recuperar {email} (respuesta idéntica exista o no el email, para
   no filtrar cuentas), POST /auth/resetear {token, nueva}.
3. Anti fuerza bruta en /auth/login: máx. 5 intentos fallidos por email en 15
   min usando Redis (en tests, fallback a memoria si no hay Redis); al superar,
   429 con mensaje en español.
4. Auditoría de registro, verificación y reseteo.
5. Frontend: páginas /registro, /verificar (lee token de la URL), /recuperar y
   /resetear; enlaces desde /login; textos claros en español; deshabilitar el
   botón durante el envío.
6. Tests: registro feliz, email duplicado, token caducado, token reutilizado,
   token con propósito equivocado, bloqueo por intentos y desbloqueo temporal.

Plan primero; espera mi aprobación antes de codificar.
```

---

## FASE 11 · Infraestructura de producción
**Duración:** 1 semana · **Avance: 60 %**

**Objetivo.** Un entorno real en internet con dominio, HTTPS, copias de seguridad probadas y alarmas, más un entorno de pruebas (staging) idéntico.

**Pasos (humanos, sin prompt):**
1. Comprar dominio y ponerlo tras **Cloudflare** (DNS + proxy, plan gratuito).
2. Elegir hosting. Recomendación para arrancar: **Render** o **Railway** (Postgres gestionado con backups, deploys desde Git, poco mantenimiento). Alternativa si priorizas coste a medio plazo: VPS Hetzner + Coolify. No lo decidas por precio del mes 1 sino por horas tuyas de mantenimiento.
3. Crear DOS entornos: `staging` (subdominio) y `producción`. Nada llega a producción sin pasar por staging.
4. Alta en **Sentry** (errores) y **UptimeRobot/BetterStack** (caídas + página de estado).
5. Generar secretos reales (JWT, contraseñas de BD) y guardarlos SOLO en el gestor de variables del hosting; rotar los de fábrica.
6. **Simulacro de restauración**: restaurar un backup de Postgres en staging y documentar el procedimiento con tiempos. Un backup no probado no existe.

**Pasos (con prompt):** preparar el repositorio para ese despliegue.

**Criterio de salida:** app accesible en `https://app.tudominio.com`, staging funcionando, un deploy automático a staging al fusionar en `main`, alarma recibida al simular una caída, y restauración documentada.

**Prompt de ejecución** · Modelo recomendado: **Claude Fable 5** (diseño de pipeline y runbook: decisiones con consecuencias operativas).

```
[PEGAR CONTEXTO MAESTRO]

FASE 11 — PREPARAR EL REPO PARA PRODUCCIÓN EN RENDER + CLOUDFLARE

No vas a desplegar tú: vas a dejar el repositorio listo y documentado para que
yo despliegue en Render con dos entornos (staging y producción) tras Cloudflare.

Requisitos:
1. Endpoint GET /api/v1/health ampliado: verifica conexión a BD y a Redis y
   devuelve estado por componente (para los healthchecks de Render y UptimeRobot).
2. Integración de Sentry en backend (FastAPI) y frontend (Next.js) activada solo
   si existe la variable SENTRY_DSN; sin ella, cero efecto.
3. render.yaml (Infrastructure as Code) con: servicio web backend, worker Celery,
   beat, frontend, Postgres y Redis; variables de entorno declaradas sin valores
   secretos.
4. GitHub Actions: al workflow de CI existente, añade job de deploy a staging
   en push a main (Render Deploy Hook vía secreto) y deploy a producción SOLO
   con aprobación manual (environment de GitHub con required reviewers).
5. Documento docs/RUNBOOK.md en español: procedimiento de deploy, rollback,
   restauración de backup paso a paso, rotación de secretos, y qué hacer ante
   caída de BD, de Redis o del conector de ingesta.
6. Revisa que ninguna configuración tenga secretos por defecto peligrosos en
   producción: si JWT_SECRET es el de fábrica y ENTORNO=produccion, la app debe
   negarse a arrancar con un error claro.

Plan primero; espera mi aprobación.
```

---

## FASE 12 · Notificaciones multicanal + scoring de alertas
**Duración:** 2 semanas · **Avance: 68 %**

**Objetivo.** Lo que pediste como corazón del negocio: que cada usuario reciba, por el canal que elija y con la frecuencia que elija, avisos de las subastas que encajan con él — y no solo por rango, sino con una nota de calidad automática.

**Pasos:**
1. **(Humano)** Alta en un proveedor de email transaccional: **Postmark** (simplísimo) o **Amazon SES** (barato). Configurar dominio de envío (SPF/DKIM) — sin esto, tus emails van a spam.
2. Abstracción de canales: una interfaz única "Notificador" con implementaciones email/telegram (y whatsapp en la fase 18). Todo aviso pasa por ahí.
3. **(Humano, 10 min)** Crear el bot de Telegram con @BotFather y guardar el token.
4. Vinculación Telegram: el usuario pulsa "Conectar Telegram", recibe un código de un solo uso, se lo envía al bot, y queda vinculado su chat.
5. Preferencias por usuario: canal(es), modo instantáneo o **resumen diario/semanal** (tarea Celery beat que agrupa), franja de silencio.
6. Enlace de **baja de comunicaciones** firmado en cada email (obligatorio legalmente).
7. **Scoring exprés de subastas nuevas**: al ingerir cada subasta, además del triaje, calcular una nota rápida 0–100 con los datos disponibles (relación VT/€ m² de la zona si hay referencia, tipología, plazo hasta cierre). Honestidad por diseño: la nota se etiqueta como "orientativa, sin análisis completo". Las alertas ganan el filtro "solo nota ≥ X".

**Criterio de salida:** un usuario recibe la misma alerta por email real y por Telegram según sus preferencias; el digest diario agrupa correctamente; darse de baja desde el email funciona sin login.

**Prompt de ejecución** · Modelo recomendado: **Claude Fable 5** (la abstracción de canales y el digest tocan Celery, plantillas y preferencias a la vez; merece el modelo más capaz).

```
[PEGAR CONTEXTO MAESTRO]

FASE 12 — NOTIFICACIONES MULTICANAL Y SCORING

Implementa el sistema de notificaciones multicanal y el scoring exprés.

Requisitos:
1. Abstracción: app/notificadores/ con interfaz común (enviar(usuario, mensaje))
   e implementaciones "email" (proveedor transaccional vía API, variable
   EMAIL_PROVIDER=postmark|ses|smtp con el SMTP actual como fallback) y
   "telegram" (Bot API con httpx; token en TELEGRAM_BOT_TOKEN).
2. Vinculación Telegram: POST /notificaciones/telegram/codigo genera código de
   6 dígitos con caducidad 10 min; un endpoint de webhook del bot (o polling en
   una tarea Celery si prefieres, justifica la elección) recibe "/start CODIGO"
   y guarda el chat_id del usuario. Botón "Desvincular".
3. Preferencias por usuario (migración): canales activos, modo
   instantaneo|digest_diario|digest_semanal, hora del digest, franja de
   silencio. Página /alertas amplía una pestaña "Preferencias".
4. Digest: tarea Celery beat que agrupa las notificaciones no enviadas del
   periodo en UN email/mensaje bien formateado en español.
5. Baja: cada email incluye enlace firmado (JWT propósito "baja") que desactiva
   las comunicaciones de ese usuario sin necesidad de login, con página de
   confirmación.
6. Scoring exprés en la ingesta: función en app/engine/ (módulo nuevo, NO tocar
   los existentes) que puntúa 0–100 con los datos de la subasta captada y
   parámetros T3 nuevos (pesos editables). Guardar en datos_brutos.score.
   Las alertas admiten filtro score_min; la UI de Subastas muestra la nota con
   etiqueta "orientativa". Documenta en el código sus límites.
7. Tests: matcher con score_min, generación/caducidad del código Telegram,
   digest que agrupa, baja firmada, y que sin proveedor configurado nada rompe.

Plan primero; espera mi aprobación.
```

---

## FASE 13 · Monetización — planes, límites y Stripe
**Duración:** 1–2 semanas · **Avance: 75 %**

**Objetivo.** Cobrar. Planes con límites claros, pago con tarjeta/SEPA, facturas e IVA automáticos.

**Pasos (humanos, imprescindibles antes de cobrar el primer euro):**
1. Resolver la **figura fiscal** (autónomo o SL) con tu gestor: sin ella no puedes facturar. Es el trámite más lento: arráncalo YA, en paralelo desde la fase 9.
2. Alta en **Stripe**, activar **Stripe Tax** (IVA automático UE) y **Customer Portal**.
3. Definir los planes. Propuesta inicial (ajústala con la beta): **Gratis** (1 alerta, 3 análisis/mes, solo avisos in-app) · **Pro ~29 €/mes** (alertas ilimitadas, 30 análisis/mes, email+Telegram, PDF) · **Despacho ~79 €/mes** (todo ilimitado, 5 usuarios, calibración, CSV). El plan gratis existe para probar; los límites son el motor de conversión.

**Pasos (con prompt):** integración técnica completa.

**Criterio de salida:** con tarjeta de test, un usuario gratis choca con su límite, mejora a Pro desde la página de precios, los límites se amplían al instante, cancela desde el portal y al final del periodo vuelve a gratis. Los webhooks sobreviven a reintentos duplicados.

**Prompt de ejecución** · Modelo recomendado: **Claude Fable 5** (los ciclos de vida de suscripción y la idempotencia de webhooks son el terreno clásico de errores sutiles que cuestan dinero).

```
[PEGAR CONTEXTO MAESTRO]

FASE 13 — SUSCRIPCIONES CON STRIPE

Integra facturación por organización con Stripe Checkout + Customer Portal.

Requisitos:
1. Migración: tabla Suscripcion por organización (plan, estado, stripe_customer,
   stripe_subscription, periodo_fin, limites JSON). Planes definidos en
   parámetros T3 nuevos (limites por plan editables por superadmin):
   gratis {alertas:1, analisis_mes:3, canales:["inapp"]},
   pro {alertas:-1, analisis_mes:30, canales:["inapp","email","telegram"]},
   despacho {todo -1, usuarios:5}.
2. Endpoints: POST /facturacion/checkout {plan} → sesión de Stripe Checkout;
   POST /facturacion/portal → URL del Customer Portal;
   POST /webhooks/stripe con verificación de firma e IDEMPOTENCIA (registrar
   event_id procesados): gestionar checkout.session.completed,
   customer.subscription.updated y .deleted, invoice.payment_failed
   (estado "morosa" con periodo de gracia de 7 días).
3. Enforcement: dependencia FastAPI "exigir_limite(recurso)" aplicada a crear
   alerta, crear análisis (contador mensual por organización) y canales de
   notificación. Al chocar: 402 con mensaje en español y el plan necesario.
4. Frontend: página /precios (pública) y /facturacion (plan actual, uso del mes
   con barras, botones mejorar/gestionar); avisos de límite alcanzado con enlace
   a mejora en los puntos de choque.
5. Modo test por defecto (claves sk_test); sin claves configuradas, todo el
   módulo queda desactivado y el producto funciona como hasta ahora.
6. Tests: enforcement de cada límite, webhook duplicado ignorado, transiciones
   de estado (alta→activa→cancelada→gratis, impago→morosa→gracia→gratis),
   y que un miembro no puede gestionar la facturación (solo propietario).

Plan primero; espera mi aprobación. Señala explícitamente qué configuraré yo a
mano en el dashboard de Stripe (productos, precios, portal, webhook endpoint).
```

---

## FASE 14 · Cumplimiento legal y RGPD
**Duración:** 1–2 semanas de trabajo, en **paralelo desde la fase 9** · **Avance: 80 %**

**Objetivo.** Poder operar en España/UE sin exposición: privacidad, términos, consentimientos y derechos de los usuarios.

**Pasos:**
1. **(Humano + abogado)** Encargar o revisar con un abogado: Política de Privacidad, Términos de Servicio, Política de Cookies y el **disclaimer de inversión** ("SEIS es una herramienta de apoyo a la decisión; no constituye asesoramiento financiero, legal ni fiscal"). Los borradores puede generarlos el modelo (prompt abajo), **la validación es humana y profesional, siempre**.
2. **(Humano)** Registro de Actividades de Tratamiento (RGPD art. 30) y firma de DPAs con los encargados: hosting, Stripe, proveedor de email, Sentry.
3. **(Código)** Consentimientos granulares en el registro: aceptar términos (obligatorio) ≠ aceptar comunicaciones comerciales ≠ aceptar cada canal. Guardar fecha y versión aceptada.
4. **(Código)** Derechos ARCO operativos: exportar mis datos (descarga JSON/CSV de todo lo del usuario y su organización) y eliminar mi cuenta (borrado con periodo de gracia de 14 días y anonimización de auditoría).
5. **(Código)** Banner de cookies solo si añades analítica con cookies (la fase 19 propone analítica sin cookies para evitarlo).

**Criterio de salida:** textos legales publicados y enlazados en registro y pie; un usuario exporta sus datos y elimina su cuenta él solo; los consentimientos quedan registrados con versión y fecha.

**Prompts** · Borradores legales: **Claude Fable 5** (pídele que marque los huecos que debe decidir el abogado). Implementación técnica: **Claude Sonnet 4.6**.

```
[PROMPT A — borradores legales, para revisión de abogado]

Actúa como redactor jurídico especializado en SaaS españoles B2C/B2B. Redacta
en español, para su REVISIÓN POR UN ABOGADO COLEGIADO (no son versión final):
1) Política de Privacidad, 2) Términos de Servicio, 3) Política de Cookies,
4) cláusulas de consentimiento del registro, 5) disclaimer de herramienta de
apoyo a la decisión de inversión.

Contexto: SEIS, SaaS español de suscripción que agrega subastas inmobiliarias
públicas, envía alertas por email/Telegram/WhatsApp y genera análisis de
inversión. Datos tratados: identificativos, credenciales, preferencias,
identificadores de chat, datos de facturación (via Stripe), datos introducidos
en análisis. Encargados: [hosting], Stripe, [proveedor email], Sentry, Meta/BSP
si WhatsApp. Titular: [figura fiscal pendiente].

Marca entre corchetes y lista al final TODAS las decisiones que debe tomar el
abogado o el titular (plazos de conservación, jurisdicción, edad mínima, DPO
sí/no...). Cíñete a RGPD, LOPDGDD y LSSI-CE.
```

```
[PROMPT B — implementación técnica; PEGAR CONTEXTO MAESTRO delante]

FASE 14 — CONSENTIMIENTOS Y DERECHOS RGPD

1. Migración: registrar en el usuario la aceptación de términos (versión y
   fecha) y consentimientos independientes de comunicaciones por canal; el
   registro de la fase 10 incorpora estas casillas (términos obligatorio,
   resto opcional y desmarcado por defecto).
2. GET /cuenta/exportar: descarga ZIP con JSON de todos los datos del usuario
   (perfil, alertas, notificaciones, favoritos) y de su organización si es
   propietario (análisis con entrada y resultado, resultados reales).
3. DELETE /cuenta: marca la cuenta para borrado en 14 días (email de aviso con
   enlace de cancelación firmado); tarea Celery diaria ejecuta los borrados
   vencidos anonimizando la auditoría (quien→"usuario eliminado") y, si era el
   único miembro, elimina la organización y sus datos.
4. Frontend: sección "Privacidad" en Administración con exportar, eliminar
   cuenta (doble confirmación) y gestión de consentimientos; enlaces a los
   textos legales en registro y pie de página (ficheros markdown servidos
   desde /legal/*).
5. Tests: consentimientos persistidos con versión, export completo, ciclo de
   borrado con gracia y cancelación, anonimización verificada.

Plan primero; espera mi aprobación.
```

---

## FASE 15 · Landing pública, onboarding y centro de ayuda
**Duración:** 1 semana · **Avance: 85 %**

**Objetivo.** Que un desconocido entienda qué es SEIS en 10 segundos, se registre, y su primera sesión le lleve de la mano hasta el momento "ajá" (su primera alerta y su primer análisis).

**Pasos:**
1. Landing en la raíz pública: propuesta de valor, cómo funciona en 3 pasos, captura del producto, precios, FAQ, CTA de registro. SEO básico (metadatos, sitemap, OpenGraph).
2. Onboarding en producto: checklist de primera vez (1. crea tu primera alerta → 2. actualiza fuentes → 3. analiza una subasta demo) con estados persistidos.
3. Centro de ayuda: convertir `MANUAL_DE_USUARIO.md` y la guía de instalación en páginas /ayuda navegables y buscables.
4. Emails de ciclo de vida mínimos: bienvenida y "no has creado tu primera alerta" a las 48 h.

**Criterio de salida:** medible en la fase 19 — de momento: un usuario nuevo llega al primer análisis guardado sin ayuda externa.

**Prompt de ejecución** · Modelo recomendado: **Claude Sonnet 4.6** para la implementación; el copy de la landing merece una pasada de **Claude Fable 5**.

```
[PEGAR CONTEXTO MAESTRO]

FASE 15 — LANDING, ONBOARDING Y AYUDA

1. Landing pública en frontend/app/(publico)/page.tsx (mover el login-guard para
   que la raíz sea pública y la app viva bajo /app o subdominio; propón la
   opción más limpia y espera mi decisión): hero con la propuesta "vigila las
   subastas por ti y te dice hasta cuánto pujar", 3 pasos con capturas,
   precios (desde la config de la fase 13), FAQ, CTA a /registro. Diseño
   coherente con el sistema visual existente (tinta/cobalto, cifras mono).
   Metadatos SEO, OpenGraph y sitemap.xml.
2. Onboarding: migración con checklist de primeros pasos por usuario; tarjeta
   en el Dashboard con los 3 pasos y su estado, que desaparece al completarse.
3. /ayuda: renderizar los manuales markdown existentes como páginas navegables
   con índice lateral y buscador simple por títulos.
4. Emails de bienvenida y de activación a las 48h sin primera alerta (tarea
   beat), respetando los consentimientos de la fase 14.
5. Tests de los endpoints nuevos y build verde.

Plan primero; espera mi aprobación.
```

---

## FASE 16 · Endurecimiento de seguridad
**Duración:** 3–5 días · **Avance: 89 %**

**Objetivo.** Cerrar los vectores básicos antes de exponer el producto a tráfico real y a dinero.

**Pasos:**
1. Auditoría guiada (prompt abajo) contra OWASP Top 10: repaso sistemático de autorización, inyección, exposición de datos, SSRF en el conector de ingesta, dependencias.
2. Rate limiting global de API (por IP y por usuario) con Redis.
3. Cabeceras de seguridad (CSP, HSTS, X-Frame-Options…) en frontend y backend.
4. Dependabot/renovate activado en el repo; escaneo de dependencias en CI.
5. Cloudflare: WAF básico, bloqueo de países si procede, bot fight mode.
6. **(Humano, recomendado)** Un pentest externo ligero o un programa de "amigos rompedores" antes del lanzamiento público.

**Criterio de salida:** informe de auditoría con todos los hallazgos altos/críticos corregidos y test que verifica el rate limiting.

**Prompt de ejecución** · Modelo recomendado: **Claude Fable 5** para la auditoría (visión adversarial); **Sonnet 4.6** para aplicar correcciones acotadas.

```
[PEGAR CONTEXTO MAESTRO]

FASE 16 — AUDITORÍA DE SEGURIDAD Y CORRECCIONES

PARTE 1 (solo análisis, sin tocar código): audita el repositorio con mentalidad
de atacante contra OWASP Top 10 y contra estos vectores específicos de SEIS:
- Autorización: ¿algún endpoint filtra datos entre organizaciones o escala roles?
- Conector de ingesta BOE: ¿SSRF si un superadmin cambia ingesta.boe.base_url?
- Webhooks de Stripe y de Telegram: verificación de origen y firma.
- Enlaces firmados (verificación, baja, borrado): ¿reutilizables? ¿enumerables?
- Subida/descarga de ficheros (PDF, CSV, export): inyección de contenido.
- Dependencias con CVEs conocidos (revisa requirements.txt y package.json).
Entrega un informe en docs/AUDITORIA_SEGURIDAD.md clasificado por severidad
con explotación hipotética y corrección propuesta. DETENTE ahí.

PARTE 2 (tras mi aprobación del informe): aplica las correcciones aprobadas,
añade rate limiting global (Redis, límites configurables por entorno, exentos
los healthchecks), cabeceras de seguridad en FastAPI y next.config, y tests
del rate limiting y de cada corrección de severidad alta.
```

---

## FASE 17 · Escalado de la captación
**Duración:** 2 semanas iniciales + trabajo continuo · **Avance: 93 %**

**Objetivo.** Que la materia prima del negocio (las subastas) fluya de forma fiable y creciente. El conector BOE actual es defensivo pero necesita ajuste empírico contra el portal real; además hay que vigilarlo y ampliar fuentes.

**Pasos:**
1. **Ajuste empírico del conector BOE**: ejecutarlo contra el portal real, capturar el HTML real y ajustar parámetros/selectores. Este trabajo es iterativo por naturaleza (prompt específico abajo).
2. Observabilidad de conectores: métricas de ítems/día por fuente y **alerta automática al superadmin si una fuente lleva 24 h a cero** (síntoma de cambio en el portal).
3. Cortesía y legalidad del scraping: cadencia limitada, respeto de robots/términos de cada portal, User-Agent identificado, y revisión de los términos de uso de cada fuente antes de añadirla.
4. Fuentes nuevas por prioridad de volumen: portales autonómicos de subastas, AEAT/TGSS, carteras bancarias. Una por iteración, con su conector aislado y sus fixtures de test.
5. Cola de ingesta robusta: reintentos con backoff, ingesta parcial nunca corrompe (ya hay dedupe; añadir transaccionalidad por lotes).

**Criterio de salida:** BOE ingiriendo a diario en producción con panel de métricas; alarma probada; al menos una fuente adicional en staging.

**Prompt de ejecución** · Modelo recomendado: **Claude Sonnet 4.6** con el HTML real pegado (tarea concreta de parsing); **Fable 5** si la estructura del portal resulta enrevesada.

```
[PEGAR CONTEXTO MAESTRO]

FASE 17 — AJUSTE DEL CONECTOR BOE CONTRA EL PORTAL REAL

Adjunto abajo (1) el HTML real de la página de resultados de subastas.boe.es y
(2) el HTML real de una página de detalle, capturados hoy. [PEGAR AQUÍ AMBOS]

Tareas:
1. Ajusta app/ingesta/boe.py para parsear EXACTAMENTE estas estructuras:
   paginación de resultados, extracción de identificador, tipo de bien, valor
   subasta, puja mínima, importe del depósito, provincia/localidad, fecha de
   conclusión y URL de la ficha. Mantén el diseño defensivo actual (nunca
   romper la ingesta; log claro de qué no se pudo parsear y cuántos).
2. Mueve a parámetros T3 (ingesta.boe.*) todo lo susceptible de cambiar:
   rutas, nombres de campos/etiquetas, tamaño de página, cadencia máxima de
   peticiones (respeta 1 petición/segundo).
3. Crea tests con fixtures: guarda versiones REDUCIDAS de estos HTML en
   backend/tests/fixtures/boe/ y testea el parser contra ellas (sin red), 
   incluyendo un HTML corrupto que debe devolver lista vacía con warning.
4. Métricas: registra en Auditoria el resultado de cada ingesta (ya existe) y
   añade tarea beat "vigilancia_fuentes" que crea Notificacion al superadmin
   si una fuente activa lleva >24h sin ítems nuevos.

Plan primero; espera mi aprobación.
```

---

## FASE 18 · Canal WhatsApp (condicional)
**Duración:** 2–4 semanas (los plazos los marca Meta) · **Avance: 95 %**

**Puerta de entrada:** ejecutar SOLO si las métricas de la fase 12 muestran demanda del canal chat (p. ej., >30 % de usuarios activos vinculan Telegram o lo piden expresamente). Si no, este presupuesto va a la fase 17.

**Pasos:**
1. **(Humano)** Verificar tu negocio en Meta Business Manager (requiere la figura fiscal de la fase 13 ya resuelta).
2. **(Humano)** Elegir BSP (proveedor intermediario): **Twilio** (documentación excelente) o **360dialog** (más barato). Meta cobra por conversación y el BSP por mensaje: modela el coste por usuario/mes antes de fijar en qué plan se incluye.
3. **(Humano)** Redactar y enviar a aprobación las **plantillas de mensaje** (obligatorias para iniciar conversación): "nueva subasta que encaja con tu alerta" y "resumen diario". Aprobación: días.
4. **(Código)** Nueva implementación "whatsapp" en la abstracción de la fase 12: opt-in explícito con verificación del número, envío vía API del BSP usando plantillas, gestión de errores y de costes (contador por organización), baja inmediata al responder "BAJA".
5. Incluirlo solo en planes de pago (el coste por mensaje lo exige).

**Criterio de salida:** un usuario de pago vincula su número, recibe una alerta real por WhatsApp y se da de baja respondiendo BAJA.

**Prompt** · Modelo recomendado: **Claude Sonnet 4.6** (integración documentada por el BSP). *Nota: el prompt es análogo al canal Telegram de la fase 12 — reutilízalo cambiando el proveedor y añadiendo: verificación de número por código, plantillas aprobadas como únicas vías de inicio, contador de coste por organización y palabra clave BAJA.*

---

## FASE 19 · Analítica, soporte y métricas de negocio
**Duración:** 3–5 días · **Avance: 97 %**

**Pasos:**
1. Analítica de producto **sin cookies** (Plausible o PostHog en modo cookieless, alojado en UE): evita el banner de cookies y simplifica el RGPD.
2. Instrumentar el embudo: registro → verificación → primera alerta → primera ingesta → primer análisis → suscripción. Sin esto, la beta de la fase 20 no enseña nada.
3. Panel de negocio para superadmin: usuarios activos, conversión del embudo, MRR, bajas — puede ser una página interna más leyendo de Stripe y de la BD.
4. Soporte: correo soporte@ con plantillas de respuesta, y widget simple de "Enviar feedback" dentro de la app (a la BD + notificación al superadmin).

**Prompt** · Modelo recomendado: **Claude Sonnet 4.6**; el panel interno puede hacerlo **Haiku 4.5** si el presupuesto aprieta.

```
[PEGAR CONTEXTO MAESTRO]

FASE 19 — ANALÍTICA Y PANEL DE NEGOCIO

1. Integra Plausible (script solo en producción vía variable de entorno) y
   define eventos personalizados del embudo: registro_completado,
   email_verificado, primera_alerta, primera_ingesta, primer_analisis,
   suscripcion_iniciada. Dispáralos desde el frontend en los puntos exactos.
2. Widget "Enviar feedback" (botón flotante discreto): modal con texto libre y
   pantalla actual; guarda en tabla nueva y notifica al superadmin.
3. Página interna /panel (solo superadmin): registros/día, embudo con tasas de
   conversión entre pasos (desde la BD), organizaciones por plan, MRR estimado
   (desde la tabla Suscripcion), últimas bajas y últimos feedbacks.
4. Tests del feedback y de los agregados del panel.

Plan primero; espera mi aprobación.
```

---

## FASE 20 · Beta cerrada y lanzamiento
**Duración:** 2–4 semanas · **Avance: 100 %**

**Objetivo.** Validar con humanos reales antes de abrir la puerta, y abrirla con red de seguridad.

**Pasos:**
1. **QA guionizado completo**: un guion end-to-end (registro → alerta → ingesta → análisis → pago test → cancelación → borrado de cuenta) ejecutado en staging en Chrome/Safari/móvil. El guion lo redacta el modelo (Fable 5) a partir del repo; la ejecución es humana.
2. **Prueba de carga básica** sobre staging (k6 o Locust): 100 usuarios concurrentes navegando y 10 análisis simultáneos; corregir cuellos evidentes.
3. **Beta cerrada**: 10–30 usuarios reales del perfil objetivo (inversores en subastas). Semanalmente: entrevistas cortas + embudo de la fase 19. Dos ciclos de corrección mínimo.
4. Ajustar **precio** con lo aprendido (dispuesto-a-pagar real, no intuición).
5. **Checklist de go-live**: backups verificados esa semana, alarmas probadas, textos legales publicados, dominio de email "calentado" (envíos graduales), plan de rollback ensayado, y soporte con capacidad para responder <24 h.
6. Lanzamiento gradual: quitar la lista de espera por tandas, no de golpe.

**Criterio de salida (fin del proyecto, 100 %):** primeros clientes de pago reales, embudo midiendo, sistema estable una semana sin intervención manual.

---

## Anexo A · Presupuesto mensual orientativo de servicios (fase de lanzamiento)

Dominio ~1 €/mes · Cloudflare 0 € · Hosting (Render starter con Postgres y Redis) 25–50 € · Email transaccional 0–15 € (por volumen) · Sentry 0 € (capa gratuita) · Plausible ~9 € · Stripe: sin cuota fija, ~1,5–2,9 % + 0,25 € por cobro · Telegram 0 € · WhatsApp (si fase 18): variable por conversación, presupuestar aparte. **Total base: ~40–80 €/mes** antes de escalar. El coste dominante del proyecto no son los servicios: son tus horas y, en su caso, el abogado (fase 14) y el gestor (fase 13).

## Anexo B · Riesgos principales y su mitigación

1. **Fuga de datos entre organizaciones** (fase 9 mal rematada) → tests negativos exhaustivos + auditoría de la fase 16 antes de la beta.
2. **Dependencia del portal BOE** (cambia su HTML y te quedas ciego) → vigilancia de fuentes de la fase 17 + parámetros T3 ajustables sin redeploy + diversificar fuentes.
3. **Emails a spam** → dominio dedicado con SPF/DKIM desde el día uno y calentamiento gradual.
4. **Legal tardío** → la fase 14 arranca en paralelo desde la 9; el bloqueante real suele ser la figura fiscal: primer trámite a iniciar.
5. **Construir la fase 18 sin demanda** → puerta de decisión con métrica objetiva tras la 12.
