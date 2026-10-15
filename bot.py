import asyncio
import os

from aiosplus import Bot, Dispatcher
from aiosplus.filters import Command
from aiosplus.types import Message

TOKEN = "69954493:fOqbkUfpTZOilid0N5nVvlcMLz-qKWyKZOM"

ADMIN_USERNAME = "@User_ligo"
START_FILE = "start_text.txt"
USERS_FILE = "users.txt"

DEFAULT_START = (
    "سلام 👋\n"
    "به ربات تبدیل ویدئو به Video Message خوش آمدید 🎥\n\n"
    "ابتدا در کانال ما عضو شوید و سپس یک ویدئو برای من ارسال کنید "
    "تا آن را به Video Message تبدیل کنم. 🔄"
)

bot = Bot(token=TOKEN)
dp = Dispatcher()

waiting_for_start_text = False
waiting_for_broadcast_text = False


def get_start_text():
    if os.path.exists(START_FILE):
        with open(START_FILE, "r", encoding="utf-8") as f:
            return f.read()

    with open(START_FILE, "w", encoding="utf-8") as f:
        f.write(DEFAULT_START)

    return DEFAULT_START


def is_admin(message):
    username = getattr(message.from_user, "username", None)

    if username and not username.startswith("@"):
        username = "@" + username

    return username is not None and username.lower() == ADMIN_USERNAME.lower()


def save_user(chat_id):
    users = load_users()

    if str(chat_id) not in users:
        with open(USERS_FILE, "a", encoding="utf-8") as f:
            f.write(f"{chat_id}\n")


def load_users():
    if not os.path.exists(USERS_FILE):
        return []

    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


@dp.message(Command("start"))
async def start_handler(message: Message):
    save_user(message.chat.id)
    await message.answer(get_start_text())


@dp.message(Command("setstart"))
async def setstart_handler(message: Message):
    global waiting_for_start_text

    if not is_admin(message):
        return

    waiting_for_start_text = True

    await message.answer(
        "✏️ متن جدید استارت را ارسال کنید.\n\n"
        "برای لغو: /cancel"
    )


@dp.message(Command("broadcast"))
async def broadcast_handler(message: Message):
    global waiting_for_broadcast_text

    if not is_admin(message):
        return

    waiting_for_broadcast_text = True

    await message.answer(
        "📢 متن اطلاعیه را ارسال کنید تا برای همه کاربران فرستاده شود.\n\n"
        "برای لغو: /cancel"
    )


@dp.message(Command("cancel"))
async def cancel_handler(message: Message):
    global waiting_for_start_text, waiting_for_broadcast_text

    if not is_admin(message):
        return

    waiting_for_start_text = False
    waiting_for_broadcast_text = False
    await message.answer("❌ عملیات لغو شد.")


@dp.message(Command("starttext"))
async def starttext_handler(message: Message):
    if not is_admin(message):
        return

    await message.answer(
        "📋 متن فعلی استارت:\n\n"
        + get_start_text()
    )


@dp.message(Command("stats"))
async def stats_handler(message: Message):
    if not is_admin(message):
        return

    users = load_users()

    await message.answer(f"📊 آمار:\n👥 کاربران: {len(users)}")


@dp.message()
async def message_handler(message: Message):
    global waiting_for_start_text, waiting_for_broadcast_text

    if is_admin(message) and waiting_for_start_text and message.text:
        waiting_for_start_text = False

        with open(START_FILE, "w", encoding="utf-8") as f:
            f.write(message.text)

        await message.answer("✅ متن استارت با موفقیت تغییر کرد!")
        return

    if is_admin(message) and waiting_for_broadcast_text and message.text:
        waiting_for_broadcast_text = False

        users = load_users()
        success = 0
        failed = 0

        await message.answer(f"⏳ در حال ارسال به {len(users)} کاربر...")

        for user_id in users:
            try:
                await bot.send_message(chat_id=int(user_id), text=message.text)
                success += 1
            except Exception as e:
                print("BROADCAST ERROR:", user_id, e)
                failed += 1

            await asyncio.sleep(0.05)

        await message.answer(
            f"✅ اطلاعیه ارسال شد.\n"
            f"موفق: {success}\n"
            f"ناموفق: {failed}"
        )
        return

    if not message.video:
        return

    await message.answer("⏳ ویدئو دریافت شد، دارم تبدیلش می‌کنم...")

    input_file = f"input_{message.message_id}.mp4"
    output_file = f"output_{message.message_id}.mp4"

    try:
        file = await bot.get_file(message.video.file_id)

        await bot.download_file(file, input_file)

        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", input_file,
            "-vf",
            "scale=720:720:force_original_aspect_ratio=increase,crop=720:720",
            "-r", "30",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "26",
            "-c:a", "aac",
            "-movflags", "+faststart",
            output_file
        )
        await process.wait()

        if process.returncode != 0:
            raise Exception("ffmpeg failed")

        await bot.send_video_note(
            chat_id=message.chat.id,
            video_note=output_file
        )

        await message.answer("✅ آماده شد!")

    except Exception as e:
        print("ERROR:", e)
        await message.answer("❌ هنگام تبدیل ویدئو مشکلی پیش آمد.")

    finally:
        if os.path.exists(input_file):
            os.remove(input_file)

        if os.path.exists(output_file):
            os.remove(output_file)


async def main():
    print("Bot is running...")
    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
