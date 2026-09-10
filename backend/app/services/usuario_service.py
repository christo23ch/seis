"""Gestión de usuarios, organizaciones (Fase 9) y autenticación."""
from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.core.security import hash_password, verify_password

ROLES_VALIDOS = ("admin", "analista", "lector")
ROLES_ORG_VALIDOS = ("propietario", "miembro")

# Motivos por los que un login con contraseña correcta puede no prosperar.
MOTIVO_SIN_VERIFICAR = "sin_verificar"
MOTIVO_DESACTIVADA = "desactivada"


def obtener_por_email(db: Session, email: str) -> models.Usuario | None:
    # `.strip()` además de `.lower()`: desde la Fase 10 la dirección llega de
    # formularios públicos, donde un espacio pegado al copiar del cliente de
    # correo es habitual. Sin recortarlo, la búsqueda falla y —como la respuesta
    # de `/recuperar` es neutra a propósito— el usuario no tendría forma de saber
    # por qué no le llega nada.
    return db.query(models.Usuario).filter(
        models.Usuario.email == email.strip().lower()).first()


def obtener_por_id(db: Session, usuario_id: str) -> models.Usuario | None:
    return db.get(models.Usuario, usuario_id)


def crear_usuario(db: Session, email: str, password: str, nombre: str | None = None,
                  rol: str = "analista", organizacion_id: str | None = None,
                  rol_org: str = "miembro", es_superadmin: bool = False,
                  activo: bool = True, email_verificado: bool = True) -> models.Usuario:
    """Alta de usuario. Por defecto queda operativo y con el correo dado por bueno.

    `email_verificado=True` por defecto **no es un descuido**: esta función la
    invocan el arranque (`scripts/init_db`), el superadmin y el propietario de
    una organización, que asignan la contraseña a mano. Son altas confiadas y no
    reciben correo de verificación, así que nacer sin verificar las dejaría
    permanentemente fuera —el login devuelve 403 a quien no ha verificado—. Es el
    mismo criterio que aplica el backfill de la migración 0006 a los usuarios
    anteriores a la Fase 10.

    Solo `registrar_usuario` (alta pública) pasa `activo=False,
    email_verificado=False`, porque ahí la dirección todavía no está demostrada.
    """
    if rol not in ROLES_VALIDOS:
        raise ValueError("rol inválido")
    if rol_org not in ROLES_ORG_VALIDOS:
        raise ValueError("rol de organización inválido")
    if obtener_por_email(db, email):
        raise ValueError("email ya registrado")
    # `.strip()` además de `.lower()` (Fase 16, M-4). `obtener_por_email` ya
    # recortaba, y esta no: un correo con un espacio pegado se guardaba con él y
    # quedaba **imposible de encontrar después**, de modo que la cuenta existía y
    # su titular no podía iniciar sesión, ni verificar, ni recuperar la clave.
    # No era alcanzable desde el alta pública —`EmailStr` recorta antes—, pero sí
    # desde `scripts/sembrar.py`, que lee ADMIN_EMAIL del entorno sin tocarlo.
    u = models.Usuario(email=email.strip().lower(), nombre=nombre,
                       hash_pwd=hash_password(password), rol=rol,
                       organizacion_id=organizacion_id, rol_org=rol_org,
                       es_superadmin=es_superadmin, activo=activo,
                       email_verificado=email_verificado)
    db.add(u)
    db.add(models.Auditoria(entidad="usuario", entidad_id=u.email, accion="crear",
                            delta={"rol": rol, "rol_org": rol_org,
                                   "organizacion_id": organizacion_id}))
    db.commit()
    db.refresh(u)
    return u


def autenticar(db: Session, email: str, password: str) -> models.Usuario | None:
    u = obtener_por_email(db, email)
    if u and u.activo and verify_password(password, u.hash_pwd):
        return u
    return None


def autenticar_con_motivo(db: Session, email: str,
                          password: str) -> tuple[models.Usuario | None, str | None]:
    """Como `autenticar`, pero distingue por qué falla cuando la clave es correcta.

    Existe para que el login pueda decirle a quien acaba de registrarse que le
    falta verificar el correo, en lugar de mentirle con «email o contraseña
    incorrectos». El motivo solo se devuelve a quien **ya acertó la contraseña**:
    ante credenciales erróneas, o ante un email inexistente, el motivo es `None`
    y el resultado es indistinguible.

    `autenticar` se mantiene intacta para no alterar el contrato de sus llamantes.
    """
    u = obtener_por_email(db, email)
    if not u or not verify_password(password, u.hash_pwd):
        return None, None
    if not u.email_verificado:
        return None, MOTIVO_SIN_VERIFICAR
    if not u.activo:
        return None, MOTIVO_DESACTIVADA
    return u, None


# ─────────────── Alta self-service (Fase 10) ───────────────

def registrar_usuario(db: Session, email: str, password: str,
                      nombre: str | None = None,
                      consentimientos: dict[str, bool] | None = None
                      ) -> models.Usuario | None:
    """Alta pública: organización propia + usuario propietario, sin activar.

    Devuelve `None` si la dirección ya tiene cuenta. El llamante **no** debe
    convertir ese `None` en un error distinto del camino feliz: la respuesta HTTP
    es idéntica exista o no la cuenta, y quien recibe el aviso del intento es el
    titular de la dirección por correo.

    Se comprueba la duplicidad antes de crear la organización; en el orden
    inverso, un email repetido dejaría una organización huérfana en cada intento.
    """
    if obtener_por_email(db, email):
        return None
    etiqueta = (nombre or email.split("@")[0]).strip()
    org = crear_organizacion(db, f"Organización de {etiqueta}"[:120])
    try:
        # Nace inactivo y sin verificar, en el propio INSERT: `get_current_user`
        # y `autenticar` ya comprueban `activo`, así que la cuenta no sirve para
        # nada hasta que su titular demuestre que controla la dirección. Fijarlo
        # aquí, y no mutándolo después, evita el instante entre dos commits en el
        # que la cuenta estaría activa.
        u = crear_usuario(db, email, password, nombre, rol="admin",
                          organizacion_id=org.id, rol_org="propietario",
                          es_superadmin=False, activo=False,
                          email_verificado=False)
    except (ValueError, IntegrityError):
        # Carrera perdida: entre nuestra comprobación de duplicidad y nuestro
        # commit, otra petición registró el mismo email. En PostgreSQL, con
        # READ COMMITTED, las dos peticiones pueden pasar la comprobación previa
        # y solo la segunda choca contra el UNIQUE de `usuario.email`. Sin este
        # `except`, el `IntegrityError` subiría hasta el router y produciría un
        # 500 justo en el endpoint cuyo contrato es «201 exista o no la cuenta».
        # Se deshace además la organización ya comiteada, que si no quedaría
        # huérfana: `crear_organizacion` comitea por su cuenta, de modo que el
        # rollback no la alcanza.
        db.rollback()
        huerfana = db.get(models.Organizacion, org.id)
        if huerfana is not None:
            db.delete(huerfana)
            db.commit()
        return None
    # Los consentimientos van en LA MISMA transacción que el alta (Fase 14). Si
    # se guardaran después, un fallo entre ambos commits dejaría una cuenta viva
    # sin constancia de qué aceptó su titular — y demostrar el consentimiento es
    # obligación del responsable, no del usuario.
    from app.services.cuenta_service import registrar_consentimientos
    registrar_consentimientos(db, u, consentimientos or {})

    db.add(models.Auditoria(quien=u.email, entidad="usuario", entidad_id=u.email,
                            accion="registro_self_service",
                            delta={"organizacion_id": org.id,
                                   "consentimientos": sorted(consentimientos or {})}))
    db.commit()
    db.refresh(u)
    return u


def verificar_email(db: Session, email: str) -> models.Usuario | None:
    """Marca la dirección como verificada y activa la cuenta."""
    u = obtener_por_email(db, email)
    if not u:
        return None
    u.email_verificado = True
    u.activo = True
    db.add(models.Auditoria(quien=u.email, entidad="usuario", entidad_id=u.email,
                            accion="verificar_email", delta={}))
    db.commit()
    db.refresh(u)
    return u


def cambiar_password(db: Session, usuario: models.Usuario,
                     nueva: str) -> models.Usuario:
    """Único punto del sistema que reescribe `hash_pwd`.

    Antes de la Fase 10 no existía ninguno: una contraseña asignada al crear la
    cuenta era definitiva. La auditoría deja constancia del cambio y **nunca**
    de la contraseña.
    """
    usuario.hash_pwd = hash_password(nueva)
    db.add(models.Auditoria(quien=usuario.email, entidad="usuario",
                            entidad_id=usuario.email, accion="cambiar_password",
                            delta={}))
    db.commit()
    db.refresh(usuario)
    return usuario


def marcar_jti(db: Session, jti: str, proposito: str) -> bool:
    """Reclama el `jti` de un token de un solo uso. False si ya estaba gastado.

    La exclusión la impone la clave primaria de `token_consumido`, no una lectura
    previa: comprobar y luego insertar dejaría una ventana en la que dos
    peticiones simultáneas con el mismo enlace pasarían las dos. Aquí, la que
    pierde la carrera recibe `IntegrityError` y se va con `False`.

    Se reclama **antes** de aplicar el efecto. Si el efecto fallara después, el
    token queda gastado sin haber servido: es el lado seguro del error, y el
    usuario siempre puede pedir otro enlace.
    """
    db.add(models.TokenConsumido(jti=jti, proposito=proposito))
    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


# ─────────────── Organizaciones y miembros (Fase 9) ───────────────

def crear_organizacion(db: Session, nombre: str) -> models.Organizacion:
    org = models.Organizacion(nombre=nombre)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def obtener_organizacion(db: Session, organizacion_id: str) -> models.Organizacion | None:
    return db.get(models.Organizacion, organizacion_id)


def miembros_de_org(db: Session, organizacion_id: str) -> list[models.Usuario]:
    return (db.query(models.Usuario)
            .filter(models.Usuario.organizacion_id == organizacion_id)
            .order_by(models.Usuario.creado_en).all())


def crear_miembro(db: Session, organizacion_id: str, email: str, password: str,
                  nombre: str | None = None, rol: str = "analista",
                  quien: str | None = None) -> models.Usuario:
    """Alta de un miembro dentro de una organización (la efectúa su propietario).

    El nuevo usuario es siempre `rol_org='miembro'` y nunca superadmin; su capacidad
    (admin/analista/lector) la fija el propietario dentro del abanico permitido.
    """
    if rol not in ("analista", "lector"):
        # un propietario no puede crear otros administradores de plataforma ni capacidades admin
        raise ValueError("un miembro solo puede tener capacidad 'analista' o 'lector'")
    u = crear_usuario(db, email, password, nombre, rol=rol,
                      organizacion_id=organizacion_id, rol_org="miembro",
                      es_superadmin=False)
    db.add(models.Auditoria(quien=quien, entidad="usuario", entidad_id=u.email,
                            accion="alta_miembro",
                            delta={"organizacion_id": organizacion_id, "rol": rol}))
    db.commit()
    return u


def set_activo_miembro(db: Session, miembro: models.Usuario, activo: bool,
                       quien: str | None = None) -> models.Usuario:
    miembro.activo = activo
    db.add(models.Auditoria(quien=quien, entidad="usuario", entidad_id=miembro.email,
                            accion="activar" if activo else "desactivar",
                            delta={"organizacion_id": miembro.organizacion_id}))
    db.commit()
    db.refresh(miembro)
    return miembro
