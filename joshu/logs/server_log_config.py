import os
import time
from logging import getLogger, Formatter, DEBUG, StreamHandler
from logging.handlers import TimedRotatingFileHandler

# Создаем объект-логгер с именем app.server:
logger = getLogger('app.server')

# Создаем объект форматирования:
SERVER_FORMATTER = Formatter('%(asctime)s %(levelname)s %(filename)s %(message)s')

# Подготовка имени файла для логирования
PATH = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(PATH, 'server.log')

# Будет производится ротация файлов по дням, с интервалом 1 день, файлы с кодировкой utf8
LOG_FILE = TimedRotatingFileHandler(PATH, encoding='utf8', interval=1, when='D')
LOG_FILE.setFormatter(SERVER_FORMATTER)


# Добавляем в логгер новый обработчик событий и устанавливаем уровень логирования
logger.addHandler(LOG_FILE)
logger.setLevel(DEBUG)

# Добавляем в логгер новый обработчик событий и устанавливаем уровень логирования
console = StreamHandler()   # выводим логи в поток
console.setLevel(DEBUG)     # задаем уровень
console.setFormatter(SERVER_FORMATTER) # задаем форматирование
logger.addHandler(console)


def server_app_info(str_info):
    logger.info(str_info)


def server_app_error(str_info):
    logger.error(str_info)


if __name__ == '__main__':
    logger.info('Тестовый запуск логирования')
    logger.critical('Критическая ошибка')
    logger.error('Ошибка')
    logger.debug('Отладочная информация')
    logger.info('Информационное сообщение')