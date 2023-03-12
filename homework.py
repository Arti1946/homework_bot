"""Телеграм-бот для Домашки."""
import logging
import os
import sys
import time
from http import HTTPStatus
from typing import Dict

import requests
import telegram
from dotenv import load_dotenv
from telegram.error import TelegramError

from exceptions import HomeworksErrors, KeyError, StatusCodeError, RequestError

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


HOMEWORKS_STATUSES: Dict = {}
RETRY_PERIOD: int = 600
ENDPOINT: str = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS: str = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}
PAYLOAD: Dict = {"from_date": 1674329510}
HOMEWORK_VERDICTS: Dict = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}


def check_tokens() -> bool:
    """Проверяем доступность переменных окружения."""
    environments = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID,
    ]
    return all(environments)


def send_message(bot: telegram, message: str):
    """Отправляем сообщение клиенту."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except TelegramError as error:
        logger.error(error)
    else:
        logging.debug("Бот отправил сообщение")


def get_api_answer(timestamp: float) -> Dict:
    """Получаем ответ API-сервиса."""
    try:
        logger.debug(
            f"отправляем запрос к API {ENDPOINT}, "
            f"c параметрами from_date: {timestamp}"
        )
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={"from_date": timestamp},
        )
        if response.status_code == HTTPStatus.OK.value:
            return response.json()
        raise StatusCodeError(
            f"API-сервер возвращает код {response.status_code}"
        )
    except requests.RequestException as error:
        raise RequestError(error)


def check_response(response: Dict) -> Dict:
    """Проверяем ответ API."""
    if isinstance(response, dict):
        if "homeworks" not in response:
            message = "Отсутствует ключ homeworks в ответе API."
            raise KeyError(message)
        elif "current_date" not in response:
            message = "Отсутствует ключ curren_date в ответе API."
            raise KeyError(message)
        elif not isinstance(response["homeworks"], list):
            raise TypeError
        return response["homeworks"]
    raise TypeError


def parse_status(homework: Dict) -> str:
    """Проверяем статус домашки."""
    if "homework_name" not in homework:
        raise HomeworksErrors("Нету ключа homework_name в ответе API домашки")
    homework_name = homework["homework_name"]
    if homework["status"] not in HOMEWORK_VERDICTS:
        raise HomeworksErrors("Нету ключа status в ответе API домашки")
    status = homework["status"]
    verdict = HOMEWORK_VERDICTS[status]
    message = (
        f"Изменился статус проверки работы " f'"{homework_name}". {verdict}'
    )
    return message


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical(
            "Отсутствует обязательная переменная окружения."
            " Программа принудительно остановлена."
        )
        sys.exit("No tokkens")
    last_message = ""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            api_response = get_api_answer(timestamp)
            check_response(api_response)
            homeworks = api_response["homeworks"]
            if len(homeworks) == 0:
                message = "Нет новых работ"
                send_message(bot, message)
                logger.debug(message)
                continue
            homework = homeworks[0]
            status = parse_status(homework)
            timestamp = api_response["current_date"]
            if isinstance(status, str):
                hw_status = homework["status"]
                homework_name = homework["homework_name"]
                if (
                    homework_name not in HOMEWORKS_STATUSES
                    or HOMEWORKS_STATUSES[homework_name] != hw_status
                ):
                    HOMEWORKS_STATUSES[homework_name] = hw_status
                    send_message(bot, status)
                logger.debug("Статус домашки не изменился")
        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            logger.error(message)
            if message != last_message:
                last_message = message
                send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()
