# SEIS — Herramientas: diseño, skills, MCPs y vault

Respuesta a «el resultado visual me parece genérico». Va de la causa raíz hacia las
herramientas, y no al revés: instalar cosas sin arreglar lo del §1 no cambiaría nada.

Todo lo que se afirma aquí sobre repositorios y comandos está **verificado ejecutándolo**, no
citado de memoria. Lo que no he podido verificar se dice explícitamente.

---

## 1 · Qué falla concretamente en el diseño actual

No son generalidades: son mediciones sobre el frontend de `main`, con capturas reales tomadas
levantando la aplicación dentro del sandbox.

### 1.1 La cara del producto es una fuente del sistema

`frontend/tailwind.config.ts`, línea 18:

```ts
display: ["Georgia", "Cambria", "Times New Roman", "serif"],
```

**Es la causa individual más importante del aspecto genérico.** Georgia es la serif que todo el
mundo tiene por defecto; usarla como tipografía de marca no es una elección, es la ausencia de
una. El titular del login («La disciplina de precio, convertida en software») sale en Georgia
mientras el resto de la interfaz usa la sans del sistema. El contraste serif/sans puede ser
excelente en un producto de análisis — pero tiene que ser **una decisión**, con una fuente
elegida, no la que quedó.

### 1.2 Nueve tamaños de fuente distintos, ninguno en el sistema

```
grep -rhoE "text-\[[0-9.]+px\]" app components   →  64 usos, 9 valores distintos

  31 × text-[12px]     12 × text-[13px]      8 × text-[11px]
   6 × text-[12.5px]    3 × text-[11.5px]    1 × text-[15px]
   1 × text-[13.5px]    1 × text-[10.5px]    1 × text-[10px]
```

Nueve tamaños por debajo de 16 px, separados por medio píxel. Y en `tailwind.config.ts` la clave
**`fontSize` aparece 0 veces**: no hay escala tipográfica, así que cada pantalla inventó la suya.
Esta es, literalmente, la firma de la improvisación que quieres corregir: sin escala, cualquier
modelo —y cualquier persona— elige un número plausible y sigue adelante.

### 1.3 Los componentes no tienen estados

`frontend/components/ui.tsx`: **124 líneas para 18 exports**, unas 7 líneas por componente. Y
`focus:` aparece **una sola vez en todo el fichero**. No hay hover, foco, deshabilitado, carga ni
error sistematizados: cada pantalla los resuelve por su cuenta, o no los resuelve. El foco
visible además no es un adorno, es un requisito de accesibilidad.

### 1.4 El layout no tiene densidad definida

En la captura del login a 1440×900, el panel derecho está **vacío en torno a un 70 %**: el
formulario ocupa unos 360 px anclados arriba y debajo queda un hueco enorme. En el panel
izquierdo, `justify-between` con tres hijos deja el titular a media altura con vacíos desiguales.
En móvil (390 px) el formulario flota centrado con vacío arriba y abajo.

No es que sea «feo»: es que **no hay una regla de densidad escrita**. Un producto de análisis
para inversores debería sentirse denso y ordenado, no un formulario flotando en gris.

### 1.5 Un fallo que no es de diseño, pero se ve en la misma pantalla

`frontend/app/login/page.tsx` imprime en la interfaz:

> *Primer arranque: admin@seis.local / admin (cámbiela de inmediato).*

Credenciales por defecto impresas en la pantalla de acceso. Además de la señal de producto sin
terminar, es información que no debería seguir ahí en cuanto haya un despliegue público.

### 1.6 Lo que sí está bien y conviene no tirar

Hay tokens de color coherentes y con intención (`tinta`, `papel`, `primario`, y un semáforo
`sem-verde/amarillo/naranja/rojo` con sus fondos), y una familia `cifra` monoespaciada para
números — que en un producto de cifras es un acierto. La base existe; faltan escala, estados y
densidad.

---

## 2 · La decisión: shadcn/ui frente a consolidar el sistema propio

No la doy por decidida en ninguna dirección. Las dos son defendibles y su coste es muy distinto.

### Lo que hay que entender antes de elegir

**shadcn/ui no es una dependencia, es un generador de código.** Copia los componentes a tu
repositorio y pasan a ser tuyos. Eso significa que adoptarlo no ata a nadie — pero tampoco
resuelve el problema por sí solo: shadcn aporta estructura, estados y accesibilidad, **no aporta
criterio estético**. Un shadcn sin tokens propios se ve exactamente igual que los otros mil
productos con shadcn, que es otra forma de genérico.

### Opción A · Adoptar shadcn/ui de verdad

**A favor**

- Resuelve de golpe el §1.3: componentes con estados y foco correctos, accesibilidad revisada
  (Radix por debajo).
- Trae primitivas que hoy no existen y que las fases 13-15 van a necesitar sí o sí: diálogo,
  desplegable, tabla ordenable, pestañas, avisos emergentes.
- Tiene **MCP oficial** (§4) para buscar e instalar componentes desde el propio editor.
- Es la convención que cualquier desarrollador que entre al proyecto ya conoce.

**En contra**

- Añade Radix UI como dependencia real (varios paquetes) a un frontend que hoy tiene **10
  dependencias** y ninguna vulnerabilidad propia.
- La migración no es «instalar»: hay que reescribir los 18 exports de `ui.tsx` y **tocar las 20
  rutas** que los consumen.
- El riesgo es alto **precisamente porque no hay red**: cero tests de frontend. Una migración de
  esa superficie sin tests se valida a ojo, pantalla por pantalla.

**Coste estimado:** 3-5 días de trabajo enfocado más una verificación visual de las 20 rutas. En
esta ventana sin portátil, esa verificación depende de capturas automatizadas (§4).

### Opción B · Consolidar el sistema propio

**A favor**

- Coste inmediato mucho menor: definir escala tipográfica, estados y densidad en
  `tailwind.config.ts` y `ui.tsx` **arregla §1.1, §1.2, §1.3 y §1.4 sin tocar las 20 rutas**,
  porque las clases utilitarias ya salen del mismo sitio.
- Cero dependencias nuevas.
- Preserva el semáforo y la familia monoespaciada, que están bien pensados.

**En contra**

- Los componentes que faltan (diálogo, desplegable, tabla ordenable) hay que escribirlos, y
  hacerlos accesibles de verdad cuesta más de lo que parece.
- Mantener un sistema propio es un coste permanente que recae en una sola persona.

**Coste estimado:** 1-2 días para la base; los componentes que falten, cuando hagan falta.

### Mi recomendación, con su porqué

**Empezar por B y dejar A como puerta abierta.** No por preferencia estética, sino por el orden
de los factores:

1. **El problema medido en el §1 no lo resuelve shadcn.** La fuente del sistema, los nueve
   tamaños arbitrarios y la falta de densidad seguirían exactamente igual: shadcn pondría
   componentes con estados encima de la misma base sin criterio.
2. **Migrar sin tests de frontend es el peor momento posible.** Si más adelante se adopta, que
   sea *después* de existir `DESIGN_SYSTEM.md` con tokens propios: así se configura shadcn con
   esos tokens desde el minuto uno y no se ve como todos los demás.
3. La Fase 15 (landing) es la que va a pedir de verdad las primitivas que faltan. Ese es el
   momento natural de reevaluar A, ya con documento de diseño y ojalá con algún test.

**Lo que NO recomiendo** es lo que suele pasar: instalar shadcn ahora, dejar media `ui.tsx` viva
y la otra media en shadcn, y acabar manteniendo dos sistemas. Si se adopta, se adopta entero y se
borra `ui.tsx`.

---

## 3 · Skills de ECC

**Verificado clonando `github.com/affaan-m/ECC`:** 286 skills. El instalador admite
`--target claude-project` (instala en `./.claude/` del propio proyecto) y `--skills <ids>`
(instala skills sueltas por identificador). Los perfiles reales son `minimal`, `core`,
`developer`, `security`, `research`, `full` y `opencode`.

### Por qué `--target claude-project` es lo correcto aquí

Tu intuición era acertada y se confirma en la ayuda del propio instalador: `claude-project`
escribe en `./.claude/` del repositorio en lugar de `~/.claude`. **En el sandbox web no existe tu
`~/.claude`**, así que una instalación global sencillamente no viaja; versionada en Git, sí. Y de
paso queda revisable en un PR como cualquier otro cambio.

### Las skills que valen la pena para este problema

Descripciones tomadas de sus propios `SKILL.md`, no de memoria:

| ID | Qué dice que hace | Por qué aquí |
|---|---|---|
| `design-system` | Generar o auditar sistemas de diseño, revisar consistencia visual y PRs que tocan estilos | **La más directamente aplicable.** Es justo el entregable de la Fase 0' |
| `frontend-design-direction` | Fijar dirección de diseño para UI de producción | Ataca la raíz: el criterio, no los componentes |
| `frontend-patterns` | Patrones de React y Next.js, estado y rendimiento | Coincide con el stack real |
| `frontend-a11y`, `accessibility` | Accesibilidad | Cubre el §1.3: el foco visible que hoy aparece una vez |

**Descartadas tras leerlas, pese a sonar relevantes:** `dashboard-builder` es de paneles de
monitorización tipo Grafana, no de UI de producto; `loop-design-check` va de bucles de agentes,
no de diseño visual. Lo menciono porque el nombre engaña.

### Cómo instalarlo sin saturar el contexto

Cada skill instalada gasta contexto en cada sesión. La receta es perfil mínimo más las skills por
identificador:

```bash
git clone --depth 1 https://github.com/affaan-m/ECC /tmp/ecc && cd /tmp/ecc
./install.sh --target claude-project --profile minimal
./install.sh --target claude-project --skills design-system,frontend-design-direction,frontend-patterns,frontend-a11y
```

Ejecutado desde la raíz de `seis/`, para que `./.claude/` caiga dentro del repositorio. Empieza
por `design-system` sola: si con esa basta, no instales las otras tres.

> **Aviso honesto:** he verificado que el repositorio, los comandos y esas skills existen, y qué
> dicen sus descripciones. **No he verificado su calidad** ejecutándolas contra este proyecto. Un
> repositorio de 286 skills de la comunidad es, por definición, desigual.

---

## 4 · MCPs

Criterio aplicado: **preferir servidores del proveedor oficial** —el ecosistema MCP tiene un
problema real de seguridad y un servidor comunitario ve todo lo que se le pasa—, **limitar a 3-5**
porque cada uno consume contexto, y distinguir lo que funciona en el sandbox web de lo que exige
máquina local.

| MCP | Oficial | ¿Sandbox web? | Veredicto |
|---|---|---|---|
| **Playwright** | Sí, Microsoft | ✅ **Verificado funcionando** | **Instalar. El más valioso ahora** |
| **shadcn** | Sí, `shadcn-ui/ui` | ✅ (solo lee registros) | Instalar **solo si** eliges la opción A del §2 |
| **Context7** | Upstash | ⚠️ No verificado | Opcional, con la reserva de abajo |
| **Figma Dev Mode** | Sí, Figma | ❌ Exige app de escritorio | **No instalar** |

### Playwright — el que de verdad cambia algo hoy

**Lo he probado en este sandbox, no lo supongo:** levanté el frontend con `npm run start`, lancé
Chromium y capturé el login a 1440×900 y a 390×844. Las observaciones del §1.4 salen de esas
capturas.

Significa que **puedes iterar diseño sin portátil**: el modelo cambia estilos, recarga, captura y
*mira* el resultado. Sin eso, cualquier trabajo de diseño en esta ventana sería a ciegas — que es
probablemente parte de por qué el resultado te parece genérico.

```bash
claude mcp add playwright --scope project -- npx -y @playwright/mcp@latest
```

Detalle práctico ya medido: el Chromium del sandbox es la build **1194**, y una `playwright`
recién instalada por npm puede esperar otra distinta. Si falla, hay que pasarle
`executablePath: /opt/pw-browsers/chromium-1194/chrome-linux/chrome`.

### shadcn — condicionado a la decisión del §2

Su CLI oficial incluye servidor MCP para buscar, ver e instalar componentes de registros:

```bash
npx shadcn@latest mcp init --client claude
```

Instalarlo antes de decidir el §2 es prepararse para una decisión que no se ha tomado. Si eliges
B, no aporta nada.

### Figma — no, y conviene decir por qué

Existe y es oficial, en dos versiones: una **remota** (la que Figma recomienda) y una **local**
que corre en `127.0.0.1:3845` y **exige la aplicación de escritorio**, con asiento Dev o Full en
plan Professional o superior.

**Pero el motivo para no instalarlo es más simple: no hay diseños en Figma.** Un MCP de Figma
sirve para traducir un diseño existente a código. Aquí el problema no es traducir un diseño: es
**no tener ninguno**. Instalarlo sería resolver un problema que no tienes.

### Context7 — con reserva explícita

Sirve para dar al modelo documentación actualizada de librerías. Suena útil con Next 15 y React
19, pero **no he podido verificar si su servicio es alcanzable a través del proxy de egreso del
sandbox**, que ya ha bloqueado otros dominios en esta sesión. Instálalo solo si notas que el
modelo se equivoca con APIs recientes, y compruébalo tú.

### Cuántos en total

**Dos ahora**: Playwright, y shadcn solo si eliges A. Con `--scope project` van al repositorio y
viajan con él, igual que las skills.

---

## 5 · El vault de Obsidian

**Existe, y está bastante más montado de lo que la conversación sugería.** Vive en la raíz del
repositorio: `.obsidian/` más `01-Home`, `02-Diario`, `10-Proyecto`, `20-Arquitectura`,
`30-Decisiones`, `40-Fases`, `50-Releases`, `60-Auditorias`, `70-Backlog`, `100-Operacion`,
`130-Documentacion-Tecnica`, `900-Plantillas` y `999-Meta`. Son **38 notas, 15 plantillas y 9
ADRs**, y ya trae una nota `999-Meta/Integracion-con-Git.md`.

### El reparto que propongo

La regla es corta y evita duplicar: **`docs/` es lo que el código debe cumplir; el vault es cómo
se llegó hasta ahí.**

| Vive en `docs/` | Vive en el vault |
|---|---|
| `ESTADO_ACTUAL.md` (el índice), `PLAN_FASES.md`, `PROMPTS_FASES.md`, `DESIGN_SYSTEM.md`, runbooks, planes de fase | Notas de decisión (ADR), diario, investigación, backlog exploratorio, mapa del proyecto |
| Se referencia desde los prompts y desde la CI; **es normativo** | Es el contexto, el porqué, y lo que aún no está decidido |

**Cómo se sincronizan sin duplicar: no se sincronizan, se enlazan.** Un ADR del vault enlaza al
documento de `docs/` que implementa su decisión, y `docs/` no repite el razonamiento: lo cita.
Duplicar contenido entre los dos es exactamente lo que produce las contradicciones que ya hemos
visto en este proyecto — `PENDIENTES.md` decía «15 líneas» donde eran 12, y `CLAUDE.md` daba por
existente un conector de ingesta que no existe.

Y el vault **ya está dentro del repositorio**, así que no hay nada que sincronizar: un solo
`git commit` mueve las dos cosas a la vez.

### ¿Merece la pena un MCP de Obsidian?

**No, y con un argumento concreto: sería redundante.** Un MCP de Obsidian sirve para leer y
escribir notas de un vault que vive *fuera* del repositorio. Este vault está *dentro*, así que ya
se puede leer y escribir con las herramientas de fichero normales — es exactamente lo que he
hecho en esta sesión para leer los nueve ADRs.

Añadirlo gastaría contexto sin ganar nada. Además, los MCP de Obsidian que conozco son
comunitarios y suelen depender del plugin *Local REST API*, que requiere la aplicación de
escritorio abierta: **no funcionaría en el sandbox web**, que es justo donde estás trabajando.

### La plantilla de ADR: usar la que ya hay

No hace falta inventarla. `900-Plantillas/Plantilla-ADR.md` existe y la Fase 11-A escribió siete
ADRs con ella (`ADR-0003` a `ADR-0009`), con *frontmatter* de tipo, fase, estado, supersesión y
etiquetas. **Y funciona**: esos siete ADRs fueron lo que me permitió entender 7.000 líneas ajenas
en minutos en vez de leerlas enteras.

**La regla a fijar** —ya recogida en `docs/PLAN_FASES.md`— es que toda decisión discutible de una
fase termine en un ADR numerado antes de cerrar su PR, y que el PR lo enlace.

---

## 6 · Orden de instalación recomendado

1. **Nada todavía.** Primero escribir `docs/DESIGN_SYSTEM.md` (Fase 0' del plan): es la causa
   raíz, y ninguna herramienta la sustituye.
2. **Playwright MCP**, en paralelo: es lo que permite ver el resultado sin portátil.
3. **La skill `design-system` de ECC**, sola, con `--target claude-project`. Si basta, parar ahí.
4. **Decidir el §2** al llegar a la Fase 15, ya con el documento de diseño escrito.
5. **shadcn MCP** solo si esa decisión es A.
