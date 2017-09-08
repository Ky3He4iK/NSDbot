# -*- coding: UTF-8 -*-
# python 3.5

from time import sleep  # загрузка паузы
from telebot import TeleBot  # загрузка бота
from threading import Thread  # загрузка дополнительного потока 
import config  # подключаем настройки
import constants  # подключаем константы
import datetime  # подключаем модуль
import requests  # подключаем запросы серваку

bot = TeleBot(config.token)  # инициализирую бота
begin_url = constants.begin_url + config.domain + constants.basic_path  # начальная часть адреса для обращений по API
null, false, true = None, False, True  # эти три переменные нужны для нормального парсинга ответа


def encrypt_password(password):
    # Как архивация уничтожением, только шифрование
    return '*' * len(password)


def load_access_key(login_sd):
    # Загружает из списка сотрудников ключ доступа нужного человека
    f = open("emp.db")
    text = f.read()[:-1]
    f.close()
    for line in text.splitlines():
        if line.split()[0] == login_sd:
            return line.split()[2]
    return None  # ничего не нашли. Возвращаем просто 0


def load_access_key_tg(tg_login):
    # Сначала ищет логин из sd по логину tg, потом возвращает нужный ключ доступа
    return load_access_key(load_sd_login(tg_login))


def load_emp_uuid(login_sd):
    # Загружает из списка сотрудников uuid нужного человека
    f = open("emp.db")
    text = f.read()[:-1]
    f.close()
    for line in text.splitlines():
        if line.split()[0] == login_sd:
            return line.split()[1]
    return None


def load_emp_uuid_tg(tg_login):
    # Сначала ищет логин из sd по логину tg, потом возвращает нужный uuid
    return load_access_key(load_sd_login(tg_login))


def load_sd_login(tg_login):
    # Ищет среди залогиненых пользователей нужный tg логин и возвращает sd логин искомого пользователя
    f = open('udata.db')
    text = f.read()[:-1]
    f.close()
    for line in text.splitlines():
        if line.split()[2] == tg_login:
            return line.split()[0]
    return None


def load_sd_login_access_key(access_key):
    # Выдаёт логин, к которому привязан ботом передаваемый ключ доступа
    f = open("emp.db")
    text = f.read()[:-1]
    f.close()
    for line in text.splitlines():
        if line.split()[2] == access_key:
            return line.split()[0]
    return None  # Нету такого


def get_access_key(login_sd):
    # возвращает рабочий ключ на 10 лет (чтоб наверняка)
    req = requests.post(begin_url + 'exec' + constants.access_key_base + config.access_key,
                        files=dict(script='return api.auth.getAccessKey("' + login_sd +
                                          '").setDeadlineDays(3653).uuid'),
                        verify=True)  # отправляем инфу
    if req.status_code == 200:  # если всё ОК
        return req.text  # возвращаем новый ключ
    return req.status_code  # если эта строчка выполняется, значит что-то пошло не так. Говорим статус сервака


def get_comments(uuid_service_call, login_sd):
    # Возвращает список комментариев к посту с данным uuid
    access_key = load_access_key(login_sd)
    if access_key is None:
        return None
    request = requests.get(begin_url + 'exec' + constants.access_key_base + access_key + 
                           '&func=modules.sdRest.listComments&params=' + uuid_service_call.split('$')[1] + ',user',
                           verify=True)
    # получаем список комментов
    global ll
    ll = []
    try:
        exec('global ll\nll = ' + request.text)
    except BaseException:
        return None
    return_list = []
    for com in ll:
        if com['author'] is None:
            com['author'] = 'SU'
        return_list.append([com['author'], com['text']])
    return return_list


def get_responsible(message):
    # Возвращает список запросов в ответственности данного пользователя
    log_in, lg_sd, access_key = check_user_for_login(message)
    if not log_in:
        return []
    request = requests.get(begin_url + 'find/serviceCall' + constants.access_key_base + access_key)

    global ll
    ll = []
    try:
        exec('global ll\nll = ' + request.text)  # превратили строку в массив
    except BaseException:
        send(message.text, "Оно само поломалось", message.chat.id)
        return None
    data = []
    uuid = load_emp_uuid_tg(message.from_user.username)
    for request in ll:
        if request['responsible'] != null and request['responsible']['UUID'] == uuid:
            data.append([str(request['number']), request['descriptionRTF'], str(request['clientName'])])
    return data  # выделили нужные запросы и запихали в массив


def get_reaction(message):
    # Возвращает список зарегестрированных запросов, требующих реакции
    log_in, lg_sd, access_key = check_user_for_login(message)
    if not log_in:
        return []
    request = requests.get(begin_url + 'find/serviceCall' + constants.access_key_base + access_key)
    # Получили список запросов (с поиском не смог разобраться)
    global ll
    ll = []
    try:
        exec('global ll\nll = ' + request.text)  # превратили строку в массив
    except BaseException:
        send(message.text, "Тебе не нужны запросы, требующие реакции", message.chat.id)
        return None
    data = []
    for request in ll:
        if request['state'] == "registered" and request['responsibleEmployee'] == null:
            data.append([str(request['number']), request['descriptionRTF'], str(request['clientName'])])
    return data  # выделили нужные запросы и запихали в массив


def get_request(message):
    # выдаёт запрос и данным номером
    log_in, lg_sd, access_key = check_user_for_login(message)
    if not log_in:
        return
    try:
        num = int(message.text)
    except ValueError:
        text = "Что-то пошло не так"  # святая истина
        send(message.text, text, message.chat.id)  # пишем в спортлото
        return
    request = requests.get(begin_url + 'find/serviceCall/' + constants.access_key_base + access_key, verify=True)
    global ll
    ll = {}
    try:
        exec('global ll\nll = ' + request.text)
    except BaseException:
        send(message.text, "Знаешь, мне надоело это всё", message.chat.id)
    for request in ll:
        if request['number'] == num:
            uuid = request['UUID']
            break
    else:
        send(message.text, "Не нашёл такого запроса", message.chat.id)
        return
    ll = {}
    request = requests.get(begin_url + 'get/' + uuid + constants.access_key_base +
                           access_key)
    try:
        exec('global ll\nll = ' + request.text)
    except BaseException:
        send(message.text, "Почему сервак возвращает чушь, а мне её переваривать?", message.chat.id)
    text = 'Тема: ' + ll['shortDescr'] + '\nОписание: ' + extract_text(ll['descriptionRTF']) + '\nДедлайн: ' + \
           ll['deadLineTime'] + \
           '\nВремя начала: ' + ll['startTime'] + '\nПроблема массы?: '
    if ll['massProblem']:
        text += 'нет'
    else:
        text += 'да'
    comments = get_comments(uuid, lg_sd)
    if comments is None:
        text += "\nКомментарии не нужны (на самом деле, просто поссорился с серваком)"
    else:
        comments = comments[:3]
        if len(comments) != 0:
            text += '\nПоследние комментарии:\n'
        else:
            text += '\nA комментариев нет'
        for com in comments:
            if com[0] == 'SU':
                line = 'SU'
            else:
                request = requests.get(begin_url + 'get/' + com[0] +
                                       constants.access_key_base + access_key,
                                       verify=True)  # получаем
                try:
                    exec('global ll\nll = ' + request.text)
                    line = ll['firstName'] + ' ' + ll['lastName']
                except BaseException:
                    line = "Чё? Чё? Кто? Кто это кинул? "
            text += line + ': ' + com[1] + '\n'
    send(message.text, text, message.chat.id)


def update_emp_uuid():
    # Обновляет список пользователей в sd
    f = open('emp.db')
    text = f.read()[:-1]
    f.close()
    login_list = []
    ids = []
    aks = []  # первоначальная инициализация

    for line in text.splitlines():
        ls = line.split()
        if len(ls) < 3:
            continue
        login_list.append(ls[0])
        ids.append(ls[1])
        aks.append(ls[2])
    control = [0] * len(ids)  # вынимаем данные из файла
    request = requests.get(begin_url + 'find/employee' + constants.access_key_base + config.access_key)
    if request.status_code != 200:
        print('error while update db')
        return

    global ll
    ll = []
    try:
        exec('global ll\nll = ' + request.text)  # превратили строку в массив
    except BaseException:
        print("Не люблю обновления и вам советую выдрать F5")
        return
    for emp in ll:
        try:
            tt = login_list.index(emp['login'])
            if ids[tt] != emp['UUID']:
                ids[tt], aks[tt], control[tt] = emp['UUID'], get_access_key(emp['login']), 1
        except ValueError:
            login_list.append(emp['login'])
            ids.append(emp['UUID'])
            aks.append(get_access_key(emp['login']))
            control.append(1)
    if sum(control) != 0:
        f = open('emp.db', 'w')
        for i in range(len(login_list)):
            # if control == 1:
            f.write(login_list[i] + ' ' + ids[i] + ' ' + aks[i] + '\n')
        f.close()  # проверяем на соответствие старых данных новым и обновляем, если надо


def check_login(login, password):
    # Проверяет правильность логинпароля
    payload = {'j_username': login, 'j_password': password}
    session = requests.session()
    for i in range(2):
        request = session.post(constants.begin_url + config.domain + '/sd/login', data=payload, verify=True)
        # Не понял почему, но только так работает
    session.close()
    if request.status_code == 200 or request.status_code == 302:  # Не надо обращать внимания на это предупреждение.
        # Всё будет на-а-армально
        return 0
    if request.status_code == 401:
        return 1
    return 2


def add_user_data(login_sd, uid, password, tg_login):
    # добавляем инфу о пользователе в свои хранилища. С проверкой на дублирования логина/чата.
    # Зачем храню пароль? для ФСБ. Правда, ключ - полное состояние вселенной в момент шифрации...
    password = encrypt_password(password)
    f = open('udata.db', 'r')
    text = f.read()[:-1]
    f.close()
    not_found = True
    f = open('udata.db', 'w')

    for line in text.splitlines():
        if line.split()[0] == login_sd or line.split()[3] == uid:
            if not_found:
                line = login_sd + ' ' + password + ' ' + tg_login + ' ' + str(uid)
                not_found = False
            else:
                continue
        f.write(line + '\n')  # если нужный логин/чат в первай раз - перезаписываем. Второй и далее - стираем.
        # Да, с двух аккаунтов tg в один sd нельзя зайти

    if not_found:
        f.write(login_sd + ' ' + password + ' ' + tg_login + ' ' + str(uid) + '\n')
    f.close()


def logging(mes):
    # Б.Б. внимательно записывает все твои действия, аноним
    # Сохраняет в файл с почасовым обновлением
    if mes == '':
        return
    if config.log_to_console:
        print(mes)
    f = open(str(datetime.datetime.today().strftime("%y:%m.%d-%Hh")) + '.log', 'a')
    # 20:08.14-88h.log - пример имени логов
    f.write(mes)
    f.close()


def form_main_mes(fr, inp, out):
    # создаёт сообщешние для Б.Б., в котором есть: кто писал, что писал и что ответил бот
    main_mes = ''
    if len(fr) > 0:
        main_mes = 'from: ' + fr + '\n'
    if len(inp) > 0:
        main_mes += "input:" + inp + '\n'
    if len(out) > 0:
        main_mes += "output:" + out + '\n'
    if len(main_mes) > 0:
        return 'time: ' + datetime.datetime.today().strftime("%M-%S:%f\n") + main_mes + '------\n'
    return ''


def send(inp, out, source, is_system=False, is_success=True):
    # отправляет сообщение кому надо для проверки
    # inp - входящее сообщение, out - исходящее, source - от кого, is_system - системное?,
    # is_success - успешно ли? (нужно всего один раз. Можно бы убрать)
    inp, out = str(inp), str(out)
    if source != str(source) and not is_system and len(out) > 0:
        bot.send_message(source, out)
    # отправили сообщение, теперь нужно его записать себе
    if config.logging_level == 4:
        return
    if is_system:
        if config.logging_level == 3:  # если ты Неуловимый Джо
            if is_success:
                is_success = 'ОК'
            else:  # иначе
                is_success = 'ОШИБКА'
            main_mes = form_main_mes(source, inp.split()[0], is_success)
        else:
            if source != str(source):  # если тип переменной source - не строка
                # думяю, есть другой способ это проверить, но и так сойдёт
                source = bot.get_chat(source).username
            main_mes = form_main_mes(source, inp, out)
    else:
        if source != str(source):
            source = bot.get_chat(source).username
        if config.logging_level == 0:  # mode 1984: on
            main_mes = form_main_mes(source, inp, out)
        elif config.logging_level == 1:
            main_mes = form_main_mes(source, inp.split()[0], out)
        else:
            main_mes = ''
    #  системное и обычное сообщнеия формируются немного по-разному
    logging(main_mes)  # не забывайте чистить логи


def extract_text(xml):
    # принимает на фход язык разметки и пытается вытащить текст оттуда
    text = xml
    while True:
        lo, lc, ro, rc = text.find('<'), text.find('>'), text.rfind('</'), text.rfind('>')
        if lo == -1 or lc == -1 or ro == -1 or rc == -1 or lo >= lc or lo >= ro or lo >= rc or lc >= ro or lc >= rc \
           or ro >= rc or text[lo + 1:lc].split()[0] != text[ro + 2:rc]:
            # от создателя решения "ферзей" через 1 if
            break
        else:
            text = text[:lo] + text[lc + 1:ro] + text[rc + 1:]
    return text


def check_user_for_login(message):
    # если этот пользователь не залогинен, сообщает об этом и программе, и пользователю
    lg_sd = load_sd_login(message.from_user.username)
    access_key = load_access_key(lg_sd)
    if lg_sd is None:
        send(message.text, 'Залогиньтесь, пожалуйста', message.chat.id)
        return [False, None, None]
    return [True, lg_sd, access_key]


@bot.message_handler(commands=['start'])
def reply_begin(message):
    # Просто краткая справка
    f = open('tgc.db')
    text = f.read()[:-1]
    f.close()
    for line in text.splitlines():
        if line == message.from_user.username + ' ' + str(message.chat.id):
            begin = 'Привет ещё раз.'
            break
    else:
        f = open('tgc.db', 'a')
        f.write(message.from_user.username + ' ' + str(message.chat.id) + '\n')
        f.close()
        begin = 'Привет.'
    send(message.text, begin + ' Для того, чтобы залогиниться используй комманду /login\n/help - вывести список'
                               ' всех комманд с кратким описанием\n/info - подробная помощь по комманде',
         message.chat.id)


@bot.message_handler(commands=['login'])
def reply_login(message):
    # Сообщает об успешности попытки залогиниться
    data = message.text.split()
    login, entry = None, False
    text = ""
    if len(data) == 3:
        ans = check_login(data[1], data[2])
        if ans == 0:  # если всё ОК
            add_user_data(data[1], message.chat.id, data[2], message.from_user.username)
            entry = True
            login = data[1]
        elif ans == 1:
            text = 'Неправильный логин/пароль'
        else:
            text = 'Что-то пошло не так'
    elif len(data) == 2:
        access_key = data[1]
        login = load_sd_login_access_key(access_key)
        if login is None:
            text = "Нет. Не тот"
        else:
            entry = True
            add_user_data(data[1], message.chat.id, "Я вообще не знаю пароль. Это не пароль. Нормальные системы "
                                                    "ограничивают длину пароля, а это уже выходит за рамки "
                                                    "дозволенного. Смекаешь? Нету тут никакого пароля, а просто фигня "
                                                    "всякая", message.from_user.username)
    else:
        text = 'Использование: /login <логин> <пароль>\nЛибо /login <access-key>'

    if entry:
        text = 'Добро пожаловать, '
        request = requests.get(begin_url + 'get/' + load_emp_uuid(login) + constants.access_key_base +
                               load_access_key(login))
        global ll
        ll = {}
        try:
            exec('global ll\nll = ' + request.text)  # об этой комманде уже написано выше
        except:
            send(message.text, "Короче, " + data[1] + ", Как тебя звать я не понял, но всё равно проходишь",
                 message.chat.id)
            return
        if ll['firstName'] is None:
            ll['firstName'] = ''
        if ll['middleName'] is None:
            ll['middleName'] = ''
        if ll['lastName'] is None:
            ll['lastName'] = ''
        # Вместо некрасивых None лагоничное отсутствие чего-либо
        # Именно лаГоничное. Без лагов скучно
        text += ll['firstName'] + ' ' + ll['middleName'] + ' ' + ll['lastName']
    send(message.text, text, message.chat.id)


@bot.message_handler(commands=['check'])
def reply(message):
    # сообщает логин sd этого пользователя
    login = message.from_user.username
    f = open('udata.db', 'r')
    text = f.read()[:-1]
    f.close()
    for line in text.splitlines():
        if line.split()[2] == login:
            send(message.text, "Вы залогинены как " + line.split()[0], message.chat.id)
            return
    send(message.text, "Для начала, нужно залогиниться в существующего пользователя", message.chat.id)


@bot.message_handler(commands=['gak'])
def reply(message):
    # возвращаем ключ пользователя
    log_in, lg_sd, access_key = check_user_for_login(message)
    if log_in:
        send(message.text, access_key, message.chat.id)


@bot.message_handler(commands=['cak'])
def reply(message):
    # проверяем годность ключа доступа
    ak = message.text.split()[1]
    request = requests.get(begin_url + 'check-status' + constants.access_key_base + ak)
    if request.text == 'Operation completed successfully':  # если вернуло ноль
        send(message.text, 'Годно', message.chat.id)
    else:
        send(message.text, 'Ключ - не торт', message.chat.id)


@bot.message_handler(commands=['quit'])
def reply(message):
    # Выходит из текущего пользователя
    log_in, lg_sd, access_key = check_user_for_login(message)
    if not log_in:
        return
    login = message.from_user.username
    f = open('udata.db')
    text = f.read()[:-1]
    f.close()
    is_ok = False
    f = open('udata.db', 'w')  # идём в магическую базу данных со сверхнадёжным шифрованием
    for line in text.splitlines():
        if line.split()[2] == login:
            send(message.text, "Всё прошло по плану", message.chat.id)
            is_ok = True
        else:
            f.write(line + '\n')
    f.close()  # надо бы использовать форму с автозакрытием, но эта на таб меньше места занимает
    if not is_ok:
        send(message.text, "Что-то пошло не так", message.chat.id)  # сообщаем


@bot.message_handler(commands=['help'])
def reply_help(message):
    # ПАМАГИТЯ!!!1!11
    titles = ['Сденано:\n', 'Не трогаю:\n', 'Info:\n']
    text_comp = ['\n'.join([str(i + 1) + '. ' + lis[i] for i in range(len(lis))]) for lis in constants.help_list]
    send('/help', '\n\n'.join([titles[i] + text_comp[i] for i in range(min(len(titles), len(text_comp)))]),
         message.chat.id)  # немного ужаса. Осталось регулярные выражения сюда как-нибудь добавить


@bot.message_handler(commands=['info'])
def reply_info(message):
    # ПАМАГИТЯ!!!1!11 v2.0
    if len(message.text) > len('/info '):
        mes = message.text.split()[1]
        try:
            text = '/' + mes + ': ' + constants.info_dict[mes]
        except KeyError:
            text = 'Такой комманды нет, либо помощь по ней не готова'
        send(message.text, text, message.chat.id)
    else:
        reply_help(message)


@bot.message_handler(commands=['comments'])
def reply(message):
    # выводит список комментов и их авторов
    log_in, lg_sd, access_key = check_user_for_login(message)
    if not log_in:
        return
    num = message.text.split()[1]
    try:
        num = int(num)
    except ValueError:
        send(message.text, 'Это не целое число', message.chat.id)
        return
    request = requests.get(begin_url + 'find/serviceCall/' + constants.access_key_base + access_key,
                           verify=True)
    if request.status_code != 200:
        send(message.text, 'Не найдено взамопонимание с сервером', message.chat.id)
        return
    global ll
    ll = []
    try:
        exec('global ll\nll = ' + request.text)
    except BaseException:
        send(message.text, "У меня обед", message.chat.id)
    for request in ll:
        if request['number'] == num:
            uuid = request['UUID']
            break
    else:
        send(message.text, "Не могу найти запрос с номером " + str(num), message.chat.id)
        return
    # Получили uuid нужного запроса (поиск ниасилил)

    text = ''
    com = get_comments(uuid, lg_sd)
    if com is None:
        text += "\nКомментарии не нужны (на самом деле, просто поссорился с серваком)"
    else:
        com = com[:50]
        text += "Последние 50 комментариев. Нужно ещё? Goto сайт\n"
        for comment in com:
            if comment[0] == 'SU':
                line = 'SU'
            else:
                request = requests.get(begin_url + 'get/' + comment[0] +
                                       constants.access_key_base + access_key,
                                       verify=True)  # получаем
                ll = {}
                try:
                    exec('global ll\nll = ' + request.text)
                    line = ll['firstName'] + ' ' + ll['lastName']
                except BaseException:
                    line = "В авторстве никто не признаётся"
            text += line + ': ' + comment[1] + '\n'
    send(message.text, text, message.chat.id)


@bot.message_handler(commands=['comment'])
def reply(message):
    # Отправление коммента
    log_in, lg_sd, access_key = check_user_for_login(message)
    if not log_in:
        return
    num = message.text.split()[1]
    com_text = message.text[message.text.find(num) + 2:]
    try:
        num = int(num)
    except ValueError:
        send(message.text, "Это не целое число", message.chat.id)
        return
    uuid = load_emp_uuid_tg(message.from_user.username)
    pl = {'number': num}
    request = requests.post(begin_url + 'find/serviceCall/' + constants.access_key_base + access_key, data=pl,
                            verify=True)
    if request.text == '[]':
        send(message.text, "Сервер вернул пустой ответ", message.chat.id)
        return
    global ll
    ll = []
    try:
        exec('global ll\nll = ' + request.text)
    except BaseException:
        send(message.text, "Плохой, негодный коммент", message.chat.id)
        return
    for request in ll:
        if request['number'] == num:
            suuid = request['UUID']  # похоже на суицид
            break
    else:
        send(message.text, "Не могу найти запрос с номером " + str(num), message.chat.id)
        return

    pl = {'author': uuid, 'source': suuid, 'text': com_text}
    request = requests.post(begin_url + 'create/comment/' + constants.access_key_base + access_key, data=pl,
                            verify=True)
    if request.status_code == 201:
        send(message.text, 'Комментарий был создан успешно', message.chat.id)
    else:
        send(message.text, 'Ошибка номер ' + request.status_code, message.chat.id)


@bot.message_handler(commands=['responsible'])
def reply(message):
    # Выдаёт список запросов в ответственности
    text = get_responsible(message)
    if text is None:
        return
    elif not text:
        send(message.text, 'Вы не имеете в ответственности запросов', message.chat.id)
    else:
        adj_text = '*Описания, содержащие знаки <, >, </ и > могут работать некорректно.\n/raw_responsible для ' \
                   'отображения без удаления разметки'
        send(message.text, '\n'.join(line[0] + ': ' + extract_text(line[1]) + '\nclient:\n' + line[2] + '\n\n'
                                     for line in list(text)) + adj_text, message.chat.id)


@bot.message_handler(commands=['raw_responsible'])
def reply(message):
    # Выдаёт список запросов в ответственности, без обработки разметки
    text = get_responsible(message)
    if text is None:
        return
    elif not text:
        send(message.text, 'Вы не имеете в ответственности запросов', message.chat.id)
    else:
        send(message.text, '\n'.join(line[0] + ': ' + line[1] + '\nclient:\n' + line[2] + '\n\n'
                                     for line in list(text)), message.chat.id)


@bot.message_handler(commands=['reaction'])
def reply(message):
    # Выдаёт список запросов, требующих реакции
    text = get_reaction(message)
    if text is None:
        return
    elif not text:
        send(message.text, 'Очередь слишком короткая, чтобы её обрабатывать', message.chat.id)
    else:
        adj_text = '*Описания, содержащие знаки <, >, </ и > могут работать некорректно.\n/raw_reaction для ' \
                   'отображения без удаления разметки'
        send(message.text, '\n'.join(line[0] + ': ' + extract_text(line[1]) + '\nclient:\n' + line[2] + '\n\n'
                                     for line in list(text)) + adj_text, message.chat.id)


@bot.message_handler(commands=['raw_reaction'])
def reply(message):
    # Выдаёт список запросов, требующих реакции, без обработки разметки
    text = get_reaction(message)
    if text is None:
        return
    if not text:
        send(message.text, 'Очередь слишком короткая, чтобы её обрабатывать', message.chat.id)
    else:
        send(message.text, '\n'.join(line[0] + ': ' + line[1] + '\nclient:\n' + line[2] + '\n\n'
                                     for line in list(text)), message.chat.id)


@bot.message_handler(commands=['replast'])
def reply(message):
    # /responsible с ограничением по времени
    log_in, lg_sd, access_key = check_user_for_login(message)
    if not log_in:
        return
    if len(message.text.split()) == 1:
        left_time = 24
    else:
        try:
            left_time = int(message.text.split()[1])
        except ValueError:
            send(message.text, "Неправильно вводишь", message.chat.id)
            return
    uuid = load_emp_uuid_tg(message.from_user.username)
    rq_list = []
    min_time = datetime.datetime.today().timestamp() - left_time * 3600
    request = requests.get(begin_url + 'find/serviceCall' + constants.access_key_base + access_key)
    global ll
    ll = []
    try:
        exec('global ll\nll = ' + request.text)
    except BaseException:
        send(message.text, "Ты не готов к этой информации", message.chat.id)
        return
    for request in ll:
        if request['responsible'] != null and request['responsible']['UUID'] == uuid:
            current_time = datetime.datetime.strptime(request['startTime'], "%Y.%m.%d %H:%M:%S").timestamp()
            if current_time >= min_time:
                rq_list.append([request['number'], request['shortDescr'], extract_text(request['descriptionRTF'])[:50]])
                if len(rq_list) == 50:
                    break

    text = ''
    for rq in rq_list:
        text += str(rq[0]) + '. ' + rq[1] + ': ' + rq[2] + '\n'
    if text == '':
        send(message.text, 'За последние ' + str(left_time) + ' часа ничего не было', message.chat.id)
    else:
        send(message.text, text, message.chat.id)


@bot.message_handler(commands=['request'])
def reply(message):
    if len(message.text.split()) == 2:
        message.text = message.text.split()[1]
        get_request(message)
    else:
        send(message.text, "Не надо так", message.chat.id)


@bot.message_handler(content_types=['text'])
def reply_number(message):
    get_request(message)


# если сообщение не обработалось
@bot.message_handler()
def reply_finally(message):
    # Последняя линия обработки
    send(message.text, "Моя твоя не понимать", message.chat.id)


# функция одного действия
def bot_thread():
    while qwe:  # как будто цикл конечный
        try:
            bot.polling(none_stop=False)  # при False есть шанс, что бот остановится безболезнено
        except BaseException as err:
            print("Error while bot work:\n", err, '\nWith args:\n', err.args)
            print("Restarting")
            sleep(20)


if __name__ == '__main__':
    open('udata.db', 'a').close()
    open('emp.db', 'a').close()
    open('tgc.db', 'a').close()
    r = requests.get(begin_url + 'check-status')
    while r.status_code != 200:   # пока недоступно
        print('Не вижу сервак. Через минуту попробую переподключиться')
        sleep(60)  # ждём минуту
        r = requests.get(begin_url + 'check-status')
        # проверяем доступность снова и снова
    update_emp_uuid()
    send('start', 'started', '', True)  # СТАРТУЕМ, я сказал СТАРТУЕМ
    global qwe   # я не совсем понял,
    qwe = True  # почему работает только так
    t = Thread(target=bot_thread)  # делаем поток
    t.daemon = True  # это демон!
    t.start()  # нечинаем
    while True:  # бесконечный цикл
        s = input()  # что-нибудь вводим
        if s == 'stop':  # Работает с маленьким шансом
            qwe = False  # попытка - не пытка
            t.join(5)  # вдруг получилось
            send('stop', 'stopped', '', True, not t.is_alive())  # сообщаем
            break  # и сматываемся
        elif s == 'exit!':  # кувалдой по системнику
            send('exit!', 'EMERGENCY STOPPING THE PROGRAM!!!', '', True)  # говорим
            print(0 / 0)  # точно сработает?
            print("WTF????")  # если не сработало
            break  # валим
        else:
            try:
                exec(input())
            except BaseException as e:
                print(e)
        if not t.is_alive():
            c = input("Restarting")
            break

# нужно добавить уведомление о новых запросах посреди ночи
