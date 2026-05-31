from flask import Blueprint, request, jsonify
import requests, time, math, os, re
# Простой кэш геокодинга
_geocode_cache = {}
geo_bp = Blueprint('geo', __name__)
NOMINATIM = 'https://nominatim.openstreetmap.org/search'
OVERPASS  = 'https://overpass-api.de/api/interpreter'
HEADERS   = {'User-Agent': 'RouteAI/1.0 (educational project)'}

YANDEX_GEOCODER = 'https://geocode-maps.yandex.ru/1.x'
YANDEX_SEARCH   = 'https://search-maps.yandex.ru/v1/'

def _geocode_nominatim(location_str):
    """Старый геокодинг через Nominatim (запасной)."""
    time.sleep(1.0)
    try:
        r = requests.get(NOMINATIM, params={
            'q': location_str, 'format': 'json',
            'limit': 1, 'accept-language': 'ru',
        }, headers=HEADERS, timeout=20)
        r.encoding = 'utf-8'
        if not r.text.strip():
            return None
        data = r.json()
        if data:
            print(f"[GEO] Nominatim: {data[0].get('display_name','')[:70]}")
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        print(f"[GEO] Nominatim error: {e}")
    return None

def geocode_start(location_str):
    """Геокодинг с кэшированием."""
    cache_key = location_str.lower().strip()
    if cache_key in _geocode_cache:
        print(f"[GEO] Из кэша: '{location_str}'")
        return _geocode_cache[cache_key]
    
    # Если ввели координаты — используем их напрямую
    coord_match = re.match(r'([\d.]+)\s*[,;]\s*([\d.]+)', location_str)
    if coord_match:
        lat, lon = float(coord_match.group(1)), float(coord_match.group(2))
        if 55.0 < lat < 56.0 and 37.0 < lon < 38.0:
            print(f"[GEO] Координаты напрямую: ({lat}, {lon})")
            _geocode_cache[cache_key] = (lat, lon)
            return lat, lon
    
    result = _geocode_start_actual(location_str)
    if result:
        _geocode_cache[cache_key] = result
    return result

def _geocode_start_actual(location_str):
    """Основной геокодинг через Яндекс с fallback на Nominatim."""
    time.sleep(0.3)
    api_key = os.getenv('YANDEX_MAPS_KEY')
    
    if api_key:
        try:
            r = requests.get(YANDEX_GEOCODER, params={
                'apikey': api_key,
                'geocode': location_str,
                'format': 'json',
                'results': 1,
                'lang': 'ru_RU',
            }, timeout=10)
            data = r.json()
            members = data.get('response', {}).get('GeoObjectCollection', {}).get('featureMember', [])
            if members:
                point = members[0]['GeoObject']['Point']['pos']
                lon, lat = map(float, point.split())
                if 55.0 < lat < 56.0 and 37.0 < lon < 38.0:
                    print(f"[GEO] Яндекс: '{location_str}' → ({lat}, {lon})")
                    return lat, lon
                else:
                    print(f"[GEO] Яндекс: подозрительные координаты ({lat}, {lon}), пробуем Nominatim")
        except Exception as e:
            print(f"[GEO] Яндекс error: {e}")
    
    return _geocode_nominatim(location_str)

def _geocode_metro(station_name):
    """Геокодирует станцию метро через несколько стратегий."""
    strategies = [
        f"станция метро {station_name}, Москва",
        f"метро {station_name}, Москва",
        f"{station_name} (станция метро), Москва",
        f"{station_name} метро Москва",
    ]
    for q in strategies:
        try:
            r = requests.get(NOMINATIM, params={
                'q': q, 'format': 'json', 'limit': 3,
                'accept-language': 'ru', 'countrycodes': 'ru',
            }, headers=HEADERS, timeout=10)
            r.encoding = 'utf-8'
            if not r.text.strip():
                continue
            try:
                results = r.json()
            except Exception:
                continue
            # Ищем результат с типом station или subway
            for item in results:
                t = item.get('type', '') + item.get('class', '')
                name = item.get('display_name', '')
                if any(k in t.lower() or k in name.lower()
                       for k in ['station', 'subway', 'metro', 'метро']):
                    print(f"[GEO] Метро '{station_name}' → {name[:60]}")
                    return float(item['lat']), float(item['lon'])
            # Если не нашли по типу — берём первый результат
            if results:
                item = results[0]
                print(f"[GEO] Метро '{station_name}' (fallback) → {item.get('display_name','')[:60]}")
                return float(item['lat']), float(item['lon'])
        except Exception as e:
            print(f"[GEO] _geocode_metro error: {e}")
        time.sleep(0.3)
    return None

# ── OSM теги ──────────────────────────────────────────────────────────────
CATEGORY_TAGS = {
    'cafe':          [('amenity','cafe')],
    'restaurant':    [('amenity','restaurant')],
    'bar':           [('amenity','bar'), ('amenity','pub')],
    'fast_food':     [('amenity','fast_food')],
    'park':          [('leisure','park'), ('leisure','garden')],
    'embankment':    [('natural','water'), ('leisure','marina')],
    'forest':        [('landuse','forest'), ('leisure','nature_reserve')],
    'viewpoint':     [('tourism','viewpoint')],
    'museum':        [('tourism','museum')],
    'gallery':       [('tourism','gallery')],
    'attraction':    [('tourism','attraction'), ('historic','monument'), ('historic','memorial')],
    'entertainment': [('amenity','theatre'), ('amenity','cinema'), ('amenity','arts_centre')],
    'sport':         [('leisure','sports_centre'), ('leisure','fitness_centre')],
    'shopping':      [('shop','mall'), ('amenity','marketplace')],
    'supermarket':   [('shop','supermarket')],
    'zoo':           [('tourism','zoo')],
}
FALLBACK_TAGS = [
    ('amenity','cafe'), ('leisure','park'), ('tourism','museum'),
    ('tourism','attraction'), ('amenity','restaurant'),
]

def _make_query(lat, lon, radius_m, tag_pairs):
    parts = []
    for key, val in tag_pairs:
        parts.append(f'node["{key}"="{val}"](around:{radius_m},{lat},{lon});')
        parts.append(f'way["{key}"="{val}"](around:{radius_m},{lat},{lon});')
    return f"[out:json][timeout:20];({''.join(parts)});out center 60;"

def _parse_overpass(elements):
    results = []
    seen = set()
    for el in elements:
        tags = el.get('tags', {})
        name = tags.get('name') or tags.get('name:ru')
        if not name or name in seen or len(name) < 2:
            continue
        seen.add(name)
        if el['type'] == 'node':
            elat, elon = el.get('lat'), el.get('lon')
        else:
            c = el.get('center', {})
            elat, elon = c.get('lat'), c.get('lon')
        if not elat or not elon:
            continue
        poi_type = (tags.get('amenity') or tags.get('leisure') or
                    tags.get('tourism') or tags.get('shop') or
                    tags.get('historic') or 'place')
        results.append({
            'name': name,
            'lat': float(elat),
            'lon': float(elon),
            'type': poi_type,
            'opening_hours': tags.get('opening_hours', ''),
            'wheelchair': tags.get('wheelchair', ''),
            'website': tags.get('website', ''),
            'phone': tags.get('phone', ''),
            # Добавляем важные теги доступности
            'highway': tags.get('highway', ''),
            'surface': tags.get('surface', ''),
            'smoothness': tags.get('smoothness', ''),
        })
    return results

def _run_overpass(query):
    """Один запрос к Overpass, без retry — вызывающий сам решает."""
    try:
        r = requests.post(OVERPASS, data={'data': query},
                          timeout=25, headers=HEADERS)
        r.raise_for_status()
        return _parse_overpass(r.json().get('elements', []))
    except Exception as e:
        print(f"[GEO] Overpass error: {e}")
        return None  # None = недоступен, [] = доступен но пусто

def search_pois_yandex(lat, lon, radius_m, categories):
    """Ищет POI через Яндекс.Карты."""
    api_key = os.getenv('YANDEX_MAPS_KEY')
    if not api_key:
        return None
    
    category_map = {
        'cafe': 'кафе', 'restaurant': 'ресторан', 'bar': 'бар',
        'park': 'парк', 'museum': 'музей', 'viewpoint': 'смотровая',
        'attraction': 'достопримечательность', 'zoo': 'зоопарк',
        'entertainment': 'развлечения', 'sport': 'спорт',
        'shopping': 'торговый центр', 'supermarket': 'супермаркет',
        'fast_food': 'фастфуд', 'embankment': 'набережная',
        'gallery': 'галерея', 'forest': 'парк',
    }
    
    all_pois = []
    for cat in (categories or [])[:5]:
        query = category_map.get(cat, cat)
        try:
            r = requests.get(YANDEX_SEARCH, params={
                'apikey': api_key,
                'text': query,
                'lang': 'ru_RU',
                'll': f'{lon},{lat}',
                'spn': f'{radius_m/111000*0.5},{radius_m/111000*0.5}',
                'type': 'biz',
                'results': 15,
            }, timeout=10)
            data = r.json()
            for item in data.get('features', []):
                props = item.get('properties', {})
                geom = item.get('geometry', {})
                coords = geom.get('coordinates', [0, 0])
                name = props.get('name', '')
                if not name:
                    continue
                company_meta = props.get('CompanyMetaData', {})
                cat_list = company_meta.get('Categories', [])
                poi_type = cat_list[0]['name'] if cat_list else cat
                
                all_pois.append({
                    'name': name,
                    'lat': float(coords[1]),
                    'lon': float(coords[0]),
                    'type': poi_type,
                    'opening_hours': company_meta.get('Hours', {}).get('text', ''),
                    'wheelchair': 'yes' if 'доступн' in str(company_meta).lower() else '',
                    'phone': company_meta.get('Phones', [{}])[0].get('formatted', ''),
                    'website': company_meta.get('url', ''),
                    'surface': '',
                    'smoothness': '',
                    'highway': '',
                })
            time.sleep(0.3)
        except Exception as e:
            print(f"[GEO] Яндекс поиск '{query}': {e}")
    
    if all_pois:
        print(f"[GEO] Яндекс: {len(all_pois)} POI")
    return all_pois if all_pois else None

def search_pois(lat, lon, radius_m, categories):
    """
    Ищет POI через Overpass.
    Возвращает список мест или None если Overpass недоступен.
    """
    tag_pairs = []
    seen_tags = set()
    for cat in (categories or []):
        for pair in CATEGORY_TAGS.get(cat, []):
            if pair not in seen_tags:
                seen_tags.add(pair)
                tag_pairs.append(pair)
    for pair in FALLBACK_TAGS:
        if pair not in seen_tags:
            seen_tags.add(pair)
            tag_pairs.append(pair)

    query = _make_query(lat, lon, radius_m, tag_pairs)
    results = _run_overpass(query)

    if results is None:
        print("[GEO] Overpass недоступен — используем fallback")
        return None  # сигнал для ai.py использовать GigaChat напрямую

    print(f"[GEO] Overpass: {len(results)} POI в {radius_m}м")
    # Фильтруем по времени суток (если передано)
    daytime = categories.get('_daytime') if isinstance(categories, dict) else None
    if daytime:
        before = len(results)
        results = [p for p in results if is_place_open_at_time(p, daytime)]
        print(f"[GEO] После фильтра по времени ({daytime}): {len(results)} (было {before})")

    if len(results) < 4:
        bigger = min(radius_m * 2, 8000)
        print(f"[GEO] Расширяем до {bigger}м")
        q2 = _make_query(lat, lon, bigger, tag_pairs)
        r2 = _run_overpass(q2)
        if r2:
            results = r2
            print(f"[GEO] После расширения: {len(results)} POI")

    return results

def geocode_place_name(name, city_hint=''):
    """Геокодирует одно место через Яндекс или Nominatim."""
    time.sleep(0.3)
    
    api_key = os.getenv('YANDEX_MAPS_KEY')
    city = city_hint.split(',')[0].strip() if city_hint else ''
    query = f"{name}, {city}" if city else name
    
    # Пробуем Яндекс
    if api_key:
        try:
            r = requests.get(YANDEX_GEOCODER, params={
                'apikey': api_key,
                'geocode': query,
                'format': 'json',
                'results': 1,
                'lang': 'ru_RU',
            }, timeout=10)
            data = r.json()
            members = data.get('response', {}).get('GeoObjectCollection', {}).get('featureMember', [])
            if members:
                point = members[0]['GeoObject']['Point']['pos']
                lon, lat = map(float, point.split())
                display_name = members[0]['GeoObject'].get('name', query)
                print(f"[GEO] Яндекс ✓ '{query}' → {display_name[:50]}")
                return lat, lon
        except Exception as e:
            print(f"[GEO] Яндекс geocode_place error: {e}")
    
    # Fallback на Nominatim
    queries = []
    if city:
        queries.append(f"{name}, {city}")
        queries.append(f"{name} {city}")
    queries.append(name)
    
    for q in queries:
        try:
            r = requests.get(NOMINATIM, params={
                'q': q, 'format': 'json', 'limit': 1,
                'accept-language': 'ru', 'countrycodes': 'ru',
            }, headers=HEADERS, timeout=20)
            r.encoding = 'utf-8'
            if r.text.strip():
                data = r.json()
                if data:
                    print(f"[GEO] Nominatim ✓ '{q}' → {data[0].get('display_name','')[:50]}")
                    return float(data[0]['lat']), float(data[0]['lon'])
        except Exception as e:
            print(f"[GEO] geocode_place_name error: {e}")
        time.sleep(0.8)
    
    return None

def geocode_near(name, center_lat, center_lon, radius_km=5.0, city_hint=''):
    """Геокодирует место строго в радиусе radius_km от центра."""
    delta = radius_km / 111.0
    viewbox = (f"{center_lon-delta},{center_lat+delta},"
               f"{center_lon+delta},{center_lat-delta}")

    # Добавляем город к запросу если есть
    city = city_hint.split(',')[0].strip() if city_hint else ''
    query_with_city = f"{name}, {city}" if city else name

    # Попытка 1: с городом + bbox + bounded
    try:
        r = requests.get(NOMINATIM, params={
            'q': query_with_city, 'format': 'json', 'limit': 5,
            'accept-language': 'ru', 'countrycodes': 'ru',
            'viewbox': viewbox, 'bounded': 1,
        }, headers=HEADERS, timeout=10)
        r.encoding = 'utf-8'
        for item in r.json():
            lat, lon = float(item['lat']), float(item['lon'])
            if haversine(center_lat, center_lon, lat, lon) <= radius_km * 1000:
                print(f"[GEO] near ✓ '{name}' → {item.get('display_name','')[:50]}")
                return lat, lon
    except Exception as e:
        print(f"[GEO] geocode_near error: {e}")

    # Попытка 2: с bbox без bounded
    try:
        r = requests.get(NOMINATIM, params={
            'q': query_with_city, 'format': 'json', 'limit': 5,
            'accept-language': 'ru', 'countrycodes': 'ru',
            'viewbox': viewbox,
        }, headers=HEADERS, timeout=10)
        r.encoding = 'utf-8'
        for item in r.json():
            lat, lon = float(item['lat']), float(item['lon'])
            if haversine(center_lat, center_lon, lat, lon) <= radius_km * 1000 * 1.5:
                print(f"[GEO] near(soft) ✓ '{name}' → {item.get('display_name','')[:50]}")
                return lat, lon
    except Exception as e:
        print(f"[GEO] geocode_near soft error: {e}")
    time.sleep(0.5)

    # Попытка 3: без ограничений, проверяем расстояние
    coords = geocode_place_name(name, city_hint)
    if coords:
        if haversine(center_lat, center_lon, coords[0], coords[1]) <= radius_km * 1000 * 2:
            return coords
    return None


def find_nearest_by_category(query, center_lat, center_lon, max_dist_m, exclude_coords=None):
    """Ищет ближайшее место через Яндекс или Nominatim."""
    time.sleep(0.3)
    
    api_key = os.getenv('YANDEX_MAPS_KEY')
    
    # Пробуем Яндекс
    if api_key:
        try:
            r = requests.get(YANDEX_SEARCH, params={
                'apikey': api_key,
                'text': query,
                'lang': 'ru_RU',
                'll': f'{center_lon},{center_lat}',
                'spn': f'{max_dist_m/111000},{max_dist_m/111000}',
                'type': 'biz',
                'results': 10,
            }, timeout=10)
            data = r.json()
            candidates = []
            for item in data.get('features', []):
                props = item.get('properties', {})
                geom = item.get('geometry', {})
                coords = geom.get('coordinates', [0, 0])
                name = props.get('name', '')
                if not name:
                    continue
                lat, lon = float(coords[1]), float(coords[0])
                d = haversine(center_lat, center_lon, lat, lon)
                if d > max_dist_m:
                    continue
                if exclude_coords and any(haversine(lat, lon, e[0], e[1]) < 200 for e in exclude_coords):
                    continue
                candidates.append((d, lat, lon, name))
            
            if candidates:
                candidates.sort(key=lambda x: x[0])
                d, lat, lon, name = candidates[0]
                print(f"[GEO] Яндекс nearest '{query}' → {name} ({d/1000:.2f}км)")
                return lat, lon, name
        except Exception as e:
            print(f"[GEO] Яндекс nearest error: {e}")
    
    # Fallback на Nominatim (если Яндекса нет или он не сработал)
    delta = (max_dist_m / 1000) / 111.0
    viewbox = (f"{center_lon-delta},{center_lat+delta},{center_lon+delta},{center_lat-delta}")
    try:
        r = requests.get(NOMINATIM, params={
            'q': query, 'format': 'json', 'limit': 10,
            'accept-language': 'ru', 'countrycodes': 'ru',
            'viewbox': viewbox, 'bounded': 1,
        }, headers=HEADERS, timeout=20)
        r.encoding = 'utf-8'
        if r.text.strip():
            results = r.json()
            candidates = []
            for item in results:
                lat, lon = float(item['lat']), float(item['lon'])
                d = haversine(center_lat, center_lon, lat, lon)
                if d > max_dist_m:
                    continue
                if exclude_coords and any(haversine(lat, lon, e[0], e[1]) < 200 for e in exclude_coords):
                    continue
                name = item.get('display_name', '').split(',')[0].strip()
                if name:
                    candidates.append((d, lat, lon, name))
            
            if candidates:
                candidates.sort(key=lambda x: x[0])
                d, lat, lon, name = candidates[0]
                print(f"[GEO] Nominatim nearest '{query}' → {name} ({d/1000:.2f}км)")
                return lat, lon, name
    except Exception as e:
        print(f"[GEO] Nominatim nearest error: {e}")
    
    return None

def find_nearest_metro(lat, lon):
    """Находит ближайшую станцию метро через Nominatim."""
    try:
        r = requests.get(NOMINATIM, params={
            'q': 'станция метро',
            'format': 'json',
            'limit': 5,
            'accept-language': 'ru',
            'countrycodes': 'ru',
            'viewbox': f"{lon-0.1},{lat+0.1},{lon+0.1},{lat-0.1}",
            'bounded': 1,
        }, headers=HEADERS, timeout=10)
        r.encoding = 'utf-8'
        results = r.json()
        if results:
            best = min(results, key=lambda x: haversine(lat, lon, float(x['lat']), float(x['lon'])))
            mlat, mlon = float(best['lat']), float(best['lon'])
            name = best.get('display_name', '').split(',')[0]
            dist = haversine(lat, lon, mlat, mlon)
            print(f"[GEO] Ближайшее метро: {name} ({dist/1000:.1f}км)")
            return mlat, mlon, name
    except Exception as e:
        print(f"[GEO] find_nearest_metro error: {e}")

    # Fallback через Overpass
    try:
        query = f"[out:json][timeout:15];node[station=subway](around:3000,{lat},{lon});out 3;"
        r = requests.post(OVERPASS, data={'data': query}, timeout=20, headers=HEADERS)
        elements = r.json().get('elements', [])
        if elements:
            el = min(elements, key=lambda x: haversine(lat, lon, x['lat'], x['lon']))
            name = el.get('tags', {}).get('name', 'Метро')
            print(f"[GEO] Метро (Overpass): {name}")
            return el['lat'], el['lon'], name
    except Exception as e:
        print(f"[GEO] find_nearest_metro Overpass error: {e}")

    return None

def is_place_open_at_time(poi, daytime):
    """
    Проверяет, подходит ли место для указанного времени суток.
    Возвращает True если место уместно, False если нет.
    """
    poi_type = poi.get('type', '')
    opening = poi.get('opening_hours', '')

    # Если есть точные часы работы — не фильтруем (пользователь сам проверит)
    if opening:
        return True

    # Типы мест, которые НЕЛЬЗЯ предлагать в определённое время
    closed_at_night = {'park', 'garden', 'viewpoint', 'zoo', 'playground',
                       'sports_centre', 'fitness_centre', 'marketplace'}
    closed_in_morning = {'bar', 'pub', 'nightclub', 'theatre', 'cinema'}
    closed_in_daytime = {'nightclub'}

    if daytime == 'night':
        if poi_type in closed_at_night:
            return False
        if poi_type == 'park' and '24/7' not in (opening or ''):
            return False

    if daytime == 'morning':
        if poi_type in closed_in_morning:
            return False

    if daytime == 'day':
        if poi_type in closed_in_daytime:
            return False

    return True

def filter_accessible_pois(pois, accessibility_type):
    """
    Фильтрует POI по доступности.
    accessibility_type: 'stroller' (коляска), 'limited' (ограниченная мобильность), None (нет ограничений)
    """
    if not accessibility_type or accessibility_type == 'none':
        return pois
    
    filtered = []
    removed = []
    
    for p in pois:
        wheelchair = p.get('wheelchair', '')
        poi_type = p.get('type', '')
        
        # Места, которые точно недоступны
        if wheelchair == 'no':
            removed.append(f"{p['name']} (нет доступа)")
            continue
        
        # Типы мест, где с коляской сложно
        hard_types = {'forest', 'nature_reserve', 'viewpoint'}
        if accessibility_type in ('stroller', 'limited') and poi_type in hard_types:
            if wheelchair != 'yes':
                removed.append(f"{p['name']} (сложный рельеф)")
                continue
        
        # Лестницы и эскалаторы
        if p.get('highway') == 'steps':
            removed.append(f"{p['name']} (лестница)")
            continue
        
        # Если wheelchair=yes или limited — берём
        if wheelchair in ('yes', 'limited'):
            filtered.append(p)
        elif wheelchair == '':
            # Нет данных — берём, но предупреждаем
            filtered.append(p)
        else:
            filtered.append(p)
    
    if removed:
        print(f"[GEO] Доступность: убрано {len(removed)} мест: {', '.join(removed)}")
    
    return filtered

# ── Утилиты ───────────────────────────────────────────────────────────────
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def geocode_places(places, city_hint=''):
    """Геокодирует список мест по названиям."""
    results = []
    for place in places:
        name = place.get('name', '')
        coords = geocode_place_name(name, city_hint)
        results.append({
            'name': name,
            'description': place.get('description', ''),
            'coords': list(coords) if coords else None,
        })
        time.sleep(1.1)
    return results

def geocode_near_multiple(name, center_lat, center_lon, radius_km=5.0, city_hint='', limit=5):
    """Возвращает список ближайших мест через Яндекс или Nominatim."""
    time.sleep(0.3)
    
    api_key = os.getenv('YANDEX_MAPS_KEY')
    city = city_hint.split(',')[0].strip() if city_hint else ''
    query_with_city = f"{name}, {city}" if city else name
    all_results = []
    
    # Пробуем Яндекс
    if api_key:
        try:
            r = requests.get(YANDEX_SEARCH, params={
                'apikey': api_key,
                'text': query_with_city,
                'lang': 'ru_RU',
                'll': f'{center_lon},{center_lat}',
                'spn': f'{radius_km/111},{radius_km/111}',
                'type': 'biz',
                'results': limit,
            }, timeout=10)
            data = r.json()
            for item in data.get('features', []):
                props = item.get('properties', {})
                geom = item.get('geometry', {})
                coords = geom.get('coordinates', [0, 0])
                name_found = props.get('name', '')
                if not name_found:
                    continue
                lat, lon = float(coords[1]), float(coords[0])
                d = haversine(center_lat, center_lon, lat, lon)
                if d <= radius_km * 1000:
                    all_results.append({
                        'name': name_found,
                        'description': props.get('description', props.get('CompanyMetaData', {}).get('address', ''))[:60],
                        'coords': [lat, lon],
                        'distance': d,
                    })
            print(f"[GEO] Яндекс: {len(all_results)} вариантов для '{name}'")
        except Exception as e:
            print(f"[GEO] Яндекс search error: {e}")
    
    # Если Яндекс не дал результатов — пробуем Nominatim
    if len(all_results) < 2:
        delta = radius_km / 111.0
        viewbox = (f"{center_lon-delta},{center_lat+delta},"
                   f"{center_lon+delta},{center_lat-delta}")
        try:
            r = requests.get(NOMINATIM, params={
                'q': query_with_city, 'format': 'json', 'limit': limit,
                'accept-language': 'ru', 'countrycodes': 'ru',
                'viewbox': viewbox, 'bounded': 1,
            }, headers=HEADERS, timeout=20)
            r.encoding = 'utf-8'
            if r.text.strip():
                for item in r.json():
                    lat, lon = float(item['lat']), float(item['lon'])
                    d = haversine(center_lat, center_lon, lat, lon)
                    if d <= radius_km * 1000:
                        all_results.append({
                            'name': item.get('display_name', '').split(',')[0].strip(),
                            'description': item.get('display_name', '')[:60],
                            'coords': [lat, lon],
                            'distance': d,
                        })
        except Exception as e:
            print(f"[GEO] Nominatim search error: {e}")
    
    # Сортируем и убираем дубли
    all_results.sort(key=lambda x: x['distance'])
    seen = set()
    unique = []
    for r in all_results:
        key = (round(r['coords'][0], 4), round(r['coords'][1], 4))
        if key not in seen:
            seen.add(key)
            unique.append(r)
    
    print(f"[GEO] Найдено {len(unique)} вариантов для '{name}'")
    return unique

OSRM_WALK = 'http://router.project-osrm.org/route/v1/walking/'
OSRM_BIKE = 'http://router.project-osrm.org/route/v1/cycling/'

def build_route_osrm(points, transport='walk'):
    """Строит реальный маршрут через OSRM по дорогам и тропинкам."""
    if len(points) < 2:
        return None
    
    base_url = OSRM_BIKE if transport == 'bike' else OSRM_WALK
    coords = ';'.join(f"{p['lon']},{p['lat']}" for p in points)
    
    try:
        r = requests.get(f"{base_url}{coords}", params={
            'overview': 'full',
            'geometries': 'geojson',
            'steps': 'false',
        }, timeout=15)
        data = r.json()
        if data.get('code') == 'Ok':
            route = data['routes'][0]
            print(f"[OSRM] Маршрут построен: {route['distance']/1000:.2f}км, {route['duration']/60:.0f}мин")
            return {
                'geometry': route['geometry'],
                'distance': route['distance'],
                'duration': route['duration'],
            }
    except Exception as e:
        print(f"[OSRM] Error: {e}")
    return None

@geo_bp.post('/geocode')
def geocode_endpoint():
    data = request.json
    if not data or not data.get('places'):
        return jsonify(error='Не переданы места для геокодинга'), 400
    
    near_lat = data.get('near_lat')
    near_lon = data.get('near_lon')
    radius_km = data.get('radius_km', 5.0)
    limit = data.get('limit', 3)  # Сколько результатов вернуть
    
    results = []
    for place in data['places']:
        name = place.get('name', '')
        
        if near_lat and near_lon:
            # Ищем несколько вариантов поблизости
            coords_list = geocode_near_multiple(name, near_lat, near_lon, radius_km, data.get('city', ''), limit)
            if not coords_list:
                # Fallback
                coords = geocode_place_name(name, data.get('city', ''))
                coords_list = [{'coords': list(coords), 'name': name}] if coords else []
            
            for item in coords_list:
                results.append({
                    'name': item.get('name', name),
                    'description': item.get('description', ''),
                    'coords': item['coords'],
                })
        else:
            coords = geocode_place_name(name, data.get('city', ''))
            results.append({
                'name': name,
                'description': place.get('description', ''),
                'coords': list(coords) if coords else None,
            })
        
        time.sleep(1.1)
    
    return jsonify(results)
