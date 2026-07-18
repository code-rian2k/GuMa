"""
Minimaler funktionaler Ersatz für tkinter, NUR für automatisierte Tests in
Umgebungen ohne Display/Tk (z.B. dieser Sandbox). Simuliert genug echtes
Verhalten (StringVar, Treeview mit Items/Selection, Text-Widget), um die
komplette App-Logik (nicht nur Syntax) durchzutesten - inkl. genau des Bugs,
der real aufgetreten ist (TclError bei selection_set auf nicht vorhandenem
Item). Wird NICHT mit an die Nutzerin ausgeliefert.
"""
import sys
import types


class TclError(Exception):
    pass


class _Base:
    def __init__(self, *a, **kw):
        self._kw = kw
        self._bound = {}

    def pack(self, *a, **kw): return self
    def grid(self, *a, **kw): return self
    def grid_columnconfigure(self, *a, **kw): return self
    def config(self, *a, **kw):
        self._kw.update(kw)
        return self
    def configure(self, *a, **kw): return self.config(*a, **kw)
    def bind(self, event=None, cb=None, *a, **kw):
        if event is not None:
            self._bound[event] = cb
    def heading(self, *a, **kw): return self
    def column(self, *a, **kw): return self
    def destroy(self): pass
    def __getattr__(self, name):
        def _noop(*a, **kw):
            return None
        return _noop


class Var:
    def __init__(self, value=""):
        self._value = value
        self._traces = []

    def get(self):
        return self._value

    def set(self, value):
        self._value = value
        for cb in list(self._traces):
            cb()

    def trace_add(self, mode, cb):
        self._traces.append(lambda: cb())


class Text(_Base):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._content = ""

    def insert(self, index, text):
        if index == "1.0":
            self._content = text + self._content
        else:
            self._content += text

    def delete(self, start, end=None):
        self._content = ""

    def get(self, start, end=None):
        return self._content


class Treeview(_Base):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._items = {}
        self._order = []
        self._selection = []

    def insert(self, parent, index, iid=None, values=None, **kw):
        iid = iid if iid is not None else str(len(self._items))
        self._items[iid] = values
        self._order.append(iid)
        return iid

    def delete(self, iid):
        if iid in self._items:
            del self._items[iid]
            self._order.remove(iid)
            if iid in self._selection:
                self._selection.remove(iid)

    def get_children(self, item=""):
        return list(self._order)

    def selection(self):
        return list(self._selection)

    def selection_set(self, iid):
        if iid not in self._items:
            raise TclError(f'Item "{iid}" not found in treeview')
        self._selection = [iid]

    def focus(self, iid=None):
        if iid is None:
            return self._selection[0] if self._selection else ""
        if iid not in self._items:
            raise TclError(f'Item "{iid}" not found in treeview')

    def item(self, iid, option=None):
        werte = {"values": self._items.get(iid)}
        if option:
            return werte.get(option)
        return werte


class Notebook(_Base):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.tabs_liste = []

    def add(self, child, text=""):
        self.tabs_liste.append((child, text))

    def select(self, index=None):
        pass


def _make_widget_class():
    return type("Widget", (_Base,), {})


def build_stub_tkinter():
    tk_mod = types.ModuleType("tkinter")
    ttk_mod = types.ModuleType("tkinter.ttk")
    messagebox_mod = types.ModuleType("tkinter.messagebox")
    filedialog_mod = types.ModuleType("tkinter.filedialog")
    simpledialog_mod = types.ModuleType("tkinter.simpledialog")

    Widget = _make_widget_class()

    class Tk(_Base):
        def title(self, t=None): self._title = t
        def geometry(self, g=None): pass
        def mainloop(self): pass

    class Toplevel(_Base):
        def title(self, t=None): self._title = t
        def geometry(self, g=None): pass
        def grab_set(self): pass

    class Menu(_Base):
        def add_command(self, *a, **kw): pass
        def add_cascade(self, *a, **kw): pass
        def add_separator(self, *a, **kw): pass

    tk_mod.Tk = Tk
    tk_mod.Toplevel = Toplevel
    tk_mod.Menu = Menu
    tk_mod.StringVar = Var
    tk_mod.Text = Text
    tk_mod.Canvas = Widget
    tk_mod.Frame = Widget
    tk_mod.Label = Widget
    tk_mod.TclError = TclError

    for name in ["Frame", "Label", "Entry", "Button", "Combobox", "Separator",
                 "LabelFrame", "PanedWindow", "Scrollbar"]:
        setattr(ttk_mod, name, Widget)
    ttk_mod.Treeview = Treeview
    ttk_mod.Notebook = Notebook

    class Style:
        def __init__(self, *a, **kw): pass
        def theme_use(self, *a, **kw): pass
        def theme_names(self): return ["clam", "default"]
        def configure(self, *a, **kw): pass
        def map(self, *a, **kw): pass

    ttk_mod.Style = Style

    calls = {"showinfo": [], "showwarning": [], "showerror": [], "askyesno": []}

    def showinfo(title, message, **kw):
        calls["showinfo"].append((title, message))

    def showwarning(title, message, **kw):
        calls["showwarning"].append((title, message))

    def showerror(title, message, **kw):
        calls["showerror"].append((title, message))

    ANTWORT_JA_NEIN = {"value": True}

    def askyesno(title, message, **kw):
        calls["askyesno"].append((title, message))
        return ANTWORT_JA_NEIN["value"]

    messagebox_mod.showinfo = showinfo
    messagebox_mod.showwarning = showwarning
    messagebox_mod.showerror = showerror
    messagebox_mod.askyesno = askyesno
    messagebox_mod._calls = calls
    messagebox_mod._antwort_ja_nein = ANTWORT_JA_NEIN

    dialog_werte = {"asksaveasfilename": "", "askopenfilenames": (), "askdirectory": ""}

    filedialog_mod.asksaveasfilename = lambda **kw: dialog_werte["asksaveasfilename"]
    filedialog_mod.askopenfilenames = lambda **kw: dialog_werte["askopenfilenames"]
    filedialog_mod.askdirectory = lambda **kw: dialog_werte["askdirectory"]
    filedialog_mod._werte = dialog_werte

    simpledialog_mod.askstring = lambda *a, **kw: None

    tk_mod.ttk = ttk_mod
    tk_mod.messagebox = messagebox_mod
    tk_mod.filedialog = filedialog_mod
    tk_mod.simpledialog = simpledialog_mod

    sys.modules["tkinter"] = tk_mod
    sys.modules["tkinter.ttk"] = ttk_mod
    sys.modules["tkinter.messagebox"] = messagebox_mod
    sys.modules["tkinter.filedialog"] = filedialog_mod
    sys.modules["tkinter.simpledialog"] = simpledialog_mod

    return tk_mod, ttk_mod, messagebox_mod, filedialog_mod, simpledialog_mod
