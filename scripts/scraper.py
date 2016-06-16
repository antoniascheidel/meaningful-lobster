import argparse
import codecs
import json
import os

import lxml.html
import pdfquery
import requests

from itertools import izip


K5_LEARNING_LINK = 'http://www.k5learning.com'
MATH_PATH = '/free-math-worksheets'
PDF_DIRECTORY = 'output/pdfs'

QUESTION_PAGE_NUMBER = 0
SOLUTION_PAGE_NUMBER = 1


def main():
    """
    Pulls all math word problem pdfs from the k5 learning website and saves their questions and
    solutions in json format.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--overwrite', dest='overwrite', action='store_true')

    args = parser.parse_args()
    overwrite = args.overwrite

    # Get all pdf filenames
    if overwrite:  # Scrape pdfs from website
        pdf_paths = extract_filetypes(
            set([MATH_PATH]),
            K5_LEARNING_LINK,
            '.pdf',
            key1=(MATH_PATH + '/'),
            key2='word-problems')
        pdf_urls = [
            ((K5_LEARNING_LINK if path.startswith('/') else '') + path) for path in pdf_paths
        ]
        pdf_filenames = download_pdfs(pdf_urls)
    else:  # Pull pdf filenames from output directory
        base_filepath = PDF_DIRECTORY
        pdf_filenames = [
            '%s/%s' % (base_filepath, filename) for filename in os.listdir(base_filepath)
        ]

    for pdf_filename in pdf_filenames:
        parse_pdf(pdf_filename)


def parse_pdf(pdf_filename):
    """
    Extracts the questions and solutions from the pdf at the given location. Writes the data as
    json.

    Parameters:
        pdf_filename (str): The filename of the pdf to query.
    """
    try:
        pdf = pdfquery.PDFQuery(pdf_filename)
    except Exception:
        return

    questions = get_all_problem_components_on_page(pdf, QUESTION_PAGE_NUMBER)
    solutions = get_all_problem_components_on_page(pdf, SOLUTION_PAGE_NUMBER)

    page_json = {}
    for question, solution in izip(questions, solutions):
        assert question[0] == solution[0]
        problem_number = str(question[0])
        question_text, solution_text = question[1], solution[1]
        if not question_text or not solution_text:
            continue
        page_json[problem_number] = {'question': question_text, 'answer': solution_text}

    if page_json:
        pdf_name = pdf_filename[:-len('.pdf')][len(PDF_DIRECTORY) + 1:],
        codecs.open('output/%s.json' % pdf_name, 'wb').write(
            json.dumps(page_json))


def process_component(text, number):
    """
    Checks that the given text is prepended with the problem number and removes it if so.
    Otherwise returns None.

    Parameters:
        text (str): The text to process.
        number (int): The problem number of the text.

    Returns:
        processed_text (str): The processed text.
    """
    prefix = "%d. " % number
    if not text.startswith(prefix):
        return None
    return text[len(prefix):]


def process_question(question_text, number):
    """
    Processes the question text. Returns None if it is an invalid question.

    Parameters:
        question_text (str): The text of the question.
        number (int): The problem number of the question.

    Returns:
        processed_question (str): The processed question.
    """
    return process_component(question_text, number)


def process_solution(solution_text, number):
    """
    Extracts the numerical solution from the solution text. Returns None if it is an invalid
    solution.

    Parameters:
        solution_text (str): The text of the solution.
        number (int): The problem number of the solution.

    Returns:
        processed_solution (str): A string representing the numerical solution to the problem.
    """
    solution_text = process_component(solution_text, number)
    if solution_text is None:
        return None

    tokens = solution_text.split()
    for index, token in enumerate(tokens):
        if token != '=' or index > len(tokens)-2:
            # The solution comes after the equals sign
            continue

        # The solution may be a single number, i.e. "53" or a number proceeded by a
        # fraction, i.e. "3 1/4"
        whole_part = tokens[index+1]
        if whole_part != strip_ending_punctuation(whole_part):
            return strip_ending_punctuation(whole_part)

        fractional_part = (
            strip_ending_punctuation(tokens[index+2]) if index+2 < len(tokens) else None)
        if fractional_part == whole_part or fractional_part is None:
            return whole_part

        try:
            int(fractional_part[0])
            answer = '%s %s' % (whole_part, fractional_part)
        except ValueError as error:
            answer = whole_part

        return answer


def strip_ending_punctuation(text):
    """
    Removes commas, periods, and exclamation marks appearing at the end of text.

    Parameters:
        text (str): The text from which to remove ending punctuation from.
    """
    if text.endswith(('.', ',', '!')):
        return text[:-1]
    return text


def get_all_problem_components_on_page(pdf, page_number):
    """
    Queries the given pdf on the given page for all problems and returns the results.

    Parameters:
        pdf (PDF): The pdf to query.
        page_number (int): The page of the pdf to analyze. Must be 0 or 1 for questions and
            solutions respectively.

    Returns:
        A list of 2-tuples consisiting of:
            problem_number (int): The problem number.
            processed_component (str): The processed problem component (a question or solution).
    """
    assert page_number in [QUESTION_PAGE_NUMBER, SOLUTION_PAGE_NUMBER]

    problem_components = []
    pdf.load(page_number)

    problem_number = 1
    while True:
        problem_label = pdf.pq('LTTextLineHorizontal:contains("%d.")' % problem_number)
        if problem_label.attr('x0') is None:
            # No question of this number
            break
        component = get_problem_component(pdf, problem_label)
        process = process_question if page_number == QUESTION_PAGE_NUMBER  else process_solution
        problem_components.append((problem_number, process(component, problem_number)))
        problem_number += 1

    return problem_components


def get_problem_component(pdf, problem_label):
    """
    Grabs text from the pdf in the same block as the given label.

    Parameters:
        pdf (PDF): The pdf to query.
        problem_label: The label containing a portion of the text we want to extract.

    Returns:
        text (str): The block of text in an expanded view of the given label on the pdf.
    """
    x0, x1 = float(problem_label.attr('x0')), float(problem_label.attr('x1'))
    y0, y1 = float(problem_label.attr('y0')), float(problem_label.attr('y1'))
    line_height = y1 - y0

    def get_text_from_bounding_box(num_lines, extra_line_spacing=10,
                                   extra_width=60):
        return pdf.pq(
            'LTTextLineHorizontal:in_bbox("%s, %s, %s, %s")' %
            (x0, y1 - (line_height + extra_line_spacing) * num_lines,
             x1 + extra_width, y1)
        ).text()

    total_lines = 1
    while (len(get_text_from_bounding_box(total_lines)) <
           len(get_text_from_bounding_box(total_lines + 1))):
        total_lines += 1
    return get_text_from_bounding_box(total_lines)


def download_pdfs(pdf_urls):
    """
    Downloads the given URLs and writes them as pdfs. Returns the filenames of the saved pdfs.

    Parameters:
        pdf_urls (list<str>): A list of the pdf URLs to download.

    Returns:
        pdf_filenames (list<str>): A list of the filenames of the saved pdfs.
    """
    pdf_filenames = []
    for pdf_url in pdf_urls:
        response = requests.get(pdf_url)
        pdf_filename = '%s/%s' % (PDF_DIRECTORY, pdf_url.split('/')[-1])
        pdf_filenames.append(pdf_filename)
        codecs.open(pdf_filename, 'wb').write(response.content)
    return pdf_filenames


def extract_filetypes(root_paths, base_url, extension, initial_key=None, default_key=None,
                      prev_visited_paths=None):
    """
    Scrapes the pages represented by the base URL and the root paths for files of the given
    extension type.

    Parameters:
        root_paths (set<str>): The paths to start from.
        base_url (str): The base URL of the website.
        extension (str): The file extension to look for.
        initial_key (str): (Optional) A key to restrict paths when looking at paths on the
            top-level page.
        default_key (str): (Optional) A key to restrict newly found paths to.
        prev_visited_paths (set<str>):

    Returns:
        paths_with_extension (set<str>): A set of all paths found which end with the given
            extension.
    """
    sub_paths = set()
    for root_path in root_paths:
        response = requests.get(base_url + root_path)
        root = lxml.html.fromstring(response.text)
        sub_paths.update(path for path in root.xpath('//a/@href') if
                         (prev_visited_paths is None and initial_key in path) or
                         (prev_visited_paths is not None and default_key in path))

    if prev_visited_paths is not None:
        visited_paths = prev_visited_paths | root_paths
    else:
        visited_paths = root_paths

    paths = sub_paths - visited_paths  # to prevent us from wandering in a loop

    paths_with_extension = set(path for path in paths if path.endswith(extension))
    paths_to_explore = paths - paths_with_extension

    if len(paths_to_explore) > 0:
        paths_with_extension.update(
            extract_filetypes(
                paths_to_explore,
                base_url,
                extension,
                initial_key=initial_key,
                default_key=default_key,
                prev_visited_paths=visited_paths))

    return paths_with_extension


if __name__ == "__main__":
    main()
