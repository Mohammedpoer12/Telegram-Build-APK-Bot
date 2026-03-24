import os
import asyncio
import logging
import zipfile
import shutil
import uuid
import aiohttp
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from workflows import get_workflow

# الإعدادات الأساسية (سيتم استخدامها إذا لم توجد في البيئة)
API_TOKEN = os.getenv('BOT_TOKEN', '8710351440:AAEBzObbsMq7uWZNBkmU7ev1rQidhCikb5c')
ADMIN_ID = 8247555045
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', 'YOUR_GITHUB_TOKEN_HERE')
GITHUB_USER = os.getenv('GITHUB_USER', 'Mohammedpoer12')

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("⚠️ عذراً، هذا البوت مخصص للأدمن فقط.")
        return
    
    welcome_text = (
        "🤖 **أهلاً بك في بوت البناء التلقائي!**\n\n"
        "البوت جاهز الآن للعمل. كل ما عليك فعله هو:\n"
        "1️⃣ إرسال ملف مشروعك بصيغة ZIP.\n"
        "2️⃣ أو إرسال رابط مستودع GitHub الخاص بك.\n\n"
        "سأقوم فوراً ببدء عملية التحويل وإرسال ملف APK إليك عند الانتهاء. 🚀"
    )
    await message.answer(welcome_text, parse_mode="Markdown")

@dp.message(F.document)
async def handle_docs(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    if not message.document.file_name.endswith('.zip'):
        await message.reply("❌ يرجى إرسال ملف مضغوط بصيغة .zip فقط.")
        return

    msg = await message.answer("📥 **استلمت الملف! جاري التحميل والبدء في البناء...**", parse_mode="Markdown")
    
    unique_id = str(uuid.uuid4())[:8]
    work_dir = f"work_{unique_id}"
    os.makedirs(work_dir, exist_ok=True)
    
    file = await bot.get_file(message.document.file_id)
    zip_path = os.path.join(work_dir, "project.zip")
    await bot.download_file(file.file_path, zip_path)
    
    extract_path = os.path.join(work_dir, "extracted")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    
    # تصحيح مسار الاستخراج إذا كان هناك مجلد فرعي واحد
    items = os.listdir(extract_path)
    if len(items) == 1 and os.path.isdir(os.path.join(extract_path, items[0])):
        final_path = os.path.join(extract_path, items[0])
    else:
        final_path = extract_path

    await process_build(message, msg, final_path, unique_id, work_dir)

@dp.message(F.text.regexp(r'https?://github\.com/[\w-]+/[\w-]+'))
async def handle_github_link(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    repo_url = message.text.strip()
    msg = await message.answer("🔗 **استلمت الرابط! جاري سحب المشروع والبدء في البناء...**", parse_mode="Markdown")
    
    unique_id = str(uuid.uuid4())[:8]
    work_dir = f"work_{unique_id}"
    os.makedirs(work_dir, exist_ok=True)
    
    extract_path = os.path.join(work_dir, "extracted")
    # استخدام git clone لسحب المشروع
    os.system(f"git clone {repo_url} {extract_path}")
    
    await process_build(message, msg, extract_path, unique_id, work_dir)

async def process_build(message, msg, path, unique_id, work_dir):
    project_type = detect_project_type(path)
    await msg.edit_text(f"🔍 **نوع المشروع المكتشف:** {project_type}\n🚀 **جاري الرفع والبدء في GitHub Actions...**", parse_mode="Markdown")

    repo_name = f"build-apk-{unique_id}"
    success = await create_and_push_to_github(repo_name, path, project_type)
    
    if not success:
        await msg.edit_text("❌ **فشل في عملية الرفع.** يرجى التأكد من صلاحيات GitHub Token.")
        shutil.rmtree(work_dir)
        return

    await msg.edit_text(f"⚙️ **جاري البناء الآن...**\nسأرسل لك الملف فور جهوزه (عادةً يستغرق 5-10 دقائق).", parse_mode="Markdown")
    
    apk_url = await wait_for_github_action(repo_name)
    
    if apk_url:
        await msg.edit_text("✅ **اكتمل البناء بنجاح! جاري تحضير الملف للإرسال...**", parse_mode="Markdown")
        apk_file_path = os.path.join(work_dir, "app-release.zip")
        await download_file(apk_url, apk_file_path)
        await message.answer_document(FSInputFile(apk_file_path), caption="📦 **تفضل! ملف APK الخاص بك جاهز.**", parse_mode="Markdown")
    else:
        await msg.edit_text("❌ **فشل بناء APK.** يرجى مراجعة سجلات GitHub Actions في حسابك.")

    await delete_github_repo(repo_name)
    shutil.rmtree(work_dir)

def detect_project_type(path):
    files = os.listdir(path)
    if 'pubspec.yaml' in files: return "Flutter"
    if 'package.json' in files: return "React Native"
    if 'build.gradle' in files or ('app' in files and os.path.exists(os.path.join(path, 'app', 'build.gradle'))):
        return "Android Native"
    return "Web (HTML)"

async def create_and_push_to_github(repo_name, path, project_type):
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    async with aiohttp.ClientSession() as session:
        async with session.post("https://api.github.com/user/repos", headers=headers, json={"name": repo_name, "private": True}) as resp:
            if resp.status != 201: return False
        
        os.system(f"cd {path} && rm -rf .git && git init && git config user.email 'bot@example.com' && git config user.name 'BuildBot'")
        workflow_content = get_workflow(project_type)
        os.makedirs(os.path.join(path, ".github/workflows"), exist_ok=True)
        with open(os.path.join(path, ".github/workflows/build.yml"), "w") as f:
            f.write(workflow_content)
            
        os.system(f"cd {path} && git add . && git commit -m 'Build request' && git branch -M main")
        remote_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_USER}/{repo_name}.git"
        os.system(f"cd {path} && git remote add origin {remote_url} && git push -u origin main")
    return True

async def wait_for_github_action(repo_name):
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    async with aiohttp.ClientSession() as session:
        for _ in range(90): # زيادة الوقت لـ 15 دقيقة
            async with session.get(f"https://api.github.com/repos/{GITHUB_USER}/{repo_name}/actions/runs", headers=headers) as resp:
                data = await resp.json()
                if data.get("total_count", 0) > 0:
                    run = data["workflow_runs"][0]
                    if run["status"] == "completed":
                        if run["conclusion"] == "success":
                            async with session.get(run["artifacts_url"], headers=headers) as art_resp:
                                art_data = await art_resp.json()
                                if art_data["total_count"] > 0:
                                    return art_data["artifacts"][0]["archive_download_url"]
                        return None
            await asyncio.sleep(10)
    return None

async def delete_github_repo(repo_name):
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    async with aiohttp.ClientSession() as session:
        await session.delete(f"https://api.github.com/repos/{GITHUB_USER}/{repo_name}", headers=headers)

async def download_file(url, path):
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                with open(path, "wb") as f: f.write(await resp.read())

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
