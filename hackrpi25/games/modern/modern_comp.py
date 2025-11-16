import pygame
import sys

pygame.init()

# ---------- Constants ----------
WIDTH, HEIGHT = 800, 600
TICKRATE = 60
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
FPS = pygame.time.Clock()
FPS.tick(TICKRATE)
pygame.display.set_caption("Old Style Terminal")

FONT = pygame.font.SysFont("Courier New", 32)
BIGFONT = pygame.font.SysFont("Courier New", 48)
WHITE = (255, 255, 255)
WALL = (50, 0, 20)
YELLOW = (255, 255, 0)
GREY = (180, 180, 180)
SCALE_FACTOR = 1e-5


state = "menu" 
menu_message = "Press ENTER to start"


def draw_menu():
    WIN.fill((0, 0, 0))
    text = BIGFONT.render(menu_message, True, WHITE)
    WIN.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2 - text.get_height()//2))
    pygame.display.update()

class Point():
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar):
        return Point(self.x * scalar, self.y * scalar)

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.transform.scale(pygame.image.load("C:/Users/birony/Desktop/HackRPI_2025/hackrpi25/hackrpi25/games/modern/PLACEHOLDER.png"), (26, 24)) #ALL ARGS PLACEHOLDERS
        self.rect = self.image.get_rect()
        self.rect.topleft = (x - self.rect.width/2, y - self.rect.height/2)
        self.pos = Point(x, y)
        self.velocity = Point(0, 0)

    def draw(self, surface):
        surface.blit(self.image, self.rect)
    
    def update(self):
        keys = pygame.key.get_pressed()
        # horizontal motion
        if keys[pygame.K_LEFT]:
            self.velocity += Point(-1 * SCALE_FACTOR, 0)
        if keys[pygame.K_RIGHT]:
            self.velocity += Point(1 * SCALE_FACTOR, 0)
        
        # jump
        if keys[pygame.K_UP] and self.rect.bottom >= HEIGHT - 12 - self.rect.height/8:
            self.velocity += Point(0, -10 * SCALE_FACTOR)

        self.velocity.y += 3 * SCALE_FACTOR  # gravity effect

        if(self.rect.left < 0):
            self.rect.left = 3
            self.velocity.x = abs(self.velocity.x) * 0.5
        if(self.rect.right > WIDTH):
            self.rect.right = WIDTH - 3
            self.velocity.x = -abs(self.velocity.x) * 0.5
        if(self.rect.bottom > HEIGHT):
            self.rect.bottom = HEIGHT - 3
            self.velocity.y = -abs(self.velocity.y) * 0.5
        
        self.rect.topleft = (self.rect.left + self.velocity.x, self.rect.top + self.velocity.y) # move based on velocity; simulates real motion, despite values being weird


player = Player(WIDTH//2, HEIGHT//2)

def run(name):
    global state, selected, scene, checked
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        if state == "menu":
            draw_menu()
            if(pygame.key.get_pressed()[pygame.K_RETURN]):
                state = "game"
                WIN.fill((255, 255, 255))
        
        if state == "game":
            WIN.fill((255, 255, 255))
            player.update()
            player.draw(WIN)
        
        FPS.tick(TICKRATE)
        pygame.display.update()

if __name__ == "__main__":
    run("")