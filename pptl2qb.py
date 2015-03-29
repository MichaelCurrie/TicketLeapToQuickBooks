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

import sys, os, datetime, time, string

def main(argv):
    """
    INPUT: paypal.csv
    OUTPUT: output.iif and unprocessed.csv
    
    """
    etl.config.look_style = 'minimal'
    #input_folder = 'C:\\Users\\mcurrie\\Desktop\\GitHub\\TicketLeapToQuickBooks'
    input_folder = 'C:\\Users\\Michael\\Desktop\\TicketLeapToQuickBooks'
    paypal_path = os.path.join(input_folder, 'paypal.csv')

    paypal_to_quickbooks(paypal_path, 
                         start_date=datetime.date(2015, 1, 1))
    
    
def paypal_to_quickbooks(paypal_path, 
                         iif_path=None, unprocessed_path=None, 
                         start_date=None, end_date=None):
    """
    Process the paypal CSV into a QuickBooks 
    
    """
    if iif_path is None:
        # If no iif path was specified, default to the same folder
        # as the input, and filename = 'output.iif'
        iif_path = os.path.join(os.path.dirname(paypal_path), 'output.iif')
    
    if unprocessed_path is None:
        # If no path for unprocessed trades was specified, default to 
        # the same folder as the input, and filename = 'unprocessed.csv'
        unprocessed_path = os.path.join(os.path.dirname(paypal_path), 
                                        'unprocessed.csv')
        
    # TODO: Validate that the cart_payment is associated with exactly 
    #       cart_payment.Quantity cart_items.
    
    # --------------------
    # 1. LOAD PAYPAL CSV FILE
    print("Loading PayPal input file")
    paypal = etl.fromcsv(paypal_path)
    paypal = cleanup_paypal(paypal)

    # Any cancelled trades basically cancel, so we can eliminate most of them
    # right off the bat.
    paypal = eliminate_cancellations(paypal)

    if start_date is not None:
        # TODO: Elminiate dates prior to start_date
        pass

    if end_date is not None:
        # TODO: Eliminiate dates after end_date
        pass

    
    # DEBUG: TO NARROW THINGS FOR NOW
    #paypal = paypal.selecteq('Name', 'Alex Rossol')  

    # --------------------
    # 2. CREATE QUICKBOOKS IIF FILE
    print("Creating output IIF file")
    try:
        os.remove(iif_path)
    except FileNotFoundError:
        # If the file wasn't there in the first place, no problem.
        pass

    
    #output_iif_file.write(handle_sales_receipts(paypal))
    #output_iif_file.write(handle_invoices(paypal))
    #output_iif_file.write(handle_ticketleap_fees(paypal))
    handle_customer_names(paypal).appendtsv(iif_path, write_header=True)

#    output_iif_file.close()

    # --------------------
    # 3. CREATE UNPROCESSED ROWS FILE
    print("Creating output unprocessed rows CSV file")

    unprocessed_file = open(unprocessed_path, 'w')
    writer = csv.writer(unprocessed_file, lineterminator='\n')

    # TODO: add ONLY the unprocessed rows to output_unprocessed_file    
    writer.writerows(paypal)
    unprocessed_file.close()


def eliminate_cancellations(paypal_given):
    """
    Eliminate the cancellations, except for the Cancelled Fee amounts 
    associated with refunded Shopping Cart Payments Received.
    Those remain, in the amount of $0.30.
    
    """

    # Ignore cancelled invoices
    paypal = paypal_given.select(lambda r: r['Status'] == 'Canceled' and 
                              r['Type'] in ['Invoice Sent', 'Invoice item'],
                           complement=True)

    # Ignore refunded shopping cart items
    paypal = paypal.select(lambda r: r['Type'] in ['Shopping Cart Item'] and
                                     r['Status'] in ['Canceled', 'Refunded'],
                           complement=True)

    # Type = 'Payment Sent', Status = 'Canceled'
    # cancels with
    # Type = 'Cancelled Payment', Status = 'Complete'
    paypal = paypal.select(lambda r: r['Status'] in ['Canceled'] and 
                                     r['Type'] in ['Payment Sent'],
                           complement=True)

    paypal = paypal.select(lambda r: r['Status'] in ['Completed'] and 
                                     r['Type'] in ['Cancelled Payment'],
                           complement=True)

    # Type = 'Shopping Cart Payment Received', Status = 'Refunded'
    # PLUS
    # Type = 'Payment Sent', Status = 'Refunded'
    # cancels with
    # Type = 'Refund', Status = 'Complete'
    # + $0.30 * count(Type = 'Shopping Cart Payment Received', 
    #                 Status = 'Refunded')
    # but that little difference is handled by revising the amount of 
    # the PayPal Cancelled Fee
    paypal = paypal.select(lambda r: r['Status'] in ['Refunded'] and 
                r['Type'] in ['Shopping Cart Payment Received', 
                              'Payment Sent'],
                           complement=True)

    paypal = paypal.select(lambda r: r['Status'] in ['Completed'] and 
                                     r['Type'] in ['Refund'],
                           complement=True)

    # we have to obtain the cancelled transactions before changing the fee
    # so the complement operation will work correctly
    cancelled_transactions = etl.complement(paypal_given, paypal)
    #TODO Validate that sum(Gross) = 0

    paypal = paypal.convert('Gross', lambda v: 0.3, 
                            where=lambda r: r['Type'] == 'Cancelled Fee' and 
                                            r['Name'] == 'PayPal' and
                                            r['Status'] == 'Completed')

    # we have to perform this also to our view showing just the cancelled
    # transactions, so we can run the validation step.
    cancelled_transactions = cancelled_transactions.convert(
                            'Gross', lambda v: 0.3, 
                            where=lambda r: r['Type'] == 'Cancelled Fee' and 
                                            r['Name'] == 'PayPal' and
                                            r['Status'] == 'Completed')

    
    #assert(sum(cancelled_transactions.cols['Gross'])==0)

    return paypal


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
    names_source_fields = ['Name', 'Email', 'To Email', 'Address Line 1', 
                           'Address Line 2', 'Town/City', 'Province', 
                           'Postal Code', 'Country', 'Phone']

    names_dest_fields = ['!CUST', 'NAME', 'BADDR1', 'BADDR2', 'BADDR3', 
                         'BADDR4', 'BADDR5', 'SADDR1', 'SADDR2', 'SADDR3', 
                         'SADDR4', 'SADDR5', 'PHONE1', 'PHONE2', 'FAXNUM', 
                         'EMAIL', 'NOTE', 'CONT1', 'CONT2', 'CTYPE', 'TERMS', 
                         'TAXABLE', 'LIMIT', 'RESALENUM', 'REP', 'TAXITEM', 
                         'NOTEPAD', 'SALUTATION', 'COMPANYNAME', 'FIRSTNAME', 
                         'MIDINIT', 'LASTNAME']    

    fees = paypal.selecteq('Type', 'Preapproved Payment Sent')
    
    #fees = fees.cut(')
    out_string = ""
    # TODO
    pass
    return out_string


def handle_customer_names(paypal):
    """
    Take a paypal csv file (already sucked into PETL) and spit out
    a petl table of the unique customer names
    
    """    
    names_source_fields = ['Name', 'Email', 'To Email', 'Address Line 1', 
                           'Address Line 2', 'Town/City', 'Province', 
                           'Postal Code', 'Country', 'Phone']

    names_dest_fields = ['!CUST', 'NAME', 'BADDR1', 'BADDR2', 'BADDR3', 
                         'BADDR4', 'BADDR5', 'SADDR1', 'SADDR2', 'SADDR3', 
                         'SADDR4', 'SADDR5', 'PHONE1', 'PHONE2', 'FAXNUM', 
                         'EMAIL', 'NOTE', 'CONT1', 'CONT2', 'CTYPE', 'TERMS', 
                         'TAXABLE', 'LIMIT', 'RESALENUM', 'REP', 'TAXITEM', 
                         'NOTEPAD', 'SALUTATION', 'COMPANYNAME', 'FIRSTNAME', 
                         'MIDINIT', 'LASTNAME']

    # The names associated with these are already in the payment
    names = paypal.selectne('Type', 'Invoice item')
    names =  names.selectne('Type', 'Shopping Cart Item')
         
    # We need the direction of the transaction to know what email to take
    names = names.addfield('Is From Customer', lambda rec: 1 if rec['Type'] == 'Shopping Cart Payment Received' else 0)
    names_source_fields.append('Is From Customer')

    names = names.cut(*names_source_fields)

    # Remove duplicates    
    names = names.distinct()

    # TODO: ensure that 'NAME' doesn't already exist in QuickBooks? How does
    # or maybe just prevent that vendor/customer error by appending '(c)' 
    # after every name
    # Returns rows with same Name but differing in some other field
    #name_conflicts = names.conflicts('Name')
    # TODO: do something with these conflicts...    


    # Construct the destination fields, one by one
    names = names.addfield('!CUST', 'CUST')
    names = names.addfield('NAME', lambda rec:   rec['Name'].title() + ' (c)')
    names = names.addfield('BADDR1', lambda rec: rec['Name'].title())
    names = names.addfield('BADDR2', lambda rec: rec['Address Line 1'] +
                                           ' ' + rec['Address Line 2'])
    names = names.addfield('BADDR3', lambda rec: rec['Town/City'].title() + ', ' +
                                                 rec['Province'].title() + ' ' + 
                                                 rec['Postal Code'].upper())
    names = names.convert('BADDR3', lambda v: '' if v == ',  ' else v)
    names = names.addfield('BADDR4', 'Country')
    names = names.addfield('BADDR5', '')
    names = names.addfield('SADDR1', '')
    names = names.addfield('SADDR2', '')
    names = names.addfield('SADDR3', '')
    names = names.addfield('SADDR4', '')
    names = names.addfield('SADDR5', '')
    names = names.addfield('PHONE1', lambda rec: rec['Phone'])
    names = names.addfield('PHONE2', '')
    names = names.addfield('FAXNUM', '')
    names = names.addfield('EMAIL', lambda rec: rec['Email'] if rec['Is From Customer'] else rec['To Email'])
    names = names.addfield('NOTE', '')
    names = names.addfield('CONT1', '')
    names = names.addfield('CONT2', '')
    names = names.addfield('CTYPE', '')
    names = names.addfield('TERMS', '')
    names = names.addfield('TAXABLE', 'N')
    names = names.addfield('LIMIT', '')
    names = names.addfield('RESALENUM', '')
    names = names.addfield('REP', '')
    names = names.addfield('TAXITEM', '')
    names = names.addfield('NOTEPAD', '')
    names = names.addfield('SALUTATION', '')
    names = names.addfield('COMPANYNAME', '')
    names = names.addfield('FIRSTNAME', lambda rec: rec['Name'].split()[0])
    names = names.addfield('MIDINIT', '')
    names = names.addfield('LASTNAME', lambda rec: rec['Name'].split()[-1])

    # We don't need the source fields anymore, so cut them out
    # so names is left as just having the dest fields
    names = names.cutout(*names_source_fields)

    return names


def cleanup_paypal(paypal):
    """
    Take a paypal csv file (already sucked into PETL) and clean it up
    
    """
    # Remove leading and trailing whitespace in the header row
    paypal_clean = paypal.setheader(list((x.strip() for x in paypal.header())))

    # Rename some header names to more convenient names
    paypal_clean = paypal_clean.rename('From Email Address', 'Email') # sales receipts
    paypal_clean = paypal_clean.rename('To Email Address', 'To Email') # invoices, payments
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
                       lambda v: ''.join(c for c in v if c in string.digits))

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


if __name__ == "__main__":
    main(sys.argv[1:])