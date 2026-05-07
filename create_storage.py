"""
Запусти этот скрипт ОДИН РАЗ после настройки .env
Он создаст нужный bucket в Supabase Storage автоматически

Использование:
  python create_storage.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")

if not url or not key or "YOUR_PROJECT" in url:
    print("❌ Сначала заполни SUPABASE_URL и SUPABASE_SERVICE_KEY в .env")
    exit(1)

sb = create_client(url, key)

try:
    # Создаём публичный bucket
    sb.storage.create_bucket("ishjoy-public", options={"public": True})
    print("✅ Bucket 'ishjoy-public' создан!")
except Exception as e:
    if "already exists" in str(e).lower():
        print("✅ Bucket уже существует — всё готово!")
    else:
        print(f"⚠️ Ошибка: {e}")
        exit(1)

print("\n🎉 Supabase Storage готов!")
print("Теперь можно загружать фото аватаров, логотипов и PDF резюме.")
