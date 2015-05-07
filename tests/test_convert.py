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
    paypal_path = os.path.join(os.path.normpath(os.path.dirname(__file__)),
                               'paypal_example.csv')

    ensure_utf8(paypal_path)

    pp2qb.paypal_to_quickbooks(paypal_path, 
                               start_date=datetime.date(2015, 1, 1))


def ensure_utf8(file_path):
    """
    Convert a file in-place to utf-8, if it isn't already in utf-8.

    Credit:
    http://stackoverflow.com/questions/6539881/
    
    """
    BLOCKSIZE = 1048576 # Arbitary file size limit

    # Find out if the file at file_path is encoded with utf-8:
    try:
        with codecs.open(file_path, 
                         encoding='utf-8', 
                         errors='strict') as source_file:
            for line in source_file:
                pass
            is_utf8 = True
    except UnicodeDecodeError:
        is_utf8 = False

    if not is_utf8:
        # Perform a conversion
        with codecs.open(file_path, 'r', 
                         encoding='iso-8859-1', 
                         errors='strict') as source_file:
            with codecs.open(file_path+'2', 'w', 
                             encoding='utf-8') as target_file:
                while True:
                    contents = source_file.read(BLOCKSIZE)
                    if not contents:
                        break
                    target_file.write(contents)
        
        # Delete the original file        
        os.remove(file_path)
        # Replace the original file with our newly encoded version
        os.rename(file_path+'2', file_path)


if __name__ == "__main__":
    test_conversion()