import logging
import os
import sys
import time
from http import HTTPStatus
from typing import Dict, List

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formater = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
handler.setFormatter(formater)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


HOMEWORKS_STATUSES = {}
ERRORS = []
RETRY_PERIOD = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}
PAYLOAD = {"from_date": 1674329510}
HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}


def check_tokens():
    """Проверяем доступность переменных окружения."""
    environments = {
        "Токен практикума": PRACTICUM_TOKEN,
        "Токен Телеграма": TELEGRAM_TOKEN,
        "ID чата телеграма": TELEGRAM_CHAT_ID,
    }
    for description, token in environments.items():
        if token is None:
            message = (
                f"Отсутствует обязательная переменная окружения: {description}"
                f". Программа принудительно остановлена."
            )
            logger.critical(message)
            return False
        else:
            return True


def send_message(bot, message):
    """Отправляем сообщение клиенту."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug("Бот отправил сообщение")
    except Exception as error:
        logger.error(error)
        raise Exception(error)


def get_api_answer(timestamp):
    """Получаем ответ API-сервиса."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={"from_date": timestamp},
        )
        if response.status_code == HTTPStatus.OK.value:
            return response.json()
        else:
            raise Exception(
                f"API-сервер возвращает код {response.status_code}"
            )
    except Exception as error:
        logger.error(error)
        raise Exception(error)


def check_response(response):
    """Проверяем ответ API."""
    keys = ("homeworks", "current_date")
    if type(response) is Dict:
        for key in keys:
            if key not in response.keys():
                message = "Отсутствуют ожидаемые ключи в ответе API."
                raise Exception(message)
            elif type(response["homeworks"]) is not List:
                raise TypeError
            else:
                return response["homeworks"]

    else:
        raise TypeError


def parse_status(homework):
    """Проверяем статус домашки."""
    try:
        if not homework["homework_name"]:
            raise Exception("Нету названия у домашки")
        homework_name = homework["homework_name"]
        if homework["status"] not in HOMEWORK_VERDICTS:
            raise Exception(f'{homework["status"]} not exist')
        status = homework["status"]
        verdict = HOMEWORK_VERDICTS[status]
        message = (
            f"Изменился статус проверки работы "
            f'"{homework_name}". {verdict}'
        )
        return message
    except Exception as error:
        raise Exception(error)


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit("No tokkens")
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            api_response = get_api_answer(timestamp)
            check_response(api_response)
            homeworks = api_response["homeworks"]
            homework = homeworks[0]
            status = parse_status(homework)
            if type(status) is str:
                if status is not None:
                    hw_status = homework["status"]
                    homework_name = homework["homework_name"]
                    if homework_name not in HOMEWORKS_STATUSES:
                        HOMEWORKS_STATUSES[homework_name] = hw_status
                        send_message(bot, status)
                    elif HOMEWORKS_STATUSES[homework_name] != hw_status:
                        HOMEWORKS_STATUSES[homework_name] = hw_status
                        send_message(bot, status)
                    else:
                        logger.debug("Статус домашки не изменился")
            time.sleep(RETRY_PERIOD)
        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            logger.error(message)
            if message not in ERRORS:
                ERRORS.append(message)
                send_message(bot, message)
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()
