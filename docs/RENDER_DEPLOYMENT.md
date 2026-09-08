# SEIS — Guía de despliegue en Render

**Propósito:** Instrucciones paso a paso para desplegar SEIS en Render por primera vez.  
**Tiempo estimado:** 30 min (si tienes dominio + credenciales).  
**Requisitos previos:**
- Cuenta en Render (render.com)
- Dominio DNS (ej. tudominio.com) apuntando a Cloudflare
- Credenciales de Stripe (si integración de pagos, Fase 13)
- Credenciales de Sentry (opcional, Fase 11)

---

## 1. Preparación de credenciales

Antes de empezar, reúne estos datos (o genera en el paso correspondiente):

| Variable | Generación | Almacenamiento |
|----------|-----------|-----------------|
| `DATABASE_URL` | Render crea (durante setup) | Render Secrets |
| `REDIS_URL` | Render crea (durante setup) | Render Secrets |
| `JWT_SECRET` | Generar: `openssl rand -hex 32` | Render Secrets |
| `ADMIN_PASSWORD` | Tu contraseña fuerte (≥12 chars) | Render Secrets (cambiar del default) |
| `SENTRY_DSN` | (Opcional) Sentry project settings | Render Secrets |

---

## 2. Setup en Render Dashboard

### 2.1 Crear nuevo proyecto desde GitHub

1. Render Dashboard → **"New +"** → **"Blueprint"**
2. Conectar GitHub (autorizar Render app)
3. Seleccionar repositorio `seis`
4. Click **"Create from Blueprint"**
5. Render leerá automáticamente `render.yaml` del repositorio

### 2.2 Configurar servicios (automático desde render.yaml)

Render crea automáticamente:
- ✅ Backend web (FastAPI)
- ✅ Frontend web (Next.js)
- ✅ Worker (Celery)
- ✅ Beat scheduler (Celery beat)
- ✅ PostgreSQL database
- ✅ Redis database

**Verificar:** en Render Dashboard, ver que los 6 servicios aparecen

### 2.3 Configurar secretos

1. Render Dashboard → **"Environment"** (o cada servicio)
2. **"Add Secret"** para cada variable en tabla abajo:

```bash
# 1. JWT_SECRET (generar)
JWT_SECRET=$(openssl rand -hex 32)
echo $JWT_SECRET  # copiar valor

# 2. DATABASE_URL (Render lo proporciona tras crear PostgreSQL)
# Render dashboard → PostgreSQL → "Connections" → URL
# Formato: postgresql+psycopg2://user:password@host:5432/dbname

# 3. REDIS_URL (Render lo proporciona tras crear Redis)
# Render dashboard → Redis → "Connections" → URL
# Formato: redis://user:password@host:10000

# 4. ADMIN_PASSWORD (tu contraseña)
ADMIN_PASSWORD="tu_contraseña_fuerte_aqui"
```

**En Render Dashboard:**

| Servicio | Variable | Valor | Alcance |
|----------|----------|-------|---------|
| seis-backend | `DATABASE_URL` | (de Render PostgreSQL) | build + run |
| seis-backend | `REDIS_URL` | (de Render Redis) | run |
| seis-backend | `JWT_SECRET` | `openssl rand -hex 32` | run |
| seis-backend | `ADMIN_PASSWORD` | tu_contraseña | run |
| seis-backend | `SENTRY_DSN` | (si Sentry) | run |
| seis-backend | `SEIS_ENV` | `production` | run |
| seis-frontend | `NEXT_PUBLIC_API_URL` | `https://seis-backend-xxxxx.onrender.com` | build |
| seis-frontend | `NEXT_PUBLIC_SENTRY_DSN` | (si Sentry) | build |

**Nota:** `NEXT_PUBLIC_API_URL` es la URL pública del backend. Render genera: `https://seis-backend-XXXXX.onrender.com` (visible tras primera compilación).

### 2.4 Deploy inicial

1. Click **"Deploy"** en cada servicio (o en la blueprint, "Deploy all")
2. Esperar a que se compilen (5-10 min):
   - Backend build: instala deps, migraciones Alembic
   - Frontend build: npm ci, npm run build
   - Worker/Beat: instalan deps

3. **Monitorear logs:**
   - Render Dashboard → cada servicio → tab "Logs"
   - Buscar errores (color rojo)
   - Si ve `ERROR: jwt_secret es el de fábrica`, revisar secretos

---

## 3. Verificación post-deployment

```bash
# Una vez deployed:

# 1. Backend health check
curl https://seis-backend-XXXXX.onrender.com/api/v1/health
# Debe devolver: {"status": "ok", "servicio": "seis-backend"}

# 2. Swagger disponible
curl https://seis-backend-XXXXX.onrender.com/docs
# Debe devolver HTML (Swagger UI)

# 3. Frontend accesible
https://seis-frontend-XXXXX.onrender.com
# Debe ver login (redirección, ya que no autenticado)

# 4. Verificar envs:
#    Backend logs → debe ver "Sentry init..." si SENTRY_DSN configurado
#    Frontend build log → debe ver "API_URL=https://seis-backend-..."
```

---

## 4. Configurar dominio personalizado

### 4.1 En Render Dashboard

1. Servicio **seis-backend** → **"Settings"** → **"Custom Domain"**
   - Ingresar: `api.tudominio.com`
   - Render genera CNAME: `seis-backend-XXXXX.onrender.com`

2. Servicio **seis-frontend** → **"Settings"** → **"Custom Domain"**
   - Ingresar: `app.tudominio.com` (o `tudominio.com` si sin subdominio)
   - Render genera CNAME: `seis-frontend-XXXXX.onrender.com`

### 4.2 En Cloudflare (o tu proveedor DNS)

1. Cloudflare Dashboard → tudominio.com → **"DNS"**
2. Agregar registros CNAME:
   ```
   api.tudominio.com  →  seis-backend-XXXXX.onrender.com
   app.tudominio.com  →  seis-frontend-XXXXX.onrender.com
   ```
3. Esperar a que DNS propague (~5-15 min)
4. Verificar:
   ```bash
   curl https://api.tudominio.com/api/v1/health
   curl https://app.tudominio.com
   ```

---

## 5. Configurar CI/CD (GitHub Actions)

### 5.1 Agregar Deploy Hooks a GitHub Secrets

En Render Dashboard:

1. Servicio **seis-backend** → **"Settings"** → **"Deploy Hook"**
   - Generar URL: `https://api.render.com/deploy/srv-XXXXX?key=YYYY`
   - Copiar URL

2. GitHub Repository → **"Settings"** → **"Secrets and variables"** → **"Actions"**
   - Secret `RENDER_DEPLOY_HOOK_STAGING`     → hook del servicio de staging
   - Secret `RENDER_DEPLOY_HOOK_PRODUCCION`  → hook del servicio de producción
   - Variable `STAGING_URL`     → URL pública de staging
   - Variable `PRODUCCION_URL`  → URL pública de producción
   - Environment `produccion` con **Required reviewers**: sin eso, el despliegue
     manual a producción no tiene puerta de aprobación humana
   - (Pegando las URLs de Render)

### 5.2 Workflows activados

- `push a main` → CI (lint/test/build) → **auto-deploy a staging** (si CI verde)
- `workflow_dispatch (manual)` → deploy a production (requiere aprobación)

**Verificar:** GitHub → Actions → ver último workflow en verde

---

## 6. Configurar Sentry (opcional, pero recomendado)

### 6.1 Crear proyecto en Sentry

1. Sentry.io → Sign in / Sign up
2. **"Create Project"** → Plataforma: `Python` → **"Create Project"**
3. Sentry genera **DSN**: `https://key@sentry.io/project_id`
4. Copiar DSN

### 6.2 Agregar a Render Secrets

En Render Dashboard:
- seis-backend → Environment → **"Add Secret"**
  - `SENTRY_DSN` = (el DSN de Sentry)

- seis-frontend → Environment → **"Add Secret"**
  - `NEXT_PUBLIC_SENTRY_DSN` = (el DSN de Sentry)

### 6.3 Redeploy para activar

```bash
git commit --allow-empty -m "Activate Sentry"
git push origin main
# CI → auto-deploy a staging
# (opcional) Deploy a production vía workflow manual
```

Luego, en Sentry dashboard:
- Debe aparecer el proyecto SEIS con eventos llegando
- Si no: revisar logs de Render (puede faltar SENTRY_DSN)

---

## 7. Simulacro de restauración de backup

**Objetivo:** verificar que los backups funcionan (Fase 11 requisito).

### 7.1 Crear backup manual

Render lo hace automáticamente (diario), pero puedes forzar:

1. Render Dashboard → PostgreSQL → **"Backups"**
2. Click **"Backup now"** (opcional, pero verifica que funciona)
3. Esperar ~2 min

### 7.2 Restaurar a BD temporal

1. En "Backups" → click sobre un backup → **"Restore"**
2. Opción: **"Restore to new database"**
3. Render crea nueva BD con los datos del backup
4. Copiar CONNECTION STRING de la nueva BD

### 7.3 Verificar integridad

```bash
# Conectarse a BD de backup
psql "<CONNECTION_STRING_BACKUP>"

# Verificar tablas principales
SELECT COUNT(*) FROM usuario;
SELECT COUNT(*) FROM analisis;
SELECT COUNT(*) FROM subasta;

# Debe devolver números razonables (no cero, a no ser que BD esté vacía)
```

### 7.4 Limpiar

Render → PostgreSQL → **"Resources"** → eliminar la BD temporal (no es gratis guardarla)

**Documentar:** tiempo de restauración (ej. "5 min para 10GB"), y que procedimiento funciona.

---

## 8. Verificar seguridad mínima

```bash
# 1. JWT_SECRET no es default
#    Backend logs → debe mostrar error si JWT_SECRET="cambia-este-..."

# 2. HTTPS en todos lados
#    Verificar: curl -i https://app.tudominio.com | grep Strict-Transport

# 3. Cloudflare WAF
#    Cloudflare dashboard → tudominio.com → "Security" → "WAF Rules" → activar básicas

# 4. Rate limiting (automático en backend)
#    Hacer 10 requests rápido a /auth/login → debe devolver 429 en el 6º
```

---

## 9. Checklist de go-live

Antes de comunicar a usuarios que está listo:

- [ ] Health check devuelve 200 (ojo: es un health simple, no verifica BD ni Redis)
- [ ] Login funciona (crear test user, verificar email)
- [ ] Análisis se puede crear y guardar
- [ ] PDF se genera sin error
- [ ] Sentry recibe eventos (opcional pero recomendado)
- [ ] Backup se restaura sin corrupción
- [ ] HTTPS en todos los dominios
- [ ] RUNBOOK.md leído y equipo lo entiende
- [ ] Contactos de emergencia configurados

---

## 10. Troubleshooting común

### Problema: "Build failed for seis-backend"

**Causa:** Dependencia falta o falla Alembic.

**Solución:**
1. Render Logs → seis-backend → "Build"
2. Buscar línea roja (error)
3. Común: `pip install` timeout → click "Retry" en Render
4. Si persiste: `pip list` en local, verificar `requirements.txt`

### Problema: "Database connection refused"

**Causa:** DATABASE_URL incorrecto o BD no lista.

**Solución:**
1. Copiar DATABASE_URL correcto desde Render PostgreSQL
2. Verificar caracteres especiales (encriptar si es necesario)
3. Render → PostgreSQL → "Status" → verde = healthy
4. Esperar 1-2 min tras crear la BD

### Problema: "Frontend build hangs"

**Causa:** `NEXT_PUBLIC_API_URL` falta o es wrongly formatted.

**Solución:**
1. Frontend env → verificar `NEXT_PUBLIC_API_URL` = `https://api.tudominio.com`
2. Redeploy
3. Check logs: debe ver "API_URL=https://..."

### Problema: Sentry no recibe eventos

**Causa:** SENTRY_DSN vacío o incorrecto.

**Solución:**
1. Backend env → verificar `SENTRY_DSN`
2. Redeploy backend
3. Trigger error (ej. crear análisis con input inválido)
4. Sentry dashboard → debe aparecer evento en <30s

---

**Fin de Guía de Despliegue en Render**

Próximas fases:
- Fase 12: Notificaciones multicanal
- Fase 13: Stripe y monetización
- Fase 14: Cumplimiento legal (RGPD)

Duda o problema: revisar RUNBOOK.md para operaciones de producción.
