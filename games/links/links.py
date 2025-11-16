from typing import List, Dict, Optional, Tuple, Any
import pygame
import sys
import os
import json
import re
import time

# UI constants
SCREEN_W = 800
SCREEN_H = 600
FPS = 60

MARGIN = 20
# Use the full width for the article area (no sidebar)
LEFT_COL_W = SCREEN_W - 2 * MARGIN

TITLE_FONT_SIZE = 28
BODY_FONT_SIZE = 18
INFO_FONT_SIZE = 20
LINK_UNDERLINE = True

BG = (250, 250, 250)  # light wiki-like background
TEXT_COLOR = (20, 20, 20)
TITLE_COLOR = (10, 10, 10)
LINK_BLUE = (6, 69, 173)      # #0645ad
LINK_PURPLE = (85, 26, 139)   # visited
HOVER_HL = (235, 245, 255, 120)    # hover background (with alpha)
BUTTON_BG = (230, 230, 230)
BUTTON_BORDER = (160, 160, 160)
ERROR_BG = (255, 245, 245)
ERROR_BORDER = (200, 80, 80)
WHITE = (255, 255, 255)

# Header texts
HEADER_TEXT = "Wikipedia"
SUBHEADER_TEXT = "Navigate to Edgar Allan Poe to win"

TOKEN_RE = re.compile(r"\[\[([^\]]+)\]\]")

# Parser helpers -------------------------------------------------------------

def load_articles(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def build_index(articles: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    idx = {}
    for a in articles:
        idx[a["id"]] = a
    return idx

def parse_content_into_segments(text: str, index: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse content into a list of segments:
      {"type":"text", "text": "..."}
      {"type":"link", "text":"...", "target":"id", "dead":bool, "visited":False, "rects":[], "trailing_space":bool}
    Accepts token forms:
      [[target|Link Text]] OR [[Link Text|target]] OR [[target]]

    For two-part tokens [[a|b]] when neither a nor b matches an id:
      treat a as target and b as display text (so [[dead_link|systems]] shows "systems" linking to dead_link).

    Adds "trailing_space" flag to link segments: True if original content had whitespace immediately after the token.
    This lets rendering avoid inserting a visible space before punctuation that follows a link.
    """
    segments = []
    last = 0
    for m in TOKEN_RE.finditer(text):
        if m.start() > last:
            segments.append({"type":"text", "text": text[last:m.start()]})
        inner = m.group(1)
        parts = [p.strip() for p in inner.split("|")]
        if len(parts) == 1:
            candidate = parts[0]
            if candidate in index:
                seg_text = index[candidate].get("title", candidate)
                target = candidate
                dead = False
            else:
                seg_text = candidate
                target = candidate
                dead = True
        else:
            a, b = parts[0], parts[1]
            if a in index:
                target = a
                seg_text = b or index[a].get("title", a)
                dead = False
            elif b in index:
                target = b
                seg_text = a or index[b].get("title", b)
                dead = False
            else:
                target = a
                seg_text = b
                dead = True

        # Determine whether there is whitespace immediately after the token in the original text
        trailing_space = False
        if m.end() < len(text):
            trailing_space = text[m.end()].isspace()

        segments.append({
            "type": "link",
            "text": seg_text,
            "target": target,
            "dead": dead,
            "visited": False,
            "rects": [],
            "trailing_space": trailing_space
        })
        last = m.end()
    if last < len(text):
        segments.append({"type":"text", "text": text[last:]})
    return segments

# Rendering helpers ----------------------------------------------------------

def _merge_rects_on_same_line(rects: List[pygame.Rect], line_tol: int = 3) -> List[pygame.Rect]:
    """
    Merge rects that belong to the same visual line (top coordinate within tolerance).
    Returns a list of merged rects sorted by top then left.
    """
    if not rects:
        return []
    rects_sorted = sorted(rects, key=lambda r: (r.top, r.left))
    merged: List[pygame.Rect] = []
    for r in rects_sorted:
        if not merged:
            merged.append(r.copy())
            continue
        last = merged[-1]
        if abs(r.top - last.top) <= line_tol:
            new_left = min(last.left, r.left)
            new_right = max(last.right, r.right)
            new_top = min(last.top, r.top)
            new_height = max(last.height, r.height)
            merged[-1] = pygame.Rect(new_left, new_top, new_right - new_left, new_height)
        else:
            merged.append(r.copy())
    return merged

_TOKEN_WITH_SPACES_RE = re.compile(r'(\S+)(\s*)', re.U)

def render_wrapped_segments(segments: List[Dict[str, Any]],
                            font: pygame.font.Font,
                            max_width: int,
                            line_spacing: int) -> Tuple[pygame.Surface, int]:
    """
    Renders segments into a Surface with wrapped lines and returns (surface, height)
    Also populates 'rects' in link segments with pixel rects relative to the surface.
    Link rects and underlines tightly fit link text (no surrounding spaces).
    Spacing is rendered as separate glyphs and only inserted when the original content had spaces,
    avoiding gaps before punctuation that immediately follows a link token.
    """
    surface = pygame.Surface((max_width, 4000), pygame.SRCALPHA)
    surface.fill((0,0,0,0))
    x = 0
    y = 0
    line_h = font.get_linesize() + line_spacing

    for seg in segments:
        if seg["type"] == "link":
            seg["rects"] = []

    words_cache: Dict[Tuple[str, Tuple[int,int,int]], pygame.Surface] = {}

    def render_word_surface(s: str, color: Tuple[int,int,int]) -> pygame.Surface:
        key = (s, color)
        if key not in words_cache:
            words_cache[key] = font.render(s, True, color)
        return words_cache[key]

    for i, seg in enumerate(segments):
        if seg["type"] == "text":
            text = seg["text"]
            # tokenise into (token, following_whitespace) pairs preserving punctuation
            for m in _TOKEN_WITH_SPACES_RE.finditer(text):
                token = m.group(1)
                following_space = m.group(2)  # may be ''
                # render token (no trailing space included)
                token_surf = render_word_surface(token, TEXT_COLOR)
                space_surf = render_word_surface(" ", TEXT_COLOR) if following_space else None
                total_w = token_surf.get_width() + (space_surf.get_width() if space_surf else 0)
                if x + total_w > max_width and x > 0:
                    x = 0
                    y += line_h
                surface.blit(token_surf, (x, y))
                if space_surf:
                    surface.blit(space_surf, (x + token_surf.get_width(), y))
                x += total_w
        else:
            # link segment
            color = LINK_PURPLE if seg.get("visited", False) else LINK_BLUE
            link_text = seg["text"]
            # tokenize link text but do NOT assume a trailing space after the whole link;
            # we'll only render a space after the final word if either the link text had one
            # or the original content had whitespace immediately after the token (seg['trailing_space'])
            tokens = list(_TOKEN_WITH_SPACES_RE.finditer(link_text))
            for idx, m2 in enumerate(tokens):
                token = m2.group(1)
                following_space_inside_link = m2.group(2)  # internal space inside displayed link text
                token_surf = render_word_surface(token, color)
                space_surf_inside = render_word_surface(" ", color) if following_space_inside_link else None

                # decide whether to include a post-word space (affects wrapping calculations)
                include_space_after = False
                # If there is an internal space in link text after this token, include it.
                if following_space_inside_link:
                    include_space_after = True
                else:
                    # if this is the last token in the link, include space AFTER the link
                    # only if the original content had whitespace immediately after the token
                    if idx == len(tokens) - 1 and seg.get("trailing_space", False):
                        include_space_after = True
                total_w = token_surf.get_width() + (space_surf_inside.get_width() if include_space_after and space_surf_inside else (font.size(" ")[0] if include_space_after else 0))

                if x + total_w > max_width and x > 0:
                    x = 0
                    y += line_h

                # blit the token (no trailing space inside the token's rect)
                surface.blit(token_surf, (x, y))
                # record rect for token itself (exclude the space)
                seg["rects"].append(pygame.Rect(x, y, token_surf.get_width(), token_surf.get_height()))

                # blit the space glyph if we decided to include one
                if include_space_after:
                    # prefer rendering the same-color space (space_surf_inside) if present, otherwise render a plain space
                    if space_surf_inside:
                        surface.blit(space_surf_inside, (x + token_surf.get_width(), y))
                        x += token_surf.get_width() + space_surf_inside.get_width()
                    else:
                        # render default space in the same color
                        space_surf = render_word_surface(" ", color)
                        surface.blit(space_surf, (x + token_surf.get_width(), y))
                        x += token_surf.get_width() + space_surf.get_width()
                else:
                    x += token_surf.get_width()

    # Merge per-line rects so underline and hit area are continuous for multi-word links
    for seg in segments:
        if seg["type"] == "link":
            merged = _merge_rects_on_same_line(seg["rects"])
            seg["rects"] = merged
            # draw underline per merged rect (continuous)
            if LINK_UNDERLINE:
                for r in merged:
                    uy = r.top + r.height - 2
                    pygame.draw.line(surface, LINK_PURPLE if seg.get("visited", False) else LINK_BLUE,
                                     (r.left, uy), (r.right - 2, uy), 1)

    height = y + line_h
    if height < 1:
        height = 1
    cropped = pygame.Surface((max_width, height), pygame.SRCALPHA)
    cropped.blit(surface, (0,0), (0,0,max_width,height))
    return cropped, int(height)

# Main game class ------------------------------------------------------------

class LinksGame:
    def __init__(self, json_path: str, start_id: Optional[str] = None, timer_start: Optional[float] = None):
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Wikipedia")
        self.clock = pygame.time.Clock()

        # fonts (serif body like Wikipedia)
        try:
            self.header_font = pygame.font.SysFont("Georgia", 40, bold=True)
            self.subheader_font = pygame.font.SysFont("Times New Roman", 22)
            self.title_font = pygame.font.SysFont("Georgia", TITLE_FONT_SIZE, bold=True)
            self.body_font = pygame.font.SysFont("Times New Roman", BODY_FONT_SIZE)
            self.info_font = pygame.font.SysFont("Arial", INFO_FONT_SIZE)
        except Exception:
            self.header_font = pygame.font.SysFont(None, 40, bold=True)
            self.subheader_font = pygame.font.SysFont(None, 25)
            self.title_font = pygame.font.SysFont(None, TITLE_FONT_SIZE, bold=True)
            self.body_font = pygame.font.SysFont(None, BODY_FONT_SIZE)
            self.info_font = pygame.font.SysFont(None, INFO_FONT_SIZE)

        # header surfaces and height
        self.header_surf = self.header_font.render(HEADER_TEXT, True, TITLE_COLOR)
        self.subheader_surf = self.subheader_font.render(SUBHEADER_TEXT, True, LINK_BLUE)
        # small spacing
        self.header_total_h = self.header_surf.get_height() + self.subheader_surf.get_height() + 12

        # load articles
        base = os.path.dirname(os.path.abspath(__file__))
        full = json_path if os.path.isabs(json_path) else os.path.join(base, os.path.basename(json_path))
        self.articles = load_articles(full)
        self.index = build_index(self.articles)

        # starting article
        if start_id and start_id in self.index:
            self.current_id = start_id
        else:
            self.current_id = self.articles[0]["id"] if self.articles else None

        # UI state
        self.history: List[str] = [self.current_id] if self.current_id else []
        self.visited_links = set()
        self.timer_start = timer_start
        self.start_time = time.time() if timer_start is None else timer_start
        self.result = {"action": "exit"}

        # content surfaces / cache
        self.content_surface = None
        self.content_height = 0
        self.scroll_y = 0

        # modal state (for 404)
        self.show_404 = False
        self.error_msg = ""
        self.modal_button_rect = None

        # win modal state
        self.win_pending = False
        self.win_time = None
        self.show_win_modal = False

        # parsed segments cache
        self.segments_cache = {}
        self.link_segments = []
        self.hovered_link = None

        self.prepare_current_article()

    def prepare_current_article(self):
        if not self.current_id or self.current_id not in self.index:
            return
        art = self.index[self.current_id]
        title = art.get("title", "")
        content = art.get("content", "")

        segments = parse_content_into_segments(content, self.index)
        self.segments_cache[self.current_id] = segments

        title_surf = self.title_font.render(title, True, TITLE_COLOR)
        title_h = title_surf.get_height() + 8

        # available width for body: full window minus margins
        body_surface, body_h = render_wrapped_segments(segments, self.body_font, LEFT_COL_W - 2*MARGIN, 2)

        total_h = title_h + body_h + 4*MARGIN
        surf = pygame.Surface((LEFT_COL_W, max(total_h, SCREEN_H - (2*MARGIN + self.header_total_h))), pygame.SRCALPHA)
        surf.fill((0,0,0,0))

        surf.fill(WHITE)
        surf.blit(title_surf, (MARGIN, MARGIN))
        surf.blit(body_surface, (MARGIN, MARGIN + title_h))

        self.content_surface = surf
        self.content_height = int(total_h)
        visible_h = SCREEN_H - (2 * MARGIN + self.header_total_h)
        self.scroll_y = max(0, min(self.scroll_y, self.content_height - visible_h))

        self.link_segments = []
        body_top = MARGIN + title_h
        for seg in segments:
            if seg["type"] == "link":
                seg_rects_global = [pygame.Rect(r.x + MARGIN, r.y + body_top, r.w, r.h) for r in seg["rects"]]
                self.link_segments.append((seg, seg_rects_global))

    def go_to_article(self, target_id: str):
        if target_id not in self.index:
            self.show_404 = True
            self.error_msg = f"Error 404: '{target_id}' not found."
            return
        self.history.append(target_id)
        self.current_id = target_id
        self.visited_links.add(target_id)
        for art_id, segments in self.segments_cache.items():
            for seg in segments:
                if seg["type"] == "link" and seg["target"] == target_id:
                    seg["visited"] = True
        self.prepare_current_article()
        if target_id == "eap":
            self.win_pending = True
            self.win_time = time.time()
            self.show_win_modal = False

    def go_back(self):
        if len(self.history) <= 1:
            return
        self.history.pop()
        self.current_id = self.history[-1]
        self.prepare_current_article()

    def handle_click_at(self, x: int, y: int):
        left_x = MARGIN
        left_y = MARGIN + self.header_total_h
        content_view_rect = pygame.Rect(left_x, left_y, LEFT_COL_W, SCREEN_H - (2*MARGIN + self.header_total_h))
        if content_view_rect.collidepoint(x, y):
            rel_x = x - left_x
            rel_y = y - left_y + self.scroll_y
            for seg, rects in self.link_segments:
                for r in rects:
                    if r.collidepoint(rel_x, rel_y):
                        if seg.get("dead", False):
                            self.show_404 = True
                            self.error_msg = f"Error 404: '{seg['target']}' not found."
                            return
                        else:
                            self.go_to_article(seg["target"])
                            return
        if self.show_404 and self.modal_button_rect and self.modal_button_rect.collidepoint(x, y):
            self.show_404 = False
            self.modal_button_rect = None
            return
        if self.show_win_modal:
            self.on_win()

    def on_win(self):
        elapsed = time.time() - self.start_time
        out = {
            "action": "finished",
            "path": self.history.copy(),
            "elapsed_seconds": round(elapsed, 3)
        }
        print(json.dumps(out))
        pygame.quit()
        sys.exit(0)

    def draw(self):
        self.screen.fill(BG)

        # draw header and subheader at the top-left
        hx = MARGIN
        hy = MARGIN
        self.screen.blit(self.header_surf, (hx, hy))
        self.screen.blit(self.subheader_surf, (hx, hy + self.header_surf.get_height() + 6))

        # content area top accounts for header height
        left_x = MARGIN
        left_y = MARGIN + self.header_total_h
        content_h = int(SCREEN_H - (2 * MARGIN + self.header_total_h))
        pygame.draw.rect(self.screen, WHITE, pygame.Rect(left_x, left_y, int(LEFT_COL_W), content_h))
        if self.content_surface:
            self.screen.blit(self.content_surface, (left_x, left_y - int(self.scroll_y)))

        # timer at top-right (next to header)
        if self.start_time is not None:
            elapsed = int(time.time() - float(self.start_time))
            mins = elapsed // 60
            secs = elapsed % 60
            timer_str = f"{mins:02d}:{secs:02d}"
            t_surf = self.info_font.render(f"Time {timer_str}", True, TEXT_COLOR)
            self.screen.blit(t_surf, (SCREEN_W - MARGIN - t_surf.get_width(), MARGIN))

        # hover: semi-transparent overlay for hovered merged rect
        mx, my = pygame.mouse.get_pos()
        rel_x = mx - left_x
        rel_y = my - left_y + self.scroll_y
        hovered = None
        for seg, rects in self.link_segments:
            for r in rects:
                if r.collidepoint(rel_x, rel_y):
                    hovered = (seg, r)
                    break
            if hovered:
                break
        if hovered:
            seg, rect = hovered
            hl_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            hl_color = HOVER_HL  # RGBA
            hl_surf.fill(hl_color)
            dest_x = rect.x + left_x
            dest_y = rect.y + left_y - int(self.scroll_y)
            self.screen.blit(hl_surf, (dest_x, dest_y))

        # win pending: after 1s show modal
        if self.win_pending and not self.show_win_modal:
            if self.win_time and (time.time() - self.win_time) >= 1.0:
                self.show_win_modal = True

        if self.show_404:
            modal_w = 420
            modal_h = 160
            mx_c = (SCREEN_W - modal_w) // 2
            my_c = (SCREEN_H - modal_h) // 2
            pygame.draw.rect(self.screen, ERROR_BG, (mx_c, my_c, modal_w, modal_h))
            pygame.draw.rect(self.screen, ERROR_BORDER, (mx_c, my_c, modal_w, modal_h), 2)
            err_title = self.title_font.render("Error 404", True, ERROR_BORDER)
            self.screen.blit(err_title, (mx_c + 18, my_c + 18))
            err_msg = self.info_font.render(self.error_msg, True, TEXT_COLOR)
            self.screen.blit(err_msg, (mx_c + 18, my_c + 60))
            btn = pygame.Rect(mx_c + modal_w//2 - 60, my_c + modal_h - 48, 120, 32)
            pygame.draw.rect(self.screen, BUTTON_BG, btn)
            pygame.draw.rect(self.screen, BUTTON_BORDER, btn, 1)
            ok = self.info_font.render("Go back", True, TEXT_COLOR)
            ok_rect = ok.get_rect(center=btn.center)
            self.screen.blit(ok, ok_rect)
            self.modal_button_rect = btn

        if self.show_win_modal:
            modal_w = 420
            modal_h = 120
            mx_c = (SCREEN_W - modal_w) // 2
            my_c = (SCREEN_H - modal_h) // 2
            pygame.draw.rect(self.screen, (245, 255, 245), (mx_c, my_c, modal_w, modal_h))
            pygame.draw.rect(self.screen, (80, 160, 90), (mx_c, my_c, modal_w, modal_h), 2)
            win_title = self.title_font.render("You win!", True, (20, 100, 40))
            self.screen.blit(win_title, (mx_c + 18, my_c + 18))
            sub = self.info_font.render("Press Enter to continue.", True, TEXT_COLOR)
            self.screen.blit(sub, (mx_c + 18, my_c + 60))

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                    self.result = {"action": "exit"}
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        running = False
                        self.result = {"action": "skipped"}
                    elif ev.key == pygame.K_BACKSPACE:
                        self.go_back()
                    elif ev.key == pygame.K_DOWN:
                        self.scroll_y = min(self.scroll_y + 40, max(0, self.content_height - (SCREEN_H - (2*MARGIN + self.header_total_h))))
                    elif ev.key == pygame.K_UP:
                        self.scroll_y = max(self.scroll_y - 40, 0)
                    elif ev.key == pygame.K_RETURN:
                        if self.show_404:
                            self.show_404 = False
                            self.modal_button_rect = None
                        elif self.show_win_modal:
                            self.on_win()
                elif ev.type == pygame.MOUSEBUTTONDOWN:
                    if ev.button == 1:
                        self.handle_click_at(ev.pos[0], ev.pos[1])
                    elif ev.button == 4:
                        self.scroll_y = max(self.scroll_y - 40, 0)
                    elif ev.button == 5:
                        self.scroll_y = min(self.scroll_y + 40, max(0, self.content_height - (SCREEN_H - (2*MARGIN + self.header_total_h))))
            self.draw()
        elapsed_seconds = None
        try:
            elapsed_seconds = round(time.time() - float(self.start_time), 3)
        except Exception:
            pass
        out = {"action": self.result.get("action", "exit")}
        if elapsed_seconds is not None:
            out["elapsed_seconds"] = elapsed_seconds
        print(json.dumps(out))
        pygame.quit()
        return out

# Entry point ----------------------------------------------------------------

def main(argv):
    start_article = None
    timer_start = None
    if len(argv) > 1:
        start_article = argv[1]
    if len(argv) > 2:
        try:
            timer_start = float(argv[2])
        except Exception:
            timer_start = None

    base = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base, "links.json")
    if not os.path.exists(json_path):
        json_path = "links.json"
        if not os.path.exists(json_path):
            print(json.dumps({"action": "exit", "error": "links.json not found"}))
            return

    game = LinksGame(json_path=json_path, start_id=start_article, timer_start=timer_start)
    return game.run()

if __name__ == "__main__":
    main(sys.argv)