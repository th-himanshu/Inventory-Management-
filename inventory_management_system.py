import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import hashlib
import os
import io
import sys

class User:
    def __init__(self, username, password_hash, is_admin=False):
        self.username = username
        self.password_hash = password_hash
        self.is_admin = is_admin

class InventoryManagementSystem:
    def __init__(self, db_name='inventory.db'):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.current_user = None

    def create_tables(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS inventory
                             (id INTEGER PRIMARY KEY,
                              name TEXT UNIQUE,
                              quantity INTEGER,
                              price REAL,
                              last_updated DATETIME)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users
                             (id INTEGER PRIMARY KEY,
                              username TEXT UNIQUE,
                              password_hash TEXT,
                              is_admin INTEGER)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS sales
                             (id INTEGER PRIMARY KEY,
                              item_name TEXT,
                              quantity INTEGER,
                              sale_date DATETIME)''')
        self.conn.commit()

    def add_item(self, name, quantity, price):
        try:
            self.cursor.execute("INSERT INTO inventory (name, quantity, price, last_updated) VALUES (?, ?, ?, ?)",
                                (name, quantity, price, datetime.now().isoformat()))
            self.conn.commit()
            print(f"{name} added to inventory.")
        except sqlite3.IntegrityError:
            print(f"{name} already exists. Use update_item to modify.")
            raise

    def remove_item(self, name):
        self.cursor.execute("DELETE FROM inventory WHERE name=?", (name,))
        if self.cursor.rowcount > 0:
            self.conn.commit()
            print(f"{name} removed from inventory.")
        else:
            print(f"{name} not found in inventory.")

    def update_item(self, name, quantity=None, price=None):
        update_fields = []
        values = []
        if quantity is not None:
            update_fields.append("quantity = ?")
            values.append(quantity)
        if price is not None:
            update_fields.append("price = ?")
            values.append(price)
        if update_fields:
            update_fields.append("last_updated = ?")
            values.append(datetime.now().isoformat())
            values.append(name)
            query = f"UPDATE inventory SET {', '.join(update_fields)} WHERE name = ?"
            self.cursor.execute(query, values)
            if self.cursor.rowcount > 0:
                self.conn.commit()
                print(f"{name} updated.")
            else:
                print(f"{name} not found in inventory.")
        else:
            print("No updates provided.")

    def display_inventory(self):
        self.cursor.execute("SELECT name, quantity, price, last_updated FROM inventory")
        items = self.cursor.fetchall()
        if items:
            print("\nCurrent Inventory:")
            for item in items:
                print(f"{item[0]}: Quantity: {item[1]}, Price: ${item[2]:.2f}, Last Updated: {item[3]}")
        else:
            print("Inventory is empty.")

    def generate_report(self):
        self.cursor.execute("SELECT SUM(quantity), SUM(quantity * price) FROM inventory")
        total_items, total_value = self.cursor.fetchone()
        print("\nInventory Report:")
        print(f"Total number of items: {total_items or 0}")
        print(f"Total inventory value: ${total_value or 0:.2f}")

    def low_stock_alert(self, threshold=10):
        self.cursor.execute("SELECT name, quantity FROM inventory WHERE quantity <= ?", (threshold,))
        low_stock_items = self.cursor.fetchall()
        if low_stock_items:
            print("\nLow Stock Alert:")
            for item in low_stock_items:
                print(f"{item[0]}: Only {item[1]} left in stock")
        else:
            print("No items are low in stock.")

    def record_sale(self, item_name, quantity):
        self.cursor.execute("UPDATE inventory SET quantity = quantity - ? WHERE name = ?", (quantity, item_name))
        if self.cursor.rowcount > 0:
            self.cursor.execute("INSERT INTO sales (item_name, quantity, sale_date) VALUES (?, ?, ?)",
                                (item_name, quantity, datetime.now().isoformat()))
            self.conn.commit()
            print(f"Sale recorded: {quantity} {item_name}")
        else:
            print(f"Error: {item_name} not found or insufficient quantity")

    def sales_prediction(self, item_name, days=30):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        self.cursor.execute("""
            SELECT DATE(sale_date) as date, SUM(quantity) as total_quantity
            FROM sales
            WHERE item_name = ? AND sale_date BETWEEN ? AND ?
            GROUP BY DATE(sale_date)
            ORDER BY date
        """, (item_name, start_date.isoformat(), end_date.isoformat()))
        sales_data = self.cursor.fetchall()
        
        if len(sales_data) < 2:
            return "Insufficient data for prediction"

        df = pd.DataFrame(sales_data, columns=['date', 'quantity'])
        df['date'] = pd.to_datetime(df['date'])
        df['days'] = (df['date'] - df['date'].min()).dt.days

        X = df[['days']]
        y = df['quantity']

        model = LinearRegression()
        model.fit(X, y)

        next_day = df['days'].max() + 1
        predicted_quantity = model.predict([[next_day]])[0]

        return f"Predicted sales for {item_name} tomorrow: {predicted_quantity:.2f} units"

    def export_to_csv(self, filename):
        df = pd.read_sql_query("SELECT * from inventory", self.conn)
        df.to_csv(filename, index=False)
        print(f"Inventory exported to {filename}")

    def export_to_excel(self, filename):
        df = pd.read_sql_query("SELECT * from inventory", self.conn)
        df.to_excel(filename, index=False)
        print(f"Inventory exported to {filename}")

    def add_user(self, username, password, is_admin=False):
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        try:
            self.cursor.execute("INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)",
                                (username, password_hash, int(is_admin)))
            self.conn.commit()
            print(f"User {username} added successfully")
        except sqlite3.IntegrityError:
            print(f"User {username} already exists")

    def is_admin(self):
        return self.current_user and self.current_user.is_admin

    def authenticate_user(self, username, password):
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        self.cursor.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, password_hash))
        user_data = self.cursor.fetchone()
        if user_data:
            self.current_user = User(user_data[1], user_data[2], bool(user_data[3]))
            return True
        return False

    def logout(self):
        self.current_user = None

class InventoryGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Inventory Management System")
        self.ims = InventoryManagementSystem()

        self.login_frame = ttk.Frame(self.master, padding="10")
        self.login_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.create_login_widgets()

        self.main_frame = ttk.Frame(self.master, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.create_main_widgets()

        self.show_login()

    def create_login_widgets(self):
        ttk.Label(self.login_frame, text="Username:").grid(column=0, row=0, sticky=tk.W)
        self.username_entry = ttk.Entry(self.login_frame)
        self.username_entry.grid(column=1, row=0)

        ttk.Label(self.login_frame, text="Password:").grid(column=0, row=1, sticky=tk.W)
        self.password_entry = ttk.Entry(self.login_frame, show="*")
        self.password_entry.grid(column=1, row=1)

        ttk.Button(self.login_frame, text="Login", command=self.login).grid(column=1, row=2)

    def create_main_widgets(self):
        self.tree = ttk.Treeview(self.main_frame, columns=('Name', 'Quantity', 'Price'), show='headings')
        self.tree.heading('Name', text='Name')
        self.tree.heading('Quantity', text='Quantity')
        self.tree.heading('Price', text='Price')
        self.tree.grid(column=0, row=0, columnspan=3)

        ttk.Button(self.main_frame, text="Add Item", command=self.add_item_window).grid(column=0, row=1)
        ttk.Button(self.main_frame, text="Update Item", command=self.update_item_window).grid(column=1, row=1)
        ttk.Button(self.main_frame, text="Remove Item", command=self.remove_item).grid(column=2, row=1)
        ttk.Button(self.main_frame, text="Generate Report", command=self.generate_report).grid(column=0, row=2)
        ttk.Button(self.main_frame, text="Low Stock Alert", command=self.low_stock_alert).grid(column=1, row=2)
        ttk.Button(self.main_frame, text="Sales Prediction", command=self.sales_prediction_window).grid(column=2, row=2)
        ttk.Button(self.main_frame, text="Export to CSV", command=self.export_to_csv).grid(column=0, row=3)
        ttk.Button(self.main_frame, text="Export to Excel", command=self.export_to_excel).grid(column=1, row=3)
        ttk.Button(self.main_frame, text="Logout", command=self.logout).grid(column=2, row=3)

    def show_login(self):
        self.main_frame.grid_remove()
        self.login_frame.grid()

    def show_main(self):
        self.login_frame.grid_remove()
        self.main_frame.grid()
        self.refresh_inventory()

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if self.ims.authenticate_user(username, password):
            self.show_main()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password")

    def logout(self):
        self.ims.logout()
        self.show_login()

    def refresh_inventory(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.ims.cursor.execute("SELECT name, quantity, price FROM inventory")
        for row in self.ims.cursor.fetchall():
            self.tree.insert('', 'end', values=row)

    def add_item_window(self):
        window = tk.Toplevel(self.master)
        window.title("Add Item")

        ttk.Label(window, text="Name:").grid(column=0, row=0)
        name_entry = ttk.Entry(window)
        name_entry.grid(column=1, row=0)

        ttk.Label(window, text="Quantity:").grid(column=0, row=1)
        quantity_entry = ttk.Entry(window)
        quantity_entry.grid(column=1, row=1)

        ttk.Label(window, text="Price:").grid(column=0, row=2)
        price_entry = ttk.Entry(window)
        price_entry.grid(column=1, row=2)

        ttk.Button(window, text="Add", command=lambda: self.add_item(name_entry.get(), quantity_entry.get(), price_entry.get(), window)).grid(column=1, row=3)

    def add_item(self, name, quantity, price, window):
        try:
            self.ims.add_item(name, int(quantity), float(price))
            self.refresh_inventory()
            window.destroy()
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity or price")
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Item already exists")

    def update_item_window(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "No item selected")
            return
        item = self.tree.item(selected[0])['values']
        
        window = tk.Toplevel(self.master)
        window.title("Update Item")

        ttk.Label(window, text="Name:").grid(column=0, row=0)
        name_entry = ttk.Entry(window)
        name_entry.insert(0, item[0])
        name_entry.config(state='readonly')
        name_entry.grid(column=1, row=0)

        ttk.Label(window, text="Quantity:").grid(column=0, row=1)
        quantity_entry = ttk.Entry(window)
        quantity_entry.insert(0, item[1])
        quantity_entry.grid(column=1, row=1)

        ttk.Label(window, text="Price:").grid(column=0, row=2)
        price_entry = ttk.Entry(window)
        price_entry.insert(0, item[2])
        price_entry.grid(column=1, row=2)

        ttk.Button(window, text="Update", command=lambda: self.update_item(item[0], quantity_entry.get(), price_entry.get(), window)).grid(column=1, row=3)

    def update_item(self, name, quantity, price, window):
        try:
            self.ims.update_item(name, int(quantity), float(price))
            self.refresh_inventory()
            window.destroy()
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity or price")

    def remove_item(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "No item selected")
            return
        item = self.tree.item(selected[0])['values']
        if messagebox.askyesno("Confirm", f"Are you sure you want to remove {item[0]}?"):
            self.ims.remove_item(item[0])
            self.refresh_inventory()

    def generate_report(self):
        report = io.StringIO()
        sys.stdout = report
        self.ims.generate_report()
        sys.stdout = sys.__stdout__
        messagebox.showinfo("Inventory Report", report.getvalue())

    def low_stock_alert(self):
        report = io.StringIO()
        sys.stdout = report
        self.ims.low_stock_alert()
        sys.stdout = sys.__stdout__
        messagebox.showinfo("Low Stock Alert", report.getvalue())

    def sales_prediction_window(self):
        window = tk.Toplevel(self.master)
        window.title("Sales Prediction")

        ttk.Label(window, text="Item Name:").grid(column=0, row=0)
        name_entry = ttk.Entry(window)
        name_entry.grid(column=1, row=0)

        ttk.Label(window, text="Days of data:").grid(column=0, row=1)
        days_entry = ttk.Entry(window)
        days_entry.insert(0, "30")
        days_entry.grid(column=1, row=1)

        ttk.Button(window, text="Predict", command=lambda: self.predict_sales(name_entry.get(), days_entry.get(), window)).grid(column=1, row=2)

    def predict_sales(self, item_name, days, window):
        try:
            prediction = self.ims.sales_prediction(item_name, int(days))
            messagebox.showinfo("Sales Prediction", prediction)
            window.destroy()
        except ValueError:
            messagebox.showerror("Error", "Invalid number of days")

    def export_to_csv(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if filename:
            self.ims.export_to_csv(filename)
            messagebox.showinfo("Export Successful", f"Inventory exported to {filename}")

    def export_to_excel(self):
        filename = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if filename:
            self.ims.export_to_excel(filename)
            messagebox.showinfo("Export Successful", f"Inventory exported to {filename}")

def main():
    root = tk.Tk()
    InventoryGUI(root)
    meth = InventoryManagementSystem()
    # meth.add_user("HK", "123", True)
    root.mainloop()

if __name__ == "__main__":
    main()



