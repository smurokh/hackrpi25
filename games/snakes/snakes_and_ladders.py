from typing import Optional
import pygame
import sys
import random
import time
import math
import os
import json

# ---- Configuration (adapted for 800x600) ----
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600

BOARD_PADDING = 16
BOARD_SIZE = 480   # 10x10 board (cells will be 48x48)
CELL_COUNT = 10
CELL_SIZE = BOARD_SIZE // CELL_COUNT

FPS = 60

# Colors - updated visuals (tiles -> light grays, ladders -> brown, snakes -> crimson)
BACKGROUND = (170, 200, 230)          # background behind board
TILE_LIGHT = (246, 246, 246)          # very light gray
TILE_DARK = (236, 236, 236)           # slightly darker light gray
GREEN = (139, 69, 19)                 # ladder color -> brown (kept name GREEN for compatibility)
RED = (220, 20, 60)                   # snake color -> crimson (kept name RED for compatibility)
BLUE = (50, 50, 200)
GOLD = (215, 170, 30)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BUTTON_BG = (240, 240, 240)
BUTTON_BORDER = (100, 100, 100)
HIGHLIGHT = (255, 240, 180)

# Snakes and ladders mapping: start -> end (can be mutated by power-ups / swaps)
JUMPS = {
    # ladders
    3: 22,
    5: 8,
    11: 26,
    20: 29,
    27: 56,
    36: 57,
    40: 59,
    51: 67,
    71: 92,
    80: 99,
    # snakes
    17: 4,
    52: 29,
    62: 19,
    64: 60,
    87: 24,
    93: 73,
    95: 75,
    98: 78,
}

# Module-level optional timer start (set by launcher via argv[2] when running as script)
TIMER_START: Optional[float] = None

# Module-level player icon (will be set in run_flash if raven.png available)
player_icon = None  # pygame.Surface or None

# -------------------------
# Helper functions (pure)
# -------------------------

def cell_index_to_coord(cell_index):
    """
    Convert a fixed cell index (1..100) to pixel center (x, y).
    Board layout zig-zags left-right every other row.
    """
    idx = cell_index - 1
    row_from_bottom = idx // 10
    within_row = idx % 10
    if row_from_bottom % 2 == 0:
        col = within_row
    else:
        col = 9 - within_row
    row_top_based = 9 - row_from_bottom
    x = BOARD_PADDING + col * CELL_SIZE + CELL_SIZE // 2
    y = BOARD_PADDING + row_top_based * CELL_SIZE + CELL_SIZE // 2
    return x, y

def coord_to_cell_index(px, py):
    if px < BOARD_PADDING or px >= BOARD_PADDING + BOARD_SIZE:
        return None
    if py < BOARD_PADDING or py >= BOARD_PADDING + BOARD_SIZE:
        return None
    col = (px - BOARD_PADDING) // CELL_SIZE
    row_top = (py - BOARD_PADDING) // CELL_SIZE  # 0 at top
    row_from_bottom = 9 - row_top
    if row_from_bottom < 0 or row_from_bottom > 9:
        return None
    if row_from_bottom % 2 == 0:
        within_row = int(col)
    else:
        within_row = 9 - int(col)
    idx = row_from_bottom * 10 + within_row
    return idx + 1

def lerp(a, b, t):
    return a + (b - a) * t

def cubic_bezier_point(p0, p1, p2, p3, t):
    u = 1 - t
    tt = t * t
    uu = u * u
    uuu = uu * u
    ttt = tt * t
    x = uuu * p0[0] + 3 * uu * t * p1[0] + 3 * u * tt * p2[0] + ttt * p3[0]
    y = uuu * p0[1] + 3 * uu * t * p1[1] + 3 * u * tt * p2[1] + ttt * p3[1]
    return int(x), int(y)

def sample_cubic_bezier(p0, p1, p2, p3, samples=30):
    return [cubic_bezier_point(p0, p1, p2, p3, i / (samples - 1)) for i in range(samples)]

def compute_snake_curve(start_cell, end_cell):
    sx, sy = cell_index_to_coord(start_cell)
    ex, ey = cell_index_to_coord(end_cell)
    vx = ex - sx
    vy = ey - sy
    dist = math.hypot(vx, vy)
    if dist < 1:
        return [(sx, sy), (ex, ey)]
    ux = vx / dist
    uy = vy / dist
    px = -uy
    py = ux
    curvature = max(30, min(120, dist * 0.35))
    sign = -1 if ((start_cell + end_cell) % 2 == 0) else 1
    p0 = (sx, sy)
    p3 = (ex, ey)
    p1 = (sx + ux * (dist * 0.25) + px * curvature * sign, sy + uy * (dist * 0.25) + py * curvature * sign)
    p2 = (sx + ux * (dist * 0.75) - px * curvature * sign, sy + uy * (dist * 0.75) - py * curvature * sign)
    # increase samples for smoother curve
    pts = sample_cubic_bezier(p0, p1, p2, p3, samples=max(28, int(dist // 3)))
    return pts

def compute_ladder_rungs_and_rails(start_cell, end_cell):
    sx, sy = cell_index_to_coord(start_cell)
    ex, ey = cell_index_to_coord(end_cell)
    vx = ex - sx
    vy = ey - sy
    dist = math.hypot(vx, vy)
    if dist < 1:
        return (sx, sy, ex, ey, [])
    ux = vx / dist
    uy = vy / dist
    px = -uy
    py = ux
    rail_offset = max(10, min(20, dist * 0.06))
    rail1_start = (sx + px * rail_offset, sy + py * rail_offset)
    rail1_end = (ex + px * rail_offset, ey + py * rail_offset)
    rail2_start = (sx - px * rail_offset, sy - py * rail_offset)
    rail2_end = (ex - px * rail_offset, ey - py * rail_offset)
    rung_spacing = max(22, min(44, dist / 6))
    num_rungs = max(3, int(dist // rung_spacing))
    rung_points = []
    for i in range(1, num_rungs + 1):
        t = i / (num_rungs + 1)
        r1x = lerp(rail1_start[0], rail1_end[0], t)
        r1y = lerp(rail1_start[1], rail1_end[1], t)
        r2x = lerp(rail2_start[0], rail2_end[0], t)
        r2y = lerp(rail2_start[1], rail2_end[1], t)
        rung_points.append(((int(r1x), int(r1y)), (int(r2x), int(r2y))))
    return (rail1_start, rail1_end, rail2_start, rail2_end, rung_points)

def get_jump_path_points(start_cell, end_cell):
    if end_cell < start_cell:
        return compute_snake_curve(start_cell, end_cell)
    else:
        sx, sy = cell_index_to_coord(start_cell)
        ex, ey = cell_index_to_coord(end_cell)
        dist = math.hypot(ex - sx, ey - sy)
        steps = max(8, int(dist // 8))
        return [(int(lerp(sx, ex, t / (steps - 1))), int(lerp(sy, ey, t / (steps - 1)))) for t in range(steps)]

# -------------------------
# Snake smoothing helper
# -------------------------

def _draw_smooth_thick_path(surface, pts, color, thickness):
    """
    Draw a smooth thick path by building a polygon 'tube' around a centerline.
    This reduces pixelation compared to pygame.draw.lines with large widths.
    """
    if not pts or len(pts) < 2:
        return
    try:
        half = float(thickness) / 2.0
        n_pts = len(pts)
        normals = []
        # compute smoothed normals
        for i in range(n_pts):
            if i == 0:
                x0, y0 = pts[0]
                x1, y1 = pts[1]
                vx, vy = x1 - x0, y1 - y0
            elif i == n_pts - 1:
                x0, y0 = pts[-2]
                x1, y1 = pts[-1]
                vx, vy = x1 - x0, y1 - y0
            else:
                x_prev, y_prev = pts[i - 1]
                x_next, y_next = pts[i + 1]
                vx, vy = x_next - x_prev, y_next - y_prev
            length = math.hypot(vx, vy)
            if length == 0:
                nx, ny = 0.0, 0.0
            else:
                nx, ny = -vy / length, vx / length
            normals.append((nx, ny))

        left = []
        right = []
        for (px, py), (nx, ny) in zip(pts, normals):
            lx = px + nx * half
            ly = py + ny * half
            rx = px - nx * half
            ry = py - ny * half
            left.append((lx, ly))
            right.append((rx, ry))

        poly = left + list(reversed(right))
        # fill polygon
        pygame.draw.polygon(surface, color, poly)
        # outline with a slightly darker color for depth
        outline = tuple(max(0, c - 40) for c in color)
        try:
            pygame.draw.aalines(surface, outline, True, poly)
        except Exception:
            pygame.draw.lines(surface, outline, True, poly, 1)
    except Exception:
        # fallback if something fails: draw simple lines
        try:
            pygame.draw.lines(surface, color, False, pts, int(thickness))
        except Exception:
            pass

# -------------------------
# Drawing routines (use fonts defined in run_flash)
# -------------------------

def draw_board(surface, font_small):
    board_rect = pygame.Rect(BOARD_PADDING, BOARD_PADDING, BOARD_SIZE, BOARD_SIZE)
    pygame.draw.rect(surface, BLACK, board_rect, 2)
    for r in range(CELL_COUNT):
        for c in range(CELL_COUNT):
            rect = pygame.Rect(BOARD_PADDING + c * CELL_SIZE,
                               BOARD_PADDING + r * CELL_SIZE,
                               CELL_SIZE, CELL_SIZE)
            # alternate light gray tiles
            color = TILE_LIGHT if (r + c) % 2 == 0 else TILE_DARK
            pygame.draw.rect(surface, color, rect)
            pygame.draw.rect(surface, BLACK, rect, 1)
    # Note: grid numbers are drawn separately so they can be layered above snakes

def draw_snakes(surface):
    """Draw all snake paths (they will be drawn first so other elements can be layered above)."""
    # thinner snakes: 3/4 of previous width (previous approx 14 -> now 11)
    snake_thickness = max(3, int(round(14 * 0.75)))
    for start, end in JUMPS.items():
        if end < start:
            pts = compute_snake_curve(start, end)
            if len(pts) >= 2:
                _draw_smooth_thick_path(surface, pts, RED, thickness=snake_thickness)
            else:
                sx, sy = cell_index_to_coord(start)
                ex, ey = cell_index_to_coord(end)
                pygame.draw.line(surface, RED, (sx, sy), (ex, ey), snake_thickness)

def draw_grid_numbers(surface, font_small):
    # Draw grid numbers on top of the board (so they appear above snakes)
    for cell in range(1, 101):
        x, y = cell_index_to_coord(cell)
        text = font_small.render(str(cell), True, BLACK)
        tx = x - CELL_SIZE // 2 + 4
        ty = y - CELL_SIZE // 2 + 2
        surface.blit(text, (tx, ty))

def draw_ladders(surface):
    """Draw ladders after snakes and grid numbers, so ladders appear above snakes."""
    for start, end in JUMPS.items():
        if end > start:
            rail1_start, rail1_end, rail2_start, rail2_end, rung_points = compute_ladder_rungs_and_rails(start, end)
            # draw ladder rails and rungs in brown (GREEN variable)
            pygame.draw.line(surface, GREEN, rail1_start, rail1_end, 5)
            pygame.draw.line(surface, GREEN, rail2_start, rail2_end, 5)
            for a, b in rung_points:
                pygame.draw.line(surface, GREEN, a, b, 3)

def draw_jumps(surface, font_small):
    """
    Backwards-compatible wrapper that draws snakes, grid numbers, then ladders.
    Kept for callers that used draw_jumps previously; it orchestrates the correct order.
    """
    # draw snakes first (below)
    draw_snakes(surface)
    # draw grid numbers above the snakes
    draw_grid_numbers(surface, font_small)
    # draw ladders above snakes and above grid numbers
    draw_ladders(surface)

def draw_player(surface, pos, player_color, radius=12):
    """
    Draw the player token at pos (center). If a player_icon has been loaded,
    blit it centered; otherwise fall back to drawing a filled circle with outline.
    """
    global player_icon
    if player_icon:
        iw = player_icon.get_width()
        ih = player_icon.get_height()
        top_left = (int(pos[0] - iw // 2), int(pos[1] - ih // 2))
        surface.blit(player_icon, top_left)
    else:
        pygame.draw.circle(surface, BLACK, pos, radius + 2)
        pygame.draw.circle(surface, player_color, pos, radius)

def draw_dice(surface, rect, face, font, dice_images):
    pygame.draw.rect(surface, BLACK, rect)
    pygame.draw.rect(surface, WHITE, rect, 2)
    if isinstance(face, int) and dice_images and face in dice_images:
        img = dice_images[face]
        ix = rect.x + (rect.width - img.get_width()) // 2
        iy = rect.y + (rect.height - img.get_height()) // 2
        surface.blit(img, (ix, iy))
    else:
        if isinstance(face, int):
            text = font.render(str(face), True, WHITE)
        else:
            text = font.render("-", True, WHITE)
        tx = rect.x + (rect.width - text.get_width()) // 2
        ty = rect.y + (rect.height - text.get_height()) // 2
        surface.blit(text, (tx, ty))

# -------------------------
# Main runner function
# -------------------------

def run_flash(on_finish=None, width=800, height=600):
    """
    Initialize pygame and run the game loop. When the game ends (exit or win),
    this function returns a dict result and calls on_finish(result) if provided.
    The dict only contains 'action' (e.g. 'finished', 'exit', 'skipped') and
    includes 'elapsed_seconds' if TIMER_START was provided.
    """
    # initialize pygame & window
    pygame.init()
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Snakes & Ladders - 800x600")
    clock = pygame.time.Clock()

    # fonts (set globals used by draw functions)
    global font_small, font_medium, font_large, font_dice, dice_rect, player_icon
    font_small = pygame.font.SysFont("arial", 14)      # kept small for compact UI text
    font_medium = pygame.font.SysFont("arial", 20, bold=True)
    font_large = pygame.font.SysFont("arial", 44, bold=True)
    font_dice = pygame.font.SysFont("arial", 36, bold=True)
    # larger font for the instruction block (user requested bigger instructions)
    font_info = pygame.font.SysFont("arial", 16)      # increased from 14 -> 16

    # Layout rectangles (placed relative to board)
    DICE_WIDTH = 220
    DICE_HEIGHT = 200
    # Move the dice box down to make room for timer/title
    dice_rect_local = pygame.Rect(BOARD_PADDING + BOARD_SIZE + 16, BOARD_PADDING + 24 + 40, DICE_WIDTH, DICE_HEIGHT)
    info_rect_local = pygame.Rect(dice_rect_local.x, dice_rect_local.y + dice_rect_local.height + 12, 240, 300)

    # Move power-up buttons down (user requested)
    # Previously: y = info_rect_local.y + info_rect_local.height - 100
    # New: move down by ~40 pixels to give more separation
    btn_mini_local = pygame.Rect(info_rect_local.x, info_rect_local.y + info_rect_local.height - 150, 130, 36)
    btn_swap_local = pygame.Rect(info_rect_local.x + 150, info_rect_local.y + info_rect_local.height - 150, 130, 36)

    # Make dice_rect available to helper functions that reference the module-level name
    dice_rect = dice_rect_local

    # Attempt to load dice images dice_1.png ... dice_6.png (expected 120x120)
    dice_images_local = {}
    images_loaded_local = True
    for i in range(1, 7):
        base_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "."
        path = os.path.join(base_dir, "snakes_assets", f"dice_{i}.png")
        try:
            img = pygame.image.load(path).convert_alpha()
            if img.get_width() != 120 or img.get_height() != 120:
                img = pygame.transform.smoothscale(img, (120, 120))
            dice_images_local[i] = img
        except Exception:
            images_loaded_local = False
            dice_images_local = {}
            break

    # Load player icon (raven.png) if available. Scale to TOKEN_SIZE.
    player_icon = None
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "."
        raven_path = os.path.join(base_dir, "snakes_assets", "raven.png")
        if os.path.exists(raven_path):
            raw_icon = pygame.image.load(raven_path).convert_alpha()
            # desired token size (diameter). Adjust as needed.
            TOKEN_SIZE = 42
            if raw_icon.get_width() != TOKEN_SIZE or raw_icon.get_height() != TOKEN_SIZE:
                player_icon = pygame.transform.smoothscale(raw_icon, (TOKEN_SIZE, TOKEN_SIZE))
            else:
                player_icon = raw_icon
    except Exception:
        player_icon = None

    # Player state
    player = {
        'square': 1,
        'color': BLUE,
        'last_roll': None,
        'has_won': False,
        'mini_ladder_count': 2,
        'swap_tiles_count': 3,
    }

    running = True
    message = "Click dice or press SPACE to roll"
    show_win_time = None
    swap_mode = False
    swap_first = None
    ROLL_BUTTON_AREA = dice_rect_local

    # inner helpers close over these local names
    def roll_dice_animation_inner():
        return roll_dice_animation_impl(screen, dice_rect_local, font_dice, player, player['color'], dice_images_local if images_loaded_local else None)

    def move_player_along_numeric_inner(target):
        return move_player_along_numeric_impl(player, target, screen, player['color'], dice_images_local if images_loaded_local else None)

    def animate_along_path_inner(start_sq, end_sq):
        return animate_along_path_impl(player, start_sq, end_sq, screen, player['color'], dice_images_local if images_loaded_local else None)

    # main loop
    result = {'action': 'exit'}
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                result = {'action': 'exit'}
                break

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Treat ESC as a level-skip: stop and return 'skipped' result
                    running = False
                    result = {'action': 'skipped'}
                    break

                if event.key == pygame.K_r:
                    player['square'] = 1
                    player['has_won'] = False
                    player['last_roll'] = None
                    player['mini_ladder_count'] = 2
                    player['swap_tiles_count'] = 3
                    message = "Game reset. Click dice or press SPACE to roll"
                    swap_mode = False
                    swap_first = None

                if event.key == pygame.K_SPACE and not player['has_won'] and not swap_mode:
                    roll = roll_dice_animation_inner()
                    player['last_roll'] = roll
                    proposed = player['square'] + roll
                    if proposed > 100:
                        message = f"Rolled {roll}. Overshoot 100 — no move."
                    else:
                        move_player_along_numeric_inner(proposed)
                        jumped = JUMPS.get(player['square'])
                        if jumped:
                            pygame.time.delay(160)
                            animate_along_path_inner(player['square'], jumped)
                            message = f"Rolled {roll}. Hit {'ladder' if jumped > proposed else 'snake'} to {jumped}."
                        else:
                            message = f"Rolled {roll}. Moved to {player['square']}."
                        if player['square'] == 100:
                            player['has_won'] = True
                            message = "You reached 100! You win! Press R to restart."
                            show_win_time = time.time()

                if event.key == pygame.K_m and not player['has_won']:
                    if player['mini_ladder_count'] > 0 and not swap_mode:
                        start, end = apply_mini_ladder(player)
                        player['mini_ladder_count'] -= 1
                        pygame.time.delay(120)
                        animate_along_path_inner(start, end)
                        message = f"Mini-ladder used: {start} -> {end}."
                        if player['square'] == 100:
                            player['has_won'] = True
                            message = "You reached 100! You win! Press R to restart."
                    else:
                        message = "No Mini Ladder charges left."

                if event.key == pygame.K_s and not player['has_won']:
                    if player['swap_tiles_count'] > 0:
                        swap_mode = True
                        swap_first = None
                        message = "Swap mode: click first tile (adjacent rule will apply)."
                    else:
                        message = "No Swap Tiles charges left."

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                # click on dice
                if ROLL_BUTTON_AREA.collidepoint(mx, my) and not player['has_won'] and not swap_mode:
                    roll = roll_dice_animation_inner()
                    player['last_roll'] = roll
                    proposed = player['square'] + roll
                    if proposed > 100:
                        message = f"Rolled {roll}. Overshoot 100 — no move."
                    else:
                        move_player_along_numeric_inner(proposed)
                        jumped = JUMPS.get(player['square'])
                        if jumped:
                            pygame.time.delay(160)
                            animate_along_path_inner(player['square'], jumped)
                            message = f"Rolled {roll}. Hit {'ladder' if jumped > proposed else 'snake'} to {jumped}."
                        else:
                            message = f"Rolled {roll}. Moved to {player['square']}."
                        if player['square'] == 100:
                            player['has_won'] = True
                            message = "You reached 100! You win! Press R to restart."
                    continue

                # powerup buttons
                if btn_mini_local.collidepoint(mx, my) and not player['has_won'] and not swap_mode:
                    if player['mini_ladder_count'] > 0:
                        start, end = apply_mini_ladder(player)
                        player['mini_ladder_count'] -= 1
                        pygame.time.delay(120)
                        animate_along_path_inner(start, end)
                        message = f"Mini-ladder used: {start} -> {end}."
                        if player['square'] == 100:
                            player['has_won'] = True
                            message = "You reached 100! You win! Press R to restart."
                    else:
                        message = "No Mini Ladder charges left."
                    continue

                if btn_swap_local.collidepoint(mx, my) and not player['has_won']:
                    if player['swap_tiles_count'] > 0:
                        swap_mode = True
                        swap_first = None
                        message = "Swap mode: click first tile to swap."
                    else:
                        message = "No Swap Tiles charges left."
                    continue

                # swap mode selection
                if swap_mode:
                    clicked_cell = coord_to_cell_index(mx, my)
                    if clicked_cell is None:
                        message = "Click on a tile to select it."
                        continue
                    if swap_first is None:
                        swap_first = clicked_cell
                        message = f"First tile selected: {swap_first}. Click adjacent tile to swap or click elsewhere to cancel."
                        continue
                    else:
                        first = swap_first
                        second = clicked_cell
                        if first == second:
                            message = "Selected same tile twice. Swap canceled."
                            swap_mode = False
                            swap_first = None
                        elif not cells_adjacent(first, second):
                            message = "Tiles are not adjacent (horiz/vert). Swap canceled."
                            swap_mode = False
                            swap_first = None
                        else:
                            # perform swap
                            swap_two_tiles(first, second)
                            player['swap_tiles_count'] -= 1
                            # After swapping, if a jump now starts on player's square, move them
                            jumped = JUMPS.get(player['square'])
                            if jumped:
                                pygame.time.delay(120)
                                animate_along_path_inner(player['square'], jumped)
                                if jumped > player['square']:
                                    move_type = 'ladder'
                                else:
                                    move_type = 'snake'
                                message = f"Swapped tiles {first} and {second}. A {move_type} appeared and moved you to {player['square']}."
                                if player['square'] == 100:
                                    player['has_won'] = True
                                    message = "You reached 100! You win! Press R to restart."
                            else:
                                message = f"Swapped tiles {first} and {second} (contents swapped)."
                            swap_mode = False
                            swap_first = None
                    continue

        # draw frame
        screen.fill(BACKGROUND)
        draw_board(screen, font_small)

        # Draw snakes first (below)
        draw_snakes(screen)

        # Draw grid numbers above snakes
        draw_grid_numbers(screen, font_small)

        # Draw ladders above snakes and numbers
        draw_ladders(screen)

        px, py = cell_index_to_coord(player['square'])
        draw_player(screen, (px, py), player['color'])

        # display running timer in top-right if TIMER_START provided (minutes:seconds)
        try:
            if TIMER_START is not None:
                elapsed_total = int(time.time() - float(TIMER_START))
                mins = elapsed_total // 60
                secs = elapsed_total % 60
                timer_str = f"{mins:02d}:{secs:02d}"
                timer_surf = font_small.render(f"Time {timer_str}", True, BLACK)
                padding = 12
                tx = width - padding - timer_surf.get_width()
                ty = padding
                screen.blit(timer_surf, (tx, ty))
        except Exception:
            pass

        # draw dice box and ensure title is placed above the box, not overlapping
        draw_dice(screen, dice_rect_local, player.get('last_roll'), font_dice, dice_images_local if images_loaded_local else None)
        title = font_medium.render("Dice", True, BLACK)
        # place title centered above the dice box with some spacing
        title_x = dice_rect_local.x + (dice_rect_local.width - title.get_width()) // 2
        title_y = dice_rect_local.y - title.get_height() - 8
        screen.blit(title, (title_x, title_y))

        # info lines (rendered with larger instruction font)
        info_lines = [
            message,
            "",
            "- Mini Ladder: Launch a ladder 3 squares up",
            "- Swap Tiles: Swap two adjacent tiles,",
            "changing snakes and ladders",
        ]
        iy = info_rect_local.y
        for line in info_lines:
            text = font_info.render(line, True, BLACK)
            screen.blit(text, (info_rect_local.x, iy))
            iy += text.get_height() + 6

        # draw buttons (moved down)
        pygame.draw.rect(screen, BUTTON_BG, btn_mini_local)
        pygame.draw.rect(screen, BUTTON_BORDER, btn_mini_local, 1)
        ms_text = font_small.render(f"Mini Ladder (M) - {player['mini_ladder_count']} left", True, BLACK)
        screen.blit(ms_text, (btn_mini_local.x + 6, btn_mini_local.y + 8))

        pygame.draw.rect(screen, BUTTON_BG, btn_swap_local)
        pygame.draw.rect(screen, BUTTON_BORDER, btn_swap_local, 1)
        sw_text = font_small.render(f"Swap Tiles (S) - {player['swap_tiles_count']} left", True, BLACK)
        screen.blit(sw_text, (btn_swap_local.x + 6, btn_swap_local.y + 8))

        if swap_mode and swap_first:
            cx, cy = cell_index_to_coord(swap_first)
            rect = pygame.Rect(cx - CELL_SIZE // 2, cy - CELL_SIZE // 2, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, HIGHLIGHT, rect, 4)

        if swap_mode and not swap_first:
            prompt = font_medium.render("Swap mode: click first tile", True, BLACK)
            screen.blit(prompt, (BOARD_PADDING + BOARD_SIZE//2 - prompt.get_width()//2, BOARD_PADDING + BOARD_SIZE + 6))
        elif swap_mode and swap_first:
            prompt = font_medium.render("Swap mode: click adjacent tile to swap", True, BLACK)
            screen.blit(prompt, (BOARD_PADDING + BOARD_SIZE//2 - prompt.get_width()//2, BOARD_PADDING + BOARD_SIZE + 6))

        if player['has_won']:
            overlay = pygame.Surface((width, height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))
            win_text = font_large.render("You Win!", True, GOLD)
            sub_text = font_medium.render("Press R to play again or ESC to quit", True, WHITE)
            screen.blit(win_text, ((width - win_text.get_width()) // 2, height // 2 - 60))
            screen.blit(sub_text, ((width - sub_text.get_width()) // 2, height // 2 + 10))

        pygame.display.flip()
        clock.tick(FPS)

    # end main loop -> cleanup
    # construct result dict for caller
    if player.get('has_won'):
        result = {'action': 'finished'}
    # else result was set earlier, e.g. skipped or exit

    try:
        if on_finish:
            try:
                on_finish(result)
            except Exception:
                # do not allow on_finish errors to crash the game
                pass
    except Exception:
        pass
    # tidy up pygame so interpreter isn't left with initialized modules
    try:
        pygame.quit()
    except Exception:
        pass

    # If TIMER_START provided, include elapsed_seconds
    out = {'action': result.get('action', 'exit')}
    try:
        if TIMER_START is not None:
            out['elapsed_seconds'] = round(time.time() - float(TIMER_START), 3)
    except Exception:
        pass
    return out

# Implementations of animation helpers that require access to draw functions etc.
# Separated out so run_flash can call them cleanly.

def roll_dice_animation_impl(screen, dice_rect, font_dice, player_pos, player_color, dice_images):
    start = time.time()
    duration = 0.6
    last = None
    while time.time() - start < duration:
        face = random.randint(1, 6)
        if face != last:
            screen.fill(BACKGROUND)
            draw_board(screen, font_small)
            # draw snakes first so animation still looks consistent
            draw_snakes(screen)
            draw_grid_numbers(screen, font_small)
            draw_ladders(screen)
            px, py = cell_index_to_coord(player_pos['square'])
            draw_player(screen, (px, py), player_color)
            draw_dice(screen, dice_rect, face, font_dice, dice_images)
            pygame.display.flip()
            last = face
        pygame.time.delay(60)
    final = random.randint(1, 6)
    screen.fill(BACKGROUND)
    draw_board(screen, font_small)
    draw_snakes(screen)
    draw_grid_numbers(screen, font_small)
    draw_ladders(screen)
    px, py = cell_index_to_coord(player_pos['square'])
    draw_player(screen, (px, py), player_color)
    draw_dice(screen, dice_rect, final, font_dice, dice_images)
    pygame.display.flip()
    return final

def move_player_along_numeric_impl(player_pos, target_square, surface, player_color, dice_images):
    current_square = player_pos['square']
    if current_square == target_square:
        return
    step = 1 if target_square > current_square else -1
    for sq in range(current_square + step, target_square + step, step):
        pos = cell_index_to_coord(sq)
        surface.fill(BACKGROUND)
        draw_board(surface, font_small)
        draw_snakes(surface)
        draw_grid_numbers(surface, font_small)
        draw_ladders(surface)
        draw_player(surface, pos, player_color)
        draw_dice(surface, dice_rect, player_pos.get('last_roll', None), font_dice, dice_images)
        pygame.display.flip()
        pygame.time.delay(100)
    player_pos['square'] = target_square

def animate_along_path_impl(player_pos, start_sq, end_sq, surface, player_color, dice_images):
    pts = get_jump_path_points(start_sq, end_sq)
    if not pts:
        player_pos['square'] = end_sq
        return
    for p in pts:
        ix, iy = p
        surface.fill(BACKGROUND)
        draw_board(surface, font_small)
        draw_snakes(surface)
        draw_grid_numbers(surface, font_small)
        draw_ladders(surface)
        draw_player(surface, (ix, iy), player_color)
        draw_dice(surface, dice_rect, player_pos.get('last_roll', None), font_dice, dice_images)
        pygame.display.flip()
        pygame.time.delay(40)
    player_pos['square'] = end_sq

def apply_mini_ladder(player_pos):
    start = player_pos['square']
    end = min(100, start + 3)
    JUMPS[start] = end
    return start, end

def swap_two_tiles(a, b):
    if a == b:
        return
    new_jumps = {}
    for start, end in list(JUMPS.items()):
        new_start = b if start == a else a if start == b else start
        new_end = b if end == a else a if end == b else end
        if new_start != new_end:
            new_jumps[new_start] = new_end
    JUMPS.clear()
    JUMPS.update(new_jumps)

def cells_adjacent(a, b):
    if a < 1 or a > 100 or b < 1 or b > 100:
        return False
    def rowcol(cell):
        idx = cell - 1
        row_from_bottom = idx // 10
        within_row = idx % 10
        if row_from_bottom % 2 == 0:
            col = within_row
        else:
            col = 9 - within_row
        return row_from_bottom, col
    ra, ca = rowcol(a)
    rb, cb = rowcol(b)
    return (abs(ra - rb) + abs(ca - cb)) == 1

# If run as a script, run the game and print a minimal JSON result for the launcher
if __name__ == "__main__":
    # accept optional args: player_name, timer_start
    player_name = None
    start_ts = None
    if len(sys.argv) > 1:
        player_name = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            start_ts = float(sys.argv[2])
        except Exception:
            start_ts = None
    # set module-level timer start for run_flash to use
    TIMER_START = start_ts
    out = run_flash()
    # If run_flash returned a dict, print it. Ensure elapsed_seconds is present if timer used.
    if isinstance(out, dict):
        print(json.dumps(out))
    else:
        print(json.dumps({'action': 'exit'}))