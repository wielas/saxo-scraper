import logging
import time
import traceback
from random import randint

from database import Author, Book
from scraping_common import create_browser_and_wait_for_page_load, extract_book_details_dict, \
    query_saxo_with_title_or_isbn, step_find_book_in_search_results

ISBN = "ISBN"
TITLE = "Title"
PAGE_COUNT = "PageCount"
PUBLISHED_DATE = "PublishedDate"
PUBLISHER = "Publisher"
FORMAT = "Format"
NUM_OF_RATINGS = "NumOfRatings"
RATING = "Rating"
DESCRIPTION = "Description"
TOP10K = "Top10k"
AUTHORS = "Authors"
RECOMMENDATIONS = "Recommendations"

BOOK_NOT_AVAILABLE = {ISBN: '9788763840958',
                      PAGE_COUNT: 0,
                      PUBLISHED_DATE: 'N/A',
                      PUBLISHER: 'N/A',
                      FORMAT: 'N/A',
                      TITLE: 'N/A',
                      AUTHORS: [],
                      NUM_OF_RATINGS: 0,
                      RATING: 0,
                      DESCRIPTION: "N/A",
                      RECOMMENDATIONS: [],
                      TOP10K: 0}


def save_book_details_to_database(book_details, session, parent=None):
    """Save the scraped data into the database."""
    try:
        book = get_book_by_isbn(session, book_details[ISBN])
        if book is None:
            book = create_new_book(book_details)
            session.add(book)
            session.flush()

            add_authors_to_book(book, book_details[AUTHORS], session)

        if parent:
            parent.recommendations.append(book)

        # add the recommendations
        if book_details["Top10k"]:
            book.top10k = book_details["Top10k"]  # in case a book details were scraped from recommendations before
            save_recommended_books(book, book_details[RECOMMENDATIONS], session)

        session.commit()

    except Exception as e:
        session.rollback()
        print(f"An error occurred while saving the book {book_details[TITLE]} details: {e}")
        logging.error(f"In book {book_details[TITLE]} an error occurred while saving the book details: {e}")
        logging.error(traceback.format_exc())


def get_book_by_isbn(session, isbn):
    return session.query(Book).filter_by(isbn=isbn).first()


def create_new_book(book_details):
    return Book(
        isbn=book_details[ISBN],
        title=book_details[TITLE],
        page_count=book_details[PAGE_COUNT],
        published_date=book_details[PUBLISHED_DATE],
        publisher=book_details[PUBLISHER],
        format=book_details[FORMAT],
        num_of_ratings=int(book_details[NUM_OF_RATINGS]),
        rating=book_details[RATING],
        description=book_details[DESCRIPTION],
        top10k=book_details[TOP10K]
    )


def add_authors_to_book(book, authors, session):
    for author_name in authors:
        author = session.query(Author).filter_by(name=author_name).first()
        if not author:
            author = Author(name=author_name)
            session.add(author)
        book.authors.append(author)


def save_recommended_books(book, recommended_isbns, session):
    for recommended_isbn in recommended_isbns:
        scrape_and_save_recommended_book(book, recommended_isbn, session)
        time.sleep(1)


def scrape_and_save_recommended_book(parent_book, book_isbn, session):  # todo optimize
    """Scrape the details of a recommended book if it does not exist in the database"""
    try:
        recommended_book = get_book_by_isbn(session, book_isbn)
        if not recommended_book:
            book_page_html = get_book_page_html(book_isbn)
            if book_page_html:
                book_details_dict = get_book_details_dict(book_page_html)
                save_book_details_to_database(book_details_dict, session, parent_book)
            else:  # case when there's many book results for the same isbn
                search_page = query_saxo_with_title_or_isbn(book_isbn)  # get the search page requrst.text
                search_page_book_info = step_find_book_in_search_results(search_page)
                if search_page_book_info == 'N/A':
                    book_not_found_in_search_results_isbn(book_isbn, session)

                book_page_html = create_browser_and_wait_for_page_load(search_page_book_info["Url"])
                book_details_dict = get_book_details_dict(book_page_html)
                save_book_details_to_database(book_details_dict, session, parent_book)
                logging.info(f"Recovery succeeded for {book_isbn}")
    except Exception as e:
        logging.error(f"Scraping the recommended book with ISBN {book_isbn}: {e}\n possibly many entries -- retrying.")
        logging.error(traceback.format_exc())
        # try:
        #     search_page = query_saxo_with_title_or_isbn(book_isbn)  # get the search page requrst.text
        #     search_page_book_info = step_find_book_in_search_results(search_page)
        #     book_page_html = create_browser_and_wait_for_page_load(search_page_book_info["Url"])
        #     book_details_dict = get_book_details_dict(book_page_html)
        #     save_book_details_to_database(book_details_dict, session, parent_book)
        #     logging.info(f"Recovery succeeded for {book_isbn}")
        # except Exception as e:
        #     logging.error(f"Recovery failed for {book_isbn}: {e}")
        #     logging.error(traceback.format_exc())


def get_book_page_html(book_isbn):
    search_url = "https://www.saxo.com/dk/products/search?query={}".format(book_isbn)
    return create_browser_and_wait_for_page_load(search_url)


def get_book_details_dict(book_page_html):
    book_details_dict = extract_book_details_dict(book_page_html)
    book_details_dict[RECOMMENDATIONS] = []
    book_details_dict[TOP10K] = 0
    return book_details_dict


def book_not_found_in_search_results_isbn(isbn, session):
    """Log the error and save the book with a default dict"""
    logging.error(f"No search results found for {isbn}")
    new = BOOK_NOT_AVAILABLE.copy()
    new[ISBN] = isbn
    save_book_details_to_database(new, session)


def book_not_found_in_search_results_title(title, author, session):
    """Log the error and save the book with a default dict"""
    logging.error(f"No search results found for {title} by {author}")
    new = BOOK_NOT_AVAILABLE.copy()
    new[TITLE] = title
    new[AUTHORS] = [author]
    save_book_details_to_database(BOOK_NOT_AVAILABLE, session)
