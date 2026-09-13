# SEIS — Sistema de diseño

**Referencia obligatoria.** A partir de aquí, **ningún prompt de frontend se ejecuta sin
referenciar este documento** (`docs/PLAN_FASES.md` §4).

> **Por qué existe.** El diagnóstico está medido en `docs/HERRAMIENTAS.md` §1: la cara del
> producto era Georgia —la serif que todo el mundo tiene por defecto—, había **nueve tamaños de
> fuente distintos** en 64 usos mientras `fontSize` aparecía **0 veces** en la configuración, y
> `focus:` aparecía **una sola vez** en las 124 líneas de `components/ui.tsx`. Sin escala escrita,
> cada sesión elegía un número plausible y seguía adelante.

---

## 0 · Lo que este documento da por supuesto, dicho en voz alta

Va primero y no en un apéndice, por la regla del [[ADR-0014]]: **un documento que aparenta cubrir
más de lo que cubre es el mismo fallo que persigue el proyecto, un nivel más arriba.**

De los cuatro supuestos con los que se abrió esta fase, **tres se cerraron dentro de ella** y uno
se traspasó con dueño. Queda esto sin verificar:

1. **El suelo de 12 px no está validado con usuarios reales.** Ver §3.1, que incluye qué pasaría
   si hubiera que subirlo. Sigue siendo un supuesto, no un hecho.
2. **El muestrario tipográfico es una pantalla, no el producto.** La elección de §2 se tomó
   mirando un fragmento de análisis; **no dice nada de cómo envejece en veinte pantallas ni en el
   PDF del informe**, que es otro medio, con otra unidad y otro renderizador.
3. **Las capturas salen de Chromium sobre Linux.** El renderizado en macOS y en Windows **no es
   idéntico**, sobre todo en los pesos finos y en el suavizado.
4. **La prueba de contraste (§4) vigila los tokens, no la interfaz.** Un color escrito a mano en
   una clase o en `globals.css` no se comprueba; tampoco las combinaciones reales de pantalla.
   Su propio alcance está declarado en la cabecera de `backend/tests/test_contraste.py`.
5. **Los estados de §5 están escritos, no implementados.** Lo único que se tocó de
   `components/ui.tsx` fueron los bordes (§4.2). Convertir los siete estados en componentes es
   trabajo de la Fase 15 y siguientes.
6. **Las pruebas de tokens miran la configuración, no la pantalla.** Una familia bien escrita que
   no llegue a cargarse —red caída en el build, subconjunto equivocado— las pasa igual. Para eso
   hace falta medir en el navegador, que es exactamente como se encontró el fallo de §2.

**Resueltos en esta fase, y por eso ya no son supuestos:** el contraste del semáforo (§4, ahora
AAA y con una prueba que lo vigila) y el borde de controles (§4, ahora 3:1).

**Traspasado con dueño:** el desbordamiento horizontal en móvil. Medido —**765-766 px de página
en un móvil de 390 px**— y demostrado que **no lo arregla ninguna tipografía**, porque el número
es casi idéntico en las cuatro opciones. Es maquetación, no letra. **Dueña: la Fase 15**, que no
cierra su PR sin resolverlo (`docs/PLAN_FASES.md`, `docs/ESTADO_ACTUAL.md`).

---

## 1 · Principios

1. **Densidad antes que aire.** Es una herramienta para decidir cuánto pujar, no una landing. La
   pantalla debe caber, no respirar.
2. **La cifra manda.** Todo número comparable en vertical va en la familia monoespaciada y con
   `tabular-nums`. Un importe que baila de fila en fila no se puede leer en columna.
3. **La carencia se ve.** Cuando el motor dice «no lo sé» —confianza 0, base imponible tomada de
   la puja, comparables insuficientes—, la interfaz lo muestra. Misma regla que el [[ADR-0015]]
   aplicó al informe.
4. **Una escala, y nadie inventa números fuera de ella.** Era la causa raíz del diagnóstico.
5. **El foco visible no es decoración**, es requisito de accesibilidad.
6. **El color nunca es el único portador.** El semáforo viaja siempre con su palabra; un riesgo
   alto se marca con etiqueta además de con tono. WCAG 1.4.1, y también sentido común: hay quien
   imprime el informe en blanco y negro.

---

## 2 · Tipografía — **DECIDIDA (2026-09-11)**

> ## Source Serif 4 en cabeceras · Inter en cuerpo e interfaz · monoespaciada del sistema en cifras

**El porqué, en las palabras del responsable del producto:** SEIS tiene que parecer software
serio para un inversor, no una demo. **Una serif bien elegida en cabeceras es el lenguaje de los
informes financieros que ese inversor ya lee** —*Financial Times*, *The Economist*, informes de
análisis—, y mantiene la distinción serif/sans que el producto ya tenía **por accidente**, ahora
como decisión.

La objeción a Inter en cuerpo —es la sans más usada del sector— se acepta a sabiendas:
**el cuerpo debe ser aburrido y legible; la personalidad va en la cabecera.**

**Descartadas, y por qué:**

- **C · Neutra suiza** (Inter Tight + Inter) — descartada explícitamente **por la razón que la
  propia propuesta daba en su contra**: es la opción con más riesgo de reproducir la queja
  original. Inter es el ajuste por defecto de la década.
- **D · Carácter editorial** (Newsreader + Public Sans) — la más distintiva, pero **envejece peor
  si el producto se vuelve más financiero**, que es la dirección prevista.
- **B · Superfamilia de ingeniería** (IBM Plex ×3) — **no está muerta: es la alternativa si algún
  día el ángulo gira** hacia lo cuantitativo/ingeniería en vez de «informe para inversor». Hoy no
  es el objetivo. Se anota aquí para que el día que se plantee no se rehaga la investigación.

**Cómo se sirven.** `next/font` las **auto-aloja en el build**: no se enlaza `fonts.gstatic.com`,
porque eso mandaría la IP de cada visitante a un tercero fuera de la UE. Contrapartida declarada:
el build necesita red la primera vez para descargarlas.

| Rol | Familia | Token |
|---|---|---|
| Cabeceras (h1-h3), cifra destacada de un índice | Source Serif 4 | `font-display` |
| Cuerpo, interfaz, formularios, tablas | Inter | `font-texto` |
| Importes, porcentajes, todo lo comparable en columna | monoespaciada del sistema | `font-cifra` |

El muestrario que sostuvo la decisión se reproduce con
`cd frontend && node scripts/tipografia-fuentes.mjs && node scripts/tipografia.mjs`.

> **Una trampa que costó encontrar, y que es la razón de `backend/tests/test_tokens_tipograficos.py`.**
> `Source Serif 4` escrita **sin comillas** en la configuración invalida la declaración
> `font-family` **entera**: CSS lee el `4` como un identificador suelto y ninguno puede empezar
> por dígito. El navegador descarta la regla **sin decir nada** y el titular cae a la fuente
> heredada. Durante un rato el documento decía «Source Serif 4 en cabeceras» y la pantalla
> mostraba Inter. **No lo vio ninguna prueba ni ninguna captura**: lo vio medir
> `getComputedStyle` en el navegador. Cuatro mutaciones, cuatro detectadas.

---

## 3 · Escala tipográfica

Siete pasos, ni uno más. Sustituye a los nueve tamaños arbitrarios del diagnóstico. Están en
`frontend/tailwind.config.ts` como `fontSize`, así que se usan por nombre: `text-menor`,
`text-h2`. **Cualquier `text-[13.5px]` que vuelva a aparecer es un error de revisión, no una
necesidad: no hay hueco que esta escala no cubra.**

| Token | px | Interlínea | Uso |
|---|---|---|---|
| `micro` | 12 | 1,5 | pie de informe, notas de tabla, chips |
| `menor` | 13 | 1,35 | celdas de tabla densa, listas de condiciones |
| `base` | 15 | 1,5 | texto de interfaz |
| `guia` | 17 | 1,5 | entradilla, valor de un índice |
| `h3` | 19 | 1,25 | título de sección dentro de una carta |
| `h2` | 24 | 1,25 | título de bloque |
| `h1` | 32 | 1,25 | título de pantalla |

> **Cuidado con una trampa que ya existía:** `globals.css` fija `html { font-size: 15px }`, así
> que **las clases de Tailwind en `rem` no miden lo que su nombre dice** (`text-sm` = 13,1 px, no
> 14). Esa discrepancia es parte de por qué la escala se fue de las manos. Los siete tokens de
> arriba están **en px** precisamente para no heredar el problema.

### 3.1 · El suelo de 12 px es un supuesto abierto

12 px como mínimo absoluto sale de la práctica habitual en productos de datos, **no de una prueba
con usuarios de SEIS** —que son inversores, un perfil que tiende a ser de más edad que la media
de un SaaS—. **No se valida por decreto.**

**Qué pasaría si hubiera que subirlo**, estimado sobre la tabla de escenarios (8 columnas, el
caso peor del producto):

| Si el suelo sube a | La escala se convierte en | Efecto en la tabla densa |
|---|---|---|
| 13 px | 13 / 14 / 16 / 18 / 20 / 26 / 34 | ~8 % más ancha. Absorbible ajustando el relleno lateral de celda de 14 a 10 px. |
| 14 px | 14 / 15 / 17 / 19 / 22 / 28 / 36 | ~17 % más ancha. **Ya no cabe en 1440 px con la barra lateral abierta**: obliga a plegar columnas o a partir la tabla. |

Dicho de otra forma: **subir un peldaño es un ajuste; subir dos es un rediseño de la tabla.** Y
como el desbordamiento en móvil ya está abierto (§0), la decisión sensata es **resolver antes el
móvil y validar el suelo después**, con la tabla ya rediseñada, en vez de tocar dos variables a
la vez.

**Cómo se cerraría este supuesto:** enseñar la pantalla de análisis a tres o cuatro usuarios
reales del perfil objetivo y preguntar por la letra pequeña del pie, que es el peor caso. No hay
sustituto automático para eso.

---

## 4 · Color

### 4.1 · El semáforo, corregido

**Estaba en el límite y se subió.** Las tres parejas críticas pasaban AA **por centésimas**
—naranja **4,50 exacto**—, y el semáforo es el elemento más leído del informe: en cuanto baja el
brillo o la pantalla está mal calibrada, deja de comunicar lo que existe para comunicar.

Ahora **todos cumplen AAA (≥7:1) sobre los tres fondos en los que aparecen**: su propio chip, la
carta blanca y el papel gris. No solo dentro del chip, porque el color también se usa como texto
suelto en mensajes y totales.

| Estado | Texto | Fondo | s/ fondo | s/ blanco | s/ papel |
|---|---|---|---|---|---|
| verde | `#0F5E2C` | `#E8F5ED` | 7,04 | 7,90 | 7,31 |
| amarillo | `#7F3A06` | `#FFF6E1` | 7,78 | 8,37 | 7,74 |
| naranja | `#8D2E09` | `#FFEADF` | 7,16 | 8,31 | 7,68 |
| rojo | `#9A1717` | `#FBE7E7` | 7,05 | 8,37 | 7,74 |

**El coste, medido, porque lo tiene:** oscurecer para ganar contraste **acerca los tonos entre
sí**, y los dos que peor se separan son justo **estados adyacentes del semáforo**. La distancia
perceptual entre el texto amarillo y el naranja cae de ΔE 13,8 a 11,8.

Se compensó **en los fondos**, que no cargan solos con el contraste: se separaron en tono —el
ámbar más amarillo, el naranja más rojo— y su distancia sube de **ΔE 4,5 a 7,3**. El chip
completo no se distingue peor que antes.

**Lo que no se hizo, y por qué:** existe un amarillo que alcanza AAA *y* se separa muchísimo del
naranja (`#615108`, ΔE 39,7). **Es oliva, no amarillo.** Eso es desnaturalizar el color
semántico, que era exactamente el límite marcado, así que se descartó.

**La red que no depende del color:** el chip lleva **siempre la palabra** («AMARILLO»,
«NARANJA»). Mientras eso se cumpla, WCAG 1.4.1 está satisfecho pase lo que pase con los tonos.
Es regla, no costumbre (§1.6).

### 4.2 · Bordes: dos tokens, y la diferencia importa

El borde único `#E4E7EC` daba **1,24 sobre blanco**, muy por debajo del 3:1 que WCAG 1.4.11 exige
a los **componentes no textuales**. Mientras un campo de formulario se delimitara solo con él, su
contorno era invisible para quien tiene baja visión. **Era incumplimiento medido, y se corrige.**

| Token | Valor | Para qué | s/ blanco | s/ papel |
|---|---|---|---|---|
| `borde-linea` | `#E4E7EC` | separar y decorar: filas de tabla, divisores. **No es un componente, no le aplica el 3:1.** | 1,24 | — |
| `borde-control` | `#8C8E92` | delimitar algo con lo que se interactúa: campo, casilla, selector, botón secundario | **3,28** | **3,03** |

**Aplicado en `components/ui.tsx`, no en una regla de elemento.** El primer intento fue
`input, select, textarea { @apply border-borde-control }` en `globals.css`, y **no sirvió de
nada**: cualquier utilidad de Tailwind en el componente (`border-slate-300`) la pisa por
especificidad. La corrección se veía en el documento y no en la pantalla. Comprobado después
midiendo el borde computado en el navegador: `rgb(140, 142, 146)`.

### 4.3 · El resto de la paleta

| Par | Ratio | Nivel |
|---|---|---|
| tinta sobre carta | 17,75 | AAA |
| tinta.suave sobre carta | 14,70 | AAA |
| primario sobre carta / blanco sobre primario | 8,34 | AAA |
| gris `#667085` sobre carta | 4,97 | AA |

### 4.4 · Esta tabla ya no es una foto de un día

`backend/tests/test_contraste.py` (18 pruebas) lee los tokens de `tailwind.config.ts` y comprueba
AAA del semáforo sobre sus tres fondos, el 3:1 del borde de control, el texto principal, y **la
distancia ΔE entre estados** — porque la mejora de contraste tiene un coste que no debe cruzar la
línea. Vive en el backend por ser el único ejecutor conectado a la CI; su propio alcance va
declarado en su cabecera.

Nueve mutaciones aplicadas, **ocho detectadas**. La que sobrevive es la guarda de recuento
(`len(tokens) >= 18`): relajarla sola no rompe nada **porque el trabajo de verdad lo hace el
inventario explícito de tokens**, que sí cae cuando un token desaparece o se renombra. Se deja
escrito en vez de fingir 9/9.

---

## 5 · Estados de los componentes

Hoy `focus:` aparece **una vez** en toda la librería. Estos siete estados son obligatorios en
cualquier componente interactivo nuevo; ninguno es opcional «si da tiempo».

| Estado | Regla |
|---|---|
| reposo | borde `borde-control`, fondo `papel-carta` |
| sobrevuelo | solo en dispositivos con puntero (`@media (hover: hover)`); nunca como única señal |
| **foco** | `outline: 2px solid primario` con `outline-offset: 2px`. **Ya está en `globals.css` para `:focus-visible` y no se anula nunca**, ni «por estética» |
| activo | desplazamiento de 1 px o cambio de fondo; nunca solo color |
| deshabilitado | opacidad 0,5 **y** `aria-disabled`; jamás gris sobre gris sin más |
| cargando | el control conserva su tamaño —nada de saltos de layout— y anuncia con `aria-busy` |
| error | borde `sem-rojo` **+ texto de error debajo**. El color solo no vale (§1.6) |

**Regla de escritura:** un componente sin sus siete estados no entra en `components/ui.tsx`. Es
la causa directa de que hoy cada pantalla los resuelva por su cuenta, o no los resuelva.

---

## 6 · Densidad y layout

El diagnóstico midió el panel derecho del login **vacío en torno a un 70 %** a 1440×900. No era
feo: era que **no había regla escrita**.

- **Anchura de contenido:** máximo 1200 px centrado; la tabla densa puede llegar al borde.
- **Relleno de carta:** 20 px vertical / 22 px horizontal. Nunca más de 24.
- **Relleno de celda en tabla densa:** 6 px vertical / 14 px horizontal. La tabla es el sitio
  donde se recorta primero si hace falta espacio (§3.1).
- **Separación entre bloques:** 22 px antes de un `h2`, 8 px después. Un solo par, no seis.
- **Nada de `justify-between` con tres hijos** para rellenar una columna: produce huecos
  desiguales, que es exactamente el defecto que se midió en el login.
- **Formularios anclados arriba**, no centrados verticalmente. Un formulario flotando en gris es
  la firma de «demo».
- **A 390 px ninguna pantalla desborda horizontalmente.** Se comprueba midiendo
  `document.documentElement.scrollWidth`, no mirando la captura. Hoy **no se cumple** en la vista
  de análisis: es el frente traspasado a la Fase 15 (§0).

---

## 7 · Preguntas que siguen abiertas

1. **El suelo de 12 px** (§3.1). No se cierra sin usuarios reales.
2. **El desbordamiento en móvil.** Con dueño: Fase 15.
3. **shadcn/ui** (`docs/HERRAMIENTAS.md` §2). Sigue abierta, y ahora **se puede decidir bien**:
   la recomendación de aquel documento era adoptarlo —si se adopta— *después* de tener tokens
   propios, y los tokens ya existen. Si se adopta, se adopta entero; media librería en cada sitio
   es el peor resultado posible.
4. **Migrar los 64 tamaños codificados a mano** (`text-[12px]` y compañía) a los siete tokens.
   La escala existe, pero las pantallas viejas aún no la usan. Trabajo mecánico, revisable con
   capturas de antes y después.

---

## 8 · Reproducir el muestrario tipográfico

```bash
cd frontend
node scripts/tipografia-fuentes.mjs      # descarga los .woff2 (solo subconjunto latino)
node scripts/tipografia.mjs              # genera el HTML y captura con Playwright
```

Las capturas salen en `frontend/capturas/tipografia/` y **no se versionan**, igual que el resto
de la revisión visual (`docs/REVISION_VISUAL.md`): se adjuntan al PR, que es donde se miran.
