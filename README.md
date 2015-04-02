# Paypal To QuickBooks
## pptl2qb.py

A little Python utility that converts PayPal transaction data into a format readable by QuickBooks (i.e. a .iif file)

Requires the [petl](https://pypi.python.org/pypi/petl) Python [etl](http://en.wikipedia.org/wiki/Extract,_transform,_load) package.

Thanks very much to http://www.my-quickbooks-expert.com/import-quickbooks.html for providing essential .iif file examples.

###Input:###

- paypal.csv file from PayPal
- start_date    (all dates before this date are not processed into the output file)
- end_date      (all dates after this date are not processed into the output file)

###Output:###

- output.[iif](http://www.my-quickbooks-expert.com/import-quickbooks.html) file for QuickBooks
- unprocessed.csv file with the unprocessed paypal.csv rows between start_date and end_date
  - this contains all rows that could not be automatically converted into entries in the .iif file by this utility
  - i.e. in the case where no rows could be processed, and all rows in the original paypal.csv file lie between start_date and end_date, unprocessed.csv will be a verbatim copy of paypal.csv

###Implementation details###
- Takes both input .csv files and put them into an SQLite database, joining on the common fields
  - For ticketleap.csv, the fields are `Buyer Email`, `Date of Purchase`, `Ticket Net Proceeds`
  - For paypal.csv, the corresponding fields are `From Email Address`, `Date`, `Gross`
- This will likely only work for ticketleap.csv rows with `Order Method` = `Web-Online`, as the `Web-Onsite` ones appear to be the manual entries that do not appear in the PayPal record directly: they might have been settled with cash, or cheque, or by Grace or Michael manually invoicing ourselves and paying with the user's credit card.
- Need to make sure date is properly represented (and just round to the nearest day since the paypal and ticketleap times will be slightly different)
- There is still a possibility of someone making two orders for the exact same amount in the same day, but that just means a duplicate QuickBooks entry too, so that's okay.

Then generate `output.iif`:

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

###Types of transactions from PayPal###

1. Ticketleap ticket sale
```
TRNS	"1/3/2015"	"Paypal Account"	"Stephen Spielberg"	"Shopping Cart Payment Received"	225.46	"Memo for whole deposit"	
SPL	"1/3/2015"	"Other Income"	"Stephen Spielberg"	-232.50
SPL	"1/3/2015"	"Other Expenses"	Fee	7.04
ENDTRNS
```

2. Paypal money sent



Keyword	Description
```
!ACCNT    	Details about your chart of accounts.
!CUST	      A customer address or phone list.
!VEND	      A vendor address or phone list.
!EMP	      A list of employees.
!OTHERNAME	A list of names you'd like to add to QuickBooks Other Name list.
!BUD	      Budget details.
!CLASS	    A list of general classifications you'd like to add to QuickBooks Class list.
!CTYPE	    A list of customer classifications you'd like to add to QuickBooks Customer Type list.
!INVITEM	  Details about the line items you use on sales and purchase forms.
!INVMEMO	  Messages you'd like to add to QuickBooks Customer Message list.
!PAYMETH	  A list of payment methods you'd like to add to QuickBooks Payment Method list.
!SHIPMETH	  A list of shipping methods you'd like to add to QuickBooks Ship Via list.
!TERMS	    A list of payment terms you'd like to add to QuickBooks Terms list.
!TIMEACT	  Details about activities you timed with the QuickBooks Timer. Works with !TIMERHDR.
!TIMERHDR	  QuickBooks Timer data.
!TODO     	A list of upcoming "to do" tasks you want QuickBooks to remind you about.
!TRNS	      Transactions.
!VTYPE	    A list of vendor classifications you'd like to add to QuickBooks Vendor Type list.
```

