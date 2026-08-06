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

1. ~~**⛔ PUERTA DE DESPLIEGUE — la IP de origen no sobrevive a `docker compose`**~~
   → ✅ **CERRADA por la Fase 11, Bloque H.** `app/core/red.py` resuelve la IP real
   solo tras un par TCP declarado de confianza, tomando el N-ésimo por la derecha
   con N fijo y exigiendo que la cola sean proxies conocidos. Guardia de arranque
   que **aborta en entornos estrictos** si nadie se pronuncia, con `ninguno` como
   salida legítima; `--no-proxy-headers` explícito para que uvicorn no reescriba
   el par TCP por su cuenta.
   > **La puerta sigue cerrada hasta que el despliegue la abra bien.** El código
   > deja de ser el impedimento, pero declarar de confianza la pasarela de Docker
   > con el puerto publicado en `0.0.0.0` es **peor que no tener el bloque**:
   > cualquiera llegaría con la IP de la pasarela y elegiría su propia identidad.
   > Ver los avisos de `.env.produccion.example`.

   *(Texto original, conservado por ser el registro de lo medido en la Fase 10:)*
   Medido: todas las peticiones externas llegan con la
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
2. ~~**`token_consumido` crece sin purga**~~ → ✅ **CERRADA por la Fase 11, Bloque I.**
   Tarea beat `seis.purgar`, diaria y con horario `crontab`. Retención por
   defecto de **45 días**, configurable, y el arranque **aborta** si se baja por
   debajo del TTL real.
   > La propuesta original decía «30 días cubre los tres propósitos vigentes».
   > Es **incorrecta por partida doble**, y conviene dejarlo escrito porque el
   > razonamiento importa más que el número: (a) el token de baja dura
   > exactamente `24 * 30` horas, así que 30 días dejaría **margen cero**; y (b),
   > más importante, **ese token nunca entra en la tabla**: `marcar_jti` tiene un
   > único llamante (`app/api/auth.py`), que sirve a `/verificar` y `/resetear`,
   > mientras que `/notificaciones/baja` decodifica y aplica sin reclamar el
   > `jti`. El TTL máximo que sí llega es el de verificación, **24 horas**.
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
7. ~~**El limitador no reintenta Redis tras el primer fallo**~~ → ✅ **CERRADA por la
   Fase 11, Bloque I.** Retroceso exponencial acotado (1 s → 30 s), y un fallo de
   **operación** —no solo de conexión— suelta el cliente: sin eso, un Redis que
   muere a mitad de vida dejaba a cada petición pagando su timeout. El retroceso
   se reinicia tras una operación correcta y no tras el `ping`, porque un Redis
   que responde al `PING` pero rechaza escrituras (memoria agotada, réplica en
   solo lectura) mantenía el ciclo en un segundo indefinidamente.
   > Cerrarla destapó un segundo defecto, **ya corregido en el mismo bloque**:
   > los dos almacenes no se sincronizan, de modo que un parpadeo de Redis
   > **levantaba los bloqueos vigentes**. Se anota siempre en ambos y se lee en
   > OR, pero **solo mientras la degradación sea reciente**: con Redis sano manda
   > Redis, porque `limpiar()` borra la clave global y de la memoria solo la del
   > proceso que atiende, y con `--workers 2` consultar la memoria siempre haría
   > que un acceso correcto dejara de desbloquear.
8. **Las cuatro páginas públicas nuevas duplican estructura** *(propietario: Fase 15)*.
   `/registro`, `/verificar`, `/recuperar` y `/resetear` repiten envoltorio,
   cabecera, máquina de estados y bloque de éxito, y `/login` y `/baja` ya lo
   hacían antes. Candidato a un `<PaginaPublica>` compartido en `components/`.
   Se deja para la Fase 15, que rehace la capa pública con la landing.
9. **Sin CAPTCHA ni lista de contraseñas comunes en `/registro`**
   *(propietario: Fase 16)*. El mínimo de 8 caracteres no comprueba contra
   contraseñas frecuentes, que es lo que NIST 800-63B recomienda por encima de las
   reglas de composición. La única barrera anti-automatización es el limitador.
10. ~~**Las cuentas registradas y nunca verificadas no caducan**~~ → ✅ **MECANISMO
   ENTREGADO por la Fase 11, Bloque I; BORRADO DESACTIVADO por defecto.**
   `app/services/purga_service.py`, con predicado de nueve condiciones, borrado
   ordenado (ninguna clave foránea declara `ondelete` y `Usuario` no tiene
   `relationship()`, así que no hay cascada de ningún tipo) y revalidación bajo
   bloqueo para cerrar la carrera con `/verificar`.
   > **`PURGA_CUENTAS_MODO=informar` de fábrica**: cuenta las candidatas, lo
   > registra y **no borra nada**. Un borrado irreversible no debe ser el
   > comportamiento por defecto de algo que aún no se ha visto correr contra
   > datos reales. Activarlo es una variable de entorno.
   >
   > **Queda abierto lo operativo**: nadie ha mirado todavía un informe real, así
   > que **la deuda no está cerrada en producción hasta que alguien active el
   > modo `borrar` con evidencia delante**. Propietario de ese paso: quien
   > despliegue.
   >
   > Hallazgo de paso, que eleva esto de higiene a defecto funcional: una cuenta
   > zombi **secuestra la dirección de correo indefinidamente**, porque
   > `registrar_usuario` no crea nada si el email existe y el endpoint responde
   > 201 neutro. Hoy cualquiera puede registrar la dirección de un tercero, no
   > verificarla nunca y **negarle el alta a su titular para siempre**.
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

## ⏳ Fases 11-20 — la 11 en curso, el resto no iniciadas

Resumen (detalle y prompts de ejecución en `docs/SEIS_Plan_Maestro_Fases_920.md`):

| Fase | Nombre | Notas |
|---|---|---|
| 11 | Infraestructura de producción | 🔄 **EN CURSO** (rama `fase-11-infraestructura`). Partida en **11-A** (agnóstica del proveedor: bloques A ✅, C′ ✅, D ✅, E, F′, H, I) y **11-B** (dependiente del proveedor: IaC, jobs de despliegue, RUNBOOK — bloqueada por H1/H2/H6). **Sentry NO forma parte de la fase**: quedó fuera por decisión del responsable (H5) y no tiene fase propietaria — ver la deuda abierta más abajo. **Hereda de la Fase 10:** proxy inverso que conserve la IP de origen (Bloque H, **pendiente**) y las tres deudas del **Bloque I ✅** (purga de `token_consumido`, reintento de Redis en el limitador y caducidad de las cuentas nunca verificadas, esta última con el borrado desactivado de fábrica) |
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
  cuando `DejaVuSans.ttf` no está instalada (p. ej. Windows local). En Docker no se
  manifiesta porque la imagen incluye `fonts-dejavu-core`. **Preexistente a la
  Fase 12** (verificado sobre árbol limpio).

  > ⚠️ **DIAGNÓSTICO CORREGIDO EN LA FASE 11 (Bloque C′).** Esta nota afirmaba que
  > «el fallback a *helvetica* llama a `_limpiar(texto, unicode_ok=False)`, que no
  > translitera todos los caracteres del informe», y proponía «completar la tabla de
  > transliteración de `_limpiar`». **Las dos cosas son falsas.**
  >
  > `_limpiar` translitera correctamente: hace `texto.encode("latin-1", "replace")`
  > (`pdf_service.py:22`), que por construcción no deja pasar ningún carácter fuera
  > de latin-1. No hay ninguna «tabla» que completar.
  >
  > La excepción medida es `UnicodeEncodeError: 'latin-1' codec can't encode
  > character '•' in position 2`. El carácter entra **por fuera del saneador**,
  > concatenado como literal en `pdf_service.py:89`:
  > `pdf.multi_cell(0, 5, "  •  " + _limpiar(...))`. En `"  •  "` el índice 2 es
  > U+2022 (viñeta), que coincide exactamente con la «position 2» del error.
  >
  > **El arreglo es una línea**, no una tabla: elegir la viñeta según
  > `pdf.unicode_ok` (`"  •  "` / `"  -  "`), o meter el prefijo dentro de
  > `_limpiar`. Sigue tocando `pdf_service.py`, fuera de `app/engine/`, y **sigue
  > requiriendo aprobación** (CLAUDE.md §7).
  >
  > **Aviso para el Bloque F′:** instalar `fonts-dejavu-core` en el runner pondrá la
  > CI en verde, y por eso es la peor opción **si se hace sola**: con la fuente
  > presente el código toma la rama `unicode_ok=True` y la rama de fallback queda
  > rota para siempre y además sin cobertura. Y esa rama es la que corre en toda
  > máquina de desarrollo Windows (`_DEJAVU` es una ruta POSIX absoluta,
  > `pdf_service.py:14`) y en cualquier imagen de hosting que no sea el
  > `backend/Dockerfile` del proyecto — es decir, el terreno abierto de la Fase 11-B.
  > Hace falta además un test que fuerce `unicode_ok=False`.

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

> ✅ **CERRADO por la Fase 11, Bloque C′** (rama `fase-11-infraestructura`). Las siete
> variables llegan ya a `backend`, `worker` **y** al nuevo servicio `beat`. Verificado
> ejecutando `docker compose config`: **7/7 presentes en los tres servicios**.
>
> La corrección no fue añadir siete líneas. La causa raíz era tener **dos bloques
> `environment` duplicados que derivaron el uno del otro**; añadirlas a mano habría
> dejado el mismo mecanismo intacto para la próxima variable. El entorno común vive
> ahora en un **ancla YAML** (`x-entorno-aplicacion`) que los tres servicios comparten,
> de modo que la deriva es estructuralmente imposible. Lo vigila
> `backend/tests/test_despliegue.py`, que lee el compose con las anclas ya resueltas y
> falla si algún servicio de aplicación se queda sin alguna de las siete.

- ~~**Proveedores SES y SMTP no funcionales vía `docker compose up`.**~~ `docker-compose.yml`
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

## Deuda abierta por la Fase 11 — alcance de la fase

1. **⛔ Sentry: requisito del contrato NO entregado** *(propietario: **SIN ASIGNAR**)*.
   El requisito 2 del prompt del Plan Maestro para la Fase 11 pide instrumentar
   Sentry en backend y frontend, activado solo si existe `SENTRY_DSN`. **Queda
   fuera de la fase por decisión del responsable (H5).** No es un olvido ni un
   pendiente menor: es un **incumplimiento deliberado y declarado** del contrato
   de la fase. La huella completa es una variable `SENTRY_DSN` declarada y vacía
   en `.env.example` y en `.env.produccion.example`, sin dependencia instalada y
   sin una sola línea de código que la lea.
   **Consecuencia asumida, escrita para que nadie la descubra tarde: mientras
   siga así, un error 500 en producción no avisa a nadie.** La única traza es el
   log del proceso, que hay que ir a mirar. **No se le inventa fase propietaria.**
2. **Toda la Fase 11-B** *(propietario: Fase 11-B, bloqueada por H1, H2 y H6)*.
   IaC del proveedor, jobs de despliegue con aprobación manual, `docs/RUNBOOK.md`,
   runbooks temáticos del Vault y el ADR de elección de hosting. **Sin proveedor,
   dominio ni proveedor de correo decididos, no se puede escribir un runbook que
   no sea ficción.** Los criterios de salida de la fase son operativos y ninguno
   es alcanzable sin esto: **la Fase 11 no se cierra al fusionar la 11-A.**

## Deuda abierta por la Fase 11, Bloque C′ (higiene de despliegue)

Registrada tras las revisiones independientes de seguridad y de pruebas. Lo que se
corrigió dentro del propio bloque no figura aquí; esto es lo que **queda abierto**.

1. **`worker` y `beat` cargan `ADMIN_PASSWORD` sin usarlo** *(propietario: Fase 16)*.
   Esa variable la consume una sola ruta de código —`scripts/init_db.py`, la siembra
   del admin bootstrap— y **solo la ejecuta el backend**. El worker y el beat la
   llevan únicamente porque `app/tasks/celery_app.py` invoca `get_settings()` al
   importarse y la guardia exige ambos secretos: **sin ella no arrancan** en un
   entorno estricto. Medido y verificado. No es una credencial menor: es la del
   usuario `es_superadmin`, que gobierna el conocimiento T2/T3 global. Cerrarlo
   exige desacoplar la guardia (exigir `admin_password` solo al proceso que vaya a
   sembrar), no basta con quitar la variable del ancla.
2. **SMTP solo soporta STARTTLS; el puerto 465 falla en silencio** *(propietario: Fase 16
   o la fase que fije proveedor de correo)*. `app/notificadores/email.py` implementa
   únicamente `smtplib.SMTP` + `starttls()`. Si el proveedor exige 465 (TLS
   implícito) y el operador pone `SMTP_PUERTO=465`, se abre en claro contra un
   puerto que espera un ClientHello, salta la excepción y `email.py` **se la traga**
   devolviendo `False`: la API sigue respondiendo 201/200 y el correo no sale. Es
   exactamente el fallo mudo que el Bloque C′ vino a cerrar, entrando por la puerta
   del puerto. Arreglo: ramificar por puerto (`SMTP_SSL` en 465) y validar
   `smtp_puerto in (25, 465, 587, 2525)` en `config.py`.
   > La validación del certificado **sí se corrigió** en este bloque:
   > `starttls()` sin contexto usaba `CERT_NONE` y `check_hostname=False`, de modo
   > que cualquier certificado autofirmado completaba el handshake y un atacante en
   > la red capturaba las credenciales SMTP y los enlaces de verificación y reseteo.
   > Ese camino era inalcanzable bajo Docker hasta que este bloque propagó las
   > credenciales, así que se cerró en el mismo movimiento que lo activó.
3. **La imagen corre como `root` y sin endurecimiento** *(propietario: Fase 16)*.
   `backend/Dockerfile` no declara `USER`, y `docker-compose.yml` no declara `user:`,
   `read_only`, `cap_drop`, `security_opt: no-new-privileges` ni límites de recursos.
   El plan de la Fase 11 lo contemplaba con la condición explícita de que, si no daba
   tiempo, **se dejara fuera y se anotara**. Queda anotado.
4. **`beat` no debe escalarse nunca, y nada en el código lo impide** *(propietario:
   runbook de la Fase 11-B)*. `docker compose up --scale beat=2` devuelve entera la
   duplicación del digest que la separación vino a cerrar. Hay un test que impide
   declarar `deploy.replicas > 1` en el fichero, pero no puede impedir una bandera
   en la línea de órdenes.
5. **Un `unhealthy` del backend se diagnostica en el sitio equivocado** *(propietario:
   runbook de la Fase 11-B)*. Compose v2 no reinicia por `unhealthy`; lo que ocurre es
   que `frontend`, que espera `condition: service_healthy`, aborta con «dependency
   failed to start» **señalando al frontend** cuando el problema está en la migración
   del backend.
6. **`beat` no persiste su `celerybeat-schedule`** *(propietario: runbook de la Fase 11-B)*.
   El `PersistentScheduler` por defecto lo escribe en el CWD del contenedor
   (`/srv/seis`), que es capa efímera: cada `up --build` o recreación lo pierde y
   una entrada nueva arranca con `last_run_at = now`, de modo que el digest
   horario vuelve a esperar una hora completa. Con `restart: unless-stopped` el
   riesgo baja mucho, pero en una sesión de despliegue con varias recreaciones
   seguidas el digest puede no llegar a dispararse. Arreglo: `--schedule=` a un
   volumen nombrado.
7. **La suite entera corre SIN integridad referencial** *(propietario: SIN ASIGNAR;
   preexistente, medido en la Fase 11, Bloque I)*. En SQLite las claves foráneas
   están **desactivadas por defecto** y `app/core/db.py` no ejecuta
   `PRAGMA foreign_keys=ON` en ninguna parte. Medido: `PRAGMA foreign_keys` → `0`.
   Consecuencia: **cualquier borrado desordenado pasa en verde en la suite y deja
   filas huérfanas, mientras en PostgreSQL abortaría la transacción.** Es la
   misma clase de falso verde que esta fase ya ha corregido tres veces. Hoy solo
   lo cubre `test_la_purga_no_deja_filas_huerfanas_con_claves_foraneas_activas`,
   que lo activa para su propio caso y lo restaura al salir.
   Ojo al activarlo globalmente: el PRAGMA es **por conexión** y la conexión
   vuelve al pool, de modo que activarlo en un test se filtra a los siguientes y
   convierte sus fallos en dependientes del orden (medido). La vía correcta es un
   listener `connect` sobre el motor, no una llamada suelta.
8. **La suite no es idempotente ante un `seis_dev.db` superviviente** *(propietario:
   SIN ASIGNAR; preexistente, detectado de paso en la Fase 11)*. La fixture `api`
   borra el fichero en su teardown, pero en Windows ese borrado puede fallar con
   `PermissionError: [WinError 32]` si alguna conexión sigue abierta. Cuando eso
   ocurre, el fichero sobrevive con el admin ya sembrado y **los módulos siguientes
   fallan con `UNIQUE constraint failed: usuario.email`**, un mensaje que no apunta
   en absoluto a la causa. Reproducido: 8 fallos y 6 errores que desaparecen sin
   tocar una línea de código, solo borrando el fichero. Arreglo natural: base en
   memoria (`sqlite:///:memory:`) o fichero temporal por sesión, en vez de un
   `seis_dev.db` fijo en el directorio de trabajo.

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
4. ~~**La CI cubre solo `tests/test_migraciones.py`, no la suite completa.**~~ → ✅ **CERRADA
   por la Fase 11, Bloque F′.** Nuevo `.github/workflows/ci.yml` con la suite completa y
   `npm run build`, instalando `fonts-dejavu-core` en el runner igual que el `Dockerfile`.
   `migraciones.yml` se conserva intacto: es la barrera específica de la Fase 9.5.
   > ⚠️ **Un verde en CI NO significa que el PDF funcione sin la fuente.** Con
   > `fonts-dejavu-core` instalada el código toma la rama `unicode_ok=True`, de modo que la
   > rama de respaldo —la única que corre en cualquier máquina o imagen sin la fuente,
   > incluido todo Windows de desarrollo— queda **rota y además sin cobertura**. El defecto
   > sigue abierto y su causa raíz está identificada más abajo (un literal fuera del
   > saneador, no una tabla de transliteración). Cerrarlo exige tocar `pdf_service.py`,
   > fuera del alcance de esta fase, y **requiere aprobación explícita**.

**Observaciones de otras fases detectadas de paso** (no de la 9.5, no se tocan aquí):
~~`docker-compose.yml` conserva `version: "3.9"`~~ → **resuelto en la Fase 11 (Bloque C′)**: retirada ·
~~`backend` (8000) y `frontend` (3000) se publican en todas las interfaces~~ → **resuelto en la
Fase 11 (Bloque C′)**: ambos pasan a `${BIND_*:-127.0.0.1}`, loopback por defecto, simétrico con
`db` y `redis`. Se adelantó a la Fase 16 porque la premisa del diferimiento —«el compose es solo
local»— caducó al convertirse este fichero en la base de un despliegue portable ·
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
