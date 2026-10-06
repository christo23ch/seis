---
tipo: feature
estado: borrador
prioridad: p2
fase: ""
tags:
  - tipo/feature
  - estado/borrador
  - prioridad/p2
---

# Perfil de inversor por cuestionario

## Motivación

Pedido por el usuario en la prueba manual del alta que originó la [[Fase-5I]] (2026-10-06). Hoy
el perfil de inversión se elige a mano en el paso 1 del alta, sin nada que ayude a escogerlo.
**No se implementa todavía:** se diseñará junto con la rentabilidad del ICO (auditoría del motor,
punto E8, `docs/AUDITORIA_MOTOR_ESPECIFICACION.md`), porque los dos tocan cómo se puntúa una
inversión para un inversor concreto.

## Requisito, tal como lo pidió el usuario

- Una **pestaña de usuario** con preguntas sobre cómo afronta las inversiones, el **capital
  disponible** y el **riesgo que asume**, que determinan el **perfil recomendado**.
- Ese perfil fija cómo se ajusta una inversión al usuario: **la misma inversión al mismo precio
  puede puntuar distinto para dos perfiles**.
- En **«Datos generales»** del alta aparece el **perfil recomendado, con opción de cambiarlo**.
- El **informe** puede incluir **los perfiles que conviene simular** para la subasta analizada.

## Criterio de aceptación

- [ ] Diseño conjunto con E8 (rentabilidad del ICO) aprobado por el responsable.
- [ ] Cuestionario y regla perfil-recomendado deterministas y auditables (P1): la IA no decide.
- [ ] El alta propone el perfil recomendado y permite cambiarlo.
- [ ] El informe sugiere qué perfiles simular.

## Fase asignada

Sin asignar (pendiente del diseño con E8).

## Relacionado

- [[Fase-5I]] · `docs/ESTADO_ACTUAL.md` («Requisito de producto registrado»).
