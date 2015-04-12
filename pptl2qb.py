# -*- coding: utf-8 -*-
"""
@author: @MichaelCurrie

PayPal API reference:
https://developer.paypal.com/docs/api/

TicketLeap API reference:
http://dev.TicketLeap.com/
(for now the information is not detailed enough for use for transactions)

"""

import petl as etl
import csv, sys, os, datetime
from pp_helper import cleanup_paypal, eliminate_cancellations, get_customer_names
from pp_append import append_sales_as_deposits, append_invoices, append_TicketLeap_fees


def main(argv):
    """
    INPUT: paypal.csv
    OUTPUT: output.iif and unprocessed.csv
    
    """
    etl.config.look_style = 'minimal'
    input_folder = 'C:\\Users\\mcurrie\\Desktop\\GitHub\\TicketLeapToQuickBooks'
    #input_folder = 'C:\\Users\\Michael\\Desktop\\TicketLeapToQuickBooks'
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
    paypal = etl.fromcsv(paypal_path)
    print("Loaded PayPal input file (" + str(paypal.nrows()) + " rows)")

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
    #paypal = append_TicketLeap_fees(paypal, iif_path)


    # TicketLeap sales receipts make up the bulk of the transactions
    paypal = append_sales_as_deposits(paypal, iif_path)

    # Invoices are for tickets or for membership sales
    paypal = append_invoices(paypal, iif_path)


    # --------------------
    # 3. CREATE UNPROCESSED ROWS FILE
    print("Creating output unprocessed rows CSV file (" + 
          str(paypal.nrows()) + " rows)")

    unprocessed_file = open(unprocessed_path, 'w')
    writer = csv.writer(unprocessed_file, lineterminator='\n')
    writer.writerows(paypal)
    unprocessed_file.close()


if __name__ == "__main__":
    main(sys.argv[1:])