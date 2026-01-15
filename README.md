# Notepad with Pets

A beautiful, aesthetic text editor with animated virtual pets. Inspired by the VS Code Pets extension.

![Dark Theme](https://img.shields.io/badge/Theme-Dark%20Catppuccin-1e1e2e)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

### Text Editor
- Modern dark theme (Catppuccin Mocha inspired)
- Full notepad functionality (New, Open, Save, Save As)
- Syntax highlighting friendly font (Consolas)
- Undo/Redo support
- Line and column display
- Keyboard shortcuts

### Virtual Pets
- Animated GIF sprites from vscode-pets (MIT License)
- Multiple pet types: Dog, Clippy, Fox
- Pets live inside the editor area (bottom overlay)
- Interactive ball throwing
- Pets walk, run, and idle with smooth animations

## Screenshots

```
+--------------------------------------------------+
|  File  Edit  Pets                                |
+--------------------------------------------------+
|  [New] [Open] [Save]  |  [Add Pet] [Throw Ball]  |
+--------------------------------------------------+
|                                                  |
|  Your text goes here...                          |
|  The editor has a beautiful dark theme.          |
|                                                  |
|                                                  |
|                                                  |
|  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  |
|     🐕          🦊                               |
|    Buddy       Foxy                              |
+--------------------------------------------------+
|  Ready          Ln 1, Col 1          Pets: 2    |
+--------------------------------------------------+
```

## Installation

### Prerequisites
- Python 3.8 or higher
- Pillow library (for GIF animation)

### Install Dependencies

```bash
pip install Pillow
```

### Run Application

```bash
cd ReverseEngineering
python notepad_with_pets.py
```

Or double-click `run_notepad_pets.bat` on Windows.

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New file |
| Ctrl+O | Open file |
| Ctrl+S | Save file |
| Ctrl+Shift+S | Save as |
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| Ctrl+X | Cut |
| Ctrl+C | Copy |
| Ctrl+V | Paste |
| Ctrl+A | Select all |
| Space | Throw ball (when not typing) |

## Pet Types

| Pet | Description | Sprite |
|-----|-------------|--------|
| Dog | Brown dog with walk/run animations | From NVPH Studio |
| Clippy | Classic Microsoft Clippy | From Marc Duiker |
| Fox | Red fox with smooth animations | From Elthen |

## Color Theme

Uses Catppuccin Mocha color palette:

- **Background**: `#1e1e2e` (Base)
- **Surface**: `#313244` 
- **Text**: `#cdd6f4`
- **Accent**: `#89b4fa` (Blue)
- **Accent Pink**: `#f5c2e7`
- **Accent Green**: `#a6e3a1`

## Project Structure

```
ReverseEngineering/
├── notepad_with_pets.py    # Main application
├── run_notepad_pets.bat    # Windows launcher
├── README.md               # This file
└── assets/
    └── pets/
        ├── dog/
        │   ├── brown_idle.gif
        │   ├── brown_walk.gif
        │   └── brown_run.gif
        ├── cat/
        │   ├── clippy_idle.gif
        │   └── clippy_walk.gif
        └── fox/
            ├── red_idle.gif
            └── red_walk.gif
```

## Credits

### Pet Sprites (MIT License)
Pet sprites are from [vscode-pets](https://github.com/tonybaloney/vscode-pets) by Anthony Shaw:

- **Dog sprites**: NVPH Studio
- **Fox sprites**: Elthen
- **Clippy sprites**: Marc Duiker

### Color Theme
Inspired by [Catppuccin](https://github.com/catppuccin/catppuccin) Mocha theme.

## License

This project is open source under the MIT License.

Pet sprites are used under the MIT License from vscode-pets.

---

**Enjoy coding with your virtual pets!** 🐕 🦊 📎
