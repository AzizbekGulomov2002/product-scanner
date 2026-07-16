import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
    URLInputFile,
)
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").strip()
LOADING_STICKER = os.getenv("TELEGRAM_LOADING_STICKER", "").strip()
HOURGLASS_ANIMATION = "https://media.giphy.com/media/3oEjI6sIIiv02jQVNu/giphy.gif"

STATUS_UZ = {
    "found": "Mahsulot topildi",
    "probable": "Taxminiy natija",
    "not_found": "Mahsulot topilmadi",
}

bot = None
dp = Dispatcher(storage=MemoryStorage())


class Form(StatesGroup):
    search = State()
    add_images = State()
    add_details = State()


def get_bot() -> Bot:
    global bot
    if bot is None:
        if not BOT_TOKEN or BOT_TOKEN == "your-telegram-bot-token-here":
            raise SystemExit("TELEGRAM_BOT_TOKEN .env faylida topilmadi.")
        bot = Bot(token=BOT_TOKEN)
    return bot


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ID / Nom / Rasm bo'yicha qidirish", callback_data="menu_search")],
        [InlineKeyboardButton(text="Bazaga mahsulot", callback_data="menu_add")],
    ])


def add_done_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Tayyor — keyingi qadam", callback_data="add_done")],
        [InlineKeyboardButton(text="Bekor qilish", callback_data="menu_back")],
    ])


def product_caption(product: dict) -> str:
    return (
        f"✅ Topildi\n\n"
        f"📦 Nomi: {product['name']}\n"
        f"🆔 ID: {product['external_id']}\n"
        f"📊 Barcode: {product.get('barcode') or '—'}"
    )


async def fetch_image_bytes(client: httpx.AsyncClient, url: str) -> bytes | None:
    if not url.startswith("http"):
        url = BACKEND_URL.rstrip("/") + url
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content
    except Exception as exc:
        logger.warning("Image download failed %s: %s", url, exc)
        return None


async def send_product_result(message: Message, product: dict, client: httpx.AsyncClient):
    caption = product_caption(product)
    images = product.get("images") or []
    media_files = []

    for img in images:
        url = img.get("image_url") or img.get("image")
        if not url:
            continue
        content = await fetch_image_bytes(client, url)
        if content:
            media_files.append(BufferedInputFile(content, filename=f"product_{img.get('id', 'img')}.jpg"))

    if not media_files:
        await message.answer(caption)
        return

    if len(media_files) == 1:
        await message.answer_photo(media_files[0], caption=caption)
        return

    media_group = [InputMediaPhoto(media=media_files[0], caption=caption)]
    media_group.extend(InputMediaPhoto(media=f) for f in media_files[1:])
    await message.answer_media_group(media_group)


async def send_loading(message: Message) -> Message:
    try:
        if LOADING_STICKER:
            return await message.answer_sticker(LOADING_STICKER)
        return await message.answer_animation(URLInputFile(HOURGLASS_ANIMATION))
    except Exception:
        return await message.answer("⏳")


async def remove_loading(msg: Message | None):
    if msg:
        try:
            await msg.delete()
        except Exception:
            pass


@asynccontextmanager
async def loading_indicator(message: Message):
    loading_msg = await send_loading(message)
    try:
        yield
    finally:
        await remove_loading(loading_msg)


async def download_photo_bytes(message: Message) -> bytes | None:
    tg_bot = get_bot()
    if message.photo:
        file = await tg_bot.get_file(message.photo[-1].file_id)
    elif message.document and message.document.mime_type and message.document.mime_type.startswith("image/"):
        file = await tg_bot.get_file(message.document.file_id)
    else:
        return None
    file_bytes = await tg_bot.download_file(file.file_path)
    return file_bytes.read() if hasattr(file_bytes, "read") else file_bytes


async def ai_search(message: Message, state: FSMContext):
    content = await download_photo_bytes(message)
    if not content:
        await message.answer("Rasm yuboring (JPG, PNG).", reply_markup=main_menu())
        return

    try:
        async with loading_indicator(message):
            async with httpx.AsyncClient(timeout=120.0) as client:
                files = {"image": ("photo.jpg", content, "image/jpeg")}
                data = {
                    "source": "telegram",
                    "telegram_user_id": str(message.from_user.id),
                    "telegram_username": message.from_user.username or "",
                }
                resp = await client.post(f"{BACKEND_URL}/api/search/image/", files=files, data=data)
                if resp.status_code != 200:
                    await message.answer("❌ Server xatosi. Django ishlayaptimi?", reply_markup=main_menu())
                    return
                result = resp.json()
    except httpx.ConnectError:
        await message.answer("❌ Serverga ulanib bo'lmadi. `./run-server.sh` ishga tushiring.", reply_markup=main_menu())
        return
    except Exception as exc:
        logger.exception("AI search error")
        await message.answer(f"❌ Xatolik: {exc}", reply_markup=main_menu())
        return

    await state.clear()
    await send_ai_result(message, result)


@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Product Searcher\n\nKerakli bo'limni tanlang:",
        reply_markup=main_menu(),
    )


@dp.callback_query(F.data == "menu_back")
async def menu_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "Product Searcher\n\nKerakli bo'limni tanlang:",
        reply_markup=main_menu(),
    )
    await callback.answer()


@dp.callback_query(F.data == "menu_search")
async def menu_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Form.search)
    await callback.message.edit_text(
        "ID, nom yoki rasm yuboring:\n\nMasalan: 001 yoki Skovorodka",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="← Orqaga", callback_data="menu_back")],
        ]),
    )
    await callback.answer()


@dp.message(Form.search, F.text)
async def handle_search(message: Message, state: FSMContext):
    query = message.text.strip()
    if not query:
        await message.answer("ID, nom yoki rasm yuboring.")
        return

    try:
        async with loading_indicator(message):
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{BACKEND_URL}/api/products/lookup/",
                    params={"q": query},
                )
                data = resp.json()

                if not data.get("found") or not data.get("products"):
                    await state.clear()
                    await message.answer("❌ Mahsulot topilmadi.", reply_markup=main_menu())
                    return

                for product in data["products"]:
                    await send_product_result(message, product, client)
    except httpx.ConnectError:
        await state.clear()
        await message.answer("❌ Serverga ulanib bo'lmadi. `./run-server.sh` ishga tushiring.")
        return

    await state.clear()
    await message.answer("Bosh menyu:", reply_markup=main_menu())


@dp.callback_query(F.data == "menu_add")
async def menu_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Form.add_images)
    await state.update_data(images=[])
    await callback.message.edit_text(
        "Mahsulot rasmlarini yuboring (bir nechta).\nTayyor bo'lgach tugmani bosing.",
        reply_markup=add_done_keyboard(),
    )
    await callback.answer()


@dp.message(F.photo | F.document)
async def handle_image(message: Message, state: FSMContext):
    current = await state.get_state()

    if current == Form.add_images.state:
        content = await download_photo_bytes(message)
        if not content:
            await message.answer("Rasm fayl yuboring (JPG, PNG).")
            return
        data = await state.get_data()
        images = data.get("images", [])
        images.append(content)
        await state.update_data(images=images)
        await message.answer(
            f"✅ Rasm qabul qilindi ({len(images)} ta).\nYana yuboring yoki «Tayyor» bosing.",
            reply_markup=add_done_keyboard(),
        )
        return

    if current == Form.add_details.state:
        await message.answer("Avval ID va nom kiriting.\nFormat: ID | Nomi | Barcode")
        return

    # Boshqa holatda — AI qidiruv (kamera skanner)
    await ai_search(message, state)


@dp.callback_query(F.data == "add_done")
async def add_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    images = data.get("images", [])
    if not images:
        await callback.answer("Kamida 1 ta rasm yuboring!", show_alert=True)
        return

    await state.set_state(Form.add_details)
    await callback.message.edit_text(
        "ID va nom kiriting:\n\n"
        "Format: ID | Nomi\n"
        "Barcode bilan: ID | Nomi | Barcode\n\n"
        "Masalan: 001 | Skovorodka | 1234567890",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="← Bekor qilish", callback_data="menu_back")],
        ]),
    )
    await callback.answer()


@dp.message(Form.add_details, F.text)
async def add_details(message: Message, state: FSMContext):
    parts = [p.strip() for p in message.text.split("|")]
    if len(parts) < 2:
        await message.answer("Format: ID | Nomi yoki ID | Nomi | Barcode")
        return

    external_id, name = parts[0], parts[1]
    barcode = parts[2] if len(parts) > 2 else ""
    data = await state.get_data()
    images = data.get("images", [])

    try:
        async with loading_indicator(message):
            async with httpx.AsyncClient(timeout=120.0) as client:
                files = [("images", (f"img{i}.jpg", img, "image/jpeg")) for i, img in enumerate(images)]
                form_data = {"external_id": external_id, "name": name, "barcode": barcode}
                resp = await client.post(
                    f"{BACKEND_URL}/api/products/create/",
                    data=form_data,
                    files=files,
                )
                result = resp.json()
    except httpx.ConnectError:
        await message.answer("❌ Serverga ulanib bo'lmadi.")
        return

    await state.clear()

    if resp.status_code == 201:
        await message.answer(
            f"✅ Saqlandi!\n\n📦 {result['product']['name']}\n🆔 ID: {result['product']['external_id']}",
            reply_markup=main_menu(),
        )
    else:
        await message.answer(
            f"❌ {result.get('error', 'Xatolik')}",
            reply_markup=main_menu(),
        )


async def send_ai_result(message: Message, data: dict):
    status = data.get("status", "not_found")
    matches = data.get("matches", [])

    if status == "not_found" or not matches:
        text = "❌ Mahsulot topilmadi."
        best_pct = data.get("confidence_percent", 0)
        if best_pct and best_pct >= 50:
            text += f"\n\n(Eng yaqin: {best_pct}% — ishonchli emas)"
        await message.answer(text, reply_markup=main_menu())
        return

    top = matches[0]
    emoji = "✅" if status == "found" else "⚠️"
    label = STATUS_UZ.get(status, status)

    text = (
        f"{emoji} {label}\n\n"
        f"📦 Nomi: {top['name']}\n"
        f"🆔 ID: {top['external_id']}\n"
        f"📊 Moslik: {top['similarity_percent']}%"
    )
    await message.answer(text, reply_markup=main_menu())


@dp.message()
async def fallback(message: Message, state: FSMContext):
    current = await state.get_state()
    if current == Form.search.state:
        await message.answer("ID, nom yoki rasm yuboring.")
    elif current == Form.add_details.state:
        await message.answer("Format: ID | Nomi | Barcode")
    else:
        await message.answer("Menyudan tanlang:", reply_markup=main_menu())


async def main():
    tg_bot = get_bot()
    logger.info("Telegram bot ishga tushmoqda...")
    await dp.start_polling(tg_bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
