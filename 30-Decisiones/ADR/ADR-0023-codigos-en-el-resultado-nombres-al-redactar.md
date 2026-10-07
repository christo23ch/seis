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
  - area/frontend
---

# ADR-0023: códigos en el resultado, nombres al redactar; operandos de «Ver cálculo» como campos opcionales

**Fecha:** 2026-10-07 · **Fase:** 5J-2a · **Base:** `docs/DEUDA_PRESENTACION_MOTOR.md`,
`docs/INVENTARIO_PRESENTACION.md`, especificación P1. **Autorización:** expresa del responsable
para tocar `app/engine/` (CLAUDE.md §6.8) solo para (a) corregir textos que el motor emite y
(b) añadir campos nuevos y opcionales al resultado; ninguna cifra existente puede cambiar.

## Contexto

El informe (y con él el PDF oficial) mostraba claves internas (`judicial_boe`, `una_alta`,
`ocupacion_desalojo`), palabras sin tilde (`juridico`, `comercializacion`) y símbolos de la
especificación con barra baja (`C_F`, `c_v`, `δ_v`, `P_max`). La 5K los hizo legibles en la
interfaz, al mostrarlos; el PDF no pasa por la interfaz y los seguía enseñando en crudo. Además,
«Ver cálculo» no podía completar 13 fórmulas porque el resultado no traía sus operandos.

Al medir qué textos estaban en la foto del caso dorado (`tests/test_invariante_5h1.py`, 510 hojas
del §19 y 514 del §19 con hipoteca), aparecieron 24 hojas afectadas en cada caso, de dos clases:

- **17 son códigos de datos** (`riesgos.dimensiones[].dimension = "juridico"`,
  `riesgos.dominancia_aplicada = "una_alta"`, `valoracion.metodo = "comparables_ajustados"`,
  `ici.carencias`, evidencias de reglas…). Los leen la interfaz, las reglas T2 (hechos con esos
  nombres), la persistencia (`riesgo_evaluado.dimension`) y los tests. No son texto para personas.
- **7 son textos para personas con símbolos dentro**: `checklist[6|12|18].texto` («…incorporadas
  a C_F», «…aplicada en c_v», «Capital para C_F…») y `riesgos.dimensiones[1].condiciones[0-3]`
  («Subsanar: posesion_verificada»…).

## Decisión

1. **Los códigos del resultado no cambian.** Son datos, no redacción.
2. **M14 los nombra al redactar** con un diccionario cerrado (`app/engine/textos.py`):
   `etiqueta(codigo)` para códigos de una palabra (dimensiones, niveles, partidas, fuente,
   ocupación, categoría de regla…) y `legible(texto)` para sustituir dentro de un texto los
   símbolos (`C_F` → «costes fijos», `c_v` → «costes proporcionales», `δ_v` → «descuento de
   prudencia», `P_max` → «precio máximo»…) y los códigos con barra baja. Términos de la
   especificación (glosario, §5). Sin reglas generales: lo que no está en el diccionario se queda
   como está, y un test barre el informe y el PDF en ocho casos para detectarlo.
3. **Los 7 textos de la foto se redactan legibles en el informe, sin cambiar el dato.** Corregirlos
   en origen cambiaría 7 hojas de la foto (solo texto, ninguna cifra) y obligaría a regenerarla.
   Queda como alternativa para el responsable; el diff está en el CHANGELOG de la fase.
4. **Lo que nace solo en texto y no está en la foto se corrige en origen**: la línea del plan de
   puja «pujar solo P_ideal 'por si acaso'» (M13) pasa a «pujar solo el precio ideal «por si
   acaso»».
5. **Los operandos de «Ver cálculo» se emiten como campos NUEVOS y OPCIONALES**, tomados de
   variables que el motor ya calculaba: margen excepcional, estrés y piso del pesimista,
   P_límite bruto, candidatos del rentista y su límite, tramo fiscal de cada precio, pesos y suelo
   del RA, ratio del segmento y sus ajustes, flujos de la TIR y tasa del VAN, operandos del
   colchón, desglose del plazo, penalizaciones del ICI y evidencias estructuradas. Ninguna fórmula
   cambia: `fiscal.resolver_por_tramos` y `m11.colchon_plazo` delegan en variantes que devuelven
   además el dato, con las mismas cuentas.
6. **El frontend sigue sin recalcular**: muestra fórmula, valores sustituidos y el resultado del
   motor; los tests de vitest recalculan cada fórmula con resultados reales y la comparan con la
   cifra del motor.

## Consecuencias

- La foto del §19 pasa sin tocarla; `test_informe_coherencia.py` admite cada cambio de redacción
  como par viejo/nuevo con los mismos dígitos en el mismo orden.
- **Informes oficiales ya emitidos**: su Markdown está congelado, así que su PDF sigue mostrando
  los códigos de antes. No se reescribe un documento oficial al renderizarlo.
- La interfaz conserva su traducción al mostrar (5K): sigue haciendo falta para los resultados y
  los informes anteriores a esta fase, y para los 7 textos de la foto.
- Un resultado anterior sin los campos nuevos sigue validando y «Ver cálculo» dice «no disponible
  aún» en lo que dependa de ellos. Sin migración: todo viaja en el JSON del resultado.
- Los pesos del ICO de los análisis anteriores a la `0014` siguen sin poder reconstruirse.

## Alternativas descartadas

- **Renombrar los códigos** (`juridico` → `jurídico`): rompe reglas T2, persistencia, interfaz y la
  foto, para ganar solo presentación.
- **Traducir en el renderizador del PDF** (`pdf_service`): cambiaría también el PDF de informes
  oficiales congelados, y la regla de qué traducir viviría lejos de quien redacta el texto.
- **Regenerar la foto del §19** para corregir los 7 textos en origen: posible, pero es decisión del
  responsable y no aporta nada al informe, que ya sale legible.
