import asyncio
import json
import logging
import os
import tempfile

from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, MessageMediaWebPage
import vk_api
from vk_api.upload import VkUpload

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("tg2vk")

TG_API_ID    = int(os.environ["TG_API_ID"])
TG_API_HASH  = os.environ["TG_API_HASH"]
TG_SESSION   = os.environ["TG_SESSION"]

VK_TOKEN     = os.environ["VK_TOKEN"]
VK_USER_ID   = int(os.environ.get("VK_USER_ID", "0"))
VK_CHAT_ID   = int(os.environ.get("VK_CHAT_ID", "0"))

RAW_SOURCES  = os.environ.get("TG_SOURCES", "").strip()
TG_SOURCES   = [s.strip() for s in RAW_SOURCES.split(",") if s.strip()]

MESSAGE_PREFIX = os.environ.get("MESSAGE_PREFIX", "📨 Telegram: ")

STATE_FILE   = "last_ids.json"
MESSAGES_LIMIT = 20

vk_session = vk_api.VkApi(token=VK_TOKEN)
vk         = vk_session.get_api()
vk_upload  = VkUpload(vk_session)


def vk_send(text: str, attachments: list[str] | None = None):
    params: dict = {"random_id": 0, "message": text or ""}
    if VK_CHAT_ID:
        params["chat_id"] = VK_CHAT_ID
    else:
        params["user_id"] = VK_USER_ID
    if attachments:
        params["attachment"] = ",".join(attachments)
    try:
        vk.messages.send(**params)
        log.info("VK ✓ %d симв., %d вложений", len(text or ""), len(attachments or []))
    except vk_api.exceptions.ApiError as e:
        log.error("VK API ошибка: %s", e)


def upload_photo(data: bytes) -> str | None:
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(data); tmp = f.name
        res = vk_upload.photo_messages(tmp)
        os.unlink(tmp)
        p = res[0]
        return f"photo{p['owner_id']}_{p['id']}"
    except Exception as e:
        log.error("Ошибка загрузки фото: %s", e)
        return None


def upload_doc(data: bytes, filename: str) -> str | None:
    try:
        ext = os.path.splitext(filename)[1] or ".bin"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            f.write(data); tmp = f.name
        peer_id = (2_000_000_000 + VK_CHAT_ID) if VK_CHAT_ID else VK_USER_ID
        res = vk_upload.document_message(tmp, peer_id=peer_id, title=filename)
        os.unlink(tmp)
        d = res["doc"]
        return f"doc{d['owner_id']}_{d['id']}"
    except Exception as e:
        log.error("Ошибка загрузки документа: %s", e)
        return None


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


async def get_session_file() -> str:
    import base64
    session_b64 = TG_SESSION
    session_bytes = base64.b64decode(session_b64)
    path = "/tmp/tg_session.session"
    with open(path, "wb") as f:
        f.write(session_bytes)
    return "/tmp/tg_session"


async def forward_dialog(client, entity, dialog_key: str, state: dict):
    last_id = state.get(dialog_key, 0)
    messages = []

    async for msg in client.iter_messages(entity, limit=MESSAGES_LIMIT):
        if msg.id <= last_id:
            break
        if not msg.out:
            messages.append(msg)

    if not messages:
        return

    messages.reverse()

    for msg in messages:
        text = msg.text or msg.message or ""

        try:
            sender = await msg.get_sender()
            first = getattr(sender, "first_name", "") or ""
            last  = getattr(sender, "last_name",  "") or ""
            uname = getattr(sender, "username",   "") or ""
            name  = f"{first} {last}".strip() or uname or dialog_key
        except Exception:
            name = dialog_key

        header = f"{MESSAGE_PREFIX}от {name}\n"
        attachments = []

        if msg.media and not isinstance(msg.media, MessageMediaWebPage):
            try:
                media_bytes = await msg.download_media(file=bytes)
            except Exception as e:
                log.error("Ошибка скачивания медиа: %s", e)
                media_bytes = None

            if media_bytes:
                if isinstance(msg.media, MessageMediaPhoto):
                    att = upload_photo(media_bytes)
                    if att:
                        attachments.append(att)
                elif isinstance(msg.media, MessageMediaDocument):
                    doc = msg.media.document
                    fname = "file"
                    for attr in doc.attributes:
                        if hasattr(attr, "file_name"):
                            fname = attr.file_name
                            break
                    if doc.size < 50 * 1024 * 1024:
                        att = upload_doc(media_bytes, fname)
                        if att:
                            attachments.append(att)
                    else:
                        text += "\n[Файл слишком большой]"

        full_text = (header + text).strip()
        vk_send(full_text, attachments or None)
        await asyncio.sleep(1)

    state[dialog_key] = messages[-1].id
    log.info("Диалог %s: переслано %d сообщений", dialog_key, len(messages))


async def main():
    session_path = await get_session_file()
    state = load_state()

    async with TelegramClient(session_path, TG_API_ID, TG_API_HASH) as client:
        log.info("Telegram подключён")

        if TG_SOURCES:
            for src in TG_SOURCES:
                try:
                    entity = await client.get_entity(src)
                    key = str(entity.id)
                    await forward_dialog(client, entity, key, state)
                except Exception as e:
                    log.error("Ошибка источника %s: %s", src, e)
        else:
            async for dialog in client.iter_dialogs():
                if dialog.is_user:
                    key = str(dialog.entity.id)
                    try:
                        await forward_dialog(client, dialog.entity, key, state)
                    except Exception as e:
                        log.error("Ошибка диалога %s: %s", key, e)

    save_state(state)
    log.info("Готово. Состояние сохранено.")


if __name__ == "__main__":
    asyncio.run(main())
