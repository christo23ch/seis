---
tipo: feature
estado: borrador
prioridad: p2
fase: ""
tags:
  - tipo/feature
  - estado/borrador
  - prioridad/p2
  - area/frontend
---

# Interfaz para cambiar la contraseña

## Motivación

`POST /auth/cambiar-password` existe, está probado (96 % de cobertura) y funciona. Pero ningún componente del frontend lo invoca: `api.cambiarPassword` no tiene consumidor, no hay página de cuenta y `construirNav` no tiene entrada para ella.

Consecuencia concreta y verificada: el propietario de una organización asigna una «Contraseña temporal» en `/equipo` y su titular **no puede cambiarla desde la aplicación**.

No incumple el contrato de la [[Fase-10-alta-self-service|Fase 10]] — el cambio de contraseña autenticado no figura entre sus seis pasos obligatorios — pero tampoco está resuelto para el usuario final.

## Criterio de aceptación

- [ ] Página o sección de cuenta con formulario de cambio de contraseña
- [ ] Invoca `api.cambiarPassword(actual, nueva)`, ya definido en `lib/api.ts`
- [ ] Entrada visible en `construirNav` o equivalente
- [ ] Mensajes de error/éxito consistentes con el resto de páginas públicas de auth

## Fase asignada

*(vacío a propósito — ver dashboard de deuda sin asignar)*

## Relacionado

- Origen: [[Fase-10-alta-self-service]]
- [[PENDIENTES-md|PENDIENTES.md]], deuda 12
