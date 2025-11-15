import pygame
import sys
import json

pygame.init()

# ---------- Constants ----------
WIDTH, HEIGHT = 800, 600
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Old Style Terminal")

FONT = pygame.font.SysFont("Courier New", 32)
BIGFONT = pygame.font.SysFont("Courier New", 48)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
GREY = (180, 180, 180)

# ---------- Game Variables ----------
state = "menu"  # or "selection"
menu_message = "Press ENTER to start"
options = {
    "Entry": [
        "You enter the house. The lights are alreay on, though dim. You see three doors, all closed. Which direction do you go? ",
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
        "Six",
        "Back"
    ],
    "Lockbox" : [
        "You open the door and see a table with a strange box on it, with a code entry. Maybe you could open the box if you found a code? ",
        "Leave"
    ],
    "Sheet1" : [
        "The sheet has several points on it, all numbered. Connect them, or count the number of dots? ",
        "Connect",
        "Count"
    ],
    "Sheet1 Connected" : [
        "The lines connect to form the number 19.",
        "Check another"
    ],
    "Sheet1 Counted" : [
        "There are 19 dots on the page.",
        "Check another"
    ],
    "Sheet2" : [
        "The sheet has an equation containing x and y. Which do you solve for? ",
        "x",
        "y"
    ],
    "Sheet2 y" : [
        "You get the equation y = 9x.",
        "Check another"
    ],
    "Sheet2 x" : [
        "You get the equation x = y/9.",
        "Check another"
    ],
    "Sheet3" : [
        "The sheet has the roman numeral XIX.",
        "Check another"
    ],
    "Sheet4" : [
        "The sheet has a picture of a pie, then a minus sign and the number 2.14...?",
        "Check another"
    ],
    "Sheet5" : [
        "On the sheet are the numbers 72, 2, and 2. It looks as though something between them was erased, and it appears to be the same between both pairs.",
        "Check another"
    ],
    "Sheet6" : [
        "On the sheet is a sequence of numbers: __, 40, 80, 160.",
        "Check another"
    ],
    "Key" : [
        "You notice another sheet, containing a table of numbers and letters. It maps a to 1, b to 2, and so on. Perhaps by converting the numbers you found and rearranging them, you can form a word? ",
        "Back"
    ],
    "Enter code" : [
        "These are the combinations you came up with. Which do you try? ",
        "STAIRS",
        "SITRAS",
        "TIRSSA",
        "SISART",
        "ATSIRS",
        "ISTRAS"
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
        "You insert the key into the door lock, and it clicks open. Do you proceed and see what lies in wait? ",
        "Move forward"
    ]
}
# selected is the currently-highlighted option index within the active scene's option list
# index 0 is a descriptive line and must not be selectable, so default to 1
selected = 1
scene = "Entry"
checked = []

# ---------- Draw Functions ----------
def draw_menu():
    WIN.fill(BLACK)
    text = BIGFONT.render(menu_message, True, WHITE)
    WIN.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2 - text.get_height()//2))
    pygame.display.update()

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
    WIN.fill(BLACK)
    x = 50
    y = 50
    max_width = WIDTH - 2 * x
    line_height = FONT.get_linesize()

    current_options = options[scene]

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

    pygame.display.update()

# ---------- Main Loop ----------
def run(name):
    global state, selected, scene, checked
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

                if state == "menu":
                    if event.key == pygame.K_RETURN:
                        state = "selection"
                        # ensure we start on the first selectable option
                        selected = 1
                elif state == "selection":
                    current_options = options[scene]
                    n = len(current_options)
                    # if there are no selectable entries, ignore navigation
                    if n <= 1:
                        continue

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
                            if scene in ["Sheet1", "Sheet2", "Sheet3", "Sheet4", "Sheet5", "Sheet6"] and scene not in checked:
                                checked.append(scene)
                            if scene in ["Sheet1 Connected", "Sheet1 Counted", "Sheet2 x", "Sheet2 y"] and scene.split()[0] not in checked:
                                checked.append(scene.split()[0])
                            scene = "Sheets"
                        elif(current_options[selected] == "One"):
                            scene = "Sheet1"
                        elif(current_options[selected] == "Connect"):
                            scene = "Sheet1 Connected"
                        elif(current_options[selected] == "Count"):
                            scene = "Sheet1 Counted"
                        elif(current_options[selected] == "Two"):
                            scene = "Sheet2"
                        elif(current_options[selected] == "x"):
                            scene = "Sheet2 x"
                        elif(current_options[selected] == "y"):
                            scene = "Sheet2 y"
                        elif(current_options[selected] == "Three"):
                            scene = "Sheet3"
                        elif(current_options[selected] == "Four"):
                            scene = "Sheet4"
                        elif(current_options[selected] == "Five"):
                            scene = "Sheet5"
                        elif(current_options[selected] == "Six"):
                            scene = "Sheet6"
                        elif(current_options[selected] == "SISART"):
                            scene = "Open"
                            if("Insert Key" not in options["Exit"]):
                                options["Exit"].append("Insert Key")
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
                        if(sorted(checked) == ["Sheet1", "Sheet2", "Sheet3", "Sheet4", "Sheet5", "Sheet6"] and ("Key" not in options["Sheets"])):
                            options["Sheets"].append("Key")
                            options["Lockbox"].append("Enter Code")
                            scene = "Key"
                        selected = 1  # reset selection to first option

        # draw/update
        if running:
            if state == "menu":
                draw_menu()
            elif state == "selection":
                draw_selection(scene)

    # end main loop -> cleanup
    try:
        pygame.quit()
    except Exception:
        pass

    return result

if __name__ == "__main__":
    # when run as a standalone script print a minimal JSON result so the launcher can parse it
    res = run("")
    out = {'action': res.get('action', 'exit')}
    print(json.dumps(out))