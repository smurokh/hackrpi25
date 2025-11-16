import pygame
import sys
import json
import time
from typing import Optional

pygame.init()

# ---------- Constants ----------
WIDTH, HEIGHT = 800, 600
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Old Style Terminal")

FONT = pygame.font.SysFont("Courier New", 32)
BIGFONT = pygame.font.SysFont("Courier New", 48)
SMALLFONT = pygame.font.SysFont("Courier New", 20)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
GREY = (180, 180, 180)

# ---------- Game Variables ----------
state = "menu"  # or "selection"
menu_message = "Press ENTER to start"
options = {
    "Entry": [
        "You enter the house. The lights are already on, though dim. You see three doors, all closed. Which direction do you go? ",
        "Forward",
        "Left",
        "Right",
    ],
    "Exit" : [
        "The door won't budge: it has a lock.",
        "Back",
    ],
    "Sheets" : [
        "You open the door and see an empty room, save for a paper with six sheets of paper on it, numbered one through six.",
        "One",
        "Two",
        "Three",
        "Four",
        "Five",
        "Back"
    ],
    "Lockbox" : [
        "You open the door and see a table with a strange box on it, with a code entry. Maybe you could open the box if you found a code? ",
        "Leave",
        "Enter Code"
    ],
    "Sheet1" : [
        "The sheet has several points on it, all numbered. Connect them, or count the number of dots? ",
        "Connect",
        "Count"
    ],
    "Sheet1 Connected" : [
        "The lines connect to form the number 22.",
        "Check another"
    ],
    "Sheet1 Counted" : [
        "There are 22 dots on the page.",
        "Check another"
    ],
    "Sheet2" : [
        "The sheet has the roman numeral XIV.",
        "Check another"
    ],
    "Sheet3" : [
        "The sheet has a picture of a pie, then a minus sign and the number 2.14...?",
        "Check another"
    ],
    "Sheet4" : [
        "On the sheet are the numbers 72, 2, and 2. It looks as though something between them was erased, and it appears to be the same symbol between both pairs.",
        "Check another"
    ],
    "Sheet5" : [
        "On the sheet is a sequence of numbers: 1, 1, 2, 3, __, 8, 13",
        "Check another"
    ],
    "Key" : [
        "You notice another sheet, containing a table of numbers and letters. It maps a to 1, b to 2, and so on. Perhaps by converting the numbers you found and rearranging them, you can form a word? ",
        "Back"
    ],
    "Enter code" : [
        "What code will you try? ",
        "STAIRS",
        "SITRAS",
        "TIRSSA",
        "SISART",
        "ATSIRS",
        "ISTRAS" # i dont think these matter anymore but im scared to touch them
    ],
    "Open" : [
        "The lockbox clicks open, revealing a small key inside.",
        "Back"
    ],
    "Failure" : [
        "Nothing happened.",
        "Back"
    ],
    "Insert Key" : [
        "You insert the key into the door lock, and it clicks open. Proceed, and see what lies in wait for you. ",
        "Move forward"
    ]
}
# selected is the currently-highlighted option index within the active scene's option list
# index 0 is a descriptive line and must not be selectable, so default to 1
selected = 1
scene = "Entry"
checked = []
code_input = ""

# ---------- Draw Functions ----------
def wrap_text(text, font, max_width):
    """Return a list of lines where each line's pixel width <= max_width.

    Splits on spaces, and if a single word is wider than max_width it will
    be broken across characters.
    """
    words = text.split(' ')
    lines = []
    current = ""

    for word in words:
        if current:
            test = current + ' ' + word
        else:
            test = word

        # If the test fits, accept it
        if font.size(test)[0] <= max_width:
            current = test
        else:
            # If current has content, push it as a line
            if current:
                lines.append(current)
                current = ""

            # If the single word is too long, break it into chunks
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
                    current = part
            else:
                current = word

    if current:
        lines.append(current)

    return lines

def draw_selection(scene=0):
    """Draw the current selection screen. Does NOT flip the display."""
    WIN.fill(BLACK)
    x = 50
    y = 50
    max_width = WIDTH - 2 * x
    line_height = FONT.get_linesize()

    current_options = options[scene]
    # If we're on the Enter-code scene, only show the descriptive line
    if scene == "Enter code":
        desc = current_options[0]
        wrapped_lines = wrap_text(desc, FONT, max_width)
        for line in wrapped_lines:
            text_surf = FONT.render(line, True, GREY)
            WIN.blit(text_surf, (x, y))
            y += line_height + 4
        y += 10
    else:
        for i, option in enumerate(current_options):
            # index 0 is descriptive and should appear disabled
            if i == 0:
                color = GREY
            else:
                color = YELLOW if i == selected else WHITE

            wrapped_lines = wrap_text(option, FONT, max_width)
            for line in wrapped_lines:
                text_surf = FONT.render(line, True, color)
                WIN.blit(text_surf, (x, y))
                y += line_height + 4

            # Add extra spacing between options
            y += 10

    # do not call pygame.display.update() here; caller will flip after any overlays
    # If this scene expects typed input, draw the input buffer under the options
    try:
        if scene == "Enter code":
            inp_label = FONT.render("Type code and press ENTER:", True, YELLOW)
            # draw the label below last option
            WIN.blit(inp_label, (50, HEIGHT - 120))
            # show the current buffer (uppercased) with a caret
            display_text = code_input.upper() + ("_" if int(time.time() * 2) % 2 == 0 else "")
            inp_text = BIGFONT.render(display_text, True, WHITE)
            WIN.blit(inp_text, (50, HEIGHT - 80))
    except Exception:
        pass


# ---------- Main Loop ----------
def run(name: Optional[str] = None, start_ts: Optional[float] = None):
    """
    name: optional player name to show in the menu message
    start_ts: optional epoch timestamp (float). If provided, the game will compute elapsed time
              as time.time() - start_ts, display it during play, and include
              'elapsed_seconds' in the JSON printed on exit.
    """
    global selected, scene, checked, menu_message, code_input
    if name:
        menu_message = f"Press ENTER to start, {name}"

    running = True
    result = {'action': 'exit'}

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # user closed window -> cleanly stop and return exit result
                running = False
                result = {'action': 'exit'}
                break

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # ESC is a level-skipper: stop loop and return a 'skipped' result
                    running = False
                    result = {'action': 'skipped'}
                    break

                current_options = options[scene]
                n = len(current_options)
                # if there are no selectable entries, ignore navigation
                if n <= 1:
                    continue

                # Special handling for the "Enter code" scene: allow typing only
                if scene == "Enter code":
                    if event.key == pygame.K_BACKSPACE:
                        code_input = code_input[:-1]
                    elif event.key == pygame.K_RETURN:
                        # If user typed something, submit the typed code
                        if code_input:
                            typed = code_input.upper()
                            code_input = ""
                            if typed == "RAVEN":
                                scene = "Open"
                                if ("Insert Key" not in options["Exit"]):
                                    options["Exit"].append("Insert Key")
                            else:
                                scene = "Failure"
                            selected = 1
                        else:
                            # empty submission: ignore
                            pass
                    else:
                        # Text input: append printable unicode characters
                        try:
                            ch = event.unicode
                            if ch and ch.isprintable() and ch not in ('\r', '\n'):
                                code_input += ch
                        except Exception:
                            pass
                    # done handling Enter code scene
                    # reset selection to the first real option when leaving will be handled elsewhere
                else:
                    if event.key == pygame.K_UP:
                        selected -= 1
                        if selected < 1:
                            selected = n - 1
                    elif event.key == pygame.K_DOWN:
                        selected += 1
                        if selected > n - 1:
                            selected = 1
                    elif event.key == pygame.K_RETURN:
                        if(current_options[selected] == "Forward"):
                            scene = "Exit"
                        elif(current_options[selected] == "Back"):
                            scene = "Entry"
                        elif(current_options[selected] == "Left"):
                            scene = "Sheets"
                        elif(current_options[selected] == "Right"):
                            scene = "Lockbox"
                        elif(current_options[selected] == "Leave"):
                            scene = "Entry"
                        elif(current_options[selected] == "Check another"):
                            if scene in ["Sheet1", "Sheet2", "Sheet3", "Sheet4", "Sheet5"] and scene not in checked:
                                checked.append(scene)
                            if scene in ["Sheet1 Connected", "Sheet1 Counted"] and "Sheet1" not in checked:
                                checked.append("Sheet1")
                            scene = "Sheets"
                        elif(current_options[selected] == "One"):
                            scene = "Sheet1"
                        elif(current_options[selected] == "Connect"):
                            scene = "Sheet1 Connected"
                        elif(current_options[selected] == "Count"):
                            scene = "Sheet1 Counted"
                        elif(current_options[selected] == "Two"):
                            scene = "Sheet2"
                        elif(current_options[selected] == "Three"):
                            scene = "Sheet3"
                        elif(current_options[selected] == "Four"):
                            scene = "Sheet4"
                        elif(current_options[selected] == "Five"):
                            scene = "Sheet5"
                        elif(current_options[selected] == "Key"):
                            scene = "Key"
                        elif(current_options[selected] == "Enter Code"):
                            scene = "Enter code"
                        elif(current_options[selected] == "Insert Key"):
                            scene = "Insert Key"
                        elif(current_options[selected] == "Move forward"):
                            # finish the game successfully
                            running = False
                            result = {'action': 'finished'}
                            break
                        else:
                            scene = "Failure"
                        print(checked)
                        if(sorted(checked) == ["Sheet1", "Sheet2", "Sheet3", "Sheet4", "Sheet5"] and ("Key" not in options["Sheets"])):
                            options["Sheets"].append("Key")
                            scene = "Key"
                        selected = 1  # reset selection to first option

        # draw/update
        if running:
            draw_selection(scene)

            # If start_ts was provided, compute and display elapsed in top-left as MM:SS
            if start_ts is not None:
                try:
                    elapsed = time.time() - float(start_ts)
                    mins = int(elapsed) // 60
                    secs = int(elapsed) % 60
                    timer_str = f"{mins:02d}:{secs:02d}"
                    small = SMALLFONT.render(f"Time: {timer_str}", True, YELLOW)
                    WIN.blit(small, (8, 8))
                except Exception:
                    pass

            # flip once per frame
            pygame.display.flip()

    # end main loop -> cleanup
    try:
        pygame.quit()
    except Exception:
        pass

    # Construct output dict; include elapsed_seconds if start_ts provided
    out = {'action': result.get('action', 'exit')}
    if start_ts is not None:
        try:
            out['elapsed_seconds'] = round(time.time() - float(start_ts), 3)
        except Exception:
            pass

    return out

if __name__ == "__main__":
    # when run as a standalone script print a minimal JSON result so the launcher can parse it
    player_name = None
    start_ts = None
    if len(sys.argv) > 1:
        player_name = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            start_ts = float(sys.argv[2])
        except Exception:
            start_ts = None

    res = run(player_name, start_ts)
    print(json.dumps(res))