import pygame
import sys

pygame.init()
name = "Player"

#def run(name)

WIDTH, HEIGHT = 800, 600
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SMS Chat Demo")

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LIGHT_GRAY = (225, 225, 225)
LIGHT_BLUE = (214, 219, 233)
BLUE = (150, 200, 255)
GREEN = (165, 239, 100)

FONT = pygame.font.Font(None, 32)

# Chat messages stored as tuples:
# ("text", "sender")
chat_log = []

# Conversation script
"""
#template
conversation = [
    {
        "npc": "Test1",
        "delay": 0,
        "choices": [
            "Choice1",
            "Choice2",
            "Choice3"
        ]
    },
    {
        "npc": "Test2",
        "delay": 1000,
        "choices": [
            "Choice1",
            "Choice2",
        ]
    },
    {
        "npc": "Done",
        "delay": 1000,
        "choices": []
    }
]
"""
conversation_steps = {
    "firstsnow": {    
        "timestamp": "Nov 11, 2009 2:30 PM",
        "script":{
            "npc": "Hi, {}!\nWe had our first snow today!".format(name),
            "delay": 0,
            "choices": []
            }
        }
    }

step = "firstsnow"

# --- NPC delay system ---
pending_npc_message = None
npc_delay_start = 0
npc_delay_ms = 0


def schedule_npc_message(text, delay):
    """Schedule an NPC message to appear after delay (ms)."""
    global pending_npc_message, npc_delay_start, npc_delay_ms
    pending_npc_message = text
    npc_delay_ms = delay
    npc_delay_start = pygame.time.get_ticks()


def process_delayed_npc_message():
    """Check if it's time to show the delayed NPC message."""
    global pending_npc_message
    if pending_npc_message is None:
        return

    current_time = pygame.time.get_ticks()
    if current_time - npc_delay_start >= npc_delay_ms:
        add_npc_message(pending_npc_message)
        pending_npc_message = None


def draw_chat():
    WIN.fill(LIGHT_BLUE)

    # Top timestamp
    time_surf = FONT.render(step["timestamp"], True, (120, 120, 120))
    time_x = (WIDTH - time_surf.get_width()) // 2
    WIN.blit(time_surf, (time_x, 10))

    y_offset = 50  # start messages lower

    for text, sender in chat_log:
        bubble_color = WHITE if sender == "npc" else GREEN

        surf = FONT.render(text, True, BLACK)
        padding = 10
        bubble = pygame.Rect(0, 0, surf.get_width() + padding * 2,
                             surf.get_height() + padding * 2)

        if sender == "npc":
            bubble.topleft = (20, y_offset)
        else:
            bubble.topright = (WIDTH - 20, y_offset)

        pygame.draw.rect(WIN, bubble_color, bubble, border_radius=8)
        WIN.blit(surf, (bubble.x + padding, bubble.y + padding))

        y_offset += bubble.height + 15


def draw_choices(choices):
    y = HEIGHT - 140
    for i, choice in enumerate(choices):
        text = FONT.render(f"{i+1}. {choice}", True, BLACK)
        WIN.blit(text, (20, y))
        y += 40


def add_npc_message(text):
    chat_log.append((text, "npc"))


def add_player_message(text):
    chat_log.append((text, "player"))

def game_loop():
    global step

    clock = pygame.time.Clock()

    # schedule first NPC message
    schedule_npc_message(
        conversation_steps[step]["script"]["npc"],
        conversation_steps[step]["script"]["delay"]
    )

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # Process delayed NPC message
        process_delayed_npc_message()

        # Draw chat UI
        draw_chat()

        # Current choices
        choices = conversation_steps[step]["script"]["choices"]
        draw_choices(choices)

        keys = pygame.key.get_pressed()

        # Player chooses a reply
        for i in range(len(choices)):
            if keys[getattr(pygame, f"K_{i+1}")]:
                add_player_message(choices[i])
                step += 1

                if step < len(conversation_steps):
                    npc_text = conversation_steps[step]["npc"]
                    npc_delay = conversation_steps[step]["delay"]
                    schedule_npc_message(npc_text, npc_delay)

                pygame.time.delay(200)  # prevents double input
                break

        pygame.display.update()
        clock.tick(60)


game_loop()
