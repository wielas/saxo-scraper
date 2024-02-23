import logging

from database import Author, Book
from scraping_common import create_browser_and_wait_for_page_load, extract_book_details_dict

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
            book.top10k = book_details["Top10k"]  # in case a book was scraped from recommendations before
            save_recommended_books(book, book_details[RECOMMENDATIONS], session)

        session.commit()

    except Exception as e:
        session.rollback()
        print(f"An error occurred while saving the book {book_details[TITLE]} details: {e}")
        logging.error(f"In book {book_details[TITLE]} an error occurred while saving the book details: {e}")


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
        description='desc',
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


def scrape_and_save_recommended_book(parent_book, book_isbn, session):
    """Scrape the details of a recommended book if it does not exist in the database"""
    try:
        recommended_book = get_book_by_isbn(session, book_isbn)
        if not recommended_book:
            book_page_html = get_book_page_html(book_isbn)
            book_details_dict = get_book_details_dict(book_page_html)
            save_book_details_to_database(book_details_dict, session, parent_book)
    except Exception as e:
        logging.error(f"In book {book_isbn} an error occurred while scraping the recommended book details: {e}")


def get_book_page_html(book_isbn):
    search_url = "https://www.saxo.com/dk/products/search?query={}".format(book_isbn)
    return create_browser_and_wait_for_page_load(search_url)


def get_book_details_dict(book_page_html):
    book_details_dict = extract_book_details_dict(book_page_html)
    book_details_dict[RECOMMENDATIONS] = []
    book_details_dict[TOP10K] = 0
    return book_details_dict
