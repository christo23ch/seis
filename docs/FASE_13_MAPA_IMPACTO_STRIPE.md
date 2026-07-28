# FASE 13: MAPA DE IMPACTO — Integración de Stripe

**Fecha:** 2026-07-25  
**Proyecto:** SEIS  
**Rama:** feature/fase-13-stripe (a crear)  
**Alcance:** Integración de monetización con Stripe (suscripciones, facturación, webhooks)

---

> ## ⚠️ DOCUMENTO PARCIALMENTE SUPERADO
>
> Este mapa se usó como insumo para el plan de ejecución, y la **revisión de diseño y seguridad
> del 2026-07-25 encontró errores confirmados en él**. Varias secciones son incorrectas y **no
> deben implementarse tal cual**:
>
> | Sección | Problema |
> |---|---|
> | **§2.1** `EventoFacturacion` | **Sin columna para el id de evento de Stripe** → la idempotencia descrita es inservible. `referencia_stripe` es el id del sub-objeto, no del `Event` |
> | **§2.1** `Organizacion` / `Suscripcion` | 3 columnas duplicadas; 1:1 que destruye el histórico; `Enum` contra la convención del repo; `Numeric(12,2)` en vez de céntimos enteros; `Date` en vez de `DateTime(timezone=True)` |
> | **§2.5** `require_metodo_pago_valido` | Precondición de negocio disfrazada de autorización → devolvería 403 ante un estado de negocio |
> | **§2.8** snippet de `config.py` | `Field(...)` haría las claves obligatorias en **todos** los entornos; el `@field_validator` tiene una **referencia circular que fallaría en el import** |
> | **§3.1 / §3.5** dependencias npm | Innecesarias con Checkout por redirección; `redirectToCheckout` está obsoleto |
> | **§5.1** alta de organización | Crea el `Customer` dentro de la transacción de registro → acopla el alta de usuarios a la disponibilidad de Stripe |
> | **§5.4** cancelación | `estado='canceled', fecha_fin=hoy` **retira acceso ya pagado** y contradice el alcance (prorrateo fuera) |
> | **§7.2** procesamiento async | Se resuelve **síncrono**; ver D3 del plan |
> | **§Tests** | `test_stripe_integración_e2e.py` — identificador de módulo no ASCII |
>
> **Fuente de verdad:** [`FASE_13_PLAN_EJECUCION.md`](FASE_13_PLAN_EJECUCION.md) v2.0.
> En caso de conflicto, manda ese documento.
>
> Lo que **sigue siendo válido** de este mapa: el inventario de archivos afectados, la matriz de
> impacto por componente y la enumeración de vacíos de infraestructura.

---

## 1. RESUMEN EJECUTIVO

### Estado Actual
- ✅ Multi-tenancy por Organizacion (Fase 9)
- ✅ Seguridad JWT, autorización por roles
- ✅ Notificaciones multicanal (patrón reutilizable)
- ✅ Migraciones Alembic idempotentes
- ❌ **Cero infraestructura de facturación/suscripción**

### Lo que Fase 13 debe entregar
- Tablas de BD: `Suscripcion`, `Factura`, `EventoFacturacion`
- Backend: Servicios de suscripción, checkout, webhook handling
- Frontend: Dashboard de facturación, integración Stripe.js
- Tests: Cobertura de flujos de pago, webhook signature verification
- Docs: Guía de integración Stripe

### Esfuerzo Estimado
**~140 horas (~3.5 sprints)** — Riesgo: **CRÍTICO** (manejo de dinero, webhooks, idempotencia)

---

## 2. ARQUITECTURA BACKEND — CAMBIOS REQUERIDOS

### 2.1 Modelos ORM (Agregar a `backend/app/models.py`)

**Tabla: Suscripcion**
```
├─ id (String 36, PK)
├─ organizacion_id (FK → Organizacion, indexed, unique)
├─ plan_codigo (String 32: 'starter', 'pro', 'enterprise')
├─ estado (Enum: active | canceled | past_due | trialing)
├─ stripe_customer_id (String 50, unique, nullable)
├─ stripe_subscription_id (String 100, unique, nullable)
├─ fecha_inicio (DateTime)
├─ fecha_fin (DateTime, nullable)
├─ proxima_fecha_facturacion (DateTime)
├─ cantidad_usuarios_autorizados (SmallInt)
├─ cantidad_analisis_incluidos (Int)
├─ creado_en (DateTime, indexed)
└─ actualizado_en (DateTime)
```

**Tabla: Factura**
```
├─ id (String 36, PK)
├─ organizacion_id (FK → Organizacion, indexed)
├─ suscripcion_id (FK → Suscripcion, nullable)
├─ stripe_invoice_id (String 100, unique, indexed)
├─ numero (String 20, unique: 'INV-2025-001')
├─ estado (Enum: draft | open | paid | uncollectible | void)
├─ fecha_emision (Date)
├─ fecha_vencimiento (Date, nullable)
├─ fecha_pagada (DateTime, nullable)
├─ monto_subtotal (Numeric 12,2)
├─ monto_impuesto (Numeric 12,2)
├─ monto_total (Numeric 12,2)
├─ moneda (String 3: 'EUR', 'USD')
├─ descripcion (Text)
├─ url_pdf (String 255, nullable)
├─ creado_en (DateTime, indexed)
├─ actualizado_en (DateTime)
└─ pagado_por (String 50, nullable) # ref a Stripe payment intent
```

**Tabla: EventoFacturacion**
```
├─ id (BigInt, PK, autoincrement)
├─ organizacion_id (FK → Organizacion, indexed)
├─ tipo (Enum: plan_created | plan_changed | plan_canceled | invoice_created | invoice_paid | invoice_failed)
├─ referencia_stripe (String 100, nullable: invoice_id, subscription_id)
├─ payload_stripe (JSONB: evento completo de Stripe)
├─ quien (String 120: email del admin que disparó, o 'stripe-webhook')
├─ creado_en (DateTime, indexed)
└─ procesado (Boolean, default=False)
```

**Cambios a Organizacion**
```
Agregar columnas:
├─ stripe_customer_id (String 50, unique, nullable)
├─ plan_actual (String 32, nullable)
├─ estado_suscripcion (String 16, nullable)
└─ proxima_facturacion (DateTime, nullable)
```

### 2.2 Servicios Nuevos

**`backend/app/services/suscripcion_service.py`** (~200 líneas)
```python
def obtener_suscripcion_actual(db, org_id) → Suscripcion | None
def crear_sesion_checkout(db, org_id, plan_codigo, quien) → {session_id, checkout_url}
def cambiar_plan(db, org_id, nuevo_plan, quien) → Suscripcion
def cancelar_suscripcion(db, org_id, quien) → Suscripcion
def listar_facturas(db, org_id, limite=12) → List[Factura]
def obtener_factura(db, org_id, factura_id) → Factura | None
def sincronizar_estado_desde_stripe(org_id) → None  # Consult Stripe API
def validar_limite_usuarios(db, org_id) → {limite, actual, disponible}
def validar_limite_analisis(db, org_id) → {limite, actual, disponible}
```

**`backend/app/services/stripe_client.py`** (~150 líneas)
```python
class StripeClientWrapper:
  def __init__(self, secret_key: str)
  
  def crear_customer(email, nombre) → customer_id
  def crear_sesion_checkout(customer_id, plan, url_success, url_cancel) → session_id
  def obtener_subscription(subscription_id) → subscription_obj
  def cambiar_subscription_plan(subscription_id, nuevo_plan) → subscription_obj
  def cancelar_subscription(subscription_id) → subscription_obj
  def obtener_invoice(invoice_id) → invoice_obj
  def listar_invoices_customer(customer_id) → List[invoice_obj]
  def verificar_firma_webhook(payload_raw: bytes, signature: str) → bool
```

**`backend/app/services/webhook_service.py`** (~120 líneas)
```python
async def procesar_evento_stripe(evento_dict: dict, db) → bool
  # Despacha según evento.type:
  # - invoice.created
  # - invoice.paid
  # - invoice.payment_failed
  # - customer.subscription.created
  # - customer.subscription.updated
  # - customer.subscription.deleted
```

### 2.3 APIs Nuevas

**`backend/app/api/facturacion.py`** (~180 líneas)

| Endpoint | Método | Protección | Respuesta |
|----------|--------|-----------|----------|
| `/suscripcion` | GET | auth | `{plan, estado, proxima_facturacion, limites}` |
| `/suscripcion/cambiar-plan` | POST | propietario | `{checkout_url, session_id}` |
| `/suscripcion/cancelar` | DELETE | propietario | `{ok, mensaje, fecha_efectiva}` |
| `/facturas` | GET | auth | `[{numero, estado, fecha, monto, url_pdf}]` |
| `/facturas/{id}` | GET | auth | `{numero, estado, items[], monto_total, url_pdf}` |
| `/facturas/{id}/descargar` | GET | auth | PDF file (Content-Disposition: attachment) |

**`backend/app/api/webhooks.py`** (~100 líneas)

| Endpoint | Método | Autenticación | Procesamiento |
|----------|--------|---------------|---------------|
| `/webhooks/stripe` | POST | signature verification | Dispatch según evento.type |

Verifica: `stripe.Webhook.construct_event(body, sig_header, webhook_secret)`

### 2.4 Modificaciones a Servicios Existentes

**`backend/app/services/usuario_service.py`**
- Agregar: `crear_suscripcion_trial(db, org_id, quien)` → Trial de 14 días

**`backend/app/services/notificaciones_service.py`**
- Agregar: `notificar_factura_pagada(db, usuario, factura)`
- Agregar: `notificar_cambio_plan(db, usuario, plan_anterior, plan_nuevo)`
- Agregar: `notificar_pago_fallido(db, usuario, factura, motivo)`

**`backend/app/services/analisis_service.py`**
- Modificar: `crear_analisis()` → Antes de crear, validar `validar_limite_analisis(org_id)`
- Agregar: lógica de rechazo si se excedió límite

### 2.5 Dependencias de Autorización

Modificar `backend/app/api/deps.py`:
```python
def require_facturacion_access() → Dependency
  # Solo propietario org puede ver/cambiar suscripción

def require_metodo_pago_valido() → Dependency
  # Verificar que org tenga stripe_customer_id válido
```

### 2.6 Migraciones Alembic

**Archivo: `backend/alembic/versions/0005_facturacion_y_suscripciones.py`** (~200 líneas)

```python
def upgrade() → None:
    # 1. Crear tabla suscripcion
    op.create_table(
        'suscripcion',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organizacion_id', sa.String(36), 
                  sa.ForeignKey('organizacion.id'), nullable=False, unique=True),
        sa.Column('plan_codigo', sa.String(32), nullable=False),
        sa.Column('estado', sa.String(16), nullable=False),
        # ... campos restantes
    )
    op.create_index('ix_suscripcion_organizacion_id', 'suscripcion', ['organizacion_id'])
    
    # 2. Crear tabla factura
    op.create_table('factura', [...])
    op.create_index('ix_factura_organizacion_id', 'factura', ['organizacion_id'])
    
    # 3. Crear tabla evento_facturacion
    op.create_table('evento_facturacion', [...])
    op.create_index('ix_evento_facturacion_organizacion_id', 'evento_facturacion', ['organizacion_id'])
    
    # 4. Agregar columnas a organizacion
    op.add_column('organizacion', sa.Column('stripe_customer_id', sa.String(50), unique=True, nullable=True))
    op.add_column('organizacion', sa.Column('plan_actual', sa.String(32), nullable=True))
    # ... otras columnas

def downgrade() → None:
    # Reversible: eliminar columnas, dropear tablas
    op.drop_table('evento_facturacion')
    op.drop_table('factura')
    op.drop_table('suscripcion')
    op.drop_column('organizacion', 'stripe_customer_id')
    # ...
```

### 2.7 Tasks Celery (Nuevas)

**`backend/app/tasks/stripe_tasks.py`** (~80 líneas)

```python
@shared_task(bind=True)
def sincronizar_facturas_pendientes(self):
  # Ejecuta diariamente
  # Para cada org con suscripcion activa:
  #   - Consulta Stripe API
  #   - Crea registros locales de facturas faltantes
  #   - Dispara alertas a propietarios

@shared_task(bind=True)
def reintentar_pagos_fallidos(self):
  # Ejecuta cada 6 horas
  # Para cada factura con estado=payment_failed:
  #   - Reintenta cobro si > 3 días desde último intento
  #   - Registra intent en evento_facturacion
```

Agregar al beat schedule en `celery_app.py`:
```python
'stripe.sync-invoices': {
    'task': 'app.tasks.stripe_tasks.sincronizar_facturas_pendientes',
    'schedule': crontab(hour=0),  # 00:00 UTC
},
```

### 2.8 Configuración y Validación

**Modificar `backend/app/core/config.py`:**
```python
class Settings(BaseSettings):
    # Stripe (REQUIRED en producción)
    stripe_public_key: str = Field(..., validation_alias='STRIPE_PUBLIC_KEY')
    stripe_secret_key: str = Field(..., validation_alias='STRIPE_SECRET_KEY')
    stripe_webhook_secret: str = Field(..., validation_alias='STRIPE_WEBHOOK_SECRET')
    
    # URLs de redirección
    stripe_redirect_success_url: str
    stripe_redirect_cancel_url: str
    
    @field_validator('stripe_secret_key')
    def validate_stripe_secret(cls, v):
        if settings.seis_env == 'production' and not v.startswith('sk_live_'):
            raise ValueError('En producción, usar live keys, no test keys')
        return v
```

Modificar `_validar_seguridad_produccion()`:
```python
if SEIS_ENV == 'production':
    if not STRIPE_SECRET_KEY or not STRIPE_WEBHOOK_SECRET:
        raise ValueError('Stripe keys required en producción')
    if not STRIPE_PUBLIC_KEY.startswith(('pk_live_', 'pk_test_')):
        raise ValueError('Stripe public key inválida')
```

### 2.9 Variables de Entorno

Agregar a `.env.example`:
```env
# STRIPE — REQUERIDO en producción
STRIPE_PUBLIC_KEY=pk_test_XXXXXXX
STRIPE_SECRET_KEY=sk_test_XXXXXXX
STRIPE_WEBHOOK_SECRET=whsec_test_XXXXXXX

# URLs de redirección post-checkout
STRIPE_REDIRECT_SUCCESS_URL=https://app.seis.local/checkout/success
STRIPE_REDIRECT_CANCEL_URL=https://app.seis.local/checkout/cancel
```

### 2.10 Dependencias Python

Agregar a `backend/requirements.txt`:
```
stripe>=8.0.0,<9.0.0
```

---

## 3. ARQUITECTURA FRONTEND — CAMBIOS REQUERIDOS

### 3.1 Nuevas Dependencias NPM

```bash
npm install --save \
  @stripe/react-stripe-js@^2.0.0 \
  @stripe/stripe-js@^3.0.0
```

Agregar a `frontend/package.json`:
```json
{
  "dependencies": {
    "@stripe/react-stripe-js": "^2.0.0",
    "@stripe/stripe-js": "^3.0.0"
  }
}
```

### 3.2 Nuevas Rutas

| Ruta | Componente | Acceso | Propósito |
|------|-----------|--------|----------|
| `/suscripcion` | `FacturacionDashboard` | propietario | Dashboard de plan, cambiar plan, historial |
| `/checkout/success` | `ConfirmacionPago` | autenticado | Post-compra éxitosa |
| `/checkout/cancel` | `CancelacionCheckout` | autenticado | Usuario canceló en Stripe |

**Archivos a crear:**
- `frontend/app/(app)/suscripcion/page.tsx` (120 líneas)
- `frontend/app/(app)/checkout/success/page.tsx` (60 líneas)
- `frontend/app/(app)/checkout/cancel/page.tsx` (50 líneas)

### 3.3 Contextos Globales

**`frontend/contexts/suscripcion-context.tsx`** (~120 líneas)

```typescript
interface SuscripcionContextType {
  suscripcion: Suscripcion | null
  cargando: boolean
  errores: string[]
  limites: {
    usuarios: { limite: number, actual: number, disponible: number }
    analisis: { limite: number, actual: number, disponible: number }
  }
  cargarSuscripcion: () => Promise<void>
  crearCheckout: (plan: string) => Promise<{url: string}>
  cancelarSuscripcion: () => Promise<void>
}

export function SuscripcionProvider({children}) {
  // Implementación con TanStack Query
}
```

Agregar a `frontend/app/providers.tsx`:
```typescript
<QueryClientProvider>
  <AuthProvider>
    <SuscripcionProvider>  {/* NEW */}
      {children}
    </SuscripcionProvider>
  </AuthProvider>
</QueryClientProvider>
```

### 3.4 Componentes Nuevos

**`frontend/components/FacturacionDashboard.tsx`** (~250 líneas)
```typescript
export function FacturacionDashboard() {
  // Mostrar:
  // - Plan actual + estado
  // - Próxima fecha de facturación
  // - Límites de usuarios / análisis
  // - Botón "Cambiar Plan" (→ checkout)
  // - Botón "Cancelar Suscripción" (con confirmación)
}
```

**`frontend/components/CheckoutButton.tsx`** (~80 líneas)
```typescript
export function CheckoutButton({plan}: {plan: string}) {
  // Click → POST /api/v1/suscripcion/cambiar-plan
  // Respuesta: {checkout_url} → redirect
  // O usar Stripe.js para embedded checkout
}
```

**`frontend/components/ListadoFacturas.tsx`** (~150 líneas)
```typescript
export function ListadoFacturas() {
  // Tabla con: Número, Fecha, Estado, Monto, Link PDF
  // GET /api/v1/facturas
  // Filtros: estado, rango de fechas
}
```

**`frontend/components/ConfirmacionPago.tsx`** (~100 líneas)
```typescript
export function ConfirmacionPago() {
  // Mostrar en /checkout/success?session_id=...
  // - Verificar estado de pago en backend
  // - Mostrar recibo / número de factura
  // - Enlace a descargar PDF
}
```

### 3.5 Librerías Tipadas

**`frontend/lib/stripe.ts`** (~80 líneas)
```typescript
import { loadStripe, Stripe } from '@stripe/stripe-js'

let stripePromise: Promise<Stripe | null>

export function getStripe() {
  if (!stripePromise) {
    stripePromise = loadStripe(
      process.env.NEXT_PUBLIC_STRIPE_PUBLIC_KEY || ''
    )
  }
  return stripePromise
}

export async function redirigirACheckout(sessionId: string) {
  const stripe = await getStripe()
  if (!stripe) throw new Error('Stripe no disponible')
  const result = await stripe.redirectToCheckout({sessionId})
  if (result.error) throw new Error(result.error.message)
}
```

**`frontend/lib/types_billing.ts`** (~100 líneas) o agregar a `types.ts`:
```typescript
export interface Suscripcion {
  id: string
  organizacion_id: string
  plan_codigo: 'starter' | 'pro' | 'enterprise'
  estado: 'active' | 'canceled' | 'past_due' | 'trialing'
  stripe_subscription_id: string
  stripe_customer_id: string
  fecha_inicio: string  // ISO 8601
  fecha_fin: string | null
  proxima_fecha_facturacion: string
  cantidad_usuarios_autorizados: number
  cantidad_analisis_incluidos: number
}

export interface Factura {
  id: string
  organizacion_id: string
  numero: string
  estado: 'draft' | 'open' | 'paid' | 'uncollectible' | 'void'
  fecha_emision: string
  fecha_vencimiento: string | null
  fecha_pagada: string | null
  monto_subtotal: number
  monto_impuesto: number
  monto_total: number
  moneda: string
  url_pdf: string
  stripe_invoice_id: string
}

export interface PlanesSuscripcion {
  starter: { precio: number, usuarios: number, analisis: number }
  pro: { precio: number, usuarios: number, analisis: number }
  enterprise: { precio: number, usuarios: number, analisis: number }
}
```

### 3.6 Cliente API Tipado

Agregar a `frontend/lib/api.ts`:
```typescript
export const api = {
  // ... existing
  
  // Billing (NEW)
  suscripcion: {
    obtener: () => POST<Suscripcion>('/suscripcion'),
    cambiarPlan: (plan: string) => POST<{checkout_url: string}>('/suscripcion/cambiar-plan', {plan}),
    cancelar: () => DELETE<{ok: boolean}>('/suscripcion/cancelar'),
  },
  facturas: {
    listar: () => GET<Factura[]>('/facturas'),
    obtener: (id: string) => GET<Factura>(`/facturas/${id}`),
    descargar: (id: string) => GET_BLOB(`/facturas/${id}/descargar`),
  },
}
```

### 3.7 Hooks Personalizados

**`frontend/hooks/useSuscripcion.ts`** (~80 líneas)
```typescript
export function useSuscripcion() {
  const {data: suscripcion, isLoading} = useQuery({
    queryKey: ['billing', 'suscripcion'],
    queryFn: () => api.suscripcion.obtener(),
  })
  
  const {mutateAsync: cambiarPlan} = useMutation({
    mutationFn: (plan: string) => api.suscripcion.cambiarPlan(plan),
    onSuccess: (data) => {
      window.location.href = data.checkout_url
    },
  })
  
  return {suscripcion, isLoading, cambiarPlan}
}
```

### 3.8 Modificaciones a Páginas Existentes

**`frontend/app/(app)/equipo/page.tsx`**
- Mostrar límite de usuarios según `suscripcion.cantidad_usuarios_autorizados`
- Mostrar contador actual vs límite
- Desactivar botón "Agregar miembro" si se alcanzó límite

**`frontend/app/(app)/nueva/page.tsx`** (Asistente)
- En paso final (resumen), validar `validar_limite_analisis()`
- Si se excedería límite: mostrar alerta + botón "Actualizar plan"

**`frontend/app/(app)/layout.tsx`**
- Agregar banner de alerta si suscripción está próxima a vencer

### 3.9 Variables de Entorno Frontend

Agregar a `.env.example`:
```env
NEXT_PUBLIC_STRIPE_PUBLIC_KEY=pk_test_XXXXXXX
```

---

## 4. MATRIZ DE IMPACTO — RESUMEN POR ARCHIVO

### Backend

| Archivo | Tipo | Líneas | Cambio | Riesgo |
|---------|------|--------|--------|--------|
| `models.py` | Modify | +150 | Agregar 3 tablas, columnas a Org | Bajo |
| `suscripcion_service.py` | Create | 200 | Lógica de planes, checkout, estado | Alto |
| `stripe_client.py` | Create | 150 | Wrapper de Stripe SDK | Crítico |
| `webhook_service.py` | Create | 120 | Procesamiento de eventos de Stripe | Crítico |
| `facturacion.py` | Create | 180 | 6 endpoints de billing | Crítico |
| `webhooks.py` | Create | 100 | Endpoint de webhook + signature verify | Crítico |
| `stripe_tasks.py` | Create | 80 | Tasks de sincronización/reintento | Medio |
| `deps.py` | Modify | +20 | require_facturacion_access() | Bajo |
| `usuario_service.py` | Modify | +30 | crear_suscripcion_trial() | Bajo |
| `notificaciones_service.py` | Modify | +50 | Alertas de pago/plan | Medio |
| `analisis_service.py` | Modify | +20 | Validar límite de análisis | Medio |
| `config.py` | Modify | +40 | Stripe keys + validación | Crítico |
| `security.py` | Modify | +20 | Verificación de webhook signature | Crítico |
| `0005_facturacion.py` | Create | 200 | Migración Alembic | Crítico |
| `docker-compose.yml` | Modify | +10 | Stripe env vars | Bajo |
| `requirements.txt` | Modify | +1 | stripe>=8.0.0 | Bajo |
| **Backend TOTAL** | | **~1400** | | |

### Frontend

| Archivo | Tipo | Líneas | Cambio | Riesgo |
|---------|------|--------|--------|--------|
| `suscripcion-context.tsx` | Create | 120 | Global state de facturación | Medio |
| `stripe.ts` | Create | 80 | Cliente Stripe.js | Medio |
| `types_billing.ts` | Create | 100 | Tipos de facturación | Bajo |
| `FacturacionDashboard.tsx` | Create | 250 | Dashboard principal de suscripción | Medio |
| `CheckoutButton.tsx` | Create | 80 | Botón de checkout | Bajo |
| `ListadoFacturas.tsx` | Create | 150 | Tabla de invoices | Bajo |
| `ConfirmacionPago.tsx` | Create | 100 | Post-compra | Bajo |
| `useSuscripcion.ts` | Create | 80 | Hook personalizado | Bajo |
| `suscripcion/page.tsx` | Create | 120 | Ruta /suscripcion | Medio |
| `checkout/success/page.tsx` | Create | 60 | Ruta /checkout/success | Bajo |
| `checkout/cancel/page.tsx` | Create | 50 | Ruta /checkout/cancel | Bajo |
| `api.ts` | Modify | +60 | Endpoints de billing | Bajo |
| `types.ts` | Modify | +40 | Tipos de suscripción/factura | Bajo |
| `equipo/page.tsx` | Modify | +30 | Mostrar límite de usuarios | Bajo |
| `nueva/page.tsx` | Modify | +25 | Validar límite de análisis | Bajo |
| `providers.tsx` | Modify | +5 | Agregar SuscripcionProvider | Bajo |
| `package.json` | Modify | +2 | @stripe/* dependencies | Bajo |
| **Frontend TOTAL** | | **~1200** | | |

### Tests

| Archivo | Tipo | Tests | Cobertura |
|---------|------|-------|-----------|
| `test_suscripciones.py` | Create | 70 | CRUD, cambios de plan, cancelación |
| `test_stripe_webhooks.py` | Create | 50 | Webhook signature, eventos, idempotencia |
| `test_facturacion_api.py` | Create | 30 | Endpoints GET/POST/DELETE |
| `test_stripe_integración_e2e.py` | Create | 40 | Flujo completo checkout → webhook |
| **Tests TOTAL** | | **~190** | |

### Documentación

| Archivo | Tipo | Líneas | Cambio |
|---------|------|--------|--------|
| `STRIPE_INTEGRATION.md` | Create | 500 | Guía completa: arquitectura, flujos, testing |
| `PAYMENT_STATES.md` | Create | 200 | Máquina de estados de suscripción/factura |
| `WEBHOOK_HANDLING.md` | Create | 150 | Detalles de procesamiento de eventos |
| `.env.example` | Modify | +5 | Stripe keys |
| `MANUAL_DE_PRUEBAS.md` | Modify | +100 | Testing con Stripe test mode |
| **Docs TOTAL** | | **~950** | |

---

## 5. FLUJOS CRÍTICOS

### 5.1 Creación de Suscripción (Alta de usuario)

```
Registro nuevo usuario → usuarioService.crear_usuario()
  ├─ Crear usuario + org
  ├─ Call: suscripcionService.crear_suscripcion_trial(org_id)
  │   ├─ StripeClient.crear_customer(email, nombre)
  │   ├─ Crear registro Suscripcion (estado='trialing')
  │   └─ Registrar evento: 'suscripcion_creada'
  └─ Responder al frontend: {usuario, trial_hasta: ...}
```

### 5.2 Cambio de Plan (Propietario org)

```
Usuario propietario → Click "Cambiar Plan" → Selecciona nuevo plan
  ↓
POST /api/v1/suscripcion/cambiar-plan {plan: 'pro'}
  ├─ Verificar: require_propietario()
  ├─ Obtener suscripción actual
  ├─ Call: StripeClient.crear_sesion_checkout(
  │       customer_id=org.stripe_customer_id,
  │       plan='pro',
  │       url_success=STRIPE_REDIRECT_SUCCESS_URL,
  │       url_cancel=STRIPE_REDIRECT_CANCEL_URL)
  ├─ Responder: {checkout_url: 'https://checkout.stripe.com/...'}
  └─ Registrar evento: 'plan_change_initiated'
  ↓
Frontend: redirect(checkout_url)
  ↓
Usuario en Stripe hosted checkout → Completa pago
  ↓
Stripe: invoice.created → invoice.paid
  ↓
Webhook: POST /api/v1/webhooks/stripe {evento: invoice.paid, ...}
  ├─ Verificar firma con STRIPE_WEBHOOK_SECRET
  ├─ Procesar: webhookService.procesar_evento_stripe()
  │   ├─ Obtener org desde invoice.metadata.organizacion_id
  │   ├─ Actualizar Suscripcion.estado = 'active'
  │   ├─ Actualizar Suscripcion.proxima_fecha_facturacion
  │   ├─ Crear Factura en BD
  │   └─ Disparar notificación: 'Pago recibido'
  ├─ Registrar evento: 'invoice_paid'
  └─ Responder HTTP 200 (confirmar recepción)
  ↓
Frontend: redirect(/checkout/success)
  ├─ Mostrar: "¡Bienvenido al plan PRO!"
  ├─ GET /api/v1/suscripcion → Mostrar nuevos límites
  └─ Link a descargar factura PDF
```

### 5.3 Webhook Processing (Crítico)

```
Stripe → POST /api/v1/webhooks/stripe
  ├─ Leer headers: Stripe-Signature
  ├─ Leer body: raw JSON
  ├─ Verificar: stripe.Webhook.construct_event(body, sig, secret)
  │   └─ Si falla: responder 400 (Stripe reintentará)
  ├─ Extraer: evento.type (ej: 'invoice.paid')
  ├─ Idempotencia: ¿Ya procesé este evento.id?
  │   └─ Si sí: responder 200 (no replicar acción)
  ├─ Procesar según tipo:
  │   ├─ invoice.paid: crear/actualizar Factura, notificar
  │   ├─ invoice.payment_failed: alertar propietario
  │   ├─ customer.subscription.updated: actualizar plan
  │   └─ customer.subscription.deleted: marcar como canceled
  ├─ Registrar en evento_facturacion (para audit)
  └─ Responder 200 OK
```

### 5.4 Cancelación de Suscripción

```
Usuario propietario → Click "Cancelar Suscripción"
  ├─ Modal de confirmación: "¿Seguro? Se perderá acceso..."
  ↓
DELETE /api/v1/suscripcion/cancelar
  ├─ Verificar: require_propietario()
  ├─ Obtener suscripción
  ├─ Call: StripeClient.cancelar_subscription(stripe_sub_id)
  │   └─ Stripe devuelve: subscription.status = 'canceled'
  ├─ Actualizar en BD: Suscripcion.estado = 'canceled', fecha_fin = hoy
  ├─ Registrar evento: 'suscripcion_cancelada'
  ├─ Notificar: email a propietario ("Suscripción cancelada")
  └─ Responder: {ok: true, efectivo_desde: '2025-07-26'}
  ↓
Frontend: Mostrar "Tu suscripción ha sido cancelada"
  ├─ Última factura disponible para descargar
  └─ Opción de reactivar (→ Cambiar Plan nuevamente)
```

---

## 6. DEPENDENCIAS EXPLÍCITAS

### 6.1 Externas (Nuevas)

| Dependencia | Versión | Propósito | Entorno |
|-------------|---------|----------|---------|
| `stripe` (Python SDK) | >=8.0.0 | Acceso a Stripe API | Backend |
| `@stripe/react-stripe-js` | ^2.0.0 | React components | Frontend |
| `@stripe/stripe-js` | ^3.0.0 | Stripe JS client | Frontend |

### 6.2 Internas (Modificadas)

- `app/core/config.py` → `app/services/suscripcion_service.py`
- `app/api/deps.py` → `app/api/facturacion.py`
- `app/models.py` ← `backend/alembic/versions/0005_facturacion.py`
- `app/main.py` → `app/api/webhooks.py`
- `frontend/lib/api.ts` ← `frontend/contexts/suscripcion-context.tsx`
- `frontend/app/providers.tsx` → `frontend/components/FacturacionDashboard.tsx`

### 6.3 Prerequisitos de Fase 13

✅ **Antes de empezar, debe estar completado:**
- Fase 9 (Multi-tenancy) — proporciona `Organizacion`, rol `propietario`
- Fase 12 (Notificaciones) — proporciona patrón de notificadores, `usuario_service.crear_usuario()`

❌ **No depende de (pueden ejecutarse en paralelo):**
- Fase 10 (Alta self-service)
- Fase 11 (Infraestructura de producción)
- Fase 14 (RGPD)

---

## 7. RIESGOS Y PUNTOS DE ATENCIÓN

### 7.1 Riesgos Críticos

| Riesgo | Descripción | Mitigación |
|--------|-------------|-----------|
| **Webhook signature spoofing** | Alguien falsifica un evento de Stripe | Verificar HMAC con `STRIPE_WEBHOOK_SECRET` antes de procesar |
| **Race condition en cambio de plan** | Usuario clica 2 veces → 2 checkouts | Rate limiting + uso de `session_id` como idempotency key |
| **Procesamiento duplicado de eventos** | Webhook entregado 2 veces → duplicar factura | Guardar `evento.id` en BD, comprobar antes de procesar |
| **Sincronización estado local vs Stripe** | Stripe dice "paid" pero BD dice "open" | Stripe API es fuente de verdad; sincronizar diariamente |
| **Fuga de datos de pago** | Guardar tarjeta en servidor | **NO hacerlo.** Stripe maneja tarjetas; solo guardar `stripe_customer_id` |
| **Secreto expuesto** | `STRIPE_SECRET_KEY` en logs/error messages | Validar en config.py que sea strong; no loguear valores |

### 7.2 Riesgos Medios

| Riesgo | Descripción | Mitigación |
|--------|-------------|-----------|
| **Límites de usuario/análisis no validados** | Usuario crea análisis aunque alcanzó límite | Validar en `analisis_service.crear_analisis()` |
| **Webhook lento/offline** | Stripe reintenta webhook, se agolpan | Procesar async en task Celery, responder 202 rápido |
| **PDF de factura URL expira** | Stripe revoca URL tras 30 días | Guardar URL en BD; regenerar si está vencida |
| **Plan inexistente en Stripe** | Dropdown muestra plan que no existe en Stripe | Validación en frontend + backend; SKUs precargados |

### 7.3 Testing en Modo Test de Stripe

- Usar **test keys** (`pk_test_`, `sk_test_`) en desarrollo
- Usar **live keys** (`pk_live_`, `sk_live_`) solo en producción (config.py rechaza test keys en prod)
- Test de tarjetas: `4242 4242 4242 4242` (éxito), `4000 0000 0000 0002` (fallo)

---

## 8. CHECKLIST DE ENTREGABLES

### Backend
- [ ] Modelos ORM (Suscripcion, Factura, EventoFacturacion)
- [ ] `suscripcion_service.py` (200 líneas)
- [ ] `stripe_client.py` (150 líneas)
- [ ] `webhook_service.py` (120 líneas)
- [ ] Endpoints en `facturacion.py` (6 rutas)
- [ ] Endpoint webhook en `webhooks.py`
- [ ] Tareas Celery en `stripe_tasks.py`
- [ ] Migración Alembic 0005 (reversible)
- [ ] Variables de entorno en `config.py` + validación
- [ ] Tests: `test_suscripciones.py` (70+ tests)
- [ ] Tests: `test_stripe_webhooks.py` (50+ tests)
- [ ] Tests: `test_facturacion_api.py` (30+ tests)
- [ ] `npm run build` limpio + `pytest` sin regresión sobre la línea base vigente: **118 recogidos — 113 pasan, 2 fallan (PDF, preexistentes), 3 se omiten** (actualizado en la Fase 9.5, Bloque J; antes decía «102 verdes»)

### Frontend
- [ ] Tipos: `Suscripcion`, `Factura` (en `types.ts`)
- [ ] Cliente Stripe: `lib/stripe.ts`
- [ ] Contexto: `suscripcion-context.tsx`
- [ ] Componentes: `FacturacionDashboard`, `CheckoutButton`, `ListadoFacturas`, `ConfirmacionPago`
- [ ] Rutas: `/suscripcion`, `/checkout/success`, `/checkout/cancel`
- [ ] Hooks: `useSuscripcion()`
- [ ] Endpoints en `lib/api.ts`
- [ ] Modificaciones a `/equipo` y `/nueva` (validaciones)
- [ ] `npm run build` limpio (sin errores de tipos)

### Documentación
- [ ] `STRIPE_INTEGRATION.md` (guía completa)
- [ ] `PAYMENT_STATES.md` (máquina de estados)
- [ ] `WEBHOOK_HANDLING.md` (procesamiento de eventos)
- [ ] `.env.example` actualizado
- [ ] `MANUAL_DE_PRUEBAS.md` con section de Stripe testing

### DevOps
- [ ] `docker-compose.yml` con Stripe env vars
- [ ] `requirements.txt` con `stripe>=8.0.0`
- [ ] `.env.example` con placeholders de Stripe
- [ ] CI/CD: Verificar que tests usan mock de Stripe (no hacer llamadas reales)

---

## 9. REFERENCIAS Y ARCHIVOS CLAVE

### Backend
```
backend/
├─ app/
│  ├─ models.py (modificar: agregar Suscripcion, Factura, etc.)
│  ├─ main.py (modificar: incluir webhook router)
│  ├─ api/
│  │  ├─ facturacion.py (NEW)
│  │  ├─ webhooks.py (NEW)
│  │  ├─ deps.py (modificar: agregar require_facturacion_access)
│  │  └─ routes.py (modificar: validar límites en análisis)
│  ├─ services/
│  │  ├─ suscripcion_service.py (NEW)
│  │  ├─ stripe_client.py (NEW)
│  │  ├─ webhook_service.py (NEW)
│  │  ├─ usuario_service.py (modificar)
│  │  ├─ notificaciones_service.py (modificar)
│  │  └─ analisis_service.py (modificar)
│  ├─ core/
│  │  ├─ config.py (modificar: Stripe keys)
│  │  └─ security.py (modificar: webhook verification)
│  └─ tasks/
│     └─ stripe_tasks.py (NEW)
├─ alembic/versions/
│  └─ 0005_facturacion_y_suscripciones.py (NEW)
├─ tests/
│  ├─ test_suscripciones.py (NEW)
│  ├─ test_stripe_webhooks.py (NEW)
│  └─ test_facturacion_api.py (NEW)
├─ requirements.txt (agregar stripe>=8.0.0)
└─ .env.example (agregar Stripe keys)
```

### Frontend
```
frontend/
├─ lib/
│  ├─ api.ts (modificar: agregar endpoints de billing)
│  ├─ types.ts (modificar: agregar Suscripcion, Factura)
│  ├─ stripe.ts (NEW)
│  └─ schema.ts (modificar: validaciones de cambio de plan)
├─ contexts/
│  └─ suscripcion-context.tsx (NEW)
├─ hooks/
│  └─ useSuscripcion.ts (NEW)
├─ components/
│  ├─ FacturacionDashboard.tsx (NEW)
│  ├─ CheckoutButton.tsx (NEW)
│  ├─ ListadoFacturas.tsx (NEW)
│  └─ ConfirmacionPago.tsx (NEW)
├─ app/
│  ├─ providers.tsx (modificar: agregar SuscripcionProvider)
│  └─ (app)/
│     ├─ suscripcion/
│     │  └─ page.tsx (NEW)
│     ├─ checkout/
│     │  ├─ success/page.tsx (NEW)
│     │  └─ cancel/page.tsx (NEW)
│     ├─ equipo/page.tsx (modificar: mostrar límite)
│     └─ nueva/page.tsx (modificar: validar límite)
├─ package.json (agregar @stripe/*)
└─ .env.example (agregar NEXT_PUBLIC_STRIPE_PUBLIC_KEY)
```

### Docker y Config
```
seis/
├─ docker-compose.yml (modificar: Stripe env vars)
├─ .env.example (modificar: Stripe keys)
├─ .gitignore (verificar: .env no committed)
└─ docs/
   ├─ STRIPE_INTEGRATION.md (NEW)
   ├─ PAYMENT_STATES.md (NEW)
   ├─ WEBHOOK_HANDLING.md (NEW)
   └─ FASE_13_MAPA_IMPACTO_STRIPE.md (este archivo)
```

---

## 10. CONCLUSIÓN

Fase 13 requiere integración profunda de Stripe en **toda la aplicación**:
- **Backend:** Modelos, servicios, APIs, webhooks, tareas
- **Frontend:** Contextos, componentes, rutas, integración con Stripe.js
- **BD:** 3 tablas nuevas, columnas en Organizacion, migraciones Alembic
- **Tests:** 190+ tests nuevos para cobertura de flujos de pago

**Riesgo:** CRÍTICO (dinero, autenticación de webhooks, idempotencia)  
**Esfuerzo:** ~140 horas (~3.5 sprints)  
**Bloqueantes:** Fase 9 ✅ y Fase 12 ✅ completadas

---

**Documento generado:** 2026-07-25  
**Versión:** 1.0 (Sin código, solo especificación de impacto)
