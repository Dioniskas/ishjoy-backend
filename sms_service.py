import httpx
import os
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException

ESKIZ_EMAIL = os.getenv("ESKIZ_EMAIL", "your@email.com")
ESKIZ_PASSWORD = os.getenv("ESKIZ_PASSWORD", "your_password")
ESKIZ_BASE = "https://notify.eskiz.uz/api"

# Кэшируем токен Eskiz в памяти
_eskiz_token = None
_eskiz_token_expires = None


async def get_eskiz_token() -> str:
    """Получаем/обновляем токен Eskiz"""
    global _eskiz_token, _eskiz_token_expires

    now = datetime.now(timezone.utc)
    if _eskiz_token and _eskiz_token_expires and now < _eskiz_token_expires:
        return _eskiz_token

    async with httpx.AsyncClient() as client:
        res = await client.post(f"{ESKIZ_BASE}/auth/login", data={
            "email": ESKIZ_EMAIL,
            "password": ESKIZ_PASSWORD,
        })
        if res.status_code != 200:
            raise HTTPException(status_code=500, detail="Ошибка авторизации SMS сервиса")

        data = res.json()
        _eskiz_token = data["data"]["token"]
        # Токен живёт 29 дней, обновляем за день до истечения
        _eskiz_token_expires = now + timedelta(days=28)
        return _eskiz_token


async def send_sms(phone: str, message: str) -> bool:
    """
    Отправляем SMS через Eskiz.uz
    phone: номер в формате 998901234567 (без +)
    """
    # Убираем + если есть
    clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")

    token = await get_eskiz_token()

    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{ESKIZ_BASE}/message/sms/send",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "mobile_phone": clean_phone,
                "message": message,
                "from": "4546",   # Короткий номер Eskiz (можно изменить)
                "callback_url": "",
            }
        )

        if res.status_code == 401:
            # Токен истёк — сбрасываем и пробуем ещё раз
            global _eskiz_token
            _eskiz_token = None
            return await send_sms(phone, message)

        data = res.json()
        return data.get("status") == "waiting"


async def send_otp_sms(phone: str, code: str) -> bool:
    """Отправляем OTP код"""
    message = f"Ishjoy tasdiqlash kodi: {code}\nKod ishchi emas: {code}"
    # Или на русском:
    # message = f"Ваш код Ishjoy: {code}. Никому не сообщайте!"
    return await send_sms(phone, message)


async def refresh_eskiz_token() -> bool:
    """Обновляем токен (вызывать раз в 29 дней)"""
    global _eskiz_token, _eskiz_token_expires
    try:
        token = await get_eskiz_token()
        async with httpx.AsyncClient() as client:
            res = await client.patch(
                f"{ESKIZ_BASE}/auth/refresh",
                headers={"Authorization": f"Bearer {token}"}
            )
            if res.status_code == 200:
                _eskiz_token_expires = datetime.now(timezone.utc) + timedelta(days=28)
                return True
    except Exception:
        _eskiz_token = None
    return False
