# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from routes.geo import geocode_start, search_pois

location = 'Arbat, Moscow'   # английский для теста
print(f"Геокодируем: {location}")
result = geocode_start(location)
print(f"Результат: {result}")

if result:
    lat, lon = result
    print(f"\nИщем POI в радиусе 2000м от {lat}, {lon}")
    pois = search_pois(lat, lon, 2000, ['city_park', 'coffee', 'museum'])
    print(f"Найдено POI: {len(pois)}")
    for p in pois[:10]:
        print(f"  - {p['name']} ({p['type']}) @ {p['lat']:.4f},{p['lon']:.4f}")
else:
    print("ОШИБКА: не удалось геокодировать стартовую точку")
