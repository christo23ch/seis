---
tipo: adr
fase: "[[Fase-16-auditoria-seguridad]]"
estado: aprobado
supersede: ""
superado_por: ""
tags:
  - tipo/adr
  - estado/aprobado
  - fase/16
  - area/proceso
  - area/calidad
---

# ADR-0014: todo mecanismo de verificación declara qué NO cubre, y falla antes que pasar en vacío

## Contexto

En cuatro sesiones seguidas, este proyecto ha encontrado cuatro defectos con la misma forma. No es una racha: es una clase.

| # | Mecanismo | Lo que parecía cubrir | Lo que cubría de verdad |
|---|---|---|---|
| 1 | El filtro de tenant del matcher | «las alertas de esta organización» | con `organizacion_id=None`, **las de nadie** — `== None` significa «usuarios sin organización» |
| 2 | Los tests de la siembra | «que `init_db.main()` funciona» | solo en `development` y `test`, donde `create_all` sí corre y la mutación `if creado:` es invisible |
| 3 | El validador de `RegistroBody` | «los consentimientos son obligatorios» | solo cuando el campo viene; **Pydantic v2 no valida los valores por defecto** |
| 4 | La red derivada del `metadata` | «todo lo que cuelga de `usuario`» | solo lo unido por **clave foránea**; `auditoria` guarda el correo por VALOR y es invisible |

En los cuatro casos:

- **El síntoma fue el verde, no un rojo.** Ninguno se manifestó como fallo. El 2 y el 3 se descubrieron porque la suite siguió pasando cuando debía haberse roto.
- **El mecanismo funcionaba correctamente dentro de su alcance.** Ninguno tenía un error de implementación. Lo que fallaba era la creencia sobre su alcance.
- **Ese alcance no estaba escrito en ninguna parte**, así que quien lo leía asumía el alcance máximo. Razonablemente: nada le decía otra cosa.

El diagnóstico, en una frase: **las herramientas que usamos para verificar no declaran su alcance, y quien las lee asume el mayor.**

Arreglar la instancia —lo que hicieron las fases 17-A, la puerta y la 14— no arregla la clase. La quinta va a ocurrir.

## Decisión

**Todo mecanismo de verificación documenta explícitamente QUÉ NO CUBRE, junto al mecanismo. Y donde sea detectable, falla en vez de pasar en vacío.**

Tres reglas:

1. **Declaración de alcance, junto al código.** Un test derivado del esquema, una limpieza por nombre de columna, un auditor de esquemas, un matcher, un detector: todos llevan una sección «QUÉ NO CUBRE» en su propio docstring. **No en un documento aparte**, porque quien está a punto de confiar en el mecanismo está leyendo el mecanismo, no el documento.
2. **Rojo antes que verde vacío.** Si un mecanismo puede detectar que no está en condiciones de hacer su trabajo —la colección que recorre está vacía, la tabla que busca no existe, la configuración que necesita falta—, debe **fallar**. Un verde que no comprobó nada es peor que un rojo, porque produce confianza.
3. **Entra en los prompts.** El bloque de contexto de todas las fases lo exige, igual que exige capturas en las fases de frontend.

## Justificación

### Por qué junto al código y no en un documento

Es la diferencia entre una advertencia que se lee y una que se archiva. El caso 4 lo ilustra: el hecho de que `auditoria` no tuviera clave foránea **estaba en el esquema**, a la vista de cualquiera, desde la Fase 1. Lo que faltaba no era el dato, era el dato **en el sitio donde se decide confiar**.

### Por qué «fallar» y no solo «avisar»

Un aviso en un log lo lee alguien que ya está buscando el problema. En el caso 1.5 de la auditoría, `tablas_hijas_de` con el `metadata` vacío devolvía el conjunto vacío y el `assert not sin_cubrir` de quien la llamaba **pasaba sin comprobar nada**. Un aviso ahí habría estado en la salida de una suite verde, es decir, en ninguna parte.

## Dónde NO llega esta regla

Esto es la parte importante del ADR, y va aquí y no en una nota al pie: **una regla que aparente cubrir más de lo que cubre sería el mismo fallo otra vez, un nivel más arriba.**

### 1. La declaración de alcance no se puede verificar

«QUÉ NO CUBRE» es prosa. Nada comprueba que sea cierta ni que esté completa. Y hay un efecto perverso: **un mecanismo con una declaración de alcance equivocada resulta MÁS creíble que uno sin ella**, porque parece haberlo pensado.

Peor aún: los cuatro casos históricos son casos en los que **el autor no veía el hueco**. Si lo hubiera visto, lo habría arreglado, no documentado. De modo que la regla captura los huecos que el autor conoce y acepta —que son valiosos— y **no captura los que motivaron la regla**.

Esta limitación no tiene arreglo dentro de la propia regla.

### 2. «Fallar en vacío» solo cubre el vacío, no el alcance equivocado

La regla 2 detecta que un mecanismo **no está en condiciones** de trabajar. No detecta que trabaje bien sobre el dominio equivocado.

El caso 4 es exactamente eso: la red del esquema **no estaba vacía**. Devolvía cinco tablas, correctamente, y era completa para las claves foráneas. Ninguna guarda de vacío la habría puesto en rojo, porque no le faltaba nada de lo que sabía buscar. Le faltaba una categoría entera que no sabía que existía.

**Los casos 1, 3 y 4 no los habría detectado la regla 2.** Solo el 1.5 de esta auditoría, que es el más leve de todos.

### 3. No se puede exigir mecánicamente

No hay linter que compruebe «este mecanismo declara su alcance». Se podría exigir que ciertos ficheros contengan la frase, y eso produciría la frase, no el pensamiento. Sería culto al cargo, y además daría una señal falsa de cumplimiento — otra vez el mismo fallo.

Queda como disciplina revisable en el PR, con lo que eso implica: depende de personas.

### 4. Algunos mecanismos no pueden fallar sin causar más daño del que evitan

`app/core/red.py` es el ejemplo vivo, y por eso se decidió en esta misma fase. Cuando no puede resolver la IP del cliente, **no falla**: cuenta, registra y sigue. Rechazar la petición dejaría el sitio inaccesible por una cabecera mal configurada, y degradar la readiness sacaría de rotación a **todas** las réplicas a la vez, porque la mala configuración sería idéntica en todas.

Así que ahí la regla se cumple en su versión débil —hablar— y no en la fuerte —fallar—. La forma correcta de enunciarla es: **«que lo diga en voz alta o que falle»**, no «que falle».

### 5. Lo que de verdad ha encontrado los cuatro casos

Conviene decirlo, porque es donde está el rendimiento real y no quiero que esta regla se lleve un crédito que no le corresponde: **los cuatro se encontraron con evidencia mecánica, no con documentación.**

- Un verde donde debía haber rojo (casos 2 y 3).
- Ejecutar contra otro motor —PostgreSQL— (el truncamiento de la Fase 14).
- Aplicar la mutación a mano y mirar (los cuatro, al confirmarlos).

La declaración de alcance **hace más barato encontrar el quinto**, porque pone la duda delante de quien lee. No lo previene. **La práctica que lo previene es la mutación**, y esa ya es norma de este proyecto desde la Fase 17-A.

Esta regla es un complemento de aquella, no un sustituto. Si hubiera que quedarse con una, sería con la mutación — con la reserva del punto 6, que se añadió después y que conviene leer antes de fiarse de esa frase.

### 6. La propia herramienta de verificación comete el fallo que persigue

Añadido el 2026-09-11, después de la corrección de la base imponible del ITP ([[ADR-0015]]), porque **ya van dos veces que el defecto aparece dentro del mecanismo de prueba y no en el código probado**:

1. **Fase 16.** El test de caducidad de la caché de sondas **leía su valor esperado de la propia constante que estaba probando**. Pasaba con cualquier valor de esa constante, incluido uno roto.
2. **ADR-0015.** Una de las nueve mutaciones —«el informe deja de avisar de que el impuesto es un mínimo»— **sobrevivió porque la mutación era falsa**: sustituía el texto del aviso por otro texto que seguía conteniendo el aviso. Lo que sobrevivió no fue el código: fue una mutación que no mutaba nada.

Esto no es una anécdota de dos descuidos. Es la misma clase de defecto un nivel más adentro: **un mecanismo funcionando correctamente dentro de un alcance que nunca declaró**, salvo que aquí el mecanismo es el que se usa para detectar precisamente eso. Y tiene una consecuencia incómoda: la mutación, que es la práctica en la que más confía este proyecto, **no se audita a sí misma**. Una mutación que sobrevive puede significar que falta un test, o puede significar que la mutación no rompía nada — y los dos casos se ven exactamente igual en la consola.

Lo único que ha funcionado contra esto es barato y no es una regla nueva: **ante una mutación que sobrevive, mirar el diff aplicado antes que la lista de tests**, y preguntarse si el comportamiento mutado es de verdad distinto. En los dos casos citados, el diff lo decía a la primera.

No se convierte en cuarta regla porque no se puede exigir mecánicamente (punto 3), y una regla que solo produce la frase no vale nada. Queda escrito para que quien lea esto dentro de unos meses vea el patrón **nombrado**, no solo corregido en dos sitios distintos.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Un documento central de «límites conocidos» | Es donde ya estaba el dato del caso 4 —en el esquema, a la vista— y no sirvió. La información tiene que estar donde se decide confiar |
| Exigirlo con un linter | Produce la frase, no el pensamiento, y añade una señal falsa de cumplimiento. Culto al cargo |
| Solo la regla de mutación, sin declaración de alcance | La mutación demuestra que un test sirve **para lo que prueba**; no dice nada de lo que ni siquiera se intentó probar. Son complementarias |
| Hacer que todo falle en vacío, sin excepciones | `red.py` demuestra que a veces fallar causa más daño. Una regla sin excepciones habría forzado la excepción a escondidas |

## Consecuencias

### Positivas

- Quien va a confiar en un mecanismo lee sus límites en el mismo sitio.
- Los huecos **conocidos y aceptados** dejan de ser folclore oral. Los cinco de esta fase están escritos junto a su código.
- La regla 2 convierte una clase concreta de verde vacuo en rojo, verificado en dos sitios.
- Obliga a escribir el alcance al diseñar, que es cuando se piensa en él.

### Negativas / deuda asumida

- **No previene la clase de defecto que la motiva.** Ver «Dónde NO llega», punto 1. Es una mitigación, no una solución.
- **Depende de personas** y no es exigible mecánicamente.
- **Puede degenerar en ruido.** Una declaración de alcance en cada función sería ilegible; se aplica a **mecanismos de verificación**, no a todo el código, y esa frontera es de criterio.
- **Riesgo de falsa confianza**, que es el peor de todos: un «QUÉ NO CUBRE» incompleto se lee como exhaustivo. Se mitiga escribiendo también, como aquí, dónde no llega la propia declaración.

## Aplicación en esta fase

Llevan declaración de alcance junto al código: `app/core/datos_personales.py`,
`app/core/cabeceras.py`, `app/api/salud.py` (caché de la sonda), `app/core/red.py`
(por qué avisa en vez de fallar) y `tests/escenario_rgpd.py`.

Fallan en vez de pasar en vacío: `tablas_hijas_de` (metadata vacío y padre
inexistente) y `test_esquemas.py` (menos esquemas de los esperados).

## Relacionado

- Fase: [[Fase-16-auditoria-seguridad]] · `docs/AUDITORIA_SEGURIDAD.md` §1
- [[ADR-0012-un-solo-camino-de-borrado-de-personas]] y [[ADR-0013-la-purga-anonimiza-la-auditoria]] — los dos mecanismos cuyo alcance motivó el caso 4
- [[ADR-0015-base-imponible-del-itp-sobre-el-mayor-valor]] — donde apareció la mutación falsa del punto 6
- `docs/PROMPTS_FASES.md` — bloque de contexto, donde la regla se hace exigible
