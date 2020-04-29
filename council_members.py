from logging_setup import logging
import sqlite3

class Legislator:
    def __init__(self, member_id, first_name, last_name, start_year, end_year):
        self.member_id = member_id
        self.first_name = first_name
        self.last_name = last_name
        self.start_year = start_year
        self.end_year = end_year

    def full_name(self):
        return "{0.first_name} {0.last_name}".format(self)

    def was_active_on(self, date):
        # TODO: use exact start/end dates to avoid false positives
        year = int(date.split('/')[-1])
        return self.start_year <= year and year <= self.end_year

class LegislatorDatabase:
    TABLE_NAME = 'council_members'

    def __init__(self):
        self.connection = sqlite3.connect('legislation.db')
        self.cursor = self.connection.cursor()

    def remove_table(self):
        logging.debug('Dropping ' + LegislatorDatabase.TABLE_NAME + ' table')
        command = "DROP TABLE IF EXISTS " + LegislatorDatabase.TABLE_NAME + ";"
        self.cursor.execute(command)

    def create_table(self):
        logging.debug('Creating ' + LegislatorDatabase.TABLE_NAME + ' table')
        # sqlite3 auto increments INTEGER PRIMARY KEY
        command = "CREATE TABLE IF NOT EXISTS " + LegislatorDatabase.TABLE_NAME + """ (
member_id INTEGER PRIMARY KEY,
name_first TEXT,
name_last TEXT,
year_start INTEGER,
year_end INTEGER
);""";
        self.cursor.execute(command)

    def add_members(self, member_infos):
        logging.debug('Adding ' + str(len(member_infos)) + ' members to ' + LegislatorDatabase.TABLE_NAME + ' table')
        keys = ['name_first', 'name_last', 'year_start', 'year_end']
        all_values = [(m[0].upper(), m[1].upper(), m[2], m[3]) for m in member_infos]
        command = "INSERT OR REPLACE INTO " + LegislatorDatabase.TABLE_NAME + " (" + ', '.join(keys) + ") VALUES (" + ','.join(['?' for k in keys]) + ");"
        self.cursor.executemany(command, all_values)

    def get_members(self):
        command = "SELECT member_id, name_first, name_last, year_start, year_end FROM " + LegislatorDatabase.TABLE_NAME + ";"
        all_results = self.cursor.execute(command).fetchall()
        return [Legislator(r[0], r[1], r[2], r[3], r[4]) for r in all_results]

    def close(self):
        logging.debug('Closed connection to ' + LegislatorDatabase.TABLE_NAME + ' table')
        self.connection.commit()
        self.connection.close()

def main():
    # From Wikipedia, some dates might be a little off.
    # TODO: use exact days so we can know who was expected to vote on any given item.
    members = [
    ("Nikki", "Fortunato Bas", 2018, 9999),
    ("Sheng", "Thao", 2018, 9999),
    ("Loren", "Taylor", 2018, 9999),
    ("Rebecca", "Kaplan", 2008, 9999),
    ("Larry", "Reid", 1997, 9999),
    ("Lynette", "McElhaney", 2012, 9999),
    ("Noel", "Gallo", 2012, 9999),
    ("Dan", "Kalb", 2012, 9999),
    ("Abel", "Guillen", 2014, 2018),
    ("Annie", "Washington", 2014, 2018),
    ("Libby", "Schaaf", 2010, 2014),
    ("Patricia", "Kernighan", 2005, 2014),
    ("Jean", "Quan", 2003, 2011),
    ("David", "Stein", 2002, 2006),
    ("Desley", "Brooks", 2002, 2018),
    ("Jane", "Brunner", 1996, 2012),
    ("Nancy", "Nadel", 1996, 2012),
    ("Ignacio", "De La Fuente", 1992, 2012),
    ("Danny", "Wan", 2000, 2005),
    ("Henry", "Chang", 1994, 2009),
    ("Nate", "Miley", 1996, 2002),
    ("Dick", "Spees", 1996, 2002),
    ("John", "Russo", 1994, 2000)
    ]

    database = LegislatorDatabase()
    database.remove_table()
    database.create_table()
    database.add_members(members)
    database.close()

if __name__ == "__main__": 
    main() 
