---
tipo: adr
fase: "[[Fase-10-alta-self-service]]"
estado: aprobado
supersede: ""
superado_por: ""
tags:
  - tipo/adr
  - estado/aprobado
  - fase/10
  - area/seguridad
---

# ADR-0001: exigir claim `tipo="sesion"` en los tokens JWT

## Contexto

`crear_token` (sesión) y `crear_token_proposito` (enlaces de verificación/reseteo por correo) se firmaban con el **mismo** `jwt_secret`. `decodificar_token` era un `jwt.decode` genérico que solo validaba firma y caducidad.

Consecuencia medida: un enlace de verificación (24 h) o de reseteo (1 h) enviado por correo valía como Bearer de sesión completo en cualquier endpoint protegido por `get_current_user`, heredando el rol real de la cuenta — y **seguía valiendo después de consumirse**, porque `token_consumido` solo lo consulta el camino de un solo uso, nunca la autenticación.

## Decisión

`crear_token` marca `tipo="sesion"`; `decodificar_token` lo exige como lista blanca.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Lista negra: rechazar tokens que contengan `proposito` | Depende de enumerar los propósitos existentes y de acordarse de actualizar la comprobación al añadir uno nuevo. Frágil por diseño. |
| Secretos separados para sesión y para propósito | Más robusto a largo plazo, pero exige rotar y gestionar dos secretos en producción; desproporcionado para el riesgo cerrado con un claim. |
| No hacer nada, aceptar el riesgo | Descartado: severidad ALTA confirmada por revisión de seguridad independiente. |

## Consecuencias

### Positivas
- Cierra la confusión de audiencia por completo, verificado en vivo: token de propósito contra `/auth/me` → 401; token de sesión → 200 con `tipo: sesion`.

### Negativas / deuda asumida
- **Cambio incompatible**: todos los tokens de sesión emitidos antes de este cambio dejan de ser válidos. Al desplegar se produce un cierre de sesión único.

## Relacionado

- Fase: [[Fase-10-alta-self-service]]
- Commit: `ab61fc6 fix(seguridad)!: exigir tipo de sesión en los tokens JWT`
