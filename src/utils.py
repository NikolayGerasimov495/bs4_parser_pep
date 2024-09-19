import logging

from bs4 import BeautifulSoup
from requests import RequestException

from exceptions import (NoWhatsNewDataAndNoVersionDataError,
                        ParserFindTagException)


# Это я уберу
def get_soup(response):
    return BeautifulSoup(response.text, features='lxml')
# TODO
# У меня не получается сюда погрузить soup, т.к.
# тесты хотят видеть ответ response и ничего другого.
# Тесты я переделывал, чтобы два аргумента принимал.
# Но тесты сайта потом блочили.
# Другого способа написать функцию, например как ниже - я не умею.
# Если можете - подскажите.
# TODO


def get_response(session, url):
    try:
        response = session.get(url)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            # TODO
            # Вот так могу оставить, но тесты не принимают
            # soup = BeautifulSoup(response.text, features='lxml')
            # return response, soup
            # TODO
            return response
        error_msg = (f'Ошибка при загрузке страницы {url}, '
                     f'код ответа: {response.status_code}')
        logging.error(error_msg)
        raise NoWhatsNewDataAndNoVersionDataError(error_msg)
    except RequestException as e:
        error_msg = f'Возникла ошибка при загрузке страницы {url}'
        logging.exception(error_msg, stack_info=True)
        raise NoWhatsNewDataAndNoVersionDataError(error_msg) from e


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {attrs}'
        logging.error(error_msg, stack_info=True)
        raise ParserFindTagException(error_msg)
    return searched_tag
