import paramiko
import psycopg2
import tkinter as tk
from tkinter import Entry, Label, Button, messagebox, Text
import datetime
import os


def run_scanner():
    try:
        # Получаем введенные значения из GUI
        host = host_entry.get()
        port = port_entry.get()
        username = username_entry.get()
        password = password_entry.get()

        # Преобразуем порты в целые числа
        port = int(port) if port.strip() else 22

        # Создаем SSH-соединение
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh_client.connect(host, port, username, password)

            # Команда для получения информации о дистрибутиве
            os_info_command = 'cat /etc/os-release'
            stdin, stdout, stderr = ssh_client.exec_command(os_info_command)
            os_info = stdout.read().decode()

            # Извлекаем название дистрибутива из поля NAME
            name_field = 'NAME="'
            if name_field in os_info:
                start_index = os_info.index(name_field) + len(name_field)
                end_index = os_info.find('"', start_index)
                distributor_name = os_info[start_index:end_index]
            else:
                distributor_name = "Название дистрибутива не найдено"

            # Извлекаем версию операционной системы из поля VERSION_ID
            version_id_field = 'VERSION_ID='
            start_index = os_info.find(version_id_field) + len(version_id_field)
            end_index = os_info.find('\n', start_index)
            os_version_id = os_info[start_index:end_index].strip()

            # Команда для получения информации об архитектуре
            arch_command = 'uname -m'
            stdin, stdout, stderr = ssh_client.exec_command(arch_command)
            arch_info = stdout.read().decode()

            # Записываем запущенные команды в лог
            log_command = f"Logged at {datetime.datetime.now()}\n" \
                          f"1. {os_info_command}\n" \
                          f"2. {arch_command}\n"
            with open('command_log.txt', 'a') as log_file:
                log_file.write(log_command)
        finally:
            ssh_client.close()

        # Создаем подключение к базе данных PostgreSQL
        db_connection = psycopg2.connect(
            database="int_db",
            user="postgres",
            password=os.getenv('DB_PASSWORD'),
            host="127.0.0.1",
            port="5432"
        )

        # Создаем курсор для выполнения SQL-запросов
        cursor = db_connection.cursor()

        # Создаем запись о сканировании в таблице scans
        cursor.execute("INSERT INTO scans DEFAULT VALUES RETURNING id")
        scan_id = cursor.fetchone()[0]

        # Записываем полученные данные в таблицу scan_data с привязкой к сканированию
        cursor.execute(
            "INSERT INTO scan_data (scan_id, os_info, os_version, arch_info) VALUES (%s, %s, %s, %s)",
            (scan_id, distributor_name, os_version_id, arch_info)
        )

        # Подтверждаем изменения
        db_connection.commit()

        # Закрываем соединение
        cursor.close()
        db_connection.close()

        # Выводим информацию о сканировании в текстовом виджете
        result_text.config(state='normal')  # Разрешаем редактирование
        result_text.delete('1.0', tk.END)  # Очищаем текстовое поле
        result_text.insert(tk.END, f"Название дистрибутива: {distributor_name}\n")
        result_text.insert(tk.END, f"Версия операционной системы: {os_version_id}\n")
        result_text.insert(tk.END, f"Архитектура: {arch_info}\n")
        result_text.config(state='disabled')  # Запрещаем редактирование

        # Выводим сообщение об ошибке, если таковая будет
    except Exception as e:
        messagebox.showerror("Ошибка", f"Произошла ошибка: {str(e)}")


# Создаем GUI
root = tk.Tk()
root.title("Сканер системы")

# Создаем и размещаем поля в GUI вводом информации
host_label = Label(root, text="Хост:")
host_label.pack()
host_entry = Entry(root)
host_entry.pack()

port_label = Label(root, text="Порт (по умолчанию 22):")
port_label.pack()
port_entry = Entry(root)
port_entry.pack()

username_label = Label(root, text="Имя пользователя:")
username_label.pack()
username_entry = Entry(root)
username_entry.pack()

password_label = Label(root, text="Пароль:")
password_label.pack()
password_entry = Entry(root, show="*")
password_entry.pack()

run_button = Button(root, text="Запустить сканирование", command=run_scanner)
run_button.pack()

# Текстовое поле для вывода информации
result_text = Text(root, height=10, width=50, wrap='word')
result_text.pack()
result_text.config(state='disabled')  # Запрещаем редактирование

# Запускаем GUI
root.mainloop()
