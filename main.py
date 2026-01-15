#!/usr/bin/env python3
"""
Notepad with Pets - Entry Point
An aesthetic text editor with animated virtual pets

Run this file to start the application.
"""

import sys
import os
import tkinter as tk

# Add the current directory to path for module imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the main application
from notepad_app import NotepadWithPets


def main():
    """Main entry point for Notepad with Pets"""
    root = tk.Tk()
    app = NotepadWithPets(root)
    root.mainloop()


if __name__ == "__main__":
    main()
