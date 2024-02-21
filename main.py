import logging
import time
import os
import pandas as pd
from random import randint
from scraping_common import find_book_in_search_results, search_for_book, extract_book_details_and_recommendations, \
    translate_danish_to_english
from scraping_sql import run_sql

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
        if not isinstance(data[key], list):  # Check if the value is not already a list
            data[key] = [data[key]]

    # Check if the file exists to avoid adding header again
    file_exists = os.path.isfile(output_file)

    # Append the DataFrame to a CSV file with no index and header only if the file does not exist
    df = pd.DataFrame(data)
    df.to_csv(output_file, mode='a', index=False, header=not file_exists)
    # df.to_csv(output_file, index=False)


def run_csv(book_page_url, output_csv):
    """Run the scraping process for a single book page and append the details to a CSV file."""
    book_details = extract_book_details_and_recommendations(book_page_url)
    save_to_csv(book_details, output_csv)
    time.sleep(randint(1, 2))


def extract_book_page_details(title, author):
    print("TITLE: ", title, "AUTHORS:", author)
    search_result = search_for_book(title)
    if search_result is None:
        print("No search results found for", title)
        logging.error(f"No search results found for {title}")

    book_page_details = find_book_in_search_results(search_result, author, title)
    return book_page_details


if __name__ == "__main__":

    input_csv = "data_csv/top3.csv"
    output_csv = "data_csv/books-scraped.csv"
    # run_csv(input_csv, output_csv)

    book_info = read_input_csv(input_csv)
    for title, author in book_info:
        title = translate_danish_to_english(title)
        author = translate_danish_to_english(author)

        book_page_details = extract_book_page_details(title, author)
        print(book_page_details)
        book_page_url = book_page_details["Url"]
        # run_csv(book_page_url, output_csv)
        run_sql(book_page_details)
