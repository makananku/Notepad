"""
Notepad with Pets - Aesthetic Text Editor with Animated Virtual Pets
Inspired by VS Code Pets Extension

Features:
- Dark theme aesthetic UI
- Animated pet sprites from vscode-pets (MIT License)
- Pet overlay on entire editor area
- Wall climbing, ball chasing, swipe animations
- Mouse click to throw ball
- Smooth movement with easing

Credits:
- Pet sprites from vscode-pets by Anthony Shaw (MIT License)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import random

# Import RTF handler for formatted file save/load
try:
    from utils.rtf_handler import RTFHandler
    HAS_RTF_SUPPORT = True
except ImportError:
    HAS_RTF_SUPPORT = False
import math
import re
from pathlib import Path

# Try to import PIL for GIF animation
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: Pillow not installed. Run: pip install Pillow")

# Import Theme and DrawingOverlay
try:
    from theme import Theme
except ImportError:
    # Fallback Theme class if theme.py not found
    class Theme:
        BG_DARK = "#1e1e2e"
        BG_DARKER = "#181825"
        BG_SURFACE = "#313244"
        BG_OVERLAY = "#45475a"
        TEXT = "#cdd6f4"
        TEXT_DIM = "#a6adc8"
        TEXT_MUTED = "#6c7086"
        SUBTEXT = "#a6adc8"
        ACCENT = "#89b4fa"
        ACCENT_PINK = "#f5c2e7"
        ACCENT_MAUVE = "#cba6f7"
        ACCENT_GREEN = "#a6e3a1"
        ACCENT_PEACH = "#fab387"

# Import DrawingOverlay
try:
    import sys
    import os
    # Add current directory to path for imports
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    from editor.drawing import DrawingOverlay
except ImportError as e:
    print(f"Warning: Could not import DrawingOverlay: {e}")
    import traceback
    traceback.print_exc()
    # Fallback - define minimal DrawingOverlay if import fails
    class DrawingOverlay:
        COLORS = {'yellow': '#f9e2af', 'green': '#a6e3a1', 'pink': '#f5c2e7', 'red': '#f38ba8', 'blue': '#89b4fa'}
        def __init__(self, text_widget, text_frame):
            self.text_widget = text_widget
            self.text_frame = text_frame
            self.active = False
            self.strokes_data = []
            self.erasing = False
            self.current_color = 'yellow'
            self.stroke_width = 4
            self.canvas = None
        def show(self): self.active = True
        def hide(self): self.active = False
        def enable_drawing(self): pass
        def disable_drawing(self): pass
        def serialize(self): return ""
        def deserialize(self, s): pass
        def set_strokes_data(self, d): pass
        def clear(self): pass
        def set_color(self, c): self.current_color = c; self.erasing = False
        def set_width(self, w): self.stroke_width = w
        def set_erase_mode(self, e): self.erasing = e

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


class Pet:
    """Virtual pet with state machine and smooth movement"""
    
    # Target height for normalization (based on dog/fox/duck size after scale 0.5)
    # This is the maximum size - pets should not exceed this
    TARGET_HEIGHT = 45
    
    # States
    IDLE = 'idle'
    WALK = 'walk'
    RUN = 'run'
    WITH_BALL = 'with_ball'
    CLIMB_UP = 'climb_up'
    CLIMB_DOWN = 'climb_down'
    SWIPE = 'swipe'
    
    # Pet types organized by animal and color
    # Format: 'pet_key': {'folder': ..., 'color': ..., sprites...}
    PET_CONFIGS = {
        # ===== DOGS =====
        'dog_akita': {
            'animal': 'Dog', 'folder': 'dog', 'color': 'Akita', 'color_hex': '#D4A574',
            'idle': 'akita_idle_8fps.gif', 'walk': 'akita_walk_8fps.gif', 'run': 'akita_run_8fps.gif',
            'with_ball': 'akita_with_ball_8fps.gif', 'swipe': 'akita_swipe_8fps.gif',
        },
        'dog_black': {
            'animal': 'Dog', 'folder': 'dog', 'color': 'Black', 'color_hex': '#2D2D2D',
            'idle': 'black_idle_8fps.gif', 'walk': 'black_walk_8fps.gif', 'run': 'black_run_8fps.gif',
            'with_ball': 'black_with_ball_8fps.gif', 'swipe': 'black_swipe_8fps.gif',
        },
        'dog_brown': {
            'animal': 'Dog', 'folder': 'dog', 'color': 'Brown', 'color_hex': '#8B4513',
            'idle': 'brown_idle_8fps.gif', 'walk': 'brown_walk_8fps.gif', 'run': 'brown_run_8fps.gif',
            'with_ball': 'brown_with_ball_8fps.gif', 'swipe': 'brown_swipe_8fps.gif',
        },
        'dog_red': {
            'animal': 'Dog', 'folder': 'dog', 'color': 'Red', 'color_hex': '#CD5C5C',
            'idle': 'red_idle_8fps.gif', 'walk': 'red_walk_8fps.gif', 'run': 'red_run_8fps.gif',
            'with_ball': 'red_with_ball_8fps.gif', 'swipe': 'red_swipe_8fps.gif',
        },
        'dog_white': {
            'animal': 'Dog', 'folder': 'dog', 'color': 'White', 'color_hex': '#F5F5F5',
            'idle': 'white_idle_8fps.gif', 'walk': 'white_walk_8fps.gif', 'run': 'white_run_8fps.gif',
            'with_ball': 'white_with_ball_8fps.gif', 'swipe': 'white_swipe_8fps.gif',
        },
        # ===== FOXES =====
        'fox_red': {
            'animal': 'Fox', 'folder': 'fox', 'color': 'Red', 'color_hex': '#CD5C5C',
            'idle': 'red_idle_8fps.gif', 'walk': 'red_walk_8fps.gif', 'run': 'red_run_8fps.gif',
            'with_ball': 'red_with_ball_8fps.gif', 'swipe': 'red_swipe_8fps.gif',
        },
        'fox_white': {
            'animal': 'Fox', 'folder': 'fox', 'color': 'White', 'color_hex': '#F5F5F5',
            'idle': 'white_idle_8fps.gif', 'walk': 'white_walk_8fps.gif', 'run': 'white_run_8fps.gif',
            'with_ball': 'white_with_ball_8fps.gif', 'swipe': 'white_swipe_8fps.gif',
        },
        # ===== CLIPPY =====
        'clippy_black': {
            'animal': 'Clippy', 'folder': 'clippy', 'color': 'Black', 'color_hex': '#2D2D2D',
            'idle': 'black_idle_8fps.gif', 'walk': 'black_walk_8fps.gif', 'run': 'black_run_8fps.gif',
            'with_ball': 'black_with_ball_8fps.gif', 'swipe': 'black_swipe_8fps.gif',
        },
        'clippy_brown': {
            'animal': 'Clippy', 'folder': 'clippy', 'color': 'Brown', 'color_hex': '#8B4513',
            'idle': 'brown_idle_8fps.gif', 'walk': 'brown_walk_8fps.gif', 'run': 'brown_run_8fps.gif',
            'with_ball': 'brown_with_ball_8fps.gif', 'swipe': 'brown_swipe_8fps.gif',
        },
        'clippy_green': {
            'animal': 'Clippy', 'folder': 'clippy', 'color': 'Green', 'color_hex': '#4CAF50',
            'idle': 'green_idle_8fps.gif', 'walk': 'green_walk_8fps.gif', 'run': 'green_run_8fps.gif',
            'with_ball': 'green_with_ball_8fps.gif', 'swipe': 'green_swipe_8fps.gif',
        },
        'clippy_yellow': {
            'animal': 'Clippy', 'folder': 'clippy', 'color': 'Yellow', 'color_hex': '#FFD700',
            'idle': 'yellow_idle_8fps.gif', 'walk': 'yellow_walk_8fps.gif', 'run': 'yellow_run_8fps.gif',
            'with_ball': 'yellow_with_ball_8fps.gif', 'swipe': 'yellow_swipe_8fps.gif',
        },
        # ===== COCKATIEL =====
        'cockatiel_gray': {
            'animal': 'Cockatiel', 'folder': 'cockatiel', 'color': 'Gray', 'color_hex': '#808080',
            'idle': 'gray_idle_8fps.gif', 'walk': 'gray_walk_8fps.gif', 'run': 'gray_run_8fps.gif',
            'with_ball': 'gray_with_ball_8fps.gif', 'swipe': 'gray_swipe_8fps.gif',
        },
        # ===== CRAB =====
        'crab_red': {
            'animal': 'Crab', 'folder': 'crab', 'color': 'Red', 'color_hex': '#CD5C5C',
            'idle': 'red_idle_8fps.gif', 'walk': 'red_walk_8fps.gif', 'run': 'red_run_8fps.gif',
            'with_ball': 'red_with_ball_8fps.gif', 'swipe': 'red_swipe_8fps.gif',
        },
        # ===== CHICKEN =====
        'chicken_white': {
            'animal': 'Chicken', 'folder': 'chicken', 'color': 'White', 'color_hex': '#F5F5F5',
            'idle': 'white_idle_8fps.gif', 'walk': 'white_walk_8fps.gif', 'run': 'white_run_8fps.gif',
            'with_ball': 'white_with_ball_8fps.gif', 'swipe': 'white_swipe_8fps.gif',
        },
        # ===== DENO =====
        'deno_green': {
            'animal': 'Deno', 'folder': 'deno', 'color': 'Green', 'color_hex': '#4CAF50',
            'idle': 'green_idle_8fps.gif', 'walk': 'green_walk_8fps.gif', 'run': 'green_run_8fps.gif',
            'with_ball': 'green_with_ball_8fps.gif', 'swipe': 'green_swipe_8fps.gif',
        },
        # ===== HORSE =====
        'horse_brown': {
            'animal': 'Horse', 'folder': 'horse', 'color': 'Brown', 'color_hex': '#8B4513',
            'idle': 'brown_idle_8fps.gif', 'walk': 'brown_walk_8fps.gif', 'run': 'brown_run_8fps.gif',
            'with_ball': 'brown_with_ball_8fps.gif', 'swipe': 'brown_swipe_8fps.gif',
        },
        'horse_white': {
            'animal': 'Horse', 'folder': 'horse', 'color': 'White', 'color_hex': '#F5F5F5',
            'idle': 'white_idle_8fps.gif', 'walk': 'white_walk_8fps.gif', 'run': 'white_run_8fps.gif',
            'with_ball': 'white_with_ball_8fps.gif', 'swipe': 'white_swipe_8fps.gif',
        },
        # ===== MOD =====
        'mod_purple': {
            'animal': 'Mod', 'folder': 'mod', 'color': 'Purple', 'color_hex': '#9C27B0',
            'idle': 'purple_idle_8fps.gif', 'walk': 'purple_walk_8fps.gif', 'run': 'purple_run_8fps.gif',
            'with_ball': 'purple_with_ball_8fps.gif', 'swipe': 'purple_swipe_8fps.gif',
        },
        # ===== PANDA =====
        'panda_black': {
            'animal': 'Panda', 'folder': 'panda', 'color': 'Black', 'color_hex': '#2D2D2D',
            'idle': 'black_idle_8fps.gif', 'walk': 'black_walk_8fps.gif', 'run': 'black_run_8fps.gif',
            'with_ball': 'black_with_ball_8fps.gif', 'swipe': 'black_swipe_8fps.gif',
        },
        # ===== RAT =====
        'rat_gray': {
            'animal': 'Rat', 'folder': 'rat', 'color': 'Gray', 'color_hex': '#808080',
            'idle': 'gray_idle_8fps.gif', 'walk': 'gray_walk_8fps.gif', 'run': 'gray_run_8fps.gif',
            'with_ball': 'gray_with_ball_8fps.gif', 'swipe': 'gray_swipe_8fps.gif',
        },
        'rat_white': {
            'animal': 'Rat', 'folder': 'rat', 'color': 'White', 'color_hex': '#F5F5F5',
            'idle': 'white_idle_8fps.gif', 'walk': 'white_walk_8fps.gif', 'run': 'white_run_8fps.gif',
            'with_ball': 'white_with_ball_8fps.gif', 'swipe': 'white_swipe_8fps.gif',
        },
        # ===== ROCKY =====
        'rocky_gray': {
            'animal': 'Rocky', 'folder': 'rocky', 'color': 'Gray', 'color_hex': '#808080',
            'idle': 'gray_idle_8fps.gif', 'walk': 'gray_walk_8fps.gif', 'run': 'gray_run_8fps.gif',
            'with_ball': 'gray_walk_8fps.gif', 'swipe': 'gray_swipe_8fps.gif',
        },
        # ===== RUBBER DUCK =====
        'duck_yellow': {
            'animal': 'Duck', 'folder': 'rubber-duck', 'color': 'Yellow', 'color_hex': '#FFD700',
            'idle': 'yellow_idle_8fps.gif', 'walk': 'yellow_walk_8fps.gif', 'run': 'yellow_run_8fps.gif',
            'with_ball': 'yellow_with_ball_8fps.gif', 'swipe': 'yellow_swipe_8fps.gif',
        },
        # ===== SNAKE =====
        'snake_green': {
            'animal': 'Snake', 'folder': 'snake', 'color': 'Green', 'color_hex': '#4CAF50',
            'idle': 'green_idle_8fps.gif', 'walk': 'green_walk_8fps.gif', 'run': 'green_run_8fps.gif',
            'with_ball': 'green_with_ball_8fps.gif', 'swipe': 'green_swipe_8fps.gif',
        },
        # ===== TOTORO =====
        'totoro_gray': {
            'animal': 'Totoro', 'folder': 'totoro', 'color': 'Gray', 'color_hex': '#808080',
            'idle': 'gray_idle_8fps.gif', 'walk': 'gray_walk_8fps.gif', 'run': 'gray_run_8fps.gif',
            'with_ball': 'gray_with_ball_8fps.gif', 'swipe': 'gray_swipe_8fps.gif',
        },
        # ===== TURTLE =====
        'turtle_green': {
            'animal': 'Turtle', 'folder': 'turtle', 'color': 'Green', 'color_hex': '#4CAF50',
            'idle': 'green_idle_8fps.gif', 'walk': 'green_walk_8fps.gif', 'run': 'green_run_8fps.gif',
            'with_ball': 'green_with_ball_8fps.gif', 'swipe': 'green_swipe_8fps.gif',
        },
        # ===== ZAPPY =====
        'zappy_yellow': {
            'animal': 'Zappy', 'folder': 'zappy', 'color': 'Yellow', 'color_hex': '#FFD700',
            'idle': 'yellow_idle_8fps.gif', 'walk': 'yellow_walk_8fps.gif', 'run': 'yellow_run_8fps.gif',
            'with_ball': 'yellow_with_ball_8fps.gif', 'swipe': 'yellow_swipe_8fps.gif',
        },
    }
    
    # Legacy aliases for backward compatibility
    LEGACY_PET_MAP = {
        'dog': 'dog_brown',
        'fox': 'fox_red',
        'clippy': 'clippy_black',  # Changed from removed cat_clippy
    }
    
    # Get list of animals and their color variants
    @classmethod
    def get_pet_menu_structure(cls):
        """Get organized structure for pet menu"""
        animals = {}
        for pet_key, config in cls.PET_CONFIGS.items():
            animal = config['animal']
            if animal not in animals:
                animals[animal] = []
            animals[animal].append({
                'key': pet_key,
                'color': config['color'],
                'color_hex': config['color_hex'],
                'idle_file': f"{config['folder']}/{config['idle']}"
            })
        return animals
    
    def __init__(self, canvas, pet_type='dog_brown', assets_path=None):
        self.canvas = canvas
        # Handle legacy pet types
        if pet_type in self.LEGACY_PET_MAP:
            pet_type = self.LEGACY_PET_MAP[pet_type]
        self.pet_type = pet_type
        self.config = self.PET_CONFIGS.get(pet_type, self.PET_CONFIGS['dog_brown'])
        
        # Position
        self.x = 100.0
        self.y = 0.0
        
        # Velocity for smooth movement
        self.vx = 0.0
        self.vy = 0.0
        self.target_x = self.x
        self.target_y = self.y
        
        # Movement parameters - fast and responsive
        self.max_speed = 12.0  # Increased from 5.0
        self.acceleration = 0.35  # Increased from 0.15
        self.friction = 0.88  # More responsive
        
        # Direction: 1 = right, -1 = left
        self.direction = 1
        
        # State machine
        self.state = self.IDLE
        self.state_timer = 0
        self.state_duration = random.randint(1500, 4000)
        
        # Animation
        self.frame_timer = 0
        self.frame_interval = 80  # ms per frame
        
        # Canvas bounds
        self.canvas_width = 800
        self.canvas_height = 600
        self.ground_y = 580
        self.wall_margin = 30
        
        # Climbing state
        self.on_wall = None  # 'left', 'right', or None
        self.climb_target_y = 0
        
        # Ball catching
        self.has_ball = False
        self.ball_timer = 0
        self.target_ball_id = None  # ID of ball currently being chased
        
        # Load sprites
        self.sprites = {}
        self.current_sprite = None
        self._load_sprites(assets_path)
    
    def _load_sprites(self, assets_path):
        """Load all sprites for this pet with dynamic scaling based on target height"""
        if assets_path is None:
            assets_path = Path(__file__).parent / 'assets' / 'pets'
        else:
            assets_path = Path(assets_path)
        
        folder = assets_path / self.config['folder']
        
        # Calculate base scale from first available sprite (usually idle)
        # This ensures all sprites for this pet use the same scale
        base_scale = 0.5  # Default scale
        if PIL_AVAILABLE:
            # Try to get original size from idle sprite
            idle_sprite = self.config.get('idle')
            if idle_sprite:
                idle_file = folder / idle_sprite
                if idle_file.exists():
                    try:
                        gif = Image.open(str(idle_file))
                        original_height = gif.height
                        # Calculate scale to reach TARGET_HEIGHT
                        # Use min to ensure we don't exceed target (for pets larger than dog/fox/duck)
                        calculated_scale = min(self.TARGET_HEIGHT / original_height, 0.5)
                        base_scale = calculated_scale
                    except Exception as e:
                        print(f"Could not determine size for {self.pet_type}: {e}")
        
        # Load all sprites with calculated scale and target_height
        for state in ['idle', 'walk', 'run', 'with_ball', 'swipe']:
            sprite_name = self.config.get(state)
            if sprite_name:
                sprite_file = folder / sprite_name
                if sprite_file.exists():
                    # Pass target_height to ensure no pet exceeds dog/fox/duck size
                    self.sprites[state] = AnimatedGIF(
                        self.canvas, 
                        str(sprite_file), 
                        scale=base_scale,
                        target_height=self.TARGET_HEIGHT
                    )
        
        self.current_sprite = self.sprites.get('idle')
    
    def set_bounds(self, width, height, ground_y):
        """Set canvas bounds"""
        self.canvas_width = width
        self.canvas_height = height
        self.ground_y = ground_y
    
    def _ease_out_quad(self, t):
        """Easing function for smooth deceleration"""
        return t * (2 - t)
    
    def _change_state(self, new_state):
        """Change to a new state"""
        self.state = new_state
        self.state_timer = 0
        
        # Set sprite for state
        if new_state == self.WITH_BALL:
            self.current_sprite = self.sprites.get('with_ball', self.sprites.get('idle'))
        elif new_state == self.SWIPE:
            self.current_sprite = self.sprites.get('swipe', self.sprites.get('idle'))
        elif new_state in [self.CLIMB_UP, self.CLIMB_DOWN]:
            self.current_sprite = self.sprites.get('walk', self.sprites.get('idle'))
        elif new_state == self.RUN:
            self.current_sprite = self.sprites.get('run', self.sprites.get('walk'))
        elif new_state == self.WALK:
            self.current_sprite = self.sprites.get('walk', self.sprites.get('idle'))
        else:
            self.current_sprite = self.sprites.get('idle')
    
    def update(self, dt, available_balls=None):
        """Update pet state and position
        
        Args:
            dt: Delta time in milliseconds
            available_balls: Optional list of Ball objects to choose from
        """
        self.state_timer += dt
        self.frame_timer += dt
        
        # Update animation frame
        if self.frame_timer >= self.frame_interval:
            self.frame_timer = 0
            if self.current_sprite:
                self.current_sprite.next_frame()
        
        # Check for nearest ball if available and pet is not holding a ball
        # IMPORTANT: Don't check for new balls if pet is in WITH_BALL state (must finish animation first)
        if available_balls and not self.has_ball and self.state != self.WITH_BALL and self.on_wall is None:
            nearest_ball = self.find_nearest_ball(available_balls)
            if nearest_ball and nearest_ball.visible:
                # Always prioritize nearest ball - switch target if a closer ball is found
                # Or if we're idle/walking and don't have a target yet
                current_distance = float('inf')
                if self.target_ball_id is not None:
                    # Find current target ball to compare distance
                    for ball in available_balls:
                        if ball.unique_id == self.target_ball_id and ball.visible:
                            current_distance = self.get_distance_to(ball.x, ball.y)
                            break
                
                nearest_distance = self.get_distance_to(nearest_ball.x, nearest_ball.y)
                
                # Chase if: idle/walking, or nearest ball is closer than current target, or current target doesn't exist
                if (self.state in [self.IDLE, self.WALK] or 
                    nearest_distance < current_distance or 
                    self.target_ball_id != nearest_ball.unique_id):
                    self.target_ball_id = nearest_ball.unique_id
                    self.chase_ball(nearest_ball.x, nearest_ball.y)
        
        # State machine
        if self.state == self.IDLE:
            self._update_idle(dt)
        elif self.state == self.WALK:
            self._update_walk(dt)
        elif self.state == self.RUN:
            self._update_run(dt)
        elif self.state == self.WITH_BALL:
            self._update_with_ball(dt)
        elif self.state == self.CLIMB_UP:
            self._update_climb_up(dt)
        elif self.state == self.CLIMB_DOWN:
            self._update_climb_down(dt)
        elif self.state == self.SWIPE:
            self._update_swipe(dt)
        
        # Apply friction when on ground
        if self.on_wall is None:
            self.vx *= self.friction
        else:
            self.vy *= self.friction
        
        # Update position
        self.x += self.vx
        self.y += self.vy
        
        # Clamp to bounds
        self._clamp_position()
    
    def _update_idle(self, dt):
        """Idle state - wait then decide next action"""
        if self.state_timer >= self.state_duration:
            # Decide next action
            action = random.random()
            
            if action < 0.1 and self.sprites.get('swipe'):
                # Chance to swipe
                self._change_state(self.SWIPE)
                self.state_duration = 500
            elif action < 0.2 and self.canvas_height > 100:
                # Chance to climb wall (only if enough vertical space)
                self._start_climbing()
            else:
                # Walk to random position
                self.target_x = random.randint(self.wall_margin + 20, self.canvas_width - self.wall_margin - 20)
                self._change_state(self.WALK)
                self.state_duration = random.randint(2000, 5000)
    
    def _update_walk(self, dt):
        """Walking state - move towards target"""
        dx = self.target_x - self.x
        
        if abs(dx) < 10:
            # Reached target
            self.vx *= 0.5  # Quick slowdown
            self._change_state(self.IDLE)
            self.state_duration = random.randint(1000, 3000)
        else:
            # Move towards target with easing
            self.direction = 1 if dx > 0 else -1
            target_speed = min(abs(dx) * 0.1, self.max_speed * 0.7)
            self.vx += (self.direction * target_speed - self.vx) * self.acceleration
    
    def _update_run(self, dt):
        """Running state - chase ball fast"""
        dx = self.target_x - self.x
        
        # Don't auto-catch here - let collision detection in _animate() handle it
        # This ensures only one pet can catch one ball (first come first served)
        if abs(dx) < 10:
            # Very close to target - slow down but don't catch yet
            # Collision detection will handle the actual catch
            self.vx *= 0.7
        else:
            # Run fast towards target
            self.direction = 1 if dx > 0 else -1
            target_speed = self.max_speed
            self.vx += (self.direction * target_speed - self.vx) * self.acceleration * 2.0
    
    def _update_with_ball(self, dt):
        """With ball state - hold ball then drop"""
        self.ball_timer += dt
        
        if self.ball_timer >= self.state_duration:
            self.has_ball = False
            self.target_ball_id = None  # Clear target ball when dropping
            self._change_state(self.IDLE)
            self.state_duration = random.randint(1000, 2000)
    
    def _start_climbing(self):
        """Start climbing a wall"""
        # Choose which wall
        if self.x < self.canvas_width / 2:
            self.on_wall = 'left'
            self.target_x = self.wall_margin
        else:
            self.on_wall = 'right'
            self.target_x = self.canvas_width - self.wall_margin
        
        self.x = self.target_x
        # Pets can climb anywhere from near top to middle of the screen
        min_y = 50  # Near the top
        max_y = int(self.ground_y * 0.6)  # Up to 60% down
        self.climb_target_y = random.randint(min_y, max(min_y + 50, max_y))
        self._change_state(self.CLIMB_UP)
        self.state_duration = 8000  # More time to climb higher
    
    def _update_climb_up(self, dt):
        """Climbing up the wall"""
        dy = self.climb_target_y - self.y
        
        if abs(dy) < 10 or self.state_timer >= self.state_duration:
            # Start climbing down or rest
            if random.random() < 0.3:
                self._change_state(self.CLIMB_DOWN)
            else:
                # Rest on wall briefly
                self.state_timer = 0
                self.state_duration = random.randint(500, 1500)
                if self.state_timer >= self.state_duration:
                    self._change_state(self.CLIMB_DOWN)
        else:
            # Climb up
            target_speed = min(abs(dy) * 0.08, self.max_speed * 0.6)
            self.vy += (-target_speed - self.vy) * self.acceleration
    
    def _update_climb_down(self, dt):
        """Climbing down the wall"""
        dy = self.ground_y - self.y
        
        if dy < 10:
            # Reached ground
            self.y = self.ground_y
            self.on_wall = None
            self.vy = 0
            self._change_state(self.IDLE)
            self.state_duration = random.randint(500, 1500)
        else:
            # Climb down
            target_speed = min(dy * 0.1, self.max_speed * 0.8)
            self.vy += (target_speed - self.vy) * self.acceleration
    
    def _update_swipe(self, dt):
        """Swipe animation"""
        if self.state_timer >= self.state_duration:
            self._change_state(self.IDLE)
            self.state_duration = random.randint(1000, 2000)
    
    def _clamp_position(self):
        """Keep pet within bounds"""
        if self.on_wall is None:
            # On ground
            self.x = max(self.wall_margin, min(self.x, self.canvas_width - self.wall_margin))
            self.y = self.ground_y
        else:
            # On wall
            self.y = max(30, min(self.y, self.ground_y))
    
    def find_nearest_ball(self, balls):
        """Find the nearest visible ball from the list
        
        Args:
            balls: List of Ball objects
            
        Returns:
            Ball object that is nearest, or None if no visible balls
        """
        if not balls:
            return None
        
        # Filter visible balls
        visible_balls = [ball for ball in balls if ball.visible]
        if not visible_balls:
            return None
        
        # Find nearest ball
        nearest = min(visible_balls, key=lambda ball: self.get_distance_to(ball.x, ball.y))
        return nearest
    
    def chase_ball(self, ball_x, ball_y):
        """Start chasing a ball"""
        if self.on_wall:
            # If on wall, climb down first
            self._change_state(self.CLIMB_DOWN)
        
        self.target_x = ball_x
        self.target_y = ball_y
        
        if self.state != self.CLIMB_DOWN:
            self._change_state(self.RUN)
    
    def draw(self):
        """Draw the pet"""
        if not self.current_sprite:
            return
        
        # Determine draw mode based on state
        if self.on_wall == 'right':
            mode = 'climb_right'
        elif self.on_wall == 'left':
            mode = 'climb_left'
        elif self.direction < 0:
            mode = 'flipped'
        else:
            mode = 'normal'
        
        self.current_sprite.draw(self.x, self.y, mode)
    
    def get_distance_to(self, x, y):
        """Get distance to a point"""
        return math.sqrt((self.x - x) ** 2 + (self.y - y) ** 2)


class Ball:
    """Throwable ball with physics - faster and more realistic"""
    
    # Class variable for unique ID counter
    _id_counter = 0
    
    def __init__(self, canvas):
        self.canvas = canvas
        self.x = -100
        self.y = -100
        self.vx = 0
        self.vy = 0
        self.visible = False
        self.ball_id = None  # Canvas item ID
        self.unique_id = Ball._id_counter  # Unique identifier for this ball instance
        Ball._id_counter += 1
        self.ground_y = 0
        self.gravity = 0.8  # Increased from 0.4
        self.bounce = 0.6
        self.friction = 0.95
        self.radius = 5  # Slightly bigger for visibility
    
    def throw(self, x, y, ground_y):
        """Throw ball to position - always within visible bounds"""
        self.ground_y = ground_y
        
        # Clamp position to canvas bounds
        try:
            canvas_width = self.canvas.winfo_width()
            if canvas_width < 50:
                canvas_width = 800
        except:
            canvas_width = 800
        
        # Ensure ball starts within visible area
        self.x = max(self.radius + 5, min(x, canvas_width - self.radius - 5))
        self.y = max(self.radius + 5, min(y, ground_y - self.radius - 5))
        
        self.visible = True
        self.vx = random.uniform(-3, 3)  # Increased horizontal velocity
        self.vy = -8  # Increased from -3 for faster initial bounce
    
    def update(self):
        """Update ball physics"""
        if not self.visible:
            return
        
        # Apply gravity
        self.vy += self.gravity
        
        # Apply velocity
        self.x += self.vx
        self.y += self.vy
        
        # Bounce off walls
        try:
            canvas_width = self.canvas.winfo_width()
            if canvas_width > 50:
                if self.x <= self.radius:
                    self.x = self.radius
                    self.vx = abs(self.vx) * 0.8
                elif self.x >= canvas_width - self.radius:
                    self.x = canvas_width - self.radius
                    self.vx = -abs(self.vx) * 0.8
        except:
            pass
        
        # Bounce off ground
        if self.y >= self.ground_y - self.radius:
            self.y = self.ground_y - self.radius
            self.vy *= -self.bounce
            self.vx *= self.friction
            
            # Stop if very slow
            if abs(self.vy) < 1.0:
                self.vy = 0
    
    def draw(self):
        """Draw the ball"""
        if self.ball_id:
            self.canvas.delete(self.ball_id)
        
        if self.visible:
            self.ball_id = self.canvas.create_oval(
                self.x - self.radius, self.y - self.radius,
                self.x + self.radius, self.y + self.radius,
                fill=Theme.ACCENT_GREEN,
                outline="#7bc96f",  # Darker green outline
                width=1,
                tags="ball"
            )
    
    def hide(self):
        """Hide the ball (caught by pet)"""
        self.visible = False
        if self.ball_id:
            self.canvas.delete(self.ball_id)
            self.ball_id = None


class TabData:
    """Data for a single tab"""
    def __init__(self, tab_id):
        self.id = tab_id
        self.filepath = None
        self.is_modified = False
        self.content = ""
        self.name = "Untitled"
        self.drawing_data = ""  # JSON string of drawing strokes
    
    def get_display_name(self):
        """Get display name for tab"""
        name = os.path.basename(self.filepath) if self.filepath else self.name
        return f"{name} *" if self.is_modified else name


class NotepadWithPets:
    """Main application - Pets overlay on entire editor"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Notepad with Pets")
        self.root.geometry("1100x750")
        self.root.configure(bg=Theme.BG_DARK)
        
        # Tab management
        self.tabs = {}  # tab_id -> TabData
        self.tab_buttons = {}  # tab_id -> button widget
        self.active_tab_id = None
        self.tab_counter = 0
        
        self.pets = []
        self.balls = []  # List of balls - support multiple balls
        self.animation_running = True
        self.drawing_overlay = None
        self.draw_mode = False
        
        # Track active font size
        self.active_font_size = None
        self.font_size_button = None
        
        # Store formatting button references for state indicators
        self.format_buttons = {}  # {'bold': btn, 'italic': btn, 'underline': btn}
        self.highlight_button = None
        
        # Unified undo/redo history for all operations (text + formatting)
        self.undo_history = []  # Stack of states
        self.redo_history = []  # Stack of undone states
        self.max_history = 100  # Maximum history entries
        self.last_saved_state = None  # Track state to detect changes
        self.is_undoing = False  # Flag to prevent recording during undo/redo
        
        self._configure_styles()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_editor()
        self._setup_statusbar()
        self._init_pets()
        self._animate()
        self._bind_events()
        
        # Create first tab
        self._create_new_tab()
    
    def _configure_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Dark.TFrame', background=Theme.BG_DARK)
        style.configure('Dark.TButton', background=Theme.BG_SURFACE, foreground=Theme.TEXT, 
                       borderwidth=0, padding=(10, 5))
        style.map('Dark.TButton', background=[('active', Theme.BG_OVERLAY)])
        style.configure('Accent.TButton', background=Theme.ACCENT, foreground=Theme.BG_DARK,
                       borderwidth=0, padding=(10, 5))
        style.map('Accent.TButton', background=[('active', Theme.ACCENT_MAUVE)])
        style.configure('Dark.TLabel', background=Theme.BG_DARK, foreground=Theme.TEXT)
        
        # Custom scrollbar style - thin and modern
        style.configure('Dark.Vertical.TScrollbar',
                       background=Theme.BG_SURFACE,
                       troughcolor=Theme.BG_DARKER,
                       borderwidth=0,
                       width=10,
                       arrowsize=0)
        style.map('Dark.Vertical.TScrollbar',
                 background=[('active', Theme.BG_OVERLAY), ('pressed', Theme.ACCENT)])
    
    def _setup_menu(self):
        """Setup menu bar"""
        self.menubar = tk.Menu(self.root, bg=Theme.BG_DARKER, fg=Theme.TEXT,
                              activebackground=Theme.BG_OVERLAY, activeforeground=Theme.TEXT, borderwidth=0)
        self.root.config(menu=self.menubar)
        
        # File menu
        file_menu = tk.Menu(self.menubar, tearoff=0, bg=Theme.BG_SURFACE, fg=Theme.TEXT,
                           activebackground=Theme.ACCENT, activeforeground=Theme.BG_DARK)
        self.menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="Open...", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self.save_as_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)
        
        # Edit menu
        edit_menu = tk.Menu(self.menubar, tearoff=0, bg=Theme.BG_SURFACE, fg=Theme.TEXT,
                           activebackground=Theme.ACCENT, activeforeground=Theme.BG_DARK)
        self.menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", command=self._undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=self._redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", command=self._cut, accelerator="Ctrl+X")
        edit_menu.add_command(label="Copy", command=self._copy, accelerator="Ctrl+C")
        edit_menu.add_command(label="Paste", command=self._paste, accelerator="Ctrl+V")
        edit_menu.add_separator()
        edit_menu.add_command(label="Select All", command=self._select_all, accelerator="Ctrl+A")
        
        # Pets menu with cascading submenus for each animal type
        pets_menu = tk.Menu(self.menubar, tearoff=0, bg=Theme.BG_SURFACE, fg=Theme.TEXT,
                           activebackground=Theme.ACCENT, activeforeground=Theme.BG_DARK)
        self.menubar.add_cascade(label="Pets", menu=pets_menu)
        
        # Create submenus for each animal type
        self._create_pet_submenus(pets_menu)
        
        pets_menu.add_separator()
        pets_menu.add_command(label="Remove Last Pet", command=self._remove_pet)
        pets_menu.add_command(label="Remove All Pets", command=self._remove_all_pets)
    
    def _setup_toolbar(self):
        """Setup toolbar with file and formatting buttons"""
        toolbar = ttk.Frame(self.root, style='Dark.TFrame')
        toolbar.pack(fill=tk.X, padx=10, pady=(10, 0))
        
        # File buttons
        ttk.Button(toolbar, text="New", style='Dark.TButton', command=self.new_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Open", style='Dark.TButton', command=self.open_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Save", style='Dark.TButton', command=self.save_file).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Formatting buttons with tag names for state indicators
        self._create_format_btn(toolbar, "B", self._toggle_bold, bold=True, tag_name='bold')
        self._create_format_btn(toolbar, "I", self._toggle_italic, italic=True, tag_name='italic')
        self._create_format_btn(toolbar, "U", self._toggle_underline, underline=True, tag_name='underline')
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        
        # Font size dropdown
        self._create_font_size_btn(toolbar)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        
        # List dropdowns
        self._create_bullet_list_btn(toolbar)
        self._create_numbered_list_btn(toolbar)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        
        # Highlight dropdown button
        self._create_highlight_btn(toolbar)
        
        # Clear format
        ttk.Button(toolbar, text="Clear", style='Dark.TButton', command=self._clear_format).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Find button
        ttk.Button(toolbar, text="Find", style='Dark.TButton', command=self._show_find_dialog).pack(side=tk.LEFT, padx=2)
        
        # Draw mode button
        ttk.Button(toolbar, text="Draw", style='Dark.TButton', command=self._toggle_draw_mode).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Pet button
        ttk.Button(toolbar, text="Add Pet", style='Accent.TButton', command=self._show_add_pet_menu).pack(side=tk.LEFT, padx=2)
        
        # Info label
        info_label = ttk.Label(toolbar, text="Click pet area to throw ball", style='Dark.TLabel')
        info_label.pack(side=tk.RIGHT, padx=10)
    
    def _create_format_btn(self, parent, text, command, bold=False, italic=False, underline=False, tag_name=None):
        """Create a small formatting button that doesn't steal focus"""
        font_style = []
        if bold:
            font_style.append('bold')
        if italic:
            font_style.append('italic')
        if underline:
            font_style.append('underline')
        
        btn = tk.Button(
            parent,
            text=text,
            font=('Consolas', 9, ' '.join(font_style) if font_style else 'normal'),
            bg=Theme.BG_SURFACE,
            fg=Theme.TEXT,
            activebackground=Theme.BG_OVERLAY,
            activeforeground=Theme.TEXT,
            borderwidth=0,
            padx=8,
            pady=2,
            command=command,
            takefocus=False  # Prevent stealing focus from text area
        )
        btn.pack(side=tk.LEFT, padx=1)
        
        # Store button reference for state indicator
        if tag_name:
            self.format_buttons[tag_name] = btn
        
        return btn
    
    def _create_highlight_btn(self, parent):
        """Create highlight color dropdown button"""
        btn = tk.Menubutton(
            parent,
            text="Highlight",
            font=('Consolas', 9),
            bg=Theme.BG_SURFACE,
            fg=Theme.TEXT,
            activebackground=Theme.BG_OVERLAY,
            activeforeground=Theme.TEXT,
            borderwidth=0,
            padx=8,
            pady=2,
            relief=tk.FLAT,
            takefocus=False  # Prevent stealing focus
        )
        btn.pack(side=tk.LEFT, padx=1)
        self.highlight_button = btn  # Store reference
        
        menu = tk.Menu(btn, tearoff=0, bg=Theme.BG_SURFACE, fg=Theme.TEXT,
                      activebackground=Theme.ACCENT, activeforeground=Theme.BG_DARK)
        menu.add_command(label="Yellow", command=lambda: self._apply_highlight('yellow'))
        menu.add_command(label="Green", command=lambda: self._apply_highlight('green'))
        menu.add_command(label="Pink", command=lambda: self._apply_highlight('pink'))
        menu.add_command(label="Blue", command=lambda: self._apply_highlight('blue'))
        menu.add_separator()
        menu.add_command(label="Remove Highlight", command=self._remove_highlight)
        btn.config(menu=menu)
    
    def _setup_editor(self):
        """Setup editor with tab bar and pet canvas"""
        editor_container = ttk.Frame(self.root, style='Dark.TFrame')
        editor_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Main frame with border
        self.main_frame = tk.Frame(editor_container, bg=Theme.BG_DARKER,
                                   highlightthickness=2, highlightbackground=Theme.BG_SURFACE)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tab bar at top
        self.tab_bar = tk.Frame(self.main_frame, bg=Theme.BG_SURFACE, height=30)
        self.tab_bar.pack(side=tk.TOP, fill=tk.X)
        self.tab_bar.pack_propagate(False)
        
        # Container for tab buttons
        self.tab_buttons_frame = tk.Frame(self.tab_bar, bg=Theme.BG_SURFACE)
        self.tab_buttons_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        # New tab button (+)
        self.new_tab_btn = tk.Button(
            self.tab_bar, text="+", font=('Consolas', 12, 'bold'),
            bg=Theme.BG_SURFACE, fg=Theme.TEXT,
            activebackground=Theme.BG_OVERLAY, activeforeground=Theme.TEXT,
            borderwidth=0, padx=10, pady=2,
            command=self._create_new_tab
        )
        self.new_tab_btn.pack(side=tk.LEFT, padx=2)
        
        # Pet canvas at bottom (tall enough for climbing)
        self.pet_height = 100  # Reduced height for pet area
        self.pet_canvas = tk.Canvas(
            self.main_frame,
            bg=Theme.BG_DARKER,
            highlightthickness=0,
            height=self.pet_height,
            cursor="hand2"
        )
        self.pet_canvas.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Click on pet canvas to throw ball
        self.pet_canvas.bind('<Button-1>', self._on_pet_canvas_click)
        
        # Text frame above pet canvas
        self.text_frame = tk.Frame(self.main_frame, bg=Theme.BG_DARKER)
        self.text_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Text widget (normal text editing)
        self.text_area = tk.Text(
            self.text_frame,
            wrap=tk.WORD,
            font=("Consolas", 11),
            bg=Theme.BG_DARKER,
            fg=Theme.TEXT,
            insertbackground=Theme.ACCENT,
            selectbackground=Theme.ACCENT,
            selectforeground=Theme.BG_DARK,
            borderwidth=0,
            padx=15,
            pady=15,
            undo=True
        )
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Custom scrollbar - thin and minimal
        self.scrollbar_frame = tk.Frame(self.text_frame, bg=Theme.BG_DARKER, width=12)
        self.scrollbar_frame.pack(side=tk.RIGHT, fill=tk.Y)
        self.scrollbar_frame.pack_propagate(False)
        
        self.scrollbar_canvas = tk.Canvas(
            self.scrollbar_frame, bg=Theme.BG_DARKER, 
            highlightthickness=0, width=8
        )
        self.scrollbar_canvas.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Scrollbar thumb
        self.scroll_thumb = None
        self.scroll_dragging = False
        self.scroll_drag_start_y = 0
        
        self.text_area.config(yscrollcommand=self._on_scroll_change)
        self.scrollbar_canvas.bind('<Button-1>', self._on_scrollbar_click)
        self.scrollbar_canvas.bind('<B1-Motion>', self._on_scrollbar_drag)
        self.scrollbar_canvas.bind('<ButtonRelease-1>', self._on_scrollbar_release)
        self.scrollbar_canvas.bind('<MouseWheel>', lambda e: self.text_area.yview_scroll(-1*(e.delta//120), "units"))
        
        # Configure text formatting tags
        self._configure_text_tags()
        
        # Initialize drawing overlay (always visible for persistent drawings)
        # Will be shown when first tab is created
        try:
            self.drawing_overlay = DrawingOverlay(self.text_area, self.text_frame)
        except Exception as e:
            print(f"Warning: Could not initialize DrawingOverlay: {e}")
            # Create minimal fallback
            class MinimalDrawingOverlay:
                COLORS = {'yellow': '#f9e2af', 'green': '#a6e3a1', 'pink': '#f5c2e7', 'red': '#f38ba8', 'blue': '#89b4fa'}
                def __init__(self, *args, **kwargs):
                    self.active = False
                    self.erasing = False
                    self.current_color = 'yellow'
                    self.stroke_width = 4
                    self.canvas = None
                def show(self): self.active = True
                def hide(self): self.active = False
                def enable_drawing(self): pass
                def disable_drawing(self): pass
                def serialize(self): return ""
                def deserialize(self, s): pass
                def set_strokes_data(self, d): pass
                def clear(self): pass
                def set_color(self, c): self.current_color = c; self.erasing = False
                def set_width(self, w): self.stroke_width = w
                def set_erase_mode(self, e): self.erasing = e
            self.drawing_overlay = MinimalDrawingOverlay()
        
        # Bind resize
        self.pet_canvas.bind('<Configure>', self._on_resize)
    
    # Tab management
    def _create_new_tab(self, filepath=None, content=""):
        """Create a new tab"""
        self.tab_counter += 1
        tab_id = f"tab_{self.tab_counter}"
        
        # Save current tab content before switching
        if self.active_tab_id and self.active_tab_id in self.tabs:
            self.tabs[self.active_tab_id].content = self.text_area.get('1.0', tk.END)
        
        # Create tab data
        tab = TabData(tab_id)
        if filepath:
            tab.filepath = filepath
            tab.name = os.path.basename(filepath)
        else:
            tab.name = f"Untitled {self.tab_counter}"
        tab.content = content
        self.tabs[tab_id] = tab
        
        # Create tab button
        self._create_tab_button(tab_id)
        
        # Switch to new tab
        self._switch_to_tab(tab_id)
        
        return tab_id
    
    def _create_tab_button(self, tab_id):
        """Create a tab button with close button"""
        tab = self.tabs[tab_id]
        
        # Tab frame (contains label + close button)
        tab_frame = tk.Frame(self.tab_buttons_frame, bg=Theme.BG_SURFACE)
        tab_frame.pack(side=tk.LEFT, padx=1)
        
        # Tab label
        label = tk.Label(
            tab_frame, text=tab.get_display_name(),
            bg=Theme.BG_SURFACE, fg=Theme.TEXT,
            font=('Consolas', 9), padx=10, pady=5,
            cursor="hand2"
        )
        label.pack(side=tk.LEFT)
        label.bind('<Button-1>', lambda e, tid=tab_id: self._switch_to_tab(tid))
        
        # Close button (x)
        close_btn = tk.Label(
            tab_frame, text="x", bg=Theme.BG_SURFACE, fg=Theme.SUBTEXT,
            font=('Consolas', 9), padx=5, pady=5, cursor="hand2"
        )
        close_btn.pack(side=tk.LEFT)
        close_btn.bind('<Button-1>', lambda e, tid=tab_id: self._close_tab(tid))
        close_btn.bind('<Enter>', lambda e: close_btn.config(fg=Theme.ACCENT_PEACH))
        close_btn.bind('<Leave>', lambda e: close_btn.config(fg=Theme.SUBTEXT))
        
        self.tab_buttons[tab_id] = {
            'frame': tab_frame,
            'label': label,
            'close': close_btn
        }
    
    def _switch_to_tab(self, tab_id):
        """Switch to a tab"""
        if tab_id not in self.tabs:
            return

        # Save current tab content and drawing
        if self.active_tab_id and self.active_tab_id in self.tabs:
            self.tabs[self.active_tab_id].content = self.text_area.get('1.0', tk.END)
            if self.drawing_overlay:
                self.tabs[self.active_tab_id].drawing_data = self.drawing_overlay.serialize()

        # Update tab button styles
        for tid, btn_data in self.tab_buttons.items():
            if tid == tab_id:
                btn_data['frame'].config(bg=Theme.BG_DARKER)
                btn_data['label'].config(bg=Theme.BG_DARKER)
                btn_data['close'].config(bg=Theme.BG_DARKER)
            else:
                btn_data['frame'].config(bg=Theme.BG_SURFACE)
                btn_data['label'].config(bg=Theme.BG_SURFACE)
                btn_data['close'].config(bg=Theme.BG_SURFACE)

        # Load tab content
        tab = self.tabs[tab_id]
        self.text_area.delete('1.0', tk.END)
        if tab.content and tab.content.strip():
            self.text_area.insert('1.0', tab.content.rstrip('\n'))
        
        # Load drawing data for this tab
        if not tab.drawing_data and tab.filepath:
            tab.drawing_data = self._load_drawing_data(tab)
        
        # Ensure drawing overlay exists and is shown (for persistent drawings)
        if not self.drawing_overlay:
            self.drawing_overlay = DrawingOverlay(self.text_area, self.text_frame)
        
        if not self.drawing_overlay.active:
            self.drawing_overlay.show()
        
        # Load and redraw drawings for this tab
        self.drawing_overlay.set_strokes_data(tab.drawing_data if tab.drawing_data else "")

        self.active_tab_id = tab_id
        self._update_title()
        
        # Clear and save initial undo state for this tab
        self.undo_history.clear()
        self.redo_history.clear()
        self._save_undo_state()
    
    def _close_tab(self, tab_id):
        """Close a tab"""
        if tab_id not in self.tabs:
            return
        
        tab = self.tabs[tab_id]
        
        # Check if modified
        if tab.is_modified:
            result = messagebox.askyesnocancel(
                "Save Changes",
                f"Save changes to {tab.get_display_name().rstrip(' *')}?"
            )
            if result is True:
                self._save_tab(tab_id)
            elif result is None:
                return  # Cancel
        
        # Remove tab button
        if tab_id in self.tab_buttons:
            self.tab_buttons[tab_id]['frame'].destroy()
            del self.tab_buttons[tab_id]
        
        # Remove tab data
        del self.tabs[tab_id]
        
        # If no tabs left, close the application
        if not self.tabs:
            self._on_close()
        elif self.active_tab_id == tab_id:
            # Switch to another tab
            next_tab_id = list(self.tabs.keys())[0]
            self._switch_to_tab(next_tab_id)
    
    def _update_tab_label(self, tab_id):
        """Update tab label text"""
        if tab_id in self.tabs and tab_id in self.tab_buttons:
            tab = self.tabs[tab_id]
            self.tab_buttons[tab_id]['label'].config(text=tab.get_display_name())
    
    def _save_tab(self, tab_id):
        """Save a specific tab"""
        if tab_id not in self.tabs:
            return
        
        tab = self.tabs[tab_id]
        
        if tab.filepath:
            # Save current content if it's the active tab
            if tab_id == self.active_tab_id:
                tab.content = self.text_area.get('1.0', tk.END)
            
            try:
                # Save current drawing data if active tab
                if tab_id == self.active_tab_id and self.drawing_overlay:
                    tab.drawing_data = self.drawing_overlay.serialize()
                
                if tab.filepath.lower().endswith('.rtf') and HAS_RTF_SUPPORT:
                    # Save as RTF with formatting
                    tags_info = self._get_tags_as_dict()
                    rtf_content = RTFHandler.export_to_rtf(tab.content, tags_info)
                    with open(tab.filepath, 'w', encoding='utf-8') as f:
                        f.write(rtf_content)
                    self._set_status(f"Saved RTF: {os.path.basename(tab.filepath)}")
                else:
                    # Save as plain text
                    with open(tab.filepath, 'w', encoding='utf-8') as f:
                        f.write(tab.content)
                    self._set_status(f"Saved: {os.path.basename(tab.filepath)}")
                
                # Save drawing data to separate file
                self._save_drawing_data(tab)
                
                tab.is_modified = False
                self._update_tab_label(tab_id)
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file:\n{str(e)}")
        else:
            self._save_tab_as(tab_id)
    
    def _save_drawing_data(self, tab):
        """Save drawing data to separate JSON file"""
        if not tab.filepath:
            return
        
        try:
            # Save to .drawing.json file alongside the main file
            base_path = os.path.splitext(tab.filepath)[0]
            drawing_file = base_path + '.drawing.json'
            
            if tab.drawing_data:
                with open(drawing_file, 'w', encoding='utf-8') as f:
                    f.write(tab.drawing_data)
            elif os.path.exists(drawing_file):
                # Remove drawing file if no drawings
                os.remove(drawing_file)
        except Exception as e:
            print(f"Could not save drawing data: {e}")
    
    def _load_drawing_data(self, tab):
        """Load drawing data from separate JSON file"""
        if not tab.filepath:
            return ""
        
        try:
            base_path = os.path.splitext(tab.filepath)[0]
            drawing_file = base_path + '.drawing.json'
            
            if os.path.exists(drawing_file):
                with open(drawing_file, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            print(f"Could not load drawing data: {e}")
        
        return ""
    
    def _get_contrast_text_color(self, bg_color):
        """Calculate contrast text color (dark or light) based on background brightness"""
        # Convert hex to RGB
        bg_color = bg_color.lstrip('#')
        r = int(bg_color[0:2], 16)
        g = int(bg_color[2:4], 16)
        b = int(bg_color[4:6], 16)
        
        # Calculate relative luminance using WCAG formula
        # Normalize RGB values to 0-1
        def normalize(c):
            c = c / 255.0
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        
        r_norm = normalize(r)
        g_norm = normalize(g)
        b_norm = normalize(b)
        
        luminance = 0.2126 * r_norm + 0.7152 * g_norm + 0.0722 * b_norm
        
        # If background is light (luminance > 0.5), use dark text, else use light text
        return '#1e1e2e' if luminance > 0.5 else '#cdd6f4'
    
    def _configure_text_tags(self):
        """Configure text tags for formatting"""
        # Define all font sizes we support
        self.font_sizes = [8, 10, 12, 14, 16, 18, 20, 24]
        self.default_size = 11
        
        # Style combinations
        style_combos = {
            '': '',
            'bold': 'bold',
            'italic': 'italic',
            'underline': 'underline',
            'bold_italic': 'bold italic',
            'bold_underline': 'bold underline',
            'italic_underline': 'italic underline',
            'bold_italic_underline': 'bold italic underline',
        }
        
        # Create tags for default size (11) with styles
        for style_name, style_value in style_combos.items():
            if style_name:  # Skip empty style
                font_tuple = ('Consolas', self.default_size, style_value) if style_value else ('Consolas', self.default_size)
                self.text_area.tag_configure(style_name, font=font_tuple)
        
        # Create compound tags for each size + style combination
        for size in self.font_sizes:
            # Plain size (no style)
            self.text_area.tag_configure(f'font_{size}', font=('Consolas', size))
            
            # Size + style combinations
            for style_name, style_value in style_combos.items():
                if style_name:  # Skip empty style
                    tag_name = f'font_{size}_{style_name}'
                    font_tuple = ('Consolas', size, style_value)
                    self.text_area.tag_configure(tag_name, font=font_tuple)
        
        # List styles
        self.text_area.tag_configure('bullet', lmargin1=20, lmargin2=20)
        self.text_area.tag_configure('numbered', lmargin1=20, lmargin2=20)
        
        # Highlight colors (Catppuccin palette) with auto contrast text
        highlight_colors = {
            'highlight_yellow': '#f9e2af',
            'highlight_green': '#a6e3a1',
            'highlight_pink': '#f5c2e7',
            'highlight_blue': '#89b4fa',
        }
        
        for tag_name, bg_color in highlight_colors.items():
            text_color = self._get_contrast_text_color(bg_color)
            # Configure highlight with select colors so text can still be selected
            self.text_area.tag_configure(tag_name, 
                                       background=bg_color, 
                                       foreground=text_color,
                                       selectbackground=Theme.ACCENT,
                                       selectforeground=Theme.BG_DARK)
        
        # Find highlight
        find_match_bg = '#fab387'
        find_current_bg = '#f38ba8'
        self.text_area.tag_configure('find_match', 
                                    background=find_match_bg, 
                                    foreground=self._get_contrast_text_color(find_match_bg))
        self.text_area.tag_configure('find_current', 
                                    background=find_current_bg, 
                                    foreground=self._get_contrast_text_color(find_current_bg))
    
    def _on_pet_canvas_click(self, event):
        """Handle click on pet canvas - throw ball"""
        if self.pets:
            self._throw_ball_at(event.x, event.y)
    
    def _on_resize(self, event):
        """Handle resize"""
        width = event.width
        height = self.pet_height
        ground_y = height - 5
        
        for pet in self.pets:
            pet.set_bounds(width, height, ground_y)
    
    # Custom scrollbar methods
    def _on_scroll_change(self, first, last):
        """Update scrollbar thumb position"""
        self.scrollbar_canvas.delete("thumb")
        
        first = float(first)
        last = float(last)
        
        # Don't show scrollbar if content fits
        if first <= 0 and last >= 1:
            return
        
        canvas_height = self.scrollbar_canvas.winfo_height()
        thumb_top = first * canvas_height
        thumb_bottom = last * canvas_height
        thumb_height = max(thumb_bottom - thumb_top, 30)  # Minimum thumb size
        
        # Draw rounded thumb
        self.scroll_thumb = self.scrollbar_canvas.create_rectangle(
            1, thumb_top + 2, 7, thumb_top + thumb_height - 2,
            fill=Theme.BG_OVERLAY,
            outline="",
            tags="thumb"
        )
        
        # Store thumb position for dragging
        self.thumb_top = thumb_top
        self.thumb_height = thumb_height
    
    def _on_scrollbar_click(self, event):
        """Handle scrollbar click"""
        canvas_height = self.scrollbar_canvas.winfo_height()
        
        # Check if clicking on thumb
        if hasattr(self, 'thumb_top') and hasattr(self, 'thumb_height'):
            if self.thumb_top <= event.y <= self.thumb_top + self.thumb_height:
                self.scroll_dragging = True
                self.scroll_drag_start_y = event.y
                return
        
        # Click on track - jump to position
        fraction = event.y / canvas_height
        self.text_area.yview_moveto(fraction)
    
    def _on_scrollbar_drag(self, event):
        """Handle scrollbar drag"""
        if self.scroll_dragging:
            canvas_height = self.scrollbar_canvas.winfo_height()
            delta = event.y - self.scroll_drag_start_y
            self.scroll_drag_start_y = event.y
            
            # Calculate new position
            fraction = delta / canvas_height
            self.text_area.yview_scroll(int(fraction * 50), "units")
    
    def _on_scrollbar_release(self, event):
        """Handle scrollbar release"""
        self.scroll_dragging = False
    
    # Text formatting methods
    def _toggle_bold(self, event=None):
        """Toggle bold on selected text"""
        self._toggle_format('bold')
        return 'break'
    
    def _toggle_italic(self, event=None):
        """Toggle italic on selected text"""
        self._toggle_format('italic')
        return 'break'
    
    def _toggle_underline(self, event=None):
        """Toggle underline on selected text"""
        self._toggle_format('underline')
        return 'break'
    
    def _get_current_format_state(self, tags):
        """Parse current formatting state from tag list"""
        has_bold = False
        has_italic = False
        has_underline = False
        font_size = None
        
        for tag in tags:
            # Check for font size + style compound tags
            if tag.startswith('font_'):
                parts = tag.split('_')
                if len(parts) >= 2 and parts[1].isdigit():
                    font_size = int(parts[1])
                    # Check for style in compound tag
                    if 'bold' in tag:
                        has_bold = True
                    if 'italic' in tag:
                        has_italic = True
                    if 'underline' in tag:
                        has_underline = True
            # Check for plain style tags
            elif tag in ['bold', 'bold_italic', 'bold_underline', 'bold_italic_underline']:
                has_bold = True
            if tag in ['italic', 'bold_italic', 'italic_underline', 'bold_italic_underline']:
                has_italic = True
            if tag in ['underline', 'bold_underline', 'italic_underline', 'bold_italic_underline']:
                has_underline = True
        
        return has_bold, has_italic, has_underline, font_size
    
    def _get_format_tag_name(self, has_bold, has_italic, has_underline, font_size=None):
        """Build the appropriate tag name for the given format state"""
        style_parts = []
        if has_bold:
            style_parts.append('bold')
        if has_italic:
            style_parts.append('italic')
        if has_underline:
            style_parts.append('underline')
        
        style_name = '_'.join(style_parts) if style_parts else ''
        
        if font_size:
            if style_name:
                return f'font_{font_size}_{style_name}'
            else:
                return f'font_{font_size}'
        else:
            return style_name if style_name else None
    
    def _remove_all_format_tags(self, start, end):
        """Remove all formatting tags from a range"""
        # Remove plain style tags
        for tag in ['bold', 'italic', 'underline', 'bold_italic', 
                    'bold_underline', 'italic_underline', 'bold_italic_underline']:
            self.text_area.tag_remove(tag, start, end)
        
        # Remove all font size tags (plain and compound)
        for size in self.font_sizes:
            self.text_area.tag_remove(f'font_{size}', start, end)
            for style in ['bold', 'italic', 'underline', 'bold_italic', 
                         'bold_underline', 'italic_underline', 'bold_italic_underline']:
                self.text_area.tag_remove(f'font_{size}_{style}', start, end)
    
    def _toggle_format(self, format_type):
        """Toggle a format on selected text, preserving font size"""
        try:
            sel_start = self.text_area.index(tk.SEL_FIRST)
            sel_end = self.text_area.index(tk.SEL_LAST)
        except tk.TclError:
            # No selection - nothing to format
            return
        
        # Save state before change for undo
        self._save_undo_state()
        
        # Get current formatting at selection start
        current_tags = list(self.text_area.tag_names(sel_start))
        has_bold, has_italic, has_underline, font_size = self._get_current_format_state(current_tags)
        
        # Toggle the requested format
        if format_type == 'bold':
            has_bold = not has_bold
        elif format_type == 'italic':
            has_italic = not has_italic
        elif format_type == 'underline':
            has_underline = not has_underline
        
        # Remove all formatting tags from selection
        self._remove_all_format_tags(sel_start, sel_end)
        
        # Apply the appropriate compound tag
        new_tag = self._get_format_tag_name(has_bold, has_italic, has_underline, font_size)
        if new_tag:
            self.text_area.tag_add(new_tag, sel_start, sel_end)
        
        # Re-select the text to maintain selection visibility
        self.text_area.tag_add(tk.SEL, sel_start, sel_end)
        
        # Update button states
        self._update_format_button_states()
    
    def _toggle_tag(self, tag_name):
        """Legacy toggle tag function - redirects to _toggle_format"""
        self._toggle_format(tag_name)
    
    def _update_format_button_states(self):
        """Update toolbar button states based on current selection formatting"""
        try:
            # Try to get selection, fall back to insert position
            try:
                pos = self.text_area.index(tk.SEL_FIRST)
            except tk.TclError:
                pos = self.text_area.index(tk.INSERT)
            
            current_tags = list(self.text_area.tag_names(pos))
            
            # Use the format state parser to detect styles (including from compound tags)
            has_bold, has_italic, has_underline, active_size = self._get_current_format_state(current_tags)
            
            # Check highlights
            highlight_color = None
            for c in ['yellow', 'green', 'pink', 'blue']:
                if f'highlight_{c}' in current_tags:
                    highlight_color = c
                    break
            
            # Update button appearances
            def set_button_active(btn, is_active):
                if btn:
                    if is_active:
                        btn.config(bg=Theme.ACCENT, fg=Theme.BG_DARK)
                    else:
                        btn.config(bg=Theme.BG_SURFACE, fg=Theme.TEXT)
            
            # Update formatting buttons
            set_button_active(self.format_buttons.get('bold'), has_bold)
            set_button_active(self.format_buttons.get('italic'), has_italic)
            set_button_active(self.format_buttons.get('underline'), has_underline)
            
            # Update highlight button
            if self.highlight_button:
                if highlight_color:
                    colors = {'yellow': '#f9e2af', 'green': '#a6e3a1', 'pink': '#f5c2e7', 'blue': '#89b4fa'}
                    self.highlight_button.config(bg=colors.get(highlight_color, Theme.BG_SURFACE), 
                                                  fg=self._get_contrast_text_color(colors.get(highlight_color, Theme.BG_SURFACE)))
                else:
                    self.highlight_button.config(bg=Theme.BG_SURFACE, fg=Theme.TEXT)
            
            # Update font size button
            if self.font_size_button:
                if active_size:
                    self.font_size_button.config(text=f"{active_size}pt", bg=Theme.ACCENT, fg=Theme.BG_DARK)
                else:
                    self.font_size_button.config(text="Size", bg=Theme.BG_SURFACE, fg=Theme.TEXT)
                self.active_font_size = active_size
        except Exception:
            pass
    
    def _create_font_size_btn(self, parent):
        """Create font size dropdown button with active size indicator"""
        self.font_size_button = tk.Menubutton(
            parent,
            text="Size",
            font=('Consolas', 9),
            bg=Theme.BG_SURFACE,
            fg=Theme.TEXT,
            activebackground=Theme.BG_OVERLAY,
            activeforeground=Theme.TEXT,
            borderwidth=0,
            padx=8,
            pady=2,
            relief=tk.FLAT,
            takefocus=False  # Prevent stealing focus
        )
        self.font_size_button.pack(side=tk.LEFT, padx=1)
        
        menu = tk.Menu(self.font_size_button, tearoff=0, bg=Theme.BG_SURFACE, fg=Theme.TEXT,
                      activebackground=Theme.ACCENT, activeforeground=Theme.BG_DARK)
        for size in [8, 10, 12, 14, 16, 18, 20, 24]:
            menu.add_command(label=f"{size}pt", command=lambda s=size: self._apply_font_size(s))
        self.font_size_button.config(menu=menu)
    
    def _apply_font_size(self, size):
        """Apply font size to selected text, preserving bold/italic/underline"""
        # Save state before change
        self._save_undo_state()
        
        try:
            sel_start = self.text_area.index(tk.SEL_FIRST)
            sel_end = self.text_area.index(tk.SEL_LAST)
        except tk.TclError:
            # No selection, apply to current line
            try:
                sel_start = self.text_area.index("insert linestart")
                sel_end = self.text_area.index("insert lineend")
            except tk.TclError:
                return
        
        # Get current formatting at selection start
        current_tags = list(self.text_area.tag_names(sel_start))
        has_bold, has_italic, has_underline, _ = self._get_current_format_state(current_tags)
        
        # Remove all formatting tags from selection
        self._remove_all_format_tags(sel_start, sel_end)
        
        # Apply the appropriate compound tag with new size and preserved style
        new_tag = self._get_format_tag_name(has_bold, has_italic, has_underline, size)
        if new_tag:
            self.text_area.tag_add(new_tag, sel_start, sel_end)
        
        # Re-select to maintain selection (only if we had a selection)
        try:
            self.text_area.index(tk.SEL_FIRST)
            self.text_area.tag_add(tk.SEL, sel_start, sel_end)
        except tk.TclError:
            pass
        
        # Update button states
        self._update_format_button_states()
    
    def _create_bullet_list_btn(self, parent):
        """Create bullet list dropdown button with variations"""
        btn = tk.Menubutton(
            parent,
            text="•",
            font=('Consolas', 12),
            bg=Theme.BG_SURFACE,
            fg=Theme.TEXT,
            activebackground=Theme.BG_OVERLAY,
            activeforeground=Theme.TEXT,
            borderwidth=0,
            padx=8,
            pady=2,
            relief=tk.FLAT,
            takefocus=False  # Prevent stealing focus
        )
        btn.pack(side=tk.LEFT, padx=1)
        
        menu = tk.Menu(btn, tearoff=0, bg=Theme.BG_SURFACE, fg=Theme.TEXT,
                      activebackground=Theme.ACCENT, activeforeground=Theme.BG_DARK)
        bullet_variations = [
            ('•', '• '),
            ('◦', '◦ '),
            ('▪', '▪ '),
            ('▫', '▫ '),
            ('-', '- '),
            ('→', '→ '),
        ]
        for symbol, prefix in bullet_variations:
            menu.add_command(label=symbol, command=lambda p=prefix: self._apply_bullet_list(p))
        btn.config(menu=menu)
    
    def _create_numbered_list_btn(self, parent):
        """Create numbered list dropdown button with variations"""
        btn = tk.Menubutton(
            parent,
            text="1.",
            font=('Consolas', 9),
            bg=Theme.BG_SURFACE,
            fg=Theme.TEXT,
            activebackground=Theme.BG_OVERLAY,
            activeforeground=Theme.TEXT,
            borderwidth=0,
            padx=8,
            pady=2,
            relief=tk.FLAT,
            takefocus=False  # Prevent stealing focus
        )
        btn.pack(side=tk.LEFT, padx=1)
        
        menu = tk.Menu(btn, tearoff=0, bg=Theme.BG_SURFACE, fg=Theme.TEXT,
                      activebackground=Theme.ACCENT, activeforeground=Theme.BG_DARK)
        numbered_variations = [
            ('1. 2. 3.', 'number'),
            ('(1) (2) (3)', 'paren'),
            ('1) 2) 3)', 'paren2'),
            ('a. b. c.', 'lower'),
            ('A. B. C.', 'upper'),
            ('i. ii. iii.', 'roman_lower'),
            ('I. II. III.', 'roman_upper'),
        ]
        for label, style in numbered_variations:
            menu.add_command(label=label, command=lambda s=style: self._apply_numbered_list(s))
        btn.config(menu=menu)
    
    def _get_indent_level(self, line_text):
        """Get indent level (number of 4-space indents) from line text"""
        # Count leading spaces, divide by 4 to get indent level
        leading_spaces = len(line_text) - len(line_text.lstrip())
        return leading_spaces // 4
    
    def _get_line_with_indent(self, line_start, indent_level):
        """Get line text with proper indent level"""
        line_end = self.text_area.index(f"{line_start} lineend")
        line_text = self.text_area.get(line_start, line_end)
        # Remove existing indent
        stripped = line_text.lstrip()
        # Add new indent
        indent = '    ' * indent_level  # 4 spaces per level
        return indent + stripped
    
    def _roman_to_int(self, roman):
        """Convert Roman numeral to integer"""
        roman_map = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
        roman = roman.upper()
        result = 0
        prev_value = 0
        
        for char in reversed(roman):
            value = roman_map.get(char, 0)
            if value < prev_value:
                result -= value
            else:
                result += value
            prev_value = value
        
        return result
    
    def _find_last_number_at_level(self, current_line, style, indent_level):
        """Find the last number used at a specific indent level and style"""
        try:
            line_num = int(current_line.split('.')[0])
            last_num = 0
            
            # Search backwards from current line
            for i in range(line_num - 1, 0, -1):
                try:
                    check_line_start = f"{i}.0"
                    check_line_end = f"{i}.end"
                    check_line_text = self.text_area.get(check_line_start, check_line_end)
                    
                    # Check indent level
                    check_indent = self._get_indent_level(check_line_text)
                    
                    # If indent level matches, check if it has the same style
                    if check_indent == indent_level:
                        # Check if it matches the style
                        if style == 'number':
                            match = re.match(r'^\s*(\d+)\.\s', check_line_text)
                            if match:
                                last_num = int(match.group(1))
                                break
                        elif style == 'paren':
                            match = re.match(r'^\s*\((\d+)\)\s', check_line_text)
                            if match:
                                last_num = int(match.group(1))
                                break
                        elif style == 'paren2':
                            match = re.match(r'^\s*(\d+)\)\s', check_line_text)
                            if match:
                                last_num = int(match.group(1))
                                break
                        elif style == 'lower':
                            match = re.match(r'^\s*([a-z])\.\s', check_line_text)
                            if match:
                                last_num = ord(match.group(1)) - ord('a') + 1
                                break
                        elif style == 'upper':
                            match = re.match(r'^\s*([A-Z])\.\s', check_line_text)
                            if match:
                                last_num = ord(match.group(1)) - ord('A') + 1
                                break
                        elif style == 'roman_lower':
                            match = re.match(r'^\s*([ivxlcdm]+)\.\s', check_line_text, re.IGNORECASE)
                            if match:
                                last_num = self._roman_to_int(match.group(1))
                                break
                        elif style == 'roman_upper':
                            match = re.match(r'^\s*([IVXLCDM]+)\.\s', check_line_text)
                            if match:
                                last_num = self._roman_to_int(match.group(1))
                                break
                    elif check_indent < indent_level:
                        # We've gone up a level, stop searching
                        break
                except:
                    continue
            
            return last_num
        except:
            return 0
    
    def _apply_bullet_list(self, bullet_char='• '):
        """Apply bullet list to current line with specified bullet character"""
        # Save state before change
        self._save_undo_state()
        
        try:
            # Get current line
            line_start = self.text_area.index("insert linestart")
            line_end = self.text_area.index("insert lineend")
            
            # Get line content
            line_text = self.text_area.get(line_start, line_end)
            
            # Remove numbered tag if exists
            self.text_area.tag_remove('numbered', line_start, line_end)
            
            # Check if already has bullet (any variation)
            bullet_pattern = re.compile(r'^\s*[•◦▪▫\-\→]\s')
            
            if bullet_pattern.match(line_text):
                # Already has bullet - increase indent level
                current_indent = self._get_indent_level(line_text)
                new_indent = current_indent + 1
                
                # Remove existing bullet
                stripped = re.sub(r'^\s*[•◦▪▫\-\→]\s*', '', line_text)
                # Add new indent and bullet
                indent = '    ' * new_indent
                new_text = indent + bullet_char + stripped
                
                # Replace line
                self.text_area.delete(line_start, line_end)
                self.text_area.insert(line_start, new_text)
                
                # Apply bullet tag
                new_line_start = self.text_area.index("insert linestart")
                new_line_end = self.text_area.index("insert lineend")
                self.text_area.tag_add('bullet', new_line_start, new_line_end)
            else:
                # No bullet yet - add at current indent level
                current_indent = self._get_indent_level(line_text)
                stripped = line_text.lstrip()
                indent = '    ' * current_indent
                
                if stripped:
                    new_text = indent + bullet_char + stripped
                else:
                    new_text = indent + bullet_char
                
                # Replace line
                self.text_area.delete(line_start, line_end)
                self.text_area.insert(line_start, new_text)
                
                # Apply bullet tag
                new_line_start = self.text_area.index("insert linestart")
                new_line_end = self.text_area.index("insert lineend")
                self.text_area.tag_add('bullet', new_line_start, new_line_end)
        except tk.TclError:
            pass
    
    def _apply_numbered_list(self, style='number'):
        """Apply numbered list to current line with specified style"""
        # Save state before change
        self._save_undo_state()
        
        try:
            # Get current line
            line_start = self.text_area.index("insert linestart")
            line_end = self.text_area.index("insert lineend")
            
            # Get line content
            line_text = self.text_area.get(line_start, line_end)
            
            # Remove bullet tag if exists
            self.text_area.tag_remove('bullet', line_start, line_end)
            
            # Check if already has number (any variation)
            numbered_pattern = re.compile(r'^\s*(\d+|[a-z]|[A-Z]|[ivxlcdm]+)\.?\s', re.IGNORECASE)
            
            if numbered_pattern.match(line_text):
                # Already has number - check if same style or different
                current_indent = self._get_indent_level(line_text)
                
                # Check if current number matches the requested style
                current_style_match = self._detect_number_style(line_text)
                
                if current_style_match == style:
                    # Same style - increase indent
                    new_indent = current_indent + 1
                    # Remove existing number
                    stripped = re.sub(r'^\s*(\d+|[a-z]|[A-Z]|[ivxlcdm]+)\.?\s*', '', line_text, flags=re.IGNORECASE)
                    # Find last number at new indent level with same style
                    last_num = self._find_last_number_at_level(line_start, style, new_indent)
                    next_num = last_num + 1
                    prefix = self._get_numbered_prefix(next_num, style)
                    # Add new indent and number
                    indent = '    ' * new_indent
                    new_text = indent + prefix + stripped
                else:
                    # Different style - keep same indent, change style
                    # Find last number at current indent level with new style
                    last_num = self._find_last_number_at_level(line_start, style, current_indent)
                    next_num = last_num + 1
                    prefix = self._get_numbered_prefix(next_num, style)
                    # Remove existing number
                    stripped = re.sub(r'^\s*(\d+|[a-z]|[A-Z]|[ivxlcdm]+)\.?\s*', '', line_text, flags=re.IGNORECASE)
                    # Add indent and new number
                    indent = '    ' * current_indent
                    new_text = indent + prefix + stripped
                
                # Replace line
                self.text_area.delete(line_start, line_end)
                self.text_area.insert(line_start, new_text)
                
                # Apply numbered tag
                new_line_start = self.text_area.index("insert linestart")
                new_line_end = self.text_area.index("insert lineend")
                self.text_area.tag_add('numbered', new_line_start, new_line_end)
            else:
                # No number yet - add at current indent level
                current_indent = self._get_indent_level(line_text)
                stripped = line_text.lstrip()
                
                # Find last number at current indent level with same style
                last_num = self._find_last_number_at_level(line_start, style, current_indent)
                next_num = last_num + 1
                prefix = self._get_numbered_prefix(next_num, style)
                
                indent = '    ' * current_indent
                if stripped:
                    new_text = indent + prefix + stripped
                else:
                    new_text = indent + prefix
                
                # Replace line
                self.text_area.delete(line_start, line_end)
                self.text_area.insert(line_start, new_text)
                
                # Apply numbered tag
                new_line_start = self.text_area.index("insert linestart")
                new_line_end = self.text_area.index("insert lineend")
                self.text_area.tag_add('numbered', new_line_start, new_line_end)
        except tk.TclError:
            pass
    
    def _detect_number_style(self, line_text):
        """Detect the style of number in a line"""
        stripped = line_text.strip()
        if re.match(r'^\d+\.\s', stripped):
            return 'number'
        elif re.match(r'^\(\d+\)\s', stripped):
            return 'paren'
        elif re.match(r'^\d+\)\s', stripped):
            return 'paren2'
        elif re.match(r'^[a-z]\.\s', stripped):
            return 'lower'
        elif re.match(r'^[A-Z]\.\s', stripped):
            return 'upper'
        elif re.match(r'^[ivxlcdm]+\.\s', stripped, re.IGNORECASE):
            # Check if uppercase
            if re.match(r'^[IVXLCDM]+\.\s', stripped):
                return 'roman_upper'
            else:
                return 'roman_lower'
        return 'number'  # default
    
    def _get_numbered_prefix(self, num, style):
        """Get numbered prefix based on style"""
        if style == 'number':
            return f'{num}. '
        elif style == 'paren':
            return f'({num}) '
        elif style == 'paren2':
            return f'{num}) '
        elif style == 'lower':
            # Convert to lowercase letter (a=1, b=2, etc.)
            letter = chr(ord('a') + (num - 1) % 26)
            return f'{letter}. '
        elif style == 'upper':
            # Convert to uppercase letter
            letter = chr(ord('A') + (num - 1) % 26)
            return f'{letter}. '
        elif style == 'roman_lower':
            return f'{self._to_roman(num).lower()}. '
        elif style == 'roman_upper':
            return f'{self._to_roman(num)}. '
        else:
            return f'{num}. '
    
    def _to_roman(self, num):
        """Convert number to Roman numeral"""
        val = [
            1000, 900, 500, 400,
            100, 90, 50, 40,
            10, 9, 5, 4,
            1
        ]
        syb = [
            "M", "CM", "D", "CD",
            "C", "XC", "L", "XL",
            "X", "IX", "V", "IV",
            "I"
        ]
        roman_num = ''
        i = 0
        while num > 0:
            for _ in range(num // val[i]):
                roman_num += syb[i]
                num -= val[i]
            i += 1
        return roman_num
    
    def _apply_highlight(self, color):
        """Apply highlight color to selected text only (not full lines, breaks at newlines)"""
        # Save state before change
        self._save_undo_state()
        
        try:
            sel_start = self.text_area.index(tk.SEL_FIRST)
            sel_end = self.text_area.index(tk.SEL_LAST)
            
            # Parse line and column from indices
            start_line, start_col = map(int, sel_start.split('.'))
            end_line, end_col = map(int, sel_end.split('.'))
            
            # Remove other highlight tags first from the exact selection
            for c in ['yellow', 'green', 'pink', 'blue']:
                self.text_area.tag_remove(f'highlight_{c}', sel_start, sel_end)
            
            # Apply highlight per line to ensure it breaks at newlines
            if start_line == end_line:
                # Single line selection - apply directly
                self.text_area.tag_add(f'highlight_{color}', sel_start, sel_end)
            else:
                # Multi-line selection - apply per line to ensure breaks at newlines
                # First line: from start_col to end of line
                self.text_area.tag_add(f'highlight_{color}', 
                                     f'{start_line}.{start_col}', 
                                     f'{start_line}.end')
                # Middle lines: entire line
                for line in range(start_line + 1, end_line):
                    self.text_area.tag_add(f'highlight_{color}', 
                                         f'{line}.0', 
                                         f'{line}.end')
                # Last line: from start to end_col
                self.text_area.tag_add(f'highlight_{color}', 
                                     f'{end_line}.0', 
                                     f'{end_line}.{end_col}')
            
            # Re-select to maintain selection
            self.text_area.tag_add(tk.SEL, sel_start, sel_end)
            
            # Update button states
            self._update_format_button_states()
        except tk.TclError:
            pass
    
    def _remove_highlight(self):
        """Remove highlight from selected text"""
        # Save state before change
        self._save_undo_state()
        
        try:
            sel_start = self.text_area.index(tk.SEL_FIRST)
            sel_end = self.text_area.index(tk.SEL_LAST)
            
            for c in ['yellow', 'green', 'pink', 'blue']:
                self.text_area.tag_remove(f'highlight_{c}', sel_start, sel_end)
            
            # Re-select to maintain selection
            self.text_area.tag_add(tk.SEL, sel_start, sel_end)
            
            # Update button states
            self._update_format_button_states()
        except tk.TclError:
            pass
    
    def _clear_format(self):
        """Clear all formatting from selected text"""
        # Save state before change
        self._save_undo_state()
        
        try:
            sel_start = self.text_area.index(tk.SEL_FIRST)
            sel_end = self.text_area.index(tk.SEL_LAST)
            
            # Remove all formatting tags
            tags_to_remove = ['bold', 'italic', 'underline', 'bold_italic', 
                            'bold_underline', 'italic_underline', 'bold_italic_underline',
                            'highlight_yellow', 'highlight_green', 'highlight_pink', 'highlight_blue',
                            'bullet', 'numbered']
            
            # Add font size tags
            for size in [8, 10, 12, 14, 16, 18, 20, 24]:
                tags_to_remove.append(f'font_{size}')
            
            for tag in tags_to_remove:
                self.text_area.tag_remove(tag, sel_start, sel_end)
            
            # Re-select to maintain selection
            self.text_area.tag_add(tk.SEL, sel_start, sel_end)
            
            # Update button states
            self._update_format_button_states()
        except tk.TclError:
            pass
    
    # Find and Replace
    def _show_find_dialog(self, show_replace=False):
        """Show find and replace dialog"""
        if hasattr(self, 'find_dialog') and self.find_dialog.winfo_exists():
            self.find_dialog.lift()
            self.find_entry.focus_set()
            return
        
        self.find_dialog = tk.Toplevel(self.root)
        self.find_dialog.title("Find and Replace" if show_replace else "Find")
        self.find_dialog.configure(bg=Theme.BG_DARK)
        self.find_dialog.geometry("400x180" if show_replace else "400x120")
        self.find_dialog.resizable(False, False)
        self.find_dialog.transient(self.root)
        
        # Find row
        find_frame = tk.Frame(self.find_dialog, bg=Theme.BG_DARK)
        find_frame.pack(fill=tk.X, padx=15, pady=(15, 5))
        
        tk.Label(find_frame, text="Find:", bg=Theme.BG_DARK, fg=Theme.TEXT,
                font=('Consolas', 10)).pack(side=tk.LEFT)
        
        self.find_entry = tk.Entry(find_frame, bg=Theme.BG_SURFACE, fg=Theme.TEXT,
                                  insertbackground=Theme.TEXT, font=('Consolas', 10),
                                  relief=tk.FLAT, width=30)
        self.find_entry.pack(side=tk.LEFT, padx=(10, 0), ipady=3)
        self.find_entry.bind('<Return>', lambda e: self._find_next())
        
        # Replace row (if show_replace)
        if show_replace:
            replace_frame = tk.Frame(self.find_dialog, bg=Theme.BG_DARK)
            replace_frame.pack(fill=tk.X, padx=15, pady=5)
            
            tk.Label(replace_frame, text="Replace:", bg=Theme.BG_DARK, fg=Theme.TEXT,
                    font=('Consolas', 10)).pack(side=tk.LEFT)
            
            self.replace_entry = tk.Entry(replace_frame, bg=Theme.BG_SURFACE, fg=Theme.TEXT,
                                         insertbackground=Theme.TEXT, font=('Consolas', 10),
                                         relief=tk.FLAT, width=27)
            self.replace_entry.pack(side=tk.LEFT, padx=(10, 0), ipady=3)
        
        # Options row
        options_frame = tk.Frame(self.find_dialog, bg=Theme.BG_DARK)
        options_frame.pack(fill=tk.X, padx=15, pady=5)
        
        self.match_case_var = tk.BooleanVar(value=False)
        tk.Checkbutton(options_frame, text="Match case", variable=self.match_case_var,
                      bg=Theme.BG_DARK, fg=Theme.TEXT, selectcolor=Theme.BG_SURFACE,
                      activebackground=Theme.BG_DARK, activeforeground=Theme.TEXT,
                      font=('Consolas', 9)).pack(side=tk.LEFT)
        
        # Buttons row
        btn_frame = tk.Frame(self.find_dialog, bg=Theme.BG_DARK)
        btn_frame.pack(fill=tk.X, padx=15, pady=10)
        
        btn_style = {'bg': Theme.BG_SURFACE, 'fg': Theme.TEXT, 'font': ('Consolas', 9),
                    'relief': tk.FLAT, 'padx': 10, 'pady': 3,
                    'activebackground': Theme.BG_OVERLAY, 'activeforeground': Theme.TEXT}
        
        tk.Button(btn_frame, text="Find Next", command=self._find_next, **btn_style).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Find All", command=self._find_all, **btn_style).pack(side=tk.LEFT, padx=2)
        
        if show_replace:
            tk.Button(btn_frame, text="Replace", command=self._replace, **btn_style).pack(side=tk.LEFT, padx=2)
            tk.Button(btn_frame, text="Replace All", command=self._replace_all, **btn_style).pack(side=tk.LEFT, padx=2)
        
        tk.Button(btn_frame, text="Close", command=self._close_find_dialog, **btn_style).pack(side=tk.RIGHT, padx=2)
        
        self.find_entry.focus_set()
        self.find_match_idx = 0
        self.find_matches = []
    
    def _close_find_dialog(self):
        """Close find dialog and clear highlights"""
        self.text_area.tag_remove('find_match', '1.0', tk.END)
        self.text_area.tag_remove('find_current', '1.0', tk.END)
        if hasattr(self, 'find_dialog'):
            self.find_dialog.destroy()
    
    def _find_all(self):
        """Find and highlight all matches"""
        search_term = self.find_entry.get()
        if not search_term:
            return
        
        # Clear previous highlights
        self.text_area.tag_remove('find_match', '1.0', tk.END)
        self.text_area.tag_remove('find_current', '1.0', tk.END)
        
        self.find_matches = []
        start_pos = '1.0'
        
        nocase = not self.match_case_var.get()
        
        while True:
            pos = self.text_area.search(search_term, start_pos, tk.END, nocase=nocase)
            if not pos:
                break
            
            end_pos = f"{pos}+{len(search_term)}c"
            self.find_matches.append((pos, end_pos))
            self.text_area.tag_add('find_match', pos, end_pos)
            start_pos = end_pos
        
        if self.find_matches:
            self.find_match_idx = 0
            self._highlight_current_match()
            self._set_status(f"Found {len(self.find_matches)} matches")
        else:
            self._set_status("No matches found")
    
    def _find_next(self):
        """Find next occurrence"""
        if not self.find_matches:
            self._find_all()
            return
        
        if self.find_matches:
            self.find_match_idx = (self.find_match_idx + 1) % len(self.find_matches)
            self._highlight_current_match()
    
    def _highlight_current_match(self):
        """Highlight current match and scroll to it"""
        if not self.find_matches:
            return
        
        # Clear previous current highlight
        self.text_area.tag_remove('find_current', '1.0', tk.END)
        
        # Highlight current
        pos, end_pos = self.find_matches[self.find_match_idx]
        self.text_area.tag_add('find_current', pos, end_pos)
        self.text_area.see(pos)
        self.text_area.mark_set(tk.INSERT, pos)
        
        self._set_status(f"Match {self.find_match_idx + 1} of {len(self.find_matches)}")
    
    def _replace(self):
        """Replace current match"""
        if not hasattr(self, 'replace_entry') or not self.find_matches:
            return
        
        replace_term = self.replace_entry.get()
        pos, end_pos = self.find_matches[self.find_match_idx]
        
        self.text_area.delete(pos, end_pos)
        self.text_area.insert(pos, replace_term)
        
        # Re-find all to update positions
        self._find_all()
    
    def _replace_all(self):
        """Replace all matches"""
        if not hasattr(self, 'replace_entry'):
            return
        
        search_term = self.find_entry.get()
        replace_term = self.replace_entry.get()
        
        if not search_term:
            return
        
        content = self.text_area.get('1.0', tk.END)
        
        if self.match_case_var.get():
            new_content = content.replace(search_term, replace_term)
            count = content.count(search_term)
        else:
            import re
            pattern = re.compile(re.escape(search_term), re.IGNORECASE)
            matches = pattern.findall(content)
            count = len(matches)
            new_content = pattern.sub(replace_term, content)
        
        self.text_area.delete('1.0', tk.END)
        self.text_area.insert('1.0', new_content)
        
        self._set_status(f"Replaced {count} occurrences")
        self.find_matches = []
    
    # Drawing mode
    def _toggle_draw_mode(self):
        """Toggle drawing/highlight mode"""
        if self.draw_mode:
            self._exit_draw_mode()
        else:
            self._enter_draw_mode()
    
    def _enter_draw_mode(self):
        """Enter drawing mode - drawing overlay stays visible"""
        self.draw_mode = True
        
        # Ensure drawing overlay exists and is visible
        if not self.drawing_overlay:
            self.drawing_overlay = DrawingOverlay(self.text_area, self.text_frame)
        
        # Load saved strokes for current tab if any
        if self.active_tab_id and self.active_tab_id in self.tabs:
            tab = self.tabs[self.active_tab_id]
            if hasattr(tab, 'drawing_data') and tab.drawing_data:
                self.drawing_overlay.set_strokes_data(tab.drawing_data)
        
        # Show overlay (if not already shown)
        if not self.drawing_overlay.active:
            self.drawing_overlay.show()
        
        # Enable drawing events
        self.drawing_overlay.enable_drawing()
        
        # Show drawing toolbar
        self._show_draw_toolbar()
        self._set_status("Draw Mode - Click and drag to draw. Press ESC to exit.")
    
    def _exit_draw_mode(self):
        """Exit drawing mode - keep drawings visible"""
        self.draw_mode = False

        # Save drawings to current tab before exiting
        if self.drawing_overlay and self.active_tab_id and self.active_tab_id in self.tabs:
            tab = self.tabs[self.active_tab_id]
            tab.drawing_data = self.drawing_overlay.serialize()
            # Disable drawing events (but keep drawings visible)
            self.drawing_overlay.disable_drawing()

        # Hide drawing toolbar but keep overlay visible
        if hasattr(self, 'draw_toolbar') and self.draw_toolbar:
            self.draw_toolbar.destroy()
            self.draw_toolbar = None

        self._set_status("Draw Mode exited - drawings remain visible")
        
        self._set_status("Ready - Click pet area below to throw ball")
    
    def _show_draw_toolbar(self):
        """Show drawing toolbar"""
        self.draw_toolbar = tk.Frame(self.root, bg=Theme.BG_SURFACE)
        self.draw_toolbar.pack(fill=tk.X, padx=10, pady=2, before=self.main_frame.master)
        
        tk.Label(self.draw_toolbar, text="Draw Mode:", bg=Theme.BG_SURFACE, 
                fg=Theme.TEXT, font=('Consolas', 9)).pack(side=tk.LEFT, padx=5)
        
        # Store button references for visual feedback
        self.color_buttons = {}
        self.size_buttons = {}
        
        # Color buttons
        colors = [('Yellow', 'yellow'), ('Green', 'green'), ('Pink', 'pink'), 
                 ('Red', 'red'), ('Blue', 'blue')]
        
        for name, color in colors:
            bg_color = DrawingOverlay.COLORS.get(color, '#fff')
            btn = tk.Button(
                self.draw_toolbar, text="  ", bg=bg_color,
                relief=tk.FLAT, padx=5, pady=2, borderwidth=2,
                command=lambda c=color: self._set_draw_color(c)
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.color_buttons[color] = btn
        
        # Set default color (yellow) as selected
        if 'yellow' in self.color_buttons:
            self.color_buttons['yellow'].config(relief=tk.SOLID, highlightthickness=1, highlightbackground=Theme.ACCENT)
        
        # Width options
        tk.Label(self.draw_toolbar, text="  Size:", bg=Theme.BG_SURFACE,
                fg=Theme.TEXT, font=('Consolas', 9)).pack(side=tk.LEFT, padx=(10, 5))
        
        for size in [2, 4, 8]:
            btn = tk.Button(
                self.draw_toolbar, text=str(size), bg=Theme.BG_DARK, fg=Theme.TEXT,
                relief=tk.FLAT, padx=6, pady=2, borderwidth=2,
                activebackground=Theme.BG_OVERLAY, activeforeground=Theme.TEXT,
                command=lambda s=size: self._set_draw_width(s)
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.size_buttons[size] = btn
        
        # Set default size (4) as selected
        if 4 in self.size_buttons:
            self.size_buttons[4].config(relief=tk.SOLID, highlightthickness=1, highlightbackground=Theme.ACCENT, 
                                        bg=Theme.ACCENT, fg=Theme.BG_DARK)
        
        # Erase button
        ttk.Separator(self.draw_toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        self.erase_button = tk.Button(
            self.draw_toolbar, text="Erase", bg=Theme.BG_DARK, fg=Theme.TEXT,
            relief=tk.FLAT, padx=8, pady=2, borderwidth=2,
            activebackground=Theme.BG_OVERLAY, activeforeground=Theme.TEXT,
            command=self._toggle_erase_mode
        )
        self.erase_button.pack(side=tk.LEFT, padx=2)
        
        # Ensure drawing overlay uses default values
        if self.drawing_overlay:
            self.drawing_overlay.set_color('yellow')
            self.drawing_overlay.set_width(4)
            self.drawing_overlay.set_erase_mode(False)
        
        # Clear and Exit buttons
        tk.Button(
            self.draw_toolbar, text="Clear", bg=Theme.BG_DARK, fg=Theme.TEXT,
            relief=tk.FLAT, padx=8, pady=2,
            activebackground=Theme.BG_OVERLAY, activeforeground=Theme.TEXT,
            command=self._clear_drawing
        ).pack(side=tk.LEFT, padx=(20, 2))
        
        tk.Button(
            self.draw_toolbar, text="Exit Draw", bg=Theme.ACCENT_PEACH, fg=Theme.BG_DARK,
            relief=tk.FLAT, padx=8, pady=2,
            activebackground=Theme.ACCENT, activeforeground=Theme.BG_DARK,
            command=self._exit_draw_mode
        ).pack(side=tk.LEFT, padx=2)
        
        # Bind ESC to exit draw mode
        self.root.bind('<Escape>', lambda e: self._exit_draw_mode() if self.draw_mode else None)
    
    def _set_draw_color(self, color):
        """Set drawing color and update visual indicator"""
        if self.drawing_overlay:
            self.drawing_overlay.set_color(color)
        
        # Update visual indicator - remove highlight from all, add to selected
        if hasattr(self, 'color_buttons'):
            for c, btn in self.color_buttons.items():
                if c == color:
                    btn.config(relief=tk.SOLID, highlightthickness=1, highlightbackground=Theme.ACCENT)
                else:
                    btn.config(relief=tk.FLAT, highlightthickness=0)
        
        # Deactivate erase mode when color is selected
        if hasattr(self, 'erase_button') and self.drawing_overlay and self.drawing_overlay.erasing:
            self.erase_button.config(relief=tk.FLAT, highlightthickness=0,
                                   bg=Theme.BG_DARK, fg=Theme.TEXT)
    
    def _set_draw_width(self, width):
        """Set drawing stroke width and update visual indicator"""
        if self.drawing_overlay:
            self.drawing_overlay.set_width(width)
        
        # Update visual indicator - remove highlight from all, add to selected
        if hasattr(self, 'size_buttons'):
            for s, btn in self.size_buttons.items():
                if s == width:
                    btn.config(relief=tk.SOLID, highlightthickness=1, highlightbackground=Theme.ACCENT, 
                              bg=Theme.ACCENT, fg=Theme.BG_DARK)
                else:
                    btn.config(relief=tk.FLAT, highlightthickness=0, 
                              bg=Theme.BG_DARK, fg=Theme.TEXT)
    
    def _toggle_erase_mode(self):
        """Toggle erase mode"""
        if self.drawing_overlay:
            current_erase = self.drawing_overlay.erasing
            self.drawing_overlay.set_erase_mode(not current_erase)
            
            # Update erase button visual
            if hasattr(self, 'erase_button'):
                if not current_erase:
                    # Activate erase mode
                    self.erase_button.config(relief=tk.SOLID, highlightthickness=1, 
                                           highlightbackground=Theme.ACCENT,
                                           bg=Theme.ACCENT_PEACH, fg=Theme.BG_DARK)
                else:
                    # Deactivate erase mode
                    self.erase_button.config(relief=tk.FLAT, highlightthickness=0,
                                           bg=Theme.BG_DARK, fg=Theme.TEXT)
    
    def _clear_drawing(self):
        """Clear all drawings"""
        if self.drawing_overlay:
            self.drawing_overlay.clear()
            # Also clear from current tab
            if self.active_tab_id and self.active_tab_id in self.tabs:
                tab = self.tabs[self.active_tab_id]
                tab.drawing_data = ""

    def _setup_statusbar(self):
        """Setup status bar"""
        statusbar = ttk.Frame(self.root, style='Dark.TFrame')
        statusbar.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.status_label = ttk.Label(statusbar, text="Ready - Click pet area below to throw ball", style='Dark.TLabel')
        self.status_label.pack(side=tk.LEFT)
        
        self.pet_count_label = ttk.Label(statusbar, text="Pets: 0", style='Dark.TLabel')
        self.pet_count_label.pack(side=tk.RIGHT)
        
        self.line_col_label = ttk.Label(statusbar, text="Ln 1, Col 1", style='Dark.TLabel')
        self.line_col_label.pack(side=tk.RIGHT, padx=20)
    
    def _init_pets(self):
        """Initialize pets - spawn default pets: akita dog, red fox, black panda, green snake"""
        # Balls will be created when thrown, not at initialization
        # Load pet icons for menus
        self._load_pet_icons()
        # Add default pets with slight delay for smooth appearance
        self.root.after(100, lambda: self._add_pet('dog_akita'))
        self.root.after(200, lambda: self._add_pet('fox_red'))
        self.root.after(300, lambda: self._add_pet('panda_black'))
        self.root.after(400, lambda: self._add_pet('snake_green'))
    
    def _load_pet_icons(self):
        """Load small icons for pet menu"""
        self.pet_icons = {}
        if not PIL_AVAILABLE:
            return
        
        assets_path = Path(__file__).parent / 'assets' / 'pets'
        
        for pet_key, config in Pet.PET_CONFIGS.items():
            try:
                icon_path = assets_path / config['folder'] / config['idle']
                if icon_path.exists():
                    img = Image.open(str(icon_path))
                    # Get first frame and resize to small icon (16x16)
                    img = img.convert('RGBA')
                    # Resize while maintaining aspect ratio
                    img.thumbnail((20, 20), Image.NEAREST)
                    self.pet_icons[pet_key] = ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"Could not load icon for {pet_key}: {e}")
    
    def _create_pet_submenus(self, parent_menu):
        """Create cascading submenus for each animal type with color variants"""
        menu_structure = Pet.get_pet_menu_structure()
        
        for animal, variants in menu_structure.items():
            # Create submenu for this animal
            animal_menu = tk.Menu(parent_menu, tearoff=0, bg=Theme.BG_SURFACE, fg=Theme.TEXT,
                                 activebackground=Theme.ACCENT, activeforeground=Theme.BG_DARK)
            parent_menu.add_cascade(label=animal, menu=animal_menu)
            
            # Add color variants
            for variant in variants:
                pet_key = variant['key']
                color_name = variant['color']
                color_hex = variant['color_hex']
                
                # Try to get icon for this pet
                icon = self.pet_icons.get(pet_key) if hasattr(self, 'pet_icons') else None
                
                if icon:
                    animal_menu.add_command(
                        label=f"  {color_name}",
                        image=icon,
                        compound=tk.LEFT,
                        command=lambda k=pet_key: self._add_pet(k)
                    )
                else:
                    # Create a colored indicator if no icon
                    animal_menu.add_command(
                        label=f"● {color_name}",
                        foreground=color_hex,
                        command=lambda k=pet_key: self._add_pet(k)
                    )
    
    def _add_pet(self, pet_type):
        """Add a new pet"""
        assets_path = Path(__file__).parent / 'assets' / 'pets'
        
        try:
            width = self.pet_canvas.winfo_width()
        except:
            width = 800
        
        if width < 10:
            width = 800
        
        height = self.pet_height
        ground_y = height - 5
        
        pet = Pet(self.pet_canvas, pet_type=pet_type, assets_path=assets_path)
        pet.set_bounds(width, height, ground_y)
        pet.x = random.randint(50, max(100, width - 50))
        pet.y = ground_y
        
        self.pets.append(pet)
        self._update_pet_count()
        
        # Get display name for status message
        config = Pet.PET_CONFIGS.get(pet_type, {})
        display_name = f"{config.get('color', '')} {config.get('animal', pet_type)}"
        self._set_status(f"Added {display_name}!")
    
    def _remove_pet(self):
        """Remove the last pet"""
        if self.pets:
            self.pets.pop()
            self.pet_canvas.delete("pet")
            self._update_pet_count()
            self._set_status("Removed pet")
    
    def _remove_all_pets(self):
        """Remove all pets"""
        self.pets.clear()
        self.pet_canvas.delete("pet")
        self.pet_canvas.delete("ball")
        self._update_pet_count()
        self._set_status("All pets removed")
    
    def _throw_ball_at(self, x, y):
        """Throw ball at clicked position - creates new ball, pets will choose nearest themselves"""
        if not self.pets:
            return

        ground_y = self.pet_height - 5
        
        # Create new ball and add to list
        new_ball = Ball(self.pet_canvas)
        new_ball.throw(x, y, ground_y)
        self.balls.append(new_ball)

        # Don't force pets to chase - they will choose nearest ball themselves in update()
        # This ensures pets prioritize nearest ball, not the last thrown one

        self._set_status("Ball thrown!")
    
    def _show_add_pet_menu(self):
        """Show popup menu to add pets with cascading submenus for each animal"""
        menu = tk.Menu(self.root, tearoff=0, bg=Theme.BG_SURFACE, fg=Theme.TEXT,
                      activebackground=Theme.ACCENT, activeforeground=Theme.BG_DARK)
        
        # Create cascading submenus for each animal type
        self._create_pet_submenus(menu)
        
        try:
            menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())
        finally:
            menu.grab_release()
    
    def _animate(self):
        """Main animation loop - 50ms for smooth animation"""
        if not self.animation_running:
            return
        
        dt = 50  # 50ms per frame
        
        try:
            canvas_width = self.pet_canvas.winfo_width()
        except:
            canvas_width = 800
        
        # Update pet bounds (in case window was resized)
        ground_y = self.pet_height - 5
        for pet in self.pets:
            pet.set_bounds(canvas_width, self.pet_height, ground_y)
        
        # Clear previous drawings
        self.pet_canvas.delete("pet")
        self.pet_canvas.delete("ball")
        
        # Update all balls
        balls_to_remove = []
        for ball in self.balls:
            if ball.visible:
                ball.update()
                
                # Check collision with all pets - first come first served
                ball_caught = False
                closest_pet = None
                closest_distance = 35  # Catch radius
                
                # Find the closest pet that can catch this ball
                for pet in self.pets:
                    # Skip if pet is already holding a ball (in WITH_BALL state)
                    # Pet must finish WITH_BALL animation before catching another ball
                    if pet.has_ball and pet.state == Pet.WITH_BALL:
                        continue
                    
                    # Check distance for pets chasing this specific ball
                    if pet.state in [Pet.RUN, Pet.WALK] and pet.target_ball_id == ball.unique_id:
                        distance = pet.get_distance_to(ball.x, ball.y)
                        if distance < closest_distance:
                            closest_distance = distance
                            closest_pet = pet
                
                # Only the closest pet catches the ball (first come first served)
                if closest_pet is not None:
                    closest_pet.has_ball = True
                    closest_pet._change_state(Pet.WITH_BALL)
                    closest_pet.state_duration = 1500  # Animation duration
                    # Clear target ball ID for this pet
                    closest_pet.target_ball_id = None
                    # Also clear target for other pets chasing this ball
                    for pet in self.pets:
                        if pet.target_ball_id == ball.unique_id:
                            pet.target_ball_id = None
                            # If pet was running, change to idle
                            if pet.state == Pet.RUN:
                                pet._change_state(Pet.IDLE)
                    ball.hide()
                    balls_to_remove.append(ball)
                    self._set_status("Ball caught!")
                    ball_caught = True
                
                # Draw ball if still visible and not caught
                if ball.visible and not ball_caught:
                    ball.draw()
        
        # Remove caught balls from list
        for ball in balls_to_remove:
            if ball in self.balls:
                self.balls.remove(ball)
        
        # Update and draw pets - pass available balls so they can choose nearest
        for pet in self.pets:
            pet.update(dt, available_balls=self.balls)
            pet.draw()
        
        # Schedule next frame
        self.root.after(50, self._animate)
    
    def _bind_events(self):
        """Bind keyboard events"""
        # File shortcuts
        self.root.bind('<Control-n>', lambda e: self.new_file())
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_file())
        self.root.bind('<Control-Shift-s>', lambda e: self.save_as_file())
        self.root.bind('<Control-Shift-S>', lambda e: self.save_as_file())
        self.root.bind('<Control-a>', lambda e: self._select_all())
        
        # Undo/Redo shortcuts
        self.root.bind('<Control-z>', lambda e: self._undo())
        self.root.bind('<Control-y>', lambda e: self._redo())
        self.root.bind('<Control-Shift-z>', lambda e: self._redo())
        
        # Formatting shortcuts - bind to both root and text_area for reliable capture
        self.root.bind('<Control-b>', self._toggle_bold)
        self.root.bind('<Control-i>', self._toggle_italic)
        self.root.bind('<Control-u>', self._toggle_underline)
        self.text_area.bind('<Control-b>', self._toggle_bold)
        self.text_area.bind('<Control-i>', self._toggle_italic)
        self.text_area.bind('<Control-u>', self._toggle_underline)
        
        # Find shortcut
        self.root.bind('<Control-f>', lambda e: self._show_find_dialog())
        self.root.bind('<Control-h>', lambda e: self._show_find_dialog(show_replace=True))

        self.text_area.bind('<<Modified>>', self._on_text_modified)
        self.text_area.bind('<KeyRelease>', self._on_key_release)
        self.text_area.bind('<ButtonRelease>', self._on_button_release)
        
        # Bind Enter key for auto-continue bullet/numbered lists
        self.text_area.bind('<Return>', self._handle_enter_key)
        
        # Bind selection change to update format button states
        self.text_area.bind('<<Selection>>', lambda e: self._update_format_button_states())

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _on_key_release(self, event=None):
        """Handle key release - update line/col and format states"""
        self._update_line_col()
        self._update_format_button_states()
        # Save state for undo when text is typed (but not during undo/redo)
        if not self.is_undoing and event and event.keysym not in ['Control_L', 'Control_R', 'Shift_L', 'Shift_R', 'Alt_L', 'Alt_R']:
            self._schedule_text_undo_save()
    
    def _on_button_release(self, event=None):
        """Handle button release - update line/col and format states"""
        self._update_line_col()
        self._update_format_button_states()
    
    def _schedule_text_undo_save(self):
        """Schedule saving undo state for text changes (debounced)"""
        if hasattr(self, '_text_undo_timer'):
            self.root.after_cancel(self._text_undo_timer)
        self._text_undo_timer = self.root.after(500, self._save_undo_state)
    
    def _on_text_modified(self, event=None):
        if self.text_area.edit_modified():
            # Mark current tab as modified
            if self.active_tab_id and self.active_tab_id in self.tabs:
                self.tabs[self.active_tab_id].is_modified = True
                self._update_tab_label(self.active_tab_id)
            self._update_title()
            self.text_area.edit_modified(False)

    def _handle_enter_key(self, event):
        """Handle Enter key - auto-continue bullet/numbered lists"""
        try:
            # Get current line before Enter is processed
            line_start = self.text_area.index("insert linestart")
            line_end = self.text_area.index("insert lineend")
            line_text = self.text_area.get(line_start, line_end)
            
            # Get indent level
            indent_level = self._get_indent_level(line_text)
            
            # Check if current line has bullet
            bullet_pattern = re.compile(r'^\s*([•◦▪▫\-\→])\s')
            bullet_match = bullet_pattern.match(line_text)
            
            # Check if current line has number
            numbered_pattern = re.compile(r'^\s*(\d+|[a-z]|[A-Z]|[ivxlcdm]+)\.?\s', re.IGNORECASE)
            numbered_match = numbered_pattern.match(line_text)
            
            # Store info for continuation
            prev_info = {
                'indent_level': indent_level,
                'bullet_match': bullet_match,
                'numbered_match': numbered_match,
                'line_text': line_text
            }
            
            # Let Enter key process normally first
            # We'll insert bullet/number after Enter creates new line
            
            # Use after_idle to run after Enter is processed
            self.root.after_idle(lambda: self._continue_list_after_enter(prev_info))
            
        except Exception:
            pass
        return None  # Allow default Enter behavior
    
    def _continue_list_after_enter(self, prev_info):
        """Continue list on new line after Enter"""
        try:
            # Get the new line (current line after Enter)
            line_start = self.text_area.index("insert linestart")
            line_end = self.text_area.index("insert lineend")
            line_text = self.text_area.get(line_start, line_end)
            
            indent_level = prev_info['indent_level']
            bullet_match = prev_info['bullet_match']
            numbered_match = prev_info['numbered_match']
            
            if bullet_match:
                # Continue bullet list with same indent
                bullet_char = bullet_match.group(1)
                indent = '    ' * indent_level
                
                bullet_pattern_check = re.compile(r'^\s*[•◦▪▫\-\→]\s')
                if not bullet_pattern_check.match(line_text):
                    # Insert bullet at same indent level
                    new_text = indent + bullet_char + ' '
                    self.text_area.delete(line_start, line_end)
                    self.text_area.insert(line_start, new_text)
                    
                    # Apply bullet tag
                    new_line_start = self.text_area.index("insert linestart")
                    new_line_end = self.text_area.index("insert lineend")
                    self.text_area.tag_add('bullet', new_line_start, new_line_end)
            
            elif numbered_match:
                # Continue numbered list with same indent and style
                prev_line_num = int(self.text_area.index("insert -1l linestart").split('.')[0])
                prev_line_start = f"{prev_line_num}.0"
                prev_line_end = f"{prev_line_num}.end"
                prev_line_text = self.text_area.get(prev_line_start, prev_line_end)
                
                # Detect style from previous line
                style = self._detect_number_style(prev_line_text)
                
                # Find last number at same indent level with same style
                last_num = self._find_last_number_at_level(line_start, style, indent_level)
                next_num = last_num + 1
                prefix = self._get_numbered_prefix(next_num, style)
                
                indent = '    ' * indent_level
                numbered_pattern_check = re.compile(r'^\s*(\d+|[a-z]|[A-Z]|[ivxlcdm]+)\.?\s', re.IGNORECASE)
                
                if not numbered_pattern_check.match(line_text):
                    # Insert number at same indent level
                    new_text = indent + prefix
                    self.text_area.delete(line_start, line_end)
                    self.text_area.insert(line_start, new_text)
                    
                    # Apply numbered tag
                    new_line_start = self.text_area.index("insert linestart")
                    new_line_end = self.text_area.index("insert lineend")
                    self.text_area.tag_add('numbered', new_line_start, new_line_end)
        except Exception:
            pass
    
    def _update_line_col(self, event=None):
        pos = self.text_area.index(tk.INSERT)
        line, col = pos.split('.')
        self.line_col_label.config(text=f"Ln {line}, Col {int(col) + 1}")

    def _update_title(self):
        """Update window title based on active tab"""
        if self.active_tab_id and self.active_tab_id in self.tabs:
            tab = self.tabs[self.active_tab_id]
            filename = tab.get_display_name()
        else:
            filename = "Untitled"
        self.root.title(f"{filename} - Notepad with Pets")
    
    def _update_pet_count(self):
        self.pet_count_label.config(text=f"Pets: {len(self.pets)}")
    
    def _set_status(self, message):
        self.status_label.config(text=message)
    
    # File operations
    def new_file(self):
        """Create a new tab"""
        self._create_new_tab()
        self._set_status("New file")

    def open_file(self):
        """Open file in new tab"""
        filetypes = [
            ("All supported", "*.txt *.py *.rtf"),
            ("Text files", "*.txt"),
            ("RTF files", "*.rtf"),
            ("Python files", "*.py"),
            ("All files", "*.*")
        ]
        filepath = filedialog.askopenfilename(filetypes=filetypes)
        
        if filepath:
            try:
                if filepath.lower().endswith('.rtf') and HAS_RTF_SUPPORT:
                    # Open RTF file with formatting
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        rtf_content = f.read()
                    text, tags_info = RTFHandler.import_from_rtf(rtf_content)
                    tab_id = self._create_new_tab(filepath=filepath, content=text)
                    # Apply formatting tags
                    self._apply_tags_from_dict(tags_info)
                    # Load drawing data
                    if tab_id and tab_id in self.tabs:
                        tab = self.tabs[tab_id]
                        tab.drawing_data = self._load_drawing_data(tab)
                        # Redraw if drawing overlay exists
                        if self.drawing_overlay:
                            self.drawing_overlay.set_strokes_data(tab.drawing_data)
                    self._set_status(f"Opened RTF: {os.path.basename(filepath)}")
                else:
                    # Open plain text file
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    tab_id = self._create_new_tab(filepath=filepath, content=content)
                    # Load drawing data
                    if tab_id and tab_id in self.tabs:
                        tab = self.tabs[tab_id]
                        tab.drawing_data = self._load_drawing_data(tab)
                        # Redraw if drawing overlay exists
                        if self.drawing_overlay:
                            self.drawing_overlay.set_strokes_data(tab.drawing_data)
                    self._set_status(f"Opened: {os.path.basename(filepath)}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file:\n{str(e)}")

    def save_file(self):
        """Save current tab"""
        if self.active_tab_id:
            self._save_tab(self.active_tab_id)

    def save_as_file(self):
        """Save current tab as new file"""
        if self.active_tab_id:
            self._save_tab_as(self.active_tab_id)
    
    def _save_tab_as(self, tab_id):
        """Save tab as new file - allows changing name and format"""
        if tab_id not in self.tabs:
            return
        
        # Get current file extension to suggest default
        tab = self.tabs[tab_id]
        current_ext = ".rtf"
        if tab.filepath:
            _, ext = os.path.splitext(tab.filepath)
            if ext:
                current_ext = ext
        
        filetypes = [
            ("RTF files (with formatting)", "*.rtf"),
            ("Text files", "*.txt"),
            ("Python files", "*.py"),
            ("All files", "*.*")
        ]
        
        # Suggest filename based on current tab
        initialfile = tab.name if tab.name else "Untitled"
        if not initialfile.endswith(('.rtf', '.txt', '.py')):
            initialfile = os.path.splitext(initialfile)[0] + current_ext
        
        filepath = filedialog.asksaveasfilename(
            title="Save As",
            defaultextension=current_ext,
            filetypes=filetypes,
            initialfile=initialfile
        )
        
        if filepath:
            tab = self.tabs[tab_id]
            tab.filepath = filepath
            tab.name = os.path.basename(filepath)
            
            # Save current content and drawing if it's the active tab
            if tab_id == self.active_tab_id:
                tab.content = self.text_area.get('1.0', tk.END)
                if self.drawing_overlay:
                    tab.drawing_data = self.drawing_overlay.serialize()
            
            try:
                if filepath.lower().endswith('.rtf') and HAS_RTF_SUPPORT:
                    # Save as RTF with formatting
                    tags_info = self._get_tags_as_dict()
                    rtf_content = RTFHandler.export_to_rtf(tab.content, tags_info)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(rtf_content)
                    self._set_status(f"Saved RTF: {os.path.basename(filepath)}")
                else:
                    # Save as plain text
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(tab.content)
                    self._set_status(f"Saved: {os.path.basename(filepath)}")
                
                # Save drawing data
                self._save_drawing_data(tab)
                
                tab.is_modified = False
                self._update_tab_label(tab_id)
                self._update_title()
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file:\n{str(e)}")

    def _ask_save(self):
        """Ask to save current tab"""
        if not self.active_tab_id or self.active_tab_id not in self.tabs:
            return True
        
        tab = self.tabs[self.active_tab_id]
        if not tab.is_modified:
            return True
            
        result = messagebox.askyesnocancel("Save Changes", "Do you want to save changes?")
        if result is True:
            self.save_file()
            return True
        elif result is False:
            return True
        return False
    
    def _apply_tags_from_dict(self, tags_info):
        """Apply formatting tags from a dictionary to the text area"""
        for tag_name, ranges in tags_info.items():
            for start_idx, end_idx in ranges:
                try:
                    self.text_area.tag_add(tag_name, start_idx, end_idx)
                except tk.TclError:
                    pass
    
    def _get_tags_as_dict(self):
        """Get all formatting tags as a dictionary for RTF export"""
        tags_info = {}
        for tag_name in self._get_all_tags():
            ranges = []
            idx = '1.0'
            while True:
                try:
                    start = self.text_area.tag_nextrange(tag_name, idx)
                    if not start:
                        break
                    ranges.append((start[0], start[1]))
                    idx = start[1]
                except tk.TclError:
                    break
            if ranges:
                tags_info[tag_name] = ranges
        return tags_info
    
    def _get_all_tags(self):
        """Get list of all formatting tags"""
        tags = ['bold', 'italic', 'underline', 'bold_italic', 
                'bold_underline', 'italic_underline', 'bold_italic_underline',
                'highlight_yellow', 'highlight_green', 'highlight_pink', 'highlight_blue',
                'bullet', 'numbered']
        # Add font size tags (plain and compound with styles)
        for size in self.font_sizes:
            tags.append(f'font_{size}')
            for style in ['bold', 'italic', 'underline', 'bold_italic', 
                         'bold_underline', 'italic_underline', 'bold_italic_underline']:
                tags.append(f'font_{size}_{style}')
        return tags
    
    def _save_undo_state(self):
        """Save current state (text + formatting) to unified undo history"""
        if self.is_undoing:
            return
        
        try:
            # Get all text content
            content = self.text_area.get('1.0', tk.END)
            
            # Get all tags and their ranges
            tags_info = {}
            all_tags = self._get_all_tags()
            
            for tag in all_tags:
                ranges = []
                try:
                    start = '1.0'
                    while True:
                        pos = self.text_area.tag_nextrange(tag, start)
                        if not pos:
                            break
                        ranges.append((pos[0], pos[1]))
                        start = pos[1]
                    if ranges:
                        tags_info[tag] = ranges
                except:
                    pass
            
            # Create state
            state = {
                'content': content,
                'tags': tags_info,
                'cursor': self.text_area.index(tk.INSERT)
            }
            
            # Check if state is different from last saved state
            if self.undo_history:
                last_state = self.undo_history[-1]
                if (last_state['content'] == state['content'] and 
                    last_state['tags'] == state['tags']):
                    return  # No change, don't save duplicate
            
            # Clear redo history when new action is performed
            self.redo_history.clear()
            
            # Add new state
            self.undo_history.append(state)
            
            # Limit history size
            if len(self.undo_history) > self.max_history:
                self.undo_history.pop(0)
        except Exception:
            pass
    
    def _save_format_state(self):
        """Legacy function - redirects to _save_undo_state"""
        self._save_undo_state()
    
    def _restore_state(self, state):
        """Restore a saved state (text + formatting)"""
        try:
            self.is_undoing = True
            
            # Disable text widget's built-in undo
            self.text_area.config(undo=False)
            
            # Clear all formatting tags
            all_tags = self._get_all_tags()
            for tag in all_tags:
                self.text_area.tag_remove(tag, '1.0', tk.END)
            
            # Set content
            self.text_area.delete('1.0', tk.END)
            self.text_area.insert('1.0', state['content'].rstrip('\n'))
            
            # Restore tags
            for tag, ranges in state['tags'].items():
                for start, end in ranges:
                    try:
                        self.text_area.tag_add(tag, start, end)
                    except:
                        pass
            
            # Restore cursor position
            try:
                self.text_area.mark_set(tk.INSERT, state['cursor'])
                self.text_area.see(tk.INSERT)
            except:
                pass
            
            # Re-enable text widget's built-in undo and reset it
            self.text_area.config(undo=True)
            self.text_area.edit_reset()
            
            # Update button states
            self._update_format_button_states()
            
            self.is_undoing = False
        except Exception:
            self.is_undoing = False
    
    def _undo(self):
        """Undo last operation - restores previous state from unified history"""
        try:
            if len(self.undo_history) < 2:
                return  # Need at least 2 states (current and previous)
            
            # Save current state to redo history
            current_state = self.undo_history.pop()
            self.redo_history.append(current_state)
            
            # Restore previous state
            previous_state = self.undo_history[-1]
            self._restore_state(previous_state)
            
            self._set_status("Undo")
        except Exception:
            pass
        return 'break'
    
    def _redo(self):
        """Redo last undone operation - restores state from redo history"""
        try:
            if not self.redo_history:
                return
            
            # Get state from redo history
            state = self.redo_history.pop()
            
            # Add to undo history
            self.undo_history.append(state)
            
            # Restore the state
            self._restore_state(state)
            
            self._set_status("Redo")
        except Exception:
            pass
        return 'break'
    
    def _cut(self):
        self.text_area.event_generate("<<Cut>>")
    
    def _copy(self):
        self.text_area.event_generate("<<Copy>>")
    
    def _paste(self):
        self.text_area.event_generate("<<Paste>>")
    
    def _select_all(self):
        self.text_area.tag_add(tk.SEL, '1.0', tk.END)
        return 'break'
    
    def _on_close(self):
        if self.is_modified and not self._ask_save():
            return
        self.animation_running = False
        self.root.destroy()


def main():
    root = tk.Tk()
    app = NotepadWithPets(root)
    root.mainloop()


if __name__ == "__main__":
    main()
