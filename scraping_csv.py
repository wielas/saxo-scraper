import json
import logging
import time
from random import randint

import requests
from bs4 import BeautifulSoup
import pandas as pd
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException


def read_input_csv(file_path):
    """Read the CSV file to get the list of tuples (book_title, book_author) and return it as a list"""
    df = pd.read_csv(file_path, encoding="ISO-8859-1")
    book_info = list(zip(df["book_title"], df["book_author"]))
    return book_info


def search_for_book(title):
    """Search for the book on Saxo.com """
    search_url = f"https://www.saxo.com/dk/products/search?query={title.replace(' ', '+')}"
    response = requests.get(search_url)

    if response.status_code == 200:
        return response.text

    else:
        logging.exception(f"Failed to fetch search results from Saxo.com. Status code: {response.status_code}")
        return None



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

def is_book_correct(author_local, book_parsed):
    """Parse the first author and compare it to the extracted authors. Return True if the names match."""
    author_local = author_local.lower().replace('"', "").split(',')[0]
    author_extracted = [auth.lower() for auth in list(book_parsed["Authors"])]
    return author_local in author_extracted and book_parsed["Work"] in ["Bog", "Brugt bog"]


def find_book_in_search_results(html_content_search_page, author, title):
    """Parse the search page and find the book's detail page link. Return it if found. Otherwise, return None."""
    print(author)
    try:
        soup_search_page = BeautifulSoup(html_content_search_page, "html.parser")
        for book in soup_search_page.find_all("div", class_="product-list-teaser"):
            book_parsed = json.loads(book.find("a").get("data-val"))

            # verify that the book matches the search criteria (author and paperbook)
            if is_book_correct(author, book_parsed):
                print(book_parsed)
                return book_parsed["Url"]

        logging.exception(f"Failed to find the book in the search results. Title: {title}, Author: {author}")
        return None

    except:
        logging.error(f"Failed to parse the search results. Title: {title}, Author: {author}")
        return None


def extract_book_details(page_url):
    """ Scrape the book's details and recommendations from its page """

    ## Requests
    print(page_url)
    response = requests.get(page_url)
    html = response.text

    # Selenium
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    with Chrome(options=chrome_options) as browser:
        browser.get(page_url)
        try:
            WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.ID, "product-page-banner-container")))
            html = browser.page_source
        except TimeoutException:
            logging.error(f"Failed to load the page. URL: {page_url}")
            html = ""

    if html:
        soup = BeautifulSoup(html, "html.parser")
    else:
        logging.error(f"Failed to fetch the book page. URL: {page_url}")

    # Extract the book details
    details = soup.find("ul", class_="description-dot-list").find_all("li")

    # Extract the product description
    description_div = soup.find("p", class_="mb-0")
    product_description = description_div.text.strip()

    # Extract the rating
    full_reviews = soup.find("div", class_="product-rating")

    rating = full_reviews.find('span', class_="text-l text-800").text.strip()
    num_of_reviews = full_reviews.find('span', class_="text-s")
    if num_of_reviews:
        num_of_reviews = num_of_reviews.text.strip()

    # Extract the recommendations
    recommendations = soup.find("div", id_="product-page-banner-container")
    print(recommendations)

    # Create a dict to store the book details ready to save to csv
    book_details = {}

    for detail in details:
        key_span = detail.find("span", class_="text-700")
        key_text = key_span.text.strip().lower()
        key_span.extract()
        value_text = detail.text.strip()
        clean_key = key_text.rstrip(':').lower()
        book_details[clean_key] = value_text

    book_details["rating"] = rating
    book_details["num_of_reviews"] = num_of_reviews
    # book_details["recommendations"] = len(recommendations)
    book_details["description"] = product_description
    return book_details
