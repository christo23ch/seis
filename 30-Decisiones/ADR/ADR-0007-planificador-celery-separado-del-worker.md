---
tipo: adr
fase: "[[Fase-11-infraestructura]]"
estado: aprobado
supersede: ""
superado_por: ""
tags:
  - tipo/adr
  - estado/aprobado
  - fase/11
  - area/infra
---

# ADR-0007: el planificador de Celery es un servicio propio, no una bandera del worker

## Contexto

Dos hechos del `docker-compose.yml` anterior, distintos entre sí pero de la misma familia: **cómo se definen los servicios de aplicación para que no se estropeen al crecer.**

**1. El planificador vivía dentro del worker.** La Fase 12 añadió `--beat` al comando del worker, y con razón: sin esa bandera, el digest horario y el sondeo de Telegram no se ejecutaban nunca. Pero `--beat` arranca un planificador **por proceso worker**. La configuración funciona con exactamente una réplica, y solo con una.

**2. El entorno estaba escrito dos veces.** `backend` y `worker` tenían cada uno su bloque `environment`, con la misma lista de variables copiada. El hallazgo **P1 de la Fase 12** —siete variables de SES/SMTP que no llegaban al contenedor, de modo que con `EMAIL_PROVIDER=ses` el correo dejaba de enviarse **en silencio** y el diagnóstico mentía— no nació de un olvido puntual: nació de que esos dos bloques **derivaron**. Uno se actualizó y el otro no, que es lo único que puede pasarle a una lista duplicada a mano con el tiempo suficiente.

## Decisión

Ambas cosas se resuelven en el mismo sitio y por el mismo motivo:

| # | Decisión |
|---|---|
| a | **`beat` es un servicio propio, único y no escalable.** El worker pierde `--beat` y pasa a solo ejecutar tareas; programarlas es competencia exclusiva del nuevo servicio. |
| b | **El entorno de aplicación se define una sola vez**, en un ancla YAML `x-entorno-aplicacion` que `backend`, `worker` y `beat` referencian. No hay tres bloques `environment`: hay uno. |

La (a) es la decisión **H7** del responsable. La (b) es su condición de posibilidad: separar `beat` sin ancla habría significado pasar de dos listas que pueden divergir a **tres**.

## Justificación

### Por qué el planificador no puede vivir dentro del worker

Porque `--beat` no es una opción de arranque, es un rol. Escalar el worker a N réplicas —la operación que se querrá hacer en cuanto aumente la carga, y la razón misma de tener un worker— arranca **N planificadores**. Los N programan el digest horario y los N sondean Telegram. El resultado no es más rendimiento: es que **cada usuario recibe N copias del mismo mensaje**.

Lo peor del defecto es cuándo aparece. No da síntoma alguno mientras haya una sola réplica, y se manifiesta exactamente el día que se escala — es decir, el día de más carga y más usuarios mirando, y con la causa disfrazada de «problema de notificaciones» en vez de «problema de topología».

### Por qué un ancla y no tres bloques disciplinados

Porque la deriva ya ocurrió y está medida: es el P1 de la Fase 12. La disciplina de mantener sincronizadas dos listas a mano falló una vez, en el peor sitio posible —el envío de correo, que falla callado—, y no hay motivo para creer que con tres listas fuera a fallar menos.

Un ancla no mejora la disciplina: **elimina la posibilidad**. No hay dos sitios que puedan discrepar porque solo hay uno. Es la diferencia entre un requisito operativo (que se incumple) y una imposibilidad estructural (que no).

### Por qué se aplica ya en `docker-compose.yml` y no en la IaC de 11-B

Porque la IaC del proveedor depende de **H1**, diferido. Dejar la corrección para la 11-B significaría que el único despliegue que hoy existe conserva el defecto durante toda la espera, y —peor— que el `docker-compose.yml` seguiría describiendo una topología que no es la que se pretende operar. Un fichero de despliegue que enseña la forma equivocada es una guía falsa, y se copia.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Mantener `--beat` embebido en el worker | Se rompe al escalar, que es justo lo que un worker existe para poder hacer. N réplicas ⇒ N planificadores ⇒ N copias de cada mensaje a cada usuario. Y no da síntoma hasta el día en que se escala. |
| Un cerrojo distribuido en Redis para que solo una réplica programe | Resuelve el problema correcto con la herramienta cara: hay que elegir TTL, renovar el cerrojo mientras se vive, decidir qué ocurre si expira a mitad de un tick y probar todos esos caminos. Es complejidad —y una modalidad de fallo nueva— que no hace falta cuando basta con separar el proceso. |
| Repetir el bloque `environment` en los tres servicios | Es exactamente lo que produjo el P1 de la Fase 12, con dos. Con tres copias la deriva llega antes, no después. |
| Dejar la separación para la IaC del proveedor (11-B) | La 11-B está bloqueada por H1, diferido. El despliegue que hoy existe arrastraría el defecto durante toda la espera y seguiría documentando la topología equivocada. |

## Consecuencias

### Positivas

- **Escalar el worker deja de tener efectos colaterales.** Es la operación de crecimiento más previsible del sistema y ahora es segura por construcción, no por acordarse.
- **Cierra el P1 de la Fase 12.** El entorno de `backend`, `worker` y `beat` no puede volver a divergir porque ya no hay nada que sincronizar.
- **Verificación ejecutada, no supuesta:** `docker compose config` → exit 0, **6 servicios** (`db`, `redis`, `backend`, `frontend`, `worker`, `beat`), **7/7 variables SES/SMTP presentes en `backend`, `worker` y `beat`**, y `--beat` ya no aparece en el worker.
- **La topología queda bajo test**, y el test ya no es una lista escrita a mano: `backend/tests/test_despliegue.py` **deriva del propio `docker-compose.yml` la expectativa que comprueba**. El fichero de despliegue deja de ser prosa que nadie verifica. **Cifra final del bloque, medida tras las tres revisiones: 220 recogidos · 217 pasan · 2 fallan · 1 omitido** — **+58 verdes y 0 regresiones** frente a la línea base de la fase (162 · 159 · 2 · 1); los 2 rojos siguen siendo los preexistentes de PDF. Las medidas intermedias (212 y 233) quedan derogadas.
- **La guardia de esta decisión está demostrada, no supuesta.** La revisión de pruebas encontró que el test del planificador **pasaba igual aunque el servicio `beat` fuese un `celery worker --beat`**: vigilaba exactamente lo que este ADR prohíbe y no lo detectaba. Se corrigió y se verificó **por mutación** — aplicada la mutación, el test nuevo **falla**. Un test que no falla ante el defecto que dice cubrir no es cobertura, es decoración.

### Negativas / deuda asumida

- **Un contenedor más que operar y vigilar.** `beat` tiene su propio ciclo de vida y su propio log, y **no sirve peticiones**: si se cae, ningún health check web lo delata. Lo único que se nota es que dejan de llegar digests, y se nota tarde.
- **Si alguien escala `beat` por error, el problema vuelve entero y no hay nada en el código que lo impida.** `docker compose up --scale beat=2` es una orden legítima que nadie va a rechazar, y reintroduce íntegro el defecto que este ADR evita — con el mismo síntoma diferido de siempre. La única salvaguarda posible es documental: queda como **requisito operativo para el runbook de la Fase 11-B — `beat` corre con exactamente una réplica, siempre.**
- **El ancla obliga a una regla explícita, porque sin ella el remedio amplía el daño.** Todo lo que entre en `x-entorno-aplicacion` llega a los tres servicios sin excepción; ese es el precio de que no puedan divergir. La regla que queda escrita, y que hay que aplicar en cada añadido futuro, es:

  > **En el ancla va lo que necesitan los tres. Lo que necesita uno solo va en el `environment` propio de ese servicio.**

  No es una precaución teórica. Ya hay un incumplimiento **medido** conviviendo con la decisión: `worker` y `beat` cargan `ADMIN_PASSWORD` sin usarla jamás —la consume una sola ruta de código, la siembra del admin bootstrap, y solo la ejecuta el `backend`—, y la llevan únicamente porque `app/tasks/celery_app.py` invoca `get_settings()` al importarse y sin ella no arrancan en un entorno estricto. No es una credencial menor: es la del usuario `es_superadmin`, que gobierna el conocimiento T2/T3 global. Queda abierta con propietario **Fase 16** en [[PENDIENTES-md|PENDIENTES.md]].

- **Caso ya identificado, para no decidirlo con prisa: cuando la Fase 13 traiga las claves de Stripe, NO van al ancla.** Van al bloque propio del `backend`. El planificador y el worker **no cobran a nadie**, y meterlas en el ancla ampliaría a tres contenedores lo que filtra uno solo comprometido, a cambio de nada. Si el diseño de la Fase 13 acabara dando a una tarea de Celery un cometido de facturación, eso es una excepción que hay que **argumentar explícitamente allí**, nunca heredar por omisión del ancla.

- **Una sola definición garantiza que los tres no diverjan; no garantiza que esté completa.** El ancla elimina la deriva entre servicios y no dice nada sobre lo que falte en los tres a la vez. La revisión lo demostró dentro de este mismo bloque: `VERSION_REGLAS` y `VERSION_PARAMETROS` **no llegaban a ningún contenedor**. Son las versiones del conocimiento T2/T3 que cada análisis congela por el principio **P1 (determinismo)**, de modo que ajustarlas en `.env` **no tenía efecto alguno bajo Docker**. No fue una laguna de la batería de tests: fue el defecto. La barrera que queda contra la siguiente ausencia no es la disciplina, es que la expectativa del test **se deriva del compose** en vez de escribirse a mano.

## Relacionado

- Fase: [[Fase-11-infraestructura]] — Bloque C′
- Plan de ejecución del bloque: `docs/FASE_11_PLAN.md` §3 (Bloque C′) y §1 (H7)
- Hallazgo que cierra: **P1 de la Fase 12** — las siete variables de SES/SMTP que no llegaban al contenedor. Ver [[PENDIENTES-md|PENDIENTES.md]].
- [[ADR-0006-liveness-y-readiness-separadas]] — el mismo bloque añade el `healthcheck` del backend apuntando a `/api/v1/health` (liveness) y **nunca** a `/health/listo`: materializa bajo Compose el requisito operativo que aquel ADR dejó escrito como prosa.
- [[ADR-0003-staging-como-entorno-estricto]] — el entorno que este ancla centraliza es el que aquel ADR volvió estricto también en staging; una definición única es lo que hace comprobable que staging reciba exactamente las mismas variables que producción.
- [[ADR-0008-loopback-por-defecto-en-los-puertos-publicados]] — la otra decisión del mismo bloque, y de la misma raíz: el `docker-compose.yml` dejó de ser «orquestación local» para convertirse en la base de un despliegue portable, y eso obliga a revisar lo que el fichero enseña.
- Tests de la decisión: `backend/tests/test_despliegue.py`
