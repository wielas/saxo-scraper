import logging
import time

from scraping_csv import find_book_in_search_results, extract_book_details, search_for_book, read_input_csv, save_to_csv

logging.basicConfig(filename='data_csv/app_errors.log', level=logging.ERROR,
                    format='%(asctime)s:%(levelname)s:%(message)s')



def run_csv(input_csv, output_csv):
    """Main function to run the scraping process. It reads the input CSV file, searches for each book, and extracts the details."""
    book_info = read_input_csv(input_csv)
    for title, author in book_info:
        print("TITLE: ", title, "AUTHORS:", author)
        search_result = search_for_book(title)
        if search_result is None:
            continue

        book_page_url = find_book_in_search_results(search_result, author, title)

        book_details = extract_book_details(book_page_url)
        # save_to_csv(book_details, output_csv)
        # time.sleep(randint(1, 3))



if __name__ == "__main__":

    input_csv = "data/top3.csv"
    output_csv = "data/books-scraped.csv"
    run_csv(input_csv, output_csv)
