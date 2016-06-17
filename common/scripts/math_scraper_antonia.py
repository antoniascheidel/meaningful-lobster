#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Scrapes math problems and stores question answer pairs.
Examples are here: http://www.mathplayground.com/wpdatabase/wpindex.html
Usage: python math_scraper.py [url for index site with links to math problems]
"""
import argparse
import json
import re
import requests
import time

from bs4 import BeautifulSoup
from common.util import log

description = 'Scrapes a list of word problems and stores questions and answers in json.'
parser = argparse.ArgumentParser(description=description)
parser.add_argument('url', help='url of math problems index site')


def get_problems_from_url(url, filename):
    """
    Scrape all the problems from the given url and write them to a file.
    """
    response = requests.get(url)

    soup = BeautifulSoup(response.text, 'html.parser')
    raw_questions = soup.find_all('div', 'QuestionText')
    questions = dict()
    for index, rq in enumerate(raw_questions):
        question_text = rq.contents
        raw_question = ' '.join([q for q in question_text if q.string])
        questions[index] = {'question': raw_question}

    answers = re.findall("\[3\]\[0\]=new Array\('(\d+)'", response.text)
    for index, answer in enumerate(answers):
        questions[index]['answer'] = int(answer)
    log('found %s questions in %s' % (len(questions), filename), 'debug')

    question_json = json.dumps(questions)
    with open('output/questions_' + filename + '.json', 'w') as out_file:
        out_file.write(question_json)


def find_links_and_process(base_url):
    """
    Find all relevant links in the html at the given url, visit them and extract
    word problems.
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    all_links = [l.get('href') for l in soup.find_all('a')]
    bad_links = []
    for link in all_links:
        if not link[0].isupper():
            continue
        try:
            get_problems_from_url(base_url + '/' + link, link[:link.find('.')])
        except Exception:
            bad_links.append(link)
    if bad_links:
        log('bad links: %s' % bad_links, 'warning')
    log('time taken: %s' % (time.time() - start), 'info')


if __name__ == '__main__':
    start = time.time()

    args = parser.parse_args()
    url = args.url
    base_url = url[0:url.rfind('/')]
    find_links_and_process(base_url)
