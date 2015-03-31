# -*- coding: utf-8 -*-
"""
Created on Tue Mar 31 02:30:46 2015

@author: Michael Currie

Methods to extract transaction data from the paypal extract file:

append_sales_as_deposits
append_invoices
append_TicketLeap_fees

+ one "private" method:

get_tables_from_mapping

"""

import petl as etl
import csv


def append_sales_as_deposits(paypal, iif_path):
    """
    Take a paypal csv file (already sucked into PETL) and spit out
    the deposits
    
    """
    # SPECIFY SOURCE/DEST FIELD NAMES
    payment_source_fields = ['Date', 'Name', 'Email', 'Gross', 'Fee', 
                             'Transaction ID']

    item_source_fields = ['Date', 'Name', 'Item Title', 'Item ID', 'Quantity', 'Gross', 
                          'Transaction ID']

    trns_fields = ['!TRNS', 'TRNSID', 'TRNSTYPE', 'DATE', 'ACCNT', 'NAME', 
                   'CLASS', 'AMOUNT', 'DOCNUM', 'MEMO', 'CLEAR']

    # "spl" for "split", a term in QuickBooks for how a transaction is broken
    # down (or "split") into the items underlying the transaction
    # Like if you spent $10, the split might be two rows: $2 for a banana and 
    # $8 for a magazine.
    spl_fields  = ['!TRNS', 'TRNSID', 'TRNSTYPE', 'DATE', 'ACCNT', 'NAME', 
                   'CLASS', 'AMOUNT', 'DOCNUM', 'MEMO', 'CLEAR']

    fee_acct = 'Operational Expenses:Association Administration:Bank Fees:PayPal Fees'
    ticket_sales_acct = 'Competition Income:Sales:Tickets:Advance Tickets'

    # SPECIFY SOURCE/DEST MAPPINGS
    # Here's how the QuickBooks file really maps to PayPal
    trns_map = {}
    trns_map['!TRNS'] = lambda r: 'TRNS'
    trns_map['TRNSTYPE'] = lambda r: 'DEPOSIT'
    trns_map['NAME'] = lambda r: r['Name']
    trns_map['DATE'] = lambda r: r['Date'].strftime('%m/%d/%Y') #'{dt.month}/{dt.day}/{dt.year}'.format(dt=r['Date'])
    trns_map['ACCNT'] = lambda r: 'PayPal Account'
    trns_map['CLASS'] = lambda r: 'Other'  # DEBUG
    trns_map['AMOUNT'] = lambda r: r['Gross']
    trns_map['MEMO'] = lambda r: 'TicketLeap ticket sale (Python auto-loaded)'
    trns_map['CLEAR'] = lambda r: 'N'
    
    spl_map = {}
    spl_map['!SPL'] = lambda r: 'SPL'
    spl_map['TRNSTYPE'] = lambda r: 'DEPOSIT'
    spl_map['DATE'] = lambda r: r['Date'].strftime('%m/%d/%Y') #'{dt.month}/{dt.day}/{dt.year}'.format(dt=r['Date'])
    spl_map['CLEAR'] = lambda r: 'N'
    spl_map['CLASS'] = lambda r: 'Other'   # DEBUG: figure out dynamically

    # The ticket sale
    spl_map_sale = spl_map.copy()
    spl_map_sale['NAME'] = lambda r: r['Name']
    spl_map_sale['ACCNT'] = lambda r: ticket_sales_acct
    spl_map_sale['MEMO'] = lambda r: r['Item Title'] + ' ' + r['Item ID']
    spl_map_sale['AMOUNT'] = lambda r: abs(r['Gross'])

    # The fee (associated with the payment)
    spl_map_fee = spl_map.copy()
    spl_map_fee['ACCNT'] = lambda r: fee_acct
    spl_map_fee['MEMO'] = lambda r: 'Standard PayPal $0.30 + 2.9% for TicketLeap ticket sale fulfillment'
    spl_map_fee['AMOUNT'] = lambda r: -abs(r['Fee'])

    # PREPARE CART PAYMENTS TABLE
    # Sales receipts are organized in the CSV file as a row to summarize,
    # (cart payment), plus one or more rows for each of the items purchased.
    cart_payments = paypal.selecteq('Type', 'Shopping Cart Payment Received')
    # Ignore refunds
    cart_payments = cart_payments.selecteq('Status', 'Completed')

    # Abort if no sales occurred
    if cart_payments.nrows() == 0:
        return paypal

    cart_payments_cut = cart_payments.cut(*payment_source_fields)

    # PREPARE CART ITEMS TABLE
    cart_items = paypal.selecteq('Type', 'Shopping Cart Item')
    cart_items_cut = cart_items.cut(*item_source_fields)

    # WRITE THE IIF FILE
    iif_file = open(iif_path, 'a')
    writer = csv.writer(iif_file, delimiter='\t', lineterminator='\n')
    # Write the .IIF header
    writer.writerow(trns_fields)
    writer.writerow(spl_fields)
    writer.writerow(['!ENDTRNS'])

    # Write each transaction to the IIF file
    for tranID in cart_payments.columns()['Transaction ID']:
        cur_cart_payment = cart_payments_cut.selecteq('Transaction ID', tranID)
        cur_cart_items = cart_items_cut.selecteq('Transaction ID', tranID)

        #---------------
        # I think there should just be one payment line per transaction ID
        assert(cur_cart_payment.nrows() == 1)

        trns_table = get_tables_from_mapping(cur_cart_payment, 
                                             trns_fields, trns_map)

        # Write the master payment line for the transaction
        # We assume there's one row (see assert above)
        writer.writerow(trns_table.data()[0])  

        #---------------
        # Handle the split lines: (1) the fee, and (2) the cart items

        # (1) The fee associated with the whole transaction.
        spl_fee_table = get_tables_from_mapping(cur_cart_payment, 
                                            spl_fields, spl_map_fee)
        # Again we can ssume there's one row (see assert above)
        writer.writerow(spl_fee_table.data()[0]) 

        # (2) Handle the split lines for the cart items
        spl_sale_table = get_tables_from_mapping(cur_cart_items, 
                                            spl_fields, spl_map_sale)
                                            
        spl_sale_data = spl_sale_table.data()
        for item_number in range(len(spl_sale_data)):
            # Record the sale lines itemizing what was in the cart
            writer.writerow(spl_sale_data[item_number])

        #---------------
        # Write each transactions' closing statement in the IIF
        writer.writerow(['ENDTRNS'])

    iif_file.close()

    # RETURN UNUSED ROWS
    # Return the original paypal table, minus all the entries
    # we just processed
    paypal_without_cart_sales = etl.complement(paypal, cart_payments)
    paypal_without_cart_sales = etl.complement(paypal_without_cart_sales,
                                               cart_items)
    return paypal_without_cart_sales


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

    trns_table = get_tables_from_mapping(fees_cut, trns_fields, trns_map)
    spl_table = get_tables_from_mapping(fees_cut, spl_fields, spl_map)

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


def get_tables_from_mapping(source_table, dest_fields, source_dest_map):
    """
    Obtain a petl tables from a source petl table and some mappings
    source_table: petl table
    dest_fields: list
    source_dest_map: dict
    
    Returns
    dest_table: petl table
    
    """
    source_fields = list(source_table.header())

    # Build up trns_table and spl_table from the source_table
    dest_table = source_table.addrownumbers()

    # Add the new fields one at a time.  There might be a better 
    # way to do this.
    for field in dest_fields:
        if field in source_dest_map:
            dest_table = dest_table.addfield(field, source_dest_map[field])
        else:
            dest_table = dest_table.addfield(field, '')

    # Cut out the original columns from the source_table to obtain
    # the destination tables, trns_table and spl_table
    dest_table = dest_table.cutout(*source_fields)
    dest_table = dest_table.cutout('row')

    return dest_table

