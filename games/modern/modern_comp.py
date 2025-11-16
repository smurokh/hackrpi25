import pygame, sys, os, math, time, json

pygame.init()

# ---------- Constants ----------
WIDTH, HEIGHT = 800, 600
TICKRATE = 240
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
FPS = pygame.time.Clock()
pygame.display.set_caption("Modern UI")

FONT = pygame.font.SysFont("Courier New", 32)
BIGFONT = pygame.font.SysFont("Courier New", 48)
WHITE = (255, 255, 255)
WALL = (50, 0, 20)
YELLOW = (255, 255, 0)
GREY = (180, 180, 180)
SCALE_FACTOR = 2.5e-3
ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# Platform dimensions
PLATFORM_HEIGHT = 20
STD_GAP = 100

PLAYER_NAME = ""
START_TS = None

def pendingCollision(obj, vel, group):
    future = obj
    # create temporary copy for collision test: we use a shallow copy of rect and mask,
    # but here existing code simply alters position; preserve behavior by using rect move
    future.pos = Point(future.pos.x + vel.x, future.pos.y + vel.y)
    future.rect = pygame.Rect(future.pos.x - future.rect.width//2, future.pos.y - future.rect.height//2,
                              future.rect.width, future.rect.height)
    hits = pygame.sprite.spritecollide(future, group, False, pygame.sprite.collide_mask)
    # restore original rect/pos (we don't want to permanently move object)
    future.pos = Point(future.pos.x - vel.x, future.pos.y - vel.y)
    future.rect = pygame.Rect(future.pos.x - future.rect.width//2, future.pos.y - future.rect.height//2,
                              future.rect.width, future.rect.height)
    return hits

def moveScene():
    global curScene
    curScene += 1
    if curScene >= len(RIGIDBODIES):
        # Display a simple win screen and wait for the player to press Enter to exit
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        pygame.quit()
                        sys.exit()

            WIN.fill((0, 0, 0))
            title = BIGFONT.render("You Win!", True, YELLOW)
            instr = FONT.render("Press Enter to exit", True, WHITE)
            WIN.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - title.get_height()))
            WIN.blit(instr, (WIDTH // 2 - instr.get_width() // 2, HEIGHT // 2 + 10))
            pygame.display.update()
            FPS.tick(TICKRATE)

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

class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, img):
        super().__init__()
        self.image = pygame.transform.scale(img, (int(width), int(height)))
        self.rect = self.image.get_rect()
        self.rect.topleft = (int(x), int(y))
        self.mask = pygame.mask.from_surface(self.image)
    
    def draw(self, surface):
        surface.blit(self.image, self.rect)

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.transform.scale(pygame.image.load(os.path.join(ASSET_DIR, "player.png")).convert_alpha(), (30, 32))
        self.rect = self.image.get_rect()
        self.rect.topleft = (x - self.rect.width/2, y - self.rect.height/2)
        self.posInit = Point(x, y)
        self.pos = Point(x, y - self.rect.height//2)
        self.velocity = Point(0, 0)
        self.mask = pygame.mask.from_surface(self.image)

    def draw(self, surface):
        surface.blit(self.image, self.rect)
    
    def update(self):
        collisions = pendingCollision(self, self.velocity, RIGIDBODIES[curScene])
        
        self.velocity += Point(0, 1.8 * SCALE_FACTOR)  # gravity effect
        keys = pygame.key.get_pressed()
        # horizontal motion
        if keys[pygame.K_LEFT]:
            self.velocity += Point(-2, 0) * SCALE_FACTOR
        if keys[pygame.K_RIGHT]:
            self.velocity += Point(2, 0) * SCALE_FACTOR
        # slow down, required due to the fun ice physics
        if len(collisions) != 0:
            if keys[pygame.K_LSHIFT]:
                self.velocity *= 0.8
            else:
                self.velocity *= 0.95
        for wall in collisions:
            # jump
            if keys[pygame.K_UP] and abs(self.rect.bottom - wall.rect.top) < 10 and self.velocity.y >= 0:
                self.velocity += Point(0, -0.8)
            elif keys[pygame.K_SPACE] and abs(self.rect.left - wall.rect.right) < 10:
                self.velocity.x += math.sqrt(0.05)
                self.velocity.y -= math.sqrt(0.05)
            elif keys[pygame.K_SPACE] and abs(self.rect.right - wall.rect.left) < 10:
                self.velocity.x -= math.sqrt(0.05)
                self.velocity.y -= math.sqrt(0.05)
        # after updating velocity, check for collisions again
        collisions = pendingCollision(self, self.velocity, RIGIDBODIES[curScene])
        for wall in collisions:
            if self.velocity.y > 0 and self.rect.bottom - wall.rect.top < 10:
                self.velocity.y *= -0.2
                self.pos.y = wall.rect.top - self.rect.height//2
            elif self.velocity.y < 0 and wall.rect.bottom - self.rect.top < 10:
                self.velocity.y *= -0.2
                self.pos.y = wall.rect.bottom + self.rect.height//2
            elif self.velocity.x > 0 and self.rect.right - wall.rect.left < 10:
                self.velocity.x *= -0.5
                self.pos.x = wall.rect.left - self.rect.width//2
            elif self.velocity.x < 0 and wall.rect.right - self.rect.left < 10:
                self.velocity.x *= -0.5
                self.pos.x = wall.rect.right + self.rect.width//2
        self.pos += self.velocity
        self.rect.topleft = (self.pos.x - self.rect.width//2, self.pos.y - self.rect.height//2)

        if self.rect.top < 0:
            self.pos = Point(self.pos.x, self.posInit.y - self.rect.height//2)
            moveScene()
        if self.rect.left < 0:
            self.pos = Point(self.posInit.x, self.posInit.y - self.rect.height//2)
        if self.rect.right > WIDTH:
            self.pos = Point(self.posInit.x, self.posInit.y - self.rect.height//2)

bgs = [
    pygame.transform.scale(pygame.image.load(os.path.join(ASSET_DIR, "stg1_bg.png")).convert(), (WIDTH, HEIGHT)),
    pygame.transform.scale(pygame.image.load(os.path.join(ASSET_DIR, "stg2_bg.png")).convert(), (WIDTH, HEIGHT)),
    pygame.transform.scale(pygame.image.load(os.path.join(ASSET_DIR, "stg3_bg.png")).convert(), (WIDTH, HEIGHT))
    ]
stg1_horizontal = pygame.image.load(os.path.join(ASSET_DIR, "stg1_horizontal.png")).convert()
stg2_horizontal = pygame.image.load(os.path.join(ASSET_DIR, "stg2_horizontal.png")).convert()
stg3_horizontal = pygame.image.load(os.path.join(ASSET_DIR, "stg3_horizontal.png")).convert()
stg1_vertical = pygame.image.load(os.path.join(ASSET_DIR, "stg1_vertical.png")).convert()
stg2_vertical = pygame.image.load(os.path.join(ASSET_DIR, "stg2_vertical.png")).convert()
stg3_vertical = pygame.image.load(os.path.join(ASSET_DIR, "stg3_vertical.png")).convert()

player = Player(150, HEIGHT)
curScene = 0
BOUND_WIDTH = 50
BOUNDARIES = [
    Wall(0, HEIGHT, WIDTH + BOUND_WIDTH * 2, BOUND_WIDTH, stg1_horizontal), # lower boundary
    Wall(-BOUND_WIDTH, -BOUND_WIDTH, BOUND_WIDTH, HEIGHT + BOUND_WIDTH * 2, stg1_vertical), # left boundary
    Wall(WIDTH, 0, BOUND_WIDTH, HEIGHT + BOUND_WIDTH * 2, stg1_vertical) # right boundary
]
RIGIDBODIES = [
    [Wall(0, HEIGHT * 5/6, WIDTH/2 + 100, PLATFORM_HEIGHT, stg1_horizontal), Wall(WIDTH/2 + 100 + STD_GAP, HEIGHT * 5/6, WIDTH - WIDTH/2 - 100 - STD_GAP, PLATFORM_HEIGHT, stg1_horizontal),
     Wall(0, HEIGHT * 2/3, WIDTH/4, PLATFORM_HEIGHT, stg1_horizontal), Wall(WIDTH/4 + STD_GAP, HEIGHT * 2/3, WIDTH - WIDTH/4 - STD_GAP, PLATFORM_HEIGHT, stg1_horizontal),
     Wall(0, 0.5 * HEIGHT, 0.75 * WIDTH, PLATFORM_HEIGHT, stg1_horizontal), Wall(0.75 * WIDTH + STD_GAP, 0.5 * HEIGHT, WIDTH - 0.75 * WIDTH - STD_GAP, PLATFORM_HEIGHT, stg1_horizontal),
     Wall(0, HEIGHT * 1/3, 50, PLATFORM_HEIGHT, stg1_horizontal), Wall(50 + STD_GAP, HEIGHT * 1/3, WIDTH - 50 - STD_GAP, PLATFORM_HEIGHT, stg1_horizontal),
     Wall(0.8 * WIDTH, HEIGHT * 1/6, WIDTH * 0.2, PLATFORM_HEIGHT, stg1_horizontal), Wall(0, HEIGHT * 1/6, 0.8 * WIDTH - STD_GAP, PLATFORM_HEIGHT, stg1_horizontal)
     ] + BOUNDARIES,
     [
         Wall(0, 0, PLATFORM_HEIGHT, 0.9 * HEIGHT, stg2_vertical), Wall(WIDTH - PLATFORM_HEIGHT, 0, PLATFORM_HEIGHT, 0.9 * HEIGHT, stg2_vertical),
         Wall(PLATFORM_HEIGHT + STD_GAP, HEIGHT * 0.9 - PLATFORM_HEIGHT, WIDTH - PLATFORM_HEIGHT - STD_GAP, PLATFORM_HEIGHT, stg2_horizontal),
         Wall(PLATFORM_HEIGHT + STD_GAP, HEIGHT * 0.7 - PLATFORM_HEIGHT, STD_GAP, PLATFORM_HEIGHT, stg2_horizontal),
         Wall(PLATFORM_HEIGHT + STD_GAP * 2, HEIGHT * 0.7 - PLATFORM_HEIGHT, PLATFORM_HEIGHT, HEIGHT * 0.2, stg2_vertical),
         Wall(PLATFORM_HEIGHT, HEIGHT * 0.5 - PLATFORM_HEIGHT, STD_GAP * 3, PLATFORM_HEIGHT, stg2_horizontal),
         Wall(PLATFORM_HEIGHT + STD_GAP * 3, HEIGHT * 0.5 - PLATFORM_HEIGHT, PLATFORM_HEIGHT, HEIGHT * 0.2, stg2_vertical),
         Wall(PLATFORM_HEIGHT + STD_GAP * 4, HEIGHT * 0.3 - PLATFORM_HEIGHT, PLATFORM_HEIGHT, HEIGHT * 0.6, stg2_vertical),
         Wall(PLATFORM_HEIGHT + STD_GAP, HEIGHT * 0.3 - PLATFORM_HEIGHT, STD_GAP * 3, PLATFORM_HEIGHT, stg2_horizontal),
         Wall(PLATFORM_HEIGHT, HEIGHT * 0.1 - PLATFORM_HEIGHT, STD_GAP * 5, PLATFORM_HEIGHT, stg2_horizontal),
         Wall(PLATFORM_HEIGHT + STD_GAP * 5, 0, PLATFORM_HEIGHT, WIDTH * 0.55, stg2_vertical),
         Wall(PLATFORM_HEIGHT + STD_GAP * 6.25, HEIGHT * 0.3 - PLATFORM_HEIGHT, PLATFORM_HEIGHT, HEIGHT * 0.2, stg2_vertical),
         Wall(PLATFORM_HEIGHT + STD_GAP * 6.25, HEIGHT * 0.6 - PLATFORM_HEIGHT, PLATFORM_HEIGHT, HEIGHT * 0.2, stg2_vertical)
     ] + BOUNDARIES,
     [
         Wall(STD_GAP, PLATFORM_HEIGHT, WIDTH - STD_GAP, PLATFORM_HEIGHT, stg3_horizontal),
         Wall(WIDTH * 0.7, HEIGHT * 0.8, STD_GAP, PLATFORM_HEIGHT, stg3_horizontal),
         Wall(WIDTH * 0.6, HEIGHT * 0.5, PLATFORM_HEIGHT, HEIGHT * 0.2, stg3_vertical),
         Wall(WIDTH * 0.7, HEIGHT * 0.4, STD_GAP, PLATFORM_HEIGHT, stg3_horizontal),
         Wall(WIDTH * 0.4, HEIGHT * 0.4, STD_GAP, PLATFORM_HEIGHT, stg3_horizontal),
         Wall(WIDTH * 0.4, HEIGHT * 0.7, STD_GAP, PLATFORM_HEIGHT, stg3_horizontal),
         Wall(WIDTH * 0.3, HEIGHT * 0.1, PLATFORM_HEIGHT, HEIGHT * 0.45, stg3_vertical),
         Wall(WIDTH * 0.1, HEIGHT * 0.7, STD_GAP, PLATFORM_HEIGHT, stg3_horizontal),
         Wall(0, HEIGHT * 0.2, STD_GAP, PLATFORM_HEIGHT, stg3_horizontal),
         Wall(0, 0, PLATFORM_HEIGHT, HEIGHT * 0.2, stg3_vertical),
     ] + [BOUNDARIES[0]]
]

def run(name):
    global selected, scene, checked, curScene, PLAYER_NAME, START_TS
    PLAYER_NAME = name or PLAYER_NAME or "Player"

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        WIN.blit(bgs[curScene], (0, 0))
        player.update()
        player.draw(WIN)
        for wall in RIGIDBODIES[curScene]:
            wall.draw(WIN)

        name_surf = FONT.render(f"{PLAYER_NAME}", True, WHITE)
        WIN.blit(name_surf, (10, 10))

        if START_TS is not None:
            elapsed = time.time() - float(START_TS)
            mins = int(elapsed) // 60
            secs = int(elapsed) % 60
            timer_str = f"{mins:02d}:{secs:02d}"
            timer_surf = FONT.render(timer_str, True, WHITE)
            WIN.blit(timer_surf, (WIDTH - 10 - timer_surf.get_width(), 10))

        keys = pygame.key.get_pressed()
        if keys[pygame.K_RETURN] or keys[pygame.K_KP_ENTER]:
            player.pos = Point(player.pos.x, player.posInit.y - player.rect.height//2)
            curScene = 3

        if keys[pygame.K_ESCAPE]:
            result = {'action': 'skipped'}
            try:
                if START_TS is not None:
                    result['elapsed_seconds'] = round(time.time() - float(START_TS), 3)
            except Exception:
                pass
            pygame.quit()
            print(json.dumps(result))
            sys.exit(0)

        FPS.tick(TICKRATE)
        pygame.display.update()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        PLAYER_NAME = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            START_TS = float(sys.argv[2])
        except Exception:
            START_TS = None

    if not PLAYER_NAME:
        PLAYER_NAME = ""

    run(PLAYER_NAME)