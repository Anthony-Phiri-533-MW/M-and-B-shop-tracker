import tkinter as tk
from tkinter import messagebox
import sqlite3
from datetime import datetime
import urllib.parse
import webbrowser

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

    popup = tk.Toplevel(root)
    popup.title("Confirm Password")
    tk.Label(popup, text="Enter Password to Clear Recent Report:").pack(padx=10, pady=5)
    entry_password = tk.Entry(popup, show="*")
    entry_password.pack(padx=10, pady=5)
    tk.Button(popup, text="Confirm", command=perform_clear).pack(pady=10)


# =================== GUI Setup ===================
root = tk.Tk()
root.title("🛒 M & B Shop Tracker")
root.state('zoomed')

# Incoming Section
frame_in = tk.LabelFrame(root, text="Incoming Commodities", padx=10, pady=10, bg='lightgreen')
frame_in.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

tk.Label(frame_in, text="Commodity Name:").grid(row=0, column=0)
entry_name_in = tk.Entry(frame_in)
entry_name_in.grid(row=0, column=1)

tk.Label(frame_in, text="Quantity:").grid(row=1, column=0)
entry_qty_in = tk.Entry(frame_in)
entry_qty_in.grid(row=1, column=1)

tk.Label(frame_in, text="Order Price (Optional):").grid(row=2, column=0)
entry_price_in = tk.Entry(frame_in)
entry_price_in.grid(row=2, column=1)

tk.Button(frame_in, text="Add Commodity", command=add_commodity).grid(row=3, column=0, columnspan=2, pady=5)

# Outgoing Section
frame_out = tk.LabelFrame(root, text="Outgoing Commodities (Sales)", padx=10, pady=10, bg='lightyellow')
frame_out.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

tk.Label(frame_out, text="Commodity Name:").grid(row=0, column=0)
entry_name_out = tk.Entry(frame_out)
entry_name_out.grid(row=0, column=1)

tk.Label(frame_out, text="Quantity Sold:").grid(row=1, column=0)
entry_qty_out = tk.Entry(frame_out)
entry_qty_out.grid(row=1, column=1)

tk.Label(frame_out, text="Price Per Unit:").grid(row=2, column=0)
entry_price_out = tk.Entry(frame_out)
entry_price_out.grid(row=2, column=1)

tk.Button(frame_out, text="Sell Commodity", command=sell_commodity).grid(row=3, column=0, columnspan=2, pady=5)

# Reports Section
frame_report = tk.LabelFrame(root, text="Reports", padx=10, pady=10)
frame_report.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

tk.Label(frame_report, text="Unsold Commodities:").grid(row=0, column=0)
text_unsold = tk.Text(frame_report, height=15, width=60)
text_unsold.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

tk.Label(frame_report, text="Daily Progress:").grid(row=0, column=1)
text_progress = tk.Text(frame_report, height=15, width=60)
text_progress.grid(row=1, column=1, padx=10, pady=5, sticky="nsew")

btn_refresh = tk.Button(frame_report, text="Refresh Report", command=lambda: [refresh_unsold(), show_progress()])
btn_refresh.grid(row=2, column=0, columnspan=2, pady=10)

btn_whatsapp = tk.Button(frame_report, text="Send Report via WhatsApp", command=send_report_whatsapp, bg="#25D366",
                         fg="white", font=("Arial", 12, "bold"))
btn_whatsapp.grid(row=3, column=0, columnspan=2, pady=10, sticky="ew")

tk.Label(frame_report, text="Enter Name to Search:").grid(row=4, column=0, sticky='e')
entry_search = tk.Entry(frame_report)
entry_search.grid(row=4, column=1, sticky='w')

tk.Button(frame_report, text="Search Commodity", command=lambda: search_commodity(entry_search.get())).grid(row=5,
                                                                                                            column=0,
                                                                                                            columnspan=2,
                                                                                                            pady=10)

# Clear Recent Report Button
tk.Button(frame_report, text="Clear Recent Report", command=clear_recent_report, bg="red", fg="white").grid(row=6,
                                                                                                            column=0,
                                                                                                            columnspan=2,
                                                                                                            pady=10)

# Grid Configuration
root.grid_rowconfigure(0, weight=1)
root.grid_rowconfigure(1, weight=1)
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)

frame_report.grid_rowconfigure(1, weight=1)
frame_report.grid_columnconfigure(0, weight=1)
frame_report.grid_columnconfigure(1, weight=1)

# Initial Display
refresh_unsold()
show_progress()

root.mainloop()
