import os; os.system('pip install vk_api')
import os
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import threading
import time
from datetime import datetime
import json

print("СТАРТ 1: Бот начал загружаться...")

GROUP_TOKEN = "vk1.a.tLPrx7XL95lpFV12NeHF3QuGuO9I80EWVg4-6qk8rQhzyFgPBsnR8unknHnPW6_1imhma3KcmL4sKFiYRQ9UaDs_qsziZbsP1dYS9UBlphjyQmaVL5TCOdS-q8-UR2M-4ToDEWyNUSIrAbAjq1Ee4ZLp0KslSpmTBitKrF8JaZnPFksCVy0KYHJENpTpc_hJ4Hg5BYw-ErSxNE1pzn0H4A"
GROUP_ID = 240887444

print("СТАРТ 2: Токен и ID загружены.")
print(f"Токен (первые 10 символов): {GROUP_TOKEN[:10]}...")
print(f"ID группы: {GROUP_ID}")

ADMINS = [479753606]
TIME_TO_ACCEPT = 60
TIME_TO_IDLE = 120
DATA_FILE = "estafeta_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

chats = load_data()

print("СТАРТ 3: Данные загружены. Пытаюсь подключиться к VK...")

try:
    vk_session = vk_api.VkApi(token=GROUP_TOKEN)
    print("СТАРТ 4: VkApi создан.")
    vk = vk_session.get_api()
    print("СТАРТ 5: API получен.")
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)
    print("СТАРТ 6: LongPoll запущен.")
except Exception as e:
    print("КРИТИЧЕСКАЯ ОШИБКА ПРИ ПОДКЛЮЧЕНИИ К ВК:")
    print(str(e))
    exit()

def send(chat_id, text):
    try:
        vk.messages.send(peer_id=chat_id, message=text, random_id=0)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def send_mention_all(chat_id, text):
    try:
        members = vk.messages.getConversationMembers(peer_id=chat_id)
        mentions = []
        for item in members['items']:
            uid = item['member_id']
            if uid > 0:
                mentions.append(f"[id{uid}|]")
        message = " ".join(mentions) + "\n" + text
        vk.messages.send(peer_id=chat_id, message=message, random_id=0)
    except Exception as e:
        print(f"Ошибка упоминания: {e}")
        send(chat_id, text)

def get_user_name(user_id):
    try:
        user = vk.users.get(user_ids=user_id)[0]
        return f"{user['first_name']} {user['last_name']}"
    except:
        return f"User{user_id}"

def init_chat(chat_id):
    if str(chat_id) not in chats:
        chats[str(chat_id)] = {
            'holder': None, 'time': None, 'penalty': {}, 'pending': None, 'pending_time': None, 'last_activity': None
        }
        save_data(chats)

def set_holder(chat_id, user_id):
    chat_key = str(chat_id)
    init_chat(chat_id)
    chats[chat_key]['holder'] = user_id
    chats[chat_key]['time'] = datetime.now().isoformat()
    chats[chat_key]['pending'] = None
    chats[chat_key]['pending_time'] = None
    chats[chat_key]['last_activity'] = datetime.now().isoformat()
    save_data(chats)

def set_pending(chat_id, from_user, to_user):
    chat_key = str(chat_id)
    init_chat(chat_id)
    chats[chat_key]['pending'] = to_user
    chats[chat_key]['pending_time'] = datetime.now().timestamp()
    chats[chat_key]['last_activity'] = datetime.now().isoformat()
    save_data(chats)

def get_holder(chat_id):
    return chats[str(chat_id)]['holder'] if str(chat_id) in chats else None

def get_pending(chat_id):
    return chats[str(chat_id)]['pending'] if str(chat_id) in chats else None

def add_penalty(chat_id, user_id):
    init_chat(chat_id)
    chat_key = str(chat_id)
    if str(user_id) not in chats[chat_key]['penalty']:
        chats[chat_key]['penalty'][str(user_id)] = 0
    chats[chat_key]['penalty'][str(user_id)] += 1
    save_data(chats)

def get_penalty(chat_id, user_id):
    chat_key = str(chat_id)
    if chat_key in chats and str(user_id) in chats[chat_key]['penalty']:
        return chats[chat_key]['penalty'][str(user_id)]
    return 0

def clear_penalties(chat_id, user_id=None):
    chat_key = str(chat_id)
    if chat_key not in chats:
        return "❌ Нет данных о штрафах"
    if user_id:
        if str(user_id) in chats[chat_key]['penalty']:
            del chats[chat_key]['penalty'][str(user_id)]
            save_data(chats)
            return f"✅ Штрафы {get_user_name(user_id)} очищены"
        return f"❌ У пользователя нет штрафов"
    else:
        chats[chat_key]['penalty'] = {}
        save_data(chats)
        return "✅ Все штрафы очищены"

def show_penalties(chat_id):
    chat_key = str(chat_id)
    if chat_key not in chats or not chats[chat_key]['penalty']:
        return "📊 Штрафов пока нет"
    text = "📊 СПИСОК ШТРАФОВ:\n"
    for uid, count in chats[chat_key]['penalty'].items():
        uid = int(uid)
        if count > 0:
            text += f"• {get_user_name(uid)}: {count} штраф(ов)\n"
    return text

def is_admin(user_id):
    return user_id in ADMINS

def timer_check():
    while True:
        time.sleep(30)
        now = datetime.now()
        now_timestamp = now.timestamp()
        for chat_id_str, data in list(chats.items()):
            chat_id = int(chat_id_str)
            if data['pending'] and data['pending_time']:
                if now_timestamp - data['pending_time'] >= (TIME_TO_ACCEPT * 60):
                    user_id = data['pending']
                    add_penalty(chat_id, user_id)
                    penalty = get_penalty(chat_id, user_id)
                    data['pending'] = None
                    data['pending_time'] = None
                    data['last_activity'] = now.isoformat()
                    save_data(chats)
                    send(chat_id, f"⚠️ {get_user_name(user_id)} НЕ ПРИНЯЛ ЭСТАФЕТУ!\n📊 Штраф +1 (всего: {penalty})\n🏃 Эстафета свободна! Напишите !принять")
            if data['last_activity']:
                try:
                    last_time = datetime.fromisoformat(data['last_activity'])
                    if (now - last_time).total_seconds() >= (TIME_TO_IDLE * 60):
                        data['holder'] = None
                        data['time'] = None
                        data['pending'] = None
                        data['pending_time'] = None
                        data['last_activity'] = now.isoformat()
                        save_data(chats)
                        send_mention_all(chat_id, "⏰ Эстафета не бралась 2 часа, возьмите чтобы избежать наказаний!\nНапишите !принять")
                except:
                    pass

thread = threading.Thread(target=timer_check, daemon=True)
thread.start()

print("СТАРТ 7: Бот готов к работе!")
print("🤖 БОТ ЭСТАФЕТА ЗАПУЩЕН!")
print(f"📱 Админ: {ADMINS[0]}")
print(f"⏰ Время на принятие: {TIME_TO_ACCEPT} минут")
print(f"⏰ Время бездействия: {TIME_TO_IDLE} минут")
print("⏳ Ожидание сообщений...")

while True:
    try:
        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                msg = event.obj.message
                chat_id = msg.peer_id
                user_id = msg.from_id
                text = msg.text.lower().strip()
                if user_id < 0:
                    continue
                init_chat(chat_id)
                chat_key = str(chat_id)
                if text == "!принять":
                    if chats[chat_key]['pending'] == user_id:
                        set_holder(chat_id, user_id)
                        send(chat_id, f"✅ {get_user_name(user_id)} ПРИНЯЛ ЭСТАФЕТУ!\n📝 Команды: !передать @Имя, !уступить, !штрафы")
                    else:
                        if get_holder(chat_id) is None and chats[chat_key]['pending'] is None:
                            set_holder(chat_id, user_id)
                            send(chat_id, f"✅ {get_user_name(user_id)} ВЗЯЛ ЭСТАФЕТУ!")
                        else:
                            holder = get_holder(chat_id)
                            if holder:
                                send(chat_id, f"❌ Эстафета уже у {get_user_name(holder)}")
                            else:
                                send(chat_id, "❌ Эстафета уже кому-то передана! Дождитесь, когда её примут")
                elif text.startswith("!передать ") or text.startswith("!передаю "):
                    if get_holder(chat_id) != user_id:
                        send(chat_id, "❌ Эстафета не у вас!")
                        continue
                    if chats[chat_key]['pending'] is not None:
                        send(chat_id, "❌ Вы уже передали эстафету кому-то! Дождитесь ответа")
                        continue
                    parts = text.split(maxsplit=1)
                    if len(parts) < 2:
                        send(chat_id, "❌ Напишите: !передать @Имя")
                        continue
                    target_name = parts[1].strip()
                    try:
                        members = vk.messages.getConversationMembers(peer_id=chat_id)
                        found = None
                        for item in members['items']:
                            uid = item['member_id']
                            if uid > 0 and uid != user_id:
                                user = vk.users.get(user_ids=uid)[0]
                                full_name = f"{user['first_name']} {user['last_name']}".lower()
                                if target_name.lower() in full_name or target_name in str(uid):
                                    found = uid
                                    break
                        if found:
                            set_pending(chat_id, user_id, found)
                            send(chat_id, f"📤 {get_user_name(user_id)} ПЕРЕДАЁТ ЭСТАФЕТУ {get_user_name(found)}!\n⏰ У {get_user_name(found)} есть {TIME_TO_ACCEPT} минут, чтобы написать !принять")
                            try:
                                vk.messages.send(
                                    user_id=found,
                                    message=f"🏃 Вам передают эстафету в беседе!\nНапишите !принять в чате, чтобы взять её.\n⏰ У вас есть {TIME_TO_ACCEPT} минут, иначе штраф!"
                                )
                            except:
                                pass
                        else:
                            send(chat_id, "❌ Участник не найден")
                    except Exception as e:
                        send(chat_id, f"❌ Ошибка: {str(e)}")
                elif text == "!уступить":
                    if get_holder(chat_id) != user_id:
                        send(chat_id, "❌ Эстафета не у вас!")
                        continue
                    add_penalty(chat_id, user_id)
                    penalty = get_penalty(chat_id, user_id)
                    chats[chat_key]['holder'] = None
                    chats[chat_key]['time'] = None
                    chats[chat_key]['pending'] = None
                    chats[chat_key]['pending_time'] = None
                    chats[chat_key]['last_activity'] = datetime.now().isoformat()
                    save_data(chats)
                    send(chat_id, f"⚠️ {get_user_name(user_id)} УСТУПИЛ ЭСТАФЕТУ!\n📊 Штраф +1 (всего: {penalty})\n🏃 Эстафета свободна! Напишите !принять")
                elif text == "!штрафы":
                    send(chat_id, show_penalties(chat_id))
                elif text == "!статус":
                    holder = get_holder(chat_id)
                    pending = get_pending(chat_id)
                    if holder:
                        send(chat_id, f"🏃 Эстафета у {get_user_name(holder)}")
                    elif pending:
                        send(chat_id, f"⏳ Эстафета передана {get_user_name(pending)}\n⏰ Ожидает принятия...")
                    else:
                        send(chat_id, "🏃 Эстафета свободна! Напишите !принять")
                elif text == "!помощь":
                    help_text = f"""📖 ДОСТУПНЫЕ КОМАНДЫ:

🔹 Основные:
!принять - взять эстафету
!передать @Имя - передать эстафету
!уступить - отказаться (+штраф)
!штрафы - посмотреть всех
!статус - кто держит

🔹 Админские:
!очистить_штрафы - очистить все штрафы в чате
!очистить_штрафы @Имя - очистить штрафы конкретного

⚠️ Правила:
- При передаче эстафеты нужно принять её за {TIME_TO_ACCEPT} минут
- Игнорирование = штраф +1
- Если 2 часа бездействия - сообщение @all"""
                    send(chat_id, help_text)
                elif text.startswith("!очистить_штрафы"):
                    if not is_admin(user_id):
                        send(chat_id, "❌ Только админ может очищать штрафы!")
                        continue
                    parts = text.split(maxsplit=1)
                    if len(parts) < 2:
                        result = clear_penalties(chat_id)
                        send(chat_id, result)
                    else:
                        target_name = parts[1].strip()
                        try:
                            members = vk.messages.getConversationMembers(peer_id=chat_id)
                            found = None
                            for item in members['items']:
                                uid = item['member_id']
                                if uid > 0:
                                    user = vk.users.get(user_ids=uid)[0]
                                    full_name = f"{user['first_name']} {user['last_name']}".lower()
                                    if target_name.lower() in full_name or target_name in str(uid):
                                        found = uid
                                        break
                            if found:
                                result = clear_penalties(chat_id, found)
                                send(chat_id, result)
                            else:
                                send(chat_id, "❌ Участник не найден")
                        except Exception as e:
                            send(chat_id, f"❌ Ошибка: {str(e)}")
                else:
                    if chat_key in chats:
                        chats[chat_key]['last_activity'] = datetime.now().isoformat()
                        save_data(chats)
    except Exception as e:
        print(f"Ошибка: {e}")
        time.sleep(10)
