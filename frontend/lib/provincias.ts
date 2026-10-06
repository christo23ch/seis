/**
 * Fase 5I-E — coordenada de referencia de cada provincia: la de su CAPITAL
 * (centroide del núcleo de población), para rellenar lat/lng aproximadas cuando
 * se elige la provincia y no se conocen las del inmueble.
 *
 * Fuente: CartoCiudad (Instituto Geográfico Nacional / CNIG), geocodificador
 * público https://www.cartociudad.es — consultado el 2026-10-06. WGS84 (EPSG:4326),
 * 4 decimales. FICHERO GENERADO por `scripts/coordenadas-provincias.mjs`: no se
 * edita a mano; se regenera con ese guion.
 *
 * Es una aproximación de la ubicación (puede haber decenas de km hasta el
 * inmueble). El motor no usa lat/lng: solo el mapa.
 */
export interface Provincia { provincia: string; capital: string; codigoIne: string; lat: number; lng: number; }

export const PROVINCIAS: readonly Provincia[] = [
  { provincia: "A Coruña", capital: "A Coruña", codigoIne: "15", lat: 43.364, lng: -8.4047 },
  { provincia: "Álava", capital: "Vitoria-Gasteiz", codigoIne: "01", lat: 42.8483, lng: -2.6791 },
  { provincia: "Albacete", capital: "Albacete", codigoIne: "02", lat: 38.9909, lng: -1.8614 },
  { provincia: "Alicante", capital: "Alicante/Alacant", codigoIne: "03", lat: 38.3588, lng: -0.4761 },
  { provincia: "Almería", capital: "Almería", codigoIne: "04", lat: 36.8431, lng: -2.4502 },
  { provincia: "Asturias", capital: "Oviedo", codigoIne: "33", lat: 43.3637, lng: -5.8512 },
  { provincia: "Ávila", capital: "Ávila", codigoIne: "05", lat: 40.656, lng: -4.6854 },
  { provincia: "Badajoz", capital: "Badajoz", codigoIne: "06", lat: 38.8713, lng: -6.9703 },
  { provincia: "Barcelona", capital: "Barcelona", codigoIne: "08", lat: 41.3947, lng: 2.1596 },
  { provincia: "Burgos", capital: "Burgos", codigoIne: "09", lat: 42.353, lng: -3.7006 },
  { provincia: "Cáceres", capital: "Cáceres", codigoIne: "10", lat: 39.4748, lng: -6.3738 },
  { provincia: "Cádiz", capital: "Cádiz", codigoIne: "11", lat: 36.5178, lng: -6.2803 },
  { provincia: "Cantabria", capital: "Santander", codigoIne: "39", lat: 43.4596, lng: -3.8198 },
  { provincia: "Castellón", capital: "Castelló de la Plana", codigoIne: "12", lat: 39.9851, lng: -0.0505 },
  { provincia: "Ceuta", capital: "Ceuta", codigoIne: "51", lat: 35.89, lng: -5.3263 },
  { provincia: "Ciudad Real", capital: "Ciudad Real", codigoIne: "13", lat: 38.9832, lng: -3.9279 },
  { provincia: "Córdoba", capital: "Córdoba", codigoIne: "14", lat: 37.895, lng: -4.7867 },
  { provincia: "Cuenca", capital: "Cuenca", codigoIne: "16", lat: 40.0626, lng: -2.1355 },
  { provincia: "Girona", capital: "Girona", codigoIne: "17", lat: 41.9728, lng: 2.8196 },
  { provincia: "Granada", capital: "Granada", codigoIne: "18", lat: 37.1821, lng: -3.6061 },
  { provincia: "Guadalajara", capital: "Guadalajara", codigoIne: "19", lat: 40.6372, lng: -3.1724 },
  { provincia: "Gipuzkoa", capital: "Donostia/San Sebastián", codigoIne: "20", lat: 43.3099, lng: -1.9755 },
  { provincia: "Huelva", capital: "Huelva", codigoIne: "21", lat: 37.2595, lng: -6.9397 },
  { provincia: "Huesca", capital: "Huesca", codigoIne: "22", lat: 42.1377, lng: -0.4072 },
  { provincia: "Illes Balears", capital: "Palma", codigoIne: "07", lat: 39.5754, lng: 2.651 },
  { provincia: "Jaén", capital: "Jaén", codigoIne: "23", lat: 37.7794, lng: -3.79 },
  { provincia: "La Rioja", capital: "Logroño", codigoIne: "26", lat: 42.4612, lng: -2.4502 },
  { provincia: "Las Palmas", capital: "Las Palmas de Gran Canaria", codigoIne: "35", lat: 28.1178, lng: -15.4317 },
  { provincia: "León", capital: "León", codigoIne: "24", lat: 42.5991, lng: -5.5727 },
  { provincia: "Lleida", capital: "Lleida", codigoIne: "25", lat: 41.6235, lng: 0.6164 },
  { provincia: "Lugo", capital: "Lugo", codigoIne: "27", lat: 43.0209, lng: -7.5607 },
  { provincia: "Madrid", capital: "Madrid", codigoIne: "28", lat: 40.4249, lng: -3.6645 },
  { provincia: "Málaga", capital: "Málaga", codigoIne: "29", lat: 36.7194, lng: -4.4408 },
  { provincia: "Melilla", capital: "Melilla", codigoIne: "52", lat: 35.2875, lng: -2.9483 },
  { provincia: "Murcia", capital: "Murcia", codigoIne: "30", lat: 37.9886, lng: -1.1365 },
  { provincia: "Navarra", capital: "Pamplona/Iruña", codigoIne: "31", lat: 42.8141, lng: -1.6511 },
  { provincia: "Ourense", capital: "Ourense", codigoIne: "32", lat: 42.3333, lng: -7.862 },
  { provincia: "Palencia", capital: "Palencia", codigoIne: "34", lat: 42.0065, lng: -4.526 },
  { provincia: "Pontevedra", capital: "Pontevedra", codigoIne: "36", lat: 42.4293, lng: -8.6436 },
  { provincia: "Salamanca", capital: "Salamanca", codigoIne: "37", lat: 40.9629, lng: -5.6679 },
  { provincia: "Santa Cruz de Tenerife", capital: "Santa Cruz de Tenerife", codigoIne: "38", lat: 28.4623, lng: -16.2667 },
  { provincia: "Segovia", capital: "Segovia", codigoIne: "40", lat: 40.9412, lng: -4.1106 },
  { provincia: "Sevilla", capital: "Sevilla", codigoIne: "41", lat: 37.3837, lng: -5.9685 },
  { provincia: "Soria", capital: "Soria", codigoIne: "42", lat: 41.7654, lng: -2.4751 },
  { provincia: "Tarragona", capital: "Tarragona", codigoIne: "43", lat: 41.1087, lng: 1.2312 },
  { provincia: "Teruel", capital: "Teruel", codigoIne: "44", lat: 40.3416, lng: -1.1048 },
  { provincia: "Toledo", capital: "Toledo", codigoIne: "45", lat: 39.8634, lng: -4.0488 },
  { provincia: "Valencia", capital: "València", codigoIne: "46", lat: 39.4648, lng: -0.3648 },
  { provincia: "Valladolid", capital: "Valladolid", codigoIne: "47", lat: 41.6399, lng: -4.7274 },
  { provincia: "Bizkaia", capital: "Bilbao", codigoIne: "48", lat: 43.2603, lng: -2.9324 },
  { provincia: "Zamora", capital: "Zamora", codigoIne: "49", lat: 41.5135, lng: -5.7443 },
  { provincia: "Zaragoza", capital: "Zaragoza", codigoIne: "50", lat: 41.6484, lng: -0.8969 },
];
