from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
import asyncio
from datetime import datetime, timedelta
import re
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import Message
from dotenv import load_dotenv
import os
import logging




load_dotenv()

bot = Bot(os.getenv('TOKEN'))
dp = Dispatcher()


# Создаем клавиатуру
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Мои задачи")],  # Одна кнопка в строке
    ],
    resize_keyboard=True  # Подгоняем размер клавиатуры под экран
)



# Словарь для хранения задач
tasks = {}  # Формат: {id: {"text": str, "deadline": datetime, "created_at": datetime}}



@dp.message(Command("start"))
async def start_handler(message: types.Message):
    welcome_text = """
👋 Привет! Я твой личный помощник для управления задачами.

Я помогу тебе:
✅ Добавлять задачи с дедлайнами
⏰ Напоминать о задачах заранее
📋 Показывать список всех задач
❌ Удалять ненужные задачи

Вот список доступных команд:
/add [задача] [дд.мм.гггг чч:мм] [минуты до напоминания] — добавить задачу с дедлайном и напоминанием
/tasks — посмотреть список задач
/delete [id] — удалить задачу
/completed [id] — отметить задачу как выполненную
/help — помощь

Начни с добавления задачи, например:
/add Купить молоко 25.10.2023 18:00 30
"""
    await message.answer(welcome_text, reply_markup=keyboard)# Передаем клавиатуру

    
@dp.message(F.text == "📋 Мои задачи")
async def handle_tasks_button(message: Message):
    # Вызываем функцию, которая показывает задачи
    await list_tasks(message)

@dp.message(Command("add"))
async def add_task(message: types.Message):
    try:
        command_content = message.text.removeprefix("/add ").strip()
        match = re.search(r"(.+?) (\d{2}\.\d{2}\.\d{4} \d{2}:\d{2})(?: (\d+))?$", command_content)
        
        if not match:
            raise ValueError("Неверный формат команды")
        
        task_text, deadline_str, reminder_minutes = match.groups()

        deadline = datetime.strptime(deadline_str, "%d.%m.%Y %H:%M")

        reminder_time = None
        if reminder_minutes:
            reminder_minutes = int(reminder_minutes)
            reminder_time = deadline - timedelta(minutes=reminder_minutes)

        task_id = len(tasks) + 1
        tasks[task_id] = {
            "text": task_text,
            "deadline": deadline,
            "created_at": datetime.now(),
            "user_id": message.from_user.id,
            "reminder_time": reminder_time,
            "completed": False,
        }

        logging.info(f"Добавлена задача: {tasks[task_id]}")

        await message.answer(
            f"✅ Задача добавлена: {task_text}\n🕒 Дедлайн: {deadline.strftime('%d.%m.%Y %H:%M')}"
            + (f"\n⏰ Напоминание за {reminder_minutes} минут до дедлайна" if reminder_minutes else "")
        )
    except (ValueError, IndexError) as e:
        logging.error(f"Ошибка при добавлении задачи: {e}")
        await message.answer(
            "❌ Ошибка в формате команды. Используйте: /add [задача] [дд.мм.гггг чч:мм] [минуты до напоминания]"
        )




@dp.message(Command("tasks"))
async def list_tasks(message: types.Message):
    if not tasks:
        await message.answer("У вас пока нет задач 😞")
        return

    task_list = []
    now = datetime.now()
    for task_id, task in tasks.items():
        # Проверяем, что задача принадлежит текущему пользователю
        if task["user_id"] == message.from_user.id:
            # Определяем статус задачи
            if task.get("completed", False):  # Если задача выполнена
                status = "✅ Выполнено"
            else:  # Если задача не выполнена
                status = (
                    f"⏳ Осталось: {str(task['deadline'] - now)}"
                    if task["deadline"] > now
                    else "❌ Просрочено"
                )
            task_list.append(
                f"{task_id}. {task['text']}\n   🕒 Дедлайн: {task['deadline'].strftime('%d.%m.%Y %H:%M')}\n   Статус: {status}"
            )
    await message.answer("📋 Ваши задачи:\n" + "\n\n".join(task_list))

@dp.message(Command("completed"))
async def completed_task(message: types.Message):
    try:
        # Получаем ID задачи из сообщения
        task_id = int(message.text.split(" ")[1])  # Формат: /completed [id]

        # Проверяем, существует ли задача с таким ID
        if task_id in tasks:
            # Проверяем, что задача принадлежит текущему пользователю
            if tasks[task_id]["user_id"] == message.from_user.id:
                # Отмечаем задачу как выполненную
                tasks[task_id]["completed"] = True
                await message.answer(f"✅ Задача с ID {task_id} отмечена как выполненная.")
            else:
                await message.answer("❌ Вы не можете отметить чужую задачу.")
        else:
            await message.answer("❌ Задача с таким ID не найдена.")
    except (IndexError, ValueError):
        # Если формат команды неверный
        await message.answer("❌ Используйте формат: /completed [id]")
    
    


@dp.message(Command("delete"))
async def delete_task(message: types.Message):
    try:
        task_id = int(message.text.split(" ")[1])  # Получаем ID задачи
        if task_id in tasks:
            del tasks[task_id]
            await message.answer(f"✅ Задача с ID {task_id} удалена.")
        else:
            await message.answer("❌ Задача с таким ID не найдена.")
    except (IndexError, ValueError):
        await message.answer("❌ Используйте формат: /delete [id]")


@dp.message(Command("help"))
async def help_handler(message: types.Message):
    help_text = """
📋 *Доступные команды:*

/add [задача] [дд.мм.гггг чч:мм] [напоминание за X минут]  
_Пример:_ `/add Позвонить маме 25.12.2023 18:00 30`

/tasks — список ваших задач  
/delete [ID] — удалить задачу  
/completed [ID] — отметить задачу как выполненную  
    """
    await message.answer(help_text, parse_mode=ParseMode.MARKDOWN)

        



logging.basicConfig(level=logging.INFO)

async def reminder_check():
    while True:
        now = datetime.now()
        logging.info(f"Проверка задач в {now}")
        if not tasks:
            logging.info("Нет задач для проверки.")
        else:
            for task_id, task in list(tasks.items()):
                logging.info(f"Проверка задачи {task_id}: {task}")
                logging.info(f"Дедлайн: {task['deadline']}, Напоминание: {task.get('reminder_time')}, Сейчас: {now}")
                
                # Проверка, что задача принадлежит пользователю и не выполнена
                if task["user_id"] and not task.get("completed", False):
                    # Уведомление о дедлайне
                    if task["deadline"] and task["deadline"] <= now:
                        logging.info(f"Отправка уведомления о дедлайне для задачи {task_id}")
                        await bot.send_message(
                            task["user_id"], f"🔔 Напоминание о задаче: {task['text']}"
                        )
                        # Удаляем задачу после уведомления (если нужно)
                        del tasks[task_id]
                    
                    # Уведомление о напоминании
                    elif task.get("reminder_time") and task["reminder_time"] <= now:
                        logging.info(f"Отправка напоминания для задачи {task_id}")
                        await bot.send_message(
                            task["user_id"], f"⏳ Не забудьте выполнить задачу: {task['text']}\nДедлайн: {task['deadline'].strftime('%d.%m.%Y %H:%M')}"
                        )
                        # Отключаем напоминание после отправки
                        task["reminder_time"] = None
        
        # Пауза между проверками
        await asyncio.sleep(10)
    



async def on_startup(dispatcher):
    asyncio.create_task(reminder_check())

if __name__ == "__main__":
    dp.run_polling(bot, on_startup=on_startup)