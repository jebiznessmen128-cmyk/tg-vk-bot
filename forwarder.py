import os
import asyncio
from aiohttp import web
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import vk_api

# 1. СПИСОК ЧАТОВ ДЛЯ ПЕРЕСЫЛКИ
ALLOWED_CHATS = [
    "ProstoKhusan",
    "fkmfkb",
    "lubit_jizn",
    "idbot"
]

# 2. Переменные окружения
api_id = int(os.environ["TG_API_ID"])
api_hash = os.environ["TG_API_HASH"]
session_string = os.environ["TG_SESSION"]

vk_token = os.environ["VK_TOKEN"]
vk_user_id = int(os.environ["VK_USER_ID"])

# Инициализация VK и Telegram
vk_session = vk_api.VkApi(token=vk_token)
vk = vk_session.get_api()
client = TelegramClient(StringSession(session_string), api_id, api_hash)

# Множество для защиты от дублей
processed_msg_ids = set()

# Веб-обработчик для Render / UptimeRobot
async def handle_ping(request):
    return web.Response(text="Bot is alive!")

@client.on(events.NewMessage(chats=ALLOWED_CHATS))
async def handler(event):
    if event.out:
        return

    msg_key = (event.chat_id, event.id)
    if msg_key in processed_msg_ids:
        return
    
    processed_msg_ids.add(msg_key)
    if len(processed_msg_ids) > 100:
        processed_msg_ids.pop()

    sender = await event.get_sender()
    chat = await event.get_chat()

    sender_name = getattr(sender, 'first_name', None) or getattr(chat, 'title', 'Неизвестно')
    text = f"📩 [{sender_name}]:\n\n{event.text}"

    try:
        vk.messages.send(
            user_id=vk_user_id,
            random_id=0,
            message=text
        )
        print(f"Успешно переслано сообщение от: {sender_name}")
    except Exception as e:
        print(f"Ошибка отправки в ВК: {e}")

async def main():
    # Запускаем веб-сервер aiohttp
    app = web.Application()
    app.router.add_get('/', handle_ping)
    
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    # Запускаем Telegram-бота
    await client.start()
    print("Бот успешно запущен и слушает сообщения 24/7...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
