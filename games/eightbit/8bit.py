# -*- coding: utf-8 -*-
"""
Created on Sat Nov 15 15:57:17 2025

@author: angel
"""
import pygame as p
import sys
import json
import time
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(BASE_DIR, "assets")


def move(screen, player,player_rect,w, m):
    #updates player movement        
    key = p.key.get_pressed()
    if key[p.K_UP] == True and player_rect.top >= 0:
        player_rect.y -= m
    if key[p.K_DOWN] == True and player_rect.bottom <= 460:
        player_rect.y += m
    
    if key[p.K_LEFT] == True and player_rect.left >= 0:
        player_rect.x -= m
    if key[p.K_RIGHT] == True and player_rect.right <= w:
        player_rect.x += m
    screen.blit(player, (player_rect.x,player_rect.y))

    
def read_instructions(screen,g_font, s_font, name,w,h, scroll):
    
    dark_brown = (101, 67, 33)
    light_brown = (181, 101, 29)
    play_bttn = p.Rect(w//2-100,400,150,50)

    opened = False
    run = True
    while run:
        for event in p.event.get():
            if event.type == p.QUIT:
                run = False
                return
            
            # if play_butt button is pressed, open level and cllse this window
            if event.type == p.MOUSEBUTTONDOWN:
                if play_bttn.collidepoint(event.pos):
                    run = False
                    return
   
        if opened == False:
            #making scroll
            open_scroll = p.Rect(50,50,700,500)
            p.draw.rect(screen, light_brown, open_scroll)
            screen.blit(scroll, (0,0))

            
            header = g_font.render(f"HELLO {name}", True , dark_brown)
            screen.blit(header,(open_scroll.centerx-150, h //2-100))#add boarder
            
            #text directions
            body1 = s_font.render("Welcome to the 8-bit Scavenger Hunt!",True,dark_brown)
            body2 = s_font.render("Your job is to go find each clue!",True,dark_brown)
            body3 = s_font.render("How do you do that, well...",True,dark_brown)
            body4 = s_font.render("Idk man, just float around and see what happens I guess.",True,dark_brown)

            body5 = s_font.render("Don't for get to find the key to get to the next level, Good Luck!",True,dark_brown)
            
            screen.blit(body1, (120, 280))
            screen.blit(body2, (120, 300))
            screen.blit(body3, (120, 320))
            screen.blit(body4, (120, 340))
            screen.blit(body5, (120, 360))

            #how to move / controls
            ctrls = s_font.render("Use you up , down, left and right keys to move!",True,dark_brown)
            screen.blit(ctrls, (w//2-200, 500))
            
            #exit button
            bttn_text = g_font.render("Play",True,dark_brown)
            p.draw.rect(screen, (255,0,0), play_bttn)
            screen.blit(bttn_text, (play_bttn.x + 30,play_bttn.y + 10))
            
            p.display.flip()
            opened = True


def get_clue(text_list,screen, s_rect,sprite, w,h,player_rect, loc):
    font = p.font.Font(os.path.join(ASSET_DIR, "Pixellari.ttf"), 20)

    clue_f = False
    sprite.set_alpha(0)

    if player_rect.collidepoint(s_rect.centerx,s_rect.centery):
        clue_f = True
        sprite.set_alpha(255)
        bkg = p.Rect(100,100,650,400)
        
        p.draw.rect(screen, (0,0,0), bkg)
        screen.blit(sprite, loc)
        rendered = [font.render(x,True,(255,255,255)) for x in text_list]
        i = 1
        
        for words in rendered:
        
            screen.blit(words, (bkg.x * i + 10, (bkg.y  * i) + 30))
            i+=1
            
            
        return  clue_f
            


def run_8bit(player_name,start_ts):
    p.init()
    p.font.init()
    
    p.display.set_caption("8-bit Scavenger Hunt")
    WIDTH, HEIGHT = 800,600
    screen = p.display.set_mode((WIDTH,HEIGHT))
    game_font = p.font.Font(os.path.join(ASSET_DIR, "Pixellari.ttf"), 40)
    small_font = p.font.Font(os.path.join(ASSET_DIR, "Pixellari.ttf"), 20)

    #MAIN GAME ASSETS 
    bkg = p.transform.scale(p.image.load(os.path.join(ASSET_DIR, '8bit_bkg_wider.png')), (800, 600))
    player = p.transform.scale(p.image.load(os.path.join(ASSET_DIR, 'bartholomew.png')).convert_alpha(), (100, 100))
    scroll = p.transform.scale( p.image.load(os.path.join(ASSET_DIR, 'scroll.png')), (400, 300))
    player_rect = player.get_rect()

    #PLAYER INITIAL POSITION
    player_rect.x = 100
    player_rect.y = 350
    move_by = 2
    
      
    #clue 1 asset  
    oracle = p.transform.scale(p.image.load(os.path.join(ASSET_DIR, 'the_oracle (2).png')).convert_alpha(), (160, 180))
    o_rect = oracle.get_rect()
    #clue 1 position
    o_rect.x = 0
    o_rect.y = 80
    
    
    #clue 2 asset
    backpack = p.transform.scale(p.image.load(os.path.join(ASSET_DIR, 'Backpack.png')).convert_alpha(), (160, 240))
    bp_rect = backpack.get_rect()
    #clue 2 position
    bp_rect.x = 610
    bp_rect.y = 50
    
    #clue 3 asset
    key = p.transform.scale(p.image.load(os.path.join(ASSET_DIR, 'key.png')).convert_alpha(), (200, 250))
    key_rect = key.get_rect()
    
    #key found? and position
    key_found = False
    key_rect.x = 325
    key_rect.y = 330
    
    #next_level button
    nxt_lvl = p.Rect(WIDTH//2 -50 , HEIGHT//2 +100, 100 , 50)
    
    
    read = True
    if read:
        read_instructions(screen,game_font, small_font, player_name,WIDTH,HEIGHT,scroll) 
        read = False
    
    run = True
    c1_counter = 0
    c2_counter = 0

    result = {'action': 'exit'}

    while run:
        for event in p.event.get():
            if event.type == p.QUIT:
                run = False

            if event.type == p.MOUSEBUTTONDOWN and nxt_lvl.collidepoint(event.pos) and key_found == True:
                run  = False
                result = {'action': 'finished'}

                
        screen.blit(bkg, (0, 0))


        move(screen, player,player_rect,WIDTH,move_by)

        #checks if  players found clues
        c1_text = ["I AM THE ORACLE WHO KNOWS ALL BOWWW IN MY PRESENCE!!", "OH THE NEXT CLUE??? I'LL NEVER TELL YOU HAHAHA"\
        ,"*ACHOOOOO* (check the clouds)", "Ugh, did you hear that?"]
        c1 = get_clue(c1_text,screen, o_rect,oracle,WIDTH,HEIGHT,player_rect, (0,0))
        if c1:
            c1_counter += 1
            
        if c1_counter > 0:
            c2_text = ["Hmm, Looks like you left you bag here while sleeing in the clouds",\
                       "It's kind of heavy...", "its almost as if it wants you to float down"," to touch the grass...."]
            c2 = get_clue(c2_text,screen, bp_rect,backpack,WIDTH,HEIGHT,player_rect, (0,25))
            if c2:
                c2_counter += 1
        if c2_counter > 0:
            c3_text = ["WOW YOU FOUND THE KEY!!!", ""]
            c3 = get_clue(c3_text, screen, key_rect,key,WIDTH,HEIGHT,player_rect, (WIDTH//2-100,HEIGHT //2-100))
            if c3:
                key_found = True
                #exit lvl
                text = small_font.render("NEXT",True,(255,255,255))
                p.draw.rect(screen, (255,0,0), nxt_lvl)
                screen.blit(text, (nxt_lvl.x + 30,nxt_lvl.y + 10))
                
         # If start_ts was provided, compute and display elapsed in top-left as MM:SS
        if start_ts is not None:
            try:
                elapsed = time.time() - float(start_ts)
                mins = int(elapsed) // 60
                secs = int(elapsed) % 60
                timer_str = f"{mins:02d}:{secs:02d}"
                small = small_font.render(f"Time: {timer_str}", True, (157,255,120))
                screen.blit(small, (8, 8))
            except Exception:
                pass
        
            
        p.display.update()     

    
    p.quit()
    # include elapsed_seconds if start_ts present
    try:
        if start_ts is not None:
            result['elapsed_seconds'] = round(time.time() - float(start_ts), 3)
    except Exception:
        pass

    return result

    
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

    res = run_8bit(player_name, start_ts)
    print(json.dumps(res))  