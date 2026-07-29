# MEJORAS — SEIS

Registro de mejoras de producto, defectos de experiencia de usuario y líneas de expansión.

**Distinto de `docs/PENDIENTES.md`**, que recoge el backlog técnico y la deuda de las fases
ya ejecutadas. Aquí va lo que surge de **usar el producto**, no de construirlo.

---

## A · Hallazgos de la primera validación funcional (2026-07-29)

Detectados recorriendo la aplicación de extremo a extremo con Docker levantado y un análisis
real completado hasta el paso 11. No son suposiciones: cada uno se reprodujo en la interfaz y
se contrastó después contra el código.

### A1 · Los campos numéricos opcionales vacíos rompen el envío al backend — **PRIORIDAD ALTA**

**Síntoma.** Al pulsar «Siguiente» en el paso 10 del asistente, el backend responde con ocho
errores `float_parsing` simultáneos: `activo.lat`, `activo.lng`, `subasta.puja_minima`,
`zona.precio_m2_p85`, `reforma.coste_m2_override`, `costes.atrasos_comunidad_ibi`,
`costes.adquisicion_fija_override` y `costes.tenencia_mensual` — todos con `"input": ""`.

**Causa, verificada en el código.** `frontend/lib/schema.ts:4-7` define `optNum`, un
`z.preprocess` que convierte `""` en `undefined`. Esa conversión **solo se aplica al validar**.
Pero `aPayload()` (`schema.ts:165-198`) construye el cuerpo de la petición desde
`form.getValues()` con propagación directa (`...v.activo`, `...v.costes`, `...v.reforma`), sin
pasar por el esquema. Resultado: el formulario valida bien y deja avanzar, pero envía `""` en
lugar de omitir el campo, y el backend lo rechaza con razón.

**Impacto.** Bloquea el flujo principal del producto salvo que el usuario rellene con `0` todos
los campos marcados como «opcional» — es decir, **la etiqueta «opcional» de la interfaz es hoy
falsa**. Un usuario sin acompañamiento se queda atascado sin entender por qué.

**Arreglo propuesto.** Que `aPayload` consuma el resultado de `esquemaAnalisis.parse(...)` en
lugar de los valores en crudo, o que normalice `""` → `undefined` internamente. Debe
acompañarse de una prueba que envíe el formulario con todos los campos opcionales vacíos.

### A2 · Rellenar con `0` produce un informe silenciosamente distinto — **PRIORIDAD ALTA**

Consecuencia directa de A1 y **más grave que él**. El rodeo natural del usuario ante el error
—escribir `0`— no es equivalente a dejar el campo vacío:

- **Vacío** significa «no lo sé» → el motor aplica su estimación prudente al alza (P5).
- **`0`** significa «he verificado que es cero» → el motor lo toma como dato cierto.

En campos como `costes.atrasos_comunidad_ibi`, `costes.tenencia_mensual` o
`costes.adquisicion_fija_override`, escribir `0` **elimina costes reales del cálculo** y mejora
artificialmente ROI, margen de seguridad y escalera de precios. El informe sale verosímil y no
advierte de nada.

Es una vulneración de los principios P4/P5 introducida por un defecto de interfaz, no por el
motor. El motor es correcto; lo que le llega, no.

**Ocurrió de verdad en la sesión de validación, y no es teórico.** Para rodear A1 se puso `0`
en «€/m² manual» del paso 8. `m05_reforma.py:15` hace:

```python
coste_m2 = r.coste_m2_override if r.coste_m2_override is not None     else float(params.get(f"reforma.baremos_m2.{nivel}"))
```

`0` no es `None`, de modo que el motor tomó el baremo como **0 €/m²** y el informe salió con
`Reforma: ligera · -597 €` para un flip integral de 82 m² en estado de conservación malo, que
debería costar decenas de miles de euros. **El análisis completo quedó contaminado**: ROI 25 %,
margen de seguridad 27,2 % y toda la escalera de precios están inflados, y **nada en la interfaz
lo advirtió**. El único indicio visible fue un coste de reforma negativo, que un usuario sin
formación técnica no tiene por qué interpretar como una alarma.

**Refuerza el arreglo de A1 y añade dos exigencias propias:**
- Validar que los importes monetarios y los `€/m²` no puedan ser negativos ni cero cuando
  actúan como *override* de un baremo, o exigir confirmación explícita del usuario.
- Mostrar en el informe qué valores fueron **declarados por el usuario** y cuáles **estimados
  por el motor**. Hoy son indistinguibles, y esa distinción es justamente lo que separa un dato
  cierto de una estimación prudente.

### A3 · Derivar coordenadas y fiscalidad desde la dirección — **PRIORIDAD MEDIA**

Hoy el usuario introduce latitud y longitud a mano. Se propone geocodificar a partir de
dirección/municipio (Catastro, Nominatim o similar) y, con las coordenadas,
**autoseleccionar la comunidad autónoma**, que determina la fiscalidad T3.

**Por qué importa más de lo que parece.** En la prueba se analizó un inmueble de Puerto del
Rosario (Fuerteventura) con la CCAA en «Madrid» por defecto. Canarias no aplica ITP peninsular
sino IGIC, de modo que el resultado fiscal era incorrecto y **nada en la interfaz lo advertía**.

Como mínimo, debería avisarse cuando las coordenadas y la CCAA declarada no se correspondan.

**Reproducido en la sesión.** Se analizó un activo en Puerto del Rosario (Fuerteventura) con
coordenadas de Madrid (40.4168, -3.7038) puestas a mano por indicación durante la validación:
el pin del mapa aparece en Madrid, no en Canarias. Confirma visualmente que nada en el
formulario cruza dirección, coordenadas y CCAA.

**Viabilidad técnica confirmada — no requiere IA.** Geocodificar una dirección (convertirla en
coordenadas) es una tarea de datos, no de lenguaje. Existen vías gratuitas o de bajo coste que
no consumen créditos de ningún modelo: Nominatim (OpenStreetMap) o la API pública del Catastro
español, más precisa para el caso de SEIS. Es una llamada HTTP igual que las que ya hace el
resto del backend. Si se decide reservar la función a planes de pago, sería una decisión de
producto (diferenciación de plan), no una limitación de coste de IA.

### A4 · No existe el perfil inversor del usuario ni su capital disponible — **BRECHA FUNCIONAL**

`CLAUDE.md` §1 describe el producto diciendo que «un usuario define su perfil inversor y
**capital disponible**». Verificado en el código: **no está implementado**.

- `capital` no aparece en `app/engine/contracts.py`. Las únicas apariciones en el backend son
  el *coste de capital* del motor (`m12_decision.py:110`), un parámetro global sin relación con
  el patrimonio del usuario.
- `PerfilInversion` (`models.py:216-220`) tiene solo `codigo`, `nombre` y `parametros`, y **no
  está asociado a ningún usuario**: son plantillas de estrategia globales.
- La pantalla `/configuracion` no es «mi perfil»: es un editor de esas plantillas globales, de
  modo que un usuario que cambie ahí el ROI objetivo **se lo cambia a todos**.

**Consecuencia.** El análisis no puede hoy descartar una oportunidad por quedar fuera del
alcance financiero del inversor, ni personalizar umbrales por usuario. Es la primera acción que
un usuario esperaría poder hacer, y no existe.

**Decisión pendiente:** si entra en la Fase 10 —que ya toca el modelo `Usuario` para el alta
self-service— o si merece fase propia.

### A5 · Formato del PDF mejorable — **PRIORIDAD BAJA**

El informe se genera y se descarga correctamente desde «Mis informes», pero su maquetación es
mejorable. No esencial: no afecta al cálculo ni bloquea ningún flujo.

### A6 · La matriz de riesgos no explica por qué cada riesgo lo es — **PRIORIDAD ALTA**

**Síntoma.** El panel «Riesgos (matriz P×I)» muestra una gráfica de barras con el `score` de
cada dimensión (jurídico, ocupación, técnico, comercial, mercado) y el agregado
`RA 40 · banda medio · dominancia una_alta`. Debajo, solo aparecen dos líneas, y ambas son
**acciones a realizar**, no explicaciones:

```
documental: Subsanar: posesion_verificada; Subsanar: fotos_exterior; ...
tecnico:    Visita interior (o con cerrajero tras adjudicación) ...
```

El usuario ve que «comercial» puntúa alto, pero **no puede saber por qué**. Y en un producto
cuyo principio rector es que la decisión sea *auditable y explicable* (P2), eso es una carencia
de fondo, no cosmética: un comité de inversión no puede defender una decisión que no sabe
justificar dimensión a dimensión.

**El dato ya existe y se está descartando.** Verificado en el código:

- `backend/app/engine/contracts.py:255-264` — `RiesgoOut` incluye `probabilidad`, `impacto`,
  `score`, `nivel`, `mitigable`, `condiciones` **y `evidencias`**.
- `frontend/lib/types.ts:5` — `RiesgoDim` declara `evidencias: string[]`, de modo que el
  campo **viaja hasta el navegador**.
- `frontend/components/resultado.tsx:107` — el panel filtra por
  `riesgos.dimensiones.filter((r) => r.condiciones.length)` y pinta únicamente
  `condiciones`. **`evidencias` no se usa en ninguna parte del componente.**

No hay que calcular nada nuevo en el motor: hay que **mostrar lo que ya llega**.

**Propuesta.**
1. Mostrar `evidencias` por dimensión, que es el «porqué» que hoy se pierde.
2. Desglosar `probabilidad × impacto` junto al `score`, en lugar de solo el agregado: un
   score de 14 no significa lo mismo si viene de probabilidad alta con impacto bajo o al revés,
   y la estrategia de mitigación es distinta en cada caso.
3. Como mínimo, hacerlo obligatorio para las dimensiones en nivel **alto** y **medio**; para
   las bajas puede quedar plegado.
4. Distinguir visualmente lo que es **explicación** (evidencias) de lo que es **acción**
   (condiciones). Hoy solo se ve lo segundo y se confunde con lo primero.
5. Explicar también el agregado: qué significa `banda medio` y, sobre todo, qué es
   `dominancia una_alta` — un usuario no tiene forma de saber que eso indica que una única
   dimensión alta está gobernando el resultado por encima del promedio (principio P6: los vetos
   y las dominancias no se compensan con promedios).

**Alcance.** Es trabajo de frontend sobre `resultado.tsx`. Conviene revisar de paso si el
informe en PDF y el `informe_markdown` sí incluyen las evidencias, porque entonces la carencia
sería solo de la vista web y la incoherencia entre ambos formatos sería en sí misma un defecto.

### A7 · Falta ayuda contextual (tooltips) en métricas y riesgos — **PRIORIDAD MEDIA**

Un usuario sin formación financiera/jurídica no tiene forma de saber, sin salir de la pantalla,
qué significan «Precio ideal», «Precio máximo», «RVC», o por qué una dimensión de riesgo se
llama «comercial» o «liquidez». Se propone un icono de ayuda junto a cada métrica y cada
dimensión de riesgo que, al pasar el cursor, muestre una explicación breve no editable.

Relacionado con A6: los tooltips explican *qué es* cada cosa; A6 explica *por qué* tiene el
valor que tiene en este análisis concreto. Son complementarios, no la misma mejora.

### A8 · Las pestañas «Informe» y «Datos de entrada» tienen un formato poco cuidado — **PRIORIDAD BAJA**

En el detalle de un análisis, las pestañas «Informe» (el `informe_markdown` en crudo) y «Datos
de entrada» (el volcado de los 11 pasos) se muestran con una maquetación por detrás del resto
de la aplicación — parecen datos técnicos sin repasar visualmente, no una parte más del
producto. No afecta al cálculo; es una mejora de presentación, igual que A5 con el PDF.

### A9 · El listado de subastas no permite interactuar con ninguna fila — **PRIORIDAD MEDIA**

**Confirmado en el código** (`frontend/app/(app)/subastas/page.tsx`): cada fila del listado es
un `<div>` puramente informativo, sin `onClick`, enlace ni botón. Hoy la pantalla solo sirve
para *mirar* subastas captadas, no para actuar sobre ellas: no hay forma de ver el detalle, de
iniciar un análisis completo a partir de una subasta, ni de marcarla como revisada o descartada.
Dado que el propio aviso de la pantalla dice que la puntuación exprés «sirve para priorizar qué
analizar en profundidad» (comentario en el código, línea 9-11), la ausencia de un botón
«Analizar esta subasta» que precargue el asistente es la pieza que falta para cerrar ese flujo.

**Nota aparte, no un defecto:** que las subastas sin puntuar desaparezcan al fijar cualquier
valor de filtro (incluido `0` o `1`) es comportamiento **intencional y ya documentado** en la
propia interfaz («las subastas sin puntuación quedan fuera del filtro», texto de ayuda bajo el
campo). Es contraintuitivo —uno esperaría que «mínimo 0» signifique «todas»— pero no es un bug.

### A10 · No existe forma de consultar el registro de auditoría — **PRIORIDAD MEDIA**

La pantalla «Administración → Gobernanza y auditoría» muestra únicamente **texto estático**
explicando el principio de trazabilidad (P1) — no es un registro real ni consultable.

**Verificado en el backend:** la tabla `Auditoria` **sí se rellena de verdad** en varias
acciones (`captacion.py:81`, `notificaciones.py:128,150,161` insertan filas con autor y delta).
Pero **no existe ningún endpoint** que la exponga por lectura. El dato se guarda con disciplina
y no se puede ver desde ninguna parte, ni con permisos de superadmin.

**Propuesta.** Añadir un endpoint de solo lectura (paginado, filtrable por entidad/autor/fecha) y
una pantalla de listado en Administración. Es la funcionalidad que la propia pantalla promete
tener y hoy no tiene.

### Comprobado y correcto en la misma sesión

- Dashboard, listado de inversiones y comparativa muestran estados vacíos explícitos y bien
  redactados, no tablas en blanco sin explicación.
- Recorrido completo de Mapa, Subastas, Alertas, Equipo, Reglas, Parámetros y Administración
  (2026-07-29): alta de miembro de equipo con rol, creación de alerta con pausa/eliminación,
  catálogo T2 completo de vetos y techos de semáforo con versión y vigencia, árbol T3 completo
  de parámetros editable y auditado, validación de email duplicado en alta de usuario — todo
  funcionando según lo esperado.
- Tras guardar el análisis, el **dashboard y el mapa se actualizan** correctamente.
- El menú lateral oculta «Conocimiento» a quien no es superadmin y «Mi equipo» a quien no es
  propietario, conforme a `layout.tsx:10-11`.
- El motor experto produce un informe completo y coherente: semáforo, ICO desglosado en 8
  dimensiones, RA con matriz P×I, escalera de precios con límite infranqueable, tres escenarios
  con probabilidades y condiciones para proceder.
- Los avisos de subsanación reflejan exactamente la documentación no aportada, confirmando que
  P4 («la ausencia de datos penaliza») funciona de verdad.

---

## B · Línea de expansión: análisis de inversión inmobiliaria fuera de subasta

**Idea.** Reutilizar la plataforma para analizar **inmuebles de portales inmobiliarios
convencionales** (Idealista, Fotocasa, particulares, agencias), no solo subastas.

**Motivación.** El mercado de subastas es un nicho: exige tolerancia al riesgo jurídico, capital
disponible con rapidez y aceptar comprar sin visitar el interior. El mercado libre es
órdenes de magnitud mayor y comparte **la mayor parte del aparato de análisis**: valoración por
comparables, costes de adquisición y tenencia, presupuesto de reforma, escenarios de
rentabilidad, riesgo de mercado y liquidez.

### Estrategias a cubrir

| Estrategia | Qué cambia respecto del motor actual |
|---|---|
| **Compra para alquilar** (buy-to-let) | La salida no es una venta sino un flujo de rentas: rentabilidad bruta y neta, cash-on-cash, cobertura del préstamo (DSCR), vacancia, morosidad, IRPF del arrendamiento |
| **Compra para vender** (sin obra) | Prácticamente el motor actual sin el módulo de reforma |
| **Compra, reforma y venta** (flip) | El motor actual, quitando la capa de riesgo jurídico propia de la subasta |
| **Compra, reforma y alquiler** | Combinación de reforma con salida por rentas |
| **Obra nueva / sobre plano** | Riesgo de entrega, avales, IVA en lugar de ITP, plazos largos |

### Diferencia estructural más importante: la financiación con préstamo

Hoy la financiación existe (`FinanciacionInput`) pero el escenario que se probó fue
`100 % equity (cash)`, coherente con la subasta judicial, donde hay que pagar el remate en
plazo legal breve y sin condición suspensiva. **En el mercado libre la hipoteca es la norma**,
y eso cambia el análisis de raíz:

- **Apalancamiento**: el ROI sobre capital propio deja de coincidir con el ROI del activo.
- **Cash-on-cash** pasa a ser la métrica principal, por delante del ROI.
- **Condicionantes bancarios**: LTV máximo, tasación oficial (que puede quedar por debajo del
  precio de compra), plazo, tipo fijo o variable, comisiones, y sobre todo la **capacidad de
  endeudamiento del comprador** — que enlaza directamente con A4, el perfil inversor.
- **Riesgo de tipos** en variable, y de refinanciación.
- **Condición suspensiva de financiación**, que en el mercado libre sí existe y cambia el perfil
  de riesgo por completo.

### Qué se reaprovecha y qué es nuevo

**Se reaprovecha casi todo el motor:** M03 valoración, M04 mercado, M05 reforma, M06 costes,
M08 riesgo urbanístico/técnico, M10 riesgo comercial y liquidez, M11 rentabilidad y escenarios,
M12 decisión, M14 informe. También la gobernanza T2/T3 de reglas y parámetros versionados, el
multi-tenancy, las alertas y el sistema de notificaciones.

**Es nuevo o cambia sustancialmente:**
- Captación desde portales inmobiliarios en lugar de boletines de subasta (con la cuestión
  legal de los términos de uso de cada portal, que hay que resolver antes de construir nada).
- Un módulo de financiación hipotecaria con capacidad de endeudamiento.
- Un módulo de rentabilidad por rentas para las estrategias de alquiler.
- M07 (riesgo jurídico de subasta: cargas, purga, posesión) queda en gran parte fuera; lo
  sustituye una diligencia registral más ligera.
- La escalera de precios cambia de significado: en subasta es una estrategia de puja; en
  mercado libre es un rango de negociación.

### Cuestiones a decidir antes de planificarlo

1. ¿Producto separado, o modo adicional dentro de SEIS? Afecta al modelo de datos, al
   *pricing* y al posicionamiento.
2. ¿Cómo se captan los inmuebles? Los portales tienen términos de uso restrictivos frente al
   scraping. Puede requerir acuerdos, API oficiales o alta manual.
3. El caso dorado §19 valida el motor de subastas. Una expansión así **necesitaría su propio
   caso dorado** por estrategia, o la garantía de determinismo se diluye.
4. Encaje temporal: es una expansión de producto, no una fase del plan maestro actual
   (que llega hasta la 20, beta cerrada). Probablemente sea material para **después del
   lanzamiento**, salvo que se decida pivotar.
