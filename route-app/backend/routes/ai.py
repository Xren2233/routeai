from flask import Blueprint, request, jsonify
import requests, os, json, uuid, re, math, time
import urllib3
from routes.geo import geocode_start, search_pois, is_place_open_at_time
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ai_bp = Blueprint('ai', __name__)
GIGACHAT_AUTH_URL = 'https://ngw.devices.sberbank.ru:9443/api/v2/oauth'
GIGACHAT_API_URL  = 'https://gigachat.devices.sberbank.ru/api/v1/chat/completions'
YANDEX_GPT_URL    = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'


# ── YandexGPT ─────────────────────────────────────────────────────────────

def call_yandexgpt(prompt):
    api_key  = os.getenv('YANDEX_GPT_KEY')
    folder   = os.getenv('YANDEX_FOLDER_ID')
    if not api_key or not folder:
        raise ValueError('YANDEX_GPT_KEY или YANDEX_FOLDER_ID не заданы')
    r = requests.post(YANDEX_GPT_URL,
        headers={'Authorization': f'Api-Key {api_key}',
                 'Content-Type': 'application/json'},
        json={'modelUri': f'gpt://{folder}/yandexgpt-lite',
              'completionOptions': {'stream': False, 'temperature': 0.5, 'maxTokens': 1500},
              'messages': [{'role': 'user', 'text': prompt}]},
        timeout=30)
    r.raise_for_status()
    return r.json()['result']['alternatives'][0]['message']['text']


def get_gigachat_token():
    creds = os.getenv('GIGACHAT_CREDENTIALS')
    r = requests.post(GIGACHAT_AUTH_URL,
        headers={'Authorization': f'Basic {creds}', 'RqUID': str(uuid.uuid4()),
                 'Content-Type': 'application/x-www-form-urlencoded'},
        data={'scope': 'GIGACHAT_API_PERS'}, verify=False, timeout=15)
    r.raise_for_status()
    return r.json()['access_token']


def call_gigachat(prompt):
    token = get_gigachat_token()
    r = requests.post(GIGACHAT_API_URL,
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        json={'model': 'GigaChat', 'messages': [{'role': 'user', 'content': prompt}],
              'temperature': 0.5, 'max_tokens': 1500},
        verify=False, timeout=30)
    r.raise_for_status()
    return r.json()['choices'][0]['message']['content']


def call_ai(prompt):
    """Пробует YandexGPT если ключ задан, иначе GigaChat."""
    yandex_key = os.getenv('YANDEX_GPT_KEY', '').strip()
    if yandex_key:
        try:
            result = call_yandexgpt(prompt)
            print("[AI] Использован YandexGPT")
            return result
        except Exception as e:
            print(f"[AI] YandexGPT недоступен: {e}, пробуем GigaChat")
    return call_gigachat(prompt)


def parse_json_response(content):
    content = re.sub(r'```json\s*', '', content)
    content = re.sub(r'```\s*', '', content).strip()

    # Попытка 1: прямой парсинг
    try:
        return json.loads(content)
    except Exception:
        pass

    # Попытка 2: вытащить JSON объект
    m = re.search(r'\{[\s\S]*\}', content)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass

    # Попытка 3: JSON обрезан — закрываем незакрытые скобки
    fixed = content.rstrip().rstrip(',')
    # Считаем незакрытые [ и {
    open_sq = fixed.count('[') - fixed.count(']')
    open_cu = fixed.count('{') - fixed.count('}')
    fixed += ']' * max(open_sq, 0) + '}' * max(open_cu, 0)
    try:
        return json.loads(fixed)
    except Exception:
        pass

    # Попытка 4: вытащить все полные объекты регуляркой
    places = re.findall(
        r'\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"description"\s*:\s*"([^"]+)"\s*\}',
        content
    )
    if places:
        return {'places': [{'name': n, 'description': d} for n, d in places]}

    raise ValueError(f'Bad JSON: {content[:200]}')


INTEREST_TYPES = {
    'cafe': ['cafe'], 'restaurant': ['restaurant'], 'bar': ['bar', 'pub'],
    'fast_food': ['fast_food'], 'park': ['park', 'garden'],
    'embankment': ['water', 'marina'], 'forest': ['forest', 'nature_reserve'],
    'viewpoint': ['viewpoint'], 'museum': ['museum'], 'gallery': ['gallery'],
    'attraction': ['attraction', 'monument', 'memorial'],
    'entertainment': ['theatre', 'cinema', 'arts_centre'],
    'sport': ['sports_centre', 'fitness_centre'],
    'shopping': ['mall', 'marketplace'], 'supermarket': ['supermarket'], 'zoo': ['zoo'],
}
DEFAULT_TYPES = ['park', 'cafe', 'attraction', 'museum']
CAT_LABELS = {
    'cafe': 'кафе', 'restaurant': 'ресторан', 'bar': 'бар', 'fast_food': 'уличная еда',
    'park': 'парк', 'embankment': 'набережная', 'forest': 'лесопарк',
    'viewpoint': 'смотровая', 'museum': 'музей', 'gallery': 'галерея',
    'attraction': 'достопримечательность', 'entertainment': 'развлечения',
    'sport': 'спорт', 'shopping': 'шопинг', 'supermarket': 'магазин', 'zoo': 'зоопарк',
}


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def score_poi(poi, wanted):
    t = poi.get('type', '')
    if t in wanted:
        return 2
    return 1 if any(w in t or t in w for w in wanted) else 0


def get_target_km(data):
    dist = data.get('distance', '')
    if dist:
        try:
            parts = str(dist).split('-')
            return sum(float(p) for p in parts) / len(parts)
        except Exception:
            pass
    dur = data.get('duration')
    if dur:
        try:
            speed = 4 if data.get('transport') != 'bike' else 12
            return float(dur) * speed
        except Exception:
            pass
    return 4.0


def calc_radius(data):
    km = get_target_km(data)
    return max(1000, min(int(km * 500), 5000))


def build_meta(data, actual_m=None):
    t = {'walk': 'Пешком', 'bike': 'Велосипед', 'mixed': 'Смешанный'}
    transport = data.get('transport', 'walk')
    
    if actual_m and actual_m > 0:
        km_str = f"{actual_m/1000:.1f} км"
        
        # Вычисляем реальное время
        if transport == 'bike':
            speed_kmh = 12  # средняя скорость велосипеда
        elif transport == 'mixed':
            speed_kmh = 8
        else:
            speed_kmh = 4  # средняя скорость пешехода
        
        # Учитываем интенсивность
        intensity = data.get('intensity', 'chill')
        if intensity == 'sport':
            speed_kmh *= 1.5
        elif intensity == 'active':
            speed_kmh *= 1.2
        
        # Добавляем время на остановки (по 10 мин на точку)
        stops_minutes = data.get('_points_count', 3) * 10 / 60  # в часах
        
        hours = actual_m / 1000 / speed_kmh + stops_minutes
        hours_str = f"{hours:.1f} ч"
    else:
        km_str = f"{data.get('distance','3-5')} км"
        hours_str = f"{data.get('duration',2)} ч"
    
    return f"{hours_str} · {km_str} · {t.get(transport,'Пешком')}"


def select_route_points(pois, slat, slon, wanted, target_km, interests=None):
    """
    Алгоритм выбора точек маршрута:
    1. По одной точке на каждую выбранную категорию (не повторяем)
    2. Если км не набрано — добавляем бонусные комфортные точки по пути (парки, скверы)
    3. Не возвращаемся в уже посещённые зоны (радиус 300м)
    """
    if not pois:
        return [], 0.0

    target_m   = target_km * 1000
    tolerance  = 1000
    COMFORT    = {'park', 'garden', 'nature_reserve', 'viewpoint', 'square'}

    # Разбиваем POI по типам
    by_type = {}
    for p in pois:
        t = p.get('type', 'other')
        by_type.setdefault(t, []).append(p)

    selected   = []
    used_ids   = set()
    used_zones = []   # список (lat, lon) уже посещённых мест — не ходим рядом
    cur_lat, cur_lon, total = slat, slon, 0.0

    def too_close_to_visited(lat, lon):
        return any(haversine(lat, lon, z[0], z[1]) < 300 for z in used_zones)

    def best_in_type(type_key, cur_lat, cur_lon, remaining):
        candidates = [p for p in by_type.get(type_key, [])
                      if id(p) not in used_ids]
        valid = [(haversine(cur_lat, cur_lon, p['lat'], p['lon']), p)
                 for p in candidates
                 if haversine(cur_lat, cur_lon, p['lat'], p['lon']) <= remaining + tolerance]
        if not valid:
            return None, 0
        valid.sort(key=lambda x: x[0])
        return valid[0][1], valid[0][0]

    # Шаг 1: по одной точке на каждый нужный тип
    # Сортируем типы по близости первой доступной точки
    type_order = []
    for t in set(wanted):
        best, d = best_in_type(t, cur_lat, cur_lon, target_m - total)
        if best:
            type_order.append((d, t))
    type_order.sort(key=lambda x: x[0])

    for _, t in type_order:
        remaining = target_m - total
        if remaining <= 0:
            break
        poi, dist = best_in_type(t, cur_lat, cur_lon, remaining)
        if not poi:
            continue
        used_ids.add(id(poi))
        used_zones.append((poi['lat'], poi['lon']))
        selected.append(poi)
        total += dist
        cur_lat, cur_lon = poi['lat'], poi['lon']
        print(f"[ROUTE] [{t}] +{dist/1000:.2f}км {poi['name']} | {total/1000:.2f}/{target_km}км")

    # Шаг 2: если км не набрано — добавляем комфортные точки по пути
    if total < target_m - tolerance:
        comfort_pois = [p for p in pois
                        if p.get('type') in COMFORT
                        and id(p) not in used_ids
                        and not too_close_to_visited(p['lat'], p['lon'])]
        for _ in range(5):
            remaining = target_m - total
            if remaining <= tolerance:
                break
            valid = [(haversine(cur_lat, cur_lon, p['lat'], p['lon']), p)
                     for p in comfort_pois
                     if id(p) not in used_ids
                     and haversine(cur_lat, cur_lon, p['lat'], p['lon']) <= remaining + tolerance
                     and not too_close_to_visited(p['lat'], p['lon'])]
            if not valid:
                break
            valid.sort(key=lambda x: x[0])
            dist, poi = valid[0]
            used_ids.add(id(poi))
            used_zones.append((poi['lat'], poi['lon']))
            selected.append(poi)
            total += dist
            cur_lat, cur_lon = poi['lat'], poi['lon']
            print(f"[ROUTE] [comfort] +{dist/1000:.2f}км {poi['name']} | {total/1000:.2f}/{target_km}км")

    type_summary = {}
    for p in selected:
        t = p.get('type', '?')
        type_summary[t] = type_summary.get(t, 0) + 1
    print(f"[ROUTE] Итого: {len(selected)} точек, {total/1000:.2f}км | типы: {type_summary}")
    return selected, total


def filter_by_distance(points, slat, slon, target_km):
    """Убирает точки слишком далеко от старта."""
    max_s = target_km * 1000 * 1.3
    out = []
    for p in points:
        c = p.get('coords')
        if not c:
            continue
        ds = haversine(slat, slon, c[0], c[1])
        if ds > max_s:
            print(f"[FILTER] ✗ {p['name']} далеко от старта {ds/1000:.1f}км")
            continue
        print(f"[FILTER] ✓ {p['name']} {ds/1000:.1f}км")
        out.append(p)
    return out


def gigachat_describe(places, params):
    if not places:
        return {}

    budget_map = {
        'free':      'только бесплатные места',
        'economy':   'эконом (до 500₽)',
        'medium':    'средний (500-2000₽)',
        'unlimited': 'без ограничений',
        'custom':    f"до {params.get('budgetAmount', '1000')}₽",
    }
    budget_str = budget_map.get(params.get('budget', 'medium'), 'средний')

    intensity_map = {
        'chill':  'спокойная прогулка с отдыхом',
        'active': 'активный осмотр достопримечательностей',
        'sport':  'интенсивная тренировка или бег',
    }
    intensity_str = intensity_map.get(params.get('intensity', 'chill'), 'спокойная')

    safety_str = 'избегать оживлённых дорог, только парки и пешеходные зоны' \
                 if params.get('safety') == 'parks' else 'любые дороги'

    access_map = {
        'stroller': 'нужны пандусы, ровное покрытие, без лестниц',
        'limited':  'нужна доступная среда, пандусы, низкие бордюры',
    }
    access_str = access_map.get(params.get('accessibility', 'none'), '')
    
    benches_str = 'обязательно наличие скамеек для отдыха' \
                  if params.get('benches') == 'yes' else ''

    bike_str = ''
    if params.get('transport') == 'bike':
        bike_map = {
            'slow':   'спокойный велотемп, велодорожки',
            'medium': 'средний велотемп',
            'fast':   'быстрый велотемп, шоссе',
        }
        bike_str = bike_map.get(params.get('bike_speed', 'medium'), '')

    include_str = f"Обязательно включить: {params['include']}." \
                  if params.get('include') else ''

    txt = '\n'.join(f"{i+1}. {p['name']} (тип: {p['type']})"
                    for i, p in enumerate(places))

    prompt = (
        f"Прогулка. Интересы: {params.get('interests_str','?')}, "
        f"компания: {params.get('company','один')}, "
        f"время суток: {params.get('daytime','день')}.\n"
        f"Бюджет: {budget_str}. "
        f"Интенсивность: {intensity_str}. "
        f"Безопасность: {safety_str}."
        f"{' Доступность: ' + access_str + '.' if access_str else ''}"
        f"{' ' + benches_str + '.' if benches_str else ''}"
        f"{' ' + bike_str + '.' if bike_str else ''}"
        f"{' ' + include_str if include_str else ''}\n\n"
        f"Для каждого места дай:\n"
        f"1. description — 1-2 предложения, почему подходит под параметры\n"
        f"2. price — примерная стоимость (например: 'бесплатно', '~300₽', '500-1500₽')\n"
        f"3. rating — твоя оценка от 1 до 5\n\n"
        f"Только JSON без markdown:\n"
        f'{{"descriptions":[{{"name":"...","description":"...","price":"...","rating":5}}]}}\n\n'
        f"Места:\n{txt}"
        f"{' Доступность: ' + access_str + '.' if access_str else ''}"
        f"{' ' + benches_str + '.' if benches_str else ''}"
    )
    try:
        result = parse_json_response(call_ai(prompt))
        out = {}
        for d in result.get('descriptions', []):
            out[d['name']] = {
                'description': d.get('description', ''),
                'price':       d.get('price', ''),
                'rating':      d.get('rating', 0),
            }
        return out
    except Exception as e:
        print(f"[AI] describe error: {e}")
        return {}


def generate_via_gigachat(data, slat, slon):
    """
    Fallback когда Overpass недоступен.
    Алгоритм: от текущей точки ищем ближайшее место по всем оставшимся категориям,
    берём самое близкое, убираем категорию, повторяем.
    """
    from routes.geo import find_nearest_by_category

    cats          = data.get('categories', [])
    accessibility = data.get('accessibility', 'none')
    daytime       = data.get('daytime', '')
    target_km     = get_target_km(data)
    target_m      = target_km * 1000

    cat_queries = {
        'cafe': 'кафе', 'restaurant': 'ресторан', 'bar': 'бар',
        'fast_food': 'столовая', 'park': 'парк', 'embankment': 'набережная',
        'forest': 'лесопарк', 'viewpoint': 'смотровая площадка',
        'museum': 'музей', 'gallery': 'галерея',
        'attraction': 'памятник', 'entertainment': 'театр',
        'sport': 'стадион', 'shopping': 'торговый центр',
        'supermarket': 'супермаркет', 'zoo': 'зоопарк',
    }

    # Очередь категорий — берём запрос для каждой
    remaining_cats = {cat: cat_queries.get(cat, cat) for cat in cats}
    if not remaining_cats:
        remaining_cats = {'park': 'парк', 'cafe': 'кафе', 'attraction': 'памятник'}

    # Если с коляской — убираем сложные категории мест
    if accessibility in ('stroller', 'limited'):
        hard_cats = {'forest', 'viewpoint', 'sport'}
        for hc in hard_cats:
            if hc in remaining_cats:
                del remaining_cats[hc]
                print(f"[AI] Доступность: убрана категория '{hc}' (сложный рельеф)")

    pts = [{'name': data['location'], 'description': 'Точка старта',
            'price': '', 'rating': None, 'coords': [slat, slon]}]

    cur_lat, cur_lon, total = slat, slon, 0.0
    used = []

    while remaining_cats and total < target_m:
        remaining = target_m - total
        if remaining <= 200:
            break

        # Ищем ближайшее место по ВСЕМ оставшимся категориям одновременно
        best = None  # (dist, lat, lon, name, cat_key)

        for cat_key, query in list(remaining_cats.items()):
            result = find_nearest_by_category(
                query, cur_lat, cur_lon,
                min(remaining + 1000, target_m * 1.3),
                used
            )
            if result:
                lat, lon, name = result
                dist = haversine(cur_lat, cur_lon, lat, lon)
                if best is None or dist < best[0]:
                    best = (dist, lat, lon, name, cat_key)
            time.sleep(0.3)

        if not best:
            print("[AI] Больше нет мест ни по одной категории")
            break

        dist, lat, lon, name, cat_key = best
        used.append((lat, lon))
        pts.append({'name': name, 'description': cat_queries.get(cat_key, cat_key),
                    'price': '', 'rating': None, 'coords': [lat, lon]})
        total += dist
        cur_lat, cur_lon = lat, lon
        del remaining_cats[cat_key]  # убираем использованную категорию
        print(f"[AI] ✓ [{cat_key}] {name} +{dist/1000:.2f}км | {total/1000:.2f}/{target_km}км | осталось: {list(remaining_cats.keys())}")

    if len(pts) < 2:
        return jsonify(error='Не удалось найти места поблизости.'), 404

    # GigaChat пишет описания
    cats_str = ', '.join(CAT_LABELS.get(c, c) for c in cats)
    desc_map = gigachat_describe(
        [{'name': p['name'], 'type': p['description']} for p in pts[1:]],
        {
            'interests_str': cats_str,
            'company':       data.get('company', 'один'),
            'daytime':       daytime,
            'budget':        data.get('budget', 'medium'),
            'accessibility': accessibility,
            'intensity':     data.get('intensity', 'chill'),
            'safety':        data.get('safety', 'any'),
        }
    )
    for p in pts[1:]:
        info = desc_map.get(p['name'], {})
        if isinstance(info, dict):
            p['description'] = info.get('description', p['description'])
            p['price']       = info.get('price', '')
            p['rating']      = info.get('rating')

    data['_points_count'] = len(pts)
    return jsonify({'places': pts, 'meta': build_meta(data, total)})

@ai_bp.get('/ping')
def ping():
    return jsonify(status='ok')


@ai_bp.post('/generate')
def generate_route():
    data = request.json
    if not data or not data.get('location'):
        return jsonify(error='Укажите место старта'), 400
    try:
        from routes.geo import geocode_start, search_pois, is_place_open_at_time
        start = geocode_start(data['location'])
        if not start:
            return jsonify(error=f'Не удалось найти "{data["location"]}". Попробуйте: Арбат, Москва'), 400
        slat, slon = start
        print(f"[AI] Старт: {data['location']} → {slat:.4f}, {slon:.4f}")
        target_km = get_target_km(data)
        radius = calc_radius(data)
        print(f"[AI] Цель: {target_km}км, радиус: {radius}м")
        interests = data.get('categories', data.get('interests', []))
        pois = search_pois(slat, slon, radius, interests)
        
        # Фильтр по времени суток
        daytime = data.get('daytime', '')
        if pois and daytime:
            from routes.geo import is_place_open_at_time
            pois = [p for p in pois if is_place_open_at_time(p, daytime)]
            print(f"[AI] После фильтра по времени ({daytime}): {len(pois)} POI")
        
        # Фильтр по доступности
        accessibility = data.get('accessibility', 'none')
        if pois and accessibility != 'none':
            from routes.geo import filter_accessible_pois
            pois = filter_accessible_pois(pois, accessibility)
            print(f"[AI] После фильтра доступности ({accessibility}): {len(pois)} POI")
        if pois is None:
            print("[AI] Overpass недоступен → GigaChat fallback")
            return generate_via_gigachat(data, slat, slon)
        if not pois:
            # Пробуем найти ближайшее метро и искать от него
            print("[AI] Мест не найдено, ищем ближайшее метро...")
            from routes.geo import find_nearest_metro
            metro = find_nearest_metro(slat, slon)
            if metro:
                mlat, mlon, mname = metro
                print(f"[AI] Пробуем от метро: {mname}")
                pois = search_pois(mlat, mlon, radius, interests)
                if pois:
                    slat, slon = mlat, mlon
                    data = dict(data)
                    data['location'] = mname
                    print(f"[AI] Старт смещён к метро {mname}")
            if not pois:
                return jsonify(error='Не найдено мест поблизости. Попробуйте другой адрес.'), 404
        wanted = []
        for i in interests:
            wanted.extend(INTEREST_TYPES.get(i, [i]))
        if not wanted:
            wanted = DEFAULT_TYPES
        selected, actual_m = select_route_points(pois, slat, slon, wanted, target_km, interests)
        print(f"[AI] Выбрано: {[p['name'] for p in selected]}")
        cats_str = ', '.join(CAT_LABELS.get(i, i) for i in interests)
        desc_map = gigachat_describe(selected, {
            'interests_str': cats_str,
            'company':       data.get('company', 'один'),
            'daytime':       data.get('daytime', 'день'),
            'budget':        data.get('budget', 'medium'),
            'budgetAmount':  data.get('budgetAmount', ''),
            'intensity':     data.get('intensity', 'chill'),
            'safety':        data.get('safety', 'any'),
            'accessibility': data.get('accessibility', 'none'),
            'benches':       data.get('benches', 'no'),
            'transport':     data.get('transport', 'walk'),
            'bike_speed':    data.get('bike_speed', 'medium'),
            'include':       data.get('include', ''),
        })
        pts = [{'name': data['location'], 'description': 'Точка старта',
                'price': '', 'rating': None, 'coords': [slat, slon]}]
        for p in selected:
            info = desc_map.get(p['name'], {})
            # Фильтр по бюджету: если бесплатно — пропускаем платные места
            budget = data.get('budget', 'medium')
            price  = info.get('price', '') if isinstance(info, dict) else ''
            if budget == 'free' and price and price != 'бесплатно' and '₽' in price:
                print(f"[BUDGET] Пропускаем {p['name']} — платное ({price}), бюджет: бесплатно")
                continue
            pts.append({
                'name':        p['name'],
                'description': info.get('description', p['type']) if isinstance(info, dict) else str(info),
                'price':       price,
                'rating':      info.get('rating') if isinstance(info, dict) else None,
                'coords':      [p['lat'], p['lon']],
                'opening_hours': p.get('opening_hours', ''),
                'wheelchair':    p.get('wheelchair', ''),
            })
        rest = filter_by_distance(pts[1:], slat, slon, target_km)
        pts = pts[:1] + rest
        data['_points_count'] = len(pts)
        return jsonify({'places': pts, 'meta': build_meta(data, actual_m)})
    except Exception as e:
        import traceback
        print(f"[ERROR]\n{traceback.format_exc()}")
        return jsonify(error=str(e)), 500


@ai_bp.post('/suggest-metro')
def suggest_metro():
    """Нейросеть подбирает станцию метро под интересы пользователя."""
    data = request.json or {}
    cats     = data.get('categories', [])
    city     = data.get('city', 'Москва')
    cats_str = ', '.join(CAT_LABELS.get(c, c) for c in cats) or 'парки, кафе, достопримечательности'

    prompt = (f"Пользователь хочет прогуляться в городе {city}.\n"
              f"Его интересы: {cats_str}.\n"
              f"Предложи 5 станций метро в {city} которые лучше всего подходят для такой прогулки.\n"
              f"Для каждой станции — 1 предложение почему она подходит.\n"
              f"Только JSON без markdown:\n"
              f'{{"stations":[{{"name":"название станции","description":"почему подходит"}}]}}')
    try:
        content  = call_ai(prompt)
        result   = parse_json_response(content)
        stations = result.get('stations', [])
        return jsonify({'stations': stations})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify(error=str(e)), 500
