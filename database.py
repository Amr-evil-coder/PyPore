#!/usr/bin/env python
# Contact: Jacob Schreiber
#          jacobtribe@soe.ucsc.com
# database.py

'''
This module focuses on the various ways to read and write to databases used to store information. It is designed to be able
to connect to either a SQL database, a google docs spreadsheet, or an excel spreadsheet, to treat like a database. It can
either read from or write to these databases, from shared read or write methods. A Factory class will handle the production
of the appropriate interface. This module uses a pandas dataframe as an intermediary for all data storage efforts. 
'''
import numpy as np
import collections

SQL_TYPES = [ 'mysql', 'postgresql', 'sqlite' ]
TEXT_TABLE_TYPES = [ 'excel', 'text', 'csv' ]
GOOGLE_SPREADSHEET_TYPES = [ 'google' ]

class GoogleSpreadsheetInterface( object ):
    '''
    This is a wrapper for the gdata module, while allows for connections to google spreadsheets. The read
    method will read all of the data from a given sheet in a given spreadsheet, and the write method will
    write a pandas dataframe to the google spreadsheet, if it exists. It has to be premade.

    Requires: gdata, pandas
    '''
    def __init__( self, email = None, password = None, source = None, title = None, key = None, sheet = 1 ):
        import gdata.spreadsheet.service as gdata
        self.client    =  gdata.SpreadsheetsService()
        self.client.email     =  email
        self.client.password  =  password
        self.client.source    =  source
        self.client.ProgrammaticLogin()
        self.key   = key
        self.title = title
        self.sheet = sheet
        q = gdata.DocumentQuery()
        q['title'] = self.title
        q['title-exact'] = 'true'
        feed = self.client.GetSpreadsheetsFeed( query = q )
        spreadsheet_id = feed.entry[0].id.text.rsplit("/", 1)[1]
        feed = self.client.GetWorksheetsFeed( spreadsheet_id )
        worksheet_id = feed.entry[ self.sheet ].id.text.rsplit("/", 1)[1]
        self.data = self.client.GetListFeed( spreadsheet_id, worksheet_id ).entry

    def read( self ):
        '''
        Read all of the information from a given sheet on a given spreadsheet. It will return this as a
        list of tuples, ordered according to the keys in the gspreadsheet. 
        '''
        return [ tuple([ row.custom[key].text for key in row.custom ]) for row in self.data ]

    def write( self, dataframe ):
        '''
        Takes in a pandas dataframe, and writes it to the google spreadsheet. This spreadsheet must already
        exist. Currently not supported.
        '''
        pass

class TextInterface( object ):
    '''
    This allows connection to a text document, allowing any deliniation. 
    '''
    def __init__( self, file ):
        self.file = file
    def read( self, seperator=" " ):
        '''
        Read in a text document to a list of tuples. Seperator assumed if csv or tsv, but otherwise
        needs to be provided if not space-seperated. 
        '''
        with open( self.file, 'r' ) as infile:
            if self.file.endswith( ".csv" ):
                seperator = ","
            elif self.file.endswith( ".tsv" ):
                seperator = "\t"
            return [ tuple( line.strip("\r\n\t").split(seperator)) for line in infile ] 

    def write( self, data, seperator=" " ):
        '''
        Writes a series of data, in order, to the document. This will override any data in the
        document.
        '''
        assert hasattr( data, "__iter__" )
        with open( self.file, 'w' ) as outfile:
            if self.file.endswith( ".csv" ):
                seperator = ","
            elif self.file.endswith( ".tsv" ):
                seperator = "\t"
            if type(data[0] == str):
                outfile.write( data )
            else:
                outfile.write( "\n".join( seperator.join( str(i) for i in entry ) for entry in data ) )

class MySQLDatabaseInterface( object ):
    '''
    To use mySQL servers, must download the apporpriate servers. 
    '''
    def __init__( self, db, user = None, password = None, host = None ):
        import MySQLdb
        self.db = MySQLdb.connect( host, user, password, db )
        self.cursor = self.db.cursor()

    def execute( self, statement ):
        '''
        Execute an arbitrary SQL statement. No restriction on the type of statements which
        can be executed, except those imposed by the SQL user. 
        '''
        try:
            self.cursor.execute( statement )
        except:
            raise DatabaseError( "MySQL Error: Unable to execute statement '{}'".format(statement) )
        self.db.commit()

    def read( self, statement ):
        try:
            self.cursor.execute( statement )
            return self.cursor.fetchall()
        except:
            raise DatabaseError( "MySQL Error: Unable to execute statement '{}'".format(statement) )

    def insert( self, table, data ):
        try:
            for row in data:
                self.cursor.execute( 'INSERT INTO {table} VALUES ( {vals} )'.format( table = table, vals = self._build_insert( row ) ) )
            self.db.commit()
        except:
            raise DatabaseError( "MySQL Error: Unable to add row ({row}) to table ({table})".format( row=row, table=table ) )

    def _build_insert( self, tuple ):
        return ','.join( [ '"{}"'.format( str(item).replace('"', '""').replace( "\\", "\\\\") ) 
                            if isinstance( item, str ) or not item 
                            else '{}'.format( item ) 
                            for item in tuple ] )

    def _datify( self, date ):
        if not isinstance( date, Qc.QString ) and not isinstance( date, str ):
            return None
        if isinstance( date, datetime.date ):
            return date
        for seg in '/-':
            if date.count( seg ) == 2:
                date = date.split( seg )
        return datetime.date( int(date[0]), int(date[1]), int(date[2]) )

class DatabaseError( Exception ):
    def __init__( self, error ):
        self.error = error
    def __str__( self ):
        return repr( self.error ) 

def DatabaseFactory( db_type, **kwargs ):
    '''
    Returns a database connection to the appropriate type of database, all of which have at least a read() and write() method.
    Arguments for the various types are:

    Google Doc
        title: Name of the spreadsheet to open your google drive
        email: Account to use to log in
        password: Password for that account 
        source: String describing where the query is coming from
        key: String present in the url of the spreadsheet of interest, after "/ccc?key=" until "#gid" in the url
    Text
        file: Name of the text document to use
    mysql
        db: Name of the database to use
        user: User name to connect with
        password: Password for this user
        host: Where the database is located 
    '''
    if db_type.lower() in GOOGLE_SPREADSHEET_TYPES:
        return GoogleSpreadsheetInterface( title = title, email = email, password = password, source = source, key = key, sheet = sheet )
    if db_type.lower() in TEXT_TABLE_TYPES:
        return TextInterface( file = file )
    if db_type.lower() == 'mysql':
        return MySQLDatabaseInterface( db = db, user = user, password = password, host = host )