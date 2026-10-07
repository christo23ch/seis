# SEIS — Manual de instrucciones para probar el programa

Este manual explica, paso a paso, cómo levantar SEIS y probarlo de forma completa: en tu máquina con Docker, **online** desplegándolo en un servidor o en servicios gratuitos, y mediante la API con Swagger. Incluye un guion de prueba funcional con datos reales (el caso de referencia §19 de la especificación) y los resultados que debes obtener.

---

## 1 · Requisitos

| Opción | Necesitas |
|---|---|
| A — Local con Docker | Docker Desktop o Docker Engine + Compose v2 |
| B — Solo API (Swagger) | Un navegador (la API incluye interfaz de pruebas en `/docs`) |
| C — Online en VPS | Un servidor Linux (Hetzner, DigitalOcean, OVH…) con 2 GB RAM |
| D — Online en PaaS | Cuenta gratuita en Render/Railway (backend) y Vercel (frontend) |

Credenciales iniciales: el usuario administrador se crea en el primer arranque con
el email y la contraseña que tú definas en `.env` (`ADMIN_EMAIL` / `ADMIN_PASSWORD`).

> **`JWT_SECRET` y `ADMIN_PASSWORD` no traen valor de ejemplo y no son opcionales.**
> `.env.example` los entrega vacíos a propósito: cualquier valor publicado aquí
> sería público. Con `SEIS_ENV=production` el arranque **falla** si están vacíos,
> son cortos o contienen palabras de plantilla. Genéralos con
> `openssl rand -base64 48`.

---

## 1 bis · ¿Actualizas una instalación que ya tenías?

> ⚠️ **Lee esto antes de `docker compose up`, o no arrancará nada.**
>
> Desde la Fase 11 el arranque **aborta** en `staging` y `production` si no te has
> pronunciado sobre los proxies. Un `.env` anterior a esa fase no declara
> `SEIS_ENV` —que por defecto vale `production`— ni `PROXIES_DE_CONFIANZA`, así que
> **caen backend, worker y beat**, no solo el primero.
>
> No es un fallo: la guardia existe para que nadie despliegue tras un proxy sin
> declararlo, porque en ese caso el límite por origen se convierte en un cupo
> global para todo el sitio **sin dar ningún síntoma**. Añade una línea a tu `.env`:
>
> ```
> PROXIES_DE_CONFIANZA=ninguno        # no hay proxy delante
> PROXIES_DE_CONFIANZA=10.0.0.5/32    # o la IP/CIDR de tu proxy…
> CABECERA_IP_CLIENTE=x-forwarded-for # …y de qué cabecera fiarte
> ```
>
> Y ten en cuenta que **hay un servicio nuevo, `beat`**: es el planificador, y sin
> él el digest de notificaciones y el sondeo de Telegram no se ejecutan jamás.
> **No lo escales nunca**: dos instancias programan cada tarea dos veces.

### Base de desarrollo SQLite creada sin Alembic (Fase 5J-1, migración `0016`)

> En desarrollo y tests el esquema lo crea `create_all` al arrancar (ADR-0004), y
> **`create_all` no añade columnas a tablas que ya existen**. Una `seis_dev.db` así no
> tiene ninguna revisión en `alembic_version` y, con el código de la 5J-1, el alta
> fallaría al guardar (`no such column: subasta.procedimiento`).
>
> Con el backend **parado** y una copia de seguridad hecha, desde `backend/`:
>
> ```bash
> cp seis_dev.db seis_dev.db.antes-0016            # copia de seguridad
> SEIS_ENV=development DATABASE_URL=sqlite:///seis_dev.db python -m alembic current   # vacío = sin revisión
> SEIS_ENV=development DATABASE_URL=sqlite:///seis_dev.db python -m alembic stamp 0015
> SEIS_ENV=development DATABASE_URL=sqlite:///seis_dev.db python -m alembic upgrade head
> ```
>
> `stamp 0015` solo es correcto si el esquema es el de la `0015`: se comprobó tabla a tabla
> y columna a columna sobre una copia de la base de desarrollo el 2026-10-07. Si
> `alembic current` ya muestra una revisión, basta con `upgrade head`. En PowerShell,
> las variables se fijan antes: `$env:SEIS_ENV="development"; $env:DATABASE_URL="sqlite:///seis_dev.db"`.
> Para deshacer: `alembic downgrade 0015` (quita las cuatro columnas) o restaurar la copia.

---

## 2 · Opción A — Prueba local completa (3 comandos)

```bash
cd seis
cp .env.example .env
# OBLIGATORIO antes de arrancar: rellena JWT_SECRET y ADMIN_PASSWORD en .env.
# Vienen vacíos a propósito y el arranque falla si no los defines.
#   JWT_SECRET=$(openssl rand -base64 48)
#   ADMIN_PASSWORD=$(openssl rand -base64 18)
docker compose up -d --build  # PostgreSQL+PostGIS, Redis, backend, worker, beat y frontend
```

> Si prefieres probar en local sin generar secretos, pon `SEIS_ENV=development`
> en `.env`: la validación estricta se aplica en `staging` **y** en `production`. **Nunca**
> expongas a Internet un despliegue arrancado así.

Espera ~2-4 minutos la primera vez (compila el frontend). Después:

| Servicio | URL |
|---|---|
| **Aplicación web** | http://localhost:3000 |
| API + Swagger interactivo | http://localhost:8000/docs |
| Salud del backend | http://localhost:8000/api/v1/health |

En http://localhost:3000 está la **landing pública**; la aplicación vive en
http://localhost:3000/app y exige sesión (Fase 15). Entra por **Iniciar sesión** con
`admin@seis.local` y el `ADMIN_PASSWORD` que definiste en `.env` — **no hay contraseña
por defecto, y la pantalla de acceso ya no imprime ninguna credencial**: con la raíz
pública, eso era información de instalación expuesta a cualquiera.

Comandos útiles:
```bash
docker compose logs -f backend     # ver el motor en marcha
docker compose down                # parar
docker compose down -v             # parar y BORRAR la base de datos (reset total)
```

---

## 3 · Opción B — Probar online solo con la API (Swagger)

Cualquier despliegue del backend expone en **`/docs`** una consola interactiva completa:

1. Abre `https://TU-BACKEND/docs`.
2. `POST /api/v1/auth/login` → *Try it out* → username `admin@seis.local`, password: la que definiste en `ADMIN_PASSWORD` → copia el `access_token`.
3. Pulsa el botón **Authorize** (candado, arriba a la derecha) y pega el token.
4. Ya puedes ejecutar `POST /api/v1/analisis/simular` con el JSON del §6 de este manual y ver la decisión completa sin tocar el frontend.

---

## 4 · Opción C — Despliegue online en un VPS (todo en uno)

En un servidor Ubuntu 22/24 recién creado:

```bash
# 1) Docker
curl -fsSL https://get.docker.com | sh

# 2) Sube el proyecto (desde tu máquina):
scp seis_completo.zip root@TU_IP:/opt/ && ssh root@TU_IP
cd /opt && apt-get install -y unzip && unzip seis_completo.zip && cd seis

# 3) Configuración de producción
# Se parte de .env.produccion.example y NO de .env.example: aquel es la plantilla
# de DESARROLLO y trae `PROXIES_DE_CONFIANZA=ninguno`, que en un VPS con proxy
# delante deja el límite por origen como cupo global y permite bloquear la cuenta
# de un tercero de forma indefinida. La plantilla de producción entrega esa
# variable VACÍA a propósito, para que el arranque aborte hasta que alguien se
# pronuncie.
cp .env.produccion.example .env
# Los tres secretos vienen VACÍOS y son obligatorios: `docker compose up` aborta
# si falta cualquiera, y el backend no arranca si son débiles o de plantilla.
# Genéralos (no los copies de este manual: lo que se publica aquí es público):
cat >> .env <<FIN
POSTGRES_PASSWORD=$(openssl rand -base64 24)
JWT_SECRET=$(openssl rand -base64 48)
ADMIN_PASSWORD=$(openssl rand -base64 18)
FIN
nano .env    # borra las líneas vacías duplicadas y ajusta:
#   SEIS_CORS_ORIGINS=http://TU_IP:3000        (o https://tu-dominio)
#   SEIS_ENV=production        (admitidos: development | test | staging | production)
#   PROXIES_DE_CONFIANZA=…     (IP o CIDR de tu proxy, o `ninguno` si no hay)
#   BIND_BACKEND / BIND_FRONTEND  ← ver el aviso de abajo ANTES de tocarlos

# 4) Arranque (el frontend debe conocer la URL pública del backend)
NEXT_PUBLIC_API_URL=http://TU_IP:8000 docker compose up -d --build
```

> ⚠️ **Por defecto no habrá nada alcanzable desde `TU_IP`, y eso es intencionado.**
> Desde la Fase 11 los puertos se publican en `127.0.0.1`, así que la pila levanta
> sana, los health checks pasan y desde fuera no responde nadie: **parece una
> avería y no lo es**. Las dos salidas, por orden de preferencia:
>
> 1. **Recomendada:** pon delante Caddy o Nginx con HTTPS, deja `BIND_*` en
>    loopback y expón solo 80/443. En ese caso **declara el proxy** en
>    `PROXIES_DE_CONFIANZA` y pon `CABECERA_IP_CLIENTE=x-forwarded-for`; sin eso
>    el límite por origen vuelve a ser un cupo global para todo el sitio.
> 2. **Solo para pruebas:** `BIND_BACKEND=0.0.0.0` y `BIND_FRONTEND=0.0.0.0`, y
>    abre 3000 y 8000 en el firewall. Ten presente que entonces `/docs` y
>    `/openapi.json` enumeran la API entera sin autenticar, y que cualquiera puede
>    hablar con uvicorn **saltándose el proxy**. No dejes esto en un sistema con
>    datos reales.
>
> **Si tocas `BIND_*`, revisa `PROXIES_DE_CONFIANZA` en la misma sesión.** Son la
> misma decisión vista desde dos lados.

> PostgreSQL y Redis se publican solo en `127.0.0.1`, así que no son alcanzables
> desde fuera del host aunque el cortafuegos no los cubra. Sigues pudiendo usar
> `psql -h localhost -p 5432` en el propio servidor.

---

## 5 · Opción D — Despliegue online gratuito (Render + Vercel)

**Backend en Render** (o Railway, equivalente):
1. *New → Web Service → Deploy from repo/zip* apuntando a la carpeta `backend/` (tiene su `Dockerfile`).
2. Añade una base **PostgreSQL** gestionada del propio Render y copia su *Internal URL*.
3. Variables de entorno del servicio:
   `DATABASE_URL=postgresql+psycopg2://…` (la URL anterior, cambiando `postgres://` por `postgresql+psycopg2://`)
   `JWT_SECRET=…` · `ADMIN_PASSWORD=…` · `SEIS_CORS_ORIGINS=https://TU-APP.vercel.app`
   **`SEIS_ENV=production`** y **`PROXIES_DE_CONFIANZA=…`** (la IP del balanceador del
   proveedor, o `ninguno`) más `CABECERA_IP_CLIENTE=x-forwarded-for` si declara proxy.
4. *Start command*:
   `sh -c "alembic upgrade head && python -m scripts.init_db && uvicorn app.main:app --host 0.0.0.0 --port $PORT --no-proxy-headers"`

> ⚠️ **Los cuatro elementos en negrita no son opcionales, y omitir uno solo relaja
> tres controles a la vez.** `SEIS_ENV` vale `development` por defecto, y en ese
> entorno: (a) `scripts/init_db` ejecuta `create_all` contra la base gestionada,
> creando en silencio lo que ninguna migración declaró y dejando `alembic_version`
> vacía —deriva de esquema permanente e invisible—; (b) no se validan los secretos;
> (c) no se exige declarar la política de proxies. Y sin `--no-proxy-headers`,
> uvicorn reescribe el par TCP por su cuenta si el proveedor define
> `FORWARDED_ALLOW_IPS=*`, con lo que la resolución de IP pasa a opinar sobre un
> dato del atacante. `alembic upgrade head` va delante porque es quien debe
> gobernar el esquema.
5. Comprueba `https://TU-BACKEND.onrender.com/docs`.

**Frontend en Vercel:**
1. *Add New → Project*, importa la carpeta `frontend/` (framework Next.js detectado solo).
2. Variable de entorno: `NEXT_PUBLIC_API_URL=https://TU-BACKEND.onrender.com`.
3. *Deploy* → tu URL pública `https://TU-APP.vercel.app` ya sirve SEIS completo.

> Redis/Celery son opcionales para probar: el análisis principal es síncrono. Para el modo asíncrono en PaaS añade un Redis gestionado y un *worker* con `celery -A app.tasks.celery_app.celery worker`.

---

## 6 · Guion de prueba funcional (caso de referencia §19)

Inicia sesión y pulsa **Nueva inversión**. Introduce exactamente esto (lo no mencionado, déjalo por defecto):

| Paso | Valores |
|---|---|
| **1 · Datos generales** | Perfil **Reforma integral + venta (flip)** · Fuente **judicial_boe** · Valor de subasta **152000** · Depósito **5** · Horas hasta cierre **200** |
| **2 · Tipo de activo** | Vivienda · Superficie **82** · Estado **malo** · Año **1975** |
| **3 · Registrales** | Sin cargas · Situación posesoria **precario** |
| **4 · Urbanísticos** | Todo por defecto (uso compatible ✓) |
| **5 · Ubicación** | Municipio **Ciudad Ejemplo** · CCAA **ejemplo** · Micro: transporte 70, seguridad 60, sanidad 65, educación 60, comercio 70, verdes 55, pipeline 55, potencial 60, entorno 65 |
| **6 · Valoraciones** | 7 comparables **reformado/testigo**: 2100 · 2200 · 2250 · 2293 · 2350 · 2420 · 2490 €/m². Macro: tendencia **3**, stock **6**, DOM venta **75**, DOM alquiler **25**, población **0.5**, renta **32000**, yield **5.5** |
| **7 · Costes** | ITP manual **6** % (resto vacío = estimación prudente) |
| **8 · Reforma** | Automático · **sin** visita interior |
| **9 · Financiación** | 100 % equity (cash) |
| **10 · Validación** | Marca: nota simple (**10** días), cert. cargas, avalúo, fotos exteriores, IBI, catastro conciliado. Deja sin marcar: posesión verificada, fotos interiores, cert. comunidad, ITE |
| **11 · Resultado** | Se calcula solo |

**Resultado esperado** (tolerancias de redondeo):

- Semáforo **🟡 AMARILLO** con condiciones · **ICO 64** (60–74) · **RA 40** (medio, dominancia *una_alta* por ocupación 4×3)
- ICI ≈ 63 · ICU ≈ 66 · δ_v 6 % · VS prudente ≈ **176.700 €**
- Escalera: ideal **≈ 50.750** · objetivo **≈ 59.450** · máximo **≈ 67.950** · límite **≈ 78.500 €** (la línea discontinua del P. adjudicación esperado, **63.840 €**, cruza entre objetivo y máximo)
- Plazo **15,5 meses** (P50) / **21,7** (P80): 7 de ocupación + 3 de obra + 3 de comercialización + **2,5 de inmovilización** (Fase 5J-2b: no consta la fecha de inicio del procedimiento judicial ⇒ el régimen más largo)
- ROI base **25 %** (≈ 19 % anualizado) · TIR **≈ 26 %** · Margen de seguridad **≈ 25 %** · RVC **1,06 (alcanzable)**
- Plan de puja: **pujas secretas y cierre improrrogable** (decidir la cifra antes, sin tramos) y depósito **30.400 €** (20 %, supuesto desfavorable)
- Condiciones: verificación posesoria in situ; certificado de comunidad
- Checklist: bloqueantes pendientes de **nota simple ≤ 5 días** y **verificación posesoria**

Pulsa **Guardar análisis** → detalle con ocho pestañas. La pestaña **Vista previa (no oficial)** muestra el informe de la configuración actual **en pantalla y sin botón de PDF**: el único PDF descargable es el de un informe oficial (ver *Pruebas de informes oficiales*, abajo), y debe ser un PDF real de varias páginas.

### Pruebas de vetos (comprueba que ninguna virtud compensa un defecto letal)
- Repite con **ocupación = renta_antigua** → **ROJO** con veto `VETO-OCU-01`.
- Repite con **financiación hipoteca sin preaprobar** → **ROJO** con `VETO-FIN-01` y su vía de subsanación.
- Repite con **valor de subasta 400000** → **ROJO** competitivo `VETO-COMP-01` (RVC < 0,80).

### Pruebas de gobernanza del conocimiento
1. **Parámetros** → cambia ITP de `ejemplo` a **8** y guarda. Vuelve al asistente (mismo caso pero con el ITP manual **vacío**): `c_v` pasa de 6,4 % a **8,4 %** y todos los precios bajan; el análisis estampa `version_parametros …+1ov`. Restaura a 6.
2. **Motor de reglas** → en `SEM-EJEC-01` pulsa *Nueva versión*, cambia el texto de la condición, justifica y publica: el historial muestra la vigencia cerrada y los nuevos análisis usan la redacción v2.
3. **Administración** → crea un usuario rol **lector**; entra con él: puede consultar, pero *Nueva inversión* y las ediciones devuelven acceso denegado (403).

### Pruebas del alta mínima y de la validación guiada (Fase 5I)

En **Nueva inversión**, con un usuario analista o administrador:

1. **Alta mínima.** Rellena solo los obligatorios, marcados con «*»: valor de subasta (paso 1),
   superficie (2), municipio (5) y el €/m² del comparable (6). Avanza con «Siguiente» hasta
   **Calcular decisión**: aparece el resultado, sin 422. **Guardar análisis** lleva al detalle.
2. **Coma decimal y miles.** Escribe «152.000» en el valor de subasta, «82,5» en la superficie y
   «2.293» en el €/m²: el detalle guarda 152000, 82,5 y 2293. En tasas y coordenadas el punto
   es decimal: «3.5» de interés es 3,5.
3. **Valores por defecto.** Los campos con valor del contrato lo muestran escrito (depósito 5,
   indicadores 50…); si lo vacías, el marcador dice «Por defecto: …». Los que el motor estima
   (atrasos, tenencia, ITP, costes fijos, baremos de reforma) quedan vacíos con su valor T3 en
   la ayuda.
4. **Validación guiada.** Pulsa «Siguiente» con el valor de subasta vacío: el paso no avanza,
   aparece «Campo obligatorio» en rojo bajo el campo, un aviso arriba y el foco va al campo.
   Escribe «ochenta» en la superficie (paso 2): «Introduzca un número». Añade un comparable sin
   €/m² (paso 6): los dos se marcan y el foco va al primero.
5. **Depósito en euros.** En «Depósito en» elige **Importe (€)** y escribe 7.600 con un valor de
   subasta de 152.000: la ayuda dice «7.600 € = 5 % del valor de subasta». Un importe mayor que
   el valor de subasta da «No puede superar el valor de subasta».
6. **Estado «No consta».** Viene seleccionado por defecto. El resultado es el de «malo»; el
   informe dice «estado de conservación **no consta**: se asume «malo» (P5)…» y el checklist
   lleva el ítem de verificación, pendiente (ADR-0020).
7. **Coordenadas desde la provincia.** En el paso 5 elige una provincia con lat/lng vacías: se
   rellenan con las de la capital y la etiqueta dice «aproximada (provincia)». Si ya habías
   escrito una latitud, no se toca. Volver a «Seleccione…» quita las aproximadas.
8. **Antigüedad.** En el campo «Antigüedad (meses)» de un comparable, el valor no baja de 0 con
   la flecha ↓ (es un campo de texto); «-1» da «No puede ser negativo».

Lo recorren las e2e `frontend/e2e/nueva-inversion.mjs` y `validacion-alta.mjs`, que lanza
`e2e/correr_simulaciones.sh`.

### Pruebas de los datos del procedimiento (Fase 5J-1, ADR-0022)

Los umbrales de aprobación son **informativos**. Desde la Fase 5J-2b, el depósito exigido va al
plan de puja, la forma de puja decide la táctica y los meses de inmovilización entran en el plazo
de la operación (ADR-0024 a ADR-0026): cambiar el procedimiento o el régimen **sí** mueve la
escalera y la rentabilidad.

1. **Valores por defecto.** En el paso 1, «Tipo de procedimiento» viene en *Judicial* (el de la
   fuente) y «¿Cuándo se inició el procedimiento judicial?» en *No sé*. En el paso 2, «¿Es la
   vivienda habitual del ejecutado?» viene en *No consta (se asume que sí)*.
2. **Sigue a la fuente.** Cambia la fuente a *aeat*: el procedimiento pasa a AEAT y desaparecen el
   régimen y la cantidad reclamada. Si cambias el procedimiento a mano, ya no sigue a la fuente.
3. **Caso §19 tal cual** (judicial, «No sé», «No consta», sin cantidad): el panel
   «Procedimiento y umbrales legales» del resultado (y de la pestaña *Estrategia de puja*) muestra
   depósito **30.400 €** (20 %), pago en **20 días naturales**, inmovilización **2,5 meses** («régimen
   judicial más largo: no consta la fecha de inicio»; con la LO 1/2025 serían 1,8), puja
   mínima aprobable y de aprobación segura **106.400 €** (70 %) y suelo absoluto **91.200 €** (60 %),
   con avisos de régimen supuesto, vivienda habitual supuesta y depósito del alta (5 %) distinto del
   legal. El informe (vista previa) lleva el mismo subapartado al final del §8 y el aviso «Cálculo
   orientativo…».
4. **Régimen anterior con deuda.** Elige «Antes del 3-4-2025», cantidad reclamada «30.000» y vivienda
   habitual «No»: depósito **7.600 €** (5 %), pago en **40 días**, inmovilización **2,5 meses** («plazo
   legal máximo»), puja mínima aprobable **30.000 €**, sin suelo absoluto y sin avisos de supuestos.
   En *Estrategia de puja*, la táctica es la de pujas visibles con prórroga («Entrar tarde con
   límites precargados…») y «Base legal aplicada» incluye «Forma de puja (pujas visibles; el cierre
   se prorroga tras la última puja)».
5. **Datos ausentes.** Con *Venta extrajudicial hipotecaria* el depósito y el capital para pujar dicen
   «No consta» y hay un aviso; con *Concursal*, todos los importes. Nunca aparece un 0. El plazo suma
   2,5 meses con el aviso «estimación prudente, sin base legal», y el plan remite al edicto para el
   depósito y la forma de puja.
6. **Régimen y cifras (5J-2b).** Con el §19, cambia «¿Cuándo se inició…?» a *Después del 3-4-2025*:
   la inmovilización baja a 1,8 meses, el plazo a 14,8 y los precios suben (P_max ≈ 68.160 €); la
   táctica sigue siendo la de pujas secretas, sin la nota sobre el régimen anterior.
7. **Validación.** «mucho» en la cantidad reclamada da «Introduzca un número»; «0», «Debe ser mayor
   que cero».

Lo recorre la e2e `frontend/e2e/procedimiento.mjs`, que lanza `e2e/correr_simulaciones.sh`.

### Pruebas de presentación (Fase 5K)

Solo cambia cómo se ve: ninguna cifra cambia. Con el caso §19 guardado, en su detalle:

1. **Vista previa (no oficial)** e **Informes oficiales → Abrir**: el informe sale maquetado, con
   títulos, tablas y casillas en el checklist. No aparece ningún `**`, `|---|` ni `#`. Las
   fórmulas salen con subíndice (C<sub>F</sub>, c<sub>v</sub>, δ<sub>v</sub>) y no hay claves con
   barra baja («judicial (Portal de Subastas del BOE)», no «judicial_boe»). Desde la 5J-2a, en los
   análisis nuevos es el propio motor quien redacta los nombres («Partida de costes fijos (P50)»,
   «descuento de prudencia», «jurídico», «una dimensión alta»).
2. A **390 px** (herramientas del navegador, modo móvil), las tablas anchas se desplazan dentro de
   su recuadro y la página no tiene desplazamiento horizontal.
3. **Datos de entrada**: secciones por pasos del asistente («Valor de subasta 152.000 €»,
   «Depósito 5 %», «No consta» en lo vacío). «Ver JSON» enseña la entrada en bruto.
4. **Resumen → «Ver cálculo»** en Costes, en la escalera, en Métricas de decisión, en Valoración y
   en Riesgos: fórmula, valores sustituidos y «Resultado del motor». Desde la 5J-2a, en un análisis
   nuevo también tienen cálculo P_ideal (margen 0,3375 en el §19), el escenario pesimista, P_límite
   bruto, P_adj con sus ajustes, la TIR (flujos del mes 0 al 16), el VAN, el colchón (84,8 meses),
   el plazo (7 + 3 + 3 + 2,5 meses desde la 5J-2b) y el RA (máx(25,36, 40)). En un análisis guardado ANTES de la 5J-2a
   esos cálculos siguen diciendo «Cálculo no disponible aún» y qué dato falta: no se inventa.
5. **Desglose del ICO**: «Rentabilidad 15,0 / 25»; el máximo sale del catálogo del análisis.
6. **Parámetros**: «Árbol completo vigente» en secciones plegables (Procedimiento muestra
   «20 %» con «LEC, art. 669…»); «Ver JSON» enseña el árbol. En el editor libre, al escribir
   `tenencia.mensual_defecto` aparece «Valor vigente: 240».

Lo recorre `frontend/e2e/presentacion.mjs` en `e2e/correr_simulaciones.sh`; con
`E2E_CAPTURAS=<directorio>` guarda capturas de cada pantalla a 1440 y 390 px.

### Pruebas del PDF y de casos con dos tramos o perfil rentista (Fase 5J-2a)

1. **PDF.** Emite un informe oficial de un análisis nuevo y descarga el PDF: ningún `C_F`, `c_v`,
   `δ_v`, `judicial_boe`, `una_alta` ni palabras sin tilde («juridico», «semaforo», «avaluo»). Un
   informe oficial emitido antes de la fase conserva su texto congelado.
2. **Dos tramos fiscales.** En el alta del §19, paso Costes, escribe un valor de referencia del
   Catastro de 150.000 €: en «Ver cálculo» de la escalera, P_objetivo aparece con la fórmula del
   tramo bajo («− t × B» y «1 + c_v − t») y la nota «Tramo bajo».
3. **Perfil rentista con hipoteca.** P_max aparece como el mínimo de sus candidatos (rentabilidad
   exigida, DSCR estresado y cash-on-cash), cada uno con su importe.

Lo cubren `backend/tests/test_textos_5j2a.py` (Markdown y texto real del PDF en nueve casos),
`backend/tests/test_datos_calculo_5j2a.py` y `frontend/tests/calculos.test.ts`, que recalculan cada
fórmula con resultados reales y la comparan con la cifra del motor.

### Pruebas de simulaciones (pestaña **Simulaciones** del detalle)

Parte del análisis guardado arriba. Encima de las pestañas, el aviso debe decir **«Configuración original del análisis»**.

1. **Crear.** Pulsa **Nueva simulación**. Cambia un parámetro numérico (p. ej. `semaforo.verde.ico_min`) y pulsa **Crear simulación (1 cambio)**. Aparece una fila nueva en estado **pendiente**; el aviso **no cambia**: crear no altera la configuración en uso. Prueba también un valor no numérico en ese campo: el botón no deja crear.
2. **Comparar.** En la fila, **Comparar con original** abre la comparación: los parámetros que cambian, con su causa (el override que pediste, o *conocimiento vigente* si los parámetros globales cambiaron desde que se hizo el análisis), y los resultados de los dos lados. **Mostrar todos** enseña también los parámetros sin cambios.
3. **Validar.** **Validar** → confirma. La simulación pasa a **validada** y a ser la configuración en uso: el aviso dice **«Mostrando la simulación {id}»** y el resto de pestañas (Resumen, Estrategia de puja…) enseñan sus resultados.
4. **Descartar.** Crea otra simulación y pulsa **Descartar** → confirma. Queda **descartada** y solo conserva **Comparar con original**. Una simulación validada **no** se puede descartar.
5. **Seleccionar.** Con dos simulaciones validadas, **Usar esta configuración** en la que no está en uso la convierte en la actual; el aviso lo refleja.
6. **Volver a la original.** En el aviso, **Volver a la configuración original** (o **Volver a la original** en la fila «Original» de la tabla). El aviso vuelve a «Configuración original del análisis»; **ninguna simulación cambia de estado**.
7. **Lector.** Entra con el usuario **lector**: ve la lista, la comparación y el aviso, pero **ningún** botón de crear, validar, descartar, usar o volver. Por API, esas escrituras responden **403**.

### Pruebas del coste de capital: rango y aviso (Fase 5G.4, ADR-0016)

1. **Explicación.** En **Resumen**, la tarjeta *Escalera de precios* termina con: «El coste de capital (1,5 % anual, coste de oportunidad del capital propio) solo se descuenta del precio límite (§9.1); ROI y TIR no lo incluyen. Importe aplicado: 3.659 €.» (caso §19). La misma línea aparece en la *Vista previa (no oficial)*, al final de la tabla de escenarios.
2. **Aviso.** En **Nueva simulación**, escribe `0,07` en *Coste de capital anual*: debajo del campo aparece «Por encima del 6 % la escalera de precios suele degenerar (umbral medido en el caso de referencia §19: 6,13 %)». El botón **sigue** dejando crear. En el caso §19 la simulación sale con la escalera degenerada y semáforo rojo.
3. **Rango.** Escribe `0,16`: el campo avisa de que está fuera del rango admitido (0–0,15). Al crear, el backend responde **422** con el mensaje «… 0,16 está fuera del rango admitido: de 0 a 0,15, ambos incluidos» y no se crea ninguna simulación. `0,15` sí se acepta.
4. **Otras cotas.** `semaforo.verde.ico_min = 150` también da 422 (rango 0–100); `80` se acepta.
5. **Edición global.** En `/app/parametros` (superadmin), el editor libre con clave `capital.coste_capital_anual` y valor `0.2` responde con el mismo mensaje de rango y no publica nada.

Por API: `POST /api/v1/analisis/{ID}/simulaciones` con `{"overrides":{"capital.coste_capital_anual":0.16}}` → 422; `PUT /api/v1/parametros` con `{"clave":"capital.coste_capital_anual","valor":0.16}` → 422.

### Pruebas de informes oficiales (pestaña **Informes oficiales**)

1. **Emitir.** **Emitir informe oficial** → confirma con **Emitir**. Aparece en el histórico con su fecha y su procedencia: **Original**, o **Simulación {id}** si había una en uso.
2. **Histórico.** Emite otro tras cambiar la configuración en uso (valida o selecciona otra simulación, o vuelve a la original). Los dos quedan en el histórico, cada uno con su procedencia.
3. **Inmutabilidad.** Abre el primer informe y anota su semáforo y precios. Cambia la configuración en uso y vuelve a abrirlo: **no cambia**. Por API no existe ninguna ruta para modificar ni borrar un informe.
4. **PDF.** **Descargar PDF oficial** descarga `SEIS_informe_oficial_{id}_{fecha}.pdf` con el contenido congelado de ese informe, no el de la configuración actual.
5. **Lector.** Con el usuario **lector**: ve el histórico, abre informes y descarga el PDF, pero **no** ve **Emitir informe oficial**; por API, `POST …/informes` responde **403**.

Estas dos secciones las recorre también la e2e `e2e/correr_simulaciones.sh` (navegador real + comprobación en la base), y el alta de cuenta la recorre `e2e/correr.sh`. Las dos corren en la CI (job `e2e`) y en local con **una sola variable para el navegador**, `CHROMIUM_PATH` (`PLAYWRIGHT_CHROMIUM` se sigue aceptando por compatibilidad):

```bash
# Linux / CI
bash e2e/correr.sh                 # alta real · puertos 8020/3020
bash e2e/correr_simulaciones.sh    # simulaciones e informes · puertos 8010/3010
# Windows (Git Bash)
CHROMIUM_PATH="C:/Program Files/Google/Chrome/Application/chrome.exe" bash e2e/correr.sh
CHROMIUM_PATH="C:/Program Files/Google/Chrome/Application/chrome.exe" bash e2e/correr_simulaciones.sh
```

Las dos compilan el frontend en `frontend/.next`: **no las lances con un `next dev` en marcha** sobre esa carpeta, y restaura `frontend/next-env.d.ts` después (`git checkout -- frontend/next-env.d.ts`).

---

## 7 · Recetario cURL (para pruebas automatizadas)

```bash
API=http://localhost:8000/api/v1

TOKEN=$(curl -s -X POST $API/auth/login -d "username=admin@seis.local&password=admin" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# analizar y persistir (payload: guarda el JSON del §6 como caso.json)
curl -s -X POST $API/analisis -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d @caso.json

# listado · detalle · vista previa en markdown (no oficial) · checklist
curl -s $API/analisis -H "Authorization: Bearer $TOKEN"
curl -s $API/analisis/{ID} -H "Authorization: Bearer $TOKEN"
curl -s $API/analisis/{ID}/informe -H "Authorization: Bearer $TOKEN"
curl -s $API/analisis/{ID}/checklist -H "Authorization: Bearer $TOKEN"

# informes oficiales: emitir (devuelve su id) · histórico · detalle · PDF oficial
curl -s -X POST $API/analisis/{ID}/informes -H "Authorization: Bearer $TOKEN"
curl -s $API/analisis/{ID}/informes -H "Authorization: Bearer $TOKEN"
curl -s $API/analisis/{ID}/informes/{INFORME_ID} -H "Authorization: Bearer $TOKEN"
curl -s -o informe_oficial.pdf $API/analisis/{ID}/informes/{INFORME_ID}/pdf -H "Authorization: Bearer $TOKEN"

# simulaciones: crear · listar · comparar · validar / descartar / seleccionar · volver a la original
curl -s -X POST $API/analisis/{ID}/simulaciones -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"overrides": {"semaforo.verde.ico_min": 70}}'
curl -s $API/analisis/{ID}/simulaciones -H "Authorization: Bearer $TOKEN"
curl -s $API/analisis/{ID}/simulaciones/{SIM_ID}/comparacion -H "Authorization: Bearer $TOKEN"
curl -s -X POST $API/analisis/{ID}/simulaciones/{SIM_ID}/validar -H "Authorization: Bearer $TOKEN"
curl -s -X POST $API/analisis/{ID}/configuracion/original -H "Authorization: Bearer $TOKEN"
# El PDF de la configuración actual (`/analisis/{ID}/informe.pdf`) sigue existiendo por
# compatibilidad, pero la interfaz ya no lo ofrece: el PDF que vale es el del informe oficial.

# análisis asíncrono vía Celery (con worker y Redis levantados)
curl -s -X POST $API/analisis/async -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d @caso.json
curl -s $API/tareas/{TAREA_ID} -H "Authorization: Bearer $TOKEN"
```

Suite de tests del motor (49 pruebas, incluye el caso dorado):
```bash
cd backend && pip install -r requirements-dev.txt && python -m pytest -q
```

---

## 8 · Solución de problemas

| Síntoma | Causa y solución |
|---|---|
| El frontend carga pero el login falla con *Failed to fetch* | El navegador no alcanza el backend o CORS: revisa `NEXT_PUBLIC_API_URL` (se fija **al compilar** el frontend) y `SEIS_CORS_ORIGINS` en el backend; reconstruye con `docker compose up -d --build`. |
| `401 Credenciales inválidas` tras reiniciar | El token caducó (12 h) → vuelve a iniciar sesión. |
| Quiero empezar de cero | `docker compose down -v && docker compose up -d --build`. |
| El PDF sale sin acentos raros | Falta `fonts-dejavu-core` (ya incluido en la imagen); reconstruye el backend. |
| Puerto ocupado | Cambia el mapeo en `docker-compose.yml` (`3001:3000`, `8001:8000`) y ajusta las variables. |

## 9 · Seguridad mínima antes de exponerlo a Internet

1. `JWT_SECRET`, `POSTGRES_PASSWORD` y `ADMIN_PASSWORD` propios, largos y únicos —el sistema no arranca sin ellos— y cambio de contraseña tras el primer login. Nunca reutilices un valor que aparezca en el repositorio o en esta documentación: es público.
2. HTTPS con un proxy (Caddy: dos líneas de configuración) y cerrar 8000 al exterior. La BD y Redis ya están limitadas a `127.0.0.1` por `docker-compose.yml`.
3. Los tipos fiscales y reglas legales del sistema son **parámetros versionados**: valídalos con asesoría profesional antes de operar con dinero real (§20 de la especificación). El sistema recomienda; la decisión de puja es del comité.
