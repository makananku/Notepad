"""
Pet class - Virtual pet with state machine and smooth movement
"""

import random
import math
from pathlib import Path
from .animated_gif import AnimatedGIF

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


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
        # ===== DUCK =====
        'duck_yellow': {
            'animal': 'Duck', 'folder': 'duck', 'color': 'Yellow', 'color_hex': '#FFD700',
            'idle': 'yellow_idle_8fps.gif', 'walk': 'yellow_walk_8fps.gif', 'run': 'yellow_run_8fps.gif',
            'with_ball': 'yellow_with_ball_8fps.gif', 'swipe': 'yellow_swipe_8fps.gif',
        },
        # ===== DENO =====
        'deno_green': {
            'animal': 'Deno', 'folder': 'deno', 'color': 'Green', 'color_hex': '#4CAF50',
            'idle': 'green_idle_8fps.gif', 'walk': 'green_walk_8fps.gif', 'run': 'green_run_8fps.gif',
            'with_ball': 'green_with_ball_8fps.gif', 'swipe': 'green_swipe_8fps.gif',
        },
        # ===== MOD (DENO) =====
        'mod_purple': {
            'animal': 'Mod', 'folder': 'mod', 'color': 'Purple', 'color_hex': '#9B59B6',
            'idle': 'purple_idle_8fps.gif', 'walk': 'purple_walk_8fps.gif', 'run': 'purple_run_8fps.gif',
            'with_ball': 'purple_with_ball_8fps.gif', 'swipe': 'purple_swipe_8fps.gif',
        },
        # ===== ROCKY (ROCKY RACCOON) =====
        'rocky_gray': {
            'animal': 'Rocky', 'folder': 'rocky', 'color': 'Gray', 'color_hex': '#808080',
            'idle': 'gray_idle_8fps.gif', 'walk': 'gray_walk_8fps.gif', 'run': 'gray_run_8fps.gif',
            'with_ball': 'gray_with_ball_8fps.gif', 'swipe': 'gray_swipe_8fps.gif',
        },
        # ===== RUBBER DUCK =====
        'rubberduck_yellow': {
            'animal': 'Rubber Duck', 'folder': 'rubberduck', 'color': 'Yellow', 'color_hex': '#FFD700',
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
        'clippy': 'clippy_black',
    }
    
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
        self.max_speed = 12.0
        self.acceleration = 0.35
        self.friction = 0.88
        
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
            assets_path = Path(__file__).parent.parent / 'assets' / 'pets'
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
                # Chance to climb wall
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
            self.vx *= 0.5
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
        min_y = 50
        max_y = int(self.ground_y * 0.6)
        self.climb_target_y = random.randint(min_y, max(min_y + 50, max_y))
        self._change_state(self.CLIMB_UP)
        self.state_duration = 8000
    
    def _update_climb_up(self, dt):
        """Climbing up the wall"""
        dy = self.climb_target_y - self.y
        
        if abs(dy) < 10 or self.state_timer >= self.state_duration:
            # Start climbing down or rest
            if random.random() < 0.3:
                self._change_state(self.CLIMB_DOWN)
            else:
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
