---
tipo: adr
fase: "[[Fase-5J]]"
estado: aceptado
supersede: ""
superado_por: ""
tags:
  - tipo/adr
  - estado/aceptado
  - area/motor
---

# ADR-0025: la táctica de puja depende de la forma de puja del régimen

**Fecha:** 2026-10-07 · **Fase:** 5J-2b · **Base:** `docs/INVESTIGACION_PROCEDIMIENTOS_SUBASTA.md`
§2.4 y §2.13 (punto 3), API de datos abiertos del BOE. **Autorización:** expresa del responsable
para tocar `app/engine/` (CLAUDE.md §6.8) en esta fase.

## Contexto

M13 recomendaba siempre «Entrar tarde con límites precargados: la extensión automática del cierre
neutraliza el sniping». En el régimen judicial de la LO 1/2025 no hay extensión: el plazo es
«improrrogable» y las pujas son secretas (LEC 648.6.ª y 649.1). La táctica era falsa justo en el
régimen que el motor supone cuando no consta la fecha de inicio.

## Decisión

1. **Nuevo dato T3 por régimen, `forma_puja`**, con artículo y estado, como los de la 5J-1. Se
   contrastó cada artículo con la API de datos abiertos del BOE
   (`/datosabiertos/api/legislacion-consolidada/id/{ID}/texto/bloque/{art}`, todas las redacciones),
   el 2026-10-07:

   | Régimen | Valor | Artículo | Estado | Lo que dice el texto |
   |---|---|---|---|---|
   | Judicial, LO 1/2025 | `secretas_sin_prorroga` | LEC 648.6.ª y 649.1 (BOE-A-2025-76) | confirmado | «el portal no informará de la existencia o inexistencia de pujas ni de su cuantía»; «plazo improrrogable de veinte días»; cuenta la última puja de cada postor; a igual importe, la anterior |
   | Judicial anterior | `visibles_con_prorroga` | LEC 648.6.ª y 649.1 (redacción de 2015) | confirmado | el portal publica la puja más alta; no se cierra hasta 1 h tras una puja que mejore la más alta, máximo 24 h |
   | AEAT | `visibles_con_prorroga` | RGR 104.2 y 3 (BOE-A-2024-1771) | confirmado | «se publicará electrónicamente la puja»; 1 h tras la última puja, máximo 24 h |
   | TGSS | `presencial` | RGRSS 117.1.c y f, 118, 120.3 | confirmado | sobre cerrado antes del acto y pujas a viva voz con tramos del 2 % (sin comprobar si en la práctica se usa ya el Portal del BOE) |
   | Notarial | `visibles` | Ley del Notariado 75.1.3.ª | confirmado | el portal «informará … de la existencia y cuantía de las pujas»; la prórroga no la fija (remite a la LEC) |
   | Extrajudicial | `null` | LH 129.2.d | sin confirmar | remite a la LEC sin decir qué redacción |
   | Concursal | `null` | TRLC 423.2 | sin confirmar | Portal del BOE u otro portal especializado |

2. **M13 elige la táctica por la forma de puja:**
   - secretas sin prórroga: decidir la cifra antes de abrir la puja; pujarla directamente, sin
     tramos; no apurar el cierre (sin prórroga, una puja que no llega a tiempo queda fuera);
   - visibles con prórroga: la táctica anterior, sin cambios;
   - visibles sin prórroga fijada: cargar límites, tramo mínimo, no dejarlo para el último minuto;
   - presencial: llevar decididas la cifra del sobre y el límite de viva voz;
   - sin dato: cargar límites y confirmar en el edicto cómo se puja.
3. **Régimen judicial desconocido:** táctica de pujas secretas (la del régimen supuesto), con la
   nota de que, si se inició antes del 3-4-2025, las pujas se ven y el cierre se prorroga, y la
   táctica sigue siendo válida. Decidir la cifra antes es correcto en los dos regímenes.
4. **La forma de puja figura en la base legal del informe y del panel** («Forma de puja (pujas
   secretas; cierre improrrogable): LEC… (confirmado)»). Si está sin confirmar, el informe lo dice.
5. **Escalera degenerada:** sigue sin haber táctica («No cargar límites ni pujar»), sea cual sea
   la forma de puja.

## Consecuencias

- Cambia el texto del plan en el §19 (régimen supuesto, pujas secretas), no sus cifras.
- `DatoLegal` gana el campo opcional `texto` para datos que no son una cifra.
- La venta no reglada no tiene forma de puja: se remite a las condiciones de venta.
