# Rob's First Attempt at Python!
# From http://www.roguebasin.com/index.php?title=Complete_Roguelike_Tutorial,_using_python%2Blibtcod,_part_1

# known bugs:
# cancelling uses the item still without effect
# casting spell does not use turn

import libtcodpy as libtcod
import math
import textwrap
import shelve
import time

#actual size of the window
SCREEN_WIDTH = 140 
SCREEN_HEIGHT = 80

#GUI panel size
BAR_WIDTH = 20
PANEL_HEIGHT = 7
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT
MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1
LEVEL_SCREEN_WIDTH = 40
CHARACTER_SCREEN_WIDTH = 30
MAP_WIDTH = 140
MAP_HEIGHT = 80

INVENTORY_WIDTH = 50

LIMIT_FPS = 20 #max frames per second

#size fo map that is visible on screen
CAMERA_WIDTH = SCREEN_WIDTH
CAMERA_HEIGHT = SCREEN_HEIGHT - PANEL_HEIGHT


#room generation
ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 3
MAX_ROOMS = 100


FOV_ALGO = 0 #defalut FOV algorithm
FOV_LIGHT_WALLS = True


#spells
HEAL_AMOUNT = 40
LIGHTNING_RANGE = 4
LIGHTNING_DAMAGE = 40
CONFUSE_NUM_TURNS = 10
CONFUSE_RANGE = 8
FIREBALL_DAMAGE = 25
FIREBALL_RADIUS = 3
TORCH_RADIUS = 3 #fix for save game crash. This variable doesn't get stored on save.

#experience and level-up
LEVEL_UP_BASE = 200
LEVEL_UP_FACTOR =150

color_dark_wall = libtcod.Color(0, 0, 100)
color_dark_ground = libtcod.Color(50, 50, 150)
color_light_wall = libtcod.Color(130, 110, 50)
color_light_ground = libtcod.Color(200, 180, 50)

DEBUG =  False #if you want to not have the FOV block the items and monsters, abillity to heal with "+"

class Tile:
	#a tile of the map and its properties
	def __init__(self, blocked, block_sight = None):
		self.blocked = blocked
		
		if DEBUG == True:
			self.explored = True
		else:
			#all tiles start unexplored
			self.explored = False
		
		#by default, if a tile is blocked, it also blocks sight
		if block_sight is None: block_sight = blocked
		self.block_sight = block_sight
		

class Rect:
	#a rectangle on the map. used to characterize a room.
	def __init__(self, x, y, w, h):
		self.x1 = x
		self.y1 = y
		self.x2 = x + w
		self.y2 = y + h
		
	#detect if overlaping
	def center(self):
		center_x = (self.x1 + self.x2) / 2
		center_y = (self.y1 + self.y2) / 2
		return (center_x, center_y)
		
	def intersection (self, other):
		#returns if this rectangle intersects with another one
		return (self.x1 <= other.x2 and self.x2 >= other.x1 and
				self.y1 <= other.y2 and self.y2 >= other.y1)

class Object:
	# this is a generic object: the player, a monster, an item, the stairs...
	# it's always represented by a character on screen.
	
	def __init__(self, x, y, char, name, color, blocks=False, always_visible=False, fighter=None, ai=None, item=None, equipment=None, block_sight=False):
		self.x = x
		self.y = y
		self.char = char
		self.name = name
		self.color = color
		self.blocks = blocks
		self.always_visible = always_visible
		
		self.block_sight = block_sight
		if self.block_sight: #let the sight component know who owns it
			self.block_sight.owner = self
		
		self.fighter = fighter
		if self.fighter: #let the fighter component know who owns it
			self.fighter.owner = self
			
		self.ai = ai
		if self.ai: #let the AI component know who owns it
			self.ai.owner = self
			
		self.item = item
		if self.item: #let the Item component know who owns it
			self.item.owner = self
			
		self.equipment = equipment
		if self.equipment:	#let the equipment component know who owns it
			self.equipment.owner = self
			#there must be an Item component for the Equipment component to work propperly
			self.item = Item()
			self.item.owner = self
		
	def move(self, dx, dy):
		# move b the given amount
		if not is_blocked(self.x + dx, self.y + dy, map):
			self.x += dx
			self.y += dy
		
	def move_towards(self, target_x, target_y):
		dx = target_x - self.x
		dy = target_y - self.y
		
		if dx > 0:
			dx = 1
		if dx < 0:
			dx = -1
		if dy > 0:
			dy = 1
		if dy < 0:
			dy = -1
		self.moveai(dx, dy)
	
	def move_away(self, target_x, target_y):
		dx = target_x - self.x
		dy = target_y - self.y
		if dx > 0:
			dx = -1
		if dx < 0:
			dx = 1
		if dy > 0:
			dy = -1
		if dy < 0:
			dy = 1
		self.moveai(dx, dy)
	
	def moveai(self, dx, dy): # causes monsters to line up in a row if there are a lot.
		if not is_blocked(self.x, self.y + dy, map):
			self.y += dy
		
		if not is_blocked(self.x + dx, self.y, map):
			self.x += dx		
		
	def distance_to(self, other):
		#return the distance to another object
		dx = other.x - self.x
		dy = other.y - self.y
		return math.sqrt(dx ** 2 + dy ** 2)	
		
	def distance(self, x, y):
		#return distance to some coordinates
		return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)	
		
	def send_to_back(self):
		#make this object is drawn first, so all others appear above it if they're in the same title.
		global objects
		objects.remove(self)
		objects.insert(0,self)
	
	def draw(self):
		# show only if's visible to the player
		if (libtcod.map_is_in_fov(fov_map, self.x, self.y) or
			(self.always_visible and map[self.x][self.y].explored)):
			(x, y) = to_camera_coordinates(self.x, self.y)
			
			if x is not None:
				# set the color and then draw the character that represents this object at its position
				libtcod.console_set_default_foreground(con, self.color)
				libtcod.console_put_char(con, x, y, self.char, libtcod.BKGND_NONE)
	  
	def clear(self):
		# erase the character that represents this object
		(x, y) = to_camera_coordinates(self.x, self.y)
		if x is not None:
			libtcod.console_put_char(con, x, y, ' ', libtcod.BKGND_NONE)
		
class Fighter:
	#comat-related properties and methods (monster, player, NPC).
	def __init__(self, hp, defense, power, xp, death_function = None):
		self.base_max_hp = hp
		self.hp = hp
		self.base_defense = defense
		self.base_power = power
		self.xp = xp
		self.death_function = death_function
	
	@property
	def power(self):
		bonus =  sum(equipment.power_bonus for equipment in get_all_equipped(self.owner))
		return self.base_power + bonus
		
	@property
	def defense(self): #return actual defense, by summing up the bonuses from all equipped items
		bonus = sum(equipment.defense_bonus for equipment in get_all_equipped(self.owner))
		return self.base_defense + bonus
		
	@property
	def max_hp(self): #return actual max_hp, by summing up the bonuses from all equipped items
		bonus = sum(equipment.max_hp_bonus for equipment in get_all_equipped(self.owner))
		return self.base_max_hp + bonus
	
	def attack(self, target):
		#a simple formula for attack damage
		damage = self.power - target.fighter.defense
		
		if damage > 0:
			#make the target take some damage
			message(self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' hit points.', libtcod.white)
			target.fighter.take_damage(damage)
			
		else:
			message(self.owner.name.capitalize() + " attacks " + target.name + ' but it has no effect!', libtcod.white)

	def take_damage(self, damage):
		#apply damage if possible
		if damage > 0:
			self.hp -= damage
			
			#check for death. if there's a death function, call it
			if self.hp <= 0:
				function = self.death_function
				if function is not None:
					function(self.owner)
				if self.owner != player: #yeild experience to the player
					player.fighter.xp += self.xp
					
	def heal(self,amount):
		#heal by the given amount, without going over the maximum
		self.hp += amount
		if self.hp > self.max_hp:
			self.hp = self.max_hp					

		
class BasicMonster:
	#AI for a basic monster.
	def take_turn(self):
		#a basic monster takes its turn. If you can see it, it can see you
		monster = self.owner
		
		#message for hearing monster just outside of your torch radius (will listen thorugh walls)
		if monster.distance_to(player) >= TORCH_RADIUS and monster.distance_to(player) <= 12:
			message('You hear a ' + self.owner.name + ' move around!', libtcod.red)
			
		#if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
		if	monster.distance_to(player)<= 5:
			
			#move towards player if far away
			if monster.distance_to(player)>= 2:
				monster.move_towards(player.x, player.y)
				
			#close enough, attack! (if the player is still alive.)
			elif player.fighter.hp > 0:
				monster.fighter.attack(player)
				
		else: # wander aimlessly
			self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))

class Trap:
	#AI for a basic monster.
	def take_turn(self):
		#a basic monster takes its turn. If you can see it, it can see you
		monster = self.owner
					
		#if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
		if	monster.distance_to(player)<= 2: # basic range should be part of a ranged attack for monster 
			if player.fighter.hp > 0:
				monster.fighter.attack(player)
				
				
class RangedMonster:
	#AI for a basic monster.
	def take_turn(self):
		#a basic monster takes its turn. If you can see it, it can see you
		monster = self.owner
		
		#message for hearing monster just outside of your torch radius (will listen thorugh walls)
		if monster.distance_to(player) >= TORCH_RADIUS and monster.distance_to(player) <= 12:
			message('You hear a ' + self.owner.name + ' move around!', libtcod.red)
			
		#if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
		if	monster.distance_to(player)<= 5:
			
			#move towards player if far away
			if monster.distance_to(player)>= 3: #Range is 2
				monster.move_towards(player.x, player.y)
				
			#close enough, shoot at the player (if the player is still alive.)
			elif player.fighter.hp > 0:
				monster.fighter.attack(player)
				
		else: # wander aimlessly
			self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
		

class ConfusedMonster:
	#AI for a temporarily confused monster (reverts to previous AI after a while.)
	def __init__(self, old_ai, num_turns=CONFUSE_NUM_TURNS):
		self.old_ai = old_ai
		self.num_turns = num_turns
		
	def take_turn(self):
		if self.num_turns >0: #still confused
			#move in a random direction
			self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
			self.num_turns -= 1
		else: #restore the previous AI (this one will be deleted because it's not referenced anymore)
			self.owner.ai = self.old_ai
			message('The ' + self.owner.name + ' is no longer confused!', libtcod.red)

# example of switching states of AI rather than using classes for permanent things
class DragonAI:# incomplete!!!!!!!!!!!!!!!!!!
	def __init__(self):
		self.state = 'chasing'
		
	def take_turn(self):
		if self.state == 'chasing':
			if monster.distance_to(player)>= 3: #Range is 2
				monster.move_towards(player.x, player.y)
			
		elif self.state == 'charging-fire-breath': # something...
			message('The ' + self.owner.name + ' is charging!', libtcod.red)

class Item:
	#an item that can be picked up and used.
	def __init__(self, use_function=None):
		self.use_function = use_function
		
	#an item that can be picked up and used
	def pick_up(self):
		#add to the player's inventory and remove from the map
		if len(inventory) >= 9:
			message('Your inventory is full, cannot pick up ' + self.owner.name + '.', libtcod.red)
		else:
			inventory.append(self.owner)
			objects.remove(self.owner)
			message('You picked up a ' + self.owner.name + '!', libtcod.green)
			
		#special case: automatically equip, if the corresponding equipment slot is unused
		equipment = self.owner.equipment
		if equipment and get_equipped_in_slot(equipment.slot) is None:
			equipment.equip()
			
	def use(self):
		# just call the "use_function" if it is defined
		if self.use_function is None:
			message('The ' + self.owner.name + ' cannot be used.')
		else:
			if self.use_function() != 'cancelled':
				inventory.remove(self.owner) # destroy after use, unless it was cancelled for some reason
				fov_recompute = True
			else:
				message('The ' + self.owner.name + ' placed back in inventory.')
				
		#special case: if the object has the Equipment component, the "use" action is to equip/dequip
		if self.owner.equipment:
			self.owner.equipment.toggle_equip()
			return
			
	
	def drop(self):
		#add to the map and remove from the player's inventory. also, place it at the player's coordinates
		objects.append(self.owner)
		inventory.remove(self.owner)
		self.owner.x = player.x
		self.owner.y = player.y
		message('You dropped a ' + self.owner.name + '.', libtcod.yellow)
		
		#special case: if the object has the Equipment component, dequip it before dropping
		if self.owner.equipment:
			self.owner.equipment.dequip()
			
	def throw(self):
		# throw an object
		message('Left-click a target tile throw, or right-click to cancel.', libtcod.light_cyan)
		(x, y) = target_tile()
		if x is None: return 'cancelled' # cancel if tile no tile targeted in the x position
		
		if is_occupied(x, y, map):
			message('You cannot throw a ' + self.owner.name + ' there.', libtcod.orange)
			return 'cancelled'
		else:
			message('You throw a ' + self.owner.name + '!', libtcod.orange)
			objects.append(self.owner) # place item in objects list
			inventory.remove(self.owner) # take item out of player inventory
			#assign item to location
			self.owner.x = x
			self.owner.y = y
			for obj in objects: #damage every fighter in range, including the player
				if obj.distance(x, y) <= 0 and obj.fighter:
					message('The ' + obj.name + ' gets hit by a ' + self.owner.name + ' for ' + str(2) + ' points!', libtcod.orange)
					obj.fighter.take_damage(2)

class Equipment:
	#an object that can be equipped, yeilding bonuses. automatically adds the item component.
	def __init__(self, slot, power_bonus=0, defense_bonus=0, max_hp_bonus=0):
		self.power_bonus = power_bonus
		self.defense_bonus = defense_bonus
		self.max_hp_bonus = max_hp_bonus
		
		self.slot = slot
		self.is_equipped = False
		
	def toggle_equip(self): #toggle equip/dequip status
		if self.is_equipped:
			self.dequip()
		else:
			self.equip()
			
	def equip(self):
		#if the slot is already being used, dequip whatever is there first
		old_equipment = get_equipped_in_slot(self.slot)
		if old_equipment is not None:
			old_equipment.dequip()
			
		#equip object and show a message about it
		self.is_equipped = True
		message('Equpped ' + self.owner.name + ' on ' + self.slot + '.', libtcod.light_green)
			
	def dequip(self):
		#dequip objet and show a message about it
		if not self.is_equipped: return
		self.is_equipped = False
		message('Dequipped ' + self.owner.name + ' from ' + self.slot + '.', libtcod.light_yellow)

def get_all_equipped(obj): #return a list of equipped items
	if obj == player:
		equipped_list = []
		for item in inventory:
			if item.equipment and item.equipment.is_equipped:
				equipped_list.append(item.equipment)
		return equipped_list
	else:
		return [] #other objects have no equipment. if you want to have monster have equipment duplicate player.
			
def create_room(room, map):

	#go through the tiles in the rectangle and make them passable
	for x in range(room.x1 + 1, room.x2 - 1):
		for y in range(room.y1 + 1, room.y2 - 1):
			map[x][y].blocked = False
			map[x][y].block_sight = False

def create_h_tunnel(x1, x2, y, map):

	#horrizontial tunnel
	for x in range(min(x1, x2), max(x1, x2) +1):
		map[x][y].blocked = False
		map[x][y].block_sight = False
	
def create_v_tunnel(y1, y2, x, map):
	
	#vertical tunnel
	for y in range(min(y1, y2), max(y1, y2) + 1):
		map[x][y].blocked = False
		map[x][y].block_sight = False

def is_occupied(x, y, map):
	#test the map tile to see if it is blocked
	if map[x][y].blocked:		
		return True # if the tile is blocked return true
		
	return False		
		
def is_blocked(x, y, map):
	#first test the map tile
	if map[x][y].blocked:		
		return True
		
	#now check for any blocking objects
	for object in objects:
		if object.blocks and object.x == x and object.y == y:
			return True #if there is already a blocking object on the tile return true
			
	return False		

def make_map():
	global map, player
	global objects, stairs, dungeon_level
	
	#the list of objects with just the player
	objects = [player]
	
	#fill map with "blocked" tiles
	map = [[ Tile(True)
		for y in range(MAP_HEIGHT) ]
			for x in range(MAP_WIDTH) ]	
	
	rooms = []
	num_rooms = 0	

	#initial x, y
	x = MAP_WIDTH / 2 # libtcod.random_get_int(0, 0, MAP_WIDTH - 2)
	y  = MAP_HEIGHT / 2  #libtcod.random_get_int(0, 0, MAP_HEIGHT - 2)
	pick = -1
	yup0 = 1
	yup1 = 1
	yup2 = 1
	yup3 = 1
	w = 7
	h = 7
	map_type = 1 #libtcod.random_get_int(0, 0, 3)
	
	for r in range(MAX_ROOMS):
		
		if map_type == 0:
			#random width and height
			w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
			h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
			
			#random position
			x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 2) # minus 2 is to make the edge of the room not run over the map edge.
			y  = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 2)
		
		else:
			w = libtcod.random_get_int(0, 5, 9)
			h = w
			for t in range(0, 3): # run generation three times to make the rooms
				flip = libtcod.random_get_int(0, 0, 3) # pick one of 4 directions, once the direction is used eliminate that choice so there are not stright runs.
				if flip == 0 and pick !=flip and yup0 == 1:
					x = x - w #- 1
					y = y - h #- 1
					yup0 = -1 # use up this direction
				
				if flip == 1 and pick !=flip  and yup1 == 1:
					x = x + w #+ 1
					y = y - h #- 1
					yup1 = -1 # use up this direction
					
				if flip == 2 and pick !=flip  and yup2 == 1:
					x = x - w #- 1
					y = y + h #+ 1
					yup2 = -1 # use up this direction
					
				if flip == 3 and pick !=flip  and yup3 == 1:
					x = x + w #+ 1
					y = y + h #+ 1
					yup3 = -1 # use up this direction
				#
				multi = 2
				if flip == 0 and pick ==flip and yup0 == 1:
					x = x - multi * w  #- 1
					y = y - multi * h  #- 1
					yup0 = -1 # use up this direction
				
				if flip == 1 and pick ==flip  and yup1 == 1:
					x = x + multi * w #+ 1
					y = y - multi * h #- 1
					yup1 = -1 # use up this direction
					
				if flip == 2 and pick ==flip  and yup2 == 1:
					x = x - multi * w #- 1
					y = y + multi * h #+ 1
					yup2 = -1 # use up this direction
					
				if flip == 3 and pick ==flip  and yup3 == 1:
					x = x + multi * w #+ 1
					y = y + multi * h #+ 1
					yup3 = -1 # use up this direction
				
				if yup0 == -1 and  yup1 == -1 and yup2 == -1 and  yup3 == -1: #reset avaliable directions.
					yup0 = 1
					yup1 = 1
					yup2 = 1
					yup3 = 1
							
				pick = flip 
		# if the generation comes up with rooms outside of the map place a different room.
		if x >= MAP_WIDTH - w - 2:
			x = libtcod.random_get_int(0, 2, MAP_WIDTH - w - 2)
		if y >= MAP_HEIGHT - h - 2:
			y  = libtcod.random_get_int(0, 2, MAP_HEIGHT - h - 2)
			
		
		#"Rect" class makes rectangles easier to work with
		new_room = Rect(x, y, w, h)
		
		
		
		#run through the other rooms and see if they intersect with this one
		failed = False
		for other_room in rooms:
			if new_room.intersection(other_room):
				failed = True
				break
				
		if not failed:
			#this means there are no intersections, so this room is valid
				
			# "paint" it to the map's tiles
			create_room(new_room, map)
			
			#add some contents to this room, such as monsters
			place_objects(new_room)
			
			#center coordinates of new room, will be useful later
			(new_x, new_y) = new_room.center()
			
			# # optional: print "room number to see how the map drawing worked
			# # we may have more than ten rooms, so print 'A' for the first room, 'B' for the next...
			# room_no = Object(new_x, new_y, chr(65+num_rooms), 'room number', libtcod.white) # fails if more than 62 rooms
			# objects.insert(0, room_no) #draw early, so monsters are drawn on top
				
			if num_rooms == 0:
					#this is the first room, where the player starts at
				player.x = new_x
				player.y = new_y
					
			else:
				#all rooms after the first:
				#connect it to the previous room with a tunnel
				
				#center coordinates of previous room
				(prev_x, prev_y) = rooms[num_rooms-1].center()
			
				#draw a coin (random number that is either 0 or 1)
				if libtcod.random_get_int(0, 0, 1) == 1:
					#first move horizontally, then vertically
					create_h_tunnel(prev_x, new_x, prev_y, map)
					create_v_tunnel(prev_y, new_y, new_x, map)
						
				else:
					#first move vertically, then horizontally
					create_v_tunnel(prev_y, new_y, prev_x, map)
					create_h_tunnel(prev_x, new_x, new_y, map)
						
			#finally, append the new room to the list
			rooms.append(new_room)
			num_rooms += 1
			
	#create stairs at the center of the last room
	stairs = Object(new_x, new_y, '<', 'stairs', libtcod.white, always_visible=True)
	objects.append(stairs)
	stairs.send_to_back() #so it's drawn below the monsters, items, players

def place_objects(room):
	
	# maximum number of monsters per room. in thr format of [number, level]
	max_monsters = from_dungeon_level([ [2, 1], [3, 2], [4, 3], [5,4] ])
	
	# chance of each monster. in the format of [%chance, level]
		
	monster_chances = 	{
						'orc' : 80, #orc always shows up, even if all other monsters have 0 chance
						'troll' : from_dungeon_level([ [15, 2], [30, 3], [60, 4], [100, 5] ]),
						'snake' : from_dungeon_level([ [50, 1], [40, 2], [20, 4], [10, 5] ]),
						'trap' : 50,
						'bandit' : 100,
						}
		
	# choose random number of monsters
	num_monsters = libtcod.random_get_int(0, 0, max_monsters)
	for i in range(num_monsters):
		# choose random spot for this monster
		x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
		y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
		
		# only place it if the tile is not blocked
		if not is_blocked(x, y, map):
			choice = random_choice(monster_chances) 
			if choice == 'orc':
				# create orc
				fighter_component = Fighter(hp=libtcod.random_get_int(0, 15, 25), defense=0, power=4, xp=25, death_function=monster_death)
				ai_component = BasicMonster()
				
				monster = Object(x, y, 'o', 'orc', libtcod.desaturated_green,
					blocks=True, fighter=fighter_component, ai=ai_component)
					
			elif choice == 'troll':
				# create a troll
				fighter_component = Fighter(hp=30, defense=libtcod.random_get_int(0, 1, 5), power=libtcod.random_get_int(0, 4, 10), xp=50, death_function=monster_death)
				ai_component = BasicMonster()
								
				monster = Object(x, y, 'T', 'troll', libtcod.darker_green,
					blocks=True, fighter=fighter_component, ai=ai_component)
					
			elif choice == 'snake':
				# create a snake
				fighter_component = Fighter(hp=5, defense=0, power=4, xp=5, death_function=monster_death)
				ai_component = BasicMonster()
				
				monster = Object(x, y, 's', 'snake', libtcod.desaturated_green,
					blocks=True, fighter=fighter_component, ai=ai_component)
					
			elif choice == 'trap':
				# create a trap
				fighter_component = Fighter(hp=2, defense=0, power=4, xp=5, death_function=monster_death)
				ai_component = Trap()
				
				monster = Object(x, y, '.', 'trap', libtcod.desaturated_green,
					blocks=True, fighter=fighter_component, ai=ai_component)	
					
			elif choice == 'bandit':
				# create a bandit
				fighter_component = Fighter(hp=5, defense=2, power=4, xp=10, death_function=monster_death)
				ai_component = RangedMonster()
				
				monster = Object(x, y, 'b', 'bandit', libtcod.darker_green,
					blocks=True, fighter=fighter_component, ai=ai_component)
					
			objects.append(monster)
			if DEBUG == True:
				monster.always_visible = True
			
	# maximum number of items per room in the format of [%chance, level]
	max_items = from_dungeon_level([[2, 1], [3, 2], [2, 3], [3, 4], [5, 5], [6, 8], [7, 10] ])
	
	# chance of each item (by default they have a chance of 0 at level 1, which then goes up)
	item_chances = {}
	item_chances['heal'] = from_dungeon_level([[2, 1], [3, 2], [2, 3], [3, 4], [5, 5], [6, 8], [7, 10] ])#25 #healing potion always shows up, even if all other items have 0 chance
	item_chances['lightning'] = from_dungeon_level([[2, 1], [3, 2], [2, 3], [3, 4], [5, 5], [6, 8], [7, 10] ])#from_dungeon_level([[1, 1], [25, 4]])
	item_chances['fireball'] = from_dungeon_level([[2, 1], [3, 2], [2, 3], [3, 4], [5, 5], [6, 8], [7, 10] ])#from_dungeon_level([[1, 1], [1, 2], [25, 3], [25, 4]])
	item_chances['confuse'] = from_dungeon_level([[2, 1], [3, 2], [2, 3], [3, 4], [5, 5], [6, 8], [7, 10] ])#from_dungeon_level([[1, 1], [1, 1], [25,2]])
	item_chances['sword'] = from_dungeon_level([[2, 1], [3, 2], [2, 3], [3, 4], [5, 5], [6, 8], [7, 10] ])#from_dungeon_level([[1, 1], [3,2]])
	item_chances['shield'] = from_dungeon_level([[2, 1], [3, 2], [2, 3], [3, 4], [5, 5], [6, 8], [7, 10] ])#from_dungeon_level([[1, 1], [2,3]])
	item_chances['axe'] = from_dungeon_level([[2, 1], [3, 2], [2, 3], [3, 4], [5, 5], [6, 8], [7, 10] ])#from_dungeon_level([[1, 1], [2,3]])
	item_chances['AXE OF AWESOME'] = from_dungeon_level([[2, 1], [3, 2], [2, 3], [3, 4], [5, 5], [6, 8], [7, 10] ])#from_dungeon_level([[1,5]])
	item_chances['torch'] = from_dungeon_level([[2, 1], [3, 2], [2, 3], [3, 4], [5, 5], [6, 8], [7, 10] ])#10
	item_chances['dagger'] = from_dungeon_level([[2, 1], [3, 2], [2, 3], [3, 4], [5, 5], [6, 8], [7, 10] ])#from_dungeon_level([[1, 1]])
	item_chances['gold'] = from_dungeon_level([[2, 1], [3, 2], [2, 3], [3, 4], [5, 5], [6, 8], [7, 10] ])#3
	
	# choose random number of itmes
	num_items = libtcod.random_get_int(0, 0, max_items)
	for i in range(num_items):
		# choose random spot for this item
		x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
		y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
		
		# only place an item if the tile is not blocked
		if not is_blocked(x, y, map):
			choice = random_choice(item_chances)
			if choice == 'heal':
				# create a healing potion
				item_component = Item(use_function=cast_heal)
				item = Object(x, y, '!', 'healing potion', libtcod.violet, item=item_component)
				
			elif choice == 'lightning':
				# create a lightning bolt scroll
				item_component = Item(use_function=cast_lightning)
				item = Object(x, y, '#', 'scroll of lightning bolt', libtcod.light_yellow, item=item_component)

			elif choice == 'confuse':
				# create a confuse scroll
				item_component = Item(use_function=cast_confuse)
				item = Object(x, y, '#', 'scroll of confusion', libtcod.light_yellow, item=item_component)
				
			elif choice == 'fireball':
				# create a fireball scroll
				item_component = Item(use_function=cast_fireball)
				item = Object(x, y, '#', 'scroll of fireball', libtcod.light_yellow, item=item_component)
			
			elif choice == 'torch':
				# create a torch light
				item_component = Item(use_function=light_torch)
				item = Object(x, y, 'i', 'torch', libtcod.darker_orange, item=item_component)
			
			elif choice == 'gold':
				# create a torch light
				item_component = Item(use_function=None)
				item = Object(x, y, '$', 'gold', libtcod.yellow, item=item_component)
			
			elif choice == 'sword':
				#create a sword
				power_bonus=4 + libtcod.random_get_int(0,-2,2)
				equipment_component = Equipment(slot='right hand', power_bonus = power_bonus)
				item = Object(x, y, '/', 'sword +%d' % power_bonus, libtcod.sky, equipment=equipment_component)
			
			elif choice == 'shield':
				#create a shield
				equipment_component = Equipment(slot='left hand', defense_bonus=1)
				item = Object(x, y, '[', 'shield', libtcod.darker_orange, equipment=equipment_component)
							
			elif choice == 'axe':
				#create an axe
				power_bonus=7 + libtcod.random_get_int(0,-2,2)
				equipment_component = Equipment(slot='right hand', power_bonus = power_bonus)
				item = Object(x, y, '7', 'axe +%d' % power_bonus, libtcod.black, equipment=equipment_component)
				
			elif choice == 'AXE OF AWESOME':
				#create an axe
				power_bonus=10
				equipment_component = Equipment(slot='right hand',  power_bonus=power_bonus, max_hp_bonus=30)
				item = Object(x, y, '7', 'axe of awesome +%d' % power_bonus, libtcod.darker_blue, equipment=equipment_component)
			
			# have torch take hand slot
			# elif choice == 'torch':
				# #create a torch
				# equipment_component = Equipment(slot='hand')
				# item = Object(x, y, 'i', 'torch', libtcod.darker_orange, equipment=equipment_component)
			
			elif choice == 'dagger':
				power_bonus=2 + libtcod.random_get_int(0,-2,2)
				equipment_component = Equipment(slot='right hand', power_bonus = power_bonus)
				item = Object(x, y, '-', 'dagger +%d' % power_bonus, libtcod.sky, equipment=equipment_component)
			
			objects.append(item)
			item.send_to_back()  #items appear below other objects
			item.always_visible = True # items always visible even outside of FOV, if explored
		
			
def get_equipped_in_slot(slot): #returns the equipment in a slot, or None it it's empty
	for obj in inventory:
		if obj.equipment and obj.equipment.slot == slot and obj.equipment.is_equipped:
			return obj.equipment
	return None

def random_choice_index(chances): #choose one option from list of chances, returning its index
	#the dice will land on some number between 1 and the sum of the chances
	dice = libtcod.random_get_int(0, 1, sum(chances))
	
	#go through all chances, keep the sum so far
	running_sum = 0
	choice = 0
	for w in chances:
		running_sum += w
		
		#see if the dice landed in the part that correspoinds to this choice
		if dice <= running_sum:
			return choice
		choice += 1

def random_choice(chances_dict):
	#choose one option from dictionary of chances, returning its key
	chances = chances_dict.values()
	strings = chances_dict.keys()
	
	return strings[random_choice_index(chances)]	

def from_dungeon_level(table):
	#returns a value that depends on level. the table specifies what value occurs after each level, default is 0.
	#assumes the table is sorted by level in ascending order.
	for (value, level) in reversed(table): # unpack the pair into variables directly in the for
		if dungeon_level >= level:
			return value
	return 0	
	
def menu(header, options, width):
	#error handling
	if len(options) > 9: raise ValueError('Cannot have a Menu with more than 9 options.')
	
	#calculate total height for the header (after auto-wrap) and one line per option
	header_height = libtcod.console_get_height_rect(con, 0, 0, width, SCREEN_HEIGHT, header)
	if header == '':
		header_height = 0	
	height = len(options) + header_height
	
	#create an off-screen console that represents the menu's window
	window = libtcod.console_new(width, height)
	
	#print the header, with auot-wrap
	libtcod.console_set_default_foreground(window, libtcod.white)
	libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)
	
	#print all the options
	y = header_height
	menu_index = ord('a') # use numbers instread of letters for menu
	for option_text in options:
		text = '(' +chr(menu_index) + ') ' + option_text
		libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
		y += 1
		menu_index += 1
		
	#blit the contents of "window" to the root console
	x = SCREEN_WIDTH/2 - width/2
	y = SCREEN_HEIGHT/2 - height/2
	libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7) # last two items show the foreground and back ground transparency
	
	#present the root console to the player and wait for a key-press
	libtcod.console_flush()
	key = libtcod.console_wait_for_keypress(True)
	#key = libtcod.sys_wait_for_event()#this should be used at some point, just don't know how to use it. http://roguecentral.org/doryen/data/libtcod/doc/1.5.2/html2/console_blocking_input.html
	
	if key.vk == libtcod.KEY_ENTER and key.lalt: # special case alt+enter toggle full screen
		libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
	
	#convert the ACII code to an index; if it corresponds to an option, return it
	index = key.c - ord('a')
	if index >= 0 and index < len(options): 
			return index
	return None
	
def render_all():
	global color_dark_wall, color_light_wall
	global color_dark_ground, color_light_ground
	global fov_recompute, fov_map
	global mouse, TORCH_RADIUS
	# if you want to have ascii characters for everything check out this:
	#http://www.roguebasin.com/index.php?title=Complete_Roguelike_Tutorial,_using_Python%2Blibtcod,_extras#Old-school_wall_and_floor_tiles

	move_camera(player.x, player.y)
	
	if fov_recompute:
		
		#torch deminishing. When item is used it doesn't do a recompute and 
		TORCH_RADIUS -=.01
		if TORCH_RADIUS <2:
			TORCH_RADIUS = 2
	
		
		#recompute FOV if needed (the player moved or something)
		fov_recompute = False
		libtcod.map_compute_fov(fov_map, player.x, player.y, int(TORCH_RADIUS), FOV_LIGHT_WALLS, FOV_ALGO)
		libtcod.console_clear(con)
		
		# go through all tiles, and set their background color
		for y in range (CAMERA_HEIGHT):
			for x in range(CAMERA_WIDTH):
				(map_x, map_y) = (camera_x + x, camera_y + y)
				visible = libtcod.map_is_in_fov(fov_map, map_x, map_y,)
				wall = map[map_x][map_y].block_sight
				if not visible:
					#if it's not visible right now, the player can only see it if it's explored
					if map[map_x][map_y].explored:
						#it's out of player's FOV
						if wall:
							libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET )
						else:
							libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET )
				else:
					#it's visible
					if wall:
						libtcod.console_set_char_background(con, x, y, color_light_wall, libtcod.BKGND_SET )
					else:
						libtcod.console_set_char_background(con, x, y, color_light_ground, libtcod.BKGND_SET )
					#scince it's visible, eplore it
					map[map_x][map_y].explored = True
				
	#draw all objects in the list, except player, draw last so it is on top
	for object in objects:
		if object != player:
			object.draw()
	player.draw()
	
	#blit off screen consol with main screen
	libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)
	
	#prepare to render the GUI panel
	libtcod.console_set_default_background(panel, libtcod.black)
	libtcod.console_clear(panel)
	
	#print the game messages, one line at a time
	y = 1
	for (line, color) in game_msgs:
		libtcod.console_set_default_foreground(panel, color)
		libtcod.console_print_ex(panel, MSG_X, y, libtcod.BKGND_NONE, libtcod.LEFT, line)
		y += 1
	
	#show the player's stats
	render_bar(1, 1, BAR_WIDTH, 'HP', player.fighter.hp, player.fighter.max_hp,
		libtcod.light_red, libtcod.darker_red)
		
	libtcod.console_print_ex(panel, 1, 3, libtcod.BKGND_NONE, libtcod.LEFT, 'Dungeon level' + str(dungeon_level))
	
	#display names of objects under the mouse
	libtcod.console_set_default_foreground(panel, libtcod.light_gray)
	libtcod.console_print_ex(panel, 1, 0, libtcod.BKGND_NONE, libtcod.LEFT, get_names_under_mouse())
	
	#blit the contents of "panel" to the root console
	libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)

def inventory_menu(header):
	#show a menu with each item of the inventory as an option
	if len(inventory) == 0:
		options = ['Inventory is empty.']
	else:
		#options = [item.name for item in inventory]
		options = []
		for item in inventory:
			text = item.name
			#show additional information, in case it's equipped
			if item.equipment and item.equipment.is_equipped:
				text = text + ' (in ' + item.equipment.slot + ')'
			options.append(text)
			
		index = menu(header, options, INVENTORY_WIDTH)
	
	# if an item was chose, return it
	if index is None or len(inventory) == 0: return None
	return inventory[index].item

def player_move_or_attack(dx,dy):
	global fov_recompute, TORCH_RADIUS
	
	
	
	#the coordinates the player is moving to/attacking
	x = player.x + dx
	y = player.y + dy
	
	#try to find an attackable object there
	target = None
	for object in objects:
		if object.fighter and object.x == x and object.y == y:
			target = object
			break
			
	#attack if target found, move otherwise
	if target is not None:
		player.fighter.attack(target)
	else:
		player.move(dx, dy)
	fov_recompute = True

def check_level_up():
	# see if the player's experiece is enough to level-up
	level_up_xp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
	if player.fighter.xp >= level_up_xp:
		#it is! level up
		player.level +=1
		player.fighter.xp -= level_up_xp
		message('Your battle skills grow stronger! You reached level ' + str(player.level) + '!', libtcod.yellow)
		choice = None
		
		while choice == None: #keep asking until a choice is made
			choice = menu('Level up! Choose a stat to raise:\n',
				['Constitiution (+20 HP, from ' + str(player.fighter.max_hp) + ')',
				'Strength (+1 attack, from ' + str(player.fighter.base_power) + ')',
				'Agility (+1 defense, from ' + str(player.fighter.defense) + ')',], LEVEL_SCREEN_WIDTH)
				
		if choice == 0:
			player.fighter.base_max_hp += 20
			player.fighter.hp += 20
		elif choice == 1:
			player.fighter.base_power += 1
		elif choice == 2:
			player.fighter.base_defense += 1
		
def handle_keys():
	global key
	global DEBUG
	
	if key.vk == libtcod.KEY_ENTER and key.lalt:
		#Alt+Enter: toggle fullscreen
		libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
	
	if key.vk == libtcod.KEY_ENTER and libtcod.KEY_UP:
		#Debug Mode
		if DEBUG == True:
			DEBUG = False
		else:
			DEBUG = True
	
	elif key.vk == libtcod.KEY_ESCAPE:
		return 'exit' #exit game
		
	if game_state == 'playing':
		
		#test for other keys
		key_char = chr(key.c)
		
		# movement keys
		if key.vk == libtcod.KEY_UP or key.vk == libtcod.KEY_KP8:
			player_move_or_attack(0, -1)
		elif key.vk == libtcod.KEY_DOWN or key.vk == libtcod.KEY_KP2:
			player_move_or_attack(0, 1)
		elif key.vk == libtcod.KEY_LEFT or key.vk == libtcod.KEY_KP4:
			player_move_or_attack(-1, 0)
		elif key.vk == libtcod.KEY_RIGHT or key.vk == libtcod.KEY_KP6:
			player_move_or_attack(1, 0)
		elif key.vk == libtcod.KEY_KP7:
			player_move_or_attack(-1, -1)
		elif key.vk == libtcod.KEY_KP9:
			player_move_or_attack(1, -1)
		elif key.vk == libtcod.KEY_KP1:
			player_move_or_attack(-1, 1)
		elif key.vk == libtcod.KEY_KP3:
			player_move_or_attack(1, 1)
		elif key.vk == libtcod.KEY_KP5:
			pass #do nothing, wait for monsters to come to you
		elif key_char == 'g':
			#pick up an item
			for object in objects: #look for an item in the player's tile
				if object.x == player.x and object.y == player.y and object.item:
					object.item.pick_up()
					break			
			
		elif key_char == 'd':
			#show the inventory; if an item is selected, drop it
			chosen_item = inventory_menu('Press the key next to an item to drop it, or anyother to cancel.\n')
			if chosen_item is not None:
				chosen_item.drop()
				
		elif key_char == 't':
			#show the inventory; if an item is selected, throw it
			chosen_item = inventory_menu('Press the key next to an item to throw it, or anyother to cancel.\n')
			if chosen_item is not None:
				chosen_item.throw()
				return
				
		else:
			if key_char == '<':
				#go down stairs, if the player is on them
				if DEBUG == True:
					next_level()
				elif stairs.x == player.x and stairs.y == player.y:
					next_level()
					
			if key_char == 'c':
				#show character information
				level_up_xp = LEVEL_UP_BASE + player.level * LEVEL_UP_FACTOR
				msgbox('Character Information\n\nLevel: ' + str(player.level) + '\nExperience: ' + str(player.fighter.xp) +
					'\nExperience to level up: ' + str(level_up_xp) + '\n\nMaximum HP: ' + str(player.fighter.max_hp) +
					'\nAttack: ' + str(player.fighter.power) + '\nDefense: ' + str(player.fighter.defense), CHARACTER_SCREEN_WIDTH)
					
			if key_char == '+' and DEBUG == True: # give some freedome to play further to test things.
				cast_heal()
				
			if key_char == 'i': 
				#show inventory
				chosen_item = inventory_menu('Press the key next to an item to use it, or any other to cancel.\n')
				if chosen_item is not None:
					chosen_item.use() # when an item is used a turn will be taken
					return
		
			return 'didnt-take-turn'
			
def get_names_under_mouse():
	global mouse
	
	#return a string with th enames of all objects under th emouse
	(x, y) = (mouse.cx, mouse.cy)
	(x, y) = (camera_x + x, camera_y + y) #from screen to map coordinates
	
	#create a list with the names of all objects at the mouse's coordinates and in FOV
	names = [obj.name for obj in objects
		if obj.x == x and obj.y == y and libtcod.map_is_in_fov(fov_map, obj.x, obj.y)]
		
	names = ', '.join(names) #join the names, separated by commas
	return names.capitalize()

def move_camera(target_x, target_y):
		global camera_x, camera_y, fov_recompute
		
		#new camera coordinates (top-left corner of th escree relative to the map)
		x = target_x - CAMERA_WIDTH / 2 #coordinates so that the target is at the center of the screen
		y = target_y - CAMERA_HEIGHT / 2
		
		#make sure the camera doesn't see outside the map
		if x < 0: x = 0
		if y < 0: y = 0
		if x > MAP_WIDTH - CAMERA_WIDTH - 1: x = MAP_WIDTH - CAMERA_WIDTH - 1
		if y > MAP_HEIGHT - CAMERA_HEIGHT - 1: y = MAP_HEIGHT - CAMERA_HEIGHT - 1
		
		if x != camera_x or y != camera_y: fov_recompute = True
		
		(camera_x, camera_y) = (x, y)

def to_camera_coordinates(x, y):
	#convert coordinates on the map to coordinates on the screen
	(x, y) = (x - camera_x, y - camera_y)
	
	if (x < 0 or y < 0 or x >= CAMERA_WIDTH or y >= CAMERA_HEIGHT):
		return (None, None) # if it's outside the view, return nothing
		
	return (x, y)
	
def cast_heal():
	#heal the player
	if player.fighter.hp == player.fighter.max_hp:
		message('You are already at full health.', libtcod.red)
		return 'cancelled'
		
	message('Your wounds start to feel better!', libtcod.light_violet)
	player.fighter.heal(HEAL_AMOUNT)

def target_tile(max_range=None):
	#return the position of a tile left-click in player's FOV (optionally in a range),
	#or (None,None) if right clicked
	global key, mouse
	while True:
		#render the screen. this erases the inventory and shows the names of objects under the mouse.
		libtcod.console_flush()
		libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE,key,mouse)
		render_all()
		
		(x, y) = (mouse.cx, mouse.cy)
		(x, y) = (camera_x + x, camera_y + y) # from screen to map coordinates
		
		if (mouse.lbutton_pressed and libtcod.map_is_in_fov(fov_map, x, y) and
			(max_range is None or player.distance(x, y) <= max_range)):
			return (x, y)
			
		if mouse.rbutton_pressed or key.vk == libtcod.KEY_ESCAPE:
			return (None, None) # cancel if the player right-clicked or pressed Escape
	
def target_monster(max_range=None):
	#returns a clicked monster inside FOV up to a range, or None if right-clicked
	while True:
		(x, y) = target_tile(max_range)
		if x is None: #player cancelled
			return None
			
		#return the first clicked monster, otherwise continue looping
		for obj in objects:
			if obj.x == x and obj.y == y and obj.fighter and obj != player:
				return obj


				
def cast_fireball():
	#ask the player for a target tile to throw a fireball at
	message('Left-click a target tile for the fireball, or right-click to cancel.', libtcod.light_cyan)
	(x, y) = target_tile()
	if x is None: return 'cancelled'
	message('The fireball explodes, burning everything within ' + str(FIREBALL_RADIUS) + ' tiles!', libtcod.orange)
	
	for obj in objects: #damage every fighter in range, including the player
		if obj.distance(x, y) <= FIREBALL_RADIUS and obj.fighter:
			message('The ' + obj.name + ' gets burned for ' + str(FIREBALL_DAMAGE) + ' hit points.', libtcod.orange)
			obj.fighter.take_damage(FIREBALL_DAMAGE)	

def cast_confuse():
	#find closest enemy in-range adn confuse it
	
	#ask the player for target to confuse
	message('Left-click an enemy to confuse it, or right-click to cancel.', libtcod.light_cyan)
	monster = target_monster(CONFUSE_RANGE)
	if monster is None: return 'canclled'
	
	#replace the monster's AI with a "confused" one; after some turns it will restore the old AI
	old_ai = monster.ai
	monster.ai = ConfusedMonster(old_ai)
	monster.ai.owner = monster #tell the new component who owns it
	message('The eyes of the ' + monster.name + ' look vacant, as he starts to stumble around!', libtcod.light_green)

def cast_lightning():
	#find closest enemy (inside a maximum range) anddamage it
	monster = closest_monster(LIGHTNING_RANGE)
	if monster is None: #no enemy found within maximum range
		message('No enemy is close enough to strike.', libtcod.red)
		return 'cancelled'
	
	#zap it!
	message('A lightning bolt strikes the ' + monster.name + ' with a loud thunder! The damamge is '
		+ str(LIGHTNING_DAMAGE) + ' hit points.', libtcod.light_blue)
	monster.fighter.take_damage(LIGHTNING_DAMAGE)
	
def light_torch():
	global TORCH_RADIUS, fov_recompute
	#increase the amount of light
	message('You light a torch.', libtcod.light_blue)
	TORCH_RADIUS = 10
	fov_recompute = True
	
	
def closest_monster(max_range):
	#find closest enem, up to a maximum range, and in the player's FOV
	closest_enemy = None
	closest_dist = max_range + 1 #start with (slightly more than maximum range
	
	for object in objects:
		if object.fighter and not object == player and libtcod.map_is_in_fov(fov_map, object.x, object.y):
			#calculate distance between this object and the player
			dist = player.distance_to(object)
			if dist < closest_dist: #it's closer, so remember it
				closest_enemy = object
				closest_dist = dist
	return closest_enemy

def player_death(player):
	#the game has ended
	global game_state
	message('You died!', libtcod.red)
	game_state = 'dead'
	
	#for added effect, transform the player into a corpse!
	player.char = '@'
	player.color = libtcod.dark_red
	
		
def monster_death(monster):
	#transform into a corpse. It doesn't block, or attack, or move
	message('The ' + monster.name.capitalize() + ' is dead! You gain ' + str(monster.fighter.xp) + ' experience points.', libtcod.orange)
	monster.char = '%'
	monster.color = libtcod.dark_red
	monster.blocks = False
	monster.fighter = None
	monster.ai = None
	monster.name = 'remains of ' + monster.name
	monster.send_to_back()

def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
	#render a bar (HP, experience, ect). first calculate the width of the bar
	bar_width = int(float(value) / maximum * total_width)
	
	#render the background first
	libtcod.console_set_default_background(panel, back_color)
	libtcod.console_rect(panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)
	
	#now render the bar on top
	libtcod.console_set_default_background(panel, back_color)
	libtcod.console_rect(panel, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)
	
	#now render the bar on top
	libtcod.console_set_default_background(panel, bar_color)
	if bar_width > 0:
		libtcod.console_rect(panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)
		
	#finally, some centered text with th evalues
	libtcod.console_set_default_foreground(panel, libtcod.white)
	libtcod.console_print_ex(panel, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER,
		name + ': ' + str(value) + '/' + str(maximum))

def message(new_msg, color = libtcod.white):
	#split the message if necessary, among multiple lines
	new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)
	
	for line in new_msg_lines:
		#if the buffer is full,remove the first line to make room for the new one
		if len(game_msgs) == MSG_HEIGHT:
			del game_msgs[0]
			
		#add the new line as a tuple, with the text and the color
		game_msgs.append( (line, color) )

def new_game():
	global player, inventory, game_msgs, game_state, dungeon_level, TORCH_RADIUS
	
	#create object representing the player
	fighter_component = Fighter(hp=100, defense=1, power=2, xp=0, death_function=player_death)
	player = Object(0, 0, '@', 'player', libtcod.white, blocks=True, always_visible=True, fighter=fighter_component)
	
	player.level = 1
	
	dungeon_level = 1
	#generate map (at this point it's not drawin to the screen)
	make_map()
	initialize_fov()
	
	game_state = 'playing'
	inventory = []
	
	#create the list of game messages and their colors, starts empty
	game_msgs = []
	
	#opening game message
	message('You fall through a hole in the ground. It\'s dark you should light a torch.', libtcod.red)
	message('Press [i] to access your inventory, [g] to get, [t] to thow, [d] to drop, [c] for character screen', libtcod.red)
	
	#initial equipment: a dagger
	equipment_component = Equipment(slot='right hand', power_bonus=2)
	obj = Object(0, 0, '-', 'dagger', libtcod.sky, equipment=equipment_component)
	inventory.append(obj)
	equipment_component.equip()
	obj.always_visible = True
	
	#torch to reduce as time goes on
	TORCH_RADIUS = 3
	
	#initial equipment: a torch
	item_component = Item(use_function=light_torch)	
	obj = Object(0, 0, 'i', 'torch', libtcod.darker_orange, item=item_component)
	inventory.append(obj)
	obj.always_visible = True

def initialize_fov():
	global fov_recompute, fov_map
	fov_recompute = True
	
	#create the FOV map, according to the generated map
	fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
	for y in range(MAP_HEIGHT):
		for x in range(MAP_WIDTH):
			libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)
			
	libtcod.console_clear(con) #unexplored areas start as the default background color

def play_game():
	global key, mouse, camera_x, camera_y
	
	player_action = None
	
	mouse = libtcod.Mouse()
	key = libtcod.Key()
	
	(camera_x, camera_y) = (0, 0)
	
	while not libtcod.console_is_window_closed():
		#render the screen
		libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE,key,mouse)
		render_all()

		libtcod.console_flush()
		
		check_level_up()
		
		#erase all objects at their old locations, before they move
		for object in objects:
			object.clear()
		
		#handle keys and exit game if needed
		player_action = handle_keys()
		if player_action == 'exit':
			save_game()
			break
			
		#let monsters take their turn
		if game_state == 'playing' and player_action != 'didnt-take-turn':
			for object in objects:
				if object.ai:
					object.ai.take_turn()

def next_level():
	global dungeon_level
	#advance to the next level
	message('You take a moment to rest, and recover your strength.', libtcod.light_violet)
	player.fighter.heal(player.fighter.max_hp /2) #heal the player by 50%
	
	message('After a rare moment of peace, you descend deeper into the heart of the dungeon...', libtcod.red)
	dungeon_level +=1
	make_map() #create a fresh new level!
	initialize_fov()

def main_menu():
	img = libtcod.image_load('menu_background.png')
	
	while not libtcod.console_is_window_closed():
		#show the background image, at twice the regular console resolution
		libtcod.image_blit_2x(img, 0, 0, 0)
		
		#show the game's title, and some credits
		libtcod.console_set_default_foreground(0, libtcod.light_yellow)
		libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT/2-4, libtcod.BKGND_NONE, libtcod.CENTER,
			'TOMB OF THE ANCIENT KINGS')
		libtcod.console_print_ex(0, SCREEN_WIDTH/2, SCREEN_HEIGHT-2, libtcod.BKGND_NONE, libtcod.CENTER,
			'By Rob')
		
		#show options and wait for th eplayer's choice
		choice = menu('', ['Play a new game', 'Continue last game', 'Quit'], 24)
		
		if choice == 0: #new game
			new_game()
			play_game()
		if choice == 1: #load last game
			try:
				load_game()
			except:
				msgbox('\n No saved game to load.\n', 24)
				continue
			play_game()
		elif choice == 2: #quit
			break

def msgbox(text, width=50):
	menu(text, [], width) #use menu() as a sort of "message box"
	
def save_game():
	#open a new empty shelve (possibly overwriting an old one) to write the game data
	file = shelve.open('FirstRLsavegame', 'n')
	file['map'] = map
	file['objects'] = objects
	file['player_index'] = objects.index(player) # index of player objects list because the rest is in objects
	file['inventory'] = inventory
	file['game_msgs'] = game_msgs
	file['game_state'] = game_state
	file['stair_index'] = objects.index(stairs)
	file['dungeon_level'] = dungeon_level
	file['torch_radius'] = TORCH_RADIUS
	file.close()

def load_game():
	#open the previously saved shelve and load the game data
	global map, objects, player, inventory, game_msgs, game_state, stairs, dungeon_level
	
	file = shelve.open('FirstRLsavegame', 'r')
	map = file['map']
	objects = file['objects']
	player = objects[file['player_index']] #get index of player in objects list and access it
	inventory = file['inventory']
	game_msgs = file['game_msgs']
	game_state = file['game_state']
	stairs = objects[file['stair_index']]
	dungeon_level = file['dungeon_level']
	TORCH_RADIUS = file['torch_radius']
	file.close()
	
	initialize_fov()
	
#########################################
#Initialization & Main Loop
#########################################

###system initialization###
# Custom font / Tileset
libtcod.console_set_custom_font('arial12x12.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'RogueLike Game', False)
libtcod.sys_set_fps(LIMIT_FPS)# realtime game code, commented out to give turn based gameplay
con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT) #create off screen console
panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)

main_menu()
