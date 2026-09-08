---
tipo: adr
fase: "[[Fase-11-infraestructura]]"
estado: aprobado
supersede: ""
superado_por: ""
tags:
  - tipo/adr
  - estado/aprobado
  - fase/11
  - area/infra
  - area/seguridad
---

# ADR-0003: staging es un entorno soportado y estricto

## Contexto

El Plan Maestro exige, para la Fase 11, «un entorno de pruebas (staging) idéntico» al real. Pero el código no lo admitía: `ENTORNOS_SOPORTADOS` declaraba solo `development`, `test` y `production`, y `entorno_normalizado` **aborta el arranque ante cualquier valor no reconocido**. Con el código anterior, `SEIS_ENV=staging` sencillamente no levantaba.

Ese aborto no es un descuido, es el hallazgo **P1-1** funcionando: antes, la guardia de secretos solo se activaba con la grafía exacta `production`, de modo que una errata plausible —`produccion`, `prod`— **desactivaba en silencio todo el control de secretos**. La corrección fue negarse a arrancar ante un entorno desconocido, porque un entorno que el sistema no reconoce no permite decidir con qué rigor tratarlo.

De ahí que añadir `staging` no sea añadir una cadena a una lista: hay que decidir **con qué rigor** se trata.

## Decisión

`staging` entra en **las dos** listas:

```python
ENTORNOS_SOPORTADOS = ("development", "test", "staging", "production")
ENTORNOS_ESTRICTOS  = ("staging", "production")
```

Un entorno estricto exige secretos propios y fuertes: `JWT_SECRET` y `ADMIN_PASSWORD` no pueden estar vacíos, ser cortos, tener poca variedad de caracteres ni contener marcadores de plantilla. La validación estructural del hallazgo C1 se aplica en staging **exactamente igual** que en producción.

Como consecuencia del cambio de semántica se renombran dos símbolos cuyo nombre había dejado de ser cierto:

| Antes | Ahora |
|---|---|
| `_validar_seguridad_produccion` | `_validar_seguridad_entorno` |
| `SecretoInseguroEnProduccionError` | `SecretoInseguroError` |

Y el mensaje de error pasa a nombrar el entorno real (`SEIS_ENV=staging`) en lugar de decir «production» siempre.

## Justificación

### Por qué staging es estricto y no laxo

Porque un staging **es una réplica del sistema real**: mismo código, alcanzable desde internet y, en la práctica, poblado a menudo con una copia de los datos de producción. Soportarlo con la guardia de secretos desactivada habría producido la peor combinación posible — **la superficie de ataque de producción con la puerta abierta** — y habría reabierto por la puerta de atrás justo el agujero que P1-1 vino a cerrar: un entorno expuesto donde los secretos de ejemplo arrancan sin protestar.

La regla que queda escrita es simple: **si un entorno merece existir en internet, merece secretos propios.**

### Por qué las erratas siguen abortando

`stagging`, `stage`, `prod` y `produccion` **no** son entornos válidos y siguen deteniendo el arranque. Admitir grafías aproximadas por comodidad reintroduciría P1-1 tal cual: bastaría una errata para caer en la rama laxa sin que nadie lo advirtiera. Se aceptan solo mayúsculas y espacios sobrantes, que se normalizan **sin relajar nada**.

### Por qué se renombran los símbolos

Porque `SecretoInseguroEnProduccionError` en una traza cuyo `SEIS_ENV` es `staging` **miente al operador**, y un nombre que miente cuesta más que el churn de renombrarlo. Lo mismo con el mensaje: quien despliega staging tiene que leer «staging» en el error, o buscará el fallo en el sitio equivocado.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Que staging corra con `SEIS_ENV=production` | Deja el sistema sin forma de distinguir los dos entornos, justo cuando la Fase 13 (Stripe) necesitará esa distinción para separar claves de prueba de claves reales. Y hace que los logs, las alarmas y la telemetría de staging sean indistinguibles de las del entorno real. |
| Soportar `staging` pero laxo (secretos débiles permitidos) | La combinación más peligrosa de todas: superficie de producción sin guardia. Además es exactamente el escenario que P1-1 cerró. |
| Aceptar grafías aproximadas (`stage`, `stagging`) por comodidad | Reintroduce P1-1: una errata bastaría para caer en la rama laxa sin síntoma. |
| Conservar los nombres antiguos para no tocar tests | Un nombre falso en una traza es deuda permanente a cambio de ahorrar un renombrado mecánico en dos ficheros. |

## Consecuencias

### Positivas

- El entorno de pruebas que exige el Plan Maestro **ya puede existir**; antes ni siquiera arrancaba.
- Staging no puede desplegarse con secretos de plantilla, ni siquiera «provisionalmente».
- El test de entornos soportados se parametriza sobre la constante, de modo que **añadir un quinto entorno obliga a pasar por ese test** en vez de colarse sin que nada lo mire.
- El mensaje de error dirige al operador al entorno correcto.

### Negativas / deuda asumida

- **Un secreto más que custodiar.** Staging exige su propio `JWT_SECRET` y su propio `ADMIN_PASSWORD`, y queda escrito en `.env.example` que **no deben reutilizarse los de producción**: el sentido de tener dos entornos se pierde en cuanto comprometer el de pruebas basta para entrar en el real. Nada en el código puede impedir que alguien copie y pegue; es un requisito operativo.
- **Renombrado con alcance fuera del código.** Se actualizaron `CLAUDE.md` y los dos documentos de la Fase 13 que instruían modificar la función por su nombre antiguo. `docs/FASE_95_PLAN_EJECUCION.md` conserva el nombre viejo **a propósito**: es el registro histórico de una fase cerrada y describe lo que era cierto entonces.
- **Staging estricto no es staging aislado.** Que exija secretos fuertes no dice nada sobre si su base de datos, su Redis o su proveedor de correo están separados de los de producción. Ese aislamiento es infraestructura y corresponde a la **Fase 11-B**.

## Relacionado

- Fase: [[Fase-11-infraestructura]] — Bloque D
- Plan de ejecución del bloque: `docs/FASE_11_PLAN.md` §3 (H7)
- [[ADR-0006-liveness-y-readiness-separadas]] — la sonda de diagnóstico publica el entorno normalizado, y por tanto distingue staging de producción
- Hallazgos que este ADR extiende: **P1-1** (un entorno desconocido no puede desactivar la guardia) y **C1** (validación estructural de secretos), ambos de la Fase 12
