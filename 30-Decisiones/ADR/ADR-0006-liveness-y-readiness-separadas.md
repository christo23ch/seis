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

# ADR-0006: liveness y readiness en endpoints separados

## Contexto

El **requisito 1 del prompt del Plan Maestro** pedía literalmente *un solo* endpoint: ampliar `GET /api/v1/health` para que verificara la conexión a la base de datos y a Redis y devolviera estado por componente, «para los healthchecks de Render y UptimeRobot».

Ese enunciado mete **dos consumidores con necesidades opuestas** en la misma URL:

- La **plataforma de hosting** lo consulta cada pocos segundos y **por cada réplica**, y su veredicto no es informativo: un fallo mata y reinicia el proceso.
- El **monitor externo y el operador** quieren saber si las dependencias responden, que es justo lo contrario: información, no ejecución.

El endpoint que hoy existe (`backend/app/api/routes.py:20`) es O(1) y no hace ninguna E/S.

## Decisión

Se publican **tres endpoints con tres audiencias distintas**, en vez de uno con tres cometidos.

| Endpoint | Audiencia | Comportamiento |
|---|---|---|
| `GET /api/v1/health` | Liveness de la plataforma | **Intacto.** O(1), sin E/S. No se toca. |
| `GET /api/v1/health/listo` | Readiness, pública | `SELECT 1` + `PING` de Redis con timeout de configuración. **503** si algo falla. Cuerpo `{"estado","componentes"}`, con cada componente valiendo exactamente `"ok"` o `"error"` — vocabulario cerrado, sin un tercer valor con matices. |
| `GET /api/v1/health/detalle` | Diagnóstico humano | `require_superadmin`. Añade entorno, revisión de Alembic, versiones del conocimiento T2/T3 y latencias. |

## Justificación

### Por qué el liveness no toca la base de datos

Porque la plataforma lo consulta cada pocos segundos y por réplica, y **actúa** sobre el resultado. Si ese endpoint dependiera de la base, bastaría con que la base se pusiera lenta para que la plataforma empezara a matar y reiniciar procesos web que están perfectamente sanos — **convirtiendo una degradación en una caída total**, y además justo en el momento de mayor carga, que es cuando la base se degrada.

### Por qué el cuerpo de `/health/listo` es mudo sobre el motivo

Porque el texto de una excepción de SQLAlchemy o de redis-py **arrastra la cadena de conexión completa, con usuario y contraseña**. Devolverlo publicaría las credenciales de la base de datos en la respuesta de una URL pública, sin autenticación de por medio. El endpoint dice **qué** componente falla; el **porqué** va al log del servidor, que es del operador.

### Por qué `/health/detalle` va autenticado

Porque la revisión de Alembic y las versiones del conocimiento T2/T3 **identifican la build desplegada** y, con ella, exactamente **qué defectos conocidos le aplican**. Publicarlo es entregarle al atacante el trabajo de reconocimiento hecho.

### Por qué `/health/detalle` responde 200 aunque algo falle

Porque su lector es **una persona diagnosticando**, no un balanceador tomando decisiones. Devolver un 5xx haría que los clientes HTTP que abortan ante un error de servidor **escondieran justamente el cuerpo que se ha ido a buscar**.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| Un único `/health?profundo=1` | Un parámetro que cambia el coste y la exposición de un endpoint público **invita a usarlo como amplificador de DoS contra la base de datos**: quien llama elige gratis cuánto trabajo hace la base por petición. |
| Ampliar el `/health` existente, tal como pedía el prompt | Rompe el liveness. Es exactamente el escenario descrito arriba: una base lenta pasaría a provocar reinicios en cascada de procesos sanos. |
| `/health/detalle` público | Regala huella al atacante: revisión de Alembic y versiones T2/T3 identifican la build y sus defectos conocidos. |

## Consecuencias

### Positivas

- Una base de datos lenta ya no puede provocar reinicios en cascada: el liveness sigue siendo O(1).
- La readiness da un **503 de verdad**, que es lo que un orquestador necesita para sacar una réplica del balanceo sin matarla.
- El diagnóstico rico queda tras `require_superadmin`, sin huella pública.
- Medido sobre la línea base de la fase: **172 recogidos · 169 pasan · 2 fallan · 1 omitido**, es decir **+10 verdes y 0 regresiones** frente a 162 · 159 · 2 · 1.

### Negativas / deuda asumida

- **Requisito operativo, para el runbook de 11-B: la plataforma de hosting debe apuntar su health check a `/api/v1/health`, NUNCA a `/health/listo`.** Configurarlo mal reintroduce íntegro el fallo que este ADR evita, y **no da síntoma alguno hasta que la base se degrada** — que es precisamente cuando peor sale.
- El cuerpo mudo obliga a mirar el log del servidor para saber el motivo. Quien no tenga acceso al log sabrá **qué** componente está caído, pero no **por qué**.
- Tres endpoints en vez de uno: tres superficies que mantener, documentar y tener en cuenta en cada auditoría.
- **Pendiente:** el **Bloque H** debe ampliar `/health/detalle` con un apartado de red (`par_tcp`, `ip_resuelta`, política de proxies). Es la única forma práctica de verificar **en producción** que la resolución de IP real no está mal configurada — sin ese apartado, un `--forwarded-allow-ips` mal puesto solo se descubre cuando alguien ya ha eludido el anti-fuerza-bruta.

## Relacionado

- Fase: [[Fase-11-infraestructura]] — Bloque A
- Plan de ejecución del bloque: `docs/FASE_11_PLAN.md` §3
- [[ADR-0002-clave-compuesta-limitador-login]] — el apartado de red pendiente es lo que permitirá comprobar en producción lo que ese ADR dejó condicionado a esta fase
- [[Fase-10-alta-self-service]] — de donde viene la puerta de despliegue por la IP de origen
