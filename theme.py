"""Central place for ExpenseMate's visual style."""
import tkinter as tk
from tkinter import ttk

COLORS = {
    "bg": "#F4F6FB",
    "sidebar": "#1F2937",
    "sidebar_text": "#AEB8C9",
    "card": "#FFFFFF",
    "border": "#E3E7EF",
    "text": "#1F2937",
    "muted": "#6B7280",
    "accent": "#16A085",
    "accent_hover": "#128F76",
    "danger": "#E74C3C",
    "warning": "#F39C12",
}

FONT = "Segoe UI"


def apply_theme(root: tk.Tk) -> None:
    root.configure(bg=COLORS["bg"])
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", background=COLORS["bg"], foreground=COLORS["text"], font=(FONT, 10))

    style.configure("Sidebar.TFrame", background=COLORS["sidebar"])
    style.configure("Card.TFrame", background=COLORS["card"])
    style.configure("Content.TFrame", background=COLORS["bg"])

    style.configure("SidebarTitle.TLabel", background=COLORS["sidebar"], foreground="#FFFFFF",
                     font=(FONT, 15, "bold"))
    style.configure("SidebarSub.TLabel", background=COLORS["sidebar"], foreground=COLORS["sidebar_text"],
                     font=(FONT, 8))

    style.configure("Nav.TButton", background=COLORS["sidebar"], foreground=COLORS["sidebar_text"],
                     borderwidth=0, focuscolor=COLORS["sidebar"], font=(FONT, 11),
                     padding=(18, 12), anchor="w")
    style.map("Nav.TButton", background=[("active", "#2A3548")], foreground=[("active", "#FFFFFF")])

    style.configure("NavActive.TButton", background=COLORS["accent"], foreground="#FFFFFF",
                     borderwidth=0, focuscolor=COLORS["accent"], font=(FONT, 11, "bold"),
                     padding=(18, 12), anchor="w")
    style.map("NavActive.TButton", background=[("active", COLORS["accent"])])

    style.configure("Heading.TLabel", background=COLORS["card"], foreground=COLORS["text"],
                     font=(FONT, 16, "bold"))
    style.configure("SubHeading.TLabel", background=COLORS["card"], foreground=COLORS["muted"], font=(FONT, 9))
    style.configure("FieldLabel.TLabel", background=COLORS["card"], foreground=COLORS["muted"],
                     font=(FONT, 9, "bold"))
    style.configure("Card.TLabel", background=COLORS["card"], foreground=COLORS["text"], font=(FONT, 10))
    style.configure("Stat.TLabel", background=COLORS["card"], foreground=COLORS["text"], font=(FONT, 20, "bold"))

    style.configure("Accent.TButton", background=COLORS["accent"], foreground="#FFFFFF",
                     borderwidth=0, focuscolor=COLORS["accent"], font=(FONT, 10, "bold"), padding=(16, 9))
    style.map("Accent.TButton", background=[("active", COLORS["accent_hover"])])

    style.configure("Secondary.TButton", background="#EDF0F6", foreground=COLORS["text"],
                     borderwidth=0, focuscolor="#EDF0F6", font=(FONT, 10), padding=(14, 8))
    style.map("Secondary.TButton", background=[("active", COLORS["border"])])

    style.configure("TEntry", fieldbackground="#FFFFFF", bordercolor=COLORS["border"],
                     lightcolor=COLORS["border"], darkcolor=COLORS["border"], padding=7, relief="flat")
    style.configure("TCombobox", fieldbackground="#FFFFFF", padding=6)

    style.configure("Treeview", background="#FFFFFF", fieldbackground="#FFFFFF",
                     foreground=COLORS["text"], rowheight=30, borderwidth=0, font=(FONT, 10))
    style.configure("Treeview.Heading", background="#F0F2F7", foreground=COLORS["muted"],
                     font=(FONT, 9, "bold"), borderwidth=0, relief="flat", padding=(8, 6))
    style.map("Treeview", background=[("selected", COLORS["accent"])], foreground=[("selected", "#FFFFFF")])

    for name, color in [("Good", COLORS["accent"]), ("Warn", COLORS["warning"]), ("Danger", COLORS["danger"])]:
        style.configure(f"{name}.Horizontal.TProgressbar", troughcolor="#EDF0F6",
                         background=color, thickness=14, borderwidth=0)


def card(parent, padding=(24, 20)):
    outer = ttk.Frame(parent, style="Content.TFrame")
    inner = ttk.Frame(outer, style="Card.TFrame", padding=padding)
    inner.pack(fill="both", expand=True)
    return outer, inner