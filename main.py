import logging
import math
import time
import os
import pandas as pd
from random import randint

from database import create_session, Book
from scraping_common import step_find_book_in_search_results, query_saxo_with_title_or_isbn, extract_book_details_dict, \
    extract_recommendations_list, translate_danish_to_english, create_browser_and_wait_for_page_load
from scraping_sql import book_not_found_in_search_results_title, save_book_details_to_database

# from scraping_sql import run_sql


logging.basicConfig(filename='data_csv/app_errors.log', level=logging.ERROR,
                    format='%(asctime)s:%(levelname)s:%(message)s')


def read_input_csv(file_path):
    """Read the CSV file to get the list of tuples (book_title, book_author) and return it as a list"""
    df = pd.read_csv(file_path, encoding="ISO-8859-1")
    book_info = list(zip(df["book_title"], df["book_author"]))
    return book_info


def save_to_csv(data, output_file):
    """save the scraped data into a CSV file"""
    for key in data:
        if not isinstance(data[key], list):
            data[key] = [data[key]]

    file_exists = os.path.isfile(output_file)

    df = pd.DataFrame(data)
    df.to_csv(output_file, mode='a', index=False, header=not file_exists)
    # df.to_csv(output_file, index=False)


def is_book_scraped(session, i):
    """Check if the book is already in the database based on top10k value"""
    return session.query(Book).filter(Book.top10k == i).first()


if __name__ == "__main__":

    input_csv = "data_csv/top_10k_books.csv"
    # input_csv = "data_csv/top3.csv"
    output_csv = "data_csv/books-scraped.csv"
    # run_csv(input_csv, output_csv)

    book_info = read_input_csv(input_csv)
    session = create_session()



    for i, (title, author) in enumerate(book_info):
        print(f"Scraping book {i + 1} out of {len(book_info)}")
        # if the book has been scraped in the previous session - continue
        if i <2590:
            continue
        if is_book_scraped(session, i + 1):
            print(f"Book {i + 1} is already in the database")
            continue

        title = translate_danish_to_english(title)
        author = translate_danish_to_english(author) if not type(author)==float else None

        search_page = query_saxo_with_title_or_isbn(title)  # get the search page requrst.text
        time.sleep(randint(1, 2))
        search_page_book_info = step_find_book_in_search_results(search_page, author,
                                                                 title)  # find the matching book and return its info
        if search_page_book_info == 'N/A':  # case when the book can't be found in the saxo database
            book_not_found_in_search_results_title(title, author, session)
            continue

        book_page_html = create_browser_and_wait_for_page_load(
            search_page_book_info["Url"])  # get the fully loaded book page html
        book_details_dict = extract_book_details_dict(book_page_html)
        book_details_dict["Recommendations"] = extract_recommendations_list(book_page_html)
        book_details_dict["Top10k"] = i + 1

        print(book_details_dict)
        save_book_details_to_database(book_details_dict, session)
        time.sleep(randint(1, 2))
