#!/usr/bin/python

'''
libtcod python tutorial
this code modifies samples_py.py from libtcod 1.4.1 It shows a '@'
walking around with a source of light giving simple FOV.
It's in the public domain.
'''
###
#import
###

import os
import time
import libtcodpy as libtcod

###
#utility function
###

def get_key(key): #handle keyboard input, uses strings to get keyboard input
	if key.vk == libtcod.KEY_CHAR:
		
		return chr(key.c)
	else:
		return key.vk

###
#global constants and variables

window_width = 46
window_height = 20

first = True
fov_px = 20
fov_py = 10

fov_recompute = True
fov_map = None

fov_colors = 	{ #python dictionary to hold colors
				'dark wall' : libtcod.Color(0, 0, 100),
				'light wall' : libtcod.Color(130, 110, 50),
				'dark ground' : libtcod.Color(50, 50, 150),
				'light ground' : libtcod.Color(200, 180, 50)
				}
fov_init = False
fov_radius = 4

move_controls = { #central place for keyboard inputs
				libtcod.KEY_UP : (0, -1), #up
				libtcod.KEY_DOWN : (0, 1), #down
				libtcod.KEY_RIGHT : (1, 0), #right
				libtcod.KEY_LEFT : (-1, 0) #left
				}
			
smap = ['##############################################',
		'#   ####   ##       =   #      #     #########',
		'#   ###     # #   # #   # #  # #     ####   ##',
		'#           #           #      #     ####   ##',
		'#######     # #   # #   ### ###### ####### ###',
		'#######     #       =   #               =  ###',
		'#######     # #   # #   # # ##########  ## ###',
		'########   ##       #   # # #   #   ## ### ###',
		'######### ###########   #     #   # ####   ###',
		'####    # ###   #   #   ##### ##### ###     ##',
		'####      ###   =   #   #      #    ####   ###',
		'####    # ###   #   #   =      # # ## ### ####',
		'######### #### ### ##   #      # #           ##',
		'#####        # ### ##   ### #  # #############',
		'#   #                          #       #######',
		'##                             ######  #######',
		'#   #        # ##### ###### #  ##          ###',
		'## ########### ####   ###      ##    ##    ###',
		'##     =        ###   ###      ##          ###',
		'##############################################',
		]
'''		
smap = ['##############################################',
        '#######################      #################',
        '#####################    #     ###############',
        '######################  ###        ###########',
        '##################      #####             ####',
        '################       ########    ###### ####',
        '###############      #################### ####',
        '################    ######                  ##',
        '########   #######  ######   #     #     #  ##',
        '########   ######      ###                  ##',
        '########                                    ##',
        '####       ######      ###   #     #     #  ##',
        '#### ###   ########## ####                  ##',
        '#### ###   ##########   ###########=##########',
        '#### ##################   #####          #####',
        '#### ###             #### #####          #####',
        '####           #     ####                #####',
        '########       #     #### #####          #####',
        '########       #####      ####################',
        '##############################################',
        ]			
'''		
###
#drawing
###

def draw(first):
	global fov_px, fov_py, fov_map
	global fov_init, fov_recompute, smap
	
	if first: #initialize the window and 
		libtcod.console_clear(0)
		libtcod.console_set_default_foreground(0, libtcod.white)
		text = 'what?'
		libtcod.console_print_ex(0, 1, 1, libtcod.BKGND_NONE, libtcod.LEFT, text)
		libtcod.console_put_char(0, fov_px, fov_py, '@',
									libtcod.BKGND_NONE)
			
		for y in range(window_height):
			for x in range(window_width):
				if smap[y][x] == '=':
					libtcod.console_put_char(0, x, y,
						libtcod.CHAR_DHLINE,
						libtcod.BKGND_NONE)
	if not fov_init:
		fov_init = True
		fov_map = libtcod.map_new(window_width, window_height)
		for y in range(window_height):
			for x in range(window_width):
				if smap[y][x] == ' ':
					libtcod.map_set_properties(fov_map, x, y, True, True)
				elif smap[y][x] == '=':
					libtcod.map_set_properties(fov_map, x, y, True, False)
				
	if fov_recompute:
		fov_recompute = False
		libtcod.map_compute_fov(fov_map, fov_px, fov_py, fov_radius, True)
	
	for y in range(window_height): # color in the map
		for x in range(window_width):
			affect, cell = 'dark', 'ground'
			if libtcod.map_is_in_fov(fov_map, x, y): affect = 'light'
			if (smap[y][x] == '#'): cell = 'wall'
			color = fov_colors['%s %s' % (affect, cell)]
			libtcod.console_set_char_background(0, x, y, color, libtcod.BKGND_SET)
			
###
#game state update
###

def update(key):
	global fov_py, fov_px, fov_recompute, smap
	
	key = get_key(key)
	if key in move_controls:
		dx, dy = move_controls[key]
		if smap[fov_py+dy][fov_px+dx] == ' ':

			fov_px = fov_px + dx
			fov_py = fov_py + dy
			libtcod.console_put_char(0, fov_px, fov_py, '@',
									libtcod.BKGND_NONE)
			fov_recompute = True
			
###
#initialization and main loop
###

#fonts = os.path.join('fonts', arial12x12.png')
#libtcod.console_set_custom_font(font, libtcod.FONT_LAYOUT_TCOD | libtcod.FONT_TYPE_GREYSCALE)
libtcod.console_set_custom_font('arial12x12.png', libtcod.FONT_LAYOUT_TCOD | libtcod.FONT_TYPE_GREYSCALE)

libtcod.console_init_root(window_width, window_height, 'Python Tutorial', False)

while not libtcod.console_is_window_closed():
	draw(first)
	libtcod.console_flush()
	time.sleep(.1) #artificially reduce fps
	key  = libtcod.console_wait_for_keypress(True)
	update(key)
	if key.vk == libtcod.KEY_ESCAPE:
		break
		
	