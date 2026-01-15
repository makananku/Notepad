# Editor package for Notepad with Pets
try:
    from editor.drawing import DrawingOverlay
except ImportError:
    try:
        from .drawing import DrawingOverlay
    except ImportError:
        DrawingOverlay = None

__all__ = ['DrawingOverlay']
