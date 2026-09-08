---
tipo: feature
estado: borrador
prioridad: p1
fase: ""
tags:
  - tipo/feature
  - estado/borrador
  - prioridad/p1
  - area/infra
  - area/seguridad
---

# Telemetría de errores (Sentry) — requisito del contrato NO entregado

## Motivación

El **requisito 2 del prompt del Plan Maestro para la Fase 11** pide instrumentar Sentry en backend y frontend, activado solo si existe `SENTRY_DSN`. **No se entregó**, por decisión del responsable del proyecto (H5).

Se registra aquí, y no solo en `docs/PENDIENTES.md`, porque la convención del Vault ([[PENDIENTES-md]]) exige que **la deuda sin fase asignada tenga nota propia**: es justamente el caso que Dataview necesita poder listar, y sin ella la deuda más grave que deja la Fase 11-A queda fuera de la consulta «Deuda sin fase asignada» de [[Home]].

## Estado real

La huella completa de Sentry en el repositorio es **una variable `SENTRY_DSN` declarada y vacía** en `.env.example` y en `.env.produccion.example`, documentada como sin consumidor. **Cero dependencias instaladas, cero código que la lea.** Rellenarla hoy no envía nada a ninguna parte.

## Por qué importa

**Mientras siga así, un error 500 en producción no avisa a nadie.** La única traza es el log del proceso, que alguien tiene que ir a mirar por su cuenta y sabiendo que hay algo que mirar.

Interactúa además con otras dos deudas de la fase, y las tres se agravan entre sí:

- La **purga en modo informe** no deja rastro cuando no hay candidatas, de modo que no se puede distinguir «cero cuentas» de «el planificador está muerto».
- **`beat` no debe escalarse y nada en el código lo impide.** Si muere, el digest y el sondeo de Telegram se detienen de forma indefinida y en silencio.

Sin telemetría, ninguno de esos tres silencios produce una señal.

## Alcance mínimo

- `sentry-sdk` en el backend, con integración de FastAPI y de Celery, activada **solo** si `SENTRY_DSN` tiene valor — el mismo criterio de fallo en cerrado que usa el resto de la configuración.
- Instrumentación equivalente en el frontend.
- **Depuración de datos personales antes de enviar**: el proyecto trata direcciones de correo no verificadas con cuidado deliberado (ver [[ADR-0009-purga-de-cuentas-nunca-verificadas]]), y ese criterio no puede perderse al mandar trazas a un tercero.

## Sin fase propietaria

**Deliberadamente sin asignar.** No se le inventa una fase: quedó fuera de la 11 por decisión expresa y ninguna fase posterior del Plan Maestro lo reclama. Debe asignarse antes de admitir usuarios reales.

## Relacionado

- [[Fase-11-infraestructura]] — la fase que lo excluyó, con el motivo escrito sin maquillar
- `docs/PENDIENTES.md` § «Deuda abierta por la Fase 11 — alcance de la fase»
