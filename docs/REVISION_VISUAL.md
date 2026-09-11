# SEIS — Revisión visual del frontend

Procedimiento para **ver** el resultado de un cambio de interfaz en vez de suponerlo. Funciona
dentro del sandbox web, sin máquina local: está verificado ejecutándolo.

**Regla:** toda fase con trabajo de frontend termina adjuntando capturas del **antes** y el
**después** de las pantallas que toca. Sin eso, la revisión de diseño se hace a ciegas — y una
revisión a ciegas es la que produjo los nueve tamaños de fuente distintos que documenta
`docs/HERRAMIENTAS.md`.

---

## 1 · Uso

```bash
# 1. Compilar y levantar (una vez por sesión)
cd frontend && npm ci && npm run build && npm run start &

# 2. Capturar el estado ACTUAL, antes de tocar nada
node scripts/capturar.mjs antes

# 3. …hacer los cambios de interfaz…

# 4. Recompilar, relanzar y capturar el DESPUÉS
npm run build && npm run start &
node scripts/capturar.mjs despues
```

> **El script vive en `frontend/scripts/`, y no es una preferencia de orden.** Estuvo en
> `scripts/` en la raíz desde que se escribió este procedimiento y **ahí no podía funcionar**:
> ESM resuelve los `import` desde el directorio **del fichero**, no desde donde se lanza el
> comando, y `playwright` está en `frontend/node_modules`. Ejecutado tal y como lo documentaba
> este mismo apartado, fallaba con `ERR_MODULE_NOT_FOUND` antes de abrir el navegador. Es la
> tercera vez que el proyecto tropieza con esto —`frontend/e2e/alta-real.mjs` se movió por la
> misma razón—, y encaja con el punto 6 del [[ADR-0014]]: **la herramienta de verificación
> estaba rota, no lo verificado.** Comprobado ejecutándolo, no razonándolo.

Las imágenes quedan en `capturas/antes/` y `capturas/despues/`, una por pantalla y anchura.
**No se versionan** (están en `.gitignore`): se adjuntan al PR, que es donde se revisan.

## 2 · Qué se captura

Cada pantalla en dos anchuras, porque el 100 % de los defectos de densidad aparecen en una de las
dos: **1440 px** (escritorio, la referencia) y **390 px** (móvil, iPhone estándar).

Las rutas privadas exigen sesión. El script inicia sesión si se le dan credenciales:

```bash
SEIS_EMAIL=admin@seis.local SEIS_PASSWORD=… node scripts/capturar.mjs antes
```

Sin credenciales captura solo las públicas (`/login`, `/registro`, `/recuperar`, `/resetear`,
`/verificar`), que ya bastan para la mayor parte del trabajo de sistema de diseño.

## 3 · Detalles que cuestan una tarde si no se saben

- **El Chromium del sandbox y el que espera `playwright` no coinciden.** El instalado es la build
  `1194`; una `playwright` recién bajada de npm puede pedir otra y fallar con
  «Executable doesn't exist». El script pasa `executablePath` explícito para evitarlo. Si cambia
  la build, se actualiza esa constante — es la única línea que hay que tocar.
- **Hace falta `npm run build` antes de `npm run start`**: `start` sirve lo compilado, no el
  código fuente. Capturar sin recompilar produce el error más caro de todos: captura idéntica y
  conclusión equivocada de que el cambio no hizo nada.
- **El backend no tiene por qué estar arriba.** Las pantallas renderizan igual; solo fallan sus
  llamadas a la API. Para el trabajo de diseño puro es suficiente, y ahorra levantar la pila.
- **`networkidle` se queda colgado** si hay sondeos periódicos. El script usa `domcontentloaded`
  más una espera corta.

## 4 · Qué mirar en las capturas

No basta con adjuntarlas: hay que decir qué se mira. El mínimo, derivado de los defectos ya
medidos en `docs/HERRAMIENTAS.md`:

1. **Densidad.** ¿Cuánta superficie está vacía? En el login actual, cerca del 70 % del panel
   derecho. Un producto de análisis debe sentirse denso y ordenado.
2. **Alineación de cifras.** Toda columna de números comparables debe usar `font-cifra` y
   alinearse a la derecha. Es lo que más delata a un producto financiero improvisado.
3. **Foco visible.** Tabular por la pantalla y comprobar que el foco se ve en cada control.
4. **Móvil de verdad.** Que a 390 px no aparezca desplazamiento horizontal ni texto por debajo de
   12 px.

## 5 · Por qué esto existe

Este flujo salió de una comprobación concreta: se levantó el frontend en el sandbox y se
fotografió el login a 1440×900 y 390×844 con Playwright. De esas capturas salieron cuatro
defectos que ninguna lectura del código había detectado, entre ellos que el panel derecho estaba
vacío en un 70 % y que la tipografía de marca era una fuente del sistema.

Es decir: **el flujo ya demostró que encuentra cosas que revisar el código no encuentra.** Por eso
pasa de anécdota a procedimiento.
