from html_table_parser import HTMLTreeNode
from html_table_parser import HTMLTreeParser
from logging_setup import logging
import requests
import sqlite3
import xml.etree.ElementTree as ET

from legislation import LegislationItem
from legislation import LegislationDatabase

class LegislationDetails:
    def __init__(self, file_number, status, name, title, agenda_date, action_date, pdf_link, action_details_link):
        self.file_number = file_number
        self.status = status
        self.name = name
        self.title = title
        self.agenda_date = agenda_date
        self.action_date = action_date
        self.pdf_link = pdf_link
        self.action_details_link = action_details_link

class DetailsDatabase:
    TABLE_NAME = 'legislation_details'

    def __init__(self):
        self.connection = sqlite3.connect('legislation.db')
        self.connection.text_factory = str
        self.cursor = self.connection.cursor()

    def remove_table(self):
        logging.debug('Dropping ' + DetailsDatabase.TABLE_NAME + ' table')
        command = "DROP TABLE IF EXISTS " + DetailsDatabase.TABLE_NAME + ";"
        self.cursor.execute(command)

    def create_table(self):
        logging.debug('Creating ' + DetailsDatabase.TABLE_NAME + ' table')
        command = "CREATE TABLE IF NOT EXISTS " + DetailsDatabase.TABLE_NAME + """ (
file_number TEXT NOT NULL PRIMARY KEY,
status TEXT,
name TEXT,
title TEXT,
agenda_date TEXT,
action_date TEXT,
pdf_link TEXT,
action_details_link TEXT,
FOREIGN KEY (file_number) REFERENCES legislation (file_number)
);""";
        self.cursor.execute(command)
    
    def add_items(self, legislation_details):
        logging.debug('Adding ' + str(len(legislation_details)) + ' items to ' + DetailsDatabase.TABLE_NAME + ' table')
        keys = ['file_number', 'status', 'name', 'title', 'agenda_date', 'action_date', 'pdf_link', 'action_details_link']
        all_values = [(item.file_number, item.status, item.name, item.title, item.agenda_date, item.action_date, item.pdf_link, item.action_details_link) for item in legislation_details]
        command = "INSERT OR REPLACE INTO " + DetailsDatabase.TABLE_NAME + " (" + ', '.join(keys) + ") VALUES (" + ','.join(['?' for k in keys]) + ");"
        self.cursor.executemany(command, all_values)

    def get_item(self, file_number):
        keys = ['file_number', 'status', 'name', 'title', 'agenda_date', 'action_date', 'pdf_link', 'action_details_link']
        command = "SELECT " + ', '.join(keys) + " FROM " + DetailsDatabase.TABLE_NAME + " WHERE file_number LIKE '" + file_number + "';"
        r = self.cursor.execute(command).fetchone()
        LegislationDetails(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7])

    def get_items(self):
        keys = ['file_number', 'status', 'name', 'title', 'agenda_date', 'action_date', 'pdf_link', 'action_details_link']
        command = "SELECT " + ', '.join(keys) + " FROM " + DetailsDatabase.TABLE_NAME + ";"
        all_results = self.cursor.execute(command).fetchall()
        return [LegislationDetails(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]) for r in all_results]

    def close(self):
        logging.debug('Closed connection to ' + DetailsDatabase.TABLE_NAME + ' table')
        self.connection.commit()
        self.connection.close()

def parseTagValue(tag, data_key, table_tree):
    leaves = table_tree.branches_matching(tag, data_key)[0].leaf_data()
    try:
        value = leaves[leaves.index(data_key) + 1]
        logging.debug('Successfully parsed data key ' + data_key + ' with value ' + value)
        return value
    except:
        logging.debug('Could not parse data key ' + data_key)
        return None

def parsePdfLink(table_tree):
    pdf_branches = table_tree.branches_with_data('CMS')
    if len(pdf_branches) == 0:
        logging.debug('Could not parse PDF because there is no CMS data')
        return None

    hyperlink = pdf_branches[0].attrs.get('href')
    if hyperlink == None:
        logging.debug('Could not parse PDF because there is no hyperlink for the CMS data')
        return None

    pdf_link = "https://oakland.legistar.com/" + hyperlink
    logging.debug('Successfully parsed pdf link ' + hyperlink)
    return pdf_link

def parseActionDetailsLink(table_tree):
    action_details_branches = table_tree.branches_with_data('Action details')
    if len(action_details_branches) == 0:
        logging.debug('Could not parse Action details because they were not found')
        return None
    onclick = action_details_branches[0].parent.attrs.get('onclick')
    if onclick == None:
        logging.debug('Could not parse Action details because there is no onclick in the expected location')
        return None
    click_components = onclick.split("'")
    if len(click_components) < 2:
        logging.debug('Could not parse Action details because the onclick link is not formatted as expected')
        return None

    action_link = "https://oakland.legistar.com/" + click_components[1]
    logging.debug('Successfully parsed Action details link ' + action_link)
    return action_link

def parseDetails(table_tree):
    file_number = parseTagValue('table', 'File #:', table_tree)
    status = parseTagValue('table', 'Status:', table_tree)
    name = parseTagValue('table', 'Name:', table_tree)
    title = parseTagValue('table', 'Title:', table_tree)
    agenda_date = None # todo, doesn't work with parseTagValue
    action_date = parseTagValue('table', 'Final action:', table_tree)
    pdf_link = parsePdfLink(table_tree)
    action_details_link = parseActionDetailsLink(table_tree)

    if pdf_link == None and action_details_link == None:
        logging.warning('Could not parse PDF or Action details for ' + file_number)

    return LegislationDetails(file_number, status, name, title, agenda_date, action_date, pdf_link, action_details_link)

def fetchHTML(url):
    logging.info('Requesting page source from ' + url)
    request = requests.get(url)
    logging.info("Success!")
    return request.text

def loadHTML(file_number, url, store_locally=False):
    filename = file_number + ".html"
    logging.debug('Loading HTML with local storage file ' + filename)
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

def loadHTMLDetails(html_content):
    parser = HTMLTreeParser()
    parser.feed(html_content)
    html_tree = parser.get_parsed_trees()[0]
    parser.close()
    return parseDetails(html_tree)

def exportItems(detail_items):
    database = DetailsDatabase()
    database.remove_table()
    database.create_table()
    database.add_items(detail_items)
    database.close()

def main(): 
    legislation_db = LegislationDatabase()
    legislation_items = legislation_db.get_items()
    html_contents = [loadHTML(item.file_number.decode('utf8'), item.link.decode('utf8'), True) for item in legislation_items]
    detail_items = [loadHTMLDetails(html) for html in html_contents]
    exportItems(detail_items)

if __name__ == "__main__": 
    main() 

