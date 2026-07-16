# SEIS — Runbook de operaciones en producción

**Propósito:** Procedimientos operacionales paso a paso para administradores y equipos SRE.  
**Lenguaje:** Español (requisito del proyecto SEIS).  
**Última actualización:** 2026-07-16 (Fase 11).

---

## 1. Arranque y despliegue

### 1.1 Arranque local (desarrollo)

```bash
cd /ruta/a/seis
cp .env.example .env
docker compose up -d --build

# Verificar
curl http://localhost:8000/health      # Backend
curl http://localhost:3000            # Frontend
curl http://localhost:8000/docs       # Swagger
```

**Credenciales de arranque:**
- Email: `admin@seis.local`
- Contraseña: `admin` (cambiar tras primer login en producción)

### 1.2 Despliegue en Render (producción)

**Requisitos previos:**
1. Dominio comprado y apuntando a Render (vía Cloudflare DNS)
2. Proyecto Render creado con `render.yaml` del repositorio
3. Variables de entorno configuradas en Render (secretos):
   - `DATABASE_URL`: Connection string PostgreSQL (ej. `postgresql+psycopg2://user:pass@host/db`)
   - `REDIS_URL`: Redis URL (ej. `redis://host:6379/0`)
   - `JWT_SECRET`: String aleatorio ≥32 caracteres (generar: `openssl rand -hex 32`)
   - `ADMIN_PASSWORD`: Cambiar del default `admin` a una contraseña fuerte
   - `SENTRY_DSN`: (Opcional) DSN de Sentry si se usa observabilidad
   - `SENTRY_ENVIRONMENT`: `production`

**Procedimiento:**
1. Hacer push a `main` (trigger: CI verde → deploy automático a staging)
2. Verificar staging: `curl https://seis-staging.onrender.com/health`
3. En GitHub, ejecutar **workflow manual** `Deploy to Production` (requiere aprobación)
4. Esperar ~5 min a que Render redepliegue todos los servicios
5. Verificar producción: `curl https://app.tudominio.com/health`

**Monitoreo:**
- Logs en Render Console (cada servicio tiene tab de logs)
- Sentry: alertas en tiempo real de errores críticos
- UptimeRobot / BetterStack: monitoreo de disponibilidad

---

## 2. Rollback de un despliegue

### 2.1 Rollback inmediato (Render)

Si algo falla tras desplegar:

```bash
# En la consola de Render, ir a cada servicio y:
# 1. "Settings" → "Deploy"
# 2. "Manual deploys" → seleccionar commit anterior
# 3. "Deploy"
```

Alternativa por CLI (si tienes acceso):
```bash
git revert HEAD --no-edit
git push origin main  # Trigger: CI → deploy a staging → aprobación manual a producción
```

### 2.2 Rollback de BD (restaurar backup)

**SOLO en caso de data corruption (muy raro):**

```bash
# 1. En Render Dashboard → base de datos PostgreSQL → "Backups"
# 2. Seleccionar backup del día anterior
# 3. "Restore to new database"
# 4. Cambiar DATABASE_URL en secretos a la nueva BD
# 5. Redeploy todos los servicios
```

⚠️ **Cuidado:** los datos entre snapshots se pierden. Último recurso.

---

## 3. Restauración de datos (ARCO/RGPD)

### 3.1 Exportar datos de un usuario

```bash
# En la DB de Render:
psql $DATABASE_URL

SELECT * FROM usuario WHERE email = 'usuario@example.com';
SELECT * FROM analisis WHERE usuario_id = <id> ORDER BY creado DESC;
SELECT * FROM resultado_real WHERE usuario_id = <id>;
SELECT * FROM alerta WHERE usuario_id = <id>;
```

Luego empaquetar como JSON/CSV y entregar al usuario.

### 3.2 Borrado de cuenta (Fase 14: RGPD)

Operación de borrado con gracia de 14 días (implementada automática vía tarea Celery):

```bash
# El usuario solicita borrado en la UI (/cuenta) → tarea programada
# Backend marca: usuario.fecha_borrado_solicitado = ahora() + 14 días
# Después de 14 días, tarea `limpiar_borrados_vencidos` (Celery beat):
#   - Elimina todos los datos del usuario
#   - Anonimiza auditoría (quien → "usuario eliminado")
#   - Si era único miembro de su org → elimina org también
```

Para borrado **INMEDIATO** (datos críticos, solicitud legal):
```bash
# (Raro, requiere aprobación legal)
# Por ahora: manual en DB, luego documentar y respaldar
```

---

## 4. Incidentes comunes

### 4.1 BD PostgreSQL caída o inaccessible

**Síntomas:**
```
GET /health → {"status": "error", "componentes": {"db": {"status": "error", ...}}}
Logs: "could not translate host name"
```

**Acciones:**
1. Verificar en Render Dashboard → PostgreSQL → "Status" (verde = sano)
2. Si está roja: esperar (Render restablece automático)
3. Si persiste >5 min:
   - Reiniciar BD (Render: Settings → "Restart database")
   - Si sigue: contactar soporte Render (plan premium)
4. Aplicación degrada automático: `/health` = 503, algunos endpoints fallan

**Prevención:**
- Connection pooling activado (Supabase/Render lo maneja)
- Backups diarios probados
- Monitoreo de storage en Render

### 4.2 Redis caído

**Síntomas:**
```
GET /health → {"status": "degraded", "componentes": {"redis": {"status": "error", ...}}}
Rate-limiting no funciona (fallback a memoria → 15 min)
Celery tasks pueden atrasarse
```

**Acciones:**
1. Verificar Render → Redis → Status
2. Reiniciar: Settings → "Restart" (1 min downtime)
3. Verificar reconexión: esperar 30s y `curl /health`

**Prevención:**
- Rate-limiting tiene fallback en memoria (funciona sin Redis)
- Celery usa fallback: si Redis no responde, intenta en-process
- Monitor en Sentry: alertas de excepciones Redis

### 4.3 Conector de ingesta BOE colgado (timeout)

**Síntomas:**
```
Logs: "timeout fetching BOE.es"
Subastas nuevas no se actualizan
```

**Acciones:**
1. Revisar logs de Celery beat: `seis-beat` en Render
2. El worker tiene retry exponencial (3 intentos, backoff 60s/300s/900s)
3. Si persiste:
   - Verificar que BOE.es está online (manual: `curl https://subastas.boe.es`)
   - Cambiar `INGESTA_BOE_BASE_URL` en secretos si has identificado alternativa
   - Redeploy
4. En Sentry: buscar "BOE" para ver historial de fallos

**Prevención:**
- Timeouts configurables (§38: `INGESTA_BOE_TIMEOUT=30s`)
- Logs detallados de cada intento (debugging rápido)
- Alternativas documentadas (si BOE.es cae largo plazo)

### 4.4 Memoria llena en Celery worker

**Síntomas:**
```
Worker crashes sin error
Render autorestart (visible en logs)
Análisis grandes fallan con OOM
```

**Acciones:**
1. En Render, aumentar plan de `seis-worker` (starter → standard)
2. Reducir `celery worker --concurrency=2` si es muy agresivo
3. Revisar si hay análisis patológicamente grandes (puede fallar legalmente)

**Prevención:**
- Monitoring de memoria: Sentry + Render metricas
- Limitar concurrency según plan (starter → 2, standard → 4)

---

## 5. Rotación de secretos (sin downtime)

### 5.1 Cambiar JWT_SECRET

⚠️ **Atención:** todos los tokens activos se invalidan (usuarios se desloguean).

```bash
# 1. Generar nuevo secret
NEW_SECRET=$(openssl rand -hex 32)

# 2. En Render Dashboard → secretos → JWT_SECRET → cambiar a NEW_SECRET
# 3. Redeploy solo backend (sin redeploy de frontend)

# 4. Frontend: usuarios verán error 401 → redirige a /login
#    (normal y esperado)

# 5. Verificar: login funciona con nueva sesión
```

### 5.2 Cambiar contraseña de PostgreSQL

```bash
# 1. En Render → PostgreSQL → Users → cambiar password
# 2. Copiar nuevo usuario/password
# 3. En secretos: actualizar DATABASE_URL con nuevo password
# 4. Redeploy backend/worker/beat

# 5. Verificar health: GET /health → {"status": "ok", "db": {"status": "ok"}}
```

### 5.3 Cambiar clave Stripe / Sentry / etc.

```bash
# Procedimiento genérico (sin downtime):
# 1. En Render secretos → actualizar VARIABLE = nuevo_valor
# 2. Redeploy solo si el módulo se inicializa en startup
#    (ej. Sentry: sí; Stripe: posiblemente no si es lazy-loaded)
# 3. Verificar en logs que se inicializó correctamente
```

---

## 6. Observabilidad y alertas

### 6.1 Sentry (errores en tiempo real)

**URL:** https://sentry.io → proyecto SEIS

**Qué hace:**
- Captura excepciones no capturadas (500 errors)
- Rastrea performance (tracing), errores de BD, Celery timeouts
- Integrado en backend (FastAPI) y frontend (Next.js)

**Alertas configuradas:**
- Error rate > 1% en 5 min → Slack / Email
- Excepción crítica (ej. DB connection lost) → inmediato

**Debugging:**
```bash
# Ver errores recientes:
# 1. Sentry Dashboard → Errors
# 2. Filtrar por "release", "environment", "error message"
# 3. Stack trace con contexto (locals, request body, etc.)
```

### 6.2 UptimeRobot / BetterStack (disponibilidad)

**URL:** Configurar manualmente tras setup (Fase 11 solo código)

**Qué hace:**
- Ping a `/health` cada 5 min desde múltiples locaciones
- Detecta caídas en <1 min, alertas inmediatas
- Status page pública (opcional)

**Setup:**
1. Registrarse en UptimeRobot o BetterStack
2. Crear monitor: `https://app.tudominio.com/health`
3. Interval: 5 min, timeout: 15s
4. Alertas a email/Slack si status != 200

### 6.3 Render Logs

**Acceso:**
1. Render Dashboard → cada servicio (backend, frontend, worker, beat)
2. Tab "Logs"
3. Filtrar por timestamp, buscar por error message

**Logs útiles:**
- Backend: uvicorn startup, endpoint access, excepciones
- Worker: Celery task start/complete, errores de análisis
- Beat: cron job execution, errors
- Frontend: build errors (si los hay)

---

## 7. Mantenimiento rutinario

### 7.1 Chequeo semanal (automatizado)

```bash
# Estos chequeos son informativos (no requieren acción salvo nota):

# 1. Backups intactos
#    Render: PostgreSQL → Backups → verificar último ≤24h

# 2. Dependencias actualizadas
#    GitHub: Dependabot alerts (fijado en CI)

# 3. Errores en Sentry
#    Sentry: Issues → revisar si hay nuevos errores críticos

# 4. Disponibilidad
#    UptimeRobot: historial de uptime (debe ser >99.5%)
```

### 7.2 Chequeo mensual

```bash
# 1. Rotación de logs (Sentry/Render retienen 30 días)
# 2. Revisión de seguridad: deps. vulnerables (npm audit, pip audit)
# 3. Performance: Core Web Vitals en frontend (Lighthouse CI)
# 4. Capacidad de BD: "SELECT pg_database_size(current_database())"
#    Si > 80 % del plan → notificar y actualizar plan
```

### 7.3 Chequeo trimestral

```bash
# 1. Simulacro de restauración de backup
#    - Crear BD temporal en Render
#    - Restaurar backup de 7 días atrás
#    - Verificar integridad (SELECT COUNT(*) en tablas principales)
#    - Documentar tiempo de restauración
#
# 2. Revisión de plan (rendimiento, costos)
#    - ¿CPU de worker al máximo? → aumentar plan
#    - ¿BD creciendo muy rápido? → purgar logs antiguos
#
# 3. Simulacro de failover (manual en Render)
#    - Simular: reiniciar BD, verificar que aplicación se recupera
```

---

## 8. Contactos de emergencia y escalada

### Escala de severidad

| Nivel | Ejemplo | Acción | Tiempo |
|-------|---------|--------|--------|
| 🔴 **Crítico** | APP DOWN | Oncall inmediato, slack emergencia | <15 min |
| 🟠 **Alto** | 50 % errores, BD lento | Reunión SRE, investigar 1h | <1h |
| 🟡 **Medio** | Error rate 5-10 %, algo degradado | Ticket, investigar 24h | <24h |
| 🟢 **Bajo** | Logs ruido, optimización | Backlog, iterar en sprint | Flexible |

### Contactos

**Responsable de operaciones (día):** [TU NOMBRE/CORREO]  
**Responsable de operaciones (noche):** [ON-CALL SCHEDULE]  
**Slack emergencia:** `#seis-incidents`  
**Escalada Render:** https://support.render.com (chat, email)  
**Escalada Stripe:** https://support.stripe.com (si es pago afectado)  

---

## 9. Glosario de herramientas

| Herramienta | URL | Propósito |
|-------------|-----|----------|
| **Render** | https://render.com | Hosting (app, BD, Redis) |
| **Cloudflare** | https://dash.cloudflare.com | DNS, WAF, caché |
| **Sentry** | https://sentry.io | Monitoreo de errores |
| **UptimeRobot** | https://uptimerobot.com | Monitoreo de disponibilidad |
| **GitHub** | https://github.com | Repositorio, CI/CD |
| **PostgreSQL CLI** | `psql` | Acceso directo a BD (emergencias) |

---

**Fin de RUNBOOK.md**

Versión: 1.0.0 (Fase 11)  
Próxima revisión: 2026-08-16 (mensual)
