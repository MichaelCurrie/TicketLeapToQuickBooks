# -*- coding: utf-8 -*-
"""
Created on Wed May  6 12:09:46 2015

@author: mcurrie
"""

import sys, os, datetime

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
    paypal_path = os.path.join(os.path.normpath(os.path.dirname(__file__)),
                               'paypal_example.csv')

    pp2qb.paypal_to_quickbooks(paypal_path, 
                               start_date=datetime.date(2015, 1, 1))



if __name__ == "__main__":
    test_conversion()