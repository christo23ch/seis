# SEIS — Lista de pendientes (backlog)

Registro vivo del trabajo planificado y aún no implementado. Cada fase se ejecuta
con el protocolo del proyecto: **plan → aprobación → implementación → tests verdes
+ `npm run build` limpio → PR**. Detalle metodológico en `docs/SEIS_Plan_Maestro_Fases_920.md`.

**Estado del recorrido:** Fase 9 (multi-tenancy) ✅, Fase 9.5 (migraciones) ✅,
Fase 12 (notificaciones + scoring) ✅ y Fase 10 (alta self-service) ✅ completadas.
Siguiente: **Fase 11 (infraestructura de producción)**, que hereda dos asuntos
medidos en la 10 — la IP de origen bajo Docker y la purga de `token_consumido`.

---

## ✅ Fase 10 — Alta self-service (COMPLETADA, 2026-07-29)

Registro público, verificación de email, recuperación y cambio de contraseña,
y protección anti-abuso. Migración **`0006_self_service`**.

### Lo entregado, y en qué se apartó del plan

| Punto | Resultado |
|---|---|
| `email_service.py` | **No se creó.** Se reutilizó `app/notificadores/`, como ya anticipaba la nota de más abajo |
| `config.py += frontend_url, email_from` | Ya existían desde la Fase 12; solo se añadieron `login_max_intentos` y `login_ventana_min` |
| `crear_token_proposito` / `decodificar_token_proposito` | Ya existían; solo faltaba persistir el `jti`, que es lo que hace la tabla `TokenConsumido` |
| Email duplicado ⇒ 400 | **Derogado.** Responde **201 idéntico** y avisa por correo al titular: un 400 convertía `/registro` en un oráculo de enumeración de cuentas, incoherente con la regla «respuesta idéntica» que el propio plan exigía a `/recuperar` |
| Rate limit solo en login | **Ampliado** a `/registro`, `/recuperar` y `/reenviar-verificacion`: sin límite, los tres endpoints públicos que envían correo permitían bombardear un buzón ajeno |
| — | **Añadido `/auth/cambiar-password`.** No estaba en el plan. No existía **ninguna** ruta de código que modificara `hash_pwd` tras crear la cuenta |
| — | **Añadido `/auth/reenviar-verificacion`.** Sin él, un enlace caducado a las 24 h dejaba la cuenta sin salida posible |
| — | **Añadido el 403 accionable** en el login sin verificar. Con `activo=False` el usuario habría visto «email o contraseña incorrectos», que es falso |

### Decisiones que conviene no reinventar

- **`email_verificado` es una columna aparte de `activo`.** `activo` ya significa el
  alta/baja administrativa que ejerce el propietario; conflarlos haría que
  reactivar a un miembro lo diera por verificado.
- **`crear_usuario` nace con `email_verificado=True` por defecto.** No es un
  descuido: esa función la invocan el arranque, el superadmin y el propietario,
  que asignan la contraseña a mano y **no envían correo de verificación**. Con el
  valor contrario, el 403 del login dejaría fuera al admin bootstrap y con él a
  toda instalación en marcha. Solo `registrar_usuario` pasa `False`.
- **El `jti` se reclama por clave primaria, no leyendo antes.** Comprobar y luego
  insertar dejaba una ventana en la que dos peticiones con el mismo enlace pasaban
  las dos. Se reclama **antes** de aplicar el efecto: si el efecto fallara después,
  el token queda gastado sin servir, que es el lado seguro del error.
- **Los correos transaccionales van con `enlace_baja=None`.** Nadie debe poder
  darse de baja del mensaje que le permite activar la cuenta.
- **`EmailBody` usa `str` y no `EmailStr`.** En `/recuperar` y
  `/reenviar-verificacion` la dirección es solo una clave de búsqueda; exigir
  sintaxis de email metía un 422 que rompía la promesa de «200 siempre» y dejaba
  fuera al propio `admin@seis.local`, que `email-validator` rechaza por ser
  `.local` un dominio de uso especial (RFC 6762).

### Corregido tras la revisión de seguridad y de calidad

Seis hallazgos se arreglaron dentro de la propia fase, no se difirieron:

- **Confusión de audiencia entre tokens (HIGH).** `decodificar_token` era un
  `jwt.decode` genérico y los tokens de propósito se firman con **el mismo
  secreto** que los de sesión. Un enlace de verificación (24 h) o de reseteo (1 h)
  enviado por correo valía además como **Bearer de sesión completo** en cualquier
  endpoint protegido, heredando el rol real de la cuenta — y **seguía valiendo
  después de consumirse**, porque `token_consumido` solo lo consulta el camino de
  un solo uso, nunca `get_current_user`. Cerrado con un claim `tipo="sesion"` que
  `decodificar_token` exige como lista blanca. Defecto **anterior a esta fase**
  (nació con la Fase 12), pero la 10 multiplicaba su superficie. Efecto
  secundario: los tokens emitidos antes del cambio dejan de servir — un cierre de
  sesión único al desplegar.
- **DoS dirigido en el login (HIGH).** Regresión **introducida por esta fase**:
  con la clave del limitador solo por email, cualquiera dejaba fuera a un tercero
  con cinco contraseñas erróneas, indefinidamente y sin que la cuenta tuviera
  siquiera que existir; el bloqueo se comprueba antes que la contraseña, así que
  ni el titular legítimo entraba. Clave ahora compuesta por email **y** origen.
  Su efecto completo depende de la Fase 11 (ver deuda 1).
- **Carrera en el alta duplicada.** `registrar_usuario` comprobaba duplicidad y
  creaba después, sin bloqueo. En PostgreSQL con READ COMMITTED, dos registros
  simultáneos del mismo email pasaban ambos la comprobación; el segundo chocaba
  contra el `UNIQUE` y propagaba un `IntegrityError` **sin capturar** — un 500 en
  el endpoint cuyo contrato es «201 siempre»— y dejaba una organización huérfana.
  Resuelto con el mismo patrón que ya usaba `marcar_jti`.
- **`/verificar` quemaba el token sin intervención humana.** Se confirmaba en un
  `useEffect` al montar la página, de modo que cualquier escáner corporativo de
  enlaces, antivirus o previsualizador de correo gastaba el uso único antes que
  su destinatario. Ahora exige un clic explícito, como `/baja`.
- **Bombardeo de bandeja dirigido.** `/reenviar-verificacion` limitaba solo por
  origen. Añadida la clave por destinatario, igual que `/recuperar`.
- **Higiene de entrada.** `max_length` en `password`, `nueva`, `actual`, `token` y
  `nombre` (este último acotado a los 80 de la columna: sin tope, un valor más
  largo abortaba la transacción en PostgreSQL y salía como 500 en vez de 422). Y
  `obtener_por_email` recorta espacios, que en formularios públicos llegan al
  copiar del cliente de correo.

### Deuda que deja la Fase 10

1. **⛔ PUERTA DE DESPLIEGUE — la IP de origen no sobrevive a `docker compose`**
   *(propietario: Fase 11)*. Medido: todas las peticiones externas llegan con la
   IP de la pasarela (`172.18.0.1`), de modo que los límites por origen de
   `/registro` y `/reenviar-verificacion` funcionan como **un cupo global** —5
   altas cada 15 minutos en todo el sitio— en vez de uno por cliente, y la clave
   compuesta del login se comporta como si solo llevara el email.
   La revisión de seguridad pidió endurecer el encuadre y tiene razón: tal como
   está, **un solo atacante sin credenciales puede negar el alta pública a todo el
   sitio de forma sostenida** con un puñado de peticiones cada 15 minutos. No
   bloquea la fusión del código, pero **sí debe bloquear la exposición de este
   `docker-compose.yml` a Internet**: hasta que haya proxy inverso con
   `uvicorn --proxy-headers` y `--forwarded-allow-ips` acotado a ese proxy, este
   despliegue no sale a producción.
2. **`token_consumido` crece sin purga** *(propietario: Fase 11)*. Una fila por
   cada enlace de verificación o reseteo consumido, para siempre. Candidata a
   tarea beat que borre las anteriores al TTL máximo (30 días cubre los tres
   propósitos vigentes).
3. **Fuga por temporización en el login** *(propietario: Fase 16)*. `autenticar` y
   `autenticar_con_motivo` cortocircuitan si el email no existe, sin llegar a
   ejecutar PBKDF2 (240 000 iteraciones). La diferencia es medible y permite
   enumerar cuentas. Preexistente a esta fase; no se cerró para no ampliar el
   alcance. Cerrarlo exige comparar contra un hash señuelo.
4. **El reseteo no invalida las sesiones abiertas** *(propietario: Fase 16)*. No
   hay revocación de JWT ni refresh tokens: tras un reseteo, un token robado sigue
   sirviendo hasta 12 h. Mitigado en parte porque `get_current_user` recomprueba
   `activo` en cada petición.
5. **Retirado `test_t3_revision_aislada_via_stamp`** (barrera de la Fase 9.5).
   Era insostenible por construcción: creaba el esquema con
   `Base.metadata.create_all` —que produce siempre la forma de **HEAD**, nunca la
   de la revisión predecesora—, marcaba la predecesora con `stamp` y aplicaba
   encima la revisión bajo prueba, que entonces intentaba crear objetos ya
   existentes. Con la `0006`: `duplicate column name: email_verificado`. Nunca
   había llegado a ejecutarse porque el Bloque D dejó la cadena con una sola
   revisión y el caso se omitía por falta de pares. Su propósito original
   —«alcanzar la 0004 sin la 0002»— desapareció al sanearse la cadena. Lo que
   cubría lo cubre `test_t3_par_consecutivo_por_la_cadena_natural`, que ejerce el
   camino real y pasa con 0005→0006.
6. **Canal de temporización en `/recuperar`** *(propietario: Fase 16)*. El cuerpo
   y el código de respuesta son idénticos exista o no la cuenta —hay test que lo
   fija—, pero **la latencia no**: si hay proveedor de correo configurado, el
   camino «existe» hace una petición HTTP real o abre una conexión SMTP y el
   camino «no existe» retorna al instante. Medir el tiempo permite distinguirlos,
   que es justo lo que D5 quiso impedir. Se cierra encolando el envío en Celery,
   que el proyecto ya usa, en vez de enviarlo dentro de la petición.
7. **El limitador no reintenta Redis tras el primer fallo** *(propietario: Fase 11)*.
   `_cliente_redis` se cachea como `False` en cuanto falla el primer `ping()` del
   proceso y no se vuelve a intentar en toda su vida. `docker-compose.yml` cubre
   el arranque con `depends_on: condition: service_healthy`, pero una caída de
   Redis posterior degrada a memoria de forma silenciosa y **permanente** hasta
   reiniciar — y con `--workers 2` eso duplica el límite efectivo.
8. **Las cuatro páginas públicas nuevas duplican estructura** *(propietario: Fase 15)*.
   `/registro`, `/verificar`, `/recuperar` y `/resetear` repiten envoltorio,
   cabecera, máquina de estados y bloque de éxito, y `/login` y `/baja` ya lo
   hacían antes. Candidato a un `<PaginaPublica>` compartido en `components/`.
   Se deja para la Fase 15, que rehace la capa pública con la landing.
9. **Sin CAPTCHA ni lista de contraseñas comunes en `/registro`**
   *(propietario: Fase 16)*. El mínimo de 8 caracteres no comprueba contra
   contraseñas frecuentes, que es lo que NIST 800-63B recomienda por encima de las
   reglas de composición. La única barrera anti-automatización es el limitador.
10. **Las cuentas registradas y nunca verificadas no caducan**
   *(propietario: Fase 11)*. Mismo patrón que la deuda 2: candidatas a la misma
   tarea de purga periódica.
11. **El JWT de sesión vive en `localStorage`** *(propietario: Fase 16, preexistente)*.
   `frontend/lib/api.ts`. Cualquier XSS expondría la sesión completa, lo que
   amplificaría las deudas 3 y 4. No lo introduce esta fase; se anota porque la
   revisión de seguridad lo señaló como amplificador de los otros hallazgos.
12. **`/auth/cambiar-password` no tiene interfaz** *(propietario: SIN ASIGNAR)*.
   El endpoint existe, está probado y tiene el 96 % de cobertura, pero
   `api.cambiarPassword` **no lo invoca ningún componente**: no hay página de
   cuenta y `construirNav` no tiene entrada para ella. Consecuencia concreta: el
   propietario de una organización asigna una «Contraseña temporal» en `/equipo`
   y su titular **no puede cambiarla desde la aplicación**. No incumple el
   contrato —el cambio de contraseña autenticado no figura entre los seis pasos
   del §Fase 10 del Plan Maestro—, pero debe asignarse fase antes de admitir
   usuarios reales. Candidata natural: Fase 15, que rehace la capa pública.

---

<details>
<summary>Plan original de la Fase 10 (histórico, anterior a las Fases 12 y 9.5)</summary>

### Punto a confirmar antes de codificar
- ~~**`email_service.py` como abstracción honesta sin proveedor real**~~ →
  **RESUELTO por la Fase 12**: ya existe `app/notificadores/` con esa misma
  abstracción (interfaz común, Postmark/SES/SMTP y buffer `ultimo_email` sin
  credenciales). La Fase 10 debe **reutilizarlo**, no crear un `email_service.py`
  paralelo; las referencias de más abajo a ese fichero quedan obsoletas.
- `crear_token_proposito` / `decodificar_token_proposito` **ya existen** en
  `app/core/security.py` (los introdujo la Fase 12 para el enlace de baja).
  Falta solo la tabla `TokenConsumido` para el uso único por `jti`.

### Reconciliación con la realidad del repo (el prompt asumía otro estado)
- Migración nueva = **0006**. (La Fase 9.5 retiró las revisiones 0001-0004 y las sustituyó por la fundacional única **`0005`**, con `down_revision = None`, de modo que la siguiente libre es la **`0006`**. La Fase 13 toma la **`0007`**, con `down_revision = "0006"`. Cualquier nota anterior que reserve la `0005` para la Fase 10 está derogada.)
- `email_service.py` **no existe** → se crea.
- Rate-limiting: Redis **con fallback a memoria** en tests.

### Cambios previstos, fichero a fichero

**Backend — modelos y migración**
- `app/models.py`: `Usuario` += `email_verificado: bool` (default False). Nueva tabla
  `TokenConsumido(jti PK, proposito, consumido_en)` (uso único de tokens).
- `alembic/versions/0006_self_service.py` (idempotente + reversible): add column
  `usuario.email_verificado` (backfill: usuarios existentes → `True`); create table
  `token_consumido`. `downgrade` elimina ambos.

**Backend — seguridad, email y rate-limit**
- `app/core/security.py`: `crear_token_proposito(sub, proposito, horas)` (con `jti`,
  `proposito`, `exp`) y `decodificar_token_proposito(token, proposito)`.
- `app/services/email_service.py` (nuevo): `enviar_email(...)` honesto + helpers
  `enviar_verificacion` / `enviar_reseteo` (enlace `{FRONTEND_URL}/verificar?token=…`);
  buffer de último email para tests.
- `app/core/rate_limit.py` (nuevo): `registrar_fallo`, `bloqueado`, `limpiar`,
  `limpiar_todo`. Redis con fallback a memoria; ventana 15 min / máx 5 (configurable).
- `app/core/config.py`: += `frontend_url`, `email_from`, `login_max_intentos=5`,
  `login_ventana_min=15`.

**Backend — servicios y endpoints**
- `app/services/usuario_service.py`: `registrar_usuario(...)` (crea Organizacion propia
  + Usuario propietario inactivo: `activo=False`, `email_verificado=False`, `rol="admin"`,
  `rol_org="propietario"`, `es_superadmin=False`); `verificar_email(...)`;
  `resetear_password(...)`; `jti_consumido(...)` / `marcar_jti(...)`. Todo con `Auditoria`.
- `app/api/auth.py` (endpoints nuevos, públicos):
  - `POST /auth/registro` {email, password≥8, nombre} → 201, envía verificación.
  - `POST /auth/verificar` {token} → activa cuenta (propósito "verificar", 24 h, un solo uso).
  - `POST /auth/recuperar` {email} → **respuesta idéntica exista o no** el email; si existe, envía reseteo (1 h).
  - `POST /auth/resetear` {token, nueva≥8} → cambia contraseña (propósito "resetear", un solo uso).
  - `POST /auth/login` → envuelto en anti-fuerza-bruta: ≥5 fallos/email/15 min ⇒ **429** en español; éxito limpia el contador.
  - Validación `≥8` con Pydantic (`Field(min_length=8)`).

**Frontend (páginas públicas, hermanas de `/login`)**
- `app/registro/page.tsx`, `app/verificar/page.tsx` (lee `?token=`),
  `app/recuperar/page.tsx`, `app/resetear/page.tsx` (lee `?token=`). Botones
  deshabilitados durante el envío; textos en español.
- `app/login/page.tsx`: enlaces a `/registro` y `/recuperar`.
- `lib/api.ts`: `registro`, `verificar`, `recuperar`, `resetear`.

**Tests**
- `tests/conftest.py`: fixture autouse `rate_limit.limpiar_todo()` por test.
- `tests/test_registro.py`: registro feliz (usuario inactivo, email capturado);
  email duplicado → 400; verificar OK → login funciona; token caducado → 400;
  token reutilizado (jti) → 400; token con propósito equivocado → 400; recuperar
  idéntico exista/no exista el email; resetear feliz; login brute-force
  (5 fallos → 6º = 429) y desbloqueo temporal (envejeciendo timestamps vía hook de reloj).

**No se toca:** `app/engine/**` ni la gobernanza salvo lo listado.

</details>

---

## ⏳ Fases 11-20 — no iniciadas

Resumen (detalle y prompts de ejecución en `docs/SEIS_Plan_Maestro_Fases_920.md`):

| Fase | Nombre | Notas |
|---|---|---|
| 11 | Infraestructura de producción | render.yaml, health por componente, Sentry, runbook. **Hereda de la Fase 10:** proxy inverso que conserve la IP de origen (hoy el límite por IP es un cupo global) y purga de `token_consumido` |
| ~~12~~ | ~~Notificaciones multicanal + scoring~~ | ✅ **Completada** — ver sección propia más abajo |
| 13 | Monetización (Stripe) | planes/límites, webhooks idempotentes |
| 14 | Cumplimiento legal y RGPD | consentimientos, ARCO, textos legales (revisión de abogado) |
| 15 | Landing pública, onboarding y ayuda | — |
| 16 | Endurecimiento de seguridad | OWASP, rate-limit global, cabeceras |
| 17 | Escalado de la captación (BOE real) | ajuste del conector contra el portal real |
| 18 | Canal WhatsApp (condicional) | solo si Fase 12 demuestra demanda |
| 19 | Analítica y panel de negocio | Plausible/PostHog, embudo, MRR |
| 20 | Beta cerrada y lanzamiento | QA guionizado, carga, go-live |

### Deuda técnica menor detectada
- ~~No existe `.env.example` en la raíz del repo~~ → **creado en la Fase 12** con
  todas las variables reales, incluidas las de notificaciones.
- Endpoints citados en prompts que aún no existen y que deberán heredar el scoping
  por `organizacion_id` cuando se creen: `export.csv`, `geo`, `resultado-real`, `/calibracion`.

### 🐛 Deuda técnica detectada durante la Fase 12 (NO corregida — decisión pendiente)
- **`pdf_service.py` rompe sin la fuente DejaVu.** `tests/test_pdf_async.py::test_informe_pdf`
  y `test_multitenant.py::…[/informe.pdf]` fallan con `FPDFUnicodeEncodingException`
  cuando `DejaVuSans.ttf` no está instalada (p. ej. Windows local). El fallback a
  *helvetica* llama a `_limpiar(texto, unicode_ok=False)`, que no translitera todos
  los caracteres del informe. En Docker no se manifiesta porque la imagen incluye
  `fonts-dejavu-core`. **Preexistente a la Fase 12** (verificado sobre árbol limpio).
  Arreglo propuesto: completar la tabla de transliteración de `_limpiar`. Toca
  `pdf_service.py`, fuera del alcance de la 12 → requiere aprobación.

---

## ✅ Fase 12 — Notificaciones multicanal y scoring exprés (COMPLETADA)

**Decisiones tomadas (aprobadas antes de codificar):**
1. **Telegram por polling** (tarea Celery `seis.telegram_polling`, cada 30 s) en lugar
   de webhook: no exige URL pública HTTPS, que es Fase 11. El procesado del mensaje
   vive en `procesar_update(db, update)`, así que migrar a webhook es llamar a esa
   función desde el endpoint.
2. **Email honesto sin credenciales**: `EMAIL_PROVIDER=postmark|ses|smtp`; vacío ⇒
   log + buffer `ultimo_email` (los tests lo inspeccionan). Nunca lanza.
3. **Scoring fuera del DAG**: `app/engine/scoring_expres.py`, hermano de `pipeline.py`,
   NO en `modules/`. El caso dorado §19 queda intacto.
4. **Prerequisitos mínimos creados aquí** (no existían): modelos `Alerta`/`Notificacion`,
   router `captacion.py`, páginas `/alertas` y `/subastas`.

**Entregado:** migraciones `0003` (4 tablas) y `0004` (amplía `auditoria.quien` a 120).
> **Corrección (Fase 9.5, Bloque J).** Esta nota afirmaba que ambas tenían «upgrade/downgrade
> verificados en SQLite». Es **falso para la `0004`**: usaba `op.alter_column` (líneas 25 y 30), y
> SQLite no implementa `ALTER TABLE ... ALTER COLUMN` —medido: `OperationalError: near "ALTER":
> syntax error`—, de modo que **no podía ejecutarse en SQLite en ningún caso**. Solo
> `op.batch_alter_table()` funciona ahí; `render_as_batch` no lo arregla (ver `CLAUDE.md` §6.11).
> Ambas revisiones fueron **retiradas** por la Fase 9.5 y sustituidas por la fundacional `0005`; su
> contenido permanece en el historial de git. El ensanchamiento de `auditoria.quien` a `String(120)`
> sigue vigente: viaja dentro de la `0005`, verificado en PostgreSQL real (`quien VARCHAR(120)`).
`app/notificadores/` (base + email + telegram + registro); `notificaciones_service.py`;
routers `notificaciones.py` (+ `/alertas`) y `captacion.py`; tareas `seis.digest`
(beat horario) y `seis.telegram_polling`; parámetros T3 `scoring_expres` editables;
páginas `/alertas` (Alertas + Preferencias), `/subastas` y `/baja` (pública);
`test_notificaciones.py` (18 tests).

**Reparado de paso (bloqueaba la fase):** `docker-compose.yml` era **YAML inválido**
desde el commit de importación inicial — a partir de `volumes:` contenía una copia
antigua duplicada de db/redis/backend/worker. `docker compose up` nunca pudo funcionar
pese a estar documentado como vía principal de arranque. Se eliminó el duplicado y se
añadió `--beat` al worker (sin él, digest y polling nunca se ejecutan).

### P1 detectados en Fase 12 (Release Committee)

- **Proveedores SES y SMTP no funcionales vía `docker compose up`.** `docker-compose.yml`
  propaga `POSTMARK_TOKEN` pero **no propaga** `SES_REGION`, `SES_ACCESS_KEY`, 
  `SES_SECRET_KEY`, `SMTP_HOST`, `SMTP_PUERTO`, `SMTP_USUARIO`, `SMTP_PASSWORD`. 
  Con `EMAIL_PROVIDER=ses` o `smtp` dentro del contenedor, las credenciales llegan 
  vacías y `NotificadorEmail.disponible()` devuelve False; el sistema cae silenciosamente 
  en la rama sin proveedor. El diagnóstico es engañoso (*«Email sin proveedor configurado»*
  cuando el operador sí configuró uno). No compromete seguridad ni rompe tests (el 
  email de prueba funciona), pero notificaciones desaparecen silenciosamente en 
  producción. **Tarea Fase 11**: detectar y propagar las 7 variables de SES/SMTP 
  en compose y documentación.

### P2 detectados en Fase 12 (Release Committee)

- **Desglose de tests incorrecto en `CLAUDE.md:40`.** El total es correcto (104), pero
  dos cifras de desglose están erradas:
  - `test_seguridad_arranque.py`: documento dice 14, realidad es **27**
  - `test_multitenant.py`: documento dice 7, realidad es **10**
  - La suma del desglose total es 88, no 104.
- **Cifra de `test_notificaciones.py` errónea en `docs/PENDIENTES.md:139` (línea anterior)**:
  documento decía 15 tests, realidad es **18**. Corregido en esta edición.

> **Resuelto en la Fase 9.5 (Bloque J):** el desglose por fichero de `CLAUDE.md` §3 se retiró en vez
> de corregirlo cifra a cifra — era una lista que se desactualizaba en cada fase y cuya suma nunca
> cuadró. Queda solo el total, con la fecha de medición y la orden que lo produce.

---

## Deuda de la Fase 9.5 sin bloque propietario

Registrada en el Bloque J. El plan canónico de la Fase 9.5 **no asigna propietario** a ninguna de
las cuatro, de modo que no se les inventa uno: quedan aquí hasta que alguien las priorice. Ninguna
bloquea el cierre de la fase; las cuatro son mejoras de la barrera anti-recurrencia, no defectos del
esquema.

1. **`env.py` no filtra los objetos de extensión, y eso deja `alembic check` inservible contra
   PostGIS.** Medido en el Bloque F sobre la base ya migrada: informa `New upgrade operations
   detected` con **74 `remove_table` y 56 `remove_index`**; verificadas una a una, las 38 tablas
   señaladas (`loader_lookuptables`, `tiger`, `zip_lookup`, `spatial_ref_sys`, `topology`…) son
   **todas de las extensiones** y **ninguna es de SEIS**. No hay ni una operación `add_*` ni
   `modify_*`: **no existe deriva del esquema**, solo ruido. Arreglo: `include_object` en
   `context.configure()` de `alembic/env.py`. Mientras tanto, la barrera real de deriva es T4, que
   sí funciona.
2. **T4 compara los índices por nombre.** `_describir_esquema()` recoge `sorted(i["name"] …)`: una
   mutación que cambiara las columnas de un índice **conservando su nombre** no se detectaría. Las
   otras cuatro dimensiones (tablas, columnas, tipos, nulabilidad) sí están demostradas por la
   prueba de mutación del Bloque G.
3. **La prueba de mutación de T4 se ejecuta a mano.** El Bloque G la ejecutó (5/5 dimensiones) y el
   Bloque I demostró que el pipeline pasa a `exit 1` ante deriva real, pero ninguna de las dos está
   automatizada como test permanente. RC-3 exige «T4 en CI» —cubierto— pero no la mutación.
4. **La CI cubre solo `tests/test_migraciones.py`, no la suite completa.** Decisión deliberada del
   Bloque I: la suite arrastra dos fallos preexistentes de PDF que dejarían el pipeline
   permanentemente en rojo, y una barrera siempre roja no vigila nada. Ampliarla exige instalar
   `fonts-dejavu-core` en el runner —el `Dockerfile` ya lo hace—, lo que probablemente resolvería
   también esos dos rojos.

**Observaciones de otras fases detectadas de paso** (no de la 9.5, no se tocan aquí):
`docker-compose.yml` conserva `version: "3.9"`, obsoleto en Compose v5 · `backend` (8000) y
`frontend` (3000) se publican en todas las interfaces mientras `db` y `redis` van a `127.0.0.1` con
comentario explícito — **a confirmar en la auditoría de seguridad de la Fase 16** ·
`Settings.env_file=".env"` es una ruta relativa: ejecutar `pytest` desde la raíz del repositorio
haría que la suite leyera el `.env` real · el docstring de `app/models.py` (líneas 3-5) sigue
anunciando la migración a `geometry(Point,4326)` «con el módulo de mapa (Fase 5)», que no ha
ocurrido; no se corrigió porque el Bloque J no autoriza tocar modelos.

---

## Observación de arquitectura

Durante la Fase 9.5 se detectó una posible ambigüedad en `CLAUDE.md` §6.7 respecto al significado
de «fusionar».

Se analizaron tres alternativas (RFC-A, RFC-B y RFC-C).

**No se modifica la gobernanza durante esta fase.**

La decisión se pospone para una futura revisión del protocolo, al no afectar a la validez técnica
de la Fase 9.5.
