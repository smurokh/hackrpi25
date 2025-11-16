# -*- coding: utf-8 -*-
"""
Created on Sat Nov 15 11:59:00 2025

@author: angel
"""
import pygame as p
import sys


def draw_menu(screen, w, h, game_font, color):
    Title_screen_text = game_font.render("Press Enter to Start", True, color)

    has_started = False
    while has_started == False:
        for event in p.event.get():
            if event.type == p.QUIT:
                p.quit()
                return  # break doesn't work here

            if event.type == p.KEYDOWN and event.key == p.K_RETURN:
                has_started = True

        screen.fill((0, 0, 0))
        # center text horizontally
        text_rect = Title_screen_text.get_rect(center=(w // 2, h // 2))
        screen.blit(Title_screen_text, text_rect)
        p.display.flip()
    return has_started


def name_input_screen(screen, font, w, h, color):
    input_box = p.Rect(w // 2 - 160, h // 2 - 100, 300, 40)
    # Button placed below the input_box (fixed y coordinate)
    button = p.Rect(input_box.x + 60, input_box.y + 60, 180, 50)
    instructions = "Enter your name below"

    color_inactive = p.Color('lightskyblue3')
    color_active = p.Color('dodgerblue2')
    try:
        button_color = p.Color(color)
    except Exception:
        button_color = p.Color('dodgerblue2')

    # Start with input active so the user can type immediately without clicking
    active = True

    player_name = ""

    running = True
    while running:
        for event in p.event.get():
            if event.type == p.QUIT:
                running = False

            # Click handling: don't deactivate input when clicking outside.
            if event.type == p.MOUSEBUTTONDOWN:
                # keep typing active even if clicking outside; only handle submit button here
                if button.collidepoint(event.pos):
                    running = False

            # Submit with Enter key (anywhere) or handle typing/backspace
            if event.type == p.KEYDOWN:
                if event.key == p.K_RETURN:
                    running = False
                elif active:
                    if event.key == p.K_BACKSPACE:
                        player_name = player_name[:-1]
                    else:
                        # Only append printable characters
                        if event.unicode and ord(event.unicode) >= 32:
                            player_name += event.unicode

        screen.fill((30, 30, 30))

        # Draw input box
        box_color = color_active if active else color_inactive
        p.draw.rect(screen, box_color, input_box, 2)

        # Draw text inside input box (show placeholder when empty)
        display_text = player_name if player_name else ""
        txt_surface = font.render(display_text, True, color)
        screen.blit(txt_surface, (input_box.x + 5, input_box.y + 5))

        # Draw button
        p.draw.rect(screen, button_color, button)
        btn_label = font.render("Submit", True, p.Color("black"))
        # center label inside button
        btn_label_rect = btn_label.get_rect(center=button.center)
        screen.blit(btn_label, btn_label_rect)

        # draw instructions
        directions = font.render(instructions, True, color)
        dir_rect = directions.get_rect(midbottom=(input_box.centerx, input_box.y - 12))
        screen.blit(directions, dir_rect)

        p.display.flip()

    # normalize return: None if empty, else trimmed string
    return player_name.strip() if player_name.strip() else None


import os


def run_start():
    p.init()
    p.font.init()

    p.display.set_caption("[GAME NAME]")
    base_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "."
    path = os.path.join(base_dir, "start_assets/Pixellari.ttf")

    try:
        game_font = p.font.Font(path, 40)
    except Exception:
        game_font = p.font.SysFont(None, 40)

    WIDTH, HEIGHT = 800, 600
    screen = p.display.set_mode((WIDTH, HEIGHT))

    player_name = None

    started = draw_menu(screen, WIDTH, HEIGHT, game_font, (57, 255, 20))

    if started:
        player_name = name_input_screen(screen, game_font, WIDTH, HEIGHT, (57, 255, 20))

    p.display.update()
    return player_name


import json

if __name__ == "__main__":
    player_name = run_start()
    print(json.dumps({"player_name": player_name}))