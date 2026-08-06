"""Higiene de despliegue — Fase 11, Bloque C′.

Estos tests no ejercitan código de la aplicación: leen los ficheros que definen
CÓMO se despliega. Están aquí porque los defectos que cubren no se manifiestan
en ninguna petición HTTP —el sistema responde con normalidad— y solo se
descubren en producción, tarde y sin síntoma:

- El P1 de la Fase 12: siete credenciales de correo que no llegaban al
  contenedor, de modo que con `EMAIL_PROVIDER=ses` el sistema caía en la rama
  «sin proveedor» y las notificaciones **desaparecían en silencio**, con un
  diagnóstico que además mentía.
- Un `.env` arrastrado a una capa de la imagen por el `COPY . .` del Dockerfile:
  los secretos quedan en el registry y borrarlos después no sirve de nada,
  porque las capas son inmutables y acumulativas.
- Un planificador duplicado por réplica: cada usuario recibiría N copias de cada
  digest.

Son baratos, no necesitan Docker y fallan en el sitio correcto. Mismo patrón que
`test_seguridad_arranque.py`, que ya leía `docker-compose.yml` y `.env.example`.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

RAIZ_REPO = Path(__file__).resolve().parents[2]

COMPOSE = RAIZ_REPO / "docker-compose.yml"
DOCKERIGNORE = RAIZ_REPO / "backend" / ".dockerignore"
GITIGNORE = RAIZ_REPO / ".gitignore"
ENV_PRODUCCION = RAIZ_REPO / ".env.produccion.example"

CONTEXTO_DEL_BACKEND = "./backend"

# Las siete del P1 de la Fase 12.
CREDENCIALES_DE_CORREO = ("SES_REGION", "SES_ACCESS_KEY", "SES_SECRET_KEY",
                          "SMTP_HOST", "SMTP_PUERTO", "SMTP_USUARIO", "SMTP_PASSWORD")


def _compose() -> dict:
    """Compose ya resuelto, con las anclas YAML expandidas.

    PyYAML resuelve las claves de fusión (`<<`) igual que Docker Compose, de modo
    que lo que se comprueba aquí es lo que cada servicio recibe de verdad, no lo
    que está escrito literalmente en su bloque.
    """
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


def _lineas_utiles(fichero: Path) -> list[str]:
    return [linea.strip() for linea in fichero.read_text(encoding="utf-8").splitlines()
            if linea.strip() and not linea.strip().startswith("#")]


def _servicios_de_aplicacion() -> list[str]:
    """Servicios que ejecutan código de la aplicación, DERIVADOS del compose.

    Se deriva en vez de escribirse a mano por la misma razón por la que
    `test_seguridad_arranque.py` se parametriza sobre `ENTORNOS_SOPORTADOS`: si
    mañana alguien añade un cuarto servicio construido desde `./backend` —un
    `flower`, un `worker-captacion`— con una lista literal se quedaría fuera de
    estas comprobaciones y podría nacer sin `JWT_SECRET` sin que nada fallara.
    Derivándola, todo servicio nuevo entra solo.

    El frontend queda fuera por construcción: se construye desde `./frontend` y
    solo recibe la URL de la API.
    """
    servicios = _compose()["services"]
    return sorted(nombre for nombre, definicion in servicios.items()
                  if definicion.get("build") == CONTEXTO_DEL_BACKEND)


def _variables_del_compose() -> set[str]:
    """Toda `${VARIABLE}` referenciada en el compose, sea con defecto o sin él."""
    crudo = COMPOSE.read_text(encoding="utf-8")
    return set(re.findall(r"\$\{([A-Z][A-Z0-9_]*)[:\-?}]", crudo))


def _cubre(patrones: list[str], nombre: str) -> bool:
    """¿Alguno de los patrones excluye ese nombre, con o sin prefijo `**/`?

    Comprueba COBERTURA, no literales. Escribir `**/.env*` en lugar de `.env` es
    equivalente o mejor, y un test que exigiera la cadena exacta se pondría rojo
    ante una mejora — que es la forma más rápida de que alguien deje de mejorar
    ficheros por no pelearse con los tests.
    """
    for patron in patrones:
        limpio = patron.removeprefix("**/").rstrip("/")
        if limpio == nombre or limpio == f"{nombre}*" or limpio.startswith(f"{nombre}."):
            return True
    return False


# ── El .dockerignore, o por qué los secretos no pueden entrar en la imagen ──

def test_existe_dockerignore_para_el_backend():
    """Sin él, `COPY . .` del Dockerfile se lleva TODO el directorio a la imagen."""
    assert DOCKERIGNORE.exists(), (
        "Falta backend/.dockerignore. backend/Dockerfile hace `COPY . .`, así que "
        "sin él la imagen se lleva el virtualenv, las bases de datos locales y "
        "cualquier .env que haya en el directorio.")


@pytest.mark.parametrize("nombre", [".env", ".venv", "__pycache__", ".pytest_cache"])
def test_el_dockerignore_excluye_secretos_y_artefactos_locales(nombre):
    """Test negativo capital del bloque.

    `.env` contiene JWT_SECRET, ADMIN_PASSWORD y POSTGRES_PASSWORD. Si entra en
    una capa de la imagen, queda accesible para cualquiera que pueda descargarla
    del registry, y **borrarlo en una capa posterior no lo elimina**: las capas
    son inmutables y acumulativas.
    """
    assert _cubre(_lineas_utiles(DOCKERIGNORE), nombre), (
        f"backend/.dockerignore debe excluir «{nombre}»")


@pytest.mark.parametrize("nombre", [".env", "__pycache__", "*.py[cod]", "*.db"])
def test_los_patrones_que_deben_aplicar_en_profundidad_llevan_prefijo(nombre):
    """La sintaxis de `.dockerignore` NO es la de `.gitignore`, y confundirlas cuesta.

    Docker casa contra la ruta completa relativa al contexto, así que un patrón
    sin `**` queda anclado a la raíz: `__pycache__/` excluye
    `backend/__pycache__` pero **no** `backend/app/__pycache__`. Medido antes de
    corregirlo: 14 directorios `__pycache__` y 78 ficheros `.pyc` fuera de
    `.venv` entraban igualmente en la imagen. Con `.env` la diferencia deja de
    ser cosmética y pasa a ser una fuga de secretos.
    """
    lineas = _lineas_utiles(DOCKERIGNORE)
    coincidencias = [l for l in lineas if l.removeprefix("**/").rstrip("/").startswith(
        nombre.rstrip("/"))]

    assert coincidencias, f"No hay ningún patrón para «{nombre}»"
    assert all(l.startswith("**/") for l in coincidencias), (
        f"Los patrones para «{nombre}» deben llevar «**/» para aplicar a cualquier "
        f"profundidad. Encontrados sin prefijo: "
        f"{[l for l in coincidencias if not l.startswith('**/')]}")


def test_el_contexto_de_build_es_backend_para_que_su_dockerignore_aplique():
    """Sin esto, los tests del `.dockerignore` podrían dar un falso verde.

    Docker busca el `.dockerignore` **en la raíz del contexto de build**. Si
    alguien cambiara `build: ./backend` por
    `{context: ., dockerfile: backend/Dockerfile}`, el fichero seguiría en su
    sitio, estos tests seguirían leyéndolo y verdes, y **dejaría de aplicarse por
    completo**: el contexto pasaría a ser el repositorio entero, incluidos el
    `.env` de la raíz y el Vault.
    """
    for servicio in _servicios_de_aplicacion():
        assert _compose()["services"][servicio]["build"] == CONTEXTO_DEL_BACKEND


@pytest.mark.parametrize("fichero", [".env.produccion", ".env.production", ".env.staging"])
def test_git_ignora_los_ficheros_de_entorno_que_la_plantilla_invita_a_crear(fichero):
    """`.env.produccion.example` invita a `cp` hacia `.env.produccion`.

    Con `.gitignore` listando solo `.env` y `.env.local`, ese fichero **no estaba
    protegido**: bastaba un `git add .` rutinario —sin `-f`— para publicar
    JWT_SECRET, ADMIN_PASSWORD, POSTGRES_PASSWORD y las credenciales de correo.
    La trampa la creó esta misma fase al introducir la plantilla.
    """
    patrones = _lineas_utiles(GITIGNORE)

    assert ".env.*" in patrones or fichero in patrones, (
        f"`.gitignore` debe cubrir «{fichero}»; hoy un `git add .` lo publicaría.")
    assert "!.env.example" in patrones, (
        "…y debe readmitir explícitamente las plantillas, o dejarían de versionarse.")


# ── Compose: el entorno que cada servicio recibe de verdad ─────────────────

def test_compose_no_declara_la_clave_version_obsoleta():
    """Compose v2 ignora `version:` y avisa de obsolescencia en cada invocación."""
    assert "version" not in _compose()


@pytest.mark.parametrize("servicio", _servicios_de_aplicacion())
def test_las_credenciales_de_correo_llegan_a_los_tres_servicios(servicio):
    """Regresión del P1 de la Fase 12 (`docs/PENDIENTES.md`).

    Faltaban en `docker-compose.yml`, así que con EMAIL_PROVIDER=ses o =smtp las
    credenciales llegaban vacías al contenedor, `NotificadorEmail.disponible()`
    devolvía False y el sistema caía en la rama sin proveedor **sin error
    alguno**. El worker las necesita tanto como el backend: el digest lo envía él.
    """
    entorno = _compose()["services"][servicio]["environment"]

    faltan = [v for v in CREDENCIALES_DE_CORREO if v not in entorno]

    assert not faltan, (
        f"El servicio «{servicio}» no recibe {faltan}. Con EMAIL_PROVIDER=ses o "
        "=smtp, el correo dejará de enviarse sin dar ningún error.")


@pytest.mark.parametrize("servicio", _servicios_de_aplicacion())
def test_los_secretos_no_tienen_valor_de_respaldo_en_ningun_servicio(servicio):
    """`${VAR:-valor}` embebería un valor público; debe ser `${VAR:?...}`, que aborta."""
    entorno = _compose()["services"][servicio]["environment"]

    for secreto in ("JWT_SECRET", "ADMIN_PASSWORD"):
        assert f"${{{secreto}:?" in str(entorno.get(secreto, "")), (
            f"{secreto} en «{servicio}» debe declararse obligatorio con "
            f"${{{secreto}:?...}}, no con un respaldo embebido.")


# ── El planificador, o por qué no puede vivir dentro del worker ────────────

def test_el_planificador_es_un_servicio_propio():
    """H7: `--beat` embebido en el worker no sobrevive a escalar réplicas.

    Con el planificador dentro del worker, N réplicas programan N veces el digest
    horario y el sondeo de Telegram, y cada usuario recibe N copias del mismo
    mensaje. Un planificador debe ser único aunque los ejecutores sean muchos.
    """
    servicios = _compose()["services"]

    assert "beat" in servicios, (
        "Falta el servicio «beat». Sin planificador, el digest de notificaciones "
        "y el sondeo de Telegram NO se ejecutan nunca.")

    comando = servicios["beat"]["command"]

    assert "beat" in comando
    # Sin esta segunda aserción el test daba un FALSO VERDE demostrado: un
    # `celery ... worker --beat` como comando del servicio `beat` contiene la
    # palabra «beat», así que pasaba — y dejaba un worker+planificador que, al
    # escalarse, reintroduce entera la duplicación del digest que este servicio
    # existe para evitar.
    assert "worker" not in comando, (
        "El servicio «beat» debe ser SOLO planificador. Un `celery worker --beat` "
        "aquí devuelve el defecto que la separación vino a cerrar.")


def test_el_planificador_no_declara_replicas_multiples():
    """`beat` es único por diseño; dos instancias duplican cada tarea programada."""
    beat = _compose()["services"]["beat"]

    replicas = beat.get("deploy", {}).get("replicas", 1)

    assert replicas == 1, (
        "El planificador no puede tener más de una réplica: cada una programaría "
        "el digest por su cuenta y los usuarios recibirían mensajes duplicados.")


@pytest.mark.parametrize("servicio", _servicios_de_aplicacion())
def test_los_servicios_de_aplicacion_se_reinician_solos(servicio):
    """Ser único no basta: `beat` también tiene que estar vivo.

    Si su proceso muere (OOM, excepción no capturada en una tarea programada,
    reinicio del host) y nadie lo relanza, el digest y el sondeo de Telegram se
    detienen de forma indefinida, sin error visible y —con Sentry fuera de la
    fase— sin que nadie se entere. Es la misma clase de fallo mudo que el P1 que
    este bloque vino a cerrar.
    """
    politica = _compose()["services"][servicio].get("restart")

    assert politica in ("unless-stopped", "always"), (
        f"El servicio «{servicio}» no declara política de reinicio: si su proceso "
        "muere, nada lo levanta.")


@pytest.mark.parametrize("variable", [
    "VERSION_REGLAS", "VERSION_PARAMETROS",
    # Fase 11, Bloque I. El mismo defecto ya se produjo tres veces en este
    # proyecto —SES/SMTP, VERSION_* y estas—: una variable que el código
    # documenta como interruptor y que no llega al contenedor. Las dos primeras
    # veces dejaron test; esta también.
    "PURGA_CUENTAS_MODO", "PURGA_CUENTAS_DIAS", "PURGA_TOKENS_DIAS",
])
def test_las_versiones_del_conocimiento_llegan_a_todos_los_servicios(variable):
    """P1 (determinismo): cada análisis congela estas versiones en su snapshot.

    No se propagaban a ningún contenedor, de modo que ajustarlas en `.env` no
    tenía efecto alguno bajo Docker. Peor que inútil: dos servicios que las
    leyeran distintas producirían análisis irreproducibles entre sí, y el motivo
    sería invisible porque el valor efectivo no coincide con el declarado.
    """
    for servicio in _servicios_de_aplicacion():
        assert variable in _compose()["services"][servicio]["environment"], (
            f"«{servicio}» no recibe {variable}; su valor de `.env` se ignoraría.")


def test_el_worker_ya_no_programa_tareas():
    comando = _compose()["services"]["worker"]["command"]

    assert "--beat" not in comando, (
        "El worker no debe llevar --beat: al escalarlo, cada réplica duplicaría "
        "las tareas programadas.")
    assert "worker" in comando


# ── La sonda del orquestador (requisito operativo del ADR-0006) ───────────

def test_el_healthcheck_del_backend_apunta_al_liveness_y_nunca_al_readiness():
    """Convierte en ejecutable el requisito operativo del ADR-0006.

    `/health/listo` toca la base de datos y Redis. Si el orquestador lo usara
    como healthcheck, una base lenta bastaría para que reiniciase contenedores
    sanos, **convirtiendo una degradación en una caída total**. Ese fallo no da
    síntoma alguno hasta que la base se degrada, que es justo el peor momento
    para descubrirlo — de ahí que lo vigile un test y no un comentario.
    """
    prueba = str(_compose()["services"]["backend"]["healthcheck"]["test"])

    assert "/api/v1/health" in prueba
    assert "/health/listo" not in prueba, (
        "El healthcheck del orquestador NO puede apuntar a la sonda de readiness: "
        "reiniciaría procesos sanos cada vez que una dependencia se degrada.")
    assert "/health/detalle" not in prueba, (
        "El healthcheck no puede apuntar a /health/detalle: exige autenticación "
        "de superadministrador y siempre daría 401.")


# ── La plantilla de producción ────────────────────────────────────────────

def test_la_plantilla_de_produccion_no_trae_ningun_valor():
    """Todo vacío a propósito, no solo los secretos.

    Un valor heredado por descuido de la plantilla de desarrollo es peor que uno
    ausente, porque el ausente se nota y el heredado no: `FRONTEND_URL` apuntando
    a localhost en producción no rompe el arranque, solo hace que todos los
    enlaces de verificación y reseteo enviados por correo lleven a ninguna parte.
    """
    con_valor = [l for l in _lineas_utiles(ENV_PRODUCCION)
                 if "=" in l and l.partition("=")[2].strip()]

    assert not con_valor, (
        f"`.env.produccion.example` debe entregar TODAS las variables vacías. "
        f"Traen valor: {con_valor}")


@pytest.mark.parametrize("plantilla", [".env.example", ".env.produccion.example"])
def test_toda_variable_del_compose_figura_en_las_plantillas(plantilla):
    """Expectativa DERIVADA del compose, no una lista escrita a mano.

    La versión anterior de este test enumeraba quince nombres a mano, y por eso
    no detectó que `BIND_BACKEND`, `BIND_FRONTEND`, `VERSION_REGLAS`,
    `VERSION_PARAMETROS` y `JWT_EXP_HORAS` entraran en el compose sin llegar a
    las plantillas. El fallo concreto que eso habilita: `BIND_BACKEND` pasó a
    tener `127.0.0.1` por defecto, así que un operador que despliegue siguiendo
    una plantilla que se declara «inventario COMPLETO» levanta la pila y **no
    tiene nada alcanzable desde fuera de la máquina**, sin ninguna pista de qué
    perilla lo arregla.

    Derivándola del compose, la variable número treinta y uno entra sola.
    """
    declaradas = set()
    for linea in (RAIZ_REPO / plantilla).read_text(encoding="utf-8").splitlines():
        # Las comentadas cuentan: una variable numérica opcional se documenta
        # con su defecto a la vista (`#LOGIN_MAX_INTENTOS=5`) precisamente
        # porque entregarla vacía rompería `Settings` fuera de Docker.
        limpia = linea.strip().lstrip("#").strip()
        if "=" in limpia and limpia.partition("=")[0].strip().isupper():
            declaradas.add(limpia.partition("=")[0].strip())

    faltan = sorted(_variables_del_compose() - declaradas)

    assert not faltan, (
        f"«{plantilla}» no documenta {faltan}. Una variable que vive en el "
        "compose y no en la plantilla es una variable que el operador nunca "
        "llega a conocer — que es exactamente el P1 de la Fase 12.")


def test_la_plantilla_de_produccion_no_rompe_la_configuracion_al_copiarse():
    """Copiada a `.env`, debe construir `Settings` sin `ValidationError`.

    Bajo docker compose el `${VAR:-N}` enmascara el problema, pero `config.py`
    declara `env_file=".env"`, así que un despliegue SIN Docker —un PaaS, o
    systemd + uvicorn, que es el escenario «portable» del título de este
    bloque— lee este fichero tal cual. Con `LOGIN_MAX_INTENTOS=` vacío, el
    modelo falla con «Input should be a valid integer» y el proceso no arranca.
    De ahí que las numéricas vayan comentadas con su defecto a la vista.
    """
    numericas = {"LOGIN_MAX_INTENTOS", "LOGIN_VENTANA_MIN",
                 "HEALTH_TIMEOUT_SEGUNDOS", "SMTP_PUERTO", "JWT_EXP_HORAS",
                 "PURGA_CUENTAS_DIAS", "PURGA_TOKENS_DIAS"}

    vacias_y_activas = {linea.partition("=")[0].strip()
                        for linea in _lineas_utiles(ENV_PRODUCCION)
                        if "=" in linea and not linea.partition("=")[2].strip()}

    assert not (numericas & vacias_y_activas), (
        f"Estas variables son numéricas y no admiten cadena vacía: "
        f"{sorted(numericas & vacias_y_activas)}. Deben ir comentadas con su "
        "valor por defecto a la vista.")


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker no disponible")
def test_el_compose_es_valido_para_docker_y_no_solo_como_yaml():
    """`yaml.safe_load` valida sintaxis YAML, NO el esquema de Compose.

    Todos los demás tests de este fichero cargan el compose con PyYAML, que
    acepta sin protestar una errata en una clave de servicio: escribir `restrt:`
    en lugar de `restart:` pasaría la batería entera y se descubriría en el
    despliegue. Este test delega la validación en quien sí conoce el esquema.
    """
    entorno = {**os.environ, "POSTGRES_PASSWORD": "x", "JWT_SECRET": "x",
               "ADMIN_PASSWORD": "x"}

    r = subprocess.run(["docker", "compose", "config", "-q"], cwd=RAIZ_REPO,
                       capture_output=True, text=True, env=entorno)

    assert r.returncode == 0, f"docker compose rechaza el fichero:\n{r.stderr}"
