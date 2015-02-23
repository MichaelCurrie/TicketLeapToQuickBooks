# TicketLeapToQuickBooks

Convert TicketLeap sales transaction data into a format readable by QuickBooks

Assumes you have opted to use PayPal for your credit card processing.

##Implementation details##
- Take both input .csv files and put them into an SQLite database, joining on the common fields
  - For ticketleap.csv, the fields are `Buyer Email`, `Date of Purchase`, `Ticket Net Proceeds`
  - For paypal.csv, the fields are `From Email Address`, `Date`, `Gross`
- This will likely only work for ticketleap.csv rows with `Order Method` = `Web-Online`, as the `Web-Onsite` ones appear to be the manual entries that do not appear in the PayPal record directly: they might have been settled with cash, or cheque, or by Grace or Michael manually invoicing ourselves and paying with the user's credit card.
- Need to make sure date is properly represented (and just round to the nearest day since the paypal and ticketleap times will be slightly different)
- There is still a possibility of someone making two orders for the exact same amount in the same day, but that just means a duplicate QuickBooks entry too, so that's okay.

Then generate 


##Program specification##

###Input:###

ticketleap.csv file from TicketLeap
paypal.csv file from PayPal
StartDate
EndDate

###Output:###

.iif file for QuickBooks

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

Each transaction is on a TRNS...ENDTRNS block:
```
TRNS	"1/3/2015"	"Paypal Account"	"Stephen Spielberg"	"Shopping Cart Payment Received"	225.46	"Memo for whole deposit"	
SPL	"1/3/2015"	"Other Income"	"Stephen Spielberg"	-232.50
SPL	"1/3/2015"	"Other Expenses"	Fee	7.04
ENDTRNS
```
Appears as:

![](https://github.com/MichaelCurrie/TicketLeapToQuickBooks/blob/master/documentation/deposit.jpeg)
