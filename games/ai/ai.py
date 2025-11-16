#!/usr/bin/env python3
"""
games/ai/ai.py

Fake "chat" demo (light mode, ChatGPT-like).

Behavior:
 - Window is 800x600, no sidebar.
 - Initially shows a centered prompt + rounded input box (like image 1).
   If a player_name is passed, the prompt says "Hello, {player_name}".
 - After the first message is sent, switches to a chat view:
     - Bot messages on the left, user messages on the right.
     - Bot responses are typed out character-by-character from a canned list.
 - Accepts optional CLI args:
     argv[1] = player_name (optional)
     argv[2] = timer_start_timestamp (float epoch seconds) - optional
     argv[3] = keyword (optional) - default "magicword"
 - If a submitted user message contains the keyword (case-insensitive),
   the game exits with {'action': 'finished', 'elapsed_seconds': ...} (if timer provided).
 - ESC or window close -> {'action': 'skipped'} or {'action': 'exit'}.
 - Prints final JSON to stdout for the launcher.
"""
from typing import Optional, List, Dict
import sys
import time
import json
import pygame

# UI configuration: 800x600 (as requested)
SCREEN_W = 800
SCREEN_H = 600
FPS = 60

# Chat area sizes (no sidebar)
CHAT_LEFT = 48
CHAT_TOP = 96
CHAT_WIDTH = SCREEN_W - 2 * CHAT_LEFT
CHAT_HEIGHT = SCREEN_H - 180  # leave space for header and input bar

INPUT_HEIGHT = 52
INPUT_MARGIN = 16

# Typing speed (ms per character)
CHAR_DELAY_MS = 20

DEFAULT_KEYWORD = "raven"

# Pre-canned responses (cycled)
CANNED_RESPONSES = [
    "I noticed how you played the earlier levels and some small details kept popping up across them.",
    "Sometimes puzzles reuse motifs. Did you catch any recurring images or symbols?",
    "One level had an interesting player icon. It seemed deliberately placed.",
    "Its plumage in the icon was dark, nearly black",
    "Think about creatures that are linked to night, to observation, and to cleverness.",
    "In folklore, birds often deliver messages or point to hidden things. Which bird feels like a messenger?",
    "The creature's name is short and crisp, and it's often associated with mystery and intelligence.",
    "It\'s a single-syllable name that starts with 'r' and ends with 'n' ... that should narrow it down.",
    "If you're ready: say the word 'raven' and we'll move on."
]

# Colors (light mode)
BG = (250, 250, 250)
CHAT_BG = (255, 255, 255)
USER_BUBBLE = (220, 235, 255)
BOT_BUBBLE = (245, 245, 245)
TEXT_COLOR = (18, 18, 18)
MUTED = (110, 110, 110)
INPUT_BG = (255, 255, 255)
INPUT_BORDER = (220, 220, 220)
TIMER_COLOR = (90, 90, 90)
ACCENT = (24, 120, 255)

# Padding for bubbles
BUBBLE_PADDING_X = 12
BUBBLE_PADDING_Y = 8
MAX_BUBBLE_W = CHAT_WIDTH - 180

# Helpers
def wrap_text_lines(text: str, font: pygame.font.Font, max_width: int) -> List[str]:
    words = text.split(' ')
    lines = []
    cur = ""
    for word in words:
        if cur:
            test = cur + " " + word
        else:
            test = word
        if font.size(test)[0] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            # if single word too long, break it across chars
            if font.size(word)[0] > max_width:
                part = ""
                for ch in word:
                    if font.size(part + ch)[0] <= max_width:
                        part += ch
                    else:
                        if part:
                            lines.append(part)
                        part = ch
                if part:
                    cur = part
                else:
                    cur = ""
            else:
                cur = word
    if cur:
        lines.append(cur)
    return lines

def format_mmss(elapsed_seconds: float) -> str:
    total = int(elapsed_seconds)
    mins = total // 60
    secs = total % 60
    return f"{mins:02d}:{secs:02d}"

# Main
def run(player_name: Optional[str] = None, timer_start: Optional[float] = None, keyword: Optional[str] = None) -> Dict:
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Assistant (demo)")

    clock = pygame.time.Clock()
    header_font = pygame.font.SysFont("Helvetica", 24, bold=True)
    big_font = pygame.font.SysFont("Helvetica", 30)
    font = pygame.font.SysFont("Segoe UI", 16)
    input_font = pygame.font.SysFont("Segoe UI", 18)
    timer_font = pygame.font.SysFont("Segoe UI", 14)

    if keyword is None:
        keyword = DEFAULT_KEYWORD

    # Messages stored as dicts: {'who': 'user'|'bot', 'text': str}
    messages: List[Dict[str, str]] = []

    canned_idx = 0
    input_text = ""
    input_active = True

    bot_typing = False
    bot_full_text = ""
    bot_char_index = 0
    bot_last_tick = 0

    # layout state: before any messages -> centered prompt mode
    centered_mode = True

    running = True
    result = {'action': 'exit'}

    try:
        while running:
            dt = clock.tick(FPS)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                    result = {'action': 'exit'}
                    break
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        running = False
                        result = {'action': 'skipped'}
                        break

                    # text input handling
                    if ev.key == pygame.K_BACKSPACE:
                        input_text = input_text[:-1]
                    elif ev.key == pygame.K_RETURN:
                        # Submit user message
                        user_msg = input_text.strip()
                        # If nothing typed and still centered, ignore
                        if user_msg == "" and centered_mode:
                            input_text = ""
                            continue
                        # first message -> switch layout
                        if centered_mode:
                            centered_mode = False
                        messages.append({'who': 'user', 'text': user_msg})
                        input_text = ""
                        # check keyword
                        if user_msg and keyword.lower() in user_msg.lower():
                            running = False
                            result = {'action': 'finished'}
                            break
                        # schedule bot response
                        bot_full_text = CANNED_RESPONSES[canned_idx % len(CANNED_RESPONSES)]
                        canned_idx += 1
                        bot_char_index = 0
                        bot_typing = True
                        bot_last_tick = pygame.time.get_ticks()
                        # append placeholder bot message
                        messages.append({'who': 'bot', 'text': ""})
                    else:
                        # handle printable characters
                        if ev.unicode and ord(ev.unicode) >= 32:
                            input_text += ev.unicode

            # bot typing update
            if bot_typing:
                now = pygame.time.get_ticks()
                if now - bot_last_tick >= CHAR_DELAY_MS:
                    bot_last_tick = now
                    bot_char_index += 1
                    if bot_char_index > len(bot_full_text):
                        bot_char_index = len(bot_full_text)
                    if messages and messages[-1]['who'] == 'bot':
                        messages[-1]['text'] = bot_full_text[:bot_char_index]
                    if bot_char_index >= len(bot_full_text):
                        bot_typing = False

            # DRAW
            screen.fill(BG)

            # Header (top center)
            header_text = header_font.render("Assistant", True, TEXT_COLOR)
            header_x = (SCREEN_W - header_text.get_width()) // 2
            screen.blit(header_text, (header_x, 14))

            # Timer top-right (MM:SS) if provided
            if timer_start is not None:
                try:
                    elapsed = time.time() - float(timer_start)
                    timer_str = format_mmss(elapsed)
                    timer_surf = timer_font.render(timer_str, True, TIMER_COLOR)
                    screen.blit(timer_surf, (SCREEN_W - timer_surf.get_width() - 12, 16))
                except Exception:
                    pass

            if centered_mode:
                # Draw centered prompt + input like image 1
                if player_name:
                    prompt_text = f"Hello, {player_name}."
                else:
                    prompt_text = "Hello."
                prompt = big_font.render(prompt_text, True, TEXT_COLOR)
                prompt_x = (SCREEN_W - prompt.get_width()) // 2
                prompt_y = SCREEN_H // 3 - 40
                screen.blit(prompt, (prompt_x, prompt_y))

                # Input box centered
                box_w = SCREEN_W - 160
                box_h = INPUT_HEIGHT
                box_x = (SCREEN_W - box_w) // 2
                box_y = prompt_y + 70
                pygame.draw.rect(screen, INPUT_BG, (box_x, box_y, box_w, box_h), border_radius=28)
                pygame.draw.rect(screen, INPUT_BORDER, (box_x, box_y, box_w, box_h), 2, border_radius=28)

                # plus icon on left (small)
                plus = input_font.render("+", True, MUTED)
                screen.blit(plus, (box_x + 18, box_y + (box_h - plus.get_height()) // 2))

                # placeholder or typed text
                placeholder = "Ask anything"
                if input_text:
                    txt_surf = input_font.render(input_text, True, TEXT_COLOR)
                else:
                    txt_surf = input_font.render(placeholder, True, (150, 150, 150))
                screen.blit(txt_surf, (box_x + 54, box_y + (box_h - txt_surf.get_height()) // 2))

            else:
                # Chat layout - full width chat area, no sidebar
                chat_x = CHAT_LEFT
                chat_y = CHAT_TOP
                chat_w = CHAT_WIDTH
                chat_h = CHAT_HEIGHT
                # chat background card
                pygame.draw.rect(screen, CHAT_BG, (chat_x, chat_y, chat_w, chat_h), border_radius=8)

                # Build rendered blocks for messages
                line_h = font.get_linesize()
                rendered_blocks = []
                for msg in messages:
                    who = msg['who']
                    text = msg['text'] or ""
                    lines = wrap_text_lines(text, font, MAX_BUBBLE_W - 2 * BUBBLE_PADDING_X)
                    if not lines:
                        lines = [""]
                    rendered_blocks.append((who, lines))

                # compute total height
                total_h = 0
                for who, lines in rendered_blocks:
                    block_h = len(lines) * line_h + 2 * BUBBLE_PADDING_Y
                    total_h += block_h + 8  # gap between blocks

                # Start drawing from bottom with margin
                cursor_y = chat_y + chat_h - 12
                for who, lines in reversed(rendered_blocks):
                    block_h = len(lines) * line_h + 2 * BUBBLE_PADDING_Y
                    cursor_y -= block_h
                    # determine bubble width based on longest line
                    max_line_w = 0
                    for ln in lines:
                        max_line_w = max(max_line_w, font.size(ln)[0])
                    bubble_w = min(MAX_BUBBLE_W, max_line_w + 2 * BUBBLE_PADDING_X)
                    bubble_h = block_h

                    if who == 'user':
                        # right-aligned bubble
                        bx = chat_x + chat_w - bubble_w - 12
                        by = cursor_y
                        pygame.draw.rect(screen, USER_BUBBLE, (bx, by, bubble_w, bubble_h), border_radius=16)
                        ty = by + BUBBLE_PADDING_Y
                        for ln in lines:
                            surf = font.render(ln, True, TEXT_COLOR)
                            screen.blit(surf, (bx + BUBBLE_PADDING_X, ty))
                            ty += line_h
                    else:
                        # left-aligned bubble
                        bx = chat_x + 12
                        by = cursor_y
                        pygame.draw.rect(screen, BOT_BUBBLE, (bx, by, bubble_w, bubble_h), border_radius=16)
                        ty = by + BUBBLE_PADDING_Y
                        for ln in lines:
                            surf = font.render(ln, True, TEXT_COLOR)
                            screen.blit(surf, (bx + BUBBLE_PADDING_X, ty))
                            ty += line_h

                    cursor_y -= 8  # gap

                # Input box below chat, full width of chat
                input_box_w = chat_w
                input_box_x = chat_x
                input_box_y = chat_y + chat_h + INPUT_MARGIN
                pygame.draw.rect(screen, INPUT_BG, (input_box_x, input_box_y, input_box_w, INPUT_HEIGHT), border_radius=10)
                pygame.draw.rect(screen, INPUT_BORDER, (input_box_x, input_box_y, input_box_w, INPUT_HEIGHT), 2, border_radius=10)
                # show input text (tail if too long)
                in_surf = input_font.render(input_text or "", True, TEXT_COLOR)
                if in_surf.get_width() > input_box_w - 24:
                    display = input_text
                    while input_font.size(display)[0] > input_box_w - 24 and display:
                        display = display[1:]
                    in_surf = input_font.render(display, True, TEXT_COLOR)
                screen.blit(in_surf, (input_box_x + 12, input_box_y + (INPUT_HEIGHT - in_surf.get_height()) // 2))

            pygame.display.flip()

    finally:
        try:
            pygame.quit()
        except Exception:
            pass

    # Build output for launcher
    out = {'action': result.get('action', 'exit')}
    if timer_start is not None:
        try:
            out['elapsed_seconds'] = round(time.time() - float(timer_start), 3)
        except Exception:
            pass
    return out

if __name__ == "__main__":
    # argv: player_name, timer_start, keyword
    player_name = None
    timer_start = None
    keyword = None
    if len(sys.argv) > 1:
        player_name = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            timer_start = float(sys.argv[2])
        except Exception:
            timer_start = None
    if len(sys.argv) > 3:
        keyword = sys.argv[3]

    res = run(player_name, timer_start, keyword)
    print(json.dumps(res))