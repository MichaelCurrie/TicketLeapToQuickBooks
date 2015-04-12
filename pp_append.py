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
                   'CLASS', 'AMOUNT', 'DOCNUM', 'MEMO', 'CLEAR', 'PAYMETH']

    # "spl" for "split", a term in QuickBooks for how a transaction is broken
    # down (or "split") into the items underlying the transaction
    # Like if you spent $10, the split might be two rows: $2 for a banana and 
    # $8 for a magazine.
    spl_fields  = ['!SPL', 'SPLID', 'TRNSTYPE', 'DATE', 'ACCNT', 'NAME', 
                   'CLASS', 'AMOUNT', 'DOCNUM', 'MEMO', 'CLEAR', 'PAYMETH']

    #fee_acct = 'Operational Expenses:Association Administration:Bank Fees:PayPal Fees'
    fee_acct = 'Competition Expenses:Sales:Ticketing:PayPal Fees'
    discount_acct = 'Competition Expenses:Advertising & Sponsorship:Promotions:Early Bird'

    # SPECIFY SOURCE/DEST MAPPINGS
    # Here's how the QuickBooks file really maps to PayPal
    trns_map = {}
    trns_map['!TRNS'] = lambda r: 'TRNS'
    trns_map['TRNSID'] = lambda r: ' '    
    trns_map['TRNSTYPE'] = lambda r: 'DEPOSIT'
    trns_map['NAME'] = lambda r: r['Name']
    trns_map['DATE'] = lambda r: r['Date'].strftime('%m/%d/%Y') #'{dt.month}/{dt.day}/{dt.year}'.format(dt=r['Date'])
    trns_map['ACCNT'] = lambda r: 'PayPal Account'
    trns_map['CLASS'] = lambda r: ''  # The real class is in the split items
    trns_map['AMOUNT'] = lambda r: round(r['Gross']-abs(r['Fee']), 2)
    trns_map['MEMO'] = lambda r: 'TicketLeap ticket sale'
    trns_map['CLEAR'] = lambda r: 'N'
    
    spl_map = {}
    spl_map['!SPL'] = lambda r: 'SPL'
    spl_map['TRNSTYPE'] = lambda r: 'DEPOSIT'
    spl_map['DATE'] = lambda r: r['Date'].strftime('%m/%d/%Y') #'{dt.month}/{dt.day}/{dt.year}'.format(dt=r['Date'])
    spl_map['CLEAR'] = lambda r: 'N'
    spl_map['PAYMETH'] = lambda r: 'Paypal'

    # The ticket sale
    spl_map_sale = spl_map.copy()
    spl_map_sale['NAME'] = lambda r: r['Name']
    spl_map_sale['MEMO'] = lambda r: r['Item Title'] + ' ' + r['Item ID']
    # For some reason QuickBooks wants the sale amount to be negative and the 
    # FEE (see spl_map_fee below) to be positive!  Ah, QuickBooks...
    spl_map_sale['AMOUNT'] = lambda r: round(-abs(r['Gross']), 2)

    # The fee (associated with the payment)
    spl_map_fee = spl_map.copy()
    spl_map_fee['ACCNT'] = lambda r: fee_acct
    spl_map_fee['MEMO'] = lambda r: 'Standard PayPal $0.30 + 2.9% for TicketLeap ticket sale fulfillment'
    spl_map_fee['AMOUNT'] = lambda r: round(abs(r['Fee']), 2)

    # The discount (associated with the payment)
    spl_map_discount = spl_map.copy()
    spl_map_discount['NAME'] = lambda r: r['Name']    
    spl_map_discount['ACCNT'] = lambda r: discount_acct
    spl_map_discount['MEMO'] = lambda r: 'Discount for buying early'
    

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
    writer.writerow(trns_fields + ['']*22)
    writer.writerow(spl_fields + ['']*22)
    writer.writerow(['!ENDTRNS'] + ['']*32)

    # Write each transaction to the IIF file
    for tranID in cart_payments.columns()['Transaction ID']:
        cur_cart_payment = cart_payments_cut.selecteq('Transaction ID', tranID)
        cur_cart_items = cart_items_cut.selecteq('Transaction ID', tranID)

        #---------------
        # I think there should just be one payment line per transaction ID
        assert(cur_cart_payment.nrows() == 1)

        trns_table = get_tables_from_mapping(cur_cart_payment, 
                                             trns_fields, trns_map)
        trns_total = trns_table.values('AMOUNT')[0]

        # Write the master payment line for the transaction
        # We assume there's one row (see assert above)
        writer.writerow(list(trns_table.data()[0]) + ['']*22)

        #---------------
        # Handle the split lines: (1) the fee, and (2) the cart items,
        # and the (3) discount, if any

        # Figure out the class (assume the cart is full of items from only 
        # one competition.  If not the only problem will be the fee will be 
        # partly misallocated.  That's not a big deal!)

        item_class, item_account = qb_account(
            cur_cart_items.values('Item Title')[0])

        spl_map_fee['CLASS'] = lambda r: item_class
        # (1) The fee associated with the whole transaction.
        spl_fee_table = get_tables_from_mapping(cur_cart_payment, 
                                                spl_fields, spl_map_fee)
        # Again we can assume there's one row (see assert above)
        writer.writerow(list(spl_fee_table.data()[0]) + ['']*22) 

        # (2) Handle the split lines for the cart items
        spl_sale_table = get_tables_from_mapping(cur_cart_items, 
                                                 spl_fields, spl_map_sale)
                             
        spl_total = spl_fee_table.values('AMOUNT')[0]
        spl_sale_data = spl_sale_table.records()
        for item in spl_sale_data:
            item_as_list = list(item)
            # Figure out the account and class for this item
            item_class, item_account = qb_account(item['MEMO'])
            item_as_list[item.flds.index('CLASS')] = item_class
            item_as_list[item.flds.index('ACCNT')] = item_account
            # Record the sale lines itemizing what was in the cart
            writer.writerow(item_as_list + ['']*22)
            spl_total += item_as_list[item.flds.index('AMOUNT')]


        # (3) The discount associated with the whole transaction. (if any)
        #     since paypal does not actually provide this as a separate field
        #     we must infer it from the difference between the transaction
        #     payment total and the split total
        if(abs(trns_total + spl_total) >= 0.01):
            spl_map_discount['CLASS'] = lambda r: item_class            
            spl_map_discount['AMOUNT'] = \
                lambda r: -round(trns_total + spl_total, 2)
            spl_discount_table = get_tables_from_mapping(cur_cart_payment, 
                                                         spl_fields, 
                                                         spl_map_discount)
            # Again we can assume there's one row (see assert above)
            writer.writerow(list(spl_discount_table.data()[0]) + ['']*22) 

        #---------------
        # Write each transactions' closing statement in the IIF
        writer.writerow(['ENDTRNS'] + ['']*32)
        # Let's double check that the split adds up to the transaction!
        #assert(trns_total == -spl_total)
        """
        if(abs(trns_total + spl_total) >= 0.01):
            raise Exception("Split ($" + str(spl_total) + ") does not equal " +
                            "transaction ($" + str(trns_total) + ") " +
                            "for Name = " + trns_table.values('NAME')[0] + 
                            " on (rounded up to day 13) date " + 
                            trns_table.values('DATE')[0])
        """
    iif_file.close()

    # RETURN UNUSED ROWS
    # Return the original paypal table, minus all the entries
    # we just processed
    paypal_without_cart_sales = etl.complement(paypal, cart_payments)
    paypal_without_cart_sales = etl.complement(paypal_without_cart_sales,
                                               cart_items)
    return paypal_without_cart_sales


def qb_account(item_title):
    """
    Given an item title, returns the appropriate QuickBooks class and account
    
    Parameter: item_title
    Returns: item_class, item_account    

    Note that this is only guaranteed to work for Ticketleap sales, not 
    PayPal invoices.
    
    """
    if 'Northern' in item_title or 'NLC' in item_title:
        item_class = 'NLC'
    else:
        item_class = 'CCC'
    
    if 'Competitor' in item_title:
        item_account = ('Competition Income:Competitors:'
                       'Amateur Registration Fees')
    else:
        item_account = 'Competition Income:Sales:Tickets:Advance Tickets'
        
    return item_class, item_account


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
    trns_map['TRNSID'] = lambda r: ' '
    trns_map['DOCNUM'] = lambda r: ' '
    trns_map['NAMEISTAXABLE'] = lambda r: ' '
    trns_map['NAME'] = lambda r: 'TicketLeap'
    trns_map['TRNSTYPE'] = lambda r: 'CHECK'
    trns_map['DATE'] = lambda r: r['Date'].strftime('%m/%d/%Y') #'{dt.month}/{dt.day}/{dt.year}'.format(dt=r['Date'])
    trns_map['ACCNT'] = lambda r: 'PayPal Account'
    trns_map['CLASS'] = lambda r: 'Other'
    # For some reason QuickBooks requires that the cheque total amount be 
    # negative, but each item is positive.
    trns_map['AMOUNT'] = lambda r: -abs(r['Gross'])  
    trns_map['CLEAR'] = lambda r: 'N'
    trns_map['TOPRINT'] = lambda r: 'N'

    spl_map = {}
    spl_map['!SPL'] = lambda r: 'SPL'
    spl_map['SPLID'] = lambda r: ' '
    spl_map['TRNSTYPE'] = lambda r: 'CHECK'
    spl_map['DATE'] = lambda r: r['Date'].strftime('%m/%d/%Y') #'{dt.month}/{dt.day}/{dt.year}'.format(dt=r['Date'])
    spl_map['ACCNT'] = lambda r: 'Operational Expenses:Association ' + \
                                 'Administration:Bank Fees:PayPal Fees'
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
    writer.writerow(list(trns_table.header()) + ['']*15)
    writer.writerow(list(spl_table.header())  + ['']*15)
    writer.writerow(['!ENDTRNS']+['']*31)

    trns_data = trns_table.data()
    spl_data = spl_table.data()

    # Now write each transaction one at a time
    for row_num in range(len(trns_data)):
        writer.writerow(list(trns_data[row_num]) + ['']*15)
        writer.writerow(list(spl_data[row_num]) + ['']*15)
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

