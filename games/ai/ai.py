#!/usr/bin/env python3
"""
games/ai/ai.py

Chat demo with a dedicated full-screen win page showing a poem.
- When the user submits the keyword (default "raven") the game switches to
  a completely new win screen (not an overlay), freezes the timer at the
  moment of the win, displays whether any skips occurred, and renders the
  supplied poem in a light-grey box.
- Enter confirms and exits with {"action":"finished", "elapsed_seconds":...}
- ESC anytime -> {"action":"skipped"}; window close -> {"action":"exit"}.
- Prints final JSON to stdout for the launcher.
"""
from typing import Optional, List, Dict, Union
import sys
import time
import json
import pygame
import textwrap

# UI configuration: 800x600
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
    "It's a single-syllable name that starts with 'r' and ends with 'n' ... that should narrow it down.",
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

POEM = """  And the Raven, never flitting, still is sitting, still is sitting
    On the pallid bust of Pallas just above my chamber door;
    And his eyes have all the seeming of a demon’s that is dreaming,
    And the lamp-light o’er him streaming throws his shadow on the floor;
    And my soul from out that shadow that lies floating on the floor
    Shall be lifted—nevermore!
        -Edgar Allen Poe"""

# -----------------------------
# Helpers: text wrapping + poem
# -----------------------------
def wrap_text_lines(text: str, font: pygame.font.Font, max_width: int) -> List[str]:
    """Wrap a single paragraph (no explicit newlines) into lines that fit max_width."""
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

def _wrap_paragraph_to_width(text: str, font: pygame.font.Font, max_width: int) -> List[str]:
    """Wrap preserving leading whitespace for indented poem lines."""
    # Preserve leading spaces as indentation by measuring them as separate prefix
    lines = []
    for raw_line in text.splitlines():
        if raw_line.strip() == "":
            lines.append("")  # stanza break
            continue
        # detect leading spaces
        leading = len(raw_line) - len(raw_line.lstrip(' '))
        indent = ' ' * leading
        stripped = raw_line.lstrip(' ')
        wrapped = wrap_text_lines(stripped, font, max_width - font.size(indent)[0])
        # reapply indent to first line; subsequent wrapped lines are not indented
        if wrapped:
            lines.append(indent + wrapped[0])
            for extra in wrapped[1:]:
                lines.append(extra)
        else:
            lines.append(indent + stripped)
    return lines

def render_poem(surface: pygame.Surface, poem: Union[str, List[str]],
                font: pygame.font.Font, rect: pygame.Rect,
                color: tuple = (18,18,18),
                line_spacing: int = 6, stanza_spacing: int = 12,
                halign: str = "left", valign: str = "top"):
    """
    Render a multi-line poem into rect. Preserves blank lines and leading indentation.
    - poem: string with \n to indicate lines and blank lines for stanza breaks
    """
    if isinstance(poem, list):
        text = "\n".join(poem)
    else:
        text = poem

    render_lines = _wrap_paragraph_to_width(text, font, rect.width)

    # compute total height
    line_h = font.get_linesize()
    total_h = 0
    for ln in render_lines:
        if ln == "":
            total_h += stanza_spacing
        else:
            total_h += line_h + line_spacing
    if total_h > 0:
        total_h -= line_spacing

    # vertical alignment
    if valign == "center":
        start_y = rect.y + (rect.height - total_h) // 2
    elif valign == "bottom":
        start_y = rect.y + rect.height - total_h
    else:
        start_y = rect.y

    y = start_y
    for ln in render_lines:
        if ln == "":
            y += stanza_spacing
            continue
        # Render respecting leading spaces: measure indent width
        leading = 0
        stripped = ln
        while stripped.startswith(" "):
            leading += 1
            stripped = stripped[1:]
        indent_px = font.size(" " * leading)[0] if leading else 0
        text_surf = font.render(stripped, True, color)
        if halign == "center":
            x = rect.x + (rect.width - text_surf.get_width()) // 2
        elif halign == "right":
            x = rect.x + rect.width - text_surf.get_width()
        else:
            x = rect.x + indent_px
        surface.blit(text_surf, (x, y))
        y += line_h + line_spacing

    return pygame.Rect(rect.x, start_y, rect.width, total_h)

# -----------------------------
# Main chat + win flow
# -----------------------------
def run(player_name: Optional[str] = None, timer_start: Optional[float] = None, keyword: Optional[str] = None) -> Dict:
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Assistant (poem)")

    clock = pygame.time.Clock()
    header_font = pygame.font.SysFont("Helvetica", 24, bold=True)
    big_font = pygame.font.SysFont("Helvetica", 30)
    font = pygame.font.SysFont("Segoe UI", 16)
    input_font = pygame.font.SysFont("Segoe UI", 18)
    timer_font = pygame.font.SysFont("Segoe UI", 14)

    if keyword is None:
        keyword = DEFAULT_KEYWORD

    messages: List[Dict[str, str]] = []
    canned_idx = 0
    input_text = ""
    bot_typing = False
    bot_full_text = ""
    bot_char_index = 0
    bot_last_tick = 0
    centered_mode = True

    running = True
    result = {'action': 'exit'}
    skipped_any = False
    won = False
    elapsed_at_win = None

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
                        skipped_any = True
                        running = False
                        result = {'action': 'skipped'}
                        break

                    if won:
                        if ev.key == pygame.K_RETURN:
                            running = False
                            result = {'action': 'finished'}
                            break
                        else:
                            continue

                    # input handling
                    if ev.key == pygame.K_BACKSPACE:
                        input_text = input_text[:-1]
                    elif ev.key == pygame.K_RETURN:
                        user_msg = input_text.strip()
                        if user_msg == "" and centered_mode:
                            input_text = ""
                            continue
                        if centered_mode:
                            centered_mode = False
                        messages.append({'who': 'user', 'text': user_msg})
                        input_text = ""
                        # check keyword -> win
                        if user_msg and keyword.lower() in user_msg.lower():
                            # freeze time
                            if timer_start is not None:
                                try:
                                    elapsed_at_win = time.time() - float(timer_start)
                                except Exception:
                                    elapsed_at_win = None
                            else:
                                elapsed_at_win = None
                            won = True
                            # draw win screen immediately (time frozen)
                            draw_win_fullscreen_and_block(screen, big_font, font, timer_start, elapsed_at_win, skipped_any, player_name)
                            # after draw_win... returns when Enter pressed -> finalize
                            running = False
                            result = {'action': 'finished'}
                            break
                        else:
                            bot_full_text = CANNED_RESPONSES[canned_idx % len(CANNED_RESPONSES)]
                            canned_idx += 1
                            bot_char_index = 0
                            bot_typing = True
                            bot_last_tick = pygame.time.get_ticks()
                            messages.append({'who': 'bot', 'text': ""})
                    else:
                        if ev.unicode and ord(ev.unicode) >= 32:
                            input_text += ev.unicode

            # bot typing
            if bot_typing and not won:
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

            # DRAW main chat
            screen.fill(BG)
            header_text = header_font.render("Assistant", True, TEXT_COLOR)
            header_x = (SCREEN_W - header_text.get_width()) // 2
            screen.blit(header_text, (header_x, 14))

            if timer_start is not None and not won:
                try:
                    elapsed = time.time() - float(timer_start)
                    timer_str = format_mmss(elapsed)
                    timer_surf = timer_font.render(timer_str, True, TIMER_COLOR)
                    screen.blit(timer_surf, (SCREEN_W - timer_surf.get_width() - 12, 16))
                except Exception:
                    pass

            if centered_mode:
                if player_name:
                    prompt_text = f"Hello, {player_name}."
                else:
                    prompt_text = "Hello."
                prompt = big_font.render(prompt_text, True, TEXT_COLOR)
                prompt_x = (SCREEN_W - prompt.get_width()) // 2
                prompt_y = SCREEN_H // 3 - 40
                screen.blit(prompt, (prompt_x, prompt_y))

                box_w = SCREEN_W - 160
                box_h = INPUT_HEIGHT
                box_x = (SCREEN_W - box_w) // 2
                box_y = prompt_y + 70
                pygame.draw.rect(screen, INPUT_BG, (box_x, box_y, box_w, box_h), border_radius=28)
                pygame.draw.rect(screen, INPUT_BORDER, (box_x, box_y, box_w, box_h), 2, border_radius=28)
                plus = input_font.render("+", True, MUTED)
                screen.blit(plus, (box_x + 18, box_y + (box_h - plus.get_height()) // 2))
                placeholder = "Ask anything"
                txt_surf = input_font.render(input_text or placeholder, True, TEXT_COLOR if input_text else (150,150,150))
                screen.blit(txt_surf, (box_x + 54, box_y + (box_h - txt_surf.get_height()) // 2))
            else:
                chat_x = CHAT_LEFT
                chat_y = CHAT_TOP
                chat_w = CHAT_WIDTH
                chat_h = CHAT_HEIGHT
                pygame.draw.rect(screen, CHAT_BG, (chat_x, chat_y, chat_w, chat_h), border_radius=8)
                line_h = font.get_linesize()
                rendered_blocks = []
                for msg in messages:
                    who = msg['who']
                    text = msg['text'] or ""
                    lines = wrap_text_lines(text, font, MAX_BUBBLE_W - 2 * BUBBLE_PADDING_X)
                    if not lines:
                        lines = [""]
                    rendered_blocks.append((who, lines))
                cursor_y = chat_y + chat_h - 12
                for who, lines in reversed(rendered_blocks):
                    block_h = len(lines) * line_h + 2 * BUBBLE_PADDING_Y
                    cursor_y -= block_h
                    max_line_w = 0
                    for ln in lines:
                        max_line_w = max(max_line_w, font.size(ln)[0])
                    bubble_w = min(MAX_BUBBLE_W, max_line_w + 2 * BUBBLE_PADDING_X)
                    bubble_h = block_h
                    if who == 'user':
                        bx = chat_x + chat_w - bubble_w - 12
                        by = cursor_y
                        pygame.draw.rect(screen, USER_BUBBLE, (bx, by, bubble_w, bubble_h), border_radius=16)
                        ty = by + BUBBLE_PADDING_Y
                        for ln in lines:
                            surf = font.render(ln, True, TEXT_COLOR)
                            screen.blit(surf, (bx + BUBBLE_PADDING_X, ty))
                            ty += line_h
                    else:
                        bx = chat_x + 12
                        by = cursor_y
                        pygame.draw.rect(screen, BOT_BUBBLE, (bx, by, bubble_w, bubble_h), border_radius=16)
                        ty = by + BUBBLE_PADDING_Y
                        for ln in lines:
                            surf = font.render(ln, True, TEXT_COLOR)
                            screen.blit(surf, (bx + BUBBLE_PADDING_X, ty))
                            ty += line_h
                    cursor_y -= 8
                input_box_w = chat_w
                input_box_x = chat_x
                input_box_y = chat_y + chat_h + INPUT_MARGIN
                pygame.draw.rect(screen, INPUT_BG, (input_box_x, input_box_y, input_box_w, INPUT_HEIGHT), border_radius=10)
                pygame.draw.rect(screen, INPUT_BORDER, (input_box_x, input_box_y, input_box_w, INPUT_HEIGHT), 2, border_radius=10)
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

    out = {'action': result.get('action', 'exit')}
    if timer_start is not None:
        try:
            out['elapsed_seconds'] = round(time.time() - float(timer_start), 3) if not won else round(elapsed_at_win, 3) if elapsed_at_win is not None else None
        except Exception:
            pass
    out['skipped_levels'] = bool(skipped_any)
    return out

def draw_win_fullscreen_and_block(screen, big_font, font, timer_start, elapsed_at_win, skipped_any, player_name):
    """Draw a standalone fullscreen win screen (time frozen) and block until Enter or Quit/ESC."""
    clock = pygame.time.Clock()
    # Prepare poem box rect and fonts
    poem_box = pygame.Rect(48, 260, SCREEN_W - 96, 240)
    poem_font = pygame.font.SysFont("Georgia", 18)
    # compute frozen time string
    if elapsed_at_win is not None:
        time_str = format_mmss(elapsed_at_win)
    else:
        time_str = "N/A"

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                # exit immediately
                pygame.quit()
                sys.exit(0)
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_RETURN:
                    return
                if ev.key == pygame.K_ESCAPE:
                    # treat as skip: return to caller; caller will handle skipped flag if needed
                    return

        # Draw full screen themed page
        screen.fill(BG)
        header_font = pygame.font.SysFont("Helvetica", 24, bold=True)
        header_text = header_font.render("Assistant", True, TEXT_COLOR)
        header_x = (SCREEN_W - header_text.get_width()) // 2
        screen.blit(header_text, (header_x, 14))

        title = big_font.render("You win!", True, (20, 100, 40))
        screen.blit(title, ((SCREEN_W - title.get_width()) // 2, 90))

        if player_name:
            name_surf = font.render(f"Player: {player_name}", True, TEXT_COLOR)
            screen.blit(name_surf, (48, 150))

        time_label = font.render(f"Time: {time_str}", True, TEXT_COLOR)
        screen.blit(time_label, (48, 180))

        skipped_text = "Yes" if skipped_any else "No"
        skip_label = font.render(f"Levels skipped: {skipped_text}", True, TEXT_COLOR)
        screen.blit(skip_label, (48, 210))

        # poem box: light grey background
        pygame.draw.rect(screen, (240, 240, 240), poem_box)
        pygame.draw.rect(screen, (220, 220, 220), poem_box, 2)

        # Render poem into poem_box
        render_poem_rect = render_poem(screen, POEM, poem_font, poem_box, color=(24,24,24), halign="left", valign="top")

        cont = font.render("Press Enter to continue.", True, MUTED)
        screen.blit(cont, ((SCREEN_W - cont.get_width()) // 2, poem_box.bottom + 18))

        pygame.display.flip()
        clock.tick(FPS)

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