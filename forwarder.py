import os
import asyncio
import json
import time
from telethon import TelegramClient
import vk_api

# 1. СПИСОК ЧАТОВ / БОТОВ ДЛЯ ПЕРЕСЫЛКИ
# Укажите юзернеймы (без @) или ID диалогов, из которых НАДО пересылать сообщения
ALLOWED_CHATS = [
    "ProstoKhusan",       # Например: "BotFather" или юзернейм любого бота
    "fkmfkb",    # Юзернейм человека
    "lubit_jizn",                # Или ID чата/пользователя (числом)
    "idbot"
]

# Файл для сохранения ID последних обработанных сообщений
STATE_FILE = "last_ids.json"

async def main():
    api_id = int(os.environ["TG_API_ID"])
    api_hash = os.environ["TG_API_HASH"]
    session_string = os.environ["TG_SESSION"]
    vk_token = os.environ["VK_TOKEN"]
    
    # ID получателя в ВК
    vk_user_id = int(os.environ.get("VK_USER_ID", "0"))

    # Инициализация ВК
    vk_session = vk_api.VkApi(token=vk_token)
    vk = vk_session.get_api()

    # Загружаем сохранённый прогресс
    last_ids = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                last_ids = json.load(f)
        except Exception as e:
            print(f"[WARN] Ошибка чтения {STATE_FILE}: {e}")

    # Инициализация Telegram клиента
    from telethon.sessions import StringSession
    async with TelegramClient(StringSession(session_string), api_id, api_hash) as client:
        print("[INFO] Telegram подключён")

        for chat in ALLOWED_CHATS:
            chat_key = str(chat)
            last_id = last_ids.get(chat_key, 0)
            
            try:
                # Получаем последние сообщения из конкретного диалога
                messages = []
                async for message in client.iter_messages(chat, limit=10):
                    if message.id <= last_id:
                        break
                    messages.append(message)

                # Обрабатываем от старых к новым
                messages.reverse()

                for msg in messages:
                    text = msg.text or ""
                    
                    # Если есть текст или медиа — формируем и отправляем
                    if text or msg.media:
                        print(f"[INFO] Пересылаем сообщение из {chat_key} (ID: {msg.id})")
                        
                        # Если сообщение слишком длинное для ВК (лимит 4096 символов)
                        full_text = f"Сообщение из {chat_key}:\n\n{text}" if text else f"Медиа из {chat_key}"
                        
                        try:
                            # Отправка в ЛИЧКУ ВК по user_id
                            vk.messages.send(
                                user_id=vk_user_id,
                                message=full_text[:4000],
                                random_id=0
                            )
                            # Пауза 2 секунды, чтобы не триггерить капчу ВК
                            time.sleep(2)
                            
                        except Exception as vk_err:
                            print(f"[ERROR] Ошибка отправки в VK: {vk_err}")

                    # Обновляем сохранённый ID последнего сообщения
                    if msg.id > last_ids.get(chat_key, 0):
                        last_ids[chat_key] = msg.id

            except Exception as chat_err:
                print(f"[ERROR] Не удалось обработать чат {chat_key}: {chat_err}")

    # Сохраняем обновленный прогресс
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(last_ids, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
