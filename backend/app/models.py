"""Modelos ORM — implementación del esquema §5.2 de la especificación SEIS.

Nota de fase (documentada en README): lat/lng se persisten como Numeric en la Fase 1;
la migración a geometry(Point,4326) de PostGIS llega con el módulo de mapa (Fase 5).
docker-compose ya levanta postgis/postgis, por lo que la migración es un ALTER, no un cambio de infra.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (Boolean, DateTime, ForeignKey, Integer, Numeric, SmallInteger,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, PortableJSON


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Organizacion(Base):
    """Tenant (Fase 9): unidad de aislamiento de análisis y resultados reales.

    Los datos históricos se asignan a una organización «por defecto» en el backfill
    de la migración 0002. El aislamiento efectivo aparece en cuanto existe una segunda.
    """
    __tablename__ = "organizacion"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    nombre: Mapped[str] = mapped_column(String(120))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class FuenteSubasta(Base):
    __tablename__ = "fuente_subasta"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(32), unique=True)   # judicial_boe, aeat, tgss, ...
    perfil: Mapped[dict] = mapped_column(PortableJSON, default=dict)


class Subasta(Base):
    __tablename__ = "subasta"
    # Fase 17-A: dedupe de la ingesta. Los NULL no colisionan entre sí en SQL, de
    # modo que las altas manuales sin identificador externo siguen siendo posibles.
    __table_args__ = (UniqueConstraint("fuente_codigo", "identificador_externo",
                                       name="uq_subasta_fuente_identificador"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    fuente_codigo: Mapped[str] = mapped_column(String(32), index=True)
    identificador_externo: Mapped[str | None] = mapped_column(String(120))
    url: Mapped[str | None] = mapped_column(Text)
    valor_subasta: Mapped[float] = mapped_column(Numeric(14, 2))
    puja_minima: Mapped[float | None] = mapped_column(Numeric(14, 2))
    tramo: Mapped[float | None] = mapped_column(Numeric(12, 2))
    deposito_pct: Mapped[float] = mapped_column(Numeric(6, 4), default=0.05)
    fecha_cierre: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estado: Mapped[str] = mapped_column(String(16), default="abierta", index=True)
    subastas_desiertas_previas: Mapped[int] = mapped_column(SmallInteger, default=0)
    datos_brutos: Mapped[dict] = mapped_column(PortableJSON, default=dict)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    activos: Mapped[list["Activo"]] = relationship(back_populates="subasta")


class Activo(Base):
    __tablename__ = "activo"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    subasta_id: Mapped[str] = mapped_column(ForeignKey("subasta.id"), index=True)
    lote: Mapped[int] = mapped_column(SmallInteger, default=1)
    tipologia: Mapped[str] = mapped_column(String(24), index=True)
    ref_catastral: Mapped[str | None] = mapped_column(String(24), index=True)
    finca_registral: Mapped[str | None] = mapped_column(String(40))
    direccion: Mapped[str | None] = mapped_column(Text)
    municipio: Mapped[str | None] = mapped_column(String(80), index=True)
    provincia: Mapped[str | None] = mapped_column(String(40))
    ccaa: Mapped[str | None] = mapped_column(String(32))
    lat: Mapped[float | None] = mapped_column(Numeric(9, 6))
    lng: Mapped[float | None] = mapped_column(Numeric(9, 6))
    superficie_m2: Mapped[float | None] = mapped_column(Numeric(10, 2))
    anio_construccion: Mapped[int | None] = mapped_column(SmallInteger)
    estado_conservacion: Mapped[str | None] = mapped_column(String(16))
    es_vivienda_habitual: Mapped[bool | None] = mapped_column(Boolean)
    vpo: Mapped[bool] = mapped_column(Boolean, default=False)
    atributos: Mapped[dict] = mapped_column(PortableJSON, default=dict)
    subasta: Mapped[Subasta] = relationship(back_populates="activos")
    cargas: Mapped[list["Carga"]] = relationship(back_populates="activo")


class Carga(Base):
    __tablename__ = "carga"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    activo_id: Mapped[str] = mapped_column(ForeignKey("activo.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(32))
    rango: Mapped[int | None] = mapped_column(SmallInteger)
    importe: Mapped[float | None] = mapped_column(Numeric(14, 2))
    es_anterior: Mapped[bool] = mapped_column(Boolean, default=False)
    se_purga: Mapped[bool] = mapped_column(Boolean, default=True)
    verificada: Mapped[bool] = mapped_column(Boolean, default=False)
    activo: Mapped[Activo] = relationship(back_populates="cargas")


class Comparable(Base):
    __tablename__ = "comparable"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tipologia: Mapped[str] = mapped_column(String(24), index=True)
    municipio: Mapped[str | None] = mapped_column(String(80), index=True)
    superficie_m2: Mapped[float | None] = mapped_column(Numeric(10, 2))
    precio: Mapped[float | None] = mapped_column(Numeric(14, 2))
    precio_m2: Mapped[float | None] = mapped_column(Numeric(10, 2))
    estado: Mapped[str | None] = mapped_column(String(16))
    origen: Mapped[str | None] = mapped_column(String(24))          # portal_oferta | testigo | notarial
    fecha_dato: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activo_flag: Mapped[bool] = mapped_column(Boolean, default=True)


class Analisis(Base):
    """Snapshot inmutable (P1/P2): entrada completa + versiones + índices + salidas."""
    __tablename__ = "analisis"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organizacion_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizacion.id"), index=True)     # Fase 9: aislamiento por tenant
    activo_id: Mapped[str | None] = mapped_column(ForeignKey("activo.id"), index=True)
    perfil_codigo: Mapped[str] = mapped_column(String(32), index=True)
    version_reglas: Mapped[str] = mapped_column(String(16))
    version_parametros: Mapped[str] = mapped_column(String(16))
    entrada: Mapped[dict] = mapped_column(PortableJSON)             # AnalisisInput serializado
    hechos: Mapped[dict] = mapped_column(PortableJSON)              # pizarra final serializada
    resultado: Mapped[dict] = mapped_column(PortableJSON)           # AnalisisResult completo
    ici: Mapped[int | None] = mapped_column(SmallInteger)
    icu: Mapped[int | None] = mapped_column(SmallInteger)
    ra: Mapped[int | None] = mapped_column(SmallInteger)
    ico: Mapped[int | None] = mapped_column(SmallInteger)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    riesgos: Mapped[list["RiesgoEvaluado"]] = relationship(back_populates="analisis")
    escenarios: Mapped[list["Escenario"]] = relationship(back_populates="analisis")
    decision: Mapped["Decision"] = relationship(back_populates="analisis", uselist=False)
    reglas_disparadas: Mapped[list["ReglaDisparada"]] = relationship(back_populates="analisis")


class RiesgoEvaluado(Base):
    __tablename__ = "riesgo_evaluado"
    analisis_id: Mapped[str] = mapped_column(ForeignKey("analisis.id"), primary_key=True)
    dimension: Mapped[str] = mapped_column(String(16), primary_key=True)
    probabilidad: Mapped[int] = mapped_column(SmallInteger)
    impacto: Mapped[int] = mapped_column(SmallInteger)
    score: Mapped[int] = mapped_column(SmallInteger)
    nivel: Mapped[str] = mapped_column(String(8))
    mitigable: Mapped[bool] = mapped_column(Boolean, default=True)
    condiciones: Mapped[list] = mapped_column(PortableJSON, default=list)
    evidencias: Mapped[list] = mapped_column(PortableJSON, default=list)
    analisis: Mapped[Analisis] = relationship(back_populates="riesgos")


class Escenario(Base):
    __tablename__ = "escenario"
    analisis_id: Mapped[str] = mapped_column(ForeignKey("analisis.id"), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(12), primary_key=True)
    probabilidad: Mapped[float] = mapped_column(Numeric(4, 3))
    vs: Mapped[float] = mapped_column(Numeric(14, 2))
    plazo_meses: Mapped[float] = mapped_column(Numeric(5, 1))
    coste_total: Mapped[float] = mapped_column(Numeric(14, 2))
    beneficio: Mapped[float] = mapped_column(Numeric(14, 2))
    roi: Mapped[float] = mapped_column(Numeric(7, 4))
    analisis: Mapped[Analisis] = relationship(back_populates="escenarios")


class Decision(Base):
    __tablename__ = "decision"
    analisis_id: Mapped[str] = mapped_column(ForeignKey("analisis.id"), primary_key=True)
    semaforo: Mapped[str] = mapped_column(String(8), index=True)
    p_ideal: Mapped[float | None] = mapped_column(Numeric(14, 2))
    p_objetivo: Mapped[float | None] = mapped_column(Numeric(14, 2))
    p_max: Mapped[float | None] = mapped_column(Numeric(14, 2))
    p_limite: Mapped[float | None] = mapped_column(Numeric(14, 2))
    margen_seguridad: Mapped[float | None] = mapped_column(Numeric(6, 4))
    p_adj_esperado: Mapped[float | None] = mapped_column(Numeric(14, 2))
    rvc: Mapped[float | None] = mapped_column(Numeric(6, 3))
    vetos: Mapped[list] = mapped_column(PortableJSON, default=list)
    condiciones: Mapped[list] = mapped_column(PortableJSON, default=list)
    analisis: Mapped[Analisis] = relationship(back_populates="decision")


class ReglaDisparada(Base):
    __tablename__ = "regla_disparada"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analisis_id: Mapped[str] = mapped_column(ForeignKey("analisis.id"), index=True)
    regla_codigo: Mapped[str] = mapped_column(String(32))
    regla_version: Mapped[str] = mapped_column(String(16))
    efecto: Mapped[dict] = mapped_column(PortableJSON, default=dict)
    evidencias: Mapped[list] = mapped_column(PortableJSON, default=list)
    orden: Mapped[int] = mapped_column(SmallInteger, default=0)
    analisis: Mapped[Analisis] = relationship(back_populates="reglas_disparadas")


class Regla(Base):
    """Conocimiento versionado T2 (§8.3): la BD es la fuente de verdad en producción."""
    __tablename__ = "regla"
    codigo: Mapped[str] = mapped_column(String(32), primary_key=True)
    version: Mapped[str] = mapped_column(String(16), primary_key=True)
    categoria: Mapped[str] = mapped_column(String(16), index=True)
    prioridad: Mapped[int] = mapped_column(SmallInteger, default=100)
    definicion: Mapped[dict] = mapped_column(PortableJSON)
    vigente_desde: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    vigente_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    autor: Mapped[str | None] = mapped_column(String(80))
    justificacion: Mapped[str | None] = mapped_column(Text)


class Parametro(Base):
    """Parámetros legales/técnicos versionados T3 (§5.2)."""
    __tablename__ = "parametro"
    clave: Mapped[str] = mapped_column(String(64), primary_key=True)
    ambito: Mapped[str] = mapped_column(String(32), primary_key=True, default="nacional")
    vigente_desde: Mapped[str] = mapped_column(String(10), primary_key=True, default="2026-01-01")
    valor: Mapped[dict] = mapped_column(PortableJSON)
    fuente_legal: Mapped[str | None] = mapped_column(Text)


class PerfilInversion(Base):
    __tablename__ = "perfil_inversion"
    codigo: Mapped[str] = mapped_column(String(32), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(64))
    parametros: Mapped[dict] = mapped_column(PortableJSON)


class ResultadoReal(Base):
    """Bucle de feedback T5 (§20)."""
    __tablename__ = "resultado_real"
    analisis_id: Mapped[str] = mapped_column(ForeignKey("analisis.id"), primary_key=True)
    precio_adjudicacion: Mapped[float | None] = mapped_column(Numeric(14, 2))
    adjudicatario_propio: Mapped[bool | None] = mapped_column(Boolean)
    coste_real_total: Mapped[float | None] = mapped_column(Numeric(14, 2))
    precio_venta_real: Mapped[float | None] = mapped_column(Numeric(14, 2))
    plazo_real_meses: Mapped[int | None] = mapped_column(SmallInteger)
    incidencias: Mapped[dict] = mapped_column(PortableJSON, default=dict)


class Usuario(Base):
    __tablename__ = "usuario"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    nombre: Mapped[str | None] = mapped_column(String(80))
    hash_pwd: Mapped[str] = mapped_column(String(200))
    rol: Mapped[str] = mapped_column(String(16), default="analista")   # capacidad: admin | analista | lector
    organizacion_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizacion.id"), index=True)     # Fase 9: tenant al que pertenece
    rol_org: Mapped[str] = mapped_column(String(16), default="miembro")  # propietario | miembro
    es_superadmin: Mapped[bool] = mapped_column(Boolean, default=False)  # plataforma: gobierna T2/T3 global
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    # Fase 10: distinto de `activo`, que es el alta/baja administrativa que ejerce el
    # propietario. Separarlos evita que reactivar a un miembro lo dé por verificado.
    email_verificado: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PreferenciasNotificacion(Base):
    """Fase 12: preferencias de notificación por usuario (1:1 con usuario)."""
    __tablename__ = "preferencias_notificacion"
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuario.id"), primary_key=True)
    canales: Mapped[list] = mapped_column(PortableJSON, default=list)   # ["email","telegram"]
    modo: Mapped[str] = mapped_column(String(16), default="instantaneo")  # instantaneo | digest_diario | digest_semanal
    hora_digest: Mapped[int] = mapped_column(SmallInteger, default=8)     # hora local 0-23
    silencio_inicio: Mapped[int | None] = mapped_column(SmallInteger)     # franja de silencio (horas)
    silencio_fin: Mapped[int | None] = mapped_column(SmallInteger)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(32))
    comunicaciones_activas: Mapped[bool] = mapped_column(Boolean, default=True)


class CodigoTelegram(Base):
    """Fase 12: código efímero de vinculación de Telegram (10 min, un solo uso)."""
    __tablename__ = "codigo_telegram"
    codigo: Mapped[str] = mapped_column(String(6), primary_key=True)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuario.id"), index=True)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usado: Mapped[bool] = mapped_column(Boolean, default=False)


class TokenConsumido(Base):
    """Fase 10: `jti` de un token de propósito ya gastado (uso único).

    `crear_token_proposito` emite un `jti` desde la Fase 12, pero nadie lo
    persistía: un enlace de verificación o de reseteo era reutilizable tantas
    veces como cupiera en su TTL. Esta tabla es el registro que lo impide.
    Misma disciplina que `CodigoTelegram`: se marca gastado ANTES de aplicar el
    efecto, y quien lo reutiliza recibe la misma respuesta que quien trae un
    token inválido o caducado.
    """
    __tablename__ = "token_consumido"
    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    proposito: Mapped[str] = mapped_column(String(24))
    consumido_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Alerta(Base):
    """Fase 12: alerta de captación privada por usuario (CLAUDE.md §4)."""
    __tablename__ = "alerta"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuario.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(120))
    criterios: Mapped[dict] = mapped_column(PortableJSON, default=dict)  # fuente, valor_max, score_min…
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Notificacion(Base):
    """Fase 12: notificación generada por el matcher; se envía al instante o en digest."""
    __tablename__ = "notificacion"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuario.id"), index=True)
    alerta_id: Mapped[str | None] = mapped_column(ForeignKey("alerta.id"))
    asunto: Mapped[str] = mapped_column(String(200))
    cuerpo: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(12), default="pendiente", index=True)  # pendiente | enviada | error
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    enviado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Auditoria(Base):
    __tablename__ = "auditoria"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quien: Mapped[str | None] = mapped_column(String(120))  # cierre Fase 12 (P0.4): antes String(36), truncaba emails
    cuando: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    entidad: Mapped[str] = mapped_column(String(32))
    entidad_id: Mapped[str] = mapped_column(String(36))
    accion: Mapped[str] = mapped_column(String(32))
    delta: Mapped[dict] = mapped_column(PortableJSON, default=dict)


__all__ = [n for n in dir() if n[0].isupper()]
