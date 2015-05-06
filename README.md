# Paypal To QuickBooks

[![Build Status](https://travis-ci.org/MichaelCurrie/TicketLeapToQuickBooks.svg?branch=master)](https://travis-ci.org/MichaelCurrie/TicketLeapToQuickBooks)

A little Python utility that converts PayPal transaction data - which may have been induced by PayPal acting as the fulfillment system for a TicketLeap account - into a format readable by QuickBooks Desktop (via the admittedly deprecated `.iif` file format).

Requires the [petl](https://pypi.python.org/pypi/petl) Python [ETL](http://en.wikipedia.org/wiki/Extract,_transform,_load) package.

Thanks very much to [http://www.my-quickbooks-expert.com/import-quickbooks.html](http://www.my-quickbooks-expert.com/import-quickbooks.html) for providing essential `.iif` file examples.

###Input:###

- `paypal.csv` file from PayPal
- `start_date`    (all dates before this date are not processed into the output file)
- `end_date`      (all dates after this date are not processed into the output file)

###Output:###

- `output.iif` [IIF file](http://www.my-quickbooks-expert.com/import-quickbooks.html) for QuickBooks
- `unprocessed.csv` file with the unprocessed `paypal.csv` rows between `start_date` and `end_date`
  - this contains all rows that could not be automatically converted into entries in the `.iif` file by this utility
  - i.e. in the case where no rows could be processed, and all rows in the original `paypal.csv` file lie between `start_date` and `end_date`, `unprocessed.csv` will be a verbatim copy of `paypal.csv`

###Implementation details###
1. Take the input `.csv` files and render it as a petl table object
2. Clean up the data, formats dates and numbers properly, etc, remove unneeded columns and rows not between the desired dates
3. Eliminate cancelled transactions and their associated cart items
4. Append to `output.iif` three kinds of transactions I bothered to handle automatically:
  - append_sales_as_deposits
  - append_invoices
  - append_TicketLeap_fees
5. Generate `output.iif`
6. Generate `unprocessed.csv`, which contains all transactions not handled by the above and that will therefore need to be entered into QuickBooks manually.


###Summary of transaction types implemented###

![](https://github.com/MichaelCurrie/TicketLeapToQuickBooks/blob/master/documentation/transaction%20types.jpeg)


###Details of `output.iif`###

This is a text file, whose first three lines are:

```
!TRNS	DATE	ACCNT	NAME	CLASS	AMOUNT	MEMO
!SPL	DATE	ACCNT	NAME	AMOUNT	MEMO
!ENDTRNS
```

The next lines are a sequence of transactions:

Each transaction is on a TRNS...ENDTRNS block:
```
TRNS	"1/3/2015"	"Paypal Account"	"Stephen Spielberg"	"Shopping Cart Payment Received"	225.46	"Memo for whole deposit"	
SPL	"1/3/2015"	"Other Income"	"Stephen Spielberg"	-232.50
SPL	"1/3/2015"	"Other Expenses"	Fee	7.04
ENDTRNS
```
Which appears as:

![](https://github.com/MichaelCurrie/TicketLeapToQuickBooks/blob/master/documentation/deposit.jpeg)

