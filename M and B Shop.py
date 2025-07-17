import tkinter as tk
from tkinter import messagebox
import sqlite3
from datetime import datetime
import urllib.parse
import webbrowser
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# =================== Database Setup ===================
conn = sqlite3.connect('grocery_shop.db')
c = conn.cursor()

# Create tables
c.execute('''CREATE TABLE IF NOT EXISTS commodities (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    quantity INTEGER
)''')

c.execute('''CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY,
    name TEXT,
    quantity_sold INTEGER,
    price_per_unit REAL,
    total_price REAL,
    date TEXT
)''')

conn.commit()

# =================== Helper Functions ===================
def add_commodity():
    name = entry_name_in.get()
    qty = entry_qty_in.get()
    price = entry_price_in.get()

    if not name or not qty.isdigit():
        messagebox.showerror("Error", "Enter valid commodity and quantity.")
        return

    qty = int(qty)

    if price and price.replace('.', '', 1).isdigit():
        price = float(price)
        c.execute("INSERT INTO sales (name, quantity_sold, price_per_unit, total_price, date) VALUES (?, ?, ?, ?, ?)",
                  (name, 0, price, 0, datetime.now().strftime("%Y-%m-%d")))

    c.execute("SELECT quantity FROM commodities WHERE name=?", (name,))
    row = c.fetchone()
    if row:
        c.execute("UPDATE commodities SET quantity = quantity + ? WHERE name=?", (qty, name))
    else:
        c.execute("INSERT INTO commodities (name, quantity) VALUES (?, ?)", (name, qty))
    conn.commit()
    messagebox.showinfo("Success", f"Added {qty} of {name}")
    refresh_unsold()

def sell_commodity():
    name = entry_name_out.get()
    qty = entry_qty_out.get()
    price = entry_price_out.get()
    if not name or not qty.isdigit() or not price.replace('.', '', 1).isdigit():
        messagebox.showerror("Error", "Enter valid sale details.")
        return

    qty = int(qty)
    price = float(price)
    total = qty * price
    today = datetime.now().strftime("%Y-%m-%d")

    c.execute("SELECT quantity FROM commodities WHERE name=?", (name,))
    row = c.fetchone()
    if not row or row[0] < qty:
        messagebox.showerror("Error", "Not enough stock or item not found.")
        return

    c.execute("UPDATE commodities SET quantity = quantity - ? WHERE name=?", (qty, name))
    c.execute("INSERT INTO sales (name, quantity_sold, price_per_unit, total_price, date) VALUES (?, ?, ?, ?, ?)",
              (name, qty, price, total, today))
    conn.commit()
    messagebox.showinfo("Success", f"Sold {qty} of {name} for {total}")
    refresh_unsold()

def refresh_unsold():
    text_unsold.delete(1.0, tk.END)
    c.execute("SELECT * FROM commodities")
    items = c.fetchall()
    if not items:
        text_unsold.insert(tk.END, "No commodities in stock.\n")
    else:
        text_unsold.insert(tk.END, "Name\tQuantity\n")
        for item in items:
            text_unsold.insert(tk.END, f"{item[1]}\t{item[2]}\n")

def show_progress():
    text_progress.delete(1.0, tk.END)
    c.execute("SELECT date FROM sales GROUP BY date ORDER BY date DESC")
    dates = c.fetchall()

    if not dates:
        text_progress.insert(tk.END, "No sales data available.\n")
        return

    for date_row in dates:
        sale_date = date_row[0]
        text_progress.insert(tk.END, f"\nProgress for {sale_date}\n")
        text_progress.insert(tk.END, "Item\tSold\tTotal\n")
        c.execute(
            "SELECT name, SUM(quantity_sold), SUM(total_price) FROM sales WHERE date=? AND quantity_sold > 0 GROUP BY name",
            (sale_date,))
        rows = c.fetchall()
        for row in rows:
            text_progress.insert(tk.END, f"{row[0]}\t{row[1]}\t{row[2]:.2f}\n")

def search_commodity(name):
    if not name:
        messagebox.showerror("Error", "Enter a commodity name to search.")
        return

    c.execute("SELECT quantity FROM commodities WHERE name=?", (name,))
    stock_result = c.fetchone()

    c.execute("SELECT SUM(quantity_sold) FROM sales WHERE name=? AND quantity_sold > 0", (name,))
    sold_result = c.fetchone()

    if stock_result:
        stock_qty = stock_result[0]
        sold_qty = sold_result[0] if sold_result[0] else 0
        messagebox.showinfo("Search Result",
                            f"Commodity: {name}\n"
                            f"Quantity in Stock: {stock_qty}\n"
                            f"Total Quantity Sold: {sold_qty}")
    else:
        messagebox.showinfo("Not Found", f"{name} not found in inventory.")

def send_report_whatsapp():
    unsold_text = text_unsold.get(1.0, tk.END).strip()
    progress_text = text_progress.get(1.0, tk.END).strip()
    combined_report = f"📋 M & B Shop Report\n\nUnsold Commodities:\n{unsold_text}\n\nDaily Sales Progress:\n{progress_text}"
    encoded_message = urllib.parse.quote(combined_report)
    whatsapp_url = f"https://wa.me/?text={encoded_message}"
    webbrowser.open(whatsapp_url)

def clear_recent_report():
    def perform_clear():
        password = entry_password.get()
        correct_password = "1234"  # Change this password as needed

        if password != correct_password:
            messagebox.showerror("Access Denied", "Incorrect password. Cannot clear report.")
            popup.destroy()
            return

        c.execute("SELECT MAX(date) FROM sales")
        recent_date = c.fetchone()[0]

        if recent_date:
            c.execute("DELETE FROM sales WHERE date=?", (recent_date,))
            conn.commit()
            messagebox.showinfo("Success", f"Cleared sales report for {recent_date}.")
            refresh_unsold()
            show_progress()
        else:
            messagebox.showinfo("No Data", "No reports found to clear.")

        popup.destroy()

    popup = ttk.Toplevel(root)
    popup.title("Confirm Password")
    ttk.Label(popup, text="Enter Password to Clear Recent Report:", style="TLabel").pack(padx=20, pady=10)
    entry_password = ttk.Entry(popup, show="*", style="TEntry")
    entry_password.pack(padx=20, pady=10)
    ttk.Button(popup, text="Confirm", command=perform_clear, style="primary.TButton").pack(pady=10)

# =================== GUI Setup ===================
# Initialize ttkbootstrap with the 'flatly' theme
root = ttk.Window(themename="flatly")
root.title("🛒 M & B Shop Tracker")
root.state('zoomed')

# Configure custom styles
style = ttk.Style()
style.configure("TLabel", font=("Helvetica", 12))
style.configure("TEntry", font=("Helvetica", 12))
style.configure("primary.TButton", font=("Helvetica", 12, "bold"))
style.configure("success.TButton", font=("Helvetica", 12, "bold"), background="#25D366", foreground="white")
style.configure("danger.TButton", font=("Helvetica", 12, "bold"), background="red", foreground="white")

# Incoming Section
frame_in = ttk.LabelFrame(root, text="Incoming Commodities", padding=10, style="success.TLabelframe")
frame_in.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
frame_in.configure(bootstyle="success")  # Lightgreen equivalent

ttk.Label(frame_in, text="Commodity Name:", style="TLabel").grid(row=0, column=0, pady=2, sticky="w")
entry_name_in = ttk.Entry(frame_in, style="TEntry")
entry_name_in.grid(row=0, column=1, pady=2, sticky="ew")

ttk.Label(frame_in, text="Quantity:", style="TLabel").grid(row=1, column=0, pady=2, sticky="w")
entry_qty_in = ttk.Entry(frame_in, style="TEntry")
entry_qty_in.grid(row=1, column=1, pady=2, sticky="ew")

ttk.Label(frame_in, text="Order Price (Optional):", style="TLabel").grid(row=2, column=0, pady=2, sticky="w")
entry_price_in = ttk.Entry(frame_in, style="TEntry")
entry_price_in.grid(row=2, column=1, pady=2, sticky="ew")

ttk.Button(frame_in, text="Add Commodity", command=add_commodity, style="primary.TButton").grid(row=3, column=0, columnspan=2, pady=5, sticky="nsew")

# Outgoing Section
frame_out = ttk.LabelFrame(root, text="Outgoing Commodities (Sales)", padding=10, style="warning.TLabelframe")
frame_out.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
frame_out.configure(bootstyle="warning")  # Lightyellow equivalent

ttk.Label(frame_out, text="Commodity Name:", style="TLabel").grid(row=0, column=0, pady=2, sticky="w")
entry_name_out = ttk.Entry(frame_out, style="TEntry")
entry_name_out.grid(row=0, column=1, pady=2, sticky="ew")

ttk.Label(frame_out, text="Quantity Sold:", style="TLabel").grid(row=1, column=0, pady=2, sticky="w")
entry_qty_out = ttk.Entry(frame_out, style="TEntry")
entry_qty_out.grid(row=1, column=1, pady=2, sticky="ew")

ttk.Label(frame_out, text="Price Per Unit:", style="TLabel").grid(row=2, column=0, pady=2, sticky="w")
entry_price_out = ttk.Entry(frame_out, style="TEntry")
entry_price_out.grid(row=2, column=1, pady=2, sticky="ew")

ttk.Button(frame_out, text="Sell Commodity", command=sell_commodity, style="primary.TButton").grid(row=3, column=0, columnspan=2, pady=5, sticky="nsew")

# Reports Section
frame_report = ttk.LabelFrame(root, text="Reports", padding=10)
frame_report.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")

ttk.Label(frame_report, text="Unsold Commodities:", style="TLabel").grid(row=0, column=0, pady=2, sticky="w")
text_unsold = tk.Text(frame_report, height=10, width=30, font=("Helvetica", 12))
text_unsold.grid(row=1, column=0, padx=5, pady=2, sticky="nsew")

ttk.Label(frame_report, text="Daily Progress:", style="TLabel").grid(row=0, column=1, pady=2, sticky="w")
text_progress = tk.Text(frame_report, height=10, width=30, font=("Helvetica", 12))
text_progress.grid(row=1, column=1, padx=5, pady=2, sticky="nsew")

# Buttons Section
frame_buttons = ttk.Frame(root)
frame_buttons.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

ttk.Button(frame_buttons, text="Refresh Report", command=lambda: [refresh_unsold(), show_progress()], style="primary.TButton").grid(row=0, column=0, padx=5, pady=5)
ttk.Button(frame_buttons, text="Send Report via WhatsApp", command=send_report_whatsapp, style="success.TButton").grid(row=0, column=1, padx=5, pady=5)

ttk.Label(frame_buttons, text="Enter Name to Search:", style="TLabel").grid(row=1, column=0, pady=2, sticky="e")
entry_search = ttk.Entry(frame_buttons, style="TEntry")
entry_search.grid(row=1, column=1, pady=2, sticky="w")

ttk.Button(frame_buttons, text="Search Commodity", command=lambda: search_commodity(entry_search.get()), style="primary.TButton").grid(row=2, column=0, columnspan=2, pady=5, sticky="ew")

ttk.Button(frame_buttons, text="Clear Recent Report", command=clear_recent_report, style="danger.TButton").grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")

# Grid Configuration
root.grid_rowconfigure(0, weight=1)
root.grid_rowconfigure(1, weight=2)
root.grid_rowconfigure(2, weight=1)
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)

frame_report.grid_rowconfigure(1, weight=1)
frame_report.grid_columnconfigure(0, weight=1)
frame_report.grid_columnconfigure(1, weight=1)

frame_buttons.grid_columnconfigure(0, weight=1)
frame_buttons.grid_columnconfigure(1, weight=1)

# Initial Display
refresh_unsold()
show_progress()

root.mainloop()