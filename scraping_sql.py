import logging

from database import Author, Book
from scraping_common import query_saxo_with_title_or_isbn, create_browser_and_wait_for_page_load, \
    extract_book_details_dict


def save_to_sql(book_details, session, parent=None):  # TODO check if isbn exists, add the parent isbn linking
    """Save the scraped data into the database."""
    try:
        if not session.query(Book).filter_by(isbn=book_details["ISBN"]).first():
            book = Book(
                isbn=book_details["ISBN"],
                title=book_details["Title"],
                page_count=book_details["PageCount"],
                published_date=book_details["PublishedDate"],
                publisher=book_details["Publisher"],
                format=book_details["Format"],
                num_of_ratings=int(book_details["NumOfRatings"]),  # Make sure it's an int
                rating=book_details["Rating"],
                description=book_details["Description"],
                top10k=book_details["Top10k"]
            )
            session.add(book)
            session.flush()

            # add the authors
            for author_name in book_details["Authors"]:
                author = session.query(Author).filter_by(name=author_name).first()
                if not author:
                    author = Author(name=author_name)
                    session.add(author)
                book.authors.append(author)

        # add the recommendations
        if book_details["Top10k"]:  # TODO link the books
            for recommended_isbn in book_details["Recommendations"]:
                scrape_recommended_book_if_non_existent(book_details["ISBN"], recommended_isbn, session)
                print(f"Recommended book with ISBN {recommended_isbn} saved in the database.")

        session.commit()
    except Exception as e:
        session.rollback()
        title = book_details["Title"]
        print(f"An error occurred while saving the book {title} details: {e}")
        logging.error(f"In book {title} an error occurred while saving the book details: {e}")


def scrape_recommended_book_if_non_existent(parent_book, book_isbn, session):
    """Scrape the details of a recommended book if it does not exist in the database"""
    try:
        recommended_book = session.query(Book).filter_by(isbn=book_isbn).first()
        if not recommended_book:
            search_url = f"https://www.saxo.com/dk/products/search?query={book_isbn}"
            book_page_html = create_browser_and_wait_for_page_load(search_url)  # get the fully loaded book page html
            book_details_dict = extract_book_details_dict(book_page_html)
            book_details_dict["Recommendations"] = []
            book_details_dict["Top10k"] = 0
            save_to_sql(book_details_dict, session)
    except Exception as e:
        print(f"An error occurred while scraping the recommended book {book_isbn} details: {e}")
        logging.error(f"In book {book_isbn} an error occurred while scraping the recommended book details: {e}")
