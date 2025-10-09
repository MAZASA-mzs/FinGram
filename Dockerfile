# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Обновляем pip
RUN pip install --upgrade pip

# Копируем файл зависимостей
COPY requirements.txt requirements.txt

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код в контейнер
COPY ./src /app/src

# Указываем команду для запуска приложения
# Запускаем main.py, который, в свою очередь, запускает и бота, и API
CMD ["python", "-m", "src.main"]
