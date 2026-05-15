// ===== MAP MODULE =====
// Яндекс.Карты API (ymaps) + OSRM для реальной геометрии маршрута по улицам

let mainMap = null;
let resultMap = null;

const EXAMPLE_POINTS = [
  { name: 'Красная площадь',    coords: [55.7539, 37.6208] },
  { name: 'Парк Зарядье',       coords: [55.7510, 37.6285] },
  { name: 'Крымская набережная',coords: [55.7340, 37.6010] },
  { name: 'Парк Горького',      coords: [55.7298, 37.6010] },
  { name: 'Воробьёвы горы',     coords: [55.7100, 37.5430] },
];

// ── Загрузка Яндекс.Карт ──────────────────────────────────────────────────
function loadYandexMaps(callback) {
  if (window.ymaps) { ymaps.ready(callback); return; }
  const script = document.createElement('script');
  // TODO: вставить свой API-ключ
  script.src = 'https://api-maps.yandex.ru/2.1/?apikey=YOUR_YANDEX_MAPS_KEY&lang=ru_RU';
  script.onload = () => ymaps.ready(callback);
  document.head.appendChild(script);
}

// ── OSRM: получить реальную геометрию маршрута по улицам ─────────────────
// profile: 'foot' | 'bike' | 'driving'
async function fetchOsrmRoute(points, profile = 'foot') {
  // OSRM ожидает координаты в формате lon,lat
  const coordStr = points.map(p => `${p.coords[1]},${p.coords[0]}`).join(';');

  // Публичные серверы OSRM по профилям:
  // foot → routing.openstreetmap.de (пешеходный)
  // bike → routing.openstreetmap.de (велосипедный)
  // driving → router.project-osrm.org
  const baseUrl = profile === 'foot'
    ? `https://routing.openstreetmap.de/routed-foot/route/v1/foot/${coordStr}`
    : profile === 'bike'
    ? `https://routing.openstreetmap.de/routed-bike/route/v1/bike/${coordStr}`
    : `https://router.project-osrm.org/route/v1/driving/${coordStr}`;

  const url = `${baseUrl}?overview=full&geometries=geojson`;

  const res = await fetch(url);
  const data = await res.json();

  if (data.code !== 'Ok') throw new Error('OSRM не смог построить маршрут');
  return data.routes[0].geometry; // GeoJSON LineString
}

// ── Конвертация GeoJSON координат [lon, lat] → ymaps [lat, lon] ──────────
function geojsonToYmaps(geometry) {
  return geometry.coordinates.map(([lon, lat]) => [lat, lon]);
}

// ── Нарисовать маршрут на карте ───────────────────────────────────────────
async function drawRoute(map, points, profile = 'foot') {
  map.geoObjects.removeAll();

  // Метки точек
  points.forEach((point, i) => {
    const placemark = new ymaps.Placemark(point.coords, {
      balloonContent: `<strong>${point.name}</strong>`,
      iconContent: i + 1,
    }, {
      preset: 'islands#blueStretchyIcon',
    });
    map.geoObjects.add(placemark);
  });

  // Запрашиваем реальный маршрут по улицам
  try {
    const geometry = await fetchOsrmRoute(points, profile);
    const routeCoords = geojsonToYmaps(geometry);

    const polyline = new ymaps.Polyline(routeCoords, {}, {
      strokeColor: '#4F6EF7',
      strokeWidth: 5,
      strokeOpacity: 0.9,
    });
    map.geoObjects.add(polyline);
  } catch (e) {
    // Fallback: прямые линии если OSRM недоступен
    console.warn('OSRM недоступен, рисуем прямые:', e);
    const fallback = new ymaps.Polyline(points.map(p => p.coords), {}, {
      strokeColor: '#4F6EF7',
      strokeWidth: 4,
      strokeOpacity: 0.6,
      strokeStyle: 'dash',
    });
    map.geoObjects.add(fallback);
  }

  // Подогнать карту под маршрут
  map.setBounds(map.geoObjects.getBounds(), { checkZoomRange: true, zoomMargin: 50 });
}

// ── Инициализация главной карты ───────────────────────────────────────────
function initMainMap() {
  if (mainMap) return;
  loadYandexMaps(() => {
    mainMap = new ymaps.Map('main-map', {
      center: [55.7522, 37.6156],
      zoom: 12,
      controls: ['zoomControl', 'fullscreenControl'],
    });
    drawRoute(mainMap, EXAMPLE_POINTS, 'foot');
  });
}

// ── Инициализация карты результата ────────────────────────────────────────
function initResultMap(points, transport) {
  const profile = transport === 'bike' ? 'bike' : 'foot';
  loadYandexMaps(() => {
    if (resultMap) { resultMap.destroy(); resultMap = null; }
    resultMap = new ymaps.Map('result-map', {
      center: points[0].coords,
      zoom: 13,
      controls: ['zoomControl', 'fullscreenControl'],
    });
    drawRoute(resultMap, points, profile);
  });
}

function onShowHome() {
  setTimeout(initMainMap, 100);
}
