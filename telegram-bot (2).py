import telebot as tl
import requests
import json
from telebot import *
import sqlite3 as sql


token = "7625785988:AAGYt_LuqUls_YQe2JkrO84RPJgnf8m5Ojc"

bot = tl.TeleBot(token)

def Open_The_Door(message, intercom_id, door_id=0):
    url = f"https://domo-dev.profintel.ru/tg-bot/domo.domofon/{intercom_id}/open?domofon_id={intercom_id}&tenant_id={tenant_id}"

    payload = json.dumps({
        "door_id":door_id
    })
    headers = {
        'x-api-key': 'SecretToken',
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    return response.status_code, response


def Get_Image_From_Intercom(message, intercom_id):
    url = f"https://domo-dev.profintel.ru/tg-bot/domo.domofon/urlsOnType?tenant_id={tenant_id}"

    payload = json.dumps({
        "intercoms_id": [intercom_id],
        "media_type": ["JPEG"]
    })

    headers = {
        'x-api-key': 'SecretToken',
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload).json()

    return response[0]["jpeg"]


def CreateKeyboard(text, Dict, message, mode_return_to_previous=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    array = []
    for elem in Dict.keys():
        array.append(types.KeyboardButton(elem))

    for elem in array:
        markup.add(elem)

    if mode_return_to_previous:
        return_button = types.KeyboardButton('Вернуться назад')
        markup.add(return_button)

    bot.send_message(message.chat.id, text,
                     reply_markup=markup)


def Intercom_ID_For_User(apartment_id):
    global intercom_names
    intercom_names = {}
    url = "https://domo-dev.profintel.ru/tg-bot/domo.apartment/" + str(apartment_id) + f"/domofon?apartment_id={str(apartment_id)}&tenant_id={str(tenant_id)}"

    headers = {
        'x-api-key': 'SecretToken',
    }
    response = requests.request("GET", url, headers=headers).json()

    for information in response:
        intercom_names[information['name']] = information['id']

    return intercom_names


def Flats_ID_For_User():
    global flat_id
    flat_id = {}
    url = f'https://domo-dev.profintel.ru/tg-bot/domo.apartment?tenant_id={tenant_id}'

    headers = {
        'x-api-key': 'SecretToken',
    }
    response = requests.request("GET", url, headers=headers).json()
    for information in response:
        flat_id[information['location']['readable_address']] = information['id']


def Check_Phone_Number_In_FastAPI(phone_number, message):
    global tenant_id
    url = "https://domo-dev.profintel.ru/tg-bot/check-tenant"

    payload = "{\r\n    \"phone\": " + phone_number + "\r\n}"
    headers = {
      'x-api-key': 'SecretToken'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    if response.status_code == 200:
        tenant_id = response.json()['tenant_id']
        bot.send_message(message.chat.id, "Авторизация прошла успешно!")
        Flats_ID_For_User()
        return True
    else:
        return False


@bot.message_handler(commands=['start'])
def Handle_Start(message):
    c1 = types.BotCommand(command='authentication', description='Авторизация пользователя')
    bot.set_my_commands([c1])
    bot.set_chat_menu_button(message.chat.id, types.MenuButtonCommands('commands'))
    bot.send_message(message.chat.id, "Введите /authentication")


def Сhecking_for_correctness(message, text, funct):
    message_ = bot.reply_to(message, text)
    bot.register_next_step_handler(message_, funct)


@bot.message_handler(commands=['authentication'])
def Start_Authentication(message):
    bot.send_message(message.from_user.id, 'Введите номер телефона [начинайте с 7]: ', reply_markup=types.ReplyKeyboardRemove(), parse_mode='Markdown')
    bot.register_next_step_handler(message, Get_Phone_Number_And_Choose_Flat_ID)


def Get_Phone_Number_And_Choose_Flat_ID(message):
    global phone_number
    phone_number = message.text
    in_base = Check_Phone_Number_In_FastAPI(phone_number, message)

    if in_base:
        CreateKeyboard(text="Выберите, для какой квартиры вы хотите просмотреть домофоны:", Dict=flat_id,
                       message=message)

        bot.register_next_step_handler(message, Intercoms_ID_Available_To_The_User)
    else:
        Сhecking_for_correctness(message, "Такого аккаунта нет! Попробуйте авторизоваться снова!", Get_Phone_Number_And_Choose_Flat_ID)


def Intercoms_ID_Available_To_The_User(message):
    try:
            global apartment_id, dict_intercoms
            apartment_id = flat_id[message.text]
            dict_intercoms = Intercom_ID_For_User(apartment_id)
            CreateKeyboard(text="Выберите домофон:", Dict=dict_intercoms, message=message, mode_return_to_previous=True)
            bot.register_next_step_handler(message, Intercom_Menu)
    except:
        Сhecking_for_correctness(message, "Введен неправильный адрес! Повторите попытку", Intercoms_ID_Available_To_The_User)


def Intercom_Menu(message):
    if message.text == "Вернуться назад":
        CreateKeyboard(text="Выберите, для какой квартиры вы хотите просмотреть домофоны:", Dict=flat_id, message=message)

        bot.register_next_step_handler(message, Intercoms_ID_Available_To_The_User)

    elif message.text == "Вернуться в меню":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button_send_photo = types.KeyboardButton('Вывести изображение с домофона')
        button_open_door = types.KeyboardButton('Открыть дверь')
        button_return_to_intercoms = types.KeyboardButton('Вернуться к домофонам')
        markup.add(button_send_photo)
        markup.add(button_open_door)
        markup.add(button_return_to_intercoms)
        bot.send_message(message.chat.id, "Меню бота:", reply_markup=markup)

        bot.register_next_step_handler(message, Choose_Send_Image_Or_Open_The_Door_Or_Return_To_Other_Intercoms)

    else:
        global intercom_id
        intercom_id = intercom_names[message.text]
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button_send_photo = types.KeyboardButton('Вывести изображение с домофона')
        button_open_door = types.KeyboardButton('Открыть дверь')
        button_return_to_intercoms = types.KeyboardButton('Вернуться к домофонам')
        markup.add(button_send_photo)
        markup.add(button_open_door)
        markup.add(button_return_to_intercoms)
        bot.send_message(message.chat.id, "Меню бота:", reply_markup=markup)

        bot.register_next_step_handler(message, Choose_Send_Image_Or_Open_The_Door_Or_Return_To_Other_Intercoms)


def Choose_Send_Image_Or_Open_The_Door_Or_Return_To_Other_Intercoms(message):
    if message.text == "Вывести изображение с домофона":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        url_photo = Get_Image_From_Intercom(message, intercom_id)
        bot.send_photo(message.chat.id, url_photo)
        button_return_to_intern_menu = types.KeyboardButton('Вернуться в меню')
        markup.add(button_return_to_intern_menu)
        bot.send_message(message.chat.id, "Выберите действие: ",
                         reply_markup=markup)
        bot.register_next_step_handler(message, Intercom_Menu)

    elif message.text == "Открыть дверь":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        status_code,response = Open_The_Door(message, intercom_id, door_id=0)
        button_return_to_intern_menu = types.KeyboardButton('Вернуться в меню')
        markup.add(button_return_to_intern_menu)
        print(response.status_code)
        if status_code == 200:
            bot.send_message(message.chat.id, "Дверь успешно открыта!", reply_markup=markup)
            bot.register_next_step_handler(message, Intercom_Menu)
        else:
            bot.send_message(message.chat.id, "Упс! Возникли какие-то проблемы!", reply_markup=markup)
            bot.register_next_step_handler(message, Intercom_Menu)


    elif message.text == "Вернуться к домофонам":
        CreateKeyboard(text="Выберите домофон:", Dict=dict_intercoms, message=message, mode_return_to_previous=True)
        bot.register_next_step_handler(message, Intercom_Menu)


bot.polling(none_stop=True, interval=0)