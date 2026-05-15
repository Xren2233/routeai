```markdown
# RouteAI — Умные маршруты для прогулок

Веб-сервис, который генерирует персональные маршруты прогулок на основе анкеты пользователя с помощью нейросети.

## Возможности

-  Персональные маршруты по интересам, бюджету и компании
-  Учёт доступности: коляски, пандусы, скамейки
-  Смена темы оформления (4 цветовые схемы)
-  Гостевой режим без регистрации
-  Редактирование маршрута (добавить/удалить точки)
-  Аватар и редактирование профиля

## Стек

- **Frontend:** HTML, CSS, Vanilla JS, Leaflet
- **Backend:** Python, Flask, SQLAlchemy, JWT, Socket.IO
- **БД:** SQLite (dev) / PostgreSQL (prod)
- **AI:** YandexGPT / GigaChat
- **Геоданные:** Nominatim (OSM), Overpass API

## Структура проекта

```
backend/
├── routes/           # Blueprints (auth, ai, geo, routes_bp)
├── app.py            # Flask + Socket.IO
├── database.py       # Модели (User, Route, FavoritePlace)
├── requirements.txt
└── Dockerfile

frontend/
├── css/style.css     # Стили с темами
├── js/
│   ├── app.js        # Роутер, темы, профиль
│   ├── auth.js       # Авторизация, guest
│   ├── survey.js     # Анкета, генерация
│   └── map.js        # Leaflet карта
└── index.html
```

## Быстрый старт

### Локально

```bash
git clone <repo-url>
cd my-sitee

cp backend/.env.example backend/.env
# Заполнить backend/.env ключами

cd backend
pip install -r requirements.txt
python app.py

# В другом терминале
cd frontend
python -m http.server 8080

# Открыть http://localhost:8080
```

### Docker

```bash
cp backend/.env.example backend/.env
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
| `DATABASE_URL`       | URL базы данных                   |

## API эндпоинты

| Метод  | URL                    | Описание                    |
|--------|------------------------|-----------------------------|
| POST   | /api/auth/register     | Регистрация                 |
| POST   | /api/auth/login        | Вход                        |
| GET    | /api/auth/me           | Текущий пользователь        |
| PUT    | /api/auth/me           | Обновить профиль            |
| DELETE | /api/auth/me           | Удалить аккаунт             |
| POST   | /api/ai/generate       | Генерация маршрута          |
| POST   | /api/ai/suggest-metro  | Подбор станций метро        |
| GET    | /api/routes/my         | Мои маршруты                |
| POST   | /api/routes/save       | Сохранить маршрут           |
| PUT    | /api/routes/:id        | Переименовать маршрут       |
| DELETE | /api/routes/:id        | Удалить маршрут             |
```