# -*- coding: utf-8 -*-
"""
Created on Sun Feb 22 22:09:50 2015

@author: mcurrie

PayPal API reference:
https://developer.paypal.com/docs/api/

TicketLeap API reference:
http://dev.TicketLeap.com/
(for now the information is not detailed enough for use for transactions)

"""

import petl as etl
import csv, sys, os, datetime, time, string

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

    if start_date is not None:
        # Eliminiate dates prior to start_date
        paypal = paypal.selectge('Date', start_date)

    if end_date is not None:
        # Eliminiate dates after end_date
        paypal = paypal.selectle('Date', end_date)

    # Any cancelled trades basically cancel, so we can eliminate most of them
    # right off the bat.
    paypal = eliminate_cancellations(paypal)
   
    # DEBUG: TO NARROW THINGS FOR NOW
    #paypal = paypal.selecteq('Name', 'Alex Rossol')  

    # --------------------
    # 2. CREATE QUICKBOOKS IIF FILE
    print("Creating output IIF file")
    # We always delete the file and start fresh
    try:
        os.remove(iif_path)
    except FileNotFoundError:
        # If the file wasn't there in the first place, no problem.
        pass

    # Start with the names data, add that to the .IIF file.
    get_customer_names(paypal).appendtsv(iif_path, write_header=True)

    # TicketLeap fees have a header for both the transaction and the split
    # so I have to write to the IIF file within the function
    paypal = append_TicketLeap_fees(paypal, iif_path)

    # TicketLeap sales receipts make up the bulk of the transactions
    #paypal = append_sales_as_deposits(paypal, iif_path)

    # Invoices are for tickets or for membership sales
    paypal = append_invoices(paypal, iif_path)


    # --------------------
    # 3. CREATE UNPROCESSED ROWS FILE
    print("Creating output unprocessed rows CSV file")

    unprocessed_file = open(unprocessed_path, 'w')
    writer = csv.writer(unprocessed_file, lineterminator='\n')
    writer.writerows(paypal)
    unprocessed_file.close()


def eliminate_cancellations(paypal_given):
    """
    Eliminate the cancellations, except for the Cancelled Fee amounts 
    associated with refunded Shopping Cart Payments Received.
    Those remain, in the amount of $0.30.
    
    """
    # Type = 'Payment Sent', Status = 'Canceled'
    # cancels with
    # Type = 'Cancelled Payment', Status = 'Complete'
    paypal = paypal_given.select(lambda r: r['Status'] in ['Canceled'] and 
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

    # Grab a copy of just the cancelled trades so we can verify they net to 0
    # We have to obtain the cancelled transactions before changing the 
    # PayPal fee so the complement operation will work correctly
    cancelled_transactions = etl.complement(paypal_given, paypal)

    paypal = paypal.convert({'Fee': lambda v: -0.3, 'Gross': lambda v: 0},
                            where=lambda r: r['Type'] == 'Cancelled Fee' and 
                                            r['Name'] == 'PayPal' and
                                            r['Status'] == 'Completed')

    num_fee_refunds = paypal.select(lambda r: r['Type'] == 'Cancelled Fee' and 
                                           r['Name'] == 'PayPal' and
                                           r['Status'] == 'Completed').nrows()

    # DEBUG: list the cancelled trades explicitly
    #input_folder = 'C:\\Users\\Michael\\Desktop\\TicketLeapToQuickBooks'
    #cancel_path = os.path.join(input_folder, 'cancelled_trades.csv')    
    #cancelled_transactions.tocsv(cancel_path, write_header=True)

    # Verify that our cancelled trades all net to 0    
    # (We simply can't assert that the sum == 0 because of machine epsilon)
    assert(abs(sum(cancelled_transactions.values('Gross').toarray())) < 0.01)

    # The fees are supposed to cancel except for -num_fee_refunds * 0.3
    assert(abs(sum(cancelled_transactions.values('Fee').toarray())-
           -num_fee_refunds * 0.3) < 0.01)

    # Finally, let's eliminate things that don't net against anything else
    # but should still not appear in the transaction list:

    # Ignore cancelled invoices (these don't net with anything but instead
    # should never appear against the balance at all)
    paypal = paypal.select(lambda r: r['Status'] == 'Canceled' and 
                              r['Type'] in ['Invoice Sent', 'Invoice item'],
                           complement=True)

    # Ignore refunded shopping cart items  (again these don't net with 
    # anything, they just serve to double-count the amount since they 
    # double with Shopping Cart Payment Received, so we must eliminate them)
    paypal = paypal.select(lambda r: r['Type'] in ['Shopping Cart Item'] and
                                     r['Status'] in ['Canceled', 'Refunded'],
                                 complement=True)

    return paypal


def append_sales_as_deposits(paypal, iif_path):
    """
    Take a paypal csv file (already sucked into PETL) and spit out
    the deposits
    
    """
    source_fields = ['Type', 'Date', 'Name', 'Gross']

    trns_fields = ['!TRNS', 'TRNSID', 'TRNSTYPE', 'DATE', 'ACCNT', 'NAME', 
                   'CLASS', 'AMOUNT', 'DOCNUM', 'MEMO', 'CLEAR']

    spl_fields  = ['!TRNS', 'TRNSID', 'TRNSTYPE', 'DATE', 'ACCNT', 'NAME', 
                   'CLASS', 'AMOUNT', 'DOCNUM', 'MEMO', 'CLEAR']

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

    # Abort if no sales occurred
    if cart_payments.nrows() == 0:
        return paypal

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

    return paypal


def append_invoices(paypal, iif_path):
    """
    Take a paypal csv file (already sucked into PETL) and spit out
    the invoices and payments received for them
    
    """
    # TODO
    # Apparently a limitation of IIF files is that they can't associate
    # a payment with an invoice, so we might be better off manually recording
    # these
    # AH - well we can at least record the invoices
    # we'll have to manually record the payments against them.
    pass
    return paypal


def append_TicketLeap_fees(paypal, iif_path):
    """
    Take a paypal csv file (already sucked into PETL) and append the
    the TicketLeap payments (the fees they charge us for using TicketLeap)
    to the .IIF file
    
    Return a slimmer paypal PETL table instance, with the rows associated
    with TicketLeap payments removed.
    
    """
    source_fields = ['Type', 'Date', 'Gross']

    trns_fields = ['!TRNS', 'TRNSID', 'TRNSTYPE', 'DATE', 'ACCNT', 'NAME', 
                   'CLASS', 'AMOUNT', 'DOCNUM', 'CLEAR', 'TOPRINT', 
                   'NAMEISTAXABLE', 'ADDR1', 'ADDR2', 'ADDR3', 'ADDR4', 
                   'ADDR5']

    spl_fields  = ['!SPL', 'SPLID', 'TRNSTYPE', 'DATE', 'ACCNT', 'NAME', 
                   'CLASS', 'AMOUNT', 'DOCNUM', 'CLEAR', 'QNTY', 'PRICE', 
                   'INVITEM', 'PAYMETH', 'TAXABLE', 'VALADJ', 'REIMBEXP']

    # Here's how the QuickBooks file really maps to PayPal
    trns_map = {}
    trns_map['!TRNS'] = lambda r: 'TRNS'
    trns_map['NAME'] = lambda r: 'TicketLeap'
    trns_map['TRNSTYPE'] = lambda r: 'CHECK'
    trns_map['DATE'] = lambda r: r['Date'].strftime('%m/%d/%Y') #'{dt.month}/{dt.day}/{dt.year}'.format(dt=r['Date'])
    trns_map['ACCNT'] = lambda r: 'PayPal Account'
    trns_map['CLASS'] = lambda r: 'Other'
    trns_map['AMOUNT'] = lambda r: abs(r['Gross'])
    trns_map['CLEAR'] = lambda r: 'N'
    trns_map['TOPRINT'] = lambda r: 'N'

    spl_map = {}
    spl_map['!SPL'] = lambda r: 'SPL'
    spl_map['TRNSTYPE'] = lambda r: 'CHECK'
    spl_map['DATE'] = lambda r: r['Date'].strftime('%m/%d/%Y') #'{dt.month}/{dt.day}/{dt.year}'.format(dt=r['Date'])
    spl_map['ACCNT'] = lambda r: 'Operational Expenses:Association Administration:Bank Fees:PayPal Fees'
    spl_map['CLASS'] = lambda r: 'Other'
    spl_map['AMOUNT'] = lambda r: abs(r['Gross'])
    spl_map['CLEAR'] = lambda r: 'N'
    spl_map['REIMBEXP'] = lambda r: 'NOTHING'


    fees = paypal.selecteq('Type', 'Preapproved Payment Sent')
    fees_cut = fees.cut(*source_fields)

    trns_table = fees_cut.addrownumbers()
    spl_table = fees_cut.addrownumbers()

    for field in trns_fields:
        if field in trns_map:
            trns_table = trns_table.addfield(field, trns_map[field])
        else:
            trns_table = trns_table.addfield(field, '')

    for field in spl_fields:
        if field in spl_map:
            spl_table = spl_table.addfield(field, spl_map[field])
        else:
            spl_table = spl_table.addfield(field, '')

    trns_table = trns_table.cutout(*source_fields)
    spl_table = spl_table.cutout(*source_fields)
    trns_table = trns_table.cutout('row')
    spl_table = spl_table.cutout('row')

    iif_file = open(iif_path, 'a')
    writer = csv.writer(iif_file, delimiter='\t', lineterminator='\n')

    # .IIF HEADER
    writer.writerow(trns_table.header())
    writer.writerow(spl_table.header())
    writer.writerow(['!ENDTRNS'])

    trns_data = trns_table.data()
    spl_data = spl_table.data()

    # Now write each transaction one at a time
    for row_num in range(len(trns_data)):
        writer.writerow(trns_data[row_num])
        writer.writerow(spl_data[row_num])
        writer.writerow(['ENDTRNS'])

    iif_file.close()
   
    return etl.complement(paypal, fees)    


def get_customer_names(paypal):
    """
    Take a paypal csv file (already sucked into PETL) and spit out
    a petl table of the unique customer names
    
    """    
    names_source_fields = ['Name', 'Email', 'To Email', 'Address Line 1', 
                           'Address Line 2', 'Town/City', 'Province', 
                           'Postal Code', 'Country', 'Phone']
    """
    names_dest_fields = ['!CUST', 'NAME', 'BADDR1', 'BADDR2', 'BADDR3', 
                         'BADDR4', 'BADDR5', 'SADDR1', 'SADDR2', 'SADDR3', 
                         'SADDR4', 'SADDR5', 'PHONE1', 'PHONE2', 'FAXNUM', 
                         'EMAIL', 'NOTE', 'CONT1', 'CONT2', 'CTYPE', 'TERMS', 
                         'TAXABLE', 'LIMIT', 'RESALENUM', 'REP', 'TAXITEM', 
                         'NOTEPAD', 'SALUTATION', 'COMPANYNAME', 'FIRSTNAME', 
                         'MIDINIT', 'LASTNAME']
    """
    
    # The names associated with these are already in the payment
    names = paypal.selectne('Type', 'Invoice item')
    names =  names.selectne('Type', 'Shopping Cart Item')
         
    # We need the direction of the transaction to know what email to take
    names = names.addfield('Is From Customer', lambda rec: 1 if rec['Type'] == 'Shopping Cart Payment Received' else 0)
    names_source_fields.append('Is From Customer')

    names = names.cut(*names_source_fields)

    # Remove duplicates    
    names = names.distinct()

    # Remove some entries 
    names = names.selectne('Name', 'Bank Account')

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