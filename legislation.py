from logging_setup import logging
import requests
import sqlite3
import xml.etree.ElementTree as ET

class LegislationItem:
    CATEGORY_TYPES = ['City Resolution', 'Ordinance', 'Proclamation', 'JPA Resolution', 'JPFA Resolution', 'ORA Resolution', 'ORSA Resolution']

    def __init__(self, file_number, link, guid, description, category, pub_date):
        self.file_number = file_number
        self.link = link
        self.guid = guid
        self.description = description
        self.category = category
        self.publish_date = pub_date


class LegislationDatabase:
    TABLE_NAME = 'legislation'

    def __init__(self):
        self.connection = sqlite3.connect('legislation.db')
        self.connection.text_factory = str
        self.cursor = self.connection.cursor()

    def remove_table(self):
        logging.debug('Dropping legislation table')
        command = "DROP TABLE IF EXISTS " + LegislationDatabase.TABLE_NAME + ";"
        self.cursor.execute(command)

    def create_table(self):
        logging.debug('Creating legislation table')
        command = "CREATE TABLE IF NOT EXISTS " + LegislationDatabase.TABLE_NAME + """ (
file_number TEXT NOT NULL PRIMARY KEY,
link TEXT NOT NULL,
guid TEXT,
category INTEGER,
publish_date TEXT,
description TEXT
);""";
        self.cursor.execute(command)
    
    def add_items(self, legislation_items):
        logging.debug('Adding ' + str(len(legislation_items)) + ' items to ' + LegislationDatabase.TABLE_NAME + ' table')
        keys = ['file_number', 'link', 'guid', 'category', 'publish_date', 'description']
        all_values = [(item.file_number, item.link, item.guid, item.category, item.publish_date, item.description) for item in legislation_items]
        command = "INSERT OR REPLACE INTO " + LegislationDatabase.TABLE_NAME + " (" + ', '.join(keys) + ") VALUES (" + ','.join(['?' for k in keys]) + ");"
        self.cursor.executemany(command, all_values)

    def get_item(self, file_number):
        keys = ['file_number', 'link', 'guid', 'description', 'category', 'publish_date']
        command = "SELECT " + ', '.join(keys) + " FROM " + LegislationDatabase.TABLE_NAME + " WHERE file_number LIKE '" + file_number + "';"
        r = self.cursor.execute(command).fetchone()
        return LegislationItem(r[0], r[1], r[2], r[3], r[4], r[5])
    
    def get_items(self):
        keys = ['file_number', 'link', 'guid', 'description', 'category', 'publish_date']
        command = "SELECT " + ', '.join(keys) + " FROM " + LegislationDatabase.TABLE_NAME + ";"
        all_results = self.cursor.execute(command).fetchall()
        return [LegislationItem(r[0], r[1], r[2], r[3], r[4], r[5]) for r in all_results]

    def close(self):
        logging.debug('Closed connection to ' + LegislationDatabase.TABLE_NAME + ' table')
        self.connection.commit()
        self.connection.close()

def loadXML():
    filename = 'legislation.xml'
    logging.debug('Loading XML with local storage file ' + filename)
    try:
        f = open(filename, 'r')
        text = f.read()
        f.close()
        logging.debug('Loaded from local storage')
        return text
    except IOError:
        logging.error('Local storage file not found')
        return None

def loadXMLItems(xml_content):
    root = ET.fromstring(xml_content)
    return root.findall('./channel/item')

def legislationItem(xml_item):
    item_info = {child.tag: child.text.encode('utf8') if child.text else None for child in xml_item}
    file_number = item_info.get('title')
    link = item_info.get('link')
    guid = item_info.get('guid')
    description = item_info.get('description')
    publish_date = item_info.get('pubDate')
    try:
        category = LegislationItem.CATEGORY_TYPES.index(item_info.get('category').decode('utf8')) + 1
    except ValueError:
        category = None

    return LegislationItem(file_number, link, guid, description, category, publish_date)

def exportItems(legislation_items):
    database = LegislationDatabase()
    database.remove_table()
    database.create_table()
    database.add_items(legislation_items)
    database.close()

def main(): 
    xml_content = loadXML()
    if xml_content == None:
        return

    xml_items = loadXMLItems(xml_content)
    legislation_items = [legislationItem(item) for item in xml_items]
    # The following are missing file numbers:
    # https://oakland.legistar.com/Gateway.aspx?M=LD&From=RSS&ID=3998043&GUID=326003A6-5589-4E34-A53E-DD1396EEEF22
    # https://oakland.legistar.com/Gateway.aspx?M=LD&From=RSS&ID=1806565&GUID=B735914F-58C3-4EAA-A1CB-6515F7BEA1AE
    # https://oakland.legistar.com/Gateway.aspx?M=LD&From=RSS&ID=741677&GUID=0B9097EF-D3C1-41C8-B942-E2B8988AEF2B
    filtered_items = list(filter(lambda x: (x.file_number != None and x.category != None), legislation_items))
    exportItems(filtered_items)

if __name__ == "__main__": 
    main() 

