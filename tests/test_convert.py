# -*- coding: utf-8 -*-
"""
Created on Wed May  6 12:09:46 2015

@author: mcurrie
"""

import sys, os, datetime
import codecs

# We must add .. to the path so that we can perform the 
# import of the package while running this as 
# a top-level script (i.e. with __name__ = '__main__')
sys.path.append('..') 
import pp2qb


def test_conversion():
    """
    INPUT: paypal.csv
    OUTPUT: output.iif and unprocessed.csv
    
    """
    #paypal_path = "C:\\Users\\mcurrie\\Desktop\\GitHub\\TicketLeapToQuickBooks\\tests\\paypal_example.csv"
    paypal_path = os.path.join(os.path.normpath(os.path.dirname(__file__)),
                               'paypal_example.csv')

    try:
        f = codecs.open(paypal_path, encoding='utf-8', errors='strict')
        for line in f:
            pass
        print("Valid utf-8")
        pp2qb.paypal_to_quickbooks(paypal_path, 
                                   start_date=datetime.date(2015, 1, 1))
    except UnicodeDecodeError:
        print("invalid utf-8")

        # TODO: Convert the csv file in-place to utf-8.
        # http://stackoverflow.com/questions/6539881/python-converting-from-iso-8859-1-latin1-to-utf-8


if __name__ == "__main__":
    test_conversion()