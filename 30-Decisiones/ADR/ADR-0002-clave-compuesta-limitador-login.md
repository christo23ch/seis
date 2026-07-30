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

# ADR-0002: clave del limitador de login compuesta por email y origen

## Contexto

La primera versión del limitador anti-fuerza-bruta usaba como clave solo el email (`login:{email}`). Con esa clave, cualquiera podía bloquear la cuenta de un tercero enviando cinco contraseñas erróneas, indefinidamente y sin que la cuenta tuviera siquiera que existir — el bloqueo se comprueba antes que la contraseña, así que ni el titular legítimo entraba.

## Decisión

La clave pasa a ser `login:{email}:{ip}`.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Clave solo por IP | Un atacante detrás de NAT compartido (oficina, universidad) bloquearía a usuarios legítimos que comparten su misma IP de salida. |
| CAPTCHA en vez de rate limit | Desproporcionado para esta fase; el Plan Maestro exige explícitamente Redis + IP+email, no CAPTCHA. |

## Consecuencias

### Positivas
- El atacante solo se bloquea a sí mismo contra esa cuenta concreta.

### Negativas / deuda asumida
- **Su efecto pleno depende de la Fase 11.** Bajo `docker compose` actual, todas las peticiones externas comparten la IP de la pasarela (`172.18.0.1`, medido), así que hoy esta clave se comporta igual que la anterior hasta que exista proxy inverso con `--forwarded-allow-ips` acotado.

## Relacionado

- Fase: [[Fase-10-alta-self-service]]
- Commit: `baa395d feat(fase-10): endpoints públicos de registro y recuperación`
