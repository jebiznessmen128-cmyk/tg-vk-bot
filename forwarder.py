import os
import asyncio
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

# Инициализация VK
vk_session = vk_api.VkApi(token=vk_token)
vk = vk_session.get_api()

# Инициализация Telegram
client = TelegramClient(StringSession(session_string), api_id, api_hash)


@client.on(events.NewMessage(chats=ALLOWED_CHATS))
async def handler(event):
    # Пропускаем исходящие сообщения (от самого себя)
    if event.out:
        return

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
    await client.start()
    print("Бот успешно запущен и слушаeт сообщения 24/7...")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
