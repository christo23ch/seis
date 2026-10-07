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

# ADR-0024: el depósito del plan de puja sale del régimen del procedimiento

**Fecha:** 2026-10-07 · **Fase:** 5J-2b · **Base:** `docs/INVESTIGACION_PROCEDIMIENTOS_SUBASTA.md`
§2.3 y §2.13, ADR-0022. **Autorización:** expresa del responsable para tocar `app/engine/`
(CLAUDE.md §6.8) en esta fase, que **cambia cifras**; tabla antes/después aprobada.

## Contexto

Desde la 5J-1 el motor calcula, con parámetros T3 por régimen, el depósito que exige la norma
(`procedimiento.deposito_eur`) y el capital necesario para pujar. Pero el plan de puja (M13), el
§2 del informe y el checklist (M14) seguían usando `subasta.deposito_pct`, el porcentaje del alta,
que por defecto es el 5 %. En una subasta judicial incoada desde el 3-4-2025 (LO 1/2025) el
depósito es el 20 % del valor de subasta, con un mínimo de 1.000 € (LEC 669.1): el plan decía
7.600 € donde la norma pide 30.400 €. La regla T2 SEM-EJEC-01 repetía «depósito del 5%».

## Decisión

1. **El plan de puja, el §2 y el checklist usan el depósito del régimen** (`procedimiento.calcular`,
   que ahora se ejecuta antes de M06). El porcentaje del alta no lo sustituye; si no coincide con
   el de la norma, se mantiene el aviso de la 5J-1 («prevalece el que figure en el edicto»).
2. **Régimen judicial desconocido ⇒ el desfavorable (20 %)**, como ya hacía la 5J-1, y el plan lo
   dice: «supuesto desfavorable: no consta cuándo se inició el procedimiento judicial (si fue antes
   del 3-4-2025, es menor)». Con el mínimo legal aplicado, se indica.
3. **Sin depósito en la norma** (extrajudicial, concursal): «no consta en la norma para este
   procedimiento: confírmelo en el edicto». **Venta no reglada**: «según las condiciones del
   vendedor». Nunca se inventa una cifra (P4).
4. **SEM-EJEC-01 pasa a la versión 2026.10** con el texto «depósito según el régimen del
   procedimiento (20 % con la LO 1/2025; 5 % si se inició antes del 3-4-2025)». Solo cambia la
   versión de esa regla: la versión del catálogo (`2026.07`) no se ha subido nunca, tampoco en
   las fases que cambiaron cifras (5G.4, 5H.1), y cada análisis guarda su resultado entero.
5. **El coste de los depósitos de subastas perdidas queda fuera**: es de cartera, no de la
   operación (decisión del responsable).

## Consecuencias

- El depósito no entra en ninguna fórmula: no mueve la escalera, el RVC ni la rentabilidad.
  Cambian el plan (`puja.plan`), el §2, el detalle del checklist y la condición de SEM-EJEC-01.
- Se salda la deuda de formato de `test_formato_espanol_5g4.py`: la regla era el único «%» pegado.
- `m13_puja.ejecutar` y `m14_informe` aceptan el resultado del procedimiento como argumento
  opcional; sin él, conservan el texto anterior (llamadas directas y tests antiguos).
- **Despliegue:** `reglas_vigentes` usa solo la tabla `regla` en cuanto tiene alguna fila vigente
  y entonces ignora el YAML. En un entorno donde se haya creado cualquier versión de regla por la
  API, el texto 2026.10 de SEM-EJEC-01 no llega solo: hay que crear esa versión también en la base.
- **Queda abierto** (fuera del alcance): SEM-EJEC-01 y M13 dicen «cesión de remate solo por el
  ejecutante», pero con la LO 1/2025 la tienen también los acreedores posteriores (LEC 647.3,
  investigación §2.8).

## Alternativas descartadas

- **Que prevalezca el porcentaje del alta.** El alta trae un 5 % por defecto que casi nadie toca;
  usarlo repetiría el error que esta fase corrige. El edicto prevalece, y el aviso lo dice.
- **Subir la versión de todo el catálogo.** Rompería la comparación de versiones de todos los
  análisis por una sola regla, sin precedente en el proyecto.
