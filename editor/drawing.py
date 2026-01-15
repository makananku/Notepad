"""
DrawingOverlay class for freehand highlighting and annotations
Draws directly on top of text area and saves drawings persistently
"""

import tkinter as tk
import math
import json

# Import Theme for colors
try:
    from theme import Theme
except ImportError:
    try:
        import sys
        import os
        # Add parent directory to path
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        from theme import Theme
    except ImportError:
        # Fallback colors
        class Theme:
            BG_DARKER = "#181825"


class DrawingOverlay:
    """Drawing overlay for freehand highlighting - draws directly on text area"""
    
    COLORS = {
        'yellow': '#f9e2af',
        'green': '#a6e3a1',
        'pink': '#f5c2e7',
        'red': '#f38ba8',
        'blue': '#89b4fa',
    }
    
    def __init__(self, text_widget, text_frame):
        """
        Initialize drawing overlay on top of text widget
        
        Args:
            text_widget: The Text widget to draw on top of
            text_frame: The Frame containing the text widget
        """
        try:
            self.text_widget = text_widget
            self.text_frame = text_frame
            self.canvas = None
            self.active = False
            self.drawing = False
            self.erasing = False
            self.current_color = 'yellow'
            self.stroke_width = 4
            self.erase_radius = 10
            self.strokes_data = []  # List of stroke data: [{'points': [(x,y), ...], 'color': str, 'width': int}, ...]
            self.canvas_strokes = []  # Canvas line IDs for current drawing session
            self.current_stroke = None  # Current stroke being drawn
            self.last_x = 0
            self.last_y = 0
        except Exception as e:
            print(f"Error initializing DrawingOverlay: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def show(self):
        """Prepare drawing overlay - canvas is only shown when drawing is enabled"""
        # Don't create canvas here - will be created when enable_drawing() is called
        # Just mark as active (ready to draw when enabled)
        self.active = True
    
    def enable_drawing(self):
        """Enable drawing events on canvas - creates canvas if needed"""
        # Create canvas if it doesn't exist
        if not self.canvas:
            try:
                bg_color = self.text_widget.cget('background')
            except:
                bg_color = "#1e1e2e"  # Fallback to dark theme color
            
            self.canvas = tk.Canvas(
                self.text_frame,
                bg=bg_color,
                highlightthickness=0,
                cursor="pencil"
            )
            # Place canvas exactly on top of text widget
            self.canvas.place(in_=self.text_widget, relx=0, rely=0, relwidth=1, relheight=1)
            
            # Redraw all saved strokes
            self._redraw_all_strokes()
        
        if self.canvas:
            # Change cursor to pencil
            self.canvas.config(cursor="pencil")
            # Restore normal bindtags so canvas can receive events
            self.canvas.bindtags((self.canvas, ".", "all"))
            # Bind drawing events
            self.canvas.bind('<Button-1>', self._start_draw)
            self.canvas.bind('<B1-Motion>', self._draw)
            self.canvas.bind('<ButtonRelease-1>', self._end_draw)
    
    def disable_drawing(self):
        """Disable drawing - hide canvas but keep stroke data"""
        if self.canvas:
            # Destroy canvas to show text widget again
            self.canvas.destroy()
            self.canvas = None
        # Note: strokes_data is preserved for when drawing is enabled again
    
    def hide(self):
        """Hide drawing overlay (but keep strokes data)"""
        if self.canvas:
            self.canvas.destroy()
            self.canvas = None
        self.active = False
        # Don't clear strokes_data - keep it for persistence
        self.canvas_strokes = []
        self.current_stroke = None
    
    def _start_draw(self, event):
        """Start drawing or erasing"""
        if self.erasing:
            self._erase_at(event.x, event.y)
        else:
            self.drawing = True
            # Start new stroke
            color = self.COLORS.get(self.current_color, '#f9e2af')
            self.current_stroke = {
                'points': [(event.x, event.y)],
                'color': self.current_color,
                'width': self.stroke_width
            }
        self.last_x = event.x
        self.last_y = event.y
    
    def _draw(self, event):
        """Draw line segment or erase"""
        if self.erasing and self.canvas:
            self._erase_at(event.x, event.y)
            self.last_x = event.x
            self.last_y = event.y
        elif self.drawing and self.canvas and self.current_stroke:
            color = self.COLORS.get(self.current_color, '#f9e2af')
            # Draw line segment
            line_id = self.canvas.create_line(
                self.last_x, self.last_y, event.x, event.y,
                fill=color,
                width=self.stroke_width,
                capstyle=tk.ROUND,
                smooth=True
            )
            self.canvas_strokes.append(line_id)
            # Add point to current stroke
            self.current_stroke['points'].append((event.x, event.y))
            self.last_x = event.x
            self.last_y = event.y
    
    def _erase_at(self, x, y):
        """Erase strokes near the given point - only removes segments that are hit"""
        if not self.canvas:
            return
        
        # Track if any changes were made
        changed = False
        new_strokes = []  # Will contain updated strokes
        
        # Process each stroke to remove only segments that are hit
        for stroke_data in self.strokes_data:
            points = stroke_data.get('points', [])
            if len(points) < 2:
                continue
            
            # Find which segments should be kept (not hit by eraser)
            segments_to_keep = []
            for i in range(len(points) - 1):
                x1, y1 = points[i]
                x2, y2 = points[i + 1]
                dist = self._point_to_line_distance(x, y, x1, y1, x2, y2)
                if dist >= self.erase_radius:
                    # This segment should be kept
                    segments_to_keep.append(i)
            
            if len(segments_to_keep) == len(points) - 1:
                # No segments were hit, keep the entire stroke
                new_strokes.append(stroke_data)
            elif len(segments_to_keep) == 0:
                # All segments were hit, remove the entire stroke
                changed = True
            else:
                # Some segments were hit, need to split the stroke into continuous parts
                changed = True
                
                # Find continuous ranges of kept segments
                # Each range represents a continuous part of the stroke
                if segments_to_keep:
                    # Sort to ensure order
                    segments_to_keep.sort()
                    
                    # Group consecutive segments
                    continuous_parts = []
                    current_part = [segments_to_keep[0]]
                    
                    for i in range(1, len(segments_to_keep)):
                        if segments_to_keep[i] == segments_to_keep[i-1] + 1:
                            # Consecutive segment, add to current part
                            current_part.append(segments_to_keep[i])
                        else:
                            # Gap found, save current part and start new one
                            continuous_parts.append(current_part)
                            current_part = [segments_to_keep[i]]
                    continuous_parts.append(current_part)
                    
                    # Create strokes from each continuous part
                    for part in continuous_parts:
                        # Get all point indices for this part
                        point_indices = set()
                        for seg_idx in part:
                            point_indices.add(seg_idx)
                            point_indices.add(seg_idx + 1)
                        
                        # Create ordered points list
                        ordered_indices = sorted(point_indices)
                        new_points = [points[i] for i in ordered_indices]
                        
                        # If we have at least 2 points, create a new stroke
                        if len(new_points) >= 2:
                            new_stroke = {
                                'points': new_points,
                                'color': stroke_data.get('color', 'yellow'),
                                'width': stroke_data.get('width', 4)
                            }
                            new_strokes.append(new_stroke)
        
        # Update strokes data if changes were made
        if changed:
            self.strokes_data = new_strokes
            # Redraw all strokes
            self._redraw_all_strokes()
    
    def _point_to_line_distance(self, px, py, x1, y1, x2, y2):
        """Calculate distance from point to line segment"""
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 0 and dy == 0:
            return math.sqrt((px - x1)**2 + (py - y1)**2)
        
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        
        return math.sqrt((px - closest_x)**2 + (py - closest_y)**2)
    
    def _end_draw(self, event):
        """End drawing or erasing"""
        if self.drawing and self.current_stroke:
            # Save completed stroke to data
            if len(self.current_stroke['points']) > 1:  # Only save if has multiple points
                self.strokes_data.append(self.current_stroke)
            self.current_stroke = None
        self.drawing = False
    
    def set_color(self, color):
        """Set drawing color"""
        self.current_color = color
        self.erasing = False
        self._update_cursor()
    
    def set_width(self, width):
        """Set stroke width"""
        self.stroke_width = width
    
    def set_erase_mode(self, erase):
        """Set erase mode"""
        self.erasing = erase
        self._update_cursor()
    
    def set_erase_radius(self, radius):
        """Set erase radius"""
        self.erase_radius = radius
    
    def _update_cursor(self):
        """Update cursor based on mode"""
        if self.canvas:
            if self.erasing:
                self.canvas.config(cursor="circle")
            else:
                self.canvas.config(cursor="pencil")
    
    def clear(self):
        """Clear all drawings"""
        if self.canvas:
            self.canvas.delete("all")
        self.strokes_data = []
        self.canvas_strokes = []
        self.current_stroke = None
    
    def _redraw_all_strokes(self):
        """Redraw all saved strokes on canvas"""
        if not self.canvas:
            return
        
        # Clear canvas
        self.canvas.delete("all")
        self.canvas_strokes = []
        
        # Redraw all strokes
        for stroke_data in self.strokes_data:
            points = stroke_data.get('points', [])
            if len(points) < 2:
                continue
            
            color = self.COLORS.get(stroke_data.get('color', 'yellow'), '#f9e2af')
            width = stroke_data.get('width', 4)
            
            # Draw stroke as connected lines
            for i in range(len(points) - 1):
                x1, y1 = points[i]
                x2, y2 = points[i + 1]
                line_id = self.canvas.create_line(
                    x1, y1, x2, y2,
                    fill=color,
                    width=width,
                    capstyle=tk.ROUND,
                    smooth=True
                )
                self.canvas_strokes.append(line_id)
    
    def get_strokes_data(self):
        """Get serializable strokes data"""
        return self.strokes_data.copy()
    
    def set_strokes_data(self, strokes_data):
        """Load strokes data and redraw - accepts JSON string or list"""
        if isinstance(strokes_data, str):
            # If it's a JSON string, deserialize it
            if strokes_data.strip():
                self.deserialize(strokes_data)
            else:
                self.strokes_data = []
                if self.canvas:
                    self._redraw_all_strokes()
        else:
            # If it's already a list, use it directly
            self.strokes_data = strokes_data if strokes_data else []
            if self.canvas:
                self._redraw_all_strokes()
    
    def serialize(self):
        """Serialize strokes to JSON string"""
        return json.dumps(self.strokes_data)
    
    def deserialize(self, json_str):
        """Deserialize strokes from JSON string"""
        try:
            self.strokes_data = json.loads(json_str) if json_str else []
            if self.canvas:
                self._redraw_all_strokes()
        except:
            self.strokes_data = []
