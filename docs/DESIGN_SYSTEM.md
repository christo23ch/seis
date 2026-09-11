# SEIS — Sistema de diseño

**Estado: incompleto a propósito.** Este documento se abre con la **decisión tipográfica
pendiente** (§2). El resto —escala, estados, densidad, componentes— se escribe *después* de
elegir letra, porque la escala se ajusta a la letra y no al revés.

A partir del momento en que este documento exista completo, **ningún prompt de frontend se
ejecuta sin referenciarlo** (`docs/PLAN_FASES.md` §4).

> **Por qué existe.** El diagnóstico está medido en `docs/HERRAMIENTAS.md` §1: la cara del
> producto es Georgia —la serif que todo el mundo tiene por defecto—, hay **nueve tamaños de
> fuente distintos** en 64 usos mientras `fontSize` aparece **0 veces** en la configuración, y
> `focus:` aparece **una sola vez** en las 124 líneas de `components/ui.tsx`. Sin escala escrita,
> cada sesión elige un número plausible y sigue adelante.

---

## 0 · Lo que este documento da por supuesto, dicho en voz alta

Va primero y no en un apéndice, por la regla del [[ADR-0014]]: **un documento que aparenta cubrir
más de lo que cubre es el mismo fallo que persigue el proyecto, un nivel más arriba.** Cada punto
es un supuesto **no verificado**, no un hecho.

1. **Contraste: medido, pero justo.** Las parejas de color actuales se midieron una a una (§4).
   Todas pasan **AA para texto normal (4,5:1)**, pero tres lo hacen **por centésimas**: verde
   sobre su fondo 4,52 · amarillo 4,57 · naranja **4,50**. Cualquier retoque futuro del color las
   rompe sin que nadie se entere. **Ninguna pareja alcanza AAA (7:1)**, y la letra pequeña del
   pie de informe es precisamente donde más falta haría. No hay ninguna comprobación automática
   que vigile esto: hoy depende de que alguien vuelva a ejecutar la medición.
2. **Tamaño mínimo legible: supuesto, no validado.** Se propone **12 px** como suelo absoluto y
   13 px para texto de tabla. Ese número sale de la práctica habitual en productos de datos, **no
   de una prueba con usuarios de SEIS** —que son inversores, un perfil que tiende a ser de más
   edad que la media de un SaaS—. Si resulta que 12 px es pequeño para ellos, la escala entera
   sube un peldaño. No se ha comprobado.
3. **Tablas densas: hay un desbordamiento real y medido, y no lo arregla la tipografía.** Con la
   tabla de escenarios (8 columnas), la página mide **765-766 px en un móvil de 390 px** en las
   cuatro opciones. Es decir: **el móvil arrastra toda la página en horizontal.** Como el número
   es prácticamente idéntico en las cuatro, **es un problema de maquetación, no de letra**, y la
   decisión de §2 no lo resuelve. Queda abierto en §5.
4. **El muestrario es una pantalla, no el producto.** No dice nada de cómo envejecen las cuatro
   opciones en veinte pantallas, ni en el PDF del informe —que es otro medio, con otra unidad y
   otro renderizador—.
5. **Las capturas salen de Chromium sobre Linux.** El renderizado en macOS y en Windows **no es
   idéntico**, sobre todo en los pesos finos y en el suavizado. Lo que se ve aquí es una
   aproximación buena, no la verdad en la máquina del cliente.
6. **Los bordes no cumplen el 3:1 de componentes no textuales** (WCAG 1.4.11): el borde actual
   `#E4E7EC` sobre blanco da **1,24**. Mientras un campo de formulario se delimite solo con ese
   borde, su contorno es invisible para quien tiene baja visión. Asumido a sabiendas hasta que se
   escriba el apartado de estados.

---

## 1 · Principios

1. **Densidad antes que aire.** Es una herramienta de análisis para decidir cuánto pujar, no una
   landing. La pantalla debe caber, no respirar.
2. **La cifra manda.** Todo número que se compare verticalmente va en la familia monoespaciada y
   con `tabular-nums`. Un importe que baila de fila en fila es un importe que no se puede leer en
   columna.
3. **La carencia se ve.** Cuando el motor dice «no lo sé» —confianza 0, base imponible tomada de
   la puja, comparables insuficientes—, la interfaz lo muestra. Es la misma regla que el
   [[ADR-0015]] aplicó al informe.
4. **Una escala, y nadie inventa números fuera de ella.** Es la causa raíz del diagnóstico.
5. **El foco visible no es decoración.** Es requisito de accesibilidad y hoy no existe.

---

## 2 · Tipografía · **DECISIÓN ABIERTA**

Cuatro opciones, todas de **licencia libre** (SIL OFL / Apache) y **auto-alojables**. Lo último
no es un detalle: servirlas desde el CDN de Google manda la IP del visitante a un tercero fuera
de la UE, que es un problema de RGPD que esta misma sesión acaba de cerrar en el backend.

Se reproducen con `node frontend/scripts/tipografia.mjs`, que renderiza **el mismo fragmento
real de un análisis** —números del caso dorado §19, no cifras inventadas— cuatro veces.

> **Las cuatro comparten escala, color y espaciado, a propósito:** así lo que se compara es la
> letra y no la maquetación. El efecto secundario hay que tenerlo delante al decidir: **una
> opción puede mejorar bastante con una escala ajustada a ella** —las serifas suelen pedir un
> cuerpo algo mayor— y eso el muestrario no lo enseña.

| | Opción | Títulos | Texto e interfaz | Cifras |
|---|---|---|---|---|
| **A** | Editorial técnica | Source Serif 4 | Inter | IBM Plex Mono |
| **B** | Superfamilia de ingeniería | IBM Plex Serif | IBM Plex Sans | IBM Plex Mono |
| **C** | Neutra suiza | Inter Tight | Inter | JetBrains Mono |
| **D** | Carácter editorial | Newsreader | Public Sans | IBM Plex Mono |

**A · Editorial técnica.** Convierte en decisión lo que hoy es accidente: mantiene el contraste
serif/sans que ya existe, pero con una serif elegida. Source Serif tiene óptica variable y
aguanta bien en titulares grandes sin volverse decorativa. *En contra:* Inter es la sans más
usada del sector, así que el cuerpo del producto no se distingue de nadie.

**B · Superfamilia de ingeniería.** Una sola familia en sus tres cortes. Es la opción con más
coherencia interna y la que mejor encaja con el tono del producto —ingeniería, no finanzas
brillantes—; los números de Plex Mono son excelentes en columna. *En contra:* IBM Plex está
fuertemente asociada a IBM y a productos de desarrollo; puede leerse como «herramienta interna»
más que como producto de inversión.

**C · Neutra suiza.** Máxima neutralidad y la mejor densidad de las cuatro: Inter Tight aprieta
los titulares y deja más sitio a la tabla. *En contra, y hay que decirlo claro:* **es la opción
con más riesgo de reproducir la queja original.** Inter es el ajuste por defecto de los años
veinte; elegirla es correcto pero no cambia la cara del producto.

**D · Carácter editorial.** La más distintiva. Newsreader tiene bastante personalidad en
titulares y Public Sans —la tipografía del gobierno de EE. UU.— es sobria y muy legible en
cuerpo pequeño. *En contra:* es la que más envejece si el producto vira a algo más financiero, y
la que peor tolera un titular largo.

**Qué mirar en las capturas**, por orden de importancia para este producto:
1. La **tabla de escenarios**: ahí es donde se lee de verdad, y donde las cuatro se diferencian.
2. La fila de índices (**ICO / RA / ICI / ICU**), que es lo primero que mira el usuario.
3. El titular largo con paréntesis, que es el caso peor de cada serif.

**No hay recomendación en este documento a propósito.** La decisión la toma el responsable del
producto mirando las capturas; este apartado se cierra con la opción elegida y su fecha.

---

## 3 · Escala tipográfica · **propuesta, sujeta a §2**

Siete pasos, ni uno más. Sustituye a los nueve tamaños arbitrarios del diagnóstico.

| Token | px | Uso |
|---|---|---|
| `micro` | 12 | pie de informe, notas de tabla, chips |
| `menor` | 13 | celdas de tabla densa, listas de condiciones |
| `base` | 15 | texto de interfaz |
| `guia` | 17 | entradilla, valor de un índice |
| `h3` | 19 | título de sección dentro de una carta |
| `h2` | 24 | título de bloque |
| `h1` | 32 | título de pantalla |

Alturas de línea: **1,25** apretado (titulares) · **1,35** tabla · **1,5** normal.

Estos valores son los que usa el muestrario, así que lo que se ve en las capturas **es** esta
escala. El suelo de 12 px es el supuesto nº 2 del §0.

---

## 4 · Color · contraste medido

Reproducible: los pares se calculan con la fórmula WCAG sobre los tokens de
`frontend/tailwind.config.ts`. **Medidos, no supuestos.**

| Par | Ratio | AA texto (4,5) | AA grande/UI (3,0) |
|---|---|---|---|
| tinta sobre carta | 17,75 | sí | sí |
| tinta.suave sobre carta | 14,70 | sí | sí |
| gris `#667085` sobre carta | 4,97 | sí | sí |
| gris `#667085` sobre papel | 4,60 | sí | sí |
| primario sobre carta | 8,34 | sí | sí |
| blanco sobre primario | 8,34 | sí | sí |
| semáforo verde sobre su fondo | 4,52 | **sí, por 0,02** | sí |
| semáforo amarillo sobre su fondo | 4,57 | **sí, por 0,07** | sí |
| semáforo naranja sobre su fondo | 4,50 | **sí, exacto** | sí |
| semáforo rojo sobre su fondo | 5,56 | sí | sí |
| borde `#E4E7EC` sobre carta | 1,24 | — | **NO** (supuesto nº 6) |

**Conclusión honesta:** la paleta es válida, pero **tres parejas del semáforo viven en el límite
y nada las vigila**. Convertir esta tabla en una comprobación automática es trabajo pendiente de
esta fase, no algo ya hecho.

---

## 5 · Preguntas abiertas de esta fase

1. **La tipografía** (§2). Bloquea el resto del documento.
2. **La tabla densa en móvil.** Medido: 765 px de página en un móvil de 390. Las salidas
   posibles —contenedor con desplazamiento horizontal propio, columnas plegables, o una vista de
   fichas por escenario— son decisiones de producto, no de letra. **No se elige aquí.**
3. **Una comprobación automática de contraste**, para que la tabla del §4 no sea una foto de un
   día concreto.
4. **shadcn/ui** (`docs/HERRAMIENTAS.md` §2): sigue abierta y **no se decide antes que §2**,
   porque la recomendación de aquel documento es adoptarlo —si se adopta— *después* de tener
   tokens propios.
5. **Estados de los componentes** (hover, foco, deshabilitado, carga, error) y **densidad de
   layout**: es el grueso de lo que falta escribir, y depende de §2.

---

## 6 · Cómo reproducir el muestrario

```bash
cd frontend
node scripts/tipografia-fuentes.mjs      # descarga los .woff2 (subconjunto latino) y arma fuentes.css
node scripts/tipografia.mjs              # genera el HTML y captura con Playwright
```

Las capturas salen en `frontend/capturas/tipografia/` y **no se versionan**, igual que el resto
de la revisión visual (`docs/REVISION_VISUAL.md`): se adjuntan al PR, que es donde se miran.
