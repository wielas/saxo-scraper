import logging
import os
import time
import json

import requests
from bs4 import BeautifulSoup
import pandas as pd
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException


def translate_danish_to_english(text):
    translations = {
        'æ': 'ae',
        'ø': 'oe',
        'å': 'aa',
        'Æ': 'Ae',
        'Ø': 'Oe',
        'Å': 'Aa'
    }

    for danish_char, english_char in translations.items():
        text = text.replace(danish_char, english_char)

    return text


def query_saxo_with_title_or_isbn(title):
    """Search for the book on Saxo.com """
    search_url = f"https://www.saxo.com/dk/products/search?query={title.replace(' ', '+')}"
    response = requests.get(search_url)

    if response.status_code == 200:
        return response.text

    else:
        logging.exception(f"Failed to fetch search results from Saxo.com. Status code: {response.status_code}")
        return None


def is_book_correct(author_local, book_parsed):
    """Parse the first author and compare it to the extracted authors. Return True if the names match."""
    author_local = translate_danish_to_english(author_local.lower().replace('"', "").split(',')[0])
    author_extracted = [translate_danish_to_english(auth.lower()) for auth in list(book_parsed["Authors"])]
    return author_local in author_extracted and book_parsed["Work"] in ["Bog", "Brugt bog"]


def step_find_book_in_search_results(html_content_search_page, author, title):
    """Parse the search page and find the book's detail page link. Return it if found. Otherwise, return None."""
    try:
        soup_search_page = BeautifulSoup(html_content_search_page, "html.parser")
        for book in soup_search_page.find_all("div", class_="product-list-teaser"):
            book_parsed = translate_danish_to_english(book.find("a").get("data-val"))
            book_parsed = json.loads(book_parsed)

            # verify that the book matches the search criteria (author and paperbook)
            if is_book_correct(author, book_parsed):
                print(book_parsed)
                return book_parsed

        logging.exception(f"Failed to find the book in the search results. Title: {title}, Author: {author}")
        return None

    except:
        logging.error(f"Failed to parse the search results. Title: {title}, Author: {author}")
        return None


def create_browser_and_wait_for_page_load(book_detail_page_url):
    """Create a browser and wait for the page to load, then return the page source"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    with Chrome(options=chrome_options) as browser:
        browser.get(book_detail_page_url)
        try:
            WebDriverWait(browser, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')
            WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "book-slick-slider")))
            time.sleep(1)
            html = browser.page_source
        except TimeoutException:
            print('kurdefiks')
            logging.error(f"Failed to load the page. URL: {book_detail_page_url}")
            html = ""

    return html


def extract_book_details_dict(book_page_html):
    """ Scrape the book's details and recommendations from its page """

    soup = BeautifulSoup(book_page_html, "html.parser")

    # Extract the title
    title = translate_danish_to_english(soup.find("h1", class_="text-xl sm:text-l text-800 mb-0").text.strip())

    # Extract the authors
    author_tags = soup.find('div', class_='text-s product-autor').find_all('a', class_='link link--black')
    authors = [translate_danish_to_english(tag.get_text(strip=True)) for tag in author_tags if tag != "&"]

    # Extract the book details messy trash
    details = soup.find("ul", class_="description-dot-list")

    # Extract the product description
    description_div = soup.find("p", class_="mb-0")
    product_description = description_div.text.strip()

    # Extract the rating and number of reviews
    full_reviews = soup.find("div", class_="product-rating")

    rating = full_reviews.find('span', class_="text-l text-800").text.strip()
    rating = float(rating.replace(",", "."))
    num_of_reviews = full_reviews.find('span', class_="text-s").text.strip()
    num_of_reviews = int(num_of_reviews.replace("(", "").replace(")", ""))

    # Create the dict
    details_dict = book_details_to_dict(details)
    details_dict["Title"] = title
    details_dict["Authors"] = authors
    details_dict["NumOfRatings"] = num_of_reviews
    details_dict["Rating"] = rating
    details_dict["Description"] = product_description
    return details_dict


def extract_recommendations_list(book_page_html):  # TODO extract only andre kobte ogsa, not the author recommendations
    """Scrape the book's recommendations from its page"""
    soup = BeautifulSoup(book_page_html, "html.parser")
    recommendations_isbn = []

    recommendations = soup.find("div", id="product-page-banner-container").find("div",
                                                                                class_="book-slick-slider slick-initialized slick-slider")
    cover_container = recommendations.find_all("div", class_=lambda e: e.startswith('new-teaser') if e else False)
    for cover in cover_container:
        isbn = cover.find("a", class_="cover-container").get('data-product-identifier')
        if isbn:
            recommendations_isbn.append(isbn)
        else:
            logging.error(f"Failed to extract the recommendation from the book page.")
    return recommendations_isbn


def book_details_to_dict(details):
    """Structure the book details into a dict and return a ready-to-csv-save dict."""
    book_details = {}
    key_mapping = {
        "Sprog": "Language",
        "Sidetal": "PageCount",
        "Udgivelsesdato": "PublishedDate",
        "ISBN13": "ISBN",
        "Forlag": "Publisher",
        "Format": "Format",
    }

    for li in details.find_all('li'):
        key_span = li.find('span', class_='text-700')
        if key_span:
            key = key_span.text.strip()
            # Remove the key_span from the li to easily extract the remaining text
            key_span.extract()
            value = li.text.strip()
            # Map the extracted key to the desired dictionary key and set the value
            if key in key_mapping:
                # Convert numeric values from strings to their appropriate types
                if key_mapping[key] in ["PageCount"]:
                    value = int(value)

                book_details[key_mapping[key]] = value

    return book_details
