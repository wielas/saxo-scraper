import json
import logging
import os
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

from scraping_common import search_for_book, find_book_in_search_results, extract_book_details_and_recommendations, \
    extract_recommendations
from database import Base, Author, Book, engine, sessionmaker, create_session


def run_sql(book_page_details):
    """Run the scraping process for a single book page and save the details to the database."""

    book_details_and_recommendations = extract_book_details_and_recommendations(book_page_details["Url"])
    # book_dict = create_dict_from_book_details(book_page_details, book_details_and_recommendations)
    book_details_and_recommendations["Title"] = book_page_details["Name"]
    book_details_and_recommendations["Authors"] = book_page_details["Authors"]

    print(json.dumps(book_details_and_recommendations, indent=4))
    session = create_session()
    save_to_sql(book_details_and_recommendations, session)
    session.close()



def save_to_sql(book_details, session):
    """Save the scraped data into the database."""
    try:
        book = Book(
            isbn=book_details["ISBN"],
            title=book_details["Title"],
            page_count=book_details["PageCount"],
            published_date=book_details["PublishedDate"],
            publisher=book_details["Publisher"],
            format=book_details["Format"],
            original_language=book_details["OriginalLanguage"],
            num_of_ratings=int(book_details["NumOfRatings"]),  # Make sure it's an int
            rating=book_details["Rating"],
            description=book_details["Description"]
        )

        # Add the authors, checking if they already exist
        for author_name in book_details["Authors"]:  # todo add authors one by one
            author = session.query(Author).filter_by(name=author_name).first()
            if not author:
                author = Author(name=author_name)
                session.add(author)
            book.authors.append(author)

        # Add the recommendations
        for recommended_isbn in book_details["Recommendations"]:
            recommended_book = session.query(Book).filter_by(isbn=recommended_isbn).first()

            if recommended_book:
                book.recommendations.append(recommended_book)

            else:
                # TODO create a detail scraping one level down if non existent
                # todo modify extraction to add recommendations only in case of the top10k
                recommended_book = Book(isbn=recommended_isbn, title='Unknown')
                session.add(recommended_book)
                book.recommendations.append(recommended_book)
                print(f"Recommended book with ISBN {recommended_isbn} not found in the database.")

        session.add(book)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"An error occurred while saving the book details: {e}")






# def extract_book_recommendations_from_page(book_page_url):
#     """Extract the book recommendations from the book's page"""
#     options = Options()
#     options.headless = True
#
#     # run the driver and wait for scripts to load
#     with Chrome(options=options) as browser:
#         browser.get(book_page_url)
#         try:
#             WebDriverWait(browser, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')
#             WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "book-slick-slider")))
#             html = browser.page_source
#         except TimeoutException:
#             logging.error(f"Page load timeout on {book_page_url}")
#             return None
#
#     # Extract the recommendations
#     soup = BeautifulSoup(html, "html.parser")
#     recommendations = extract_recommendations(soup)
#     return recommendations







