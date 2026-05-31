# RouteAI — Умные маршруты для прогулок

Веб-сервис для создания персонализированных пешеходных и велосипедных маршрутов с помощью нейросетей.

## Возможности

-  Генерация маршрутов по интересам, бюджету и компании
-  Учёт доступности: коляски, пандусы, скамейки
-  Смена темы оформления (3 цветовые схемы)
-  Гостевой режим без регистрации
-  Редактирование маршрута (добавление/удаление точек)
-  Аватар и редактирование профиля

## Технологии

- **Frontend:** HTML, CSS, JavaScript, Leaflet
- **Backend:** Python, Flask, SQLAlchemy, JWT, Socket.IO
- **База данных:** SQLite
- **Нейросети:** YandexGPT / GigaChat
- **Карты:** Яндекс.Карты, OpenStreetMap (Overpass API)

## Установка и запуск

```bash
git clone https://github.com/Xren2233/routeai.git
cd my-sitee

# Настроить переменные окружения
cp backend/.env.example backend/.env
# Отредактировать backend/.env — добавить ключи API

# Запуск
cd backend
pip install -r requirements.txt
python app.py

## Демо

[Открыть сайт](https://routeai.pythonanywhere.com)
