---
tipo: adr
fase: "[[Fase-0-sistema-de-diseno]]"
estado: aprobado
supersede: ""
superado_por: ""
tags:
  - tipo/adr
  - estado/aprobado
  - fase/0
  - area/frontend
  - area/diseno
---

# ADR-0010: consolidar el sistema de UI propio en vez de adoptar shadcn/ui

## Contexto

El responsable del proyecto describe el resultado visual como «genérico y poco atractivo» para un
producto que aspira a parecer software comercial serio para inversores. La pregunta que abre esta
decisión es si la causa es la falta de una biblioteca de componentes seria —y por tanto se
arregla adoptando shadcn/ui— o algo anterior.

**Medición del frontend real, no impresiones** (`main`, 2026-09-08):

| Hecho | Dónde |
|---|---|
| La tipografía de marca es **Georgia**, la serif que todo sistema trae por defecto | `frontend/tailwind.config.ts:18` |
| **64 usos** de tamaños de fuente arbitrarios, con **9 valores distintos** entre 10 y 15 px, separados por medio píxel | `grep -rhoE "text-\[[0-9.]+px\]" app components` |
| **`fontSize` aparece 0 veces** en la configuración: no existe escala tipográfica | `frontend/tailwind.config.ts` |
| **124 líneas para 18 exports**, y `focus:` aparece **una sola vez** en todo el fichero | `frontend/components/ui.tsx` |
| El panel derecho del login está vacío en torno al **70 %** a 1440×900 | Captura con Playwright |

También se constató lo que **sí** está bien y conviene preservar: los tokens de color tienen
intención (`tinta`, `papel`, `primario`, y un semáforo `sem-*` con sus fondos) y existe una
familia monoespaciada `cifra` para números, que en un producto de cifras es un acierto.

El dato que ordena la decisión: **shadcn/ui no es una dependencia, es un generador de código** que
copia componentes al repositorio. Aporta estructura, estados y accesibilidad (Radix por debajo).
**No aporta criterio estético.** Un shadcn sin tokens propios se parece a los otros mil productos
que usan shadcn, que es otra forma de resultado genérico.

Restricción del momento: el frontend tiene **cero tests** y **cero linting** (sin configuración de
ESLint y con `eslint.ignoreDuringBuilds: true`), y el responsable trabaja sin máquina local
durante algunas semanas.

## Decisión

**Consolidar el sistema de UI propio** —escala tipográfica, estados y densidad en
`tailwind.config.ts` y `components/ui.tsx`— y **reevaluar la adopción de shadcn/ui en la Fase 15**,
ya con `docs/DESIGN_SYSTEM.md` escrito y tokens propios definidos.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| **Adoptar shadcn/ui ahora** | No resuelve **ninguno** de los cuatro defectos medidos: la fuente del sistema, los nueve tamaños arbitrarios, la ausencia de escala y la falta de densidad seguirían igual, con componentes mejores encima de la misma base sin criterio. Además obliga a reescribir los 18 exports de `ui.tsx` y tocar **las 20 rutas** que los consumen, sin un solo test de frontend que sostenga la migración |
| **Adoptar shadcn parcialmente**, conviviendo con `ui.tsx` | Es el resultado más probable de empezar sin decidir, y el peor: dos sistemas que mantener a la vez. Si algún día se adopta, se adopta entero y se borra `ui.tsx` |
| **No hacer nada y confiar en mejores prompts** | Es lo que ya se estaba haciendo. Sin escala ni reglas escritas, cada sesión —humana o no— elige un número plausible y sigue: los 9 tamaños distintos son la prueba documental de ese fallo |

## Consecuencias

### Positivas

- Arregla los cuatro defectos medidos **sin tocar las 20 rutas**, porque las clases utilitarias ya
  salen del mismo sitio. Coste estimado: 1-2 días frente a 3-5 más verificación visual.
- Cero dependencias nuevas en un frontend que hoy tiene 10 y ninguna vulnerabilidad propia.
- Preserva el semáforo y la familia monoespaciada, que están bien pensados.
- Si más adelante se adopta shadcn, se configurará **con los tokens propios ya definidos**, que es
  la única forma de que no se vea como todos los demás.

### Negativas / deuda asumida

- Los componentes que faltan y que las fases 13-15 van a necesitar —diálogo, desplegable, tabla
  ordenable, pestañas, avisos emergentes— hay que escribirlos, y hacerlos accesibles de verdad
  cuesta más de lo que parece.
- Mantener un sistema propio es un coste permanente que recae en una sola persona.
- **Se asume conscientemente** que esta decisión puede revertirse en la Fase 15. No es un cierre
  definitivo: es un orden de los factores.

## Relacionado

- Análisis completo con las mediciones y el coste por opción: `docs/HERRAMIENTAS.md` §1 y §2.
- Requisito derivado: `docs/DESIGN_SYSTEM.md` debe existir **antes** de la Fase 15, y la elección
  tipográfica debe presentarse como 2-3 opciones argumentadas con capturas comparativas, no
  elegida por gusto.
- Momento de reevaluación: Fase 15 (landing y onboarding), que es la que pide de verdad las
  primitivas que faltan.
