# app/core/logger.py
import logging
import sys
import colorlog

def setup_app_logging(name: str = "app") -> logging.Logger:
    """
    Настраивает унифицированный логгер для всего проекта.
    """
    log_format = (
        "%(log_color)s%(levelname)s:%(reset)s     %(message)s"
    )

    log_colors = {
        'DEBUG':    'cyan',
        'INFO':     'green',
        'WARNING':  'yellow',
        'ERROR':    'red',
        'CRITICAL': 'red,bg_white',
    }

    # 3. Настройка обработчика (вывод в консоль)
    handler = colorlog.StreamHandler(sys.stdout)
    handler.setFormatter(colorlog.ColoredFormatter(
        log_format,
        log_colors=log_colors,
    ))

    # 4. Инициализация логгера
    logger = colorlog.getLogger(name)
    
    # Чтобы не дублировать логи, если логгер уже настроен выше по дереву
    if not logger.handlers:
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False # Важно: не прокидываем логи в root, чтобы избежать дублей

    return logger

# Создаем глобальный объект логгера для удобного импорта
logger = setup_app_logging("meta-search")