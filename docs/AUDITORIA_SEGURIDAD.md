# Auditoría de seguridad — Fase 16

**Fecha:** 2026-09-10 · **Commit auditado:** `5fb3024` · **Modelo:** Opus 5
**Alcance:** backend (`backend/app`), frontend (`frontend`), CI, dependencias.
**Estado:** ✅ **parte 2 aplicada** (2026-09-10). Las 3 altas y las 7 medias
corregidas, cada una con demostración por mutación. Ver §7.

---

## 0 · Cómo leer esto

Cada hallazgo lleva **cómo se comprobó**. Donde dice «medido», hay un comando o
una batería detrás; donde dice «inferido», es lectura de código sin ejecución, y
está marcado como tal a propósito: la diferencia entre las dos cosas es lo que
distingue una auditoría de una opinión ordenada.

**Tres cosas que esta auditoría NO es:**

- No es una prueba de penetración. No hay despliegue contra el que lanzar nada,
  así que todo lo que dependa de la topología real (§4) queda como requisito de
  despliegue, no como hallazgo verificado.
- No cubre módulos que no existen. Stripe (Fase 13) y el descargador del BOE
  (17-B) aparecen como **requisitos de diseño**, no como vulnerabilidades: no se
  puede auditar código que no se ha escrito, y fingir que sí llenaría el informe
  de hallazgos inventados.
- No sustituye una revisión humana de la lógica de negocio.

**Resumen de severidades:** 0 críticas · **3 altas** (A-1, A-2 y 1.3) ·
**7 medias** (M-1…M-5, 1.4 y 1.5) · **6 bajas** · 3 requisitos de despliegue ·
4 no aplicables todavía.

> Los hallazgos de §1 se numeran 1.3–1.5 y no M-x porque pertenecen al patrón, no
> al inventario. Cuentan igual en el total: 1.3 es una de las tres altas.

Y una conclusión que conviene adelantar, porque cambia dónde hay que mirar: **el
código de seguridad de este proyecto está en buen estado.** Los dos hallazgos
altos no son fallos de implementación sino **huecos en las guardias de
configuración** — sitios donde el sistema confía en que quien despliega no se
equivoque, teniendo el proyecto ya el hábito de no confiar en eso. Lo que sí
merece atención estructural es §1.

---

## 1 · El punto ciego de familia: ligaduras por valor

**Esto no es un hallazgo, es el patrón detrás de cuatro hallazgos en cuatro
sesiones.** Va primero porque las correcciones puntuales de §2 no lo tocan.

### 1.1 Qué ve la red y qué no

El proyecto tiene un mecanismo excelente: derivar del `metadata` de SQLAlchemy
qué tablas cuelgan de `usuario`, en vez de enumerarlas a mano. Funciona —
detectó `consentimiento` en la Fase 14 antes de que nadie lo pensara.

**Lo que ve** (medido): `alerta`, `codigo_telegram`, `consentimiento`,
`notificacion`, `preferencias_notificacion`. Cinco tablas, todas con clave
foránea declarada a `usuario.id`.

**Lo que no puede ver, por construcción:**

| Ligadura | Qué contiene | Personal | Estado |
|---|---|---|---|
| `auditoria.quien` | correo del actor, o `sistema:x` | **sí** | limpiado en el borrado desde la Fase 14 (ADR-0013) |
| `auditoria.entidad_id` | id de cualquier entidad, a veces el correo | **sí** | ídem |
| `auditoria.delta` | JSON libre | potencial | **sin cobertura** |
| `token_consumido.jti` | identificador de un token de una persona | seudónimo | **sin cobertura** |
| `preferencias_notificacion.telegram_chat_id` | identidad en un sistema externo | **sí** | cubierto por casualidad: su tabla sí tiene clave foránea |

Las tres ligaduras no personales (`subasta.fuente_codigo`,
`analisis.perfil_codigo`, `regla_disparada.regla_codigo`) apuntan a catálogos, no
a personas: son integridad referencial no declarada, no un problema de privacidad.

**Medición:** de 23 tablas, **9 no declaran ninguna clave foránea**, y `auditoria`
—la que más datos personales acumula por unidad de tiempo— es una de ellas.

### 1.2 Por qué el patrón se repite

Las cuatro veces que este proyecto ha descubierto un punto ciego, la forma era la
misma: **una comprobación que parecía cubrir un dominio cubría solo la parte del
dominio que la herramienta sabe ver.**

| Sesión | Punto ciego | Lo que la herramienta no veía |
|---|---|---|
| Fase 12 → 17-A | `organizacion_id=None` | el filtro compilaba y significaba «nadie» |
| puerta (a) | `if creado:` | el test corría donde la mutación era invisible |
| Fase 14 | `acepta_terminos: bool = False` | Pydantic no valida los valores por defecto |
| Fase 14 | correo en `auditoria` | la red del esquema solo ve claves foráneas |

En los cuatro casos **el síntoma fue el verde**, no el rojo. Y en los cuatro, lo
que falló no fue el razonamiento sino el alcance de una herramienta que se
presentaba como completa.

### 1.3 [ALTA] `auditoria.delta` puede acumular datos personales sin que nada lo vigile

**Cómo se comprobó:** medido. Se revisaron las 23 construcciones de
`Auditoria(...)` del código. Hoy el único `delta` armado con entrada del usuario
es el de `actualizar_preferencias`, cuyo esquema (`PreferenciasUpdate`) solo
admite `canales`, `modo` y tres horas. **Hoy no hay datos personales ahí.**

**Por qué es ALTA pese a eso:** no hay ningún mecanismo que lo mantenga cierto.
`delta` es un JSON libre, cualquier fase futura puede meter un correo, un
teléfono o una dirección, y ni el borrado por RGPD ni ningún test lo detectarían.
La Fase 14 limpia `quien` y `entidad_id` **por nombre de columna**; `delta` no
está en esa lista y no puede estarlo, porque su contenido es arbitrario.

**Explotación hipotética:** no es un ataque; es un incumplimiento. Un titular
ejerce su derecho de supresión, el sistema responde que ha borrado todo, y su
dirección sigue en `auditoria.delta` de la fase que la metió allí.

**Corrección propuesta:** un test que recorra las construcciones de `Auditoria`
—o, mejor, una función `auditar()` única por la que pasen todas— y falle si
`delta` contiene algo con forma de correo. Convertir la disciplina actual, que
hoy se cumple, en algo que no dependa de que se siga cumpliendo.

### 1.4 [MEDIA] `token_consumido` no se limpia al borrar a una persona

**Cómo se comprobó:** medido. `token_consumido` no tiene clave foránea a
`usuario`; el borrado no la toca, y la red del esquema no la ve.

**Impacto real: bajo.** Un `jti` es un UUID aleatorio sin nada del titular. No es
un dato personal por sí mismo; a lo sumo revela que *alguien* consumió un token
de verificación en tal fecha.

**Por qué está aquí igualmente:** es la misma clase de ligadura y conviene que
esté inventariada. Ya existe una purga por antigüedad (`purgar_tokens_consumidos`),
que es la mitigación suficiente. **Recomendación: documentarlo, no cambiar nada.**

### 1.5 [MEDIA] La red del esquema pasa en vacío si el `metadata` está vacío

**Cómo se comprobó:** medido, y me pasó a mí durante esta auditoría.
`tablas_hijas_de(metadata, "usuario")` devuelve el conjunto vacío si nadie ha
importado `app.models`, y entonces `assert not sin_cubrir` **pasa sin comprobar
nada**.

**En el código actual no ocurre:** `tests/escenario_rgpd.py` importa `app.models`
en su cabecera, así que el `metadata` siempre está poblado cuando el test corre.
Verificado.

**Por qué se reporta:** el modo de fallo es silencioso y es exactamente el de esta
familia. `tests/test_esquemas.py` ya lleva el remedio (`assert len(esquemas) > 20`);
`escenario_rgpd` no.

**Corrección propuesta:** una línea —
`assert len(metadata.sorted_tables) > 15, "el metadata está vacío"`.

---

## 2 · Hallazgos por severidad

### [ALTA] A-1 · `SEIS_CORS_ORIGINS="*"` se acepta junto con credenciales

**Cómo se comprobó:** medido, con el cliente de pruebas.

```
SEIS_CORS_ORIGINS="*" → petición con Origin: https://sitio-del-atacante.example
Access-Control-Allow-Origin      : https://sitio-del-atacante.example
Access-Control-Allow-Credentials : true
```

Starlette, ante `allow_origins=["*"]` con `allow_credentials=True`, **refleja el
origen del atacante** en lugar de emitir un `*` (que el navegador rechazaría). El
resultado es la combinación peligrosa: cualquier sitio puede hacer peticiones
con credenciales y **leer la respuesta**.

**Explotación hipotética:** la severidad real depende de dónde viva el token.
SEIS usa `Authorization: Bearer` y no cookies, así que el navegador no adjunta la
sesión sola: un sitio ajeno no obtiene por sí mismo una sesión válida. Lo que sí
consigue es que **cualquier página de internet pueda usar la API como cliente sin
restricción de origen**, incluidos los endpoints públicos con límite por IP
(`/registro`, `/recuperar`), convirtiendo a los visitantes de un sitio cualquiera
en origen de tráfico contra SEIS.

**Por qué es ALTA y no MEDIA:** no por el impacto máximo, sino porque **es la
única familia de configuración peligrosa que el proyecto NO valida**. `config.py`
aborta el arranque si los secretos son débiles, si `PROXIES_DE_CONFIANZA` está
vacío en entorno estricto, o si la purga está mal configurada. CORS no tiene
guardia. La incoherencia es el hallazgo.

**Corrección propuesta:** en `_validar_seguridad_entorno`, abortar en
`ENTORNOS_ESTRICTOS` si `cors_origins` contiene `*`, o si alguna entrada no
empieza por `https://`. Cinco líneas, y el patrón ya existe tres veces en el
mismo fichero.

### [ALTA] A-2 · La resolución de IP se degrada al cupo global **en silencio**

**Cómo se comprobó:** medido. `app/core/red.py` **no importa `logging` y no emite
un solo registro** en sus 262 líneas. Verificado también que la degradación
ocurre: con una cabecera de más de 16 elementos, `resolver_ip` devuelve el par
TCP (la IP del proxy).

**El escenario que importa** no es el ataque, es la avería. Si el proxy inverso
deja de enviar la cabecera —un cambio de configuración, una migración de nginx a
otro balanceador, un `PROXIES_DE_CONFIANZA` que deja de coincidir tras cambiar de
subred—, **todo el tráfico pasa a resolverse como la IP de la pasarela**. Los
límites por origen de `/registro`, `/login` y `/recuperar` vuelven a ser un cupo
global compartido, y un solo atacante puede negar el alta pública a todo el
sitio.

Es **exactamente el defecto que este módulo existe para cerrar**, reintroducido
por una omisión de configuración, y **no produce ningún síntoma**: no hay error,
no hay log, no hay métrica. Se descubriría cuando alguien se quejara de no poder
registrarse.

**Corrección propuesta:** contar las resoluciones que caen al par TCP y exponer
la proporción en `/health/detalle`, que ya informa de `ip_resuelta`. Con la
política activa, una tasa de caída cercana al 100 % significa que la cabecera no
está llegando. No hace falta alertar: basta con que sea visible en el sitio donde
ya se mira.

### [MEDIA] M-1 · Sin cabeceras de seguridad

**Cómo se comprobó:** medido. `app/main.py` añade **un solo middleware**, el de
CORS. No hay `Strict-Transport-Security`, `X-Content-Type-Options`,
`X-Frame-Options`/`frame-ancestors`, `Referrer-Policy` ni `Content-Security-Policy`.

**Impacto:** la API devuelve JSON, así que el margen para XSS reflejado es
pequeño; pero `/analisis/{id}/informe` devuelve `PlainTextResponse` y
`/informe.pdf` un binario, y sin `X-Content-Type-Options: nosniff` un navegador
puede interpretarlos por olfato.

**Corrección propuesta:** middleware propio con las cinco cabeceras. Ya está
previsto en la parte 2 del prompt de esta fase.

### [MEDIA] M-2 · `/health/listo` sin límite de tasa

**Cómo se comprobó:** medido — `app/api/salud.py` no usa el limitador.

**Impacto:** cada llamada ejecuta `SELECT 1` contra PostgreSQL y un `PING` a
Redis. Es un endpoint público y no autenticado que **obliga a trabajo en dos
servicios de infraestructura** por petición. No tumba nada por sí solo, pero es
el amplificador más barato del sistema.

**Matiz que baja la severidad:** el `statement_timeout` de la sonda acota cada
consulta, así que una avalancha no puede encolar consultas largas.

**Corrección propuesta:** límite generoso por IP (el orquestador sondea desde
pocas direcciones). Cuidado: un límite demasiado estricto convierte la sonda en
un fallo de readiness y saca réplicas sanas de rotación. Es un caso donde el
remedio mal calibrado es peor que la enfermedad.

### [MEDIA] M-3 · PostCSS vulnerable, transitivo de Next.js

**Cómo se comprobó:** medido — `npm audit --omit=dev`: **2 vulnerabilidades
(1 alta, 1 moderada)**, cuatro advisories de PostCSS (XSS por `</style>` sin
escapar, y tres de lectura arbitraria de ficheros `.map` vía `sourceMappingURL`).
La cadena es `next@15.5.25 → postcss`. `npm audit fix --force` instalaría
**next@16.3.4, que es un cambio incompatible**.

**Explotabilidad real: baja.** Los cuatro exigen CSS controlado por el atacante.
En SEIS el CSS procede del repositorio y se procesa en build, no en tiempo de
petición: no hay entrada de usuario que llegue a PostCSS.

**Recomendación: NO actualizar a Next 16 por esto.** El riesgo del salto mayor
—en el mismo momento en que la 11-B va a producción— supera al de unos
advisories no alcanzables. Anotar, vigilar si Next publica un parche en la 15.x,
y reevaluar en la Fase 15, que ya toca frontend.

**Backend: limpio.** `pip-audit` sobre `requirements.txt` y `requirements-dev.txt`:
sin vulnerabilidades conocidas.

### [MEDIA] M-4 · `crear_usuario` normaliza el correo de forma distinta que `obtener_por_email`

**Cómo se comprobó:** medido. `obtener_por_email` hace `.strip().lower()`;
`crear_usuario` solo `.lower()`.

**No es explotable por el alta pública:** verificado que `EmailStr` de Pydantic ya
recorta los espacios antes de que el valor llegue al servicio
(`" juan@ejemplo.com"` → `"juan@ejemplo.com"`). La ruta pública está a salvo.

**Dónde sí queda expuesto:** los llamantes que no pasan por `EmailStr`. En
concreto `scripts/sembrar.py`, que crea el administrador inicial con
`s.admin_email` leído del entorno **sin recortar**. Un `ADMIN_EMAIL` con un
espacio final en el `.env` crea un administrador **que no puede iniciar sesión
nunca**, porque el login normaliza y no lo encuentra.

**Corrección propuesta:** normalizar en `crear_usuario`, que es el punto por el
que pasan todos. Una línea.

### [MEDIA] M-5 · El token de baja es reutilizable durante 30 días

**Cómo se comprobó:** medido — `/notificaciones/baja` no llama a `marcar_jti`,
decisión documentada en `config.py` («darse de baja dos veces es inocuo»).

**Impacto:** el razonamiento es correcto en cuanto al efecto —la operación es
idempotente— pero incompleto en cuanto al **tiempo de vida**: es un portador
válido 30 días que nombra a un usuario. Quien lo obtenga (correo reenviado, log
de proxy con la query string, escáner corporativo de enlaces) puede mantener a
esa persona dada de baja indefinidamente, rebajando el consentimiento comercial
sin que el titular lo pida.

**Verificado que NO hay confusión de audiencia:** el token de baja lleva
`proposito` y no `tipo`, y `decodificar_token` exige `tipo == "sesion"`. No sirve
como sesión.

**Corrección propuesta:** o bien consumir el `jti` también aquí, o bien bajar el
TTL. Si se consume, hay que cuidar la reentrada: el segundo clic desde el mismo
correo debe seguir respondiendo «hecho» y no un error.

### [BAJA] B-1 · `politica_actual()` reconstruye la política en cada petición

**Medido:** 5,1 µs por llamada con un rango declarado; **68,9 µs con 22 rangos**
(los de Cloudflare), 13,4× más. Se ejecuta una vez por petición que consulte la
IP. Se puede cachear con `lru_cache` sobre el CSV.

### [BAJA] B-2 · La política de proxies no acota cuántas redes se declaran

Con la cola de XFF validada elemento a elemento, el coste por petición es
*(elementos de la cola)* × *(redes declaradas)*. Ambos están acotados
(16 × n), pero `n` no tiene tope. Es amplificación menor y depende de la
configuración del propio operador; se anota junto a B-1 porque se arregla igual.

### [BAJA] B-3 · Acciones de GitHub ancladas a etiqueta mutable

`checkout@v4`, `setup-python@v5`, `setup-node@v4`. Ya inventariado en
`PENDIENTES.md`. Anclar a SHA es la práctica recomendada.

### [BAJA] B-4 · La exportación RGPD no tiene límite de tasa propio

`GET /cuenta/exportar` recorre cinco tablas del titular. Exige sesión válida, así
que el abuso es de un usuario autenticado contra sí mismo. Un límite por usuario
lo cierra.

### [BAJA] B-5 · Sin revocación de sesión

Los JWT son válidos hasta `exp` (12 h por defecto). **Verificado que la
desactivación sí surte efecto**: `get_current_user` comprueba `activo`, y un
usuario borrado deja de resolverse. Queda el caso de un token robado, que sigue
sirviendo hasta caducar. Una lista de revocación es infraestructura; con 12 h y
sin datos de terceros por ahora, se acepta y se anota.

### [BAJA] B-6 · `/legal/{tipo}` sin límite de tasa

Público y sin autenticar, pero sirve de memoria y no toca la base. Mencionado por
completitud del inventario.

---

## 3 · Lo que se revisó y está BIEN

Un informe que solo lista defectos no dice si el sistema está sano. Esto se
verificó y **resistió**:

- **Aislamiento entre organizaciones.** Los cinco endpoints con identificador en
  la ruta comprueban propiedad y devuelven **404, nunca 403** (`_alerta_propia`,
  el filtro de `analisis`). Un 403 confirmaría la existencia del recurso ajeno.
- **La cadena de proxies es inmune a la inyección de XFF.** Se simuló la cadena
  real —cada proxy apendando el par TCP que ve— con 1, 2 y 3 proxies y seis
  formas de ataque: prefijo falso, inyección de una IP de la lista, cola
  falsificada, relleno hasta el tope, proxies inventados. **En ningún caso el
  atacante consiguió elegir la IP leída.** El diseño de «contar posiciones, no
  mirar valores» + validación de la cola se sostiene.
  *(Nota metodológica: mi primera batería dio tres falsos positivos porque yo
  fijaba la cabecera final a mano en vez de dejar que la construyeran los
  proxies. Los «fallos» eran de la prueba, no del código.)*
- **Confusión de audiencia entre tokens: cerrada.** `decodificar_token` exige
  `tipo == "sesion"` con lista blanca; los de propósito verifican `proposito`.
  Un enlace de verificación no vale como sesión.
- **Uso único donde importa.** Verificación y reseteo consumen `jti` con
  restricción de clave primaria, es decir, la carrera la cierra la base de datos
  y no una comprobación de aplicación.
- **Neutralidad de las respuestas.** `/registro`, `/recuperar` y
  `/reenviar-verificacion` responden igual exista o no la cuenta. No hay oráculo
  de enumeración.
- **Contraseñas:** PBKDF2-HMAC-SHA256 con sal. **JWT:** HS256 fijado en la
  verificación (no se acepta el algoritmo del token, que es el fallo clásico).
- **Saneado del PDF:** hay **un único punto** por el que el texto llega a `fpdf`
  (`_limpiar`), y transcodifica a latin-1 como último recurso. Un punto único es
  lo que hace auditable esto.
- **Escritura en base de datos:** todo va por el ORM con parámetros ligados. El
  único SQL en texto es `SET LOCAL statement_timeout`, con el valor forzado a
  entero antes de interpolarse — verificado.

---

## 4 · Requisitos de despliegue (no son hallazgos de código)

**R-1 · El proxy inverso DEBE borrar o reescribir la cabecera de IP en el borde.**
Con `cf-connecting-ip` o `true-client-ip`, el código acepta el valor íntegro con
la única condición de que el par TCP sea de confianza: **el proxy es el único
control que queda**. nginx, por defecto, no borra la cabecera. El propio módulo
lo documenta; esta auditoría lo eleva a **bloqueante de la 11-B**.

**R-2 · `SALTOS_DE_PROXY` debe coincidir con la topología real.** Un valor
demasiado alto hace que todo caiga al par TCP (cupo global, A-2). Uno demasiado
bajo lee una posición que el cliente controla — aunque la validación de la cola
lo detiene. Verificable en el despliegue con `/health/detalle`, que ya expone
`ip_resuelta`.

**R-3 · HTTPS y HSTS los termina el borde.** La aplicación no los impone.

---

## 5 · No aplicable todavía

- **Webhooks de Stripe (Fase 13).** No existe código. **Requisito de diseño:**
  verificar la firma con el secreto del endpoint **antes** de leer el cuerpo, e
  idempotencia por `event.id` persistido —no en memoria—, porque Stripe reintenta.
- **Descargador del BOE (Fase 17-B): riesgo de SSRF por diseño.** Hoy no hay
  ninguna petición saliente: `app/ingesta/boe.py` solo parsea texto, verificado.
  Pero los parámetros `ingesta.boe.*` son **T3, editables por un superadmin**, y
  la 17-B añadirá una descarga. En cuanto una URL editable la resuelva el
  servidor, hay SSRF contra la red interna. **Requisito para la 17-B:** dominio
  en lista blanca, resolución DNS validada contra rangos privados, sin seguir
  redirecciones a otro dominio.
- **Webhook de Telegram.** Hoy es *polling* saliente, no un webhook entrante: no
  hay origen que verificar. Si se migra a webhook, hará falta el token secreto en
  la ruta y comprobar `X-Telegram-Bot-Api-Secret-Token`.
- **Área privada de clientes (Fase 4).** No existe.

---

## 6 · Qué haría yo, en este orden

1. **A-1 (CORS)** — cinco líneas, patrón ya presente tres veces en `config.py`.
2. **A-2 (visibilidad de la degradación)** — el fallo silencioso es el caro.
3. **1.3 (`delta`)** — la tercera alta, y la única que exige pensar en vez de
   teclear. Va aquí y no al final: es la que impide que §1 se repita una quinta vez.
4. **M-1 (cabeceras)**, **M-4 (normalizar el correo)** y **1.5 (guarda del
   `metadata`)** — los tres son baratos, cerrados y sin discusión.
5. **M-2, M-5** — con criterio: M-2 mal calibrado saca réplicas sanas de rotación.
6. **B-1/B-2 (cachear la política)** — si se toca `red.py` para A-2, sale casi gratis.
7. **M-3 (Next 16)** — **no ahora**. Reevaluar en la Fase 15.

**Una petición para la parte 2:** cada corrección de severidad alta o media
debería ir con su demostración por mutación, como en las tres últimas fases. En
este proyecto la prueba de que un test sirve ha sido, cuatro veces, verlo en rojo.


---

## 7 · Parte 2 · Qué se corrigió y qué no

Aprobadas las 3 altas y las 7 medias. Estado tras aplicarlas: **513 passed con
PostgreSQL, 0 omitidos**; frontend compila.

| # | Corrección | Mutación aplicada | Rojo |
|---|---|---|---|
| A-1 | Guardia de CORS en `config.py` | desactivar la guardia | 4 tests |
| A-1 | ídem, parcial | mirar `*` pero no exigir `https` | 1 test |
| A-2 | Motivo + contador + `/health/detalle` | dejar de contar la caída | 2 tests |
| 1.3 | Oyente `before_insert` sobre `Auditoria` | desenganchar el veto | 1 test |
| 1.3 | ídem, sutil | dejar de mirar las CLAVES del dict | 1 test |
| 1.5 | `tablas_hijas_de` falla en vacío | quitar la guarda | 1 test |
| M-1 | Middleware de cabeceras | no emitirlas | 5 tests |
| M-2 | Caché de la sonda | volver a consultar siempre | 1 test |
| M-2 | ídem, sutil | **caché que nunca caduca** | **sobrevivió dos veces** |
| M-4 | `crear_usuario` normaliza | quitar el `.strip()` | 1 test |
| M-5 | Enlace de baja a 7 días | volver a 30 | 1 test |

### La mutación que sobrevivió, y por qué importa

**Una caché de sonda que nunca caduca** pasó la suite entera. Es un defecto real:
convertiría una caída de la base en un `200 OK` permanente, es decir, la sonda
mentiría exactamente en el momento en que sirve para algo.

Se añadió un test de caducidad. **Y volvió a sobrevivir.** El test hacía

```python
reloj["t"] += salud.SEGUNDOS_DE_CACHE_SONDA + 0.01
```

es decir, **leía su valor esperado de la constante que estaba probando**: con la
constante a infinito, el avance también era infinito y la caché caducaba igual.

Es la quinta vez que aparece la misma forma, y esta vez dentro del test escrito
para cerrarla. Cerrada con dos aserciones independientes: un avance **fijo** de
5 s, y una comprobación aparte de que la ventana es finita y del orden de un
segundo.

### Dos desviaciones respecto a lo que este informe proponía

**M-2: caché en vez de límite de tasa.** El informe proponía limitar. Al
implementarlo quedó claro que un 429 —o un 503— en una sonda de readiness lo lee
el orquestador como «no está lista», y como la configuración sería idéntica en
todas las réplicas **sacaría de rotación a las sanas**. Se acota el TRABAJO (una
consulta por segundo como mucho) en vez de las peticiones, y el orquestador nunca
recibe un código que no espera.

**A-2: avisa, no falla.** La regla del ADR-0014 dice «que lo diga en voz alta o
que falle». Aquí se eligió hablar: rechazar la petición dejaría el sitio
inaccesible por una cabecera mal configurada, y degradar la readiness sacaría de
rotación a todas las réplicas a la vez. Queda escrito en el propio módulo como
límite conocido.

### Lo que NO se tocó, por decisión

- **M-3 (PostCSS vía Next 15).** No se actualiza a Next 16. Los cuatro advisories
  exigen CSS controlado por el atacante y aquí el CSS viene del repositorio; el
  salto mayor en vísperas de producción es riesgo real a cambio de riesgo
  teórico. Reevaluar en la Fase 15.
- **1.4 (`token_consumido`).** Un `jti` es un UUID sin nada del titular y ya hay
  purga por antigüedad. Se documenta y no se cambia.
- **B-3 (acciones ancladas a etiqueta).** Sigue en `PENDIENTES.md`.
- **Las bajas B-4, B-5, B-6.** Anotadas; ninguna aprobada para esta tanda.
- **B-1/B-2** sí se corrigieron de paso al tocar `red.py`: `politica_actual`
  pasa a estar cacheada. Sin test propio — su efecto es de µs y un test de
  rendimiento sería frágil sin proteger nada.
