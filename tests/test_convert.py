# -*- coding: utf-8 -*-
"""
Created on Wed May  6 12:09:46 2015

@author: mcurrie
"""

import sys, os, datetime

# We must add .. to the path so that we can perform the 
# import of movement_validation while running this as 
# a top-level script (i.e. with __name__ = '__main__')
sys.path.append('..') 
import pp2qb


def main(argv):
    """
    INPUT: paypal.csv
    OUTPUT: output.iif and unprocessed.csv
    
    """
    #input_folder = 'C:\\Users\\mcurrie\\Desktop\\GitHub\\TicketLeapToQuickBooks'
    #input_folder = 'C:\\Users\\Michael\\Desktop\\TicketLeapToQuickBooks'
    paypal_path = os.path.join(os.path.normpath(os.path.dirname(argv[0])),
                               'paypal_example.csv')

    pp2qb.paypal_to_quickbooks(paypal_path, 
                               start_date=datetime.date(2015, 1, 1))



if __name__ == "__main__":
    main(sys.argv)