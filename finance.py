#invalid operation helps to catch invalid decimal conversions
# I use decimal for accurate money computation
from decimal import Decimal, InvalidOperation 

import pandas as pd


def parse_money(value, field_name="Amount"):
    """Read finite money with at mosttwo decimal places; never round input slightly."""
    try:
        amount= Decimal(str(value).strip())                             #convert the value to text, remove extra spaces, then convert it to Decimal
        if not amount.is_finite():                                      # reject special value such as infinity or NaN
            raise ValueError(f"{field_name} must be a finite number.")
        cents= amount.quantize(Decimal("0.01"))                         #Convert the monetary value to two decimal places
        if amount != cents:                                             #Reject value that contain more than two decimal places
            raise ValueError(f"{field_name} must have at most decimal places.")
        return cents
    except (InvalidOperation,TypeError) as error:
        raise ValueError(f"{field_name} must be a valid monetary amount") from error



class Finance:

    COLUMNS = ["sale_id", "amount", "date"]

    def __init__(self, income_df=None):
        self.income_df= income_df if income_df is not None else pd.DataFrame(columns=self.COLUMNS)
        self.amount_received=Decimal("0")                          #It is used to store the amount received from the customer
        self.change= Decimal("0")                                  #It is used to store the customer's change after payment

    def record_income(self, sale_summary):                         #It creates one income record using information from a completed sale 
        row= { "sale_id": sale_summary["sale_id"], 
              "amount": str(sale_summary["total"]),
              "date": sale_summary["sale_date"],
              }
        self.income_df= pd.concat([self.income_df, pd.DataFrame([row])], ignore_index= True)  #It adds the new income record to the existing income DataFrame

    def process_payment(self,total, amount_received):
        total = parse_money(total, "Total")
        amount_received = parse_money(amount_received,"amount recieved")
        if total <= 0:
            raise ValueError("Total must be greater than zero.")
        if amount_received < total :
            raise ValueError(f"Insufficient payment. {total - amount_received:.2f} more is needed.")
        self.amount_received = amount_received
        self.change = amount_received - total
        return self.change






    
    
