import json
import logging
import time
from random import randint

import requests
from bs4 import BeautifulSoup
import pandas as pd


def read_input_csv(file_path):
    # Read the CSV file to get the list of tuples (book_title, book_author) and return it as a list
    df = pd.read_csv(file_path, encoding="windows-1250")
    book_info = list(zip(df["book_title"], df["book_author"]))
    return book_info


def search_for_book(title):
    # Search for the book on Saxo.com
    search_url = f"https://www.saxo.com/dk/products/search?query={title.replace(' ', '+')}"
    response = requests.get(search_url)

    if response.status_code == 200:
        return response.text

    else:
        logging.exception(f"Failed to fetch search results from Saxo.com. Status code: {response.status_code}")
        return None


def find_book_in_search_results(html_content_search_page, author, title):
    # Find the book's detail page link and return it
    try:
        soup_search_page = BeautifulSoup(html_content_search_page, "html.parser")
        for book in soup_search_page.find_all("div", class_="product-list-teaser"):

            book_parsed = json.loads(book.find("a").get("data-val"))
            # verify that the book matches the search criteria (author and paperbook)
            if author in book_parsed["Authors"] and book_parsed["Work"] in ["Bog", "Brugt bog"]:
                print(book_parsed)
                return book_parsed["Url"]

        logging.exception(f"Failed to find the book in the search results. Title: {title}, Author: {author}")
        return None

    except:
        logging.error(f"Failed to parse the search results. Title: {title}, Author: {author}")
        return None


def extract_book_details(page_url):
    """ Scrape the book's details and recommendations from its page """
    response = requests.get(page_url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Extract the book details
    details = soup.find("ul", class_="description-dot-list").find_all("li")
    book_details = {}

    for detail in details:
        key_span = detail.find("span", class_="text-700")
        key_text = key_span.text.strip().lower()
        key_span.extract()
        value_text = detail.text.strip()
        clean_key = key_text.rstrip(':').lower()
        book_details[clean_key] = value_text

    # Extract the product description
    description_div = soup.find("p", class_="mb-0")
    product_description = description_div.text.strip()
    book_details["description"] = product_description

    # Extract the rating
    full_reviews = soup.find("div", class_="product-rating")
    print(full_reviews)
    rating = full_reviews.find('span', class_="text-l text-800").text.strip()
    num_of_reviews = full_reviews.find('span', class_="text-s").text.strip()  # todo: fix this

    print(rating)

    # Extract the recommendations


    print(book_details)


def save_to_csv(data, output_file):
    # Use Pandas to save the scraped data into a CSV file
    pass


def run(input_csv, output_csv):
    book_info = read_input_csv(input_csv)
    for title, author in book_info:
        search_result = search_for_book(title)

        if search_result is None:
            continue

        book_page_url = find_book_in_search_results(search_result, author, title)

        book_details = extract_book_details(book_page_url)
        # save_to_csv(book_details, output_csv)
        # time.sleep(randint(1, 3))
        break


if __name__ == "__main__":
    logging.basicConfig(filename='app_errors.log', level=logging.ERROR,
                        format='%(asctime)s:%(levelname)s:%(message)s')

    input_csv = "data/top_10k_books.csv"
    output_csv = "data/books-scraped.csv"

    run(input_csv, output_csv)
