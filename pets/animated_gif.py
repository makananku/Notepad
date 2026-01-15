"""
AnimatedGIF class for handling animated sprite sheets
"""

import tkinter as tk
import os

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class AnimatedGIF:
    """Handler for animated GIF sprites with rotation support"""
    
    def __init__(self, canvas, path, scale=0.5, target_height=None):
        self.canvas = canvas
        self.path = path
        self.scale = scale
        self.target_height = target_height
        self.frames = []
        self.current_frame = 0
        self.image_id = None
        self._load_gif()
    
    def _load_gif(self):
        """Load and extract frames from GIF"""
        if not PIL_AVAILABLE or not os.path.exists(self.path):
            return
        
        try:
            gif = Image.open(self.path)
            
            # Calculate scale based on target_height if provided
            calculated_scale = self.scale
            if self.target_height is not None:
                # Get first frame to determine original size
                gif.seek(0)
                first_frame = gif.convert('RGBA')
                original_height = first_frame.height
                
                # Calculate scale to reach target_height
                scale_by_height = self.target_height / original_height
                
                # Use the calculated scale (pet.py already ensures it doesn't exceed target)
                # But double-check: if scale from pet.py would exceed target, use scale_by_height
                calculated_scale = min(scale_by_height, self.scale) if self.scale > scale_by_height else self.scale
                
                # Reset to beginning
                gif.seek(0)
            
            try:
                while True:
                    frame = gif.convert('RGBA')
                    if calculated_scale != 1:
                        new_size = (int(frame.width * calculated_scale), int(frame.height * calculated_scale))
                        frame = frame.resize(new_size, Image.NEAREST)
                    
                    # Store normal, flipped, and rotated versions
                    flipped = frame.transpose(Image.FLIP_LEFT_RIGHT)
                    self.frames.append({
                        'normal': ImageTk.PhotoImage(frame),
                        'flipped': ImageTk.PhotoImage(flipped),
                        # For climbing: head should point UP, belly faces INTO the room
                        # Left wall: rotate 90° CCW (+90) so head points up, feet on left wall
                        'climb_left': ImageTk.PhotoImage(frame.rotate(90, expand=True)),
                        # Right wall: flip first, then rotate 90° CCW (+90) so head points up, feet on right wall
                        'climb_right': ImageTk.PhotoImage(flipped.rotate(90, expand=True)),
                    })
                    
                    gif.seek(gif.tell() + 1)
            except EOFError:
                pass
                
        except Exception as e:
            print(f"Error loading GIF {self.path}: {e}")
    
    def draw(self, x, y, mode='normal'):
        """Draw current frame at position with specified mode"""
        if not self.frames:
            return None
        
        if self.image_id:
            self.canvas.delete(self.image_id)
        
        frame_data = self.frames[self.current_frame]
        frame = frame_data.get(mode, frame_data['normal'])
        
        anchor = tk.S if mode in ['normal', 'flipped'] else tk.CENTER
        self.image_id = self.canvas.create_image(x, y, image=frame, anchor=anchor, tags="pet")
        return self.image_id
    
    def next_frame(self):
        """Advance to next frame"""
        if self.frames:
            self.current_frame = (self.current_frame + 1) % len(self.frames)
    
    def get_size(self):
        """Get sprite size"""
        if self.frames:
            frame = self.frames[0]['normal']
            return (frame.width(), frame.height())
        return (24, 24)
