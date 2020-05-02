from html_table_parser import HTMLTreeNode
from html_table_parser import HTMLTreeParser
from io import BytesIO
import logging
from pdfminer.high_level import extract_text
import requests
import sqlite3

from council_members import LegislatorDatabase
from legislation_details import LegislationDetails
from legislation_details import DetailsDatabase

class LegislationVote:
    def __init__(self, file_number, member_id, vote_type):
        self.file_number = file_number
        self.member_id = member_id
        self.vote_type = vote_type

class VotesDatabase:
    TABLE_NAME = 'legislation_votes'

    def __init__(self):
        self.connection = sqlite3.connect('legislation.db')
        self.connection.text_factory = str
        self.cursor = self.connection.cursor()

    def remove_table(self):
        logging.debug('Dropping ' + VotesDatabase.TABLE_NAME + ' table')
        command = "DROP TABLE IF EXISTS " + VotesDatabase.TABLE_NAME + ";"
        self.cursor.execute(command)

    def create_table(self):
        logging.debug('Creating ' + VotesDatabase.TABLE_NAME + ' table')
        command = "CREATE TABLE IF NOT EXISTS " + VotesDatabase.TABLE_NAME + """ (
file_number TEXT,
member_id INTEGER,
vote_type INTEGER,
PRIMARY KEY (file_number, member_id),
FOREIGN KEY (file_number) REFERENCES legislation (file_number),
FOREIGN KEY (member_id) REFERENCES council_members (member_id)
);""";
        self.cursor.execute(command)

    def add_items(self, legislation_votes):
        logging.debug('Adding ' + str(len(legislation_votes)) + ' items to ' + VotesDatabase.TABLE_NAME + ' table')
        keys = ['file_number', 'member_id', 'vote_type']
        all_values = [(vote.file_number, vote.member_id, vote.vote_type) for vote in legislation_votes]
        command = "INSERT OR REPLACE INTO " + VotesDatabase.TABLE_NAME + " (" + ', '.join(keys) + ") VALUES (" + ','.join(['?' for k in keys]) + ");"
        self.cursor.executemany(command, all_values)

    def get_items(self):
        keys = ['file_number', 'member_id', 'vote_type']
        command = "SELECT " + ', '.join(keys) + " FROM " + VotesDatabase.TABLE_NAME + ";"
        all_results = self.cursor.execute(command).fetchall()
        return [LegislationVote(r[0], r[1], r[2]) for r in all_results]

    def close(self):
        logging.debug('Closed connection to ' + VotesDatabase.TABLE_NAME + ' table')
        self.connection.commit()
        self.connection.close()

class VoteParser:
    def __init__(self, detail_item):
        self.file_number = detail_item.file_number
        self.action_date = detail_item.action_date
        legislators_db = LegislatorDatabase()
        self.legislators = list(filter(lambda l: (l.was_active_on(self.action_date)), legislators_db.get_members()))

    def parse_from_html(self, html_tree):
        votes_table = html_tree.branches_matching('table', 'Person Name')
        votes_body = votes_table[0].branches_with_tag('tbody')
        votes_entries = votes_body[0].leaf_data()

        if len(votes_entries) < 2 or 'No records to display' in votes_entries:
            logging.debug('No individual voting record in html for ' + self.file_number)
            return None

        keywords = ['Aye', 'No', 'Absent', 'Abstained', 'Excused']
        votes = []
        for i in range(0, len(votes_entries), 2):
            # Normalize and uppercase names to match DB, eg Guillén to GUILLEN
            # Could use unidecode library if there are more cases needed
            full_name = votes_entries[i].replace('é', 'e').upper()
            vote = votes_entries[i+1]
            matching_legislator = None
            vote_type = -1
            for legislator in self.legislators:
                if legislator.last_name.split(' ')[-1] in full_name:
                    matching_legislator = legislator
                    try:
                        vote_type = keywords.index(vote) + 1
                        break
                    except ValueError:
                        logging.warning('Could not find how ' + legislator.full_name() + ' voted (' + vote + ') on ' + self.file_number)
                        break

            if matching_legislator == None:
                logging.warning('Could not find legislator ' + full_name + ' who voted (' + vote + ') on ' + self.file_number)
            else:
                logging.debug('Adding legislation vote of ' + str(vote_type) + ' from ' + str(matching_legislator.full_name()) + ' on ' + self.file_number)
                votes.append(LegislationVote(self.file_number, matching_legislator.member_id, vote_type))
            
        logging.debug('Parsed ' + str(len(votes)) + ' votes from html on ' + self.file_number)
        return votes

    def parse_from_pdf(self, raw_text):
        keywords = ['AYES', 'NOES', 'ABSENT', 'ABSTENTION', 'EXCUSED', 'ATTEST']
        last_keywords = [raw_text.rfind(k) for k in keywords]

        votes = []
        for legislator in self.legislators:
            try:
                name_index = raw_text.rindex(legislator.last_name)
                min_index = min(range(len(last_keywords)), key = lambda i: name_index - last_keywords[i] if last_keywords[i] != -1 and name_index >= last_keywords[i] else 999999 - i)
                if min_index >= len(keywords) - 1:
                    raise ValueError("Last occurence of " + legislator.full_name() + " appeared before all of the voting keywords.")
                vote_type = min_index + 1
                logging.debug('Adding legislation vote of ' + str(vote_type) + ' from ' + legislator.full_name() + ' on ' + self.file_number)
                votes.append(LegislationVote(self.file_number, legislator.member_id, vote_type))
            except ValueError:
                logging.warning('Could not find how ' + legislator.full_name() + ' voted on ' + self.file_number)
                votes.append(LegislationVote(self.file_number, legislator.member_id, -1))

        logging.debug('Parsed ' + str(len(votes)) + ' votes from html on ' + self.file_number)
        return votes

def fetchPDF(url):
    logging.info('Requesting PDF from ' + url)
    request = requests.get(url)
    logging.info("Success!")
    return request.content

def loadPDF(file_number, url, store_locally=False):
    filename = file_number + ".pdf"
    logging.debug('Loading PDF with local storage file ' + filename)
    try:
        f = open(filename, 'rb')
        content = f.read()
        f.close()
        logging.debug('Loaded from local storage')
        return content
    except IOError:
        logging.debug('Local storage file not found')
        content = fetchPDF(url)
        if not store_locally:
            return content
        f = open(filename, 'wb')
        f.write(content)
        f.close()
        return content

def extractText(pdf_contents):
    pdf_file = BytesIO(pdf_contents)
    text = extract_text(pdf_file)
    pdf_file.close()
    return text

def fetchHTML(url):
    logging.info('Requesting page source from ' + url)
    request = requests.get(url)
    logging.info("Success!")
    return request.text

def loadHTML(file_number, url, store_locally=False):
    filename = file_number + "-votes.html"
    logging.debug('Loading html with local storage file ' + filename)
    try:
        f = open(filename, 'r')
        text = f.read()
        f.close()
        logging.debug('Loaded from local storage')
        return text
    except IOError:
        logging.debug('Local storage file not found')
        text = fetchHTML(url)
        if not store_locally:
            return text
        f = open(filename, 'w')
        f.write(text)
        f.close()
        return text

def extractHTMLTree(html_content):
    parser = HTMLTreeParser()
    parser.feed(html_content)
    html_tree = parser.get_parsed_trees()[0]
    parser.close()
    return html_tree

def exportVotes(votes):
    database = VotesDatabase()
    database.remove_table()
    database.create_table()
    database.add_items(votes)
    database.close()

def main():
    details_db = DetailsDatabase()
    detail_items = details_db.get_items()
    all_votes = []
    for item in detail_items:
        parser = VoteParser(item)

        if item.action_details_link != None:
            html_content = loadHTML(item.file_number, item.action_details_link, True)
            html_tree = extractHTMLTree(html_content)
            html_votes = parser.parse_from_html(html_tree)
            if html_votes != None:
                all_votes += html_votes
                continue

        if item.pdf_link != None:
            pdf_content = loadPDF(item.file_number, item.pdf_link, True)
            pdf_text = extractText(pdf_content)
            all_votes += parser.parse_from_pdf(pdf_text)
        else:
            logging.warning('Skipping ' + item.file_number)
        
    exportVotes(all_votes)

if __name__ == "__main__": 
    main() 

