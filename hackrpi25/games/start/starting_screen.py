# -*- coding: utf-8 -*-
"""
Created on Sat Nov 15 11:59:00 2025

@author: angel
"""
import pygame as p
import sys


def draw_menu(screen,w , h, game_font, color):
    Title_screen_text = game_font.render("Press Enter to Start", True,color)

    
    has_started = False
    while has_started == False:
        for event in p.event.get():
            if event.type == p.QUIT:
                p.quit()
                return #break doesn't work here
            
            if event.type == p.KEYDOWN and event.key == p.K_RETURN:
                has_started = True
                
                

        screen.fill((0,0,0))
        screen.blit(Title_screen_text,(w//2 -200, h //2))
        p.display.flip()    
    return has_started
        
    
   
def name_input_screen(screen, font, w, h, color):
    input_box = p.Rect(w//2 - 160, h//2 - 100, 300, 40)
    button = p.Rect(input_box.x + 60, input_box.x + 100, 180, 50)
    instructions = "Enter your name below"
    
    color_inactive = p.Color('lightskyblue3')
    color_active = p.Color('dodgerblue2')
    button_color = p.Color(color)

    active = False

    player_name = ""

    running = True
    while running:
        for event in p.event.get():
            if event.type == p.QUIT:
                running = False

            # Click to activate text box
            if event.type == p.MOUSEBUTTONDOWN:
                if input_box.collidepoint(event.pos):
                    active = True
                else:
                    active = False

                # if submit button is pressed, stop running loop to get text
                if button.collidepoint(event.pos):
                    running = False
                    
            

            # player_name / input
            if event.type == p.KEYDOWN and active:
                if event.key == p.K_BACKSPACE:
                    player_name = player_name[:-1]
                else:
                    player_name += event.unicode

        screen.fill((30, 30, 30))

        # Draw input box
        box_color = color_active if active else color_inactive
        p.draw.rect(screen, box_color, input_box, 2)

        # Draw text inside input box
        txt_surface = font.render(player_name, True,color)
        screen.blit(txt_surface, (input_box.x + 5, input_box.y + 5))

        # Draw button
        p.draw.rect(screen, button_color, button)
        btn_label = font.render("Submit", True, p.Color("black"))
        screen.blit(btn_label, (button.x + 25, button.y + 10))
        
        # draw instructions
        directions = font.render(instructions, True, color)
        screen.blit(directions, (input_box.x - 50, input_box.y - 100))
        
        
        p.display.flip()

    return player_name

import os

def run_start():
    p.init()
    p.font.init()
    
    p.display.set_caption("[GAME NAME]")
    base_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "."
    path = os.path.join(base_dir, "start_assets/Pixellari.ttf")

    game_font = p.font.Font(path, 40)
    WIDTH, HEIGHT = 800,600
    screen = p.display.set_mode((WIDTH,HEIGHT))
   
    player_name = ''

    started = draw_menu(screen,WIDTH,HEIGHT,game_font, (57,255,20))

    if started:     
        player_name = name_input_screen(screen,game_font,WIDTH, HEIGHT,(57,255,20))

    p.display.update()
    return(player_name)
   
import json
if __name__ == "__main__": 
    player_name = run_start()
    print(json.dumps({"player_name": player_name}))