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

def main(argv):
    """
    INPUT: paypal.csv
    OUTPUT: output.iif and unprocessed.csv
    
    """
    # --------------------
    # 1. HARDCODED SETUP INFO
    etl.config.look_style = 'minimal'
    input_folder = 'C:\\Users\\mcurrie\\Desktop\\GitHub\\TicketLeapToQuickBooks'
    input_pp = os.path.join(input_folder, 'paypal.csv')
    start_date = datetime.date(2015, 1, 1)
    end_date = None
    output_iif = os.path.join(input_folder, 'output.iif')
    output_unprocessed = os.path.join(input_folder, 'unprocessed.csv')
    
    # TODO: Validate that the cart_payment is associated with exactly 
    #       cart_payment.Quantity cart_items.
    
    # --------------------
    # 2. LOAD PAYPAL CSV FILE
    print("Loading PayPal input file")
    paypal = etl.fromcsv(input_pp)
    paypal = cleanup_paypal(paypal)
    
    # DEBUG: TO NARROW THINGS FOR NOW
    paypal = paypal.selecteq('Name', 'Alex Rossol')  

    # --------------------
    # 3. CREATE QUICKBOOKS IIF FILE
    print("Creating output IIF file")
    output_iif_file = get_output_file(output_iif)

    output_iif_file.write(handle_sales_receipts(paypal))
    output_iif_file.write(handle_invoices(paypal))
    output_iif_file.write(handle_ticketleap_fees(paypal))
    output_iif_file.write(handle_customer_names(paypal))

    output_iif_file.close()

    # --------------------
    # 4. CREATE UNPROCESSED ROWS FILE
    print("Creating output unprocessed rows CSV file")

    output_unprocessed_file = get_output_file(output_unprocessed)
    writer = csv.writer(output_unprocessed_file, lineterminator='\n')

    # TODO: add ONLY the unprocessed rows to output_unprocessed_file    
    writer.writerows(paypal)
    output_unprocessed_file.close()


def handle_sales_receipts(paypal):
    """
    Take a paypal csv file (already sucked into PETL) and spit out
    the sales receipts (in a string)
    
    """
    out_string = ""
    
    out_string += '!TRNS	DATE	ACCNT	NAME	CLASS	AMOUNT	MEMO\n'
    out_string += '!SPL	DATE	ACCNT	NAME	AMOUNT	MEMO\n'
    out_string += '!ENDTRNS\n'

    # Sales receipts are organized in the CSV file as a row to summarize,
    # (cart payment), plus one or more rows for each of the items purchased.
    cart_payments = paypal.selecteq('Type', 'Shopping Cart Payment Received')
    # Ignore refunds
    cart_payments = cart_payments.selecteq('Status', 'Completed')
    cart_payments = cart_payments.cut('Date', 'Name', 'Email', 'Gross', 'Fee', 
                                      'Transaction ID')

    cart_items = paypal.selecteq('Type', 'Shopping Cart Item')
    cart_items = cart_items.cut('Item Title', 'Item ID', 'Quantity', 'Gross', 
                                'Transaction ID')

    # TODO ABORT IF EMPTY

    for tranID in cart_payments.columns()['Transaction ID']:
        cur_cart_payment = cart_payments.selecteq('Transaction ID', tranID)
        cur_cart_items = cart_items.selecteq('Transaction ID', tranID).columns()

        # TODO ABORT IF EMPTY

        # TODO WRITE TO IIF
        pass
    
        for item_number in range(len(cur_cart_items)):
            # TODO WRITE TO IIF
            pass

    # TODO WRITE CLOSING STATEMENT TO IIF

    return out_string


def handle_invoices(paypal):
    """
    Take a paypal csv file (already sucked into PETL) and spit out
    the invoices and payments received for them
    
    """
    out_string = ""
    # TODO
    pass
    return out_string


def handle_ticketleap_fees(paypal):
    """
    Take a paypal csv file (already sucked into PETL) and spit out
    the ticketleap payments (the fees they charge us for using TicketLeap)
    
    """
    out_string = ""
    # TODO
    pass
    return out_string


def handle_customer_names(paypal):
    """
    Take a paypal csv file (already sucked into PETL) and spit out
    the unique customer names
    
    """    
    out_string = ""

    names = paypal.cut('Name', 'Email', 'Address Line 1', 'Address Line 2', 
                       'Town/City', 'Province', 'Postal Code', 'Country', 
                       'Phone')
    # TODO: ensure that 'NAME' doesn't already exist in QuickBooks? How does
    # or maybe just prevent that vendor/customer error by appending '(c)' 
    # after every name
    names_dict = names.columns()
    # Returns rows with same Name but differing in some other field
    name_conflicts = names.conflicts('Name')
    
    names = names.addfield('First Name', lambda rec: rec['Name'].split()[0])
    names = names.addfield('Last Name',  lambda rec: rec['Name'].split()[1])
    names = names.addfield('Taxable', 'N')
    names = names.addfield('Address1', lambda rec: rec['Address Line 1'] +
                                           ' ' + rec['Address Line 2'])
    names = names.addfield('Address2', lambda rec: rec['Town/City'] + ', ' +
                                           rec['Province'] + ' ' + 
                                           rec['Postal Code'])

    
    names_header = ['!CUST', 'NAME', 'BADDR1', 'BADDR2', 'BADDR3', 
                    'BADDR4', 'BADDR5', 'SADDR1', 'SADDR2', 'SADDR3', 
                    'SADDR4', 'SADDR5', 'PHONE1', 'PHONE2', 'FAXNUM', 
                    'EMAIL', 'NOTE', 'CONT1', 'CONT2', 'CTYPE', 'TERMS', 
                    'TAXABLE', 'LIMIT', 'RESALENUM', 'REP', 'TAXITEM', 
                    'NOTEPAD', 'SALUTATION', 'COMPANYNAME', 'FIRSTNAME', 
                    'MIDINIT', 'LASTNAME']
    
        
    
    """ 
    {'NAME': 'Name', 
     'BADDR1': 'Name', 
     'BADDR2': 'Address1',
     'BADDR3': 'Address2',
     'BADDR4': 'Country',
     'TAXABLE': 'Taxable',
     'EMAIL': 'Email',
     'PHONE1': 'Phone Number',
     'FIRSTNAME': 'First Name',
     'LASTNAME': 'Last Name'}
    """  

    
    return out_string


def cleanup_paypal(paypal):
    """
    Take a paypal csv file (already sucked into PETL) and clean it up
    
    """
    # Remove leading and trailing whitespace in the header row
    paypal_clean = paypal.setheader(list((x.strip() for x in paypal.header())))

    # Rename some header names to more convenient names
    paypal_clean = paypal_clean.rename('From Email Address', 'Email')
    paypal_clean = paypal_clean.rename('Contact Phone Number', 'Phone')
    paypal_clean = paypal_clean.rename('Zip/Postal Code', 'Postal Code')
    paypal_clean = paypal_clean.rename(
        'State/Province/Region/County/Territory/Prefecture/Republic',
        'Province')
    paypal_clean = paypal_clean.rename(
        'Address Line 2/District/Neighborhood',
        'Address Line 2')

    # It seems that Quickbooks requires that phone numbers be entirely 
    # composed of digits, e.g. 4035559195 instead of 403-555-9195
    paypal_clean = paypal_clean.convert('Phone', 
                       lambda v: ''.join(c for c in v if c in digits))

    # Get rid of columns that are not needed
    paypal_clean = paypal_clean.cutout(
        'Shipping and Handling Amount', 'Insurance Amount', 'Sales Tax', 
        'Option 1 Name', 'Option 1 Value', 'Option 2 Name', 'Option 2 Value', 
        'Auction Site', 'Buyer ID', 'Item URL', 'Closing Date', 'Escrow Id', 
        'Invoice Id', 'Time Zone', 'Net', 'Balance', 'Counterparty Status', 
        'Address Status')

    # Convert the 'Date' column to proper Python datetime-type dates
    def convert_ppdate(paypal_date):
        ex_struct_time = time.strptime(paypal_date, '%m/%d/%Y')
        ex_date = datetime.date(ex_struct_time.tm_year, 
                                ex_struct_time.tm_mon, 
                                ex_struct_time.tm_mday)
        return ex_date

    paypal_clean = etl.transform.conversions.convert(paypal_clean,
                                                     'Date', 
                                                     convert_ppdate)

    # Convert the money and quantity columns from string to float
    paypal_clean = etl.transform.conversions.convert(paypal_clean, 
                                                     ('Gross', 'Fee', 
                                                      'Quantity'),
                                                     float)
    return paypal_clean


    

def get_output_file(file_name):
    try:
        file = open(file_name, 'w')
    except:
        print("Could not open " + file_name + " for writing")
        sys.exit(0)

    return file


if __name__ == "__main__":
    main(sys.argv[1:])