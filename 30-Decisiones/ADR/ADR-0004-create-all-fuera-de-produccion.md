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
  - area/datos
---

# ADR-0004: el esquema se deriva de los modelos solo en desarrollo y test; la siembra sigue corriendo en todos los entornos

## Contexto

La convención **§6.9** de [[CLAUDE-md|CLAUDE.md]] prohíbe derivar la DDL de los modelos dentro de `alembic/versions/`. El motivo escrito allí es que una revisión así **no describe un cambio de esquema**: reproduce el estado que los modelos tengan **el día que se ejecute**, de modo que dos instalaciones con la misma revisión acaban con esquemas distintos y el historial deja de ser reproducible.

Ese mismo antipatrón vivía **fuera** de `alembic/versions/`, en la ruta de arranque: `scripts/init_db.py` llamaba a `Base.metadata.create_all(engine)` y `docker-compose.yml` lo encadenaba **después** de `alembic upgrade head`.

Y esa posición —después— es la que convierte una molestia en un defecto caro:

1. Si un modelo declara una tabla o una columna que **ninguna migración crea**, `create_all` la crea **en silencio y en producción**.
2. El esquema real deja de ser el que describe la cadena de migraciones. La revisión anotada en `alembic_version` sigue diciendo la verdad sobre qué migraciones corrieron, y **miente sobre qué esquema hay**.
3. La deriva que el test **T4** existe para detectar queda **enmascarada justo donde más caro sale**: `create_all` la repara antes de que nadie la note, así que el verde de la cadena de migraciones deja de significar lo que se supone que significa.

El plan clasificó este bloque como de **riesgo ALTO** por un motivo concreto: tocar el arranque puede impedir que el producto levante de cero, que es exactamente el defecto que originó la Fase 9.5.

## Decisión

**`create_all` se ejecuta únicamente en `development` y `test`.** En cualquier otro entorno el esquema lo gobierna Alembic, sin excepción, y el arranque lo dice en voz alta en vez de callárselo.

```python
ENTORNOS_CON_CREATE_ALL = ("development", "test")
```

La siembra —perfiles, reglas T2, parámetros T3, fuentes y administrador inicial— se extrae a `backend/scripts/sembrar.py`, invocable a mano contra una base ya migrada, **y sigue ejecutándose en todos los entornos**. Esto último se aparta del plan a propósito; el porqué está abajo y no se disimula.

## Justificación

### Por qué la prohibición pesa más aquí que en una revisión

Una revisión que deriva la DDL de los modelos al menos **deja rastro**: está en el historial, se lee, se audita, se puede señalar. `create_all` en el arranque no deja ninguno. Se ejecuta en cada despliegue, no aparece en ningún diff a partir del día en que se escribió, y su efecto —crear lo que falte— es indistinguible de que no faltara nada.

Dicho al revés: la §6.9 protege la **auditabilidad del historial**; ponerlo en el arranque atacaba lo mismo por un sitio donde la convención no llegaba a mirar.

### Por qué desarrollo y test lo conservan

Porque ahí no hay ninguna cadena de migraciones que respetar ni ningún esquema real que proteger: la base se tira y se rehace continuamente, y crear el esquema al vuelo es lo cómodo y lo inocuo. Obligar a `alembic upgrade head` para correr la suite añadiría coste en cada ejecución sin comprar absolutamente nada — y la suite corre sobre SQLite, donde el esquema es desechable por definición.

La línea divisoria no es arbitraria: es **la misma que separa los entornos estrictos** de los que no lo son, y la traza [[ADR-0003-staging-como-entorno-estricto|el ADR que hizo de `staging` un entorno estricto]]. El entorno es ya la variable que decide con qué rigor se trata todo lo demás; no hacía falta inventar otra.

### Por qué la siembra sí corre en todos los entornos, apartándose del plan

El plan pedía que en staging y producción la siembra se invocara **a mano, una vez**, con este argumento: «un superadmin creándose en cada arranque es superficie que no debe existir por defecto». El argumento es correcto sobre el riesgo y equivocado sobre el remedio, por dos hechos:

1. **La siembra es idempotente y lo es por construcción, no por suerte.** Cada bloque comprueba antes si ya hay datos, y `sembrar_admin` **solo crea el administrador si no existe ningún usuario en absoluto** — no «si no existe ese email». En una instalación en marcha no se crea nada, arranque tras arranque.
2. **Sacarla del arranque haría que `docker compose up` no baste para tener un sistema en pie.** Una instalación nueva quedaría sin reglas, sin parámetros y sin administrador: técnicamente levantada e inservible. Eso es, por otra puerta, **el defecto que originó la Fase 9.5** — que una instalación limpia no pudiera funcionar sin un paso manual que alguien tiene que recordar. Y un paso manual que alguien tiene que recordar es un paso que se olvida.

Queda dicho sin adornar lo que se acepta a cambio: **la seguridad de que no se cree un superadministrador de más depende de una condición dentro del código, no de que el camino no exista.** Si un día esa condición se relaja, no habrá nada más detrás.

### Por qué se separa `sembrar.py` de `init_db.py` aunque los dos sigan corriendo juntos

Porque son dos responsabilidades con reglas opuestas —una prohibida fuera de desarrollo, la otra obligatoria en todas partes— y tenerlas en el mismo módulo es lo que permitió que la primera viajara de polizón durante tanto tiempo. Separadas, la siembra puede además invocarse sola (`python -m scripts.sembrar`) contra una base ya migrada, **sin arrastrar consigo ninguna creación de tablas**.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Dejar `create_all` donde estaba y confiar en que T4 detecte la deriva | T4 corre en CI, no en producción. Y `create_all` **repara la deriva antes de que se manifieste**, de modo que en el único sitio donde importa el test nunca llegaría a tener nada que denunciar. |
| Retirar `create_all` también de desarrollo y test | La suite y el flujo local se apoyan en él, no hay migraciones que respetar en esos entornos y el esquema es desechable. Añade coste en cada ejecución a cambio de proteger algo que no existe. |
| Condicionarlo con una perilla propia (`CREATE_ALL=1`) en vez de por entorno | Una variable más que alguien puede poner a 1 «provisionalmente» en producción para salir de un apuro — y las cosas provisionales de ese tipo no se quitan. El entorno ya decide el rigor de todo lo demás; duplicar el criterio es invitar a que los dos discrepen. |
| Sacar la siembra del arranque, como decía el plan | `docker compose up` dejaría de bastar para tener un sistema en pie: el defecto de la Fase 9.5 entrando por otra puerta. |
| Dejar la corrección para la 11-B, con la IaC del proveedor | La 11-B está bloqueada por H1. El único despliegue que hoy existe arrastraría el defecto durante toda la espera, y el `docker-compose.yml` —que desde el Bloque C′ es plantilla de despliegue portable— seguiría enseñando la forma equivocada. |

## Consecuencias

### Positivas

- **El esquema de staging y producción lo describe la cadena de migraciones, y solo ella.** Vuelve a ser cierto que dos instalaciones en la misma revisión tienen el mismo esquema.
- **La deriva deja de repararse sola.** Un modelo sin su migración pasa a manifestarse como error, que es lo que debe hacer; antes se convertía en una tabla creada en silencio y en una diferencia entre entornos que nadie veía.
- **El test capital afirma sobre la llamada, no sobre un valor de retorno.** `backend/tests/test_arranque_esquema.py` **sabotea `create_all` para que estalle si alguien lo invoca** en un entorno estricto. Un test que comprobara el booleano devuelto seguiría verde el día que un refactor invocara `create_all` por otro camino; este no.
- **La siembra gana una vía de invocación propia** contra una base ya migrada, que es justo lo que hará falta en la 11-B.

### Negativas / deuda asumida

- **La red de seguridad desaparece precisamente donde antes tapaba.** Si una fase futura añade un modelo y olvida la migración, el síntoma ya no será «funciona raro»: será un error en producción. Es lo correcto, y es más ruidoso — conviene que quede escrito antes de que ocurra y alguien lo lea como una regresión.
- **La ausencia de superadministrador de más se sostiene en una condición del código.** Ver arriba. No hay una segunda barrera detrás de `sembrar_admin`.
- **La verificación que de verdad cierra este bloque es manual y ningún test la sustituye.** El plan la deja escrita como innegociable: `docker compose down -v && docker compose up -d --build` sobre volumen destruido, con `/api/v1/health` respondiendo 200. La suite corre sobre SQLite y no puede demostrar que una instalación limpia levanta bajo Docker. El [[runbook-verificar-migracion-alembic-en-postgresql-real|runbook de migración en PostgreSQL real]] cubre la parte de que el ciclo `upgrade`/`downgrade` sigue sano.
- **La desviación del plan queda registrada, no corregida en silencio.** Es la misma regla de conducta que fijó [[ADR-0008-loopback-por-defecto-en-los-puertos-publicados|el ADR del loopback por defecto]]: una premisa que no se sigue se escribe con su motivo.

## Relacionado

- Fase: [[Fase-11-infraestructura]] — Bloque E
- Plan de ejecución del bloque: `docs/FASE_11_PLAN.md` §3
- Convención que este ADR extiende de `alembic/versions/` a la ruta de arranque: [[CLAUDE-md|CLAUDE.md]] §6.9 (y §6.10, sobre la DML de migración)
- [[ADR-0003-staging-como-entorno-estricto]] — la lista de entornos estrictos es la misma línea divisoria que usa esta decisión
- [[ADR-0005-confianza-en-cabeceras-de-ip-solo-tras-par-declarado]] — el otro bloque que añade una guardia de arranque anclada en los entornos estrictos
- [[runbook-verificar-migracion-alembic-en-postgresql-real]]
- Tests: `backend/tests/test_arranque_esquema.py` y **T4** en `backend/tests/test_migraciones.py`, que debía seguir verde y es la prueba de que retirar `create_all` no dejó hueco de esquema
