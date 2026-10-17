# Task History Manager

A lightweight Windows desktop app (Tkinter) to keep track of your tasks along with the **Kimi** and **Claude** CLI session commands needed to resume each one.

**⬇️ Download the latest portable exe:** [Task History Manager.exe](https://github.com/hassantvs24/task-history-manager/releases/latest) — no installation or Python required.

## Features

- **Add / Update tasks** with a Task ID, title, and resume commands for Kimi and Claude
- **Duplicate Task ID protection** — the app warns when adding a Task ID that already exists
- **Search & filter** tasks instantly as you type
- **Column sorting** — click any column heading (Date/Time, Task Title, Kimi, Claude) to sort ascending/descending
- **Drag & drop reordering** — rearrange tasks manually; use the **Default Order** button to restore your saved order
- **Double-click to copy** — double-click a Kimi or Claude cell in the task list to copy its content instantly
- **Copy Kimi / Copy Claude** toolbar buttons — copy the selected task's session command with one click
- **One-click Copy** — copy a session command to the clipboard, or **Run** it directly from the app
- **Multi-select delete** — select several tasks (Ctrl/Shift-click) and delete them with a confirmation preview
- **Import / Export** tasks as JSON or CSV for backup or sharing; imports skip duplicate Task IDs (with an added/updated/skipped summary)
- **Single instance** — launching again brings the existing window to the foreground
- Data is stored in a plain `tasks.json` file next to the app

### Notes

- **Notes tab** — save multi-line notes with an optional title (stored in `notes.json`)
- **Note editing** — select a note to load it into the editor, then **Add / Update**, **Clear**, **Copy**, or **Delete**
- **Copy note title** — one-click copy of the note's title from the editor
- **Duplicate note protection** — the app warns when saving a note whose exact text already exists
- **Double-click a note to copy** — double-clicking a note row in the list copies its full text instantly
- **Note drag & drop reordering** — rearrange notes manually; the saved order is preserved

## Usage

### Run from source

```bat
Task History Manager.bat
```

(or `pythonw app.py`)

### Build the portable exe

```bat
build.bat
```

This uses PyInstaller to produce a single-file, windowed executable at `dist\Task History Manager.exe`.

## Data files

| File           | Purpose                                  |
| -------------- | ---------------------------------------- |
| `tasks.json`   | Your saved tasks (created automatically) |
| `notes.json`   | Your saved notes (created automatically) |

## Requirements

- Windows
- Python 3.x with Tkinter (for running from source / building)
- PyInstaller (for building the exe)

## License

MIT
