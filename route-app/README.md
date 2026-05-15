# RouteAI — Умные маршруты для прогулок

Веб-сервис, который генерирует персональные маршруты прогулок на основе анкеты пользователя с помощью нейросети.

## Стек

- **Frontend:** HTML, CSS, Vanilla JS, Яндекс.Карты API
- **Backend:** Python, Flask, SQLAlchemy, JWT
- **БД:** SQLite (dev) / PostgreSQL (prod)
- **AI:** YandexGPT / GigaChat
- **Геоданные:** Nominatim (OSM), Overpass API, OSRM

## Быстрый старт

### Локально

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd route-app

# 2. Настроить переменные окружения
cp backend/.env.example backend/.env
# Заполнить backend/.env своими ключами

# 3. Запустить бэкенд
cd backend
pip install -r requirements.txt
python app.py

# 4. Запустить фронтенд (в другом терминале)
cd frontend
python -m http.server 8080

# 5. Открыть в браузере
# http://localhost:8080
```

### Через Docker

```bash
cp backend/.env.example backend/.env
# Заполнить .env

docker-compose up --build
# Frontend: http://localhost:8080
# Backend:  http://localhost:5000
```

## Переменные окружения

| Переменная           | Описание                          |
|----------------------|-----------------------------------|
| `JWT_SECRET`         | Секрет для JWT токенов            |
| `GIGACHAT_CREDENTIALS` | Base64 ключ GigaChat            |
| `YANDEX_GPT_KEY`     | API ключ YandexGPT                |
| `YANDEX_FOLDER_ID`   | Folder ID Яндекс Облака           |
| `YANDEX_MAPS_KEY`    | API ключ Яндекс.Карт              |
| `DATABASE_URL`       | URL базы данных (SQLite/PostgreSQL)|

## API эндпоинты

| Метод  | URL                    | Описание                    |
|--------|------------------------|-----------------------------|
| POST   | /api/auth/register     | Регистрация                 |
| POST   | /api/auth/login        | Вход                        |
| GET    | /api/auth/me           | Текущий пользователь        |
| POST   | /api/ai/generate       | Генерация маршрута          |
| GET    | /api/routes/my         | Мои маршруты                |
| POST   | /api/routes/save       | Сохранить маршрут           |
| DELETE | /api/routes/:id        | Удалить маршрут             |
