import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
	'-c', '--cache',
	help="Store a local copy of any downloaded files",
    action="store_true", dest="should_cache",
    default=False,
)
parser.add_argument(
	'-p', '--poll',
	help="Poll for all missing legislation items",
    action="store_true", dest="should_poll",
    default=False,
)
parser.add_argument(
	'-f', '--file',
	help="Specify a file id to scrape",
    dest="file_id",
)
args, unused = parser.parse_known_args()

from logging_setup import logging
from legislation import LegislationDatabase
from legislation_details import DetailsDatabase
from legislation_details import loadHTML
from legislation_details import loadHTMLDetails
from record_votes import VotesDatabase
import record_votes

def fill(file_number, should_cache):
    logging.info("Will fill voting info for " + file_number)

    legislation_db = LegislationDatabase()
    legislation_item = legislation_db.get_item(file_number)
    legislation_db.close()

    legislation_details_html = loadHTML(file_number, legislation_item.link.decode('utf8'), should_cache)
    details_item = loadHTMLDetails(legislation_details_html)

    details_db = DetailsDatabase()
    details_db.add_items([details_item])
    details_db.close()

    parser = record_votes.VoteParser(details_item)
    all_votes = None

    if details_item.action_details_link != None:
        html_content = record_votes.loadHTML(details_item.file_number, details_item.action_details_link, should_cache)
        html_tree = record_votes.extractHTMLTree(html_content)
        all_votes = parser.parse_from_html(html_tree)

    if all_votes == None and details_item.pdf_link != None:
        pdf_content = record_votes.loadPDF(details_item.file_number, details_item.pdf_link, should_cache)
        pdf_text = record_votes.extractText(pdf_content)
        all_votes = parser.parse_from_pdf(pdf_text)

    if all_votes == None:
        logging.warning('Could not parse ' + file_number)
        # Add a fake vote so that fillNext() doesn't try this one again
        all_votes = [record_votes.LegislationVote(file_number, -1, -1)]
        
    database = VotesDatabase()
    database.add_items(all_votes)
    database.close()

def fillNext(should_cache):
    legislation_db = LegislationDatabase()
    votes_db = VotesDatabase()
    query = "SELECT file_number FROM " + legislation_db.TABLE_NAME + """ ldb
    WHERE NOT EXISTS (SELECT NULL 
        FROM """ + votes_db.TABLE_NAME + """ vdb 
        WHERE ldb.file_number LIKE vdb.file_number)
    ORDER BY file_number DESC
    LIMIT 1;"""
    logging.debug("Query for missing file numbers: " + query)

    result = legislation_db.cursor.execute(query).fetchone()
    legislation_db.close()
    votes_db.close()

    if result == None:
    	logging.info("No file numbers missing votes!")
    	return False

    file_number = result[0].decode('utf8')
    fill(file_number, should_cache)
    return True

if __name__ == "__main__":
	file_number = args.file_id
	should_cache = args.should_cache
	should_poll = args.should_poll
	if file_number != None:
		fill(file_number, should_cache)
	elif should_poll:
		while (fillNext(should_cache) == True):
			logging.debug('Sending another request')
	else:
		fillNext(should_cache)
