# Coste del matcher con ingesta de plataforma

**Fase 17-A · condición 4 de la aprobación · complementa [[ADR-0011]]**

Hasta ahora el matcher solo corría cuando un humano captaba una subasta a mano, y
solo miraba las alertas de su organización. Con ingesta diaria del BOE pasa a
evaluar **todas las alertas activas de la plataforma contra cada lote**. Esta nota
mide qué cuesta eso y dice qué hay que acotar y cuándo.

Respuesta corta: **emparejar es barato y no hace falta tocarlo. Lo que no escala
es notificar** — y el problema no es de rendimiento, es de producto.

---

## 1. Cómo se ha medido

`procesar_lote` completo (persistencia + matcher + despacho) sobre SQLite, base
vacía en cada medición, en este sandbox. Scripts versionados: `backend/scripts/medir_matcher.py` y
`backend/scripts/medir_matcher_consultas.py` (§6).

Tres avisos de honestidad sobre las cifras, por orden de importancia:

1. **El despacho medido NO incluye la red.** Sin `EMAIL_PROVIDER` configurado,
   `NotificadorEmail.enviar` registra en log y devuelve `False`
   (`app/notificadores/email.py`). Lo medido en el bloque C es solo el trabajo de
   ORM del envío. **El coste real de despachar es entre uno y tres órdenes de
   magnitud mayor** y se estima aparte, en §4.
2. **SQLite no es PostgreSQL.** Los tiempos absolutos no se trasladan. Lo que sí
   se traslada es la **forma** de las curvas y el **número de consultas**, que es
   independiente del motor.
3. **El tamaño real del lote diario del BOE no se conoce todavía.** Se sabrá en la
   17-B, con HTML real. Por eso todo aquí está expresado en función de N.

---

## 2. Emparejar: lineal y barato

Lote de 50 subastas, ninguna alerta casa (0 notificaciones, 0 despacho):

| Alertas activas en la plataforma | Tiempo | Por subasta |
|---:|---:|---:|
| 100 | 0,21 s | 4,2 ms |
| 500 | 0,40 s | 8,0 ms |
| 1.000 | 0,61 s | 12,3 ms |
| 2.000 | 1,13 s | 22,6 ms |
| 5.000 | 2,78 s | 55,7 ms |

Lineal en el número de alertas, como cabía esperar: `casa_alerta` es una función
pura de tres comparaciones y no toca la base de datos.

**5.000 alertas activas son unos 3 segundos de una tarea nocturna.** Para hacerse
una idea de si 5.000 es mucho: con 1.000 clientes de pago a 5 alertas cada uno.
No hay ninguno todavía. Esto no necesita acotarse — ni ahora, ni previsiblemente
en los dos primeros años.

Lo que sí conviene anotar, porque es gratis de arreglar el día que estorbe: el
matcher **relee la lista entera de alertas una vez por subasta**.

| Escenario | Consultas totales | `SELECT` sobre `alerta` | Filas de alerta leídas |
|---|---:|---:|---:|
| 1.000 alertas, lote 10 | 1.072 | 10 | ~10.000 |
| 1.000 alertas, lote 50 | 5.352 | 50 | ~50.000 |

Cincuenta consultas que devuelven mil filas cada una, para volver a evaluarlas en
Python. Sacar esa consulta fuera del bucle es un cambio de tres líneas. **No se
hace ahora** porque 3 segundos no molestan a nadie y porque un cambio no pedido en
el camino crítico del aislamiento entre organizaciones se revisa peor de lo que
rinde.

---

## 3. Notificar: aquí sí está el problema, y es de producto

El número de notificaciones no es N ni A: es **N × (alertas que casan)**.

| Alertas | Lote | Casan | Notificaciones | Tiempo (sin red) |
|---:|---:|---:|---:|---:|
| 100 | 50 | 10 | **500** | 0,39 s |
| 500 | 50 | 50 | **2.500** | 1,12 s |
| 1.000 | 50 | 100 | **5.000** | 1,98 s |

Léase la primera fila despacio, porque no es una cifra de rendimiento: **10
usuarios con una alerta amplia reciben 500 notificaciones entre los diez, 50 cada
uno, de una sola pasada nocturna.**

Eso, en modo instantáneo, son 50 correos de golpe a las 3 de la mañana. Ningún
usuario real aguanta eso una segunda noche: se da de baja, y con razón. El límite
que importa no es el de la base de datos, es el de la paciencia de quien recibe.

**Y el modo por defecto es `instantaneo`** (`app/models.py:262`). Es el que tenía
sentido cuando una notificación equivalía a un acto humano deliberado. Con
captación automática deja de tenerlo.

### Esto no es un problema de escala. Es el modo de fábrica

Conviene dejarlo escrito con todas las letras, porque la cifra invita a leerlo mal:
**los 50 correos por cabeza ocurren con diez usuarios, no con cinco mil.** No hace
falta crecer para que pase. Pasa la primera noche que el conector traiga un lote
normal, con la base de usuarios que haya.

De ahí que el remedio no sea un límite de envíos ni ninguna otra forma de recortar
el síntoma. Poner un tope de «como mucho N avisos por usuario y lote» dejaría a ese
usuario sin ver las subastas que sí encajaban con su alerta, que es justamente lo
que ha pedido. **La pregunta correcta es cuál debe ser el modo por defecto**, y esa
es una decisión de producto, no una optimización.

El agrupado ya existe y no hay que construir nada: `modo=digest_diario` deja las
notificaciones pendientes y la tarea `beat` envía **un** correo con todo. Lo que
falta es decidir. Las opciones, para que la 17-B las tenga delante:

- **`digest_diario` como valor por defecto para todo el mundo**, y el instantáneo
  como algo que el usuario activa a sabiendas.
- **El modo por defecto depende del origen**: instantáneo sigue significando
  instantáneo para lo que capta un humano de su organización —un acto puntual y
  deliberado—, y la ingesta de plataforma agrupa siempre.
- **El usuario elige en el alta**, con el agrupado preseleccionado.

No se elige aquí. Se elige en la 17-B, con la decisión escrita como tal y no
heredada de un valor por defecto que se puso cuando notificar equivalía a un acto
humano deliberado (`app/models.py:262`).

---

## 4. El despacho síncrono dentro de la ingesta

`evaluar_subasta` termina recorriendo las notificaciones creadas y, para las de
modo instantáneo, llama a `enviar_notificacion` **en línea**, dentro de la propia
tarea de ingesta. Con las cifras de arriba:

- **5.000 consultas extra** solo para releer preferencias, una por notificación
  (`obtener_preferencias` dentro del bucle). Medido: 5.352 → 10.352 consultas al
  pasar de digest a instantáneo, con las mismas 5.000 notificaciones.
- **Y 5.000 llamadas HTTPS secuenciales** a Postmark/SES en cuanto haya proveedor.
  Estimando 100–300 ms por llamada —rango habitual, **no medido aquí**—, son
  **entre 8 y 25 minutos de tarea nocturna, en serie, sin reintentos**. Si el
  proveedor tarda o corta, la tarea se alarga o muere a mitad, y no hay cola: las
  notificaciones ya están creadas en `pendiente`, así que no se pierden, pero
  tampoco salen.

### Lo peligroso no es la lentitud: es dónde se irá a buscar el fallo

El envío vive dentro de la tarea de ingesta, así que **cuando reviente el correo,
lo que fallará ante quien mire es la captación.** La tarea nocturna aparecerá en
rojo, o colgada, o a medias; el registro dirá que la ingesta no terminó. Y no será
verdad: las subastas estarán guardadas y confirmadas —el `commit` ocurre antes del
despacho, a propósito—, mientras la causa real estará en un proveedor de correo que
tardó, cortó la conexión o devolvió un 429.

Ese es el modo de fallo caro: no el minuto perdido, sino **la hora que alguien
dedicará a depurar el parser del BOE por un problema que está en Postmark**. Un
fallo que apunta al sitio equivocado cuesta más que uno que se cae de frente.

Por eso el punto 2 de §5 no es afinado ni optimización: **el envío tiene que estar
fuera del camino de la ingesta antes de conectar un proveedor real.** Mientras no
haya proveedor no puede pasar nada —el notificador registra en log y devuelve
`False`—, así que la frontera es exactamente esa: configurar `EMAIL_PROVIDER` en
producción sin haber movido antes el envío es lo que no debe hacerse.

---

## 5. Qué hay que hacer, y cuándo

**Ahora (17-A): nada más que esto.** No hay usuarios reales, no hay proveedor de
email configurado y el conector todavía no descarga nada. Acotar hoy sería
optimizar contra cifras inventadas.

**Antes de encender la ingesta diaria contra usuarios reales**, que es la 17-B, hay
que cerrar dos cosas. Quedan aquí escritas para que sean condición de esa fase y
no un descubrimiento posterior:

| # | Qué | Naturaleza | Por qué no puede esperar más allá de la 17-B |
|---|---|---|---|
| 1 | **Decidir cuál debe ser el modo de notificación por defecto** (§3), con las tres opciones de arriba sobre la mesa. **Dueña: la ficha de la Fase 17-B** (`PLAN_FASES.md`), que no cierra su PR sin resolverla | **Decisión de producto pendiente**, no optimización | 50 correos por cabeza y noche **con diez usuarios**. No hace falta crecer para que ocurra: ocurre la primera noche |
| 2 | **Sacar el envío del camino de la ingesta**, a su propia tarea | Diseño, no rendimiento | Cuando reviente el correo, lo que parecerá roto es la captación, y se depurará en el sitio equivocado (§4). Frontera dura: **antes de configurar un proveedor real** |

**Lo que NO hay que hacer ahora**, dicho explícitamente para que nadie lo haga por
si acaso: sacar la consulta de alertas del bucle, resolver el emparejamiento en
SQL, o limitar cuántas notificaciones puede generar un lote. Lo primero rinde 3
segundos; lo segundo mete lógica de negocio en una consulta justo donde vive el
aislamiento entre organizaciones; lo tercero es una decisión de producto que se
toma con usuarios delante, no antes.

**Disparadores para volver aquí**, medibles sin instrumentación nueva:

- más de **5.000 alertas activas** en la plataforma → sacar la consulta del bucle;
- una ingesta que pase de **5 minutos** → el despacho ya se comió la tarea;
- la primera baja de un usuario citando exceso de correos → el punto 1 no se
  decidió, y la decisión la ha tomado el usuario yéndose.

---

## 6. Reproducir estas cifras

```bash
cd backend
python scripts/medir_matcher.py            # tiempos por bloque
python scripts/medir_matcher_consultas.py  # consultas y filas por lote
```

Ambos usan una base SQLite desechable y no necesitan variables de entorno: se las
ponen ellos. Van versionados a propósito, para que dentro de un año se pueda
comprobar si estas cifras siguen siendo ciertas en vez de creérselas.

Cada medición parte de una base vacía. La primera versión de `medir_matcher.py`
acumulaba alertas entre bloques y daba cifras que no medían lo que decían medir;
si se amplían, que sea con `drop_all`/`create_all` por medición.
