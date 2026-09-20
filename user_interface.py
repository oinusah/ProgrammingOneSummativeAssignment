from file_handling import FileHandling
from finance import Finance
from inventory import Inventory
from product import Product
from sales import Sales

from time import sleep

from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.progress import Progress
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

PRIMARY = "bold bright_blue"
ACCENT = "bold #ff69b4"
SUCCESS = "bold green"
WARNING = "bold yellow on red"
ERROR = "bold red"

sleep_amount = 0.03

class ShopApplication:
    MENU = {
        "1":"Add product", "2": "Display all products", "3": "Search products",
        "4":"Update product information", "5": "Update product quantity",
        "6":"Record a sale", "7": "Display low-stock products",
        "8":"Display sales information", "0": "Save and exit",
    }
    FIELDS = {
        "product_name": "Product name", "price": "Price", "category": "Category",
        "brand": "Brand", "size": "Size", "supplier": "Supplier",
        "expiry_date": "Expiry date DD/MM/YYYY",
    }

    def __init__(self, data_directory= "data", low_stock_limit = 5):
        self.inventory = Inventory( low_stock_limit)
        self.files = FileHandling(data_directory)
        self.sales = self.finance = None
        self.console = Console(theme=Theme({"prompt": PRIMARY}))
        self.pending_save = set()


    def run(self):
        if self._ask("Types yes to open, or exit to close", choices= ("yes","exit")) == "exit":
            return
        try:
            self._start_application()
        except (OSError, ValueError, TypeError) as error:
            self.console.log(f" {error} cannot open shop app", style="bold yellow on red", markup=False)
            return
        self.console.print(Panel("Welcome to My shop inventory & sales Tracker",style= ACCENT, border_style=PRIMARY, expand=False))
        while self._save_changes():
            self._show_menu()
            choice = self._ask("choose you menu option",show_choices=False, choices= list(self.MENU))
            try:
                if choice == "0":
                    self.console.print("All changes saved. Goodbye!", style=SUCCESS)
                    return
                if choice == "1":
                    self._add_product()
                elif choice in ("2","3","7"):
                    products= self.inventory.get_all_products()
                    title = "All products"
                    if choice == "3":
                        keyword = self._ask("Enter an ID, name, category,brand, or supplier")
                        products = self.inventory.search_products(keyword)
                        title = "Search Results"
                    elif choice == "7":
                        products = self.inventory.get_low_stock_products()
                        title ="Low-Stock Results"
                    self._print_products(products, title)
                elif choice in ("4","5"):
                    self._update_product(quantity_only=choice == "5")
                elif choice == "6" and self._record_sale() is False:
                    return
                elif choice == "8":
                    history = self.sales.get_sales_history()
                    headings = [name.replace("_"," ").title() for name in history.columns]
                    self._table("sale History", headings, history.itertuples(index=False, name=None))
            except ValueError as error:
                self.console.print( str(error),style=ERROR, markup=False)         

    def _ask(self, label,show_choices = True, **options):  # raw funtion that Propmts the user to return trimmed input.. to be use explitly in this codes...Basicx
        return Prompt.ask(f"[{PRIMARY}] {escape(label)} [/{PRIMARY}]", console= self.console, show_choices=show_choices, show_default=False,**options).strip()

    def _table(self,title, headings, rows, show_header=True):
        table = Table( title=title, title_style=ACCENT,box=box.ROUNDED,
                      border_style=PRIMARY, header_style=PRIMARY, show_header=show_header)
        for heading in headings:
            table.add_column(heading)
        for row in rows:
            cells = []
            for value in row:
                cells.append(value if isinstance(value,Text) else Text(str(value)))
            table.add_row(*cells)
        if table.row_count:
            self.console.print(table)
        else:
            self.console.print("No record found.", style=WARNING)

    def _start_application(self): 
        self.files.prepare_directory()
        loaders = [self.files.load_products, self.files.load_sales, self.files.load_income]
        results = []
        with Progress(console=self.console) as progress:
            task = progress.add_task(f"[{ACCENT}]Opening shop system...", total=len(loaders))
            for loader in loaders:
                results.append(loader())
                sleep(sleep_amount)
                progress.advance(task)
                progress.refresh()
            self.inventory.products = results[0]
            self.sales = Sales(self.inventory, results[1])
            self.finance = Finance(results[2])
                  
    def _save_changes(self): #load CSVs into inventory/sales/finance
        while self.pending_save:
            try:
                self.files.save_changes(self.inventory, self.sales, self.finance, self.pending_save)
            except OSError as error:
                self.console.print(f"Save failed:{error}",style=ERROR, markup=False)
                self.console.print("changes remain in memory, Fix file acces, then retry.", style=WARNING)
                if self._ask("Retry saving?", choices=["yes", "no"], default="yes") == "no":
                    self.console.print("Closed with unsaved changes. Check all three CSVs before reopening.", style= WARNING)
                    return False
        return True        

    def _show_menu(self): # shows the user MENU
        self.console.print(Panel(
            f"[cyan]PRODUCT:[/] {len(self.inventory)}  "
            f"[yellow]Low stock:[/] {len(self.inventory.get_low_stock_products())}",
            title="shop Details", title_align="Left",border_style=PRIMARY, expand=False,
            style=ACCENT
,        ))
        rows = [(Text(key, style=PRIMARY), Text(label, style=ACCENT))
            for key, label in self.MENU.items()]
        self._table("Main Menu", ["Option", "Action"], rows, show_header=False)

    def _add_product(self):
        self.console.print(Panel("Add product", border_style=PRIMARY, style=ACCENT))
        values = {"product_id": self._ask("Product ID")}
        for field, label in self.FIELDS.items():
            values[field] = self._ask(label)
            if field == "price":
                values["quantity"] = self._ask("quantity")
        self.inventory.add_product(Product(**values))
        self.pending_save.add("products")
        self.console.print("Product added.", style=SUCCESS)        

    def _update_product(self, quantity_only=False):
        product_id = self._ask("Product ID")
        if self.inventory.find_product(product_id) is None:
            raise ValueError(" Product not found")
        if quantity_only:
            self.inventory.update_quantity( product_id, self._ask("New quantity"))
        else:
            choices = dict(enumerate(self.FIELDS, start=1))
            self._table("Field to update", ["Option", "Field"], enumerate(self.FIELDS.values(), start=1))
            choice = self._ask("Field to update", show_choices=False, choices=[str(number) for number in choices])
            field = choices[int(choice)]
            value = self._ask(f"New {self.FIELDS[field]}")
            self.inventory.update_product(product_id, {field: value})
        self.pending_save.add("products")
        self.console.print("Product updated.", style=SUCCESS)

    def _print_products(self, products, title):
        rows = []
        for product in products:
            status = Text("OK", style=SUCCESS)
            if product.quantity <= self.inventory.low_stock_limit:
                status =Text("LOW", style=WARNING)
            if product.quantity == 0:
                status = Text("OUT", style=ERROR)
            rows.append((
                product.product_id,
                product.product_name,
                product.category or "-",
                product.brand or "-",
                f"{product.price:.2f}",
                product.quantity, status
            ))
        self._table(title, ["ID", "Product", "Category", "Brand", "Price", "Quantity", "Status"],rows)        
                
    def _record_sale(self):
        self.sales.cancel_sale()
        self.console.print(Panel("Enter items; type Done to checkout", border_style=PRIMARY, style=ACCENT))
        while True:
            product_id = self._ask("Product ID")
            if product_id.lower().strip() == "done":
                break
            try:
                self.sales.add_item( product_id, self._ask("Quantity"))
            except ValueError as error:
                self.console.print(str(error), style=ERROR, markup=False) 
        if not self.sales.current_sale:
            self.console.print("No items were added", style=WARNING)
            return
        rows = [ (item["product_name"], item["quantity"], f"{item['unit_price']:.2f}",
               f"{item['subtotal']:.2f}") for item in self.sales.current_sale]
        self._table("Current Sale", ["Product", "Quantity", "Unit Price", "Subtotal"], rows)
        total = self.sales.calculate_total()
        self.console.print(f"Total: {total:.2f}", style=PRIMARY)
        while True:
            try:
                change = self.finance.process_payment(total, self._ask("Amount received"))
                complete = self._ask("Complete this sale?", choices=["yes", "no"], default="yes")
                break
            except ValueError as error:
                self.console.print(str(error),style=ERROR, markup=False )
                if self._ask("Try payment again?", choices=["yes", "no"], default="yes") == "no":
                    complete = "no"
                    break
        if complete == "no" :
            self.sales.cancel_sale()
            self.console.print("Sale cancelled.", style=WARNING)
            return
        summary = self.sales.complete_sale()
        self.finance.record_income(summary)
        self.pending_save.update({"products", "sales", "income"})
        if not self._save_changes():
            return False
        self.console.print(Panel(f"Sale #{summary['sale_id']} completed and saved\nChange: {change:.2f}", style=SUCCESS))





        


