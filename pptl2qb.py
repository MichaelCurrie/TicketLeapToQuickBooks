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

#import petl as etl

#tl = etl.fromtsv('ticketleap.csv')
#pp = etl.fromtsv('paypal.csv')

import sys

def usage():
    print("pptl2qb.py --start=20150101 --end=20150228.  Both --start and --end are optional")

def main(argv):
    for arg in argv:
        print(arg)
    
    # TODO: command-line arguments    
    # http://www.diveintopython.net/scripts_and_streams/command_line_arguments.html
    generate_output()


def generate_output():
    output_iif = 'output.iif'
    output_unprocessed = 'unprocessed.csv'
    
    output_iif_file = get_output_file(output_iif)
    output_unprocessed_file = get_output_file(output_unprocessed)
    
    output_iif_file.write('test succeeded')
    
    output_iif_file.close()
    output_unprocessed_file.close()
    

def get_output_file(file_name):
    try:
        file = open(file_name, 'w')
    except:
        print("Could not open " + file_name + " for writing")
        sys.exit(0)

    return file


if __name__ == "__main__":
    main(sys.argv[1:])