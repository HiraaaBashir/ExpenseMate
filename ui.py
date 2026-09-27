"""
Tkinter UI for ExpenseMate.

Talks to the backend only through the service classes (category_service,
budget_service, transaction_service, csv_service) - no direct SQL here.
Analytics is computed here in the UI from data the services already return;
there's no dedicated analytics module in the backend.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date
from collections import defaultdict

from category_service import CategoryService
from budget_service import BudgetService
from transaction_service import TransactionService
from csv_service import CSVService
from exceptions import ValidationError, DuplicateBudgetError
from category_repo import CategoryNotFoundError
from transaction_repo import TransactionNotFoundError
from theme import apply_theme, card, COLORS, FONT


def labeled_entry(parent, label, var, width=16, row=0, col=0, **grid_opts):
    wrap = ttk.Frame(parent, style="Card.TFrame")
    wrap.grid(row=row, column=col, padx=(0, 16), pady=(0, 4), sticky="w", **grid_opts)
    ttk.Label(wrap, text=label, style="FieldLabel.TLabel").pack(anchor="w")
    entry = ttk.Entry(wrap, textvariable=var, width=width)
    entry.pack(anchor="w", pady=(3, 0))
    return entry


def labeled_combo(parent, label, var, values, width=14, row=0, col=0, **grid_opts):
    wrap = ttk.Frame(parent, style="Card.TFrame")
    wrap.grid(row=row, column=col, padx=(0, 16), pady=(0, 4), sticky="w", **grid_opts)
    ttk.Label(wrap, text=label, style="FieldLabel.TLabel").pack(anchor="w")
    combo = ttk.Combobox(wrap, textvariable=var, values=values, width=width, state="readonly")
    combo.pack(anchor="w", pady=(3, 0))
    return combo


class ExpenseMateUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ExpenseMate")
        self.geometry("1000x640")
        self.minsize(880, 560)
        apply_theme(self)

        self.category_service = CategoryService()
        self.budget_service = BudgetService()
        self.transaction_service = TransactionService(self.budget_service)
        self.csv_service = CSVService(self.transaction_service)

        self.category_map = {}  # category name -> category_id

        self._build_layout()
        self._show_view("transactions")

    # ---------------------------------------------------------------
    # Shell: sidebar + content switcher
    # ---------------------------------------------------------------

    def _build_layout(self):
        root = ttk.Frame(self, style="Content.TFrame")
        root.pack(fill="both", expand=True)

        sidebar = ttk.Frame(root, style="Sidebar.TFrame", width=210)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ttk.Label(sidebar, text="ExpenseMate", style="SidebarTitle.TLabel").pack(anchor="w", padx=20, pady=(24, 2))
        ttk.Label(sidebar, text="Personal Expense Manager", style="SidebarSub.TLabel").pack(
            anchor="w", padx=20, pady=(0, 24))

        self._nav_buttons = {}
        for key, label in [("transactions", "Transactions"), ("budgets", "Budgets"),
                            ("categories", "Categories"), ("analytics", "Analytics")]:
            btn = ttk.Button(sidebar, text=label, style="Nav.TButton", command=lambda k=key: self._show_view(k))
            btn.pack(fill="x")
            self._nav_buttons[key] = btn

        self.content = ttk.Frame(root, style="Content.TFrame", padding=28)
        self.content.pack(side="left", fill="both", expand=True)

        self._views = {
            "transactions": self._build_transactions_view(self.content),
            "budgets": self._build_budgets_view(self.content),
            "categories": self._build_categories_view(self.content),
            "analytics": self._build_analytics_view(self.content),
        }
        for v in self._views.values():
            v.place(in_=self.content, x=0, y=0, relwidth=1, relheight=1)

        self.refresh_categories()
        self.refresh_transactions()
        self.refresh_budgets()

    def _show_view(self, key):
        for k, btn in self._nav_buttons.items():
            btn.configure(style="NavActive.TButton" if k == key else "Nav.TButton")
        self._views[key].tkraise()
        if key == "analytics":
            self._refresh_analytics()

    # ---------------------------------------------------------------
    # Categories view
    # ---------------------------------------------------------------

    def _build_categories_view(self, parent):
        outer, inner = card(parent)
        ttk.Label(inner, text="Categories", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(inner, text="Create the categories you'll use for transactions and budgets.",
                  style="SubHeading.TLabel").pack(anchor="w", pady=(0, 18))

        form = ttk.Frame(inner, style="Card.TFrame")
        form.pack(fill="x", pady=(0, 14))
        self.category_name_var = tk.StringVar()
        labeled_entry(form, "Category name", self.category_name_var, width=22, row=0, col=0)
        btn_wrap = ttk.Frame(form, style="Card.TFrame")
        btn_wrap.grid(row=0, column=1, sticky="s", pady=(18, 4))
        ttk.Button(btn_wrap, text="+ Add Category", style="Accent.TButton", command=self.add_category).pack()

        tree_wrap = ttk.Frame(inner, style="Card.TFrame")
        tree_wrap.pack(fill="both", expand=True)
        self.category_tree = ttk.Treeview(tree_wrap, columns=("id", "name"), show="headings")
        self.category_tree.heading("id", text="ID")
        self.category_tree.heading("name", text="Name")
        self.category_tree.column("id", width=60, anchor="center")
        self.category_tree.column("name", width=250)
        self.category_tree.tag_configure("odd", background="#FAFBFD")
        self.category_tree.tag_configure("even", background="#FFFFFF")
        self.category_tree.pack(side="left", fill="both", expand=True)

        ttk.Button(inner, text="Delete Selected", style="Secondary.TButton",
                   command=self.delete_category).pack(anchor="w", pady=(10, 0))
        return outer

    def add_category(self):
        try:
            self.category_service.add_category(self.category_name_var.get())
            self.category_name_var.set("")
            self.refresh_categories()
        except ValidationError as e:
            messagebox.showerror("Error", str(e))

    def delete_category(self):
        selected = self.category_tree.selection()
        if not selected:
            return
        category_id = self.category_tree.item(selected[0])["values"][0]
        try:
            self.category_service.delete_category(category_id)
            self.refresh_categories()
        except CategoryNotFoundError as e:
            messagebox.showerror("Error", str(e))
        except Exception:
            messagebox.showerror(
                "Error", "This category can't be deleted - it still has transactions or a budget linked to it.")

    def refresh_categories(self):
        for row in self.category_tree.get_children():
            self.category_tree.delete(row)
        categories = self.category_service.get_all_categories()
        self.category_map = {c.category_name: c.category_id for c in categories}
        for i, c in enumerate(categories):
            self.category_tree.insert("", "end", tags=("even" if i % 2 == 0 else "odd",),
                                       values=(c.category_id, c.category_name))
        names = list(self.category_map.keys())
        self.transaction_category_combo["values"] = names
        self.budget_category_combo["values"] = names

    # ---------------------------------------------------------------
    # Transactions view
    # ---------------------------------------------------------------

    def _build_transactions_view(self, parent):
        outer, inner = card(parent)
        ttk.Label(inner, text="Transactions", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(inner, text="Add income or expenses and keep track of every entry.",
                  style="SubHeading.TLabel").pack(anchor="w", pady=(0, 18))

        form = ttk.Frame(inner, style="Card.TFrame")
        form.pack(fill="x", pady=(0, 6))

        self.amount_var = tk.StringVar()
        self.type_var = tk.StringVar(value="expense")
        self.transaction_category_var = tk.StringVar()
        self.date_var = tk.StringVar(value=date.today().isoformat())

        labeled_entry(form, "Amount", self.amount_var, width=10, row=0, col=0)
        labeled_combo(form, "Type", self.type_var, ["income", "expense"], width=9, row=0, col=1)
        self.transaction_category_combo = labeled_combo(
            form, "Category", self.transaction_category_var, [], width=14, row=0, col=2)
        labeled_entry(form, "Date", self.date_var, width=12, row=0, col=3)

        btn_wrap = ttk.Frame(form, style="Card.TFrame")
        btn_wrap.grid(row=0, column=4, sticky="s", pady=(18, 4))
        ttk.Button(btn_wrap, text="+ Add Transaction", style="Accent.TButton",
                   command=self.add_transaction).pack()

        self.budget_pulse = ttk.Label(inner, text="", style="SubHeading.TLabel")
        self.budget_pulse.pack(anchor="w", pady=(2, 14))

        io_row = ttk.Frame(inner, style="Card.TFrame")
        io_row.pack(fill="x", pady=(0, 12))
        ttk.Button(io_row, text="Import CSV", style="Secondary.TButton", command=self.import_csv).pack(side="left")
        ttk.Button(io_row, text="Export CSV", style="Secondary.TButton",
                   command=self.export_csv).pack(side="left", padx=8)

        columns = ("id", "date", "type", "category", "amount")
        tree_wrap = ttk.Frame(inner, style="Card.TFrame")
        tree_wrap.pack(fill="both", expand=True)
        self.transaction_tree = ttk.Treeview(tree_wrap, columns=columns, show="headings")
        widths = {"id": 50, "date": 100, "type": 90, "category": 150, "amount": 110}
        for col in columns:
            self.transaction_tree.heading(col, text=col.capitalize())
            self.transaction_tree.column(col, width=widths[col],
                                          anchor="center" if col != "category" else "w")
        self.transaction_tree.tag_configure("odd", background="#FAFBFD")
        self.transaction_tree.tag_configure("even", background="#FFFFFF")
        scroll = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.transaction_tree.yview)
        self.transaction_tree.configure(yscrollcommand=scroll.set)
        self.transaction_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="left", fill="y")

        ttk.Button(inner, text="Delete Selected", style="Secondary.TButton",
                   command=self.delete_transaction).pack(anchor="w", pady=(10, 0))
        return outer

    def add_transaction(self):
        category_name = self.transaction_category_var.get()
        if category_name not in self.category_map:
            messagebox.showerror("Error", "Please select a category first (add one in the Categories tab).")
            return
        try:
            amount = float(self.amount_var.get())
        except ValueError:
            messagebox.showerror("Error", "Amount must be a number.")
            return
        try:
            result = self.transaction_service.add_transaction(
                amount=amount, type=self.type_var.get(), date=self.date_var.get(),
                category_id=self.category_map[category_name],
            )
        except ValidationError as e:
            messagebox.showerror("Error", str(e))
            return

        self.amount_var.set("")
        self.refresh_transactions()
        self.refresh_budgets()
        self._show_budget_pulse(self.category_map[category_name], self.date_var.get()[:7])

        if result["alert_triggered"]:
            messagebox.showwarning(
                "Budget Alert", f"You've now spent {result['percent_spent']:.0f}% of this category's budget.")

    def _show_budget_pulse(self, category_id, month):
        status = self.budget_service.check_budget_status(category_id, month)
        if status["percent_spent"] is None:
            self.budget_pulse.configure(text="")
            return
        pct = status["percent_spent"]
        symbol = "\U0001F534" if pct >= 100 else "\U0001F7E0" if pct >= 80 else "\U0001F7E2"
        self.budget_pulse.configure(text=f"{symbol}  {pct:.0f}% of this category's budget used this month")

    def delete_transaction(self):
        selected = self.transaction_tree.selection()
        if not selected:
            return
        transaction_id = self.transaction_tree.item(selected[0])["values"][0]
        try:
            self.transaction_service.delete_transaction(transaction_id)
            self.refresh_transactions()
            self.refresh_budgets()
        except TransactionNotFoundError as e:
            messagebox.showerror("Error", str(e))

    def refresh_transactions(self):
        for row in self.transaction_tree.get_children():
            self.transaction_tree.delete(row)
        categories = {c.category_id: c.category_name for c in self.category_service.get_all_categories()}
        rows = sorted(self.transaction_service.get_all_transactions(), key=lambda t: t.date, reverse=True)
        for i, t in enumerate(rows):
            self.transaction_tree.insert(
                "", "end", tags=("even" if i % 2 == 0 else "odd",),
                values=(t.transaction_id, t.date, t.type, categories.get(t.category_id, "?"), f"{t.amount:.2f}"))

    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        result = self.csv_service.import_csv(path)
        self.refresh_transactions()
        self.refresh_budgets()
        message = f"Imported {result['imported']} transaction(s)."
        if result["errors"]:
            message += f"\n{len(result['errors'])} row(s) skipped:\n"
            message += "\n".join(f"Row {row}: {msg}" for row, msg in result["errors"][:10])
        messagebox.showinfo("Import Complete", message)

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        self.csv_service.export_csv(path)
        messagebox.showinfo("Export Complete", "Transactions exported successfully.")

    # ---------------------------------------------------------------
    # Budgets view
    # ---------------------------------------------------------------

    def _build_budgets_view(self, parent):
        outer, inner = card(parent)
        ttk.Label(inner, text="Budgets", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(inner, text="Set a monthly limit per category and watch it fill up.",
                  style="SubHeading.TLabel").pack(anchor="w", pady=(0, 18))

        form = ttk.Frame(inner, style="Card.TFrame")
        form.pack(fill="x", pady=(0, 20))
        self.budget_category_var = tk.StringVar()
        self.budget_month_var = tk.StringVar(value=date.today().strftime("%Y-%m"))
        self.budget_limit_var = tk.StringVar()

        self.budget_category_combo = labeled_combo(
            form, "Category", self.budget_category_var, [], width=14, row=0, col=0)
        labeled_entry(form, "Month", self.budget_month_var, width=10, row=0, col=1)
        labeled_entry(form, "Limit", self.budget_limit_var, width=10, row=0, col=2)
        btn_wrap = ttk.Frame(form, style="Card.TFrame")
        btn_wrap.grid(row=0, column=3, sticky="s", pady=(18, 4))
        ttk.Button(btn_wrap, text="Set Budget", style="Accent.TButton", command=self.set_budget).pack()

        columns = ("id", "category", "month", "limit", "spent")
        tree_wrap = ttk.Frame(inner, style="Card.TFrame")
        tree_wrap.pack(fill="both", expand=True)
        self.budget_tree = ttk.Treeview(tree_wrap, columns=columns, show="headings")
        headers = {"id": "ID", "category": "Category", "month": "Month", "limit": "Limit", "spent": "% Spent"}
        widths = {"id": 50, "category": 160, "month": 90, "limit": 100, "spent": 90}
        for col in columns:
            self.budget_tree.heading(col, text=headers[col])
            self.budget_tree.column(col, width=widths[col], anchor="center" if col != "category" else "w")
        self.budget_tree.tag_configure("odd", background="#FAFBFD")
        self.budget_tree.tag_configure("even", background="#FFFFFF")
        self.budget_tree.pack(side="left", fill="both", expand=True)
        return outer

    def set_budget(self):
        category_name = self.budget_category_var.get()
        if category_name not in self.category_map:
            messagebox.showerror("Error", "Please select a category first (add one in the Categories tab).")
            return
        try:
            limit_amount = float(self.budget_limit_var.get())
        except ValueError:
            messagebox.showerror("Error", "Limit must be a number.")
            return
        try:
            self.budget_service.set_budget(
                self.category_map[category_name], self.budget_month_var.get(), limit_amount)
            self.budget_limit_var.set("")
            self.refresh_budgets()
        except (ValidationError, DuplicateBudgetError) as e:
            messagebox.showerror("Error", str(e))

    def refresh_budgets(self):
        for row in self.budget_tree.get_children():
            self.budget_tree.delete(row)
        categories = {c.category_id: c.category_name for c in self.category_service.get_all_categories()}
        for i, b in enumerate(self.budget_service.get_all_budgets()):
            status = self.budget_service.check_budget_status(b.category_id, b.month)
            spent_display = f"{status['percent_spent']:.0f}%" if status["percent_spent"] is not None else "-"
            self.budget_tree.insert(
                "", "end", tags=("even" if i % 2 == 0 else "odd",),
                values=(b.budget_id, categories.get(b.category_id, "?"), b.month, f"{b.limit_amount:.2f}", spent_display))

    # ---------------------------------------------------------------
    # Analytics view (computed here in the UI, no backend analytics module)
    # ---------------------------------------------------------------

    def _build_analytics_view(self, parent):
        outer, inner = card(parent)
        ttk.Label(inner, text="Analytics", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(inner, text="See where your money goes each month.",
                  style="SubHeading.TLabel").pack(anchor="w", pady=(0, 18))

        form = ttk.Frame(inner, style="Card.TFrame")
        form.pack(fill="x", pady=(0, 14))
        self.analytics_month_var = tk.StringVar(value=date.today().strftime("%Y-%m"))
        labeled_entry(form, "Month", self.analytics_month_var, width=10, row=0, col=0)
        btn_wrap = ttk.Frame(form, style="Card.TFrame")
        btn_wrap.grid(row=0, column=1, sticky="s", pady=(18, 4))
        ttk.Button(btn_wrap, text="Refresh", style="Accent.TButton", command=self._refresh_analytics).pack()

        summary_row = ttk.Frame(inner, style="Card.TFrame")
        summary_row.pack(fill="x", pady=(0, 10))
        self.income_stat = self._stat_block(summary_row, "Income", 0)
        self.expense_stat = self._stat_block(summary_row, "Expense", 1)
        self.balance_stat = self._stat_block(summary_row, "Balance", 2)

        self.analytics_frame = ttk.Frame(inner, style="Card.TFrame")
        self.analytics_frame.pack(fill="both", expand=True)
        return outer

    def _stat_block(self, parent, label, col):
        wrap = ttk.Frame(parent, style="Card.TFrame")
        wrap.grid(row=0, column=col, padx=(0, 32), sticky="w")
        ttk.Label(wrap, text=label.upper(), style="FieldLabel.TLabel").pack(anchor="w")
        value = ttk.Label(wrap, text="0.00", style="Stat.TLabel")
        value.pack(anchor="w")
        return value

    def _refresh_analytics(self):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        for widget in self.analytics_frame.winfo_children():
            widget.destroy()

        month = self.analytics_month_var.get()
        categories = {c.category_id: c.category_name for c in self.category_service.get_all_categories()}
        transactions = [t for t in self.transaction_service.get_all_transactions() if t.date[:7] == month]

        income = sum(t.amount for t in transactions if t.type == "income")
        expense = sum(t.amount for t in transactions if t.type == "expense")
        self.income_stat.configure(text=f"{income:.2f}")
        self.expense_stat.configure(text=f"{expense:.2f}")
        self.balance_stat.configure(text=f"{income - expense:.2f}")

        breakdown = defaultdict(float)
        for t in transactions:
            if t.type == "expense":
                breakdown[categories.get(t.category_id, "?")] += t.amount

        palette = ["#16A085", "#4C6FFF", "#F39C12", "#E74C3C", "#8E44AD", "#2C3E50"]
        fig, ax = plt.subplots(figsize=(5, 3.6))
        fig.patch.set_facecolor(COLORS["card"])
        if breakdown:
            ax.pie(breakdown.values(), labels=breakdown.keys(), autopct="%1.0f%%",
                   colors=palette[: len(breakdown)], textprops={"fontsize": 9, "family": FONT})
        else:
            ax.text(0.5, 0.5, "No expenses recorded this month", ha="center", fontsize=10, color=COLORS["muted"])
            ax.axis("off")
        ax.set_title(f"Expenses by category \u2014 {month}", fontsize=11, color=COLORS["text"])

        canvas = FigureCanvasTkAgg(fig, master=self.analytics_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)


if __name__ == "__main__":
    app = ExpenseMateUI()
    app.mainloop()