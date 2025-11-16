import pygame
import pygame_textinput
import sys
import os
import time
import json

pygame.init()


def run(name, start_ts):
    WIDTH, HEIGHT = 800, 600
    WIN = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("SMS Chat")

    LIGHT_BLUE = (214, 219, 233)
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)

    FONT = pygame.font.Font(None, 32)

    month = 12
    travel = False
    presents = []
    take_input = False

    textinput = pygame_textinput.TextInputVisualizer()
    textinput.topleft = (100, 100)
    back = pygame.Rect(0, 0, 200, 100)
    back.topleft = (WIDTH - 300, HEIGHT - 300)

    present = pygame.Rect(20, 150, 204.8, 204.8)

    image_dict = {
        "pot": (200, 300),
        "sunrise": (300.8, 200.8),
        "snow": (307.2, 408),
        "necklace": (204.8, 204.8),
        "gift": (204.8, 204.8)
    }

    def get_image_path(image_id):
        image_id += ".jpg"
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        ASSET_DIR = os.path.join(BASE_DIR, "sms_assets")
        return os.path.join(ASSET_DIR, image_id)

    def move_time(travel_flag, cur_month):
        if cur_month != 5:
            cur_month += 1
        if cur_month == 13:
            cur_month = 1
        return cur_month

    def draw_chat(timestamp, text, image_id):
        WIN.fill(LIGHT_BLUE)

        # timestamp centered top
        time_surf = FONT.render(timestamp, True, BLACK)
        time_x = (WIDTH - time_surf.get_width()) // 2
        WIN.blit(time_surf, (time_x, 10))

        # running timer top-right if provided
        if start_ts is not None:
            try:
                elapsed = time.time() - float(start_ts)
                mins = int(elapsed) // 60
                secs = int(elapsed) % 60
                timer_str = f"{mins:02d}:{secs:02d}"
                timer_surf = FONT.render(timer_str, True, BLACK)
                WIN.blit(timer_surf, (WIDTH - 12 - timer_surf.get_width(), 10))
            except Exception:
                pass

        y_offset = 50
        title_surf = FONT.render("Aunt Ruby", True, BLACK)
        title_x = (WIDTH - title_surf.get_width()) // 2
        WIN.blit(title_surf, (title_x, y_offset))

        y_offset += 50

        # message bubble
        surf = FONT.render(text, True, BLACK)
        padding = 10
        bubble = pygame.Rect(0, 0, surf.get_width() + padding * 2, surf.get_height() + padding * 2)
        bubble.topleft = (20, y_offset)

        pygame.draw.rect(WIN, WHITE, bubble, border_radius=8)
        WIN.blit(surf, (bubble.x + padding, bubble.y + padding))

        if image_id:
            y_offset += 50
            image_path = get_image_path(image_id)
            try:
                image_name = pygame.image.load(image_path).convert()
                photograph = pygame.sprite.Sprite()
                photograph.image = pygame.transform.scale(image_name, (int(image_dict[image_id][0]), int(image_dict[image_id][1])))
                WIN.blit(photograph.image, (20, y_offset))
            except Exception:
                # If asset missing, just continue (keeps behavior minimal)
                pass

    def draw_choices(q, choices):
        y = HEIGHT - 140
        text = FONT.render(q, True, BLACK)
        WIN.blit(text, (20, y))
        y += 40
        for i in range(len(choices)):
            text = FONT.render("{}: {}".format(i + 1, choices[i]), True, BLACK)
            WIN.blit(text, (20, y))
            y += 40

    # Main loop
    clock = pygame.time.Clock()
    while True:

        if month == 12:
            draw_chat("Dec 12, 2009 13:45 PM", "It's really looking like a winter wonderland!", None)
            choices = ("Flower pot", "Coffee")
            draw_choices("What do you want to get your aunt for Christmas?", choices)

        elif month == 1:
            draw_chat("Jan 1, 2010 12:00 PM", "Happy New Year!", "snow")

        elif month == 2:
            draw_chat("Feb 2, 2010 1:00 PM", "Happy February!", None)

        elif month == 3:
            text = "Happy March!"
            image = None
            # guard if 'choices' isn't set for some reason
            try:
                if choices[1] in presents:
                    text = "Edgar loves watching the birds!"
                    image = "sunrise"
            except Exception:
                pass
            draw_chat("Mar 3, 2010 2:00 PM", text, image)

        elif month == 4:
            text = ("Happy April!")
            image = None
            try:
                if choices[0] in presents:
                    text = "Edgar and the flowers!"
                    image = "pot"
            except Exception:
                pass
            draw_chat("Apr 4, 2010 3:00 PM", text, image)

        elif month == 5 and travel == False:
            draw_chat("May 5, 2010 4:00 PM", "Happy birthday! I sent you something in the mail.", "gift")

        elif month == 5 and travel:
            draw_chat("May 5, 2010 4:00 PM", "Safe time travels!", "necklace")

        elif month == 13:
            out = {'action': 'finished'}
            if start_ts is not None:
                try:
                    out['elapsed_seconds'] = round(time.time() - float(start_ts), 3)
                except Exception:
                    pass
            # cleanly quit pygame before returning
            pygame.display.flip()
            pygame.quit()
            return out

        events = pygame.event.get()

        for event in events:

            # Checks if the user exits the game window
            if event.type == pygame.QUIT:
                out = {'action': 'exit'}
                if start_ts is not None:
                    try:
                        out['elapsed_seconds'] = round(time.time() - float(start_ts), 3)
                    except Exception:
                        pass
                pygame.quit()
                return out

            # Checks if user presses a key
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # ESC is a level-skipper: stop loop and return a 'skipped' result
                    out = {'action': 'skipped'}
                    if start_ts is not None:
                        try:
                            out['elapsed_seconds'] = round(time.time() - float(start_ts), 3)
                        except Exception:
                            pass
                    pygame.quit()
                    return out

                if event.key == pygame.K_RETURN and travel:
                    s = str(textinput.value).strip()
                    if len(s) == 8 and str(s).isdigit():
                        month = int(s[:2])
                        day = int(s[2:4])
                        year = int(s[4:])
                        # special code checks
                        if month == 10 and day == 23 and year == 1345:
                            month = 13
                        elif day == month and year == 2010:
                            pass
                        else:
                            month = 12
                    else:
                        month = 12
                # Special days that need specific inputs
                if month == 12:
                    if event.key == pygame.K_1 or event.key == pygame.K_2:
                        if event.key == pygame.K_1:
                            presents.append(choices[0])
                        else:
                            presents.append(choices[1])
                        month = move_time(travel, month)

                # Generic space to move
                else:
                    if event.key == pygame.K_SPACE:
                        month = move_time(travel, month)

            # Checks if user clicks
            if event.type == pygame.MOUSEBUTTONDOWN:
                if back.collidepoint(event.pos) and travel:
                    take_input = True
                else:
                    take_input = False
                if present.collidepoint(event.pos) and travel == False:
                    travel = True

        if take_input:
            textinput.update(events)

        if travel:

            pygame.draw.rect(WIN, WHITE, back, border_radius=8)

            title1_surf = FONT.render("Enter an 8-digit number", True, BLACK)
            title2_surf = FONT.render("(MMDDYYYY)", True, BLACK)
            WIN.blit(title1_surf, (10 + back.x, back.y - 100))
            WIN.blit(title2_surf, (10 + back.x, back.y - 50))
            WIN.blit(textinput.surface, (10 + back.x, 10 + back.y))

        pygame.display.update()
        clock = pygame.time.Clock()
        clock.tick(60)


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