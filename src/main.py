import logging
import re
from urllib.parse import urljoin

import requests_cache
from bs4 import BeautifulSoup
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import BASE_DIR, MAIN_DOC_URL, PEP_URL
from exceptions import NoWhatsNewDataAndNoVersionDataError
from outputs import control_output
from utils import find_tag, get_response


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    response = get_response(session, whats_new_url)

    soup = BeautifulSoup(response.text, features='lxml')

    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})
    div_with_ul = find_tag(main_div, 'div', attrs={'class': 'toctree-wrapper'})
    sections_by_python = div_with_ul.find_all('li',
                                              attrs={'class': 'toctree-l1'})

    results = [('Ссылка на статью', 'Заголовок', 'Редактор, автор')]

    for section in tqdm(sections_by_python):
        version_a_tag = section.find('a')
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        response = get_response(session, version_link)

        soup = BeautifulSoup(response.text, 'lxml')

        h1 = find_tag(soup, 'h1')
        dl = soup.find('dl')  # Найдите в "супе" тег dl.
        dl_text = dl.text.replace('\n', ' ')

        results.append(
            (version_link, h1.text, dl_text)
        )

    return results


def latest_versions(session):
    response = get_response(session, MAIN_DOC_URL)
    soup = BeautifulSoup(response.text, 'lxml')

    sidebar = find_tag(soup, 'div', attrs={'class': "sphinxsidebarwrapper"})
    ul_tags = sidebar.find_all('ul')

    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break

    results = [('Ссылка на документацию', 'Версия', 'Статус')]

    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'

    for a_tag in a_tags:
        link = a_tag['href']
        text_match = re.search(pattern, a_tag.text)

        if text_match is not None:
            version, status = text_match.groups()
        else:
            version, status = a_tag.text, ''

        results.append(
            (link, version, status)
        )

    return results


def download(session):
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    response = get_response(session, downloads_url)

    soup = BeautifulSoup(response.text, 'lxml')

    tag_table = find_tag(soup, 'table', attrs={'class': 'docutils'})
    pdf_a4_tag = tag_table.find('a', {'href': re.compile(r'.+pdf-a4\.zip$')})
    pdf_a4_link = pdf_a4_tag['href']

    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename

    response = session.get(archive_url)

    with open(archive_path, 'wb') as file:
        file.write(response.content)

    logging.info(f'Архив был загружен и сохранён: {archive_path}')


def pep(session):
    response = get_response(session, PEP_URL)
    soup = BeautifulSoup(response.text, 'lxml')

    section_tag = find_tag(soup, 'section', attrs={'id': 'numerical-index'})
    tag_tbody = find_tag(section_tag, 'tbody')
    tr_tags = tag_tbody.find_all('tr')

    results = [('Статус', 'Количество')]

    for tr_tag in tqdm(tr_tags):
        td = find_tag(tr_tag, 'a', attrs={'class': "pep reference internal"})

        # Статусы на общей странице
        expected_statuses = []
        for abbr in tr_tag.find_all('abbr'):
            type, status = abbr['title'].split(', ')
            expected_statuses.append(status)

        # Статус в самой карточке
        tag_href = td['href']
        version_link = urljoin(PEP_URL, tag_href)
        response = get_response(session, version_link)

        soup = BeautifulSoup(response.text, 'lxml')
        dl_tag = find_tag(soup, 'dl',
                          attrs={'class': 'rfc2822 field-list simple'})
        status = dl_tag.find(string=re.compile(r'^Status$')).parent
        status_card = status.next_sibling.next_sibling.text

        if status_card not in expected_statuses:
            logging.info(
                'Несовпадающие статусы:\n'
                f'{version_link}\n'
                f'Статус в карточке: {status_card}\n'
                f'Ожидаемые статусы: {", ".join(expected_statuses)}\n'
            )

        results.append((status_card, 1))

    # Обновляем количество для каждого статуса
    status_counts = {}
    for status, count in results[1:]:
        status_counts[status] = status_counts.get(status, 0) + count
    results = [('Статус', 'Количество')] + [(status, count) for status,
    count in status_counts.items()]

    # Добавляем строку с общим количеством
    total_count = sum(count for _, count in results[1:])
    results.append(('Total', total_count))

    return results


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
    configure_logging()
    logging.info('Парсер запущен!')

    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()

    logging.info(f'Аргументы командной строки: {args}')

    # Создание кеширующей сессии.
    session = requests_cache.CachedSession()

    if args.clear_cache:
        session.cache.clear()

    parser_mode = args.mode

    results = MODE_TO_FUNCTION[parser_mode](session)
    if results is not None:
        control_output(results, args)

    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
