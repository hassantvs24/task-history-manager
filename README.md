# Task History Manager

A lightweight Windows desktop app (Tkinter) to keep track of your tasks along with the **Kimi** and **Claude** CLI session commands needed to resume each one.

**⬇️ Download the latest portable exe:** [Task History Manager.exe](https://github.com/hassantvs24/task-history-manager/releases/latest) — no installation or Python required.

## Features

- **Add / Update tasks** with a Task ID, title, and resume commands for Kimi and Claude
- **One-click Copy** — copy a session command to the clipboard, or **Run** it directly from the app
- **Search & filter** tasks instantly as you type
- **Import / Export** tasks as CSV for backup or sharing
- **Single instance** — launching again brings the existing window to the foreground
- **Window state persistence** — size and position are remembered between runs
- Data is stored in a plain `tasks.json` file next to the app

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
| `settings.json`| Window geometry (created automatically)  |

## Requirements

- Windows
- Python 3.x with Tkinter (for running from source / building)
- PyInstaller (for building the exe)

## License

MIT
