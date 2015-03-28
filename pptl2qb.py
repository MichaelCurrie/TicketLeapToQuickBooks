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
import csv

import sys, os, datetime, time

def usage():
    print("pptl2qb.py --start=20150101 --end=20150228.  Both --start and --end are optional")

def main(argv):
    etl.config.look_style = 'minimal'
    #for arg in argv:
    #    print(arg)
    input_folder = 'C:\\Users\\mcurrie\\Desktop\\GitHub\\TicketLeapToQuickBooks'
    input_pp = os.path.join(input_folder, 'paypal.csv')
    # DEBUG: For now we're not using Ticketleap since it passed its data
    #        to PayPal anyway
    # input_tl = os.path.join(input_folder, 'ticketleap.csv') 
    start_date = datetime.date(2015, 1, 1)
    end_date = None
    output_iif = os.path.join(input_folder, 'output.iif')
    output_unprocessed = os.path.join(input_folder, 'unprocessed.csv')
    
    # TODO: Validate that the cart_payment is associated with exactly 
    #       cart_payment.Quantity cart_items.
    
    # TODO: command-line arguments    
    # http://www.diveintopython.net/scripts_and_streams/command_line_arguments.html

    paypal = etl.fromcsv(input_pp)

    paypal = cleanup_paypal(paypal)
    
    paypal = paypal.selecteq('Name', 'Alex Rossol')  # DEBUG

    # Sales receipts are organized in the CSV file as a row to summarize,
    # (cart payment), plus one or more rows for each of the items purchased.
    cart_payment = paypal.selecteq('Type', 'Shopping Cart Payment Received')
    # Ignore refunds
    cart_payment = cart_payment.selecteq('Status', 'Completed')
    cart_payment = cart_payment.cut('Date', 'Name', 'Email', 'Gross', 'Fee', 
                                    'Transaction ID')

    cart_items = paypal.selecteq('Type', 'Shopping Cart Item')
    cart_items = cart_items.cut('Item Title', 'Item ID', 'Quantity', 'Gross', 
                                'Transaction ID')

    sales_receipts = cart_payment.leftjoin(cart_items, key=['Transaction ID'])

    print("hi")
    print("hi again")
 #   names = etl.cut(pp2, 'Name', 'Date', 'Time', 'Date', 'Type')

  #  table.cut(0,8,9,12).look(style='minimal')


    # group by Name
    # iterate over all items


    names = paypal.cut('Name', 'Email', 'Address Line 1', 'Address Line 2', 
                       'Town/City', 'Province', 'Postal Code', 'Country', 
                       'Phone')
    # TODO: ensure that 'NAME' doesn't already exist in QuickBooks? How does
    # or maybe just prevent that vendor/customer error by appending '(c)' 
    # after every name
    names_dict = names.columns()
    

 
    # TODO: transform those rows as necessary
    # follow this use case:
    # http://nbviewer.ipython.org/github/alimanfoo/petl/blob/master/notes/case_study_1.ipynb
    
    generate_output(output_iif)

    output_unprocessed_file = get_output_file(output_unprocessed)
    # TODO: add all the unprocessed rows to output_unprocessed_file
    
    writer = csv.writer(output_unprocessed_file, lineterminator='\n')
    writer.writerows(paypal)
    output_unprocessed_file.close()



def cleanup_paypal(paypal):
    """
    Take a paypal csv file (already sucked into PETL) and clean it up
    
    """
    # Remove leading and trailing whitespace in the header row
    paypal_clean = paypal.setheader(list((x.strip() for x in paypal.header())))

    # Let's perform some cleanup on the headers, renaming some and 
    # removing some that we don't need
    paypal_clean = paypal_clean.rename('From Email Address', 'Email')
    paypal_clean = paypal_clean.rename('Contact Phone Number', 'Phone')
    paypal_clean = paypal_clean.rename('Zip/Postal Code', 'Postal Code')
    paypal_clean = paypal_clean.rename(
        'State/Province/Region/County/Territory/Prefecture/Republic',
        'Province')
    paypal_clean = paypal_clean.rename(
        'Address Line 2/District/Neighborhood',
        'Address Line 2')

    paypal_clean = paypal_clean.cutout('Time Zone', 'Net', 'Balance', 
                                       'Custom Number', 'Counterparty Status', 
                                       'Address Status')
    paypal_clean = paypal_clean.cutout(*list(range(18,33)))

    # Let's convert the Date column to proper Python datetime-type dates
    def convert_ppdate(paypal_date):
        ex_struct_time = time.strptime(paypal_date, '%m/%d/%Y')
        ex_date = datetime.date(ex_struct_time.tm_year, 
                                ex_struct_time.tm_mon, 
                                ex_struct_time.tm_mday)
        return ex_date

    paypal_clean = etl.transform.conversions.convert(paypal_clean,
                                                     'Date', 
                                                     convert_ppdate)

    # Let's convert the dollar columns from string to float
    paypal_clean = etl.transform.conversions.convert(paypal_clean, 
                                                     ('Gross', 'Fee'),
                                                     float)
    return paypal_clean



def generate_output(output_iif):
    
    output_iif_file = get_output_file(output_iif)
    
    output_iif_file.write('!TRNS	DATE	ACCNT	NAME	CLASS	AMOUNT	MEMO\n')
    output_iif_file.write('!SPL	DATE	ACCNT	NAME	AMOUNT	MEMO\n')
    output_iif_file.write('!ENDTRNS\n')
    
    # TODO:
    # add all of the transactions    
    # maybe use a dict for what's in the transaction?

    
    #TRNS    "1/3/2015"  "Paypal Account"    "Stephen Spielberg" "Shopping Cart Payment Received"    225.46  "Memo for whole deposit"
    #SPL "1/3/2015"  "Other Income"  "Stephen Spielberg" -232.50
    #SPL "1/3/2015"  "Other Expenses"    Fee 7.04
    #ENDTRNS    
    
    
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