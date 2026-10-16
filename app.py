"""Task History Manager - save task titles with Kimi & Claude session IDs."""
import csv
import ctypes
import json
import subprocess
import sys
import uuid
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

# When bundled by PyInstaller, store data next to the exe so it persists
BASE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
DATA_FILE = BASE_DIR / "tasks.json"
NOTES_FILE = BASE_DIR / "notes.json"
SETTINGS_FILE = BASE_DIR / "settings.json"


def task_id_of(title):
    """Return the Task ID part of a stored title (text before first ': '), or None."""
    if ": " in title:
        tid = title.split(": ", 1)[0].strip()
        return tid or None
    return None


_SINGLE_INSTANCE_MUTEX = None


def acquire_single_instance():
    """Create a named mutex; return False if another instance is already running."""
    global _SINGLE_INSTANCE_MUTEX
    _SINGLE_INSTANCE_MUTEX = ctypes.windll.kernel32.CreateMutexW(None, False, "TaskHistoryManager_SingleInstance")
    return ctypes.windll.kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS


def focus_existing_window():
    """Bring the already-running instance's window to the foreground."""
    hwnd = ctypes.windll.user32.FindWindowW(None, "Task History Manager")
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        ctypes.windll.user32.SetForegroundWindow(hwnd)


def load_tasks():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return []


def save_tasks(tasks):
    DATA_FILE.write_text(json.dumps(tasks, indent=2, ensure_ascii=False), encoding="utf-8")


def load_notes():
    if NOTES_FILE.exists():
        notes = json.loads(NOTES_FILE.read_text(encoding="utf-8"))
        return [{"id": n.get("id") or uuid.uuid4().hex, "title": n.get("title", ""), "text": n.get("text", "")} for n in notes]
    return []


def save_notes(notes):
    NOTES_FILE.write_text(json.dumps(notes, indent=2, ensure_ascii=False), encoding="utf-8")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Task History Manager")
        self.tasks = load_tasks()
        self.notes = load_notes()
        self.load_settings()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        tasks_tab = ttk.Frame(self.notebook)
        self.notebook.add(tasks_tab, text="Tasks")
        notes_tab = ttk.Frame(self.notebook)
        self.notebook.add(notes_tab, text="Notes")

        # --- Input form ---
        form = ttk.LabelFrame(tasks_tab, text="Add Task", padding=8)
        form.pack(fill="x", padx=8, pady=8)

        ttk.Label(form, text="Task ID:").grid(row=0, column=0, sticky="w")
        self.tid_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.tid_var, width=20).grid(row=0, column=1, sticky="w", padx=4, pady=2)

        ttk.Label(form, text="Task Title:").grid(row=1, column=0, sticky="w")
        self.title_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.title_var, width=90).grid(row=1, column=1, columnspan=3, sticky="ew", padx=4, pady=2)

        ttk.Label(form, text="Kimi:").grid(row=2, column=0, sticky="w")
        self.kimi_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.kimi_var, width=90).grid(row=2, column=1, sticky="ew", padx=4, pady=2)
        ttk.Button(form, text="Copy", width=6, command=lambda: self.copy_var(self.kimi_var)).grid(row=2, column=2)
        ttk.Button(form, text="Run", width=6, command=lambda: self.run_cmd(self.kimi_var.get())).grid(row=2, column=3)

        ttk.Label(form, text="Claude:").grid(row=3, column=0, sticky="w")
        self.claude_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.claude_var, width=90).grid(row=3, column=1, sticky="ew", padx=4, pady=2)
        ttk.Button(form, text="Copy", width=6, command=lambda: self.copy_var(self.claude_var)).grid(row=3, column=2)
        ttk.Button(form, text="Run", width=6, command=lambda: self.run_cmd(self.claude_var.get())).grid(row=3, column=3)

        ttk.Button(form, text="Add / Update", command=self.add_task).grid(row=4, column=1, sticky="w", padx=4, pady=6)
        form.columnconfigure(1, weight=1)

        # --- Search ---
        search_bar = ttk.Frame(tasks_tab)
        search_bar.pack(fill="x", padx=8)
        self.status_var = tk.StringVar()
        ttk.Label(search_bar, textvariable=self.status_var).pack(side="left", padx=(0, 15))
        ttk.Label(search_bar, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh_list())
        ttk.Entry(search_bar, textvariable=self.search_var, width=40).pack(side="left", padx=4)
        ttk.Button(search_bar, text="Clear", width=6, command=self.clear_search).pack(side="left", padx=2)

        # --- Buttons (same row as search, right side) ---
        ttk.Button(search_bar, text="Import", command=self.import_tasks).pack(side="right", padx=2)
        ttk.Button(search_bar, text="Export", command=self.export_tasks).pack(side="right", padx=2)
        ttk.Separator(search_bar, orient="vertical").pack(side="right", fill="y", padx=8)
        ttk.Button(search_bar, text="Delete", command=self.delete_selected).pack(side="right", padx=(12, 2))
        ttk.Button(search_bar, text="Copy Claude", command=lambda: self.copy_selected("claude")).pack(side="right", padx=2)
        ttk.Button(search_bar, text="Copy Kimi", command=lambda: self.copy_selected("kimi")).pack(side="right", padx=2)

        # --- Task list ---
        cols = ("datetime", "title", "kimi", "claude")
        self.tree = ttk.Treeview(tasks_tab, columns=cols, show="headings", height=18, selectmode="extended")
        self.sort_col = "datetime"
        self.sort_reverse = True  # newest first by default
        for c in cols:
            self.tree.heading(c, text=self.heading_text(c), command=lambda col=c: self.sort_by(col))
        self.tree.column("datetime", width=150)
        self.tree.column("title", width=420)
        self.tree.column("kimi", width=280)
        self.tree.column("claude", width=280)
        sb = ttk.Scrollbar(tasks_tab, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        sb.pack(side="left", fill="y", pady=8)

        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.build_notes_tab(notes_tab)

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh_list()
        self.refresh_notes()

    # --- Settings: always open at the standard size ---
    def load_settings(self):
        self.geometry("1000x600")

    def on_close(self):
        self.destroy()

    # --- Notes tab ---
    def build_notes_tab(self, tab):
        # --- Note editor ---
        editor_frame = ttk.LabelFrame(tab, text="Note", padding=8)
        editor_frame.pack(fill="x", padx=8, pady=8)

        ttk.Label(editor_frame, text="Title (optional):").grid(row=0, column=0, sticky="w")
        self.note_title_var = tk.StringVar()
        ttk.Entry(editor_frame, textvariable=self.note_title_var, width=60).grid(row=0, column=1, sticky="ew", padx=4, pady=2)
        ttk.Button(editor_frame, text="Copy", width=6, command=self.copy_note_title).grid(row=0, column=2, padx=2)

        self.note_text = tk.Text(editor_frame, height=8, wrap="word")
        note_sb = ttk.Scrollbar(editor_frame, orient="vertical", command=self.note_text.yview)
        self.note_text.configure(yscrollcommand=note_sb.set)
        self.note_text.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        note_sb.grid(row=1, column=3, sticky="ns", pady=(4, 0))
        editor_frame.columnconfigure(1, weight=1)

        # --- Buttons ---
        btn_row = ttk.Frame(tab)
        btn_row.pack(fill="x", padx=8)
        ttk.Button(btn_row, text="Add / Update", command=self.add_note).pack(side="left", padx=2)
        ttk.Button(btn_row, text="Clear", width=8, command=self.clear_note_editor).pack(side="left", padx=2)
        ttk.Button(btn_row, text="Copy", width=8, command=self.copy_note).pack(side="left", padx=2)
        ttk.Button(btn_row, text="Delete", command=self.delete_note).pack(side="right", padx=2)

        # --- Notes list ---
        self.notes_tree = ttk.Treeview(tab, columns=("title", "preview"), show="headings", height=15, selectmode="browse")
        self.notes_tree.heading("title", text="Title")
        self.notes_tree.heading("preview", text="Note")
        self.notes_tree.column("title", width=180)
        self.notes_tree.column("preview", width=600)
        notes_sb = ttk.Scrollbar(tab, orient="vertical", command=self.notes_tree.yview)
        self.notes_tree.configure(yscrollcommand=notes_sb.set)
        self.notes_tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        notes_sb.pack(side="left", fill="y", pady=8)

        self.notes_tree.bind("<<TreeviewSelect>>", self.on_note_select)
        self.notes_tree.bind("<Double-1>", self.copy_selected_note)
        self._drag_iid = None
        self.notes_tree.bind("<Button-1>", self.on_note_drag_start)
        self.notes_tree.bind("<B1-Motion>", self.on_note_drag_motion)
        self.notes_tree.bind("<ButtonRelease-1>", self.on_note_drag_end)

    def note_editor_content(self):
        return self.note_text.get("1.0", "end-1c").strip()

    def clear_note_editor(self):
        self.note_text.delete("1.0", "end")
        self.note_title_var.set("")
        self.notes_tree.selection_remove(self.notes_tree.selection())

    def add_note(self):
        text = self.note_editor_content()
        if not text:
            messagebox.showwarning("Missing", "Note text is required.")
            return
        sel = self.notes_tree.selection()
        sel_id = sel[0] if sel else None
        # duplicate note text is not allowed (unless updating the same note)
        for n in self.notes:
            if n.get("text", "") == text and n.get("id") != sel_id:
                messagebox.showwarning("Duplicate Note", "A note with this exact text already exists.")
                return
        note = {"id": uuid.uuid4().hex, "title": self.note_title_var.get().strip(), "text": text}
        if sel:
            # update the selected note
            old_id = sel[0]
            for i, n in enumerate(self.notes):
                if n.get("id") == old_id:
                    self.notes[i] = note
                    break
        else:
            self.notes.append(note)
        save_notes(self.notes)
        self.clear_note_editor()
        self.refresh_notes()

    def on_note_select(self, _evt):
        sel = self.notes_tree.selection()
        if not sel:
            return
        for n in self.notes:
            if n.get("id") == sel[0]:
                self.note_title_var.set(n.get("title", ""))
                self.note_text.delete("1.0", "end")
                self.note_text.insert("1.0", n.get("text", ""))
                break

    def copy_note(self):
        text = self.note_editor_content()
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)

    def copy_note_title(self):
        title = self.note_title_var.get().strip()
        if not title:
            return
        self.clipboard_clear()
        self.clipboard_append(title)

    # --- drag & drop reordering ---
    def on_note_drag_start(self, evt):
        self._drag_iid = self.notes_tree.identify_row(evt.y) or None

    def on_note_drag_motion(self, evt):
        if not self._drag_iid:
            return
        target = self.notes_tree.identify_row(evt.y)
        if target and target != self._drag_iid:
            self.notes_tree.move(self._drag_iid, "", self.notes_tree.index(target))

    def on_note_drag_end(self, _evt):
        if not self._drag_iid:
            return
        order = self.notes_tree.get_children()
        by_id = {n.get("id"): n for n in self.notes}
        self.notes = [by_id[iid] for iid in order]
        save_notes(self.notes)
        self._drag_iid = None

    def copy_selected_note(self, _evt=None):
        sel = self.notes_tree.selection()
        if not sel:
            return
        for n in self.notes:
            if n.get("id") == sel[0]:
                self.clipboard_clear()
                self.clipboard_append(n.get("text", ""))
                break

    def delete_note(self):
        sel = self.notes_tree.selection()
        if not sel:
            return
        if messagebox.askyesno("Delete", "Delete the selected note?"):
            self.notes = [n for n in self.notes if n.get("id") != sel[0]]
            save_notes(self.notes)
            self.clear_note_editor()
            self.refresh_notes()

    def refresh_notes(self):
        for item in self.notes_tree.get_children():
            self.notes_tree.delete(item)
        for n in self.notes:
            preview = " ".join(n.get("text", "").split())[:120]
            self.notes_tree.insert("", "end", iid=n.get("id"), values=(n.get("title", ""), preview))

    def heading_text(self, col):
        arrow = ""
        if col == self.sort_col:
            arrow = "  \u25bc" if self.sort_reverse else "  \u25b2"
        labels = {"datetime": "Date/Time", "title": "Task Title", "kimi": "Kimi", "claude": "Claude"}
        return labels[col] + arrow

    def sort_by(self, col):
        if col == self.sort_col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_col = col
            self.sort_reverse = col == "datetime"  # datetime: newest first; others: A-Z
        for c in ("datetime", "title", "kimi", "claude"):
            self.tree.heading(c, text=self.heading_text(c))
        self.refresh_list()

    def copy_var(self, var):
        self.clipboard_clear()
        self.clipboard_append(var.get())

    def copy_selected(self, field):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        idx = {"datetime": 0, "title": 1, "kimi": 2, "claude": 3}[field]
        self.clipboard_clear()
        self.clipboard_append(vals[idx])

    def run_cmd(self, cmd):
        cmd = cmd.strip()
        if not cmd:
            return
        subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)

    def add_task(self):
        tid = self.tid_var.get().strip()
        title = self.title_var.get().strip()
        if not tid and not title:
            messagebox.showwarning("Missing", "Task ID or title is required.")
            return
        full_title = f"{tid}: {title}" if tid else title
        # duplicate Task ID is not allowed (unless updating the same task)
        if tid:
            for t in self.tasks:
                if task_id_of(t["title"]) == tid and t["title"] != full_title:
                    messagebox.showwarning(
                        "Duplicate Task ID",
                        f"Task ID {tid} already exists for:\n\n{t['title']}\n\nDuplicate IDs are not allowed.",
                    )
                    return
        task = {"datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "title": full_title, "kimi": self.kimi_var.get().strip(), "claude": self.claude_var.get().strip()}
        # update if title already exists
        for i, t in enumerate(self.tasks):
            if t["title"] == full_title:
                self.tasks[i] = task
                break
        else:
            self.tasks.append(task)
        save_tasks(self.tasks)
        self.tid_var.set("")
        self.title_var.set("")
        self.kimi_var.set("")
        self.claude_var.set("")
        self.refresh_list()

    def on_select(self, _evt):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        # split stored "ID: title" back into the two fields
        if ": " in vals[1]:
            tid, title = vals[1].split(": ", 1)
            self.tid_var.set(tid)
            self.title_var.set(title)
        else:
            self.tid_var.set("")
            self.title_var.set(vals[1])
        self.kimi_var.set(vals[2])
        self.claude_var.set(vals[3])

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        titles = [self.tree.item(i, "values")[1] for i in sel]
        preview = "\n".join(f"  - {t}" for t in titles[:5])
        if len(titles) > 5:
            preview += f"\n  ... and {len(titles) - 5} more"
        if messagebox.askyesno("Delete", f"Delete {len(titles)} task(s)?\n\n{preview}"):
            self.tasks = [t for t in self.tasks if t["title"] not in titles]
            save_tasks(self.tasks)
            self.refresh_list()

    # --- Export / Import ---
    def export_tasks(self):
        path = filedialog.asksaveasfilename(
            title="Export tasks",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("CSV", "*.csv")],
        )
        if not path:
            return
        try:
            if path.lower().endswith(".csv"):
                with open(path, "w", newline="", encoding="utf-8-sig") as f:
                    w = csv.writer(f)
                    w.writerow(["datetime", "title", "kimi", "claude"])
                    for t in self.tasks:
                        w.writerow([t.get("datetime", ""), t["title"], t["kimi"], t["claude"]])
            else:
                Path(path).write_text(json.dumps(self.tasks, indent=2, ensure_ascii=False), encoding="utf-8")
            messagebox.showinfo("Export", f"Exported {len(self.tasks)} task(s) to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    def merge_tasks(self, incoming):
        """Merge incoming tasks: duplicate Task IDs skipped, same title replaced, else appended.
        Returns (added, updated, skipped)."""
        existing_ids = {task_id_of(t["title"]) for t in self.tasks}
        existing_titles = {t["title"] for t in self.tasks}
        added = updated = skipped = 0
        for t in incoming:
            tid = task_id_of(t.get("title", ""))
            if t["title"] in existing_titles:
                # same title = update (its own ID match is fine)
                for i, old in enumerate(self.tasks):
                    if old["title"] == t["title"]:
                        self.tasks[i] = t
                        break
                updated += 1
            elif tid and tid in existing_ids:
                skipped += 1
                continue
            else:
                self.tasks.append(t)
                existing_titles.add(t["title"])
                if tid:
                    existing_ids.add(tid)
                added += 1
        return added, updated, skipped

    def import_tasks(self):
        path = filedialog.askopenfilename(
            title="Import tasks",
            filetypes=[("JSON", "*.json"), ("CSV", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            if path.lower().endswith(".csv"):
                incoming = []
                with open(path, newline="", encoding="utf-8-sig") as f:
                    for row in csv.DictReader(f):
                        incoming.append({
                            "datetime": row.get("datetime", ""),
                            "title": row.get("title", ""),
                            "kimi": row.get("kimi", ""),
                            "claude": row.get("claude", ""),
                        })
            else:
                incoming = json.loads(Path(path).read_text(encoding="utf-8"))
            incoming = [t for t in incoming if t.get("title")]
            added, updated, skipped = self.merge_tasks(incoming)
            save_tasks(self.tasks)
            self.refresh_list()
            messagebox.showinfo("Import", f"Imported {len(incoming)} task(s):\n{added} added, {updated} updated, {skipped} skipped (duplicate Task ID).")
        except Exception as e:
            messagebox.showerror("Import failed", str(e))

    def clear_search(self):
        self.search_var.set("")
        self.refresh_list()

    def refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        words = self.search_var.get().lower().split()
        key = {"datetime": lambda t: t.get("datetime", ""), "title": lambda t: t["title"].lower(),
               "kimi": lambda t: t["kimi"].lower(), "claude": lambda t: t["claude"].lower()}[self.sort_col]

        def matches(t):
            tid = (task_id_of(t["title"]) or "").lower()
            title = t["title"].lower()
            return all(w in tid or w in title for w in words)

        shown = [t for t in self.tasks if not words or matches(t)]
        shown.sort(key=key, reverse=self.sort_reverse)
        for t in shown:
            self.tree.insert("", "end", values=(t.get("datetime", ""), t["title"], t["kimi"], t["claude"]))
        self.status_var.set(f"Showing {len(shown)} of {len(self.tasks)} task(s)")


if __name__ == "__main__":
    if not acquire_single_instance():
        focus_existing_window()
        sys.exit(0)
    App().mainloop()
