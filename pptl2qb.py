# -*- coding: utf-8 -*-
"""
Created on Sun Feb 22 22:09:50 2015

@author: mcurrie

PayPal API reference:
https://developer.paypal.com/docs/api/

TicketLeap API reference:
http://dev.ticketleap.com/
(for now the information is not detailed enough for use for transactions)

"""

import petl as etl

import sys
import datetime

def usage():
    print("pptl2qb.py --start=20150101 --end=20150228.  Both --start and --end are optional")

def main(argv):
    #for arg in argv:
    #    print(arg)
    input_pp = 'paypal.csv'
    input_tl = 'ticketleap.csv'
    start_date = datetime.date(2015, 1, 1)
    end_date = None
    output_iif = 'output.iif'
    output_unprocessed = 'unprocessed.csv'
    
    # TODO: command-line arguments    
    # http://www.diveintopython.net/scripts_and_streams/command_line_arguments.html

    # TODO: open input_pp, input_tl
    #tl = etl.fromtsv('ticketleap.csv')
    pp = etl.fromcsv('paypal.csv')

    # TODO: transform those rows as necessary
    # follow this use case:
    # http://nbviewer.ipython.org/github/alimanfoo/petl/blob/master/notes/case_study_1.ipynb
    
    generate_output(output_iif)

    output_unprocessed_file = get_output_file(output_unprocessed)
    # TODO: add all the unprocessed rows to output_unprocessed_file
    output_unprocessed_file.close()


def generate_output(output_iif):
    
    output_iif_file = get_output_file(output_iif)
    
    output_iif_file.write('!TRNS	DATE	ACCNT	NAME	CLASS	AMOUNT	MEMO\n')
    output_iif_file.write('!SPL	DATE	ACCNT	NAME	AMOUNT	MEMO\n')
    output_iif_file.write('!ENDTRNS\n')
    
    # TODO:
    # add all of the transactions    
    # maybe use a dict for what's in the transaction?
    
    output_iif_file.close()
    

def get_output_file(file_name):
    try:
        file = open(file_name, 'w')
    except:
        print("Could not open " + file_name + " for writing")
        sys.exit(0)

    return file


if __name__ == "__main__":
    main(sys.argv[1:])