import asyncio
import base64
import os
from telethon import TelegramClient

API_ID   = int(input("Введите TG_API_ID: "))
API_HASH = input("Введите TG_API_HASH: ").strip()

SESSION_FILE = "export_session_tmp"

async def main():
    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    await client.start()
    me = await client.get_me()
    print(f"\n✅ Авторизованы как: {me.first_name} (@{me.username})\n")
    await client.disconnect()

    session_path = SESSION_FILE + ".session"
    with open(session_path, "rb") as f:
        session_b64 = base64.b64encode(f.read()).decode()

    os.remove(session_path)

    print("=" * 60)
    print("Скопируйте строку ниже и сохраните её в Блокнот:")
    print("=" * 60)
    print(session_b64)
    print("=" * 60)

asyncio.run(main())