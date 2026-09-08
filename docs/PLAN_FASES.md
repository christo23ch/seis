# SEIS — Plan de fases hasta el lanzamiento

**Fecha:** 2026-09-08 · **Base:** `main` tras fusionar la Fase 11-A y las correcciones de seguridad (402 tests)
**Sustituye, en el orden y la clasificación, a lo que dice `docs/SEIS_Plan_Maestro_Fases_920.md`.** Aquel sigue
siendo válido como descripción de *qué* hace cada fase; este manda en *cuándo* y *cómo*.

---

## 0 · Por qué este plan reordena el Plan Maestro

Dos motivos, y conviene entenderlos antes de mirar la tabla.

**El primero: sin captación no hay producto.** SEIS promete «te avisamos de las subastas que
encajan contigo». Hoy la única forma de que entre una subasta es que alguien la teclee: no
existe conector de ingesta. Las alertas, el scoring y los canales de la Fase 12 están
construidos y probados, pero **vigilan un caudal que no existe**. Mientras eso siga así, todo
lo demás —cobrar, landing, beta— construye sobre una promesa que el producto no puede cumplir.
Por eso la captación sube al segundo puesto, por delante de la monetización, aunque el Plan
Maestro la pusiera en la posición 17.

**El segundo: no hay portátil.** Las fases se clasifican por dónde pueden ejecutarse, y el
orden maximiza el trabajo 🟢 sin romper la ruta crítica.

| | Significado |
|---|---|
| 🟢 | **Ejecutable ahora.** Código puro, entero en el sandbox web. |
| 🟡 | **Código ahora, activación después.** Se escribe y se prueba ya; queda inerte hasta que configures un panel externo. |
| 🔴 | **Requiere máquina local.** Depuración iterativa contra red, QA multinavegador, carga, restauración real de backups. |

---

## 1 · Trámites humanos que deberías arrancar HOY desde el móvil

No dependen del portátil y son el camino crítico real: sus plazos los marca un tercero, no tú.

| Trámite | Por qué ya | Plazo típico |
|---|---|---|
| **Figura fiscal** (autónomo o SL) con tu gestor | Sin ella no puedes facturar. Bloquea la Fase 13 entera y, por dependencia, la 18 | Semanas |
| **Dominio + Cloudflare** | Bloquea el despliegue (11-B) y el calentamiento del dominio de correo | Horas + propagación |
| **Alta en Render** (o el hosting elegido) | Bloquea 11-B | Minutos |
| **Alta en Postmark o SES + SPF/DKIM** | Sin dominio verificado, los correos de verificación van a spam. Ya hay código que los envía | Días (verificación DNS) |
| **Bot de Telegram** con @BotFather | 10 minutos. Desbloquea el canal ya construido en la Fase 12 | Minutos |
| **Abogado** para textos legales | Bloquea la Fase 14 y el lanzamiento | Semanas |
| **Sentry + UptimeRobot** | Observabilidad de 11-B | Minutos |

---

## 2 · Mecanismo contra un cuarto hallazgo perdido

En esta sesión aparecieron **tres** líneas de trabajo que ninguna sesión conocía: una rama
divergente con una Fase 10 duplicada, una Fase 11 huérfana, y un PR #4 con 7.000 líneas y 236
tests que llevaba un mes abierto. Eso no es mala suerte: **no existe un índice fiable del
estado**. `CLAUDE.md` y `docs/PENDIENTES.md` describen el contenido, pero ninguno lista *qué
ramas y qué PRs están vivos*, que es justo lo que se perdió.

### La regla

**`docs/ESTADO_ACTUAL.md` es el índice, y ninguna fase cierra su PR sin actualizarlo.**
Se le añade una sección de cabecera, obligatoria y corta:

```markdown
## Frentes abiertos  (actualizado: AAAA-MM-DD · commit de main: XXXXXXX)

| Rama | PR | Estado | Qué contiene | Siguiente acción |
|---|---|---|---|---|
| fase-13-stripe | #12 | 🟡 en curso | Suscripción + webhooks | Falta enforcement |
| (ninguna otra) | | | | |

**Suite:** 402 passed, 1 skipped · **Última fase cerrada:** 11-A
```

### Cómo se mantiene sin depender de que te acuerdes

Tres capas, de menos a más fiable:

1. **En el prompt de cada fase** (`docs/PROMPTS_FASES.md`): el último requisito de todos los
   prompts es actualizar esa tabla antes de abrir el PR. Depende de que el modelo obedezca.
2. **En la CI, como test.** Un test compara la lista de ramas remotas y PRs abiertos con la
   tabla del documento y **falla si divergen**. Esto es lo que lo hace fiable: no depende de
   memoria humana ni de la buena voluntad del modelo, sino de la misma puerta que ya bloquea
   los merges. Es barato: una llamada a la API de GitHub y una comparación de conjuntos.
3. **En el vault.** `999-Meta/Estado-de-Implantacion.md` ya existe y cumple un papel parecido
   para el propio vault; se enlaza desde `01-Home/Home.md` para que sea lo primero que se ve al
   abrirlo.

### ADRs: aprovechar lo que ya hay

El vault trae `900-Plantillas/Plantilla-ADR.md` y la Fase 11-A ya escribió **siete ADRs**
(0003-0009) siguiendo esa plantilla. No hay que inventar nada: **la regla es que toda decisión
discutible de una fase termine en un ADR numerado antes de cerrar su PR**, y que el PR lo
enlace. Los siete de la Fase 11-A son la prueba de que el hábito funciona — fueron lo que me
permitió entender 7.000 líneas ajenas en minutos en vez de leerlas enteras.

---

## 3 · Las fases

### Fase 11-B · Despliegue real 🟡
**Objetivo.** Que SEIS esté en internet, con dominio, HTTPS, backups y alarmas.
**Por qué aquí.** Todo lo demás se valida contra algo desplegado; sin esto, cada fase siguiente
acumula riesgo no medido. Y la 11-A ya dejó el repositorio listo, así que es lo más barato.

- **Modelo:** `render.yaml` con la sintaxis correcta de blueprint, workflows de despliegue,
  runbook. Semilla ya escrita en el **PR #6 cerrado** — reutilizarla corrigiendo dos cosas:
  `healthCheckPath` debe ser `/health/listo` (no la sonda de liveness) y las variables deben
  alinearse con `.env.produccion.example` de la 11-A.
- **Tú:** dominio, Cloudflare, alta en Render, secretos, *Required reviewers* del entorno
  `produccion`, y el **simulacro de restauración de backup** (🔴, exige portátil).
- **Bloqueantes:** dominio y hosting.
- **Salida verificable:** `curl https://<dominio>/health/listo` responde 200 desde fuera; un push
  a `main` despliega staging solo; un despliegue a producción exige aprobación; restauración de
  backup documentada con tiempos medidos.
- **Riesgo específico:** el `.env` es un **cambio incompatible** — un `.env` anterior a la 11-A
  impide arrancar la pila entera (`SEIS_ENV` sin declarar vale `production` en el compose, que
  es estricto, y exige `PROXIES_DE_CONFIANZA`). Te morderá al recuperar el portátil.
- **Modelo recomendado:** **Opus 5.** El diseño operativo ya está decidido en la 11-A y sus ADRs.

### Fase 17-A · Conector de captación 🟡 (con una parte 🔴)
**Objetivo.** Que entren subastas solas, que es la promesa del producto.
**Por qué aquí, y no en la posición 17.** Es el riesgo número uno del proyecto: sin caudal, las
alertas de la Fase 12 vigilan el vacío y no hay nada que monetizar en la 13.

- **Modelo (🟢, ahora):** `app/ingesta/` con parser defensivo (nunca lanza, cuenta lo no
  parseado), parámetros T3 `ingesta.boe.*` para que selectores y cadencia se cambien sin
  desplegar, dedupe por `UniqueConstraint(fuente_codigo, identificador_externo)` —hoy
  `UniqueConstraint` está importado en `models.py` pero **sin aplicar a ninguna tabla**—,
  transaccionalidad por lote, y vigilancia de fuentes (aviso al superadmin si una fuente lleva
  24 h a cero) reutilizando `Notificacion`, que ya existe.
- **Tú (🔴 o desde el móvil):** pegar el HTML real de `subastas.boe.es` (listado + una ficha).
  **Comprobado: el sandbox no puede descargarlo** — el proxy de egreso deniega ese dominio, así
  que el ajuste de selectores no se puede hacer sin que tú aportes el HTML.
- **Salida verificable:** con las fixtures reales, el parser extrae ≥ 90 % de los campos
  críticos; un HTML corrupto devuelve lista vacía sin excepción; ejecutar dos veces el mismo
  lote no duplica filas; una fuente en silencio 24 h genera notificación.
- **Riesgo específico:** el scraping tiene cara legal y de cortesía (robots, términos, cadencia
  ≤ 1 req/s, User-Agent identificado). No es solo técnico.
- **Modelo recomendado:** **Opus 5** para el andamiaje; **Sonnet 5** para el ajuste de selectores
  cuando tengas el HTML (tarea acotada de parsing, con fixtures como red).

### Fase 14 · RGPD 🟢
**Objetivo.** Poder operar legalmente con datos de personas reales en la UE.
**Por qué aquí.** Es 🟢 casi entera, y **bloquea el lanzamiento**: hoy no hay consentimientos,
ni exportación, ni borrado de cuenta. Además el registro self-service ya está vivo.

- **Modelo:** consentimientos granulares con versión y fecha en el registro; `GET
  /cuenta/exportar`; `DELETE /cuenta` con gracia de 14 días y anonimización de auditoría.
  Aprovecha que la Fase 11-A ya construyó `purga_service.py`, que resolvió el problema difícil:
  **no hay `ondelete` en ninguna de las seis claves foráneas**, así que un borrado desordenado
  aborta la transacción en PostgreSQL y —peor— deja huérfanos en SQLite.
- **Tú:** abogado para los textos (el modelo redacta borradores marcando los huecos).
- **Salida verificable:** un usuario exporta sus datos y borra su cuenta sin intervención; los
  consentimientos quedan con versión y fecha; la auditoría del borrado queda anonimizada.
- **Riesgo específico:** el borrado toca datos irrecuperables. Los tests deben cubrir el ciclo
  completo con cancelación dentro de la gracia.
- **Modelo recomendado:** **Opus 5.** El borrado en cascada manual es delicado, pero es
  verificable con tests, que es el criterio.

### Fase 13 · Monetización con Stripe 🟡
**Objetivo.** Cobrar.
**Por qué aquí.** Ya tiene plan escrito (`docs/FASE_13_PLAN_EJECUCION.md` y su mapa de impacto),
pero depende del trámite más lento de todos —la figura fiscal— y no tiene sentido cobrar por un
producto que aún no capta.

- **Modelo:** tabla `Suscripcion`, Checkout, Customer Portal, webhooks **idempotentes**,
  dependencia `exigir_limite`. Sin claves configuradas, el módulo queda desactivado y el
  producto funciona como hoy.
- **Tú:** figura fiscal, alta en Stripe, Stripe Tax, productos y precios, endpoint de webhook.
- **Salida verificable:** con tarjeta de prueba, un usuario gratis choca con su límite, mejora,
  se le amplía al instante, cancela y vuelve a gratis; un webhook repetido no duplica efectos.
- **Riesgo específico:** el enforcement de «alertas» necesita enganchar en el CRUD de alertas de
  la Fase 12 — existe, pero conviene revisarlo antes de dar el límite por aplicado.
- **Modelo recomendado:** **Opus 5.** Los ciclos de suscripción y la idempotencia son terreno de
  errores sutiles, pero son exactamente lo que un test de transiciones cubre bien.

### Fase 16 · Endurecimiento de seguridad 🟢
**Objetivo.** Cerrar vectores antes de exponer el producto a tráfico y dinero.
**Por qué aquí.** Tiene que ir después de que existan Stripe y la ingesta, porque son dos de sus
objetivos de auditoría (SSRF en el conector, firma de webhooks) — auditar antes sería auditar
la mitad.

- **Modelo, Parte 1 (solo informe):** auditoría OWASP contra el repositorio →
  `docs/AUDITORIA_SEGURIDAD.md`, y **parar ahí**.
- **Modelo, Parte 2 (tras tu aprobación):** correcciones, rate limiting global —extendiendo
  `core/rate_limit.py`, que la 11-A ya reescribió con ventana deslizante y degradación
  controlada—, cabeceras de seguridad.
- **Tú:** Dependabot, WAF de Cloudflare, y (recomendado) que alguien externo intente romperlo.
- **Salida verificable:** cero hallazgos altos o críticos abiertos; test que verifica el rate
  limiting global; cabeceras comprobadas en la respuesta real.
- **Modelo recomendado:** **Fable 5.1 solo para la Parte 1** (el informe), y **Opus 5 para la
  Parte 2**. Es el único uso de Fable que propongo en todo el plan, y esta es la justificación:
  la auditoría es razonamiento adversarial puro, y su modo de fallo es **el hallazgo que nadie
  encuentra**. No hay test que falle por un vector que no se te ocurrió, así que el coste del
  error es alto y, por definición, invisible para la suite — que es exactamente tu criterio.
  Aplicar tu regla al pie de la letra: Fable produce el documento, Opus 5 implementa.

### Fase 15 · Landing, onboarding y ayuda 🟢
**Objetivo.** Que un desconocido entienda SEIS en 10 segundos y llegue solo a su primer análisis.
**Por qué aquí.** Es la primera fase con trabajo visual serio, y **no debe empezar sin
`docs/DESIGN_SYSTEM.md`** (ver §4). Además su onboarding mide «primera alerta», que solo
significa algo cuando hay captación real.

- **Modelo:** landing pública en la raíz (hoy `/` está bajo `(app)` y protegida), onboarding con
  checklist persistida, `/ayuda`, correos de ciclo de vida.
- **Tú:** decidir si la app se mueve a `/app` o a un subdominio; escribir el contenido real y el
  `MANUAL_DE_USUARIO.md`, que **no existe** (solo hay `MANUAL_DE_PRUEBAS.md`, que es de
  instalación).
- **Salida verificable:** Lighthouse ≥ 90 en rendimiento y accesibilidad; un usuario nuevo llega
  al primer análisis sin ayuda; la landing no rompe el guard de sesión de la app.
- **Riesgo específico:** mover el guard de sesión es el cambio con más superficie de regresión de
  toda la fase. Tests de que las rutas privadas siguen exigiendo sesión.
- **Modelo recomendado:** **Opus 5**, referenciando siempre `docs/DESIGN_SYSTEM.md`.

### Fase 19 · Analítica y panel de negocio 🟡
**Objetivo.** Medir el embudo, sin lo cual la beta no enseña nada.
- **Modelo:** Plausible sin cookies (evita el banner y simplifica el RGPD), eventos del embudo,
  panel de superadmin, widget de feedback.
- **Tú:** alta en Plausible.
- **Salida verificable:** los seis eventos del embudo se disparan en los puntos exactos; el panel
  cuadra con la base de datos.
- **Modelo recomendado:** **Sonnet 5.** Integración documentada y acotada.

### Fase 18 · WhatsApp 🔴 (condicional)
**Objetivo.** Canal chat de alto contacto.
**Puerta:** solo si la Fase 12 demuestra demanda (p. ej. > 30 % de usuarios activos vinculan
Telegram). Depende además de la figura fiscal (Meta Business) y de plantillas aprobadas por Meta,
cuyos plazos no controlas.
- **Modelo recomendado:** **Sonnet 5**, reutilizando el patrón del canal Telegram ya construido.

### Fase 20 · Beta cerrada y lanzamiento 🔴
**Objetivo.** Validar con humanos reales antes de abrir.
Exige QA guionizado multinavegador, prueba de carga y usuarios reales: **es la fase que más
necesita el portátil**. El guion de QA sí puede redactarlo el modelo por adelantado (🟢).
- **Salida verificable:** primeros clientes de pago; embudo midiendo; una semana estable sin
  intervención manual.
- **Modelo recomendado:** **Opus 5** para el guion; la ejecución es humana.

---

## 4 · Fase 0 transversal · Sistema de diseño 🟢

**No es una fase del Plan Maestro: es un prerrequisito que este plan añade.** El motivo está en
`docs/ESTADO_ACTUAL.md`: el frontend son 3.292 líneas **sin un solo test y sin ESLint**, con toda
la UI en un único `components/ui.tsx` artesanal. Sin tokens ni reglas escritas, cada sesión
improvisa y el resultado sale genérico — que es exactamente la queja.

Debe producirse **antes que la Fase 15**, y a partir de entonces **ningún prompt de frontend se
ejecuta sin referenciar `docs/DESIGN_SYSTEM.md`**.

Su contenido, la decisión abierta sobre shadcn/ui y las herramientas (skills, MCPs, Obsidian) van
en `docs/HERRAMIENTAS.md` (Paso 4), no aquí.

---

## 5 · Resumen del orden y por qué

| # | Fase | Clase | Depende de |
|---|---|---|---|
| 1 | 11-B · Despliegue | 🟡 | Dominio, hosting |
| 2 | 17-A · Captación | 🟡 + 🔴 | HTML real del BOE |
| 3 | 14 · RGPD | 🟢 | Abogado (textos) |
| 4 | 13 · Stripe | 🟡 | **Figura fiscal** (empieza hoy) |
| 5 | 16 · Seguridad | 🟢 | Que existan 13 y 17 |
| 0' | Sistema de diseño | 🟢 | — (antes de la 15) |
| 6 | 15 · Landing | 🟢 | Sistema de diseño |
| 7 | 19 · Analítica | 🟡 | Alta en Plausible |
| 8 | 18 · WhatsApp | 🔴 | Puerta de demanda + fiscal |
| 9 | 20 · Beta | 🔴 | Todo lo anterior |

**Mientras no haya portátil**, el trabajo 🟢 disponible es: el andamiaje de la 17-A, la Fase 14
casi entera, la Fase 16 completa, y el sistema de diseño. Es varias semanas de trabajo sin tocar
un panel externo.
