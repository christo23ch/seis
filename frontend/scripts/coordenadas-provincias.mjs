#!/usr/bin/env node
// Genera `lib/provincias.ts`: la coordenada de referencia de cada una de las 52
// provincias (50 + Ceuta y Melilla), tomada de una fuente OFICIAL y no a mano.
//
//   cd frontend && node scripts/coordenadas-provincias.mjs
//
// Escribe `lib/provincias.ts` él mismo, a través de un temporal y un renombrado:
// si la API falla o una comprobación salta, el fichero anterior queda intacto
// (con `> lib/provincias.ts` el shell lo vaciaba ANTES de ejecutar).
//
// Fuente: geocodificador de CartoCiudad (Instituto Geográfico Nacional / CNIG,
// https://www.cartociudad.es), API pública, sin scraping. Para cada capital de
// provincia se pide su NÚCLEO DE POBLACIÓN (`type: poblacion`, el casco urbano,
// no el término municipal, que en municipios extensos cae lejos de la ciudad) y
// se toma el centroide de su mayor polígono. Coordenadas WGS84 (EPSG:4326),
// redondeadas a 4 decimales (≈ 10 m).
//
// Por qué la capital y no el centro geográfico de la provincia: un inmueble en
// subasta está mucho más a menudo en la capital o su área que en el centro
// geométrico del territorio, que a veces es un monte (Teruel, Cuenca, Lleida).
// Es solo una aproximación para el mapa: el motor no usa lat/lng.

const API = "https://www.cartociudad.es/geocoder/api/geocoder";

// Provincia (como se escribe en el formulario) → capital, código INE de la
// provincia (para descartar homónimos de otras provincias).
const PROVINCIAS = [
  ["A Coruña", "A Coruña", "15"], ["Álava", "Vitoria-Gasteiz", "01"], ["Albacete", "Albacete", "02"],
  ["Alicante", "Alicante/Alacant", "03"], ["Almería", "Almería", "04"], ["Asturias", "Oviedo", "33"],
  ["Ávila", "Ávila", "05"], ["Badajoz", "Badajoz", "06"], ["Barcelona", "Barcelona", "08"],
  ["Burgos", "Burgos", "09"], ["Cáceres", "Cáceres", "10"], ["Cádiz", "Cádiz", "11"],
  ["Cantabria", "Santander", "39"], ["Castellón", "Castelló de la Plana", "12"], ["Ceuta", "Ceuta", "51"],
  ["Ciudad Real", "Ciudad Real", "13"], ["Córdoba", "Córdoba", "14"], ["Cuenca", "Cuenca", "16"],
  ["Girona", "Girona", "17"], ["Granada", "Granada", "18"], ["Guadalajara", "Guadalajara", "19"],
  ["Gipuzkoa", "Donostia/San Sebastián", "20"], ["Huelva", "Huelva", "21"], ["Huesca", "Huesca", "22"],
  ["Illes Balears", "Palma", "07"], ["Jaén", "Jaén", "23"], ["La Rioja", "Logroño", "26"],
  ["Las Palmas", "Las Palmas de Gran Canaria", "35"], ["León", "León", "24"], ["Lleida", "Lleida", "25"],
  ["Lugo", "Lugo", "27"], ["Madrid", "Madrid", "28"], ["Málaga", "Málaga", "29"],
  ["Melilla", "Melilla", "52"], ["Murcia", "Murcia", "30"], ["Navarra", "Pamplona/Iruña", "31"],
  ["Ourense", "Ourense", "32"], ["Palencia", "Palencia", "34"], ["Pontevedra", "Pontevedra", "36"],
  ["Salamanca", "Salamanca", "37"], ["Santa Cruz de Tenerife", "Santa Cruz de Tenerife", "38"],
  ["Segovia", "Segovia", "40"], ["Sevilla", "Sevilla", "41"], ["Soria", "Soria", "42"],
  ["Tarragona", "Tarragona", "43"], ["Teruel", "Teruel", "44"], ["Toledo", "Toledo", "45"],
  ["Valencia", "València", "46"], ["Valladolid", "Valladolid", "47"], ["Bizkaia", "Bilbao", "48"],
  ["Zamora", "Zamora", "49"], ["Zaragoza", "Zaragoza", "50"],
];

const json = async (url) => {
  const r = await fetch(url, { signal: AbortSignal.timeout(20000) });
  if (!r.ok) throw new Error(`CartoCiudad respondió ${r.status} a ${url}`);
  const t = await r.text();
  return JSON.parse(t.replace(/^callback\(/, "").replace(/\)\s*$/, ""));
};

/** Para comparar nombres: sin tildes, minúsculas, cada parte de un nombre bilingüe. */
const normal = (t) => (t ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
const coincide = (a, b) => normal(a).split("/").some((x) => normal(b).split("/").includes(x));

/** Centroide (fórmula del área con signo) de un anillo [[lng, lat], …]. */
function centroide(anillo) {
  let a = 0, cx = 0, cy = 0;
  for (let i = 0; i < anillo.length - 1; i++) {
    const [x0, y0] = anillo[i], [x1, y1] = anillo[i + 1];
    const f = x0 * y1 - x1 * y0;
    a += f; cx += (x0 + x1) * f; cy += (y0 + y1) * f;
  }
  return { area: Math.abs(a / 2), lng: cx / (3 * a), lat: cy / (3 * a) };
}

/** Anillo EXTERIOR de cada polígono de un WKT MULTIPOLYGON/POLYGON. Los huecos
 * (anillos interiores) se descartan: mezclarlos con el exterior —primera versión
 * de este guion— daba centroides absurdos (Madrid en latitud 27). */
function anillosExteriores(wkt) {
  const cuerpo = wkt.trim().replace(/^(MULTI)?POLYGON\s*/i, "");
  const poligonos = /^\(\s*\(\s*\(/.test(cuerpo)
    ? cuerpo.replace(/^\(\s*/, "").replace(/\s*\)$/, "").split(/\)\s*\)\s*,\s*\(\s*\(/)
    : [cuerpo];
  return poligonos.map((p) => p.replace(/^[\s(]+/, "").split(")")[0]
    .split(",").map((par) => par.trim().split(/\s+/).map(Number)).filter((v) => v.length === 2));
}

const DENTRO_DE_ESPANA = ({ lat, lng }) => lat >= 27.5 && lat <= 43.9 && lng >= -18.3 && lng <= 4.4;

async function coordenada(capital, codigo) {
  const candidatos = await json(`${API}/candidatesJsonp?q=${encodeURIComponent(capital)}&limit=20`);
  // El NÚCLEO de la capital pedida, no el primer resultado de su provincia.
  const deLaCapital = (x) => x.provinceCode === codigo && (coincide(x.poblacion, capital) || coincide(x.muni, capital));
  let c = candidatos.find((x) => x.type === "poblacion" && deLaCapital(x));
  if (!c) {
    c = candidatos.find((x) => x.type === "Municipio" && deLaCapital(x));
    if (c) process.stderr.write(`aviso: ${capital}: sin núcleo de población, se usa el término municipal\n`);
  }
  if (!c) throw new Error(`sin candidato para ${capital} (${codigo})`);
  const r = await json(`${API}/findJsonp?id=${encodeURIComponent(c.id)}&type=${encodeURIComponent(c.type)}`);
  if (!r.geom) throw new Error(`sin geometría para ${capital}`);
  const anillos = anillosExteriores(r.geom);
  const [anillo, c0] = anillos.map((a) => [a, centroide(a)]).sort((x, y) => y[1].area - x[1].area)[0];
  // Comprobaciones: el centroide cae dentro de la caja de su propio polígono, y en España.
  const xs = anillo.map((v) => v[0]), ys = anillo.map((v) => v[1]);
  if (!(c0.lng >= Math.min(...xs) && c0.lng <= Math.max(...xs) && c0.lat >= Math.min(...ys) && c0.lat <= Math.max(...ys))
      || !DENTRO_DE_ESPANA(c0)) {
    throw new Error(`centroide fuera de su polígono o de España para ${capital}: ${c0.lat}, ${c0.lng}`);
  }
  return { lat: Number(c0.lat.toFixed(4)), lng: Number(c0.lng.toFixed(4)), tipo: c.type, id: c.id };
}

const filas = [];
for (const [provincia, capital, codigo] of PROVINCIAS) {
  const c = await coordenada(capital, codigo);
  filas.push(`  { provincia: ${JSON.stringify(provincia)}, capital: ${JSON.stringify(capital)}, codigoIne: "${codigo}", lat: ${c.lat}, lng: ${c.lng} },`);
}

const hoy = new Date().toISOString().slice(0, 10);
const salida = `/**
 * Fase 5I-E — coordenada de referencia de cada provincia: la de su CAPITAL
 * (centroide del núcleo de población), para rellenar lat/lng aproximadas cuando
 * se elige la provincia y no se conocen las del inmueble.
 *
 * Fuente: CartoCiudad (Instituto Geográfico Nacional / CNIG), geocodificador
 * público https://www.cartociudad.es — consultado el ${hoy}. WGS84 (EPSG:4326),
 * 4 decimales. FICHERO GENERADO por \`scripts/coordenadas-provincias.mjs\`: no se
 * edita a mano; se regenera con ese guion.
 *
 * Es una aproximación de la ubicación (puede haber decenas de km hasta el
 * inmueble). El motor no usa lat/lng: solo el mapa.
 */
export interface Provincia { provincia: string; capital: string; codigoIne: string; lat: number; lng: number; }

export const PROVINCIAS: readonly Provincia[] = [
${filas.join("\n")}
];
`;
const { writeFile, rename } = await import("node:fs/promises");
const destino = new URL("../lib/provincias.ts", import.meta.url);
const temporal = new URL("../lib/provincias.ts.tmp", import.meta.url);
await writeFile(temporal, salida, "utf8");
await rename(temporal, destino);
process.stderr.write(`lib/provincias.ts: ${filas.length} provincias\n`);
