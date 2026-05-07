# 🚀 Ishjoy Backend — Инструкция по запуску

## Структура проекта
```
ishjoy-backend/
├── main.py              # FastAPI приложение
├── database.py          # Подключение к БД
├── models.py            # Таблицы базы данных
├── schemas.py           # Pydantic схемы
├── auth_utils.py        # JWT авторизация
├── requirements.txt     # Зависимости
├── .env.example         # Переменные окружения
└── routers/
    ├── auth.py          # Авторизация по SMS
    ├── jobs.py          # Вакансии
    ├── resumes.py       # Резюме
    ├── applications.py  # Отклики
    └── ai_features.py   # AI функции
```

---

## ШАГ 1 — Supabase (бесплатная БД)

1. Зайди на https://supabase.com → Sign Up (бесплатно)
2. New Project → придумай имя "ishjoy" и пароль
3. После создания: Settings → Database → Connection String
4. Скопируй URI, замени [YOUR-PASSWORD] на свой пароль
5. Измени `postgresql://` на `postgresql+asyncpg://`

---

## ШАГ 2 — Anthropic API ключ

1. Зайди на https://console.anthropic.com
2. API Keys → Create Key
3. Скопируй ключ (начинается с `sk-ant-`)

---

## ШАГ 3 — Локальный запуск

```bash
# 1. Создай папку и перейди в неё
cd ishjoy-backend

# 2. Создай виртуальное окружение
python -m venv venv
source venv/bin/activate      # Mac/Linux
# или: venv\Scripts\activate  # Windows

# 3. Установи зависимости
pip install -r requirements.txt

# 4. Создай .env файл
cp .env.example .env
# Открой .env и вставь свои ключи

# 5. Запускай!
python main.py
```

Открой браузер: http://localhost:8000/docs — увидишь всё API!

---

## ШАГ 4 — Деплой на Render.com (бесплатно)

1. Зайди на https://render.com → Sign Up
2. New → Web Service
3. Connect GitHub репозиторий (загрузи код на GitHub)
4. Настройки:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Environment Variables — добавь все из .env
6. Deploy! Получишь URL типа `https://ishjoy-api.onrender.com`

---

## AI Функции

| Эндпоинт | Описание |
|----------|----------|
| `POST /api/ai/generate-resume` | Создать резюме из текста |
| `POST /api/ai/smart-search` | Умный поиск вакансий |
| `POST /api/ai/cover-letter` | Сопроводительное письмо |
| `POST /api/ai/interview-prep` | Подготовка к собеседованию |
| `POST /api/ai/chat` | Карьерный консультант |
| `GET /api/ai/salary-insight` | Анализ зарплат |

---

## API Документация

После запуска: http://localhost:8000/docs (Swagger UI)

---

## Следующие шаги

- [ ] SMS через Eskiz.uz (uzb SMS провайдер)
- [ ] Загрузка фото (Cloudinary)
- [ ] Push-уведомления (Firebase)
- [ ] Конвертация в APK (Capacitor)
