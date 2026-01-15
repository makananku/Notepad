"""
Ball class - Throwable ball with physics
"""

import random


class Ball:
    """Throwable ball with physics - faster and more realistic"""
    
    # Ball color (can be overridden)
    COLOR_FILL = "#a6e3a1"  # Green (from Theme.ACCENT_GREEN)
    COLOR_OUTLINE = "#7bc96f"
    
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
        self.gravity = 0.8
        self.bounce = 0.6
        self.friction = 0.95
        self.radius = 5
    
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
        self.vx = random.uniform(-3, 3)
        self.vy = -8
    
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
                fill=self.COLOR_FILL,
                outline=self.COLOR_OUTLINE,
                width=1,
                tags="ball"
            )
    
    def hide(self):
        """Hide the ball (caught by pet)"""
        self.visible = False
        if self.ball_id:
            self.canvas.delete(self.ball_id)
            self.ball_id = None
