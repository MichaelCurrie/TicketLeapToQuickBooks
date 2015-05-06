# -*- coding: utf-8 -*-
"""
Created on Tue Mar 31 02:25:03 2015

@author: Michael

Three helper functions to cleanup and do basic extraction from the paypal data:

cleanup_paypal
eliminate_cancellations
get_customer_names

"""

import petl as etl
import datetime, time, string


def cleanup_paypal(paypal):
    """
    Take a paypal csv file (already sucked into PETL) and clean it up
    
    """
    # Remove leading and trailing whitespace in the header row
    paypal_clean = paypal.setheader(list((x.strip() for x in paypal.header())))

    # Rename some header names to more convenient names
        # Sales receipts:
    paypal_clean = paypal_clean.rename('From Email Address', 'Email') 
    paypal_clean = paypal_clean.rename('To Email Address', 'To Email') 
        # Invoices, payments:
    paypal_clean = paypal_clean.rename('Contact Phone Number', 'Phone')
    paypal_clean = paypal_clean.rename('Zip/Postal Code', 'Postal Code')
    paypal_clean = paypal_clean.rename('State/Province/Region/County/'
                                       'Territory/Prefecture/Republic',
                                       'Province')
    paypal_clean = paypal_clean.rename('Address Line 2/District/Neighborhood',
                                       'Address Line 2')

    # It seems that Quickbooks requires that phone numbers be entirely 
    # composed of digits, e.g. 4035559195 instead of 403-555-9195
    paypal_clean = paypal_clean.convert('Phone', 
                       lambda v: ''.join(c for c in v if c in string.digits))

    # Get rid of columns that are not needed
    paypal_clean = paypal_clean.cutout('Time',
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

    paypal_clean = paypal_clean.convert('Date', convert_ppdate)

    # Workaround to avoid the strange bug described here
    # Set all days before the 13th of any given month to the 13th of 
    # that month.
    # https://github.com/MichaelCurrie/TicketLeapToQuickBooks/issues/1
    paypal_clean = paypal_clean.convert('Date',
        lambda v: datetime.date(v.year, v.month, 13) if v.day < 13 else v)

    # Convert all figures like "1,000.00" to "1000.00"
    paypal_clean = paypal_clean.convert(('Gross', 'Fee', 'Quantity'),
                                        lambda v: v.replace(',',''))
    # Convert the money and quantity columns from string to float
    paypal_clean = paypal_clean.convert(('Gross', 'Fee', 'Quantity'),
                                        float)

    return paypal_clean



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

