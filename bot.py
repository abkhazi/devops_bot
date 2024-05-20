from importlib.resources import read_text
import logging
import re
import paramiko
import psycopg2
from psycopg2 import Error
import os

from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler

from dotenv import load_dotenv

load_dotenv()

token=os.getenv('TOKEN')
db_host=os.getenv('DB_HOST')
db_port=os.getenv('DB_PORT')
db_user=os.getenv('DB_USER')
db_password=os.getenv('DB_PASSWORD')
db_name=os.getenv('DB_DATABASE')

# Подключаем логирование
logging.basicConfig(
    filename='logfile.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

def start(update: Update, context):
    user = update.effective_user
    update.message.reply_text(f'Привет {user.full_name}!')


def helpCommand(update: Update, context):
    update.message.reply_text('Help!')


def verify_passwordCommand(update: Update, context):
    update.message.reply_text('Введите пароль: ')

    return 'verify_password'

# Переменные для SSH-подключения

SSH_HOST = os.getenv('RM_HOST')
SSH_PORT = os.getenv('RM_PORT')
SSH_USERNAME = os.getenv('RM_USER')
SSH_PASSWORD = os.getenv('RM_PASSWORD')

# Функция для установки SSH-подключения к удаленному серверу
def establish_ssh_connection():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SSH_HOST, SSH_PORT, username=SSH_USERNAME, password=SSH_PASSWORD)
    return ssh

# Функция для выполнения команды на удаленном сервере
def execute_command(ssh, command):
    stdin, stdout, stderr = ssh.exec_command(command)
    return stdout.read().decode('utf-8')

# Функция для получения логов репликации PostgreSQL
def get_repl_logs(update: Update, context):
    ssh = establish_ssh_connection()
    result = execute_command(ssh, 'cat /var/log/postgresql/*.log | grep -E -i "replication|репл" | head -n 10')
    ssh.close()
    update.message.reply_text(result)

# Функция для выполнения SQL-запроса к базе данных
def execute_sql_query(query):
    connection = None
    try:
        connection = psycopg2.connect(user=db_user,
                                      password=db_password,
                                      host=db_host,
                                      port=db_port,
                                      database=db_name)
# 192.168.126.140
        cursor = connection.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        result = "\n".join(map(str, data))  # Преобразуем данные в строку для отправки
        logging.info("SQL-запрос успешно выполнен")
        return result
    except (Exception, Error) as error:
        logging.error("Ошибка при выполнении SQL-запроса: %s", error)
        return "Ошибка при выполнении SQL-запроса"
    finally:
        if connection is not None:
            cursor.close()
            connection.close()

# Функция  для получения email-адресов из таблицы Email
def get_emails(update: Update, context):
    query = "SELECT * FROM emails;"
    result = execute_sql_query(query)
    update.message.reply_text(result)

# Функция  для получения номеров телефонов из таблицы PhoneNumbers
def get_phone_numbers(update: Update, context):
    query = "SELECT * FROM phone_numbers;"
    result = execute_sql_query(query)
    update.message.reply_text(result)

# Функции для сбора информации о системе

def get_release(update: Update, context):
    ssh = establish_ssh_connection()
    result = execute_command(ssh, 'cat /etc/*-release')
    ssh.close()
    update.message.reply_text(result)

def get_uname(update: Update, context):
    ssh = establish_ssh_connection()
    result = execute_command(ssh, 'uname -a')
    ssh.close()
    update.message.reply_text(result)

def get_uptime(update: Update, context):
    ssh = establish_ssh_connection()
    result = execute_command(ssh, 'uptime')
    ssh.close()
    update.message.reply_text(result)

# Функции для сбора информации о файловой системе

def get_df(update: Update, context):
    ssh = establish_ssh_connection()
    result = execute_command(ssh, 'df -h')
    ssh.close()
    update.message.reply_text(result)

# Функции для сбора информации об оперативной памяти

def get_free(update: Update, context):
    ssh = establish_ssh_connection()
    result = execute_command(ssh, 'free -m')
    ssh.close()
    update.message.reply_text(result)

# Функции для сбора информации о производительности системы

def get_mpstat(update: Update, context):
    ssh = establish_ssh_connection()
    result = execute_command(ssh, 'mpstat')
    ssh.close()
    update.message.reply_text(result)

# Функции для сбора информации о работающих пользователях

def get_w(update: Update, context):
    ssh = establish_ssh_connection()
    result = execute_command(ssh, 'w')
    ssh.close()
    update.message.reply_text(result)

# Функции для сбора логов

def get_auths(update: Update, context):
    ssh = establish_ssh_connection()
    result = execute_command(ssh, 'last -n 10')
    ssh.close()
    update.message.reply_text(result)

def get_critical(update: Update, context):
    ssh = establish_ssh_connection()
    result = execute_command(ssh, 'tail -n 5 /var/log/syslog')
    ssh.close()
    update.message.reply_text(result)

# Функции для сбора информации о запущенных процессах

def get_ps(update: Update, context):
    ssh = establish_ssh_connection()
    result = execute_command(ssh, 'ps aux | head -n 11')
    ssh.close()
    update.message.reply_text(result)

# Функции для сбора информации об используемых портах

def get_ss(update: Update, context):
    ssh = establish_ssh_connection()
    result = execute_command(ssh, 'ss -tuln')
    ssh.close()
    update.message.reply_text(result)


# Функция для получения информации об установленных пакетах
def get_apt_list(update: Update, context):
    user_input = " ".join(context.args)  # Получаем запрос пользователя
    ssh = establish_ssh_connection()

    # Если запрос от пользователя пустой, выводим все пакеты
    if not user_input:
        result = execute_command(ssh, 'apt list --installed | head -n 50')
    else:
        # Если есть запрос от пользователя, ищем информацию о пакете
        result = execute_command(ssh, f'apt list --installed | grep "{user_input}"')

    ssh.close()
    update.message.reply_text(result)


# Функции для сбора информации о запущенных сервисах

def get_services(update: Update, context):
    ssh = establish_ssh_connection()
    result = execute_command(ssh, 'systemctl list-units --type=service --state=running')
    ssh.close()
    update.message.reply_text(result)

# Функция для записи номеров телефонов в базу данных
def insert_phone_numbers(phone_numbers):
    try:
        connection = psycopg2.connect(user=db_user,
                                      password=db_password,
                                      host=db_host,
                                      port=db_port,
                                      database=db_name)      
          
        cursor = connection.cursor()
        for number in phone_numbers:
            cursor.execute("INSERT INTO phone_numbers (phone) VALUES (%s)", (number,))
        connection.commit()
        logging.info("Номера телефонов успешно добавлены в базу данных")
    except (Exception, Error) as error:
        logging.error("Ошибка при добавлении номеров телефонов в базу данных: %s", error)
    finally:
        if connection is not None:
            cursor.close()
            connection.close()

# Функция для записи email-адресов в базу данных
def insert_emails(emails):
    try:
        connection = psycopg2.connect(user=db_user,
                                      password=db_password,
                                      host=db_host,
                                      port=db_port,
                                      database=db_name)

        cursor = connection.cursor()
        for email in emails:
            cursor.execute("INSERT INTO emails (email) VALUES (%s)", (email,))
        connection.commit()
        logging.info("Email-адреса успешно добавлены в базу данных")
    except (Exception, Error) as error:
        logging.error("Ошибка при добавлении email-адресов в базу данных: %s", error)
    finally:
        if connection is not None:
            cursor.close()
            connection.close()


# Статусы для конечного автомата разговора
ENTER_TEXT_PHONE = 0
ENTER_TEXT_EMAIL = 1
CONFIRM_WRITE = 2

# Обработчик команды для получения номеров телефонов
def find_phone_number(update: Update, context):
    update.message.reply_text('Введите текст для поиска номеров телефонов:')
    return ENTER_TEXT_PHONE

# Обработка ответа на запрос текста
def receive_text_phone(update: Update, context):
    user_input = update.message.text

    phoneNumRegex = re.compile(r'(?:\+7|8)[\s-]?(?:\(\d{3}\)|\d{3})[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}')
    phoneNumberList = phoneNumRegex.findall(user_input)

    if not phoneNumberList:
        update.message.reply_text('Телефонные номера не найдены')
        return ConversationHandler.END

    phone_numbers_response = "\n".join([f"{i+1}. {number}" for i, number in enumerate(phoneNumberList)])
    update.message.reply_text(phone_numbers_response)

    context.user_data['phone_numbers'] = phoneNumberList

    # Предложение записи найденных номеров в базу данных
    update.message.reply_text('Хотите записать найденные номера телефонов в базу данных? (Да/Нет)')
    return CONFIRM_WRITE

# Обработка ответа на запрос записи в базу данных
def handle_write_to_db(update: Update, context):
    user_input = update.message.text.lower()

    if user_input == 'да':
        # Извлекаем номера телефонов из user_data
        phone_numbers = context.user_data.get('phone_numbers', [])
        if phone_numbers:
            insert_phone_numbers(phone_numbers)
            update.message.reply_text('Номера телефонов успешно добавлены в базу данных')
        else:
            update.message.reply_text('Произошла ошибка, не найдены номера телефонов для записи')
    elif user_input == 'нет':
        update.message.reply_text('Ок, не будем записывать номера в базу данных.')
    else:
        update.message.reply_text('Пожалуйста, введите "Да" или "Нет".')

    return ConversationHandler.END

# Обработчик команды для получения email-адресов
def find_email(update: Update, context):
    update.message.reply_text('Введите текст для поиска email-адресов:')
    return ENTER_TEXT_EMAIL

# Обработка ответа на запрос текста для поиска email-адресов
def receive_emails_text(update: Update, context):
    user_input = update.message.text

    emailRegex = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    emailList = emailRegex.findall(user_input)

    if not emailList:
        update.message.reply_text('E-mail не найдены')
        return ConversationHandler.END

    context.user_data['emails'] = emailList
    emails_response = "\n".join([f"{i+1}. {number}" for i, number in enumerate(emailList)])
    update.message.reply_text(emails_response)

    # Предложение записи найденных email-адресов в базу данных
    update.message.reply_text('Хотите записать найденные email-адреса в базу данных? (Да/Нет)')
    return CONFIRM_WRITE

    # Обработка ответа на запрос записи email-адресов в базу данных
def handle_email_write_to_db(update: Update, context):
    user_input = update.message.text.lower()

    if user_input == 'да':
        
        emails = context.user_data.get('emails', [])
        if emails:
            insert_emails(emails)
            update.message.reply_text('E-mail успешно добавлены в базу данных')
        else:
            update.message.reply_text('Произошла ошибка, не найдены E-mail  для записи')
    elif user_input == 'нет':
        update.message.reply_text('Ок, не будем записывать E-mail  в базу данных.')
    else:
        update.message.reply_text('Пожалуйста, введите "Да" или "Нет".')

    return ConversationHandler.END


def verify_password (update: Update, context):
    user_input = update.message.text 

    passwordRegex = re.compile(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()])[A-Za-z\d!@#$%^&*()]{8,}$')
    passwordList =   passwordRegex.findall(user_input) 

    if not passwordList:
        update.message.reply_text('Пароль простой')
        return ConversationHandler.END 
    
    update.message.reply_text('Пароль сложный') 
    return ConversationHandler.END 

def echo(update: Update, context):
    update.message.reply_text(update.message.text)

def main():
    updater = Updater(token, use_context=True)

    # Получаем диспетчер для регистрации обработчиков
    dp = updater.dispatcher

    # Обработчик диалога
    convHandlerfind_phone_number = ConversationHandler(
        entry_points=[CommandHandler('find_phone_number', find_phone_number)],
        states={
            ENTER_TEXT_PHONE: [MessageHandler(Filters.text & ~Filters.command, receive_text_phone)],
            CONFIRM_WRITE: [MessageHandler(Filters.text & ~Filters.command, handle_write_to_db)],
            'find_phone_number': [MessageHandler(Filters.text & ~Filters.command, find_phone_number)]
        },
        fallbacks=[]
    )
    convHandlerfind_email = ConversationHandler(
        entry_points=[CommandHandler('find_email', find_email)],
        states={
            ENTER_TEXT_EMAIL: [MessageHandler(Filters.text & ~Filters.command, receive_emails_text)],
            CONFIRM_WRITE: [MessageHandler(Filters.text & ~Filters.command, handle_email_write_to_db)],
            'find_email': [MessageHandler(Filters.text & ~Filters.command, find_email)]
        },
        fallbacks=[]
    )

    convHandlerverify_password = ConversationHandler(
        entry_points=[CommandHandler('verify_password', verify_passwordCommand)],
        states={
            'verify_password': [MessageHandler(Filters.text & ~Filters.command, verify_password)],
        },
        fallbacks=[]
    )

    # Регистрируем обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("get_repl_logs", get_repl_logs))
    dp.add_handler(CommandHandler("get_emails", get_emails))
    dp.add_handler(CommandHandler("get_phone_numbers", get_phone_numbers))
    dp.add_handler(CommandHandler("get_release", get_release))
    dp.add_handler(CommandHandler("get_uname", get_uname))
    dp.add_handler(CommandHandler("get_uptime", get_uptime))
    dp.add_handler(CommandHandler("get_df", get_df))
    dp.add_handler(CommandHandler("get_free", get_free))
    dp.add_handler(CommandHandler("get_mpstat", get_mpstat))
    dp.add_handler(CommandHandler("get_w", get_w))
    dp.add_handler(CommandHandler("get_auths", get_auths))
    dp.add_handler(CommandHandler("get_critical", get_critical))
    dp.add_handler(CommandHandler("get_ps", get_ps))
    dp.add_handler(CommandHandler("get_ss", get_ss))
    dp.add_handler(CommandHandler("get_apt_list", get_apt_list))
    dp.add_handler(CommandHandler("get_services", get_services))
    dp.add_handler(CommandHandler("help", helpCommand))
    dp.add_handler(convHandlerfind_phone_number)
    dp.add_handler(convHandlerfind_email)
    dp.add_handler(convHandlerverify_password)

 	# Регистрируем обработчик текстовых сообщений
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
		
	# Запускаем бота
    updater.start_polling()

	# Останавливаем бота при нажатии Ctrl+C
    updater.idle()


if __name__ == '__main__':
    main()
