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

# ADR-0005: una cabecera de IP solo se lee si el par TCP es un proxy declarado, y la posición se cuenta en vez de buscarse

## Contexto

Esta es la decisión que levanta la **puerta de despliegue heredada de la Fase 10**, la única que hoy impide exponer el producto a internet.

Lo medido entonces: bajo `docker compose`, el reenvío del puerto publicado **no conserva la IP de origen**. Todas las peticiones externas llegan con la de la pasarela (`172.18.0.1`). En consecuencia, los límites por origen de `/registro` y `/reenviar-verificacion` no limitan por cliente: son **un cupo global de cinco altas cada quince minutos para todo el sitio**, y un solo atacante sin credenciales puede negar el alta pública de forma sostenida.

La corrección evidente —leer `X-Forwarded-For`— es peor que la enfermedad. **Esa cabecera la escribe cualquiera.** Fiarse de ella sin declarar de quién no arregla el cupo global: convierte el anti-fuerza-bruta de la Fase 10 en un adorno, porque basta enviar una IP distinta en cada intento. Se pasaría de un tope de capacidad a un agujero de autenticación.

Y hay un tercer hecho que descarta la solución de manual: el Plan Maestro pone el dominio **tras Cloudflare** (decisión **CF**). Con el proxy activo, `X-Forwarded-For` arrastra además las IPs de Cloudflare, cuyos **rangos son públicos**. Cualquier esquema que decida *qué* valor leer mirando *qué* valores hay es, con Cloudflare delante, trivialmente manipulable.

## Decisión

**Una cabecera de IP solo se lee cuando el extremo TCP que nos habla es uno de los proxies declarados; y dentro de una cabecera de lista, el valor se toma por posición fija contada desde la derecha, no buscando.**

Tres variables, en `app/core/red.py`:

| Variable | Papel |
|---|---|
| `PROXIES_DE_CONFIANZA` | IPs o CIDR de nuestros proxies. **La puerta.** |
| `CABECERA_IP_CLIENTE` | De cuál fiarse, de una lista blanca cerrada. |
| `SALTOS_DE_PROXY` | N-ésimo por la derecha; solo aplica a `x-forwarded-for`. |

**Las tres son inertes mientras la primera esté vacía.** Hay **una sola puerta** y su defecto de fábrica es el seguro: sin declarar proxies, no se lee ninguna cabecera pase lo que pase con las otras dos, y el comportamiento es exactamente el de antes del bloque.

Sobre la extracción del valor, dos reglas que van juntas:

1. **N fijo desde la derecha.** No se miran los valores para decidir cuál leer; se cuentan posiciones.
2. **Las posiciones a la derecha de la leída deben ser todas proxies declarados.** Si alguna no lo es, se descarta la cabecera entera y se devuelve el par TCP.

Completan la decisión una **guardia de arranque que aborta en los entornos estrictos si nadie se pronuncia** —con el centinela `ninguno` como salida legítima— y `--no-proxy-headers` explícito en `docker-compose.yml` y en `backend/Dockerfile`.

## Justificación

### Por qué el par TCP y no la cabecera

Porque el par TCP es **el único dato de una petición que quien la envía no puede escribir**: sale del socket, no del mensaje. Todo lo demás es texto que elige el cliente. De ahí el orden, que es el de la decisión entera: **primero se decide si podemos fiarnos de quien nos habla; solo después se lee lo que dice.**

Invertir ese orden es el error que comparten todas las alternativas descartadas.

### Por qué no se salta por pertenencia

Lo que hacen uvicorn moderno y varias bibliotecas es recorrer `X-Forwarded-For` de derecha a izquierda **descartando los valores que estén en la lista de confianza**, y quedarse con el primero que no lo esté. Suena razonable y es **vulnerable**: el atacante envía

```
X-Forwarded-For: 6.6.6.6, <una IP cualquiera de la lista de confianza>
```

el recorrido descarta la IP inyectada por estar en la lista, y devuelve `6.6.6.6`. **El atacante ha desplazado la lectura eligiendo qué había que descartar.** Con Cloudflare delante es trivial, porque sus rangos son públicos y basta copiar uno.

Contar posiciones inmuniza contra eso por construcción: **no hay nada que inyectar cuando la decisión no mira valores.** Un prefijo falsificado empuja la cadena hacia la izquierda, nunca hacia la posición que se lee.

### Por qué, además, se exige que la cola sean proxies declarados

Porque contar posiciones, a solas, falla en una topología real **si el origen es alcanzable saltándose el eslabón exterior**. Con `Cloudflare → nginx → uvicorn` y `saltos=2`, un atacante que llegue a **nginx directamente** envía `XFF: 6.6.6.6, 1.2.3.4`, nginx añade la suya al final, y la posición `-2` pasa a ser un valor que eligió el atacante.

Exigir que las posiciones a la derecha de la leída sean proxies conocidos cierra ese caso **sin reintroducir el defecto anterior**: no se decide *qué* leer mirando valores —eso sigue siendo por posición—, solo se **valida** lo ya leído. La distinción es toda la diferencia entre las dos reglas.

### Por qué `--no-proxy-headers` explícito

Porque uvicorn trae `proxy_headers=True` **por defecto** y reescribiría `scope["client"]` por su cuenta, con una semántica que ha cambiado entre versiones. Eso destruye el par TCP, que es justamente el dato con el que aquí se decide confiar: la aplicación acabaría razonando sobre un valor ya manipulado por otra capa.

Dos capas resolviendo lo mismo con dos listas distintas es el peor de los mundos posibles, porque cada una parece cubrir a la otra y ninguna cubre nada. Se elige que resuelva **una sola**, y que sea la que se puede probar.

### Por qué el arranque aborta si nadie se pronuncia

**El modo de fallo más caro de este bloque no es la falsificación: es el olvido.** Alguien despliega tras un proxy y no lo declara. El sistema funciona, las sondas pasan, nadie nota nada — y el límite por origen vuelve a ser el cupo global, es decir, exactamente la deuda que este bloque existe para cerrar, pero ya en internet y sin nadie mirando.

Un silencio así **no se detecta jamás**. Un arranque abortado se detecta en medio minuto. Por eso `PROXIES_DE_CONFIANZA` vacío detiene el arranque en `staging` y `production`, y por eso existe el centinela `ninguno`: para que pronunciarse no obligue a inventarse una topología, y para que **una declaración consciente sea distinguible de un descuido**. Vacío y «no hay proxy» dejan de ser el mismo estado.

La misma guardia valida el rango de `SALTOS_DE_PROXY`, y no por pulcritud: un valor mayor que la cadena real deja el bloque **inerte en silencio** —`resolver_ip` cae siempre al par TCP— con todo aparentemente funcionando. La guardia cubre el olvido; ese rango cubre el error.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|---|---|
| **Delegar en uvicorn** (`--proxy-headers` + `--forwarded-allow-ips`), que es lo que pedía el plan | Reescribe `scope["client"]` y **destruye el par TCP**, el único dato no falsificable de la petición. Su semántica ha cambiado entre versiones, su salto es **por pertenencia** —la fila de más abajo— y reparte la política entre la línea de órdenes del contenedor y el código, donde no se puede probar entera. |
| **Leer el primer valor de `X-Forwarded-For`** | Es literalmente el valor que escribe el cliente. Y tras Cloudflare la cabecera arrastra además las IPs de Cloudflare, así que el primer valor devuelve al mismo agujero por partida doble: eludir el anti-fuerza-bruta con una IP distinta en cada intento. |
| **Saltar los saltos «de confianza» por pertenencia** (uvicorn moderno y varias bibliotecas) | Vulnerable: el atacante inyecta una IP de la propia lista y **desplaza la lectura**. Con Cloudflare es trivial porque sus rangos son públicos. El defecto de fondo es dejar que los valores —que elige el atacante— decidan qué se lee. |
| **Confiar en `CF-Connecting-IP` sin comprobar el par TCP** | Esa cabecera la escribe cualquiera, igual que XFF; el nombre no la protege. Sin comprobar quién nos habla es exactamente igual de falsificable, y encima invita a fiarse por costumbre. Con el par declarado sí es la mejor opción, por ser de valor único. |
| **Codificar los rangos de Cloudflare en el código** | Cambian. Un rango obsoleto compilado en la imagen falla en cerrado —se deja de reconocer al proxy y se vuelve al cupo global— o, si alguien lo amplía «por si acaso», falla en abierto. Es **configuración de despliegue, no constante de programa**; el precio es que hay que refrescarlos, y eso pertenece al runbook de la 11-B. |
| **Declarar de confianza la pasarela de Docker** (`172.18.0.1`) para que el bloque «funcione» bajo Compose sin proxy | Con el puerto publicado en `0.0.0.0` equivale a declarar `0.0.0.0/0`: todo el tráfico externo llega con la IP de la pasarela, así que **cualquiera elegiría su propia identidad**. Es peor que no tener el bloque. Queda como aviso en `.env.produccion.example`, porque ninguna comprobación de arranque puede distinguirlo: una IP privada es un proxy perfectamente legítimo. |

## Consecuencias

### Positivas

- **La puerta de despliegue de la Fase 10 queda levantada por el lado del código.** Es el requisito que bloqueaba exponer el producto a internet.
- **El defecto de fábrica es el de antes del bloque.** Quien no declare nada obtiene el comportamiento anterior, no una versión a medias que parece resolver algo.
- **Se cierra el apartado que [[ADR-0006-liveness-y-readiness-separadas|el ADR de las sondas de salud]] dejó pendiente:** `/health/detalle` publica ahora `par_tcp`, `ip_resuelta` y la política vigente. Comparar los dos primeros en una petición real es la única comprobación práctica **en producción** de que la política no está mal declarada — sin ella, una configuración equivocada solo se descubre cuando alguien ya ha eludido el limitador. No se vuelcan las cabeceras crudas: el diagnóstico no debe ser un espejo de lo que envía quien llama.
- **La parte delicada es pura y se prueba sin montar HTTP.** `resolver_ip` recibe los valores crudos, no la petición.
- **El limitador agrega IPv6 por su /64.** Un cliente doméstico dispone de ese bloque entero y rota de dirección a voluntad: contar por dirección exacta habría sido no contar. La normalización de las IPv4 mapeadas (`::ffff:a.b.c.d`) va **antes** de decidir por versión, porque hacerlo después colapsaría a todos los clientes IPv4 en `::/64` — un cupo global recién construido dentro del bloque que vino a eliminarlo.
- **La lista blanca de cabeceras es cerrada y se aplica también en tiempo de ejecución**, no solo en la guardia: aquella corre únicamente en entornos estrictos, así que sin esto una errata en el `.env` de desarrollo (`cf-connecting_ip`) habría desactivado la resolución sin que nadie lo notara.

### Negativas / deuda asumida

- **Una variable obligatoria más en producción.** `PROXIES_DE_CONFIANZA` sin declarar **aborta el arranque** en staging y producción. Es deliberado y tiene un coste real: un despliegue nuevo no levanta hasta que alguien se pronuncie. `ninguno` existe para que ese pronunciamiento no obligue a inventar nada.
- **La corrección depende de que la topología declarada sea la real, y eso el código no puede comprobarlo.** Nada sabe cuántos proxies hay de verdad delante. Un `SALTOS_DE_PROXY` que no coincida con la cadena **no da síntoma**: cae siempre al par TCP y el cupo vuelve a ser global con todo funcionando aparentemente bien. La guardia acota el rango y `/health/detalle` publica el resultado, pero **la verificación final es mirar una petición real**.
- **Los rangos de Cloudflare hay que refrescarlos, y nada avisa cuando cambian.** Un rango caduco deja de reconocerse como proxy y el tráfico que entre por él vuelve al cupo global, en silencio. Preferir `cf-connecting-ip` reduce el problema —es de valor único, así que elimina `SALTOS_DE_PROXY`, la variable frágil— pero no lo elimina: el par TCP sigue teniendo que estar declarado. Corresponde al runbook de la 11-B.
- **Se renuncia a `X-Forwarded-Proto`.** El módulo resuelve la IP y nada más: no reconstruye esquema ni host, y con `--no-proxy-headers` uvicorn tampoco. Tras un proxy que termine TLS, una redirección o una URL absoluta generadas por la aplicación pueden salir en `http`. Hoy no afecta a nada —no hay despliegue real todavía— y queda anotado para quien monte el proxy en la 11-B.
- **El proxy inverso debe borrar o normalizar la cabecera en todo lo que no venga de sus rangos.** Eso no lo puede imponer el código, y sin ello la declaración protege menos de lo que parece.
- **Este bloque solo significa algo con el puerto del backend cerrado al mundo.** Un uvicorn alcanzable directamente convierte la lista de proxies en una preferencia: el atacante no tiene ninguna obligación de entrar por el proxy. Ver [[ADR-0008-loopback-por-defecto-en-los-puertos-publicados|el ADR del loopback por defecto]], que es su condición de posibilidad.
- **La guardia se cobró su precio de inmediato, y dentro del propio bloque.** La revisión técnica devolvió **BLOQUEADO con 2 CRITICAL**, ambos **regresiones abiertas por este bloque** y corregidas en él: (1) `.env.example` trae `SEIS_ENV=production` —entorno estricto— y dejaba `PROXIES_DE_CONFIANZA` vacío, de modo que `cp .env.example .env && docker compose up` **ya no levantaba**: el defecto exacto que originó la Fase 9.5, reintroducido por la guardia que este ADR defiende. Se corrigió con `PROXIES_DE_CONFIANZA=ninguno`, que además es la declaración honesta para el flujo local. (2) Declarar las tres variables solo en el servicio `backend` habría sido **cierto sobre el consumo y falso sobre la validación**: `app/tasks/celery_app.py` invoca `get_settings()` al importarse, así que la guardia corre también en `worker` y en `beat`, que **habrían entrado en bucle de reinicio** en cuanto el entorno fuese estricto. Se corrigió llevándolas al ancla `x-entorno-aplicacion`. Es el mismo motivo por el que `ADMIN_PASSWORD` ya viajaba allí sin que la use nadie más que el backend — la deuda 1 del Bloque C′, con propietario Fase 16.

## Relacionado

- Fase: [[Fase-11-infraestructura]] — Bloque H
- Plan de ejecución del bloque: `docs/FASE_11_PLAN.md` §3 (y la decisión **CF** en §1)
- [[Fase-10-alta-self-service]] — de ella viene la puerta de despliegue que este ADR levanta
- [[ADR-0002-clave-compuesta-limitador-login]] — su efecto pleno estaba condicionado a esta fase: sin IP real, la mitad de la clave compuesta era la misma para todo el mundo
- [[ADR-0006-liveness-y-readiness-separadas]] — el apartado de red de `/health/detalle` que quedó pendiente allí se entrega aquí
- [[ADR-0008-loopback-por-defecto-en-los-puertos-publicados]] — condición de posibilidad: con el puerto abierto al mundo, declarar proxies de confianza no protegería nada
- [[ADR-0004-create-all-fuera-de-produccion]] — el otro bloque de la fase que ancla una guardia de arranque en los entornos estrictos
- [[PENDIENTES-md|PENDIENTES.md]] — deuda 1 de la Fase 10, marcada cerrada **por el lado del código**; el aviso sobre la pasarela de Docker sigue vivo allí
- Módulo: `backend/app/core/red.py` · Guardia: `_validar_politica_de_proxy` en `backend/app/core/config.py` · Tests: `backend/tests/test_ip_cliente.py`
