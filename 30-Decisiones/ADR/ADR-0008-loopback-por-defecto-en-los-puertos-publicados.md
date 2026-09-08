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
  - area/seguridad
---

# ADR-0008: los puertos publicados escuchan solo en loopback mientras nadie declare lo contrario

## Contexto

El plan aprobado de la fase dice literalmente, en la tabla del Bloque C′: «**No** se toca la publicación de puertos: es Fase 16». **Se ha tocado.** Este ADR existe para registrar esa desviación con su motivo, no para disimularla.

Los hechos que la provocan:

1. **`backend` (8000) y `frontend` (3000) se publicaban en todas las interfaces**, mientras `db` y `redis` llevaban desde la Fase 12 publicándose solo en `127.0.0.1`. La asimetría estaba anotada desde la Fase 9.5 como observación de otra fase, sin propietario.
2. **La premisa del diferimiento caducó dentro de este mismo bloque.** «Es Fase 16» se decidió cuando el `docker-compose.yml` era orquestación local y nada más. El Bloque C′ le cambió el cometido: `.dockerignore`, `.env.produccion.example`, el ancla de entorno y el `healthcheck` lo convierten en **la base de un despliegue portable**. El fichero pasó a ser algo que alguien copiará a un VPS.
3. **Con ese cometido nuevo, publicar 8000 en `0.0.0.0` deja de ser inocuo.** `/docs` y `/openapi.json` quedan **enumerando la API entera sin autenticación**, y —más grave— permite **hablar con uvicorn saltándose el proxy inverso del Bloque H**, con lo que su lista de proxies de confianza no protegería nada: bastaría llamar al puerto directamente.

## Decisión

Los dos servicios web publican por **variable con valor por defecto en loopback**: `backend` en `${BIND_BACKEND:-127.0.0.1}` y `frontend` en `${BIND_FRONTEND:-127.0.0.1}`.

Exponer a todas las interfaces deja de ser el comportamiento por omisión y pasa a ser **un acto explícito** del operador.

## Justificación

### Por qué no se difirió, si el plan lo difería

Porque lo diferido no era la corrección: era la corrección **bajo una premisa** —«el compose es solo local»— que este bloque destruyó al reescribir el fichero para que sirviera de plantilla de despliegue. Mantener el diferimiento habría significado publicar como entregable de la fase un fichero pensado para copiarse a un servidor **y que enseña la forma equivocada**. Un fichero de despliegue equivocado no se queda quieto: se copia.

El cambio, además, **no depende de ninguno de los bloqueos diferidos**. No necesita saber el proveedor (H1) ni el dominio (H2): es una decisión local del fichero, y es exactamente la que `db` y `redis` ya tenían tomada.

### Por qué el agujero peor no es `/docs`

Porque `/docs` es reconocimiento y el bypass del proxy es **elusión de un control de seguridad**. El Bloque H existe para resolver la puerta de despliegue heredada de la Fase 10: hacer que la IP de origen sobreviva, para que el anti-fuerza-bruta y los límites por origen dejen de comportarse como un cupo global. Ese bloque se apoya en declarar qué proxy es de confianza. **Un puerto de uvicorn abierto al mundo convierte esa declaración en un adorno**, porque el atacante no tiene ninguna obligación de entrar por el proxy.

Dicho en corto: dejar 8000 en `0.0.0.0` habría neutralizado en silencio el bloque que levanta la puerta de despliegue, y el síntoma habría sido ninguno.

### Por qué una variable y no `127.0.0.1` a fuego

Porque hay despliegues legítimos en los que el contenedor **debe** ser alcanzable directamente —una máquina sin proxy inverso delante, o una red donde el proxy es otro host—. Fijarlo a fuego habría convertido una decisión de seguridad en un impedimento, y los impedimentos se sortean editando el fichero a mano, que es peor que declararlo en el entorno. La variable conserva la decisión **y** deja la salida documentada.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Dejarlo en `0.0.0.0` y diferir a la Fase 16, como decía el plan | La premisa del diferimiento ya no era cierta al llegar el final del bloque. Se habría entregado como resultado de la fase una plantilla de despliegue que expone la API sin autenticar y permite eludir el proxy del Bloque H, con la etiqueta «pendiente» puesta a un fichero que la gente copia hoy. |
| Apagar `/docs` y `/openapi.json` según el entorno, en vez de tocar los puertos | Cierra **uno** de los dos agujeros, y no el peor: no hace absolutamente nada contra hablar con uvicorn saltándose el proxy. Además traslada al código de la aplicación un problema que es del fichero de despliegue, y deja la asimetría con `db` y `redis` intacta. |
| Fijar `127.0.0.1` a fuego, sin variable | Convierte la decisión en un impedimento para los despliegues donde la exposición directa es legítima, y los impedimentos se resuelven editando el compose a mano en el servidor — que es exactamente la deriva que el resto del bloque se dedicó a eliminar. |

## Consecuencias

### Positivas

- **El valor por defecto deja de ser «expuesto».** Quien copie el fichero y no piense en ello obtiene la opción segura; antes obtenía la contraria.
- **Simetría con `db` y `redis`,** que ya escuchaban solo en loopback. El fichero deja de contradecirse a sí mismo.
- **El Bloque H puede llegar a significar algo.** Con el backend accesible solo por el proxy, declarar proxies de confianza pasa a ser un control real y no una preferencia.
- **Cierra una observación de la Fase 9.5** que llevaba anotada desde entonces sin propietario asignado. Ver [[PENDIENTES-md|PENDIENTES.md]].
- Queda **bajo el test derivado del compose**, no bajo una lista escrita a mano: la expectativa se calcula del propio `docker-compose.yml`, de modo que una perilla nueva no puede volver a quedarse fuera del inventario sin que algo falle.

### Negativas / deuda asumida

- **Quien despliegue esperando acceso externo debe declarar `BIND_BACKEND=0.0.0.0` a propósito, y eso es deliberado.** Es el coste explícito de la decisión: la pila levanta sana, los health checks pasan, y **no hay nada alcanzable desde fuera**. El fallo se parece a una avería y no lo es.
- **La primera víctima de eso fue el propio bloque.** La revisión técnica encontró **cinco variables que vivían en el compose y no en las plantillas**, y la más grave era precisamente `BIND_BACKEND`: un operador siguiendo una plantilla que se autodeclaraba «inventario COMPLETO» levantaba la pila, no alcanzaba nada y **no tenía ninguna pista de qué perilla lo arreglaba**. La corrección de fondo no fue añadir la variable a la lista —eso arregla el caso, no el mecanismo— sino **sustituir la lista escrita a mano por una expectativa derivada del propio compose**; ese test derivado cazó de inmediato otro hueco recién creado.
- **Loopback no es un control de seguridad por sí solo.** No protege de nada que ya corra en el mismo host, no sustituye al Bloque H y no sustituye a la autenticación. Lo único que hace —y no es poco— es que la exposición deje de ser gratuita y por omisión.
- **Se ha desviado del alcance aprobado.** Queda como precedente y como regla de conducta: una premisa que caduca **se documenta y la desviación se registra**, nunca se corrige en silencio. El registro vive en `docs/FASE_11_PLAN.md` §3 bis, junto a las otras dos afirmaciones del plan que resultaron falsas al ejecutarlo.

## Relacionado

- Fase: [[Fase-11-infraestructura]] — Bloque C′
- Registro de la desviación: `docs/FASE_11_PLAN.md` §3 bis (y §3, tabla del Bloque C′, donde consta el alcance original)
- [[ADR-0007-planificador-celery-separado-del-worker]] — la otra decisión del mismo bloque; comparte causa raíz: el compose dejó de ser local y pasó a ser plantilla de despliegue
- [[ADR-0002-clave-compuesta-limitador-login]] — su efecto pleno depende del Bloque H, y un uvicorn accesible sin pasar por el proxy lo dejaría sin efecto igualmente
- [[Fase-10-alta-self-service]] — de ella viene la puerta de despliegue por la IP de origen, que es lo que el Bloque H debe levantar
- Los números **ADR-0004 y ADR-0005 siguen reservados** para los bloques E y H; sus notas aún no existen. Ver [[contador-secuencias]].
- Tests de la decisión: `backend/tests/test_despliegue.py`
