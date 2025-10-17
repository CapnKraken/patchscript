import pygame
from pygame.locals import *
import math
import random
import traceback # for error reporting
from pathlib import Path # for opening files and making directories

import sys

#region GAME OBJECT CLASS
# ================================================================================================

class gobj:

    globs:dict = {
        '_sfx_vol':100,
        '_music_vol':100,
        '_music':'silence',
        '_paused':0,
        '_local_directory':"",
    }         # 'globs' is short for 'globals' i.e. global variables
    statics = [] # statics stores raw strings

    colliders:list[pygame.Rect] = []
    object_map:list[int] = []
    dead_objects:list[int] = []
    objects:dict = {}
    collider_count:int = 0
    current_id = 0

    music_paused = False
    music_playing_current = None
    music_seek_offset = 0

    # not the most elegant solution but presumably will work
    apply_sysvars_flag = False
    apply_fullscreen_change_flag = True # true because it will apply when the program starts

    resolution:tuple[int,int]

    messages:list = []  # messages stores, well, messages. For inter-object communication.
    sprites:dict = {}   # sprites stores the surfaces containing the loaded game graphics
    sounds:dict = {}    # sounds stores the sound effects and how long they take
    fonts:dict = {'default':None}     # stores all of the loaded fonts

    collision_mask:pygame.Mask = None
    
    renderlist = []     # all the renderable objects are added to this list each frame

    _FINISHED = False   # if this is true, the program ends.

    obj_init_atts = (
            ('_x',0),
            ('_y',0),
            ('_global_x',0),
            ('_global_y',0),
            ('_rotation',0),
            ('_fliph',0),
            ('_flipv',0),
            ('_sprite',-1),
            ('_width',0),
            ('_height',0),
            ('_draw_r', 0),
            ('_draw_g',0),
            ('_draw_b',0),
            ('_draw_a',-1),
            ('_draw_stroke',0),
            ('_draw_centered',1),
            ('_draw_font',"default"),
            ('_draw_antialiased',0),
            ('_ignore_pause', 0),
            ('_hide_errors', 0),
            ('_transform_children', 0)
        )

    def __init__(self, script_file:str, attributes:dict, parent_obj_id:int, is_root=False):
        # global_pos is very important as it controls the position
        self.global_pos:list[float] = [0,0]

        # attributes is very important as it controls basically everything else.
        self.attributes = {}

        self.children:list[gobj] = []

        if is_root:
            self.parent_obj = None
        else:
            self.parent_obj = parent_obj_id

        # set the immutable id of the object. No other object will ever have this id
        self.immut_id = gobj.current_id
        gobj.current_id += 1
        #print(self.immut_id)
        gobj.objects[self.immut_id] = self

        self.script_file = script_file
        self.scriptsys = scriptsystem(self,script_file)

        # gobj only needs a canvas if it's using the 'draw' functionality
        self.canvas:pygame.Surface = None
        self.canvas_rect:pygame.Rect = None
        self.is_canvas_dirty = False

        self.new_color_shift = [0,0,0,0]

        self.is_dead = False
        self.is_root = is_root
        
        # make a deep copy of the given dictionary
        for item in attributes:
            self.set(item, attributes[item])

        self.collision_rect = None
        self.c_index = None

        self.initattributes(gobj.obj_init_atts)

        if self.is_root:
            self.set('_ignore_pause', 1)

        self.render_rect = None
        self.render_surface = None
        self.has_sprite = False

        # initialize update flags
        self.update_position = False
        self.update_rotation = False
        self.update_flip = False
        self.update_scale = False
        self.update_color = False

        self.abnormal_scale = False

        self.default_width = 0
        self.default_height = 0

        # sprite transformations
        self.rotation_matrix = [1, 0, 0, 1]

        self.setposition(0,0)

        self.prev_x = self.get('_x')
        self.prev_y = self.get('_y')
        self.prev_rot = self.get('_rotation')
        self.prev_fliph = self.get('_fliph')
        self.prev_flipv = self.get('_flipv')
        self.prev_width = self.get('_width')
        self.prev_height = self.get('_height')
        self.prev_color_shift = self.new_color_shift

    def initattributes(self, attributes:tuple):
        for attribute in attributes:
            if not attribute[0] in self.attributes:
                self.attributes[attribute[0]] = attribute[1]
    
    def get(self, key):
        try:
            return self.attributes[key]
        except:
            return None
    
    def set(self, key, value):
        self.attributes[key] = value
        return value
    
    # the main loop will blits() a list of these to the main display surface
    def getrendertuple(self):
        rect = self.render_rect
        surf = self.render_surface

        if rect and surf:
            return (surf, rect)
        else:
            return None
    
    # takes the draw_r, ..g, ..b, ..a values and turns them into a color.
    def get_color(self):
        r = self.attributes['_draw_r']
        g = self.attributes['_draw_g']
        b = self.attributes['_draw_b']
        a = self.attributes['_draw_a']

        color = [r, g, b]
        if a != -1:
            color.append(a)
        
        for item in color:
            if not type(item) is int:
                item = 0
            if item < 0:
                item = 0
            elif item > 255:
                item = 255
        return color

    # Copy of get_numeric from playhead.
    def get_numeric_coordinate(self, token):
        try:
            result = float(self.attributes[token])
            return result
        except:
            error("Runtime", "Conversion Error", "Can't convert",str(type(self.attributes(token))), "to numeric.",self)

    # Test the values of certain variables to determine if you need to update transformations     
    def test_transformations(self):
        x = self.get('_x')
        y = self.get('_y')
        rot = self.get('_rotation')
        fh = self.get('_fliph')
        fv = self.get('_flipv')
        w = self.get('_width')
        h = self.get('_height')
        
        self.update_position = x != self.prev_x or y != self.prev_y
        self.update_rotation = rot != self.prev_rot
        self.update_flip = fh != self.prev_fliph or fv != self.prev_flipv
        self.update_scale = w != self.prev_width or h != self.prev_height
        self.update_color = self.new_color_shift != self.prev_color_shift

        self.abnormal_scale = w != self.default_width or h != self.default_height

        transforms = {}

        if self.update_position:
            self.prev_x = x
            self.prev_y = y
        if self.update_rotation:
            transforms['r'] = rot-self.prev_rot
            self.prev_rot = rot
        if self.update_flip:
            transforms['fh'] = int(self.prev_fliph != fh)
            transforms['fv'] = int(self.prev_flipv != fv)
            self.prev_fliph = fh
            self.prev_flipv = fv
        if self.update_scale:
            self.prev_width = w
            self.prev_height = h
        if self.update_color:
            self.prev_color_shift = self.new_color_shift
        return transforms

    # Verify that an object we want to add to an object's child list is not an ancestor of that object.
    def check_valid_adoption(self, intended_adoptee:int)->bool:
        if intended_adoptee == 0:
            return False

        check_obj:int = self.immut_id
        while check_obj != 0:
            if check_obj == intended_adoptee:
                return False
            
            temp_obj:gobj = gobj.objects[check_obj]
            check_obj = temp_obj.parent_obj

        return True

    # update the object's state and its childrens' states
    def obj_tick(self):

        if gobj.globs['_paused'] and self.attributes['_ignore_pause'] == 0:
            return

        self.scriptsys.script_tick()

        # remove inactive children
        removal_indexes = []
        for i, child in enumerate(self.children):
            if child.is_dead:
                removal_indexes.append(i)
        for index in reversed(removal_indexes):
            self.children.pop(index)

        # update transformations
        transforms = self.test_transformations()

        update_transform = False
        if self.update_rotation:
            update_transform = True
            # update matrix here
            if self.get('_transform_children'):
                angle = math.radians(self.get('_rotation'))
                self.rotation_matrix = [
                    math.cos(angle), -math.sin(angle),
                    math.sin(angle), math.cos(angle)
                ]


        if self.update_flip or self.update_scale or self.update_color:
            update_transform = True
            
        if update_transform and self.has_sprite:
            spr = self.get('_sprite')
            fliph = self.get('_fliph')
            flipv = self.get('_flipv')
            rot = self.get('_rotation')

            if self.update_scale or (self.abnormal_scale and self.update_rotation):
                width = self.get('_width')
                height = self.get('_height')
                self.setsprite(spr, fliph, flipv, rot, self.new_color_shift, width, height)
            else:
                self.setsprite(spr, fliph, flipv, rot, self.new_color_shift)


        # update active children
        for child in self.children:
            child_pos = [child.get_numeric_coordinate('_x'), child.get_numeric_coordinate('_y')]
            
            if self.get('_transform_children'):
                if self.update_rotation:
                    child.set('_rotation', child.get('_rotation')+transforms['r'])
                if self.update_flip:
                    if transforms['fh']:
                        child.set('_fliph', int(not child.get('_fliph')))
                    if transforms['fv']:
                        child.set('_flipv', int(not child.get('_flipv')))
                if self.get('_fliph'):
                    child_pos[0] *= -1
                if self.get('_flipv'):
                    child_pos[1] *= -1

                if self.get('_rotation'):
                    x = child_pos[0]
                    y = child_pos[1]
                    a = self.rotation_matrix[0]
                    b = self.rotation_matrix[1]
                    c = self.rotation_matrix[2]
                    d = self.rotation_matrix[3]

                    child_pos[0] = x*a + y*b
                    child_pos[1] = x*c + y*d

            child.setposition(child_pos[0] + self.global_pos[0], child_pos[1] + self.global_pos[1])
            child.obj_tick()
    
    def render(self):
        if self.canvas:
            gobj.renderlist.append((self.canvas, self.canvas_rect))
        rt = self.getrendertuple()
        if rt:
            gobj.renderlist.append(rt)
        
        for child in self.children:
            child.render()

    # respond to messages
    def respond(self):
        for msg in gobj.messages:
            self.scriptsys.respond(msg[0], msg[1])
        
        for child in self.children:
            child.respond()

    # if an object is marked dead, it will be deleted when the frame is done processing
    def markdead(self):
        if self.is_dead:
            return

        self.is_dead = True
        gobj.dead_objects.append(self.immut_id)

        # mark the child objects for deletion
        for child in self.children:
            child.markdead()
        
        # sever the connection
        self.children.clear()

    # set the object's visual sprite, with optional parameters for flipping and rotation
    def setsprite(self,sprite,fliph=0, flipv=0, rot=0, color_shift=[0,0,0,0], width=-1, height=-1):
        if sprite == -1:
            return
        elif sprite == 0:
            surf = self.render_surface
        else:
            surf = pygame.transform.flip(gobj.sprites[sprite], fliph, flipv)

        if color_shift[0:3] == [0,0,0] and color_shift[3] != 0:
            surf.set_alpha(surf.get_alpha() + color_shift[3])
        elif color_shift != [0,0,0,0]:

            pixarr = pygame.PixelArray(surf)
            for i, row in enumerate(pixarr):
                for j, item in enumerate(row):
                    new_color = color_shift.copy()
                    mapped = surf.unmap_rgb(item)
                    if mapped.a != 0:

                        new_color[0] += mapped.r
                        new_color[1] += mapped.g
                        new_color[2] += mapped.b
                        new_color[3] += mapped.a

                        for k in range(len(new_color)):
                            if new_color[k] > 255:
                                new_color[k] = 255
                            if new_color[k] < 0:
                                new_color[k] = 0

                        pixarr[i,j] = tuple(new_color)
            surf = pixarr.make_surface()
            pixarr.close()

        if width != -1:
            surf = pygame.transform.scale(surf, [width, height])
            self.set('_width', width)
            self.set('_height', height)
        else:
            sz = surf.get_size()
            self.set('_width', sz[0])
            self.set('_height', sz[1])
            self.default_width = sz[0]
            self.default_height = sz[1]
        if rot != 0:
            surf = pygame.transform.rotate(surf, -rot)
        self.render_surface = surf
        render_sz = surf.get_size()
        self.render_rect = pygame.Rect(0, 0, render_sz[0], render_sz[1])
        self.render_rect.center = self.global_pos

        self.has_sprite = True

        '''
        1. get main surface
        2. scale to size
        3. rotate
        4. set render rect
        '''

    # return a list containing the id's of all objects colliding with the caller
    def testcollisions(self, ph):
        rect:pygame.Rect = self.collision_rect
        collisions = rect.collidelistall(gobj.colliders)
        collided_objects = []
        for item in collisions:
            obj_id = gobj.object_map[item]
            if obj_id != self.immut_id:
                collided_objects.append(obj_id)
        ph.setvar("_return", collided_objects)
    
    # set the object's position directly
    def setposition(self, x, y):
        self.global_pos[0] = x
        self.global_pos[1] = y
        col_rect:pygame.Rect = self.collision_rect
        ren_rect:pygame.Rect = self.render_rect
        if col_rect:
            #col_rect.center = (round(self.global_pos[0]), round(self.global_pos[1]))
            col_rect.center = self.global_pos
        if ren_rect:
            #ren_rect.center = (round(self.global_pos[0]), round(self.global_pos[1]))
            ren_rect.center = self.global_pos
        self.update_position = True
    
    
    # move the object a certain x and y value
    def move(self, vel):
        self.global_pos[0] += vel[0] # x
        self.global_pos[1] += vel[1] # y

        # update the local position variables as well
        local_x = self.attributes['_x']
        local_y = self.attributes['_y']
        self.set('_x', local_x + vel[0])
        self.set('_y', local_y + vel[1])

        self.set('_global_x', self.global_pos[0])
        self.set('_global_y', self.global_pos[1])
        
        col_rect:pygame.Rect = self.collision_rect
        ren_rect:pygame.Rect = self.render_rect
        if col_rect:
            #col_rect.center = (round(self.global_pos[0]), round(self.global_pos[1]))
            col_rect.center = self.global_pos
        if ren_rect:
            #ren_rect.center = (round(self.global_pos[0]), round(self.global_pos[1]))
            ren_rect.center = self.global_pos
        self.update_position = True
    
    def calculatemotionvector(self, direction, magnitude):
        # calculate actual speed vector

        # make sure the values exist
        if magnitude == None or direction == None:
            return [0,0]

        motion = [0,0]

        # x component
        motion[0] = math.cos(math.radians(direction)) * magnitude
        # y component
        motion[1] = math.sin(math.radians(direction)) * magnitude

        return motion

    def anglebetweentwopoints(self, origin, target):
        # format it so the origin would be (0,0)
        adjusted = (target[0]-origin[0], target[1]-origin[1])
        if adjusted[0] == 0:
            if adjusted[1] > 0:
                result = 90
            else:
                result = 270
        else:
            rads = math.atan(adjusted[1]/adjusted[0])
            #print("rads:",rads)
            result = math.degrees(rads)
            #print("deg:",result)
            if adjusted[0] < 0:
                result += 180
        return result

    def calculatedistance(self, origin, target):
        # apply distance formula to find distance between 2 points
        x = target[0] - origin[0]
        x = x ** 2
        y = target[1] - origin[1]
        y = y ** 2
        return (math.sqrt(x + y))
    
    def playsound(self, sound):
        s:tuple[pygame.mixer.Sound, int] = gobj.sounds.get(sound)
        s[0].set_volume(gobj.globs.get('_sfx_vol')/100)
        if s:
            s[0].play(maxtime=s[1])
    
    # add a message and some messagedata to the global message queue
    def sendmessage(self, message):
        gobj.messages.append(message)
    
    # CLASS METHODS

    # delete an object from all global lists
    def delobj(obj_immut_id:int):
        obj:gobj = gobj.objects.pop(obj_immut_id)

        if obj.collision_rect != None:
            gobj.colliders.pop(obj.c_index)
            gobj.object_map.pop(obj.c_index)

            gobj.collider_count -= 1

            # reduce id's by 1
            for i in range(obj.c_index, len(gobj.object_map)):
                #print("changing c_index of:", gobj.objects[gobj.object_map[i]])
                gobj.objects[gobj.object_map[i]].c_index -= 1

    def trap_error(obj_immut_id:int, error_type:str):
        obj:gobj = gobj.objects.get(obj_immut_id)
        for hat in obj.scriptsys.hats:
            if hat[0] == 'trap':
                new_ph = playhead(hat[1], obj)
                new_ph.variables['_error_type'] = error_type
                obj.scriptsys.playheads.append(new_ph)
#endregion

#region SCRIPTING SYSTEM CLASSES
# ================================================================================================

# allow for custom file path names. If the path starts with "\", it denotes a custom path
def getpathname(givenpath:str, filetype:int):
    result = ""

    local_dir = gobj.globs.get("_local_directory")
    #print("local directory:", local_dir)
    if local_dir != "":
        result += f"{local_dir}/"

    if givenpath[0] == "\\":
        result = givenpath.strip("\\")
    else:
        match filetype:
            case 1: # image
                result += "visuals/"+givenpath
            case 2: # audio
                result += "audio/"+givenpath
            case 3: # data
                result += "data/"+givenpath
            case 4: # font
                result += "fonts/"+givenpath
            case _: # script
                result += "scripts/"+givenpath+".patch"

    return result

#region PLAYHEAD

# class to keep track of data for independently running scripts
class playhead:
    def __init__(self, startindex, parent_obj:gobj):
        self.variables = {}             # store of all the variables the script is operating on
        self.wait_timer = 0             # if >0, script will yield and decrement the counter
        self.skip_to = None             # if != None, script will skip until it find the correct command
        self.pc_stack = [startindex+1]   # stack of ints representing the program counters
        self.stacklen = 0
        self.is_running = True          # when this is false, the playhead is deleted

        self.parent_obj = parent_obj
        self.has_error = False

    def printdata(self):
        print('\nstack:', self.pc_stack)
        print('wait:', self.wait_timer)
        print('running:', self.is_running)
        print('skip:', self.skip_to)
        print('vars:', self.variables)
    
    def postfix_check_false(self, item):
        match item:
            case int():
                return item == 0
            case float():
                return item == 0.0
            case str():
                return item == ""
            case list():
                return item == []
        return False

    # Evaluate a postfix (operators following operands) expression.
    def postfix_eval(self, expression:list):
        eval_stack = []
        # In this scheme, '^' is power, '~' is xor.
        stacklen = 0

        for item in expression:
            if item in operators:

                result = 0

                if item in {'not', 'len', 'sin', 'cos', 'tan', 'arcsin', 'arccos', 'arctan', 'lower', 'upper', 'abs', 'round', 'int', 'float', 'str'}:
                    # Handle unary operators

                    if stacklen < 1:
                        error("Runtime", "Evaluation error.", f"Not enough operands for operator '{item}'.", self)
                        return 0
                    
                    op1 = eval_stack.pop()
                    if type(op1) is str:
                        op1 = self.get_any(op1)
                    elif type(op1) is float and op1.is_integer():
                        op1 = int(op1)
                    stacklen -= 1

                    match item:
                        case 'not':
                            # Handle the unary 'not' operator
                            # If the item is equivalent to false, 'not' will set it to true, that is, 1. Otherwise it'll be set to 0.
                            if self.postfix_check_false(op1):
                                result = 1
                        case 'len':
                            # length of a string or list
                            try:
                                result = len(op1)
                            except:
                                error("Runtime", "Evaluation error.", f"Invalid type '{type(op1)}' for '{item}' operator: must be string or list.", self)
                                return 0
                        case 'lower':
                            try:
                                result = op1.lower()
                            except:
                                error("Runtime", "Evaluation error.", f"Invalid type '{type(op1)}' for '{item}' operator: must be a string.", self)
                                return 0
                        case 'upper':
                            try:
                                result = op1.upper()
                            except:
                                error("Runtime", "Evaluation error.", f"Invalid type '{type(op1)}' for '{item}' operator: must be a string.", self)
                                return 0
                        case 'abs':
                            try:
                                result = abs(op1)
                            except:
                                error("Runtime", "Evaluation error.", f"Invalid type '{type(op1)}' for '{item}' operator: must be numeric.", self)
                                return 0
                        case 'round':
                            try:
                                result = round(op1)
                            except:
                                error("Runtime", "Evaluation error.", f"Invalid type '{type(op1)}' for '{item}' operator: must be numeric.", self)
                                return 0
                        case 'int':
                            try:
                                result = int(op1)
                            except:
                                error("Runtime", "Evaluation error.", f"Cannot convert '{op1}' type '{type(op1)}' to type 'int'.", self)
                                return 0
                        case 'float':
                            try:
                                result = float(op1)
                            except:
                                error("Runtime", "Evaluation error.", f"Cannot convert '{op1}' type '{type(op1)}' to type 'float'.", self)
                                return 0
                        case 'str':
                            result = self.string_rep(op1)
                        case _:
                            # Trig unary operators
                            if item in {'sin', 'cos', 'tan', 'arcsin', 'arccos', 'arctan'}:
                                try:
                                    in_rads = math.radians(op1)
                                    match item:
                                        case "sin":
                                            result = math.sin(in_rads)
                                        case "cos":
                                            result = math.cos(in_rads)
                                        case "tan":
                                            result = math.tan(in_rads)
                                        case "arcsin":
                                            result = math.asin(in_rads)
                                        case "arccos":
                                            result = math.acos(in_rads)
                                        case "arctan":
                                            result = math.atan(in_rads)
                                except:
                                    error("Runtime", "Evaluation error.", f"Invalid type '{type(op1)}' for '{item}' operator: must be int or float.", self)   
                                    return 0  
                else:
                    # All other operators require two operands
                    if stacklen < 2:
                        error("Runtime", "Evaluation error.", f"Not enough operands for operator '{item}'.", self)
                        return 0
                    
                    op2 = eval_stack.pop()
                    op1 = eval_stack.pop()

                    if type(op2) is str:
                        op2 = self.get_any(op2)
                    elif type(op2) is float and op2.is_integer():
                        op2 = int(op2)

                    if type(op1) is str:
                        op1 = self.get_any(op1)
                    elif type(op1) is float and op1.is_integer():
                        op1 = int(op1)
                    
                    stacklen -= 2

                    # Testing the operators ascending order of rigidity
                    if item in {'and', 'or', '==', '!='}:
                        # These ones work with all data types
                        match item:
                            case 'and':
                                if not (self.postfix_check_false(op1) or self.postfix_check_false(op2)):
                                    result = 1
                            case 'or':
                                if not (self.postfix_check_false(op1) and self.postfix_check_false(op2)):
                                    result = 1
                            case '==':
                                result = int(op1 == op2)
                            case '!=':
                                result = int(op1 != op2)
                    elif item == '`': # array subscript operator
                        try:
                            if op2 < 0 or op2 >= len(op1):
                                error("Runtime", "Evaluation error.", f"Index {op2} is out of range. Must be between 0 and {len(op1)-1}.", self)
                                return 0
                            result = op1[op2]
                        except:
                            error("Runtime", "Evaluation error.", f"Invalid types {type(op1)} and {type(op2)} for operator '{item}'. Expected 'list/string' and 'int'.", self)
                            return 0
                    else:
                        # Lists are now invalid for any other thing
                        if type(op1) is list or type(op2) is list:
                            error("Runtime", "Evaluation error.", f"Invalid type 'list' for operator '{item}'.", self)
                            return 0
                        
                        has_strings = (type(op1) is str or type(op2) is str)
                        if item == '+' and has_strings:
                            result = self.string_rep(op1) + self.string_rep(op2)

                        elif item in {'+', '<', '>', '<=', '>='}:
                            #if not (type(op1) is str and type(op2) is str) and (type(op1) is str or type(op2) is str):
                            if has_strings:
                                error("Runtime", "Evaluation error.", f"Incompatible types '{type(op1)}' and '{type(op2)}' for operator '{item}'.", self)
                                return 0
                            match item:
                                case '+':
                                    result = op1 + op2
                                case '<':
                                    result = int(op1 < op2)
                                case '>':
                                    result = int(op1 > op2)
                                case '<=':
                                    result = int(op1 <= op2)
                                case '>=':
                                    result = int(op1 >= op2)
                        else:
                            # Strings are now invalid
                            if type(op1) is str or type(op2) is str:
                                error("Runtime", "Evaluation error.", f"Invalid type 'string' for operator '{item}'.", self)
                                return 0
                            
                            if item in {'-', '*', '/', '//', '^'}:
                                match item:
                                    case '-':
                                        result = op1 - op2
                                    case '*':
                                        result = op1 * op2
                                    case '/':
                                        result = op1 / op2
                                    case '//':
                                        result = op1 // op2
                                    case '^':
                                        result = op1 ** op2
                            else:
                                # floats are now invalid
                                if type(op1) is float or type(op2) is float:
                                    error("Runtime", "Evaluation error.", f"Invalid type 'float' for operator '{item}'.", self)
                                    return 0
                                
                                match(item):
                                    case '%':
                                        result = op1 % op2
                                    case '&':
                                        result = op1 & op2
                                    case '|':
                                        result = op1 | op2
                                    case '~': # xor
                                        result = op1 ^ op2
                                    case '<<': # left shift
                                        result = op1 << op2
                                    case '>>': # right shift
                                        result = op1 >> op2
                if type(result) is str:
                    eval_stack.append('"' + result)
                    #print(eval_stack)
                else:   
                    eval_stack.append(result)
                stacklen += 1
                            
            else:
                eval_stack.append(item) # add an operand
                stacklen += 1
        
        if stacklen != 1:
            # Should have one element in it after running through entire list.
            error("Runtime", "Invalid expression.", f"Expression {expression} does not evaluate to a single answer.", self)
            return 0
        else:
            if type(eval_stack[0]) is str:
                return eval_stack[0].strip('"')
            return eval_stack[0]
    
    def get_any(self, token):
        match token:
            case int() | float():
                return token
            case str():
                try:
                # See if it's a numeric
                    # if it's already a float
                    result = float(token)
                    return int(result) if result.is_integer() else result
      
                except:
                    # first, see if it's a string
                    if token[0] == '"':
                        #print(token, token.strip('"'))
                        return token.strip('"')
                    
                    # then a list
                    if token[0] == '[':
                        return self.parse_array_literal(token)

                    # otherwise, see if it's a variable
                    value = self.getvar(token)
                    if value == None:
                        return 0
                    return value
            case _:
                print(f"type is {type(token)}")

    def get_gobj(self, token):
        try:
            value = int(self.getvar(token))
            return gobj.objects[value]
        except ValueError:
            error("Runtime", "Conversion Error", "Can't convert",str(type(value)), "to gobj.",self)
            return 0
        except KeyError:
            error("Runtime", "ID not found", f"No object with ID {value}\n{gobj.objects.keys()}",self)
            return 0

    def split_array_token(self, token:str) -> list:
        bracket_count = 0
        split_start = 0
        result = []
        for i, item in enumerate(token):
            if item == '[':
                if bracket_count == 0:
                    split_start = i
                bracket_count += 1
            elif item == ']':
                bracket_count -= 1
            elif item == ',':
                if bracket_count == 0:
                    result.append(token[split_start:i])
                    split_start = i+1
        result.append(token[split_start:])
        return result

    def parse_array_literal(self, token:str) -> list:
        if len(token) < 2:
            error("Runtime", "Invalid array literal.", f"'{token}' is not a valid array literal.", self)
            return []
        
        if len(token[1:-1]) == 0:
            return []

        array = []

        elements = self.split_array_token(token[1:-1])
        for item in elements:
            array.append(self.get_any(item))
        
        return array

    def get_list(self, token:str):

        if token[0] == '[': # array literal
            return self.parse_array_literal(token)

        value = self.getvar(token)
        if value == None:
            result = []
            return result
        
        match value:
            case list():
                return value
            case _:
                return [value]
    
    def get_string(self, token):
        if token[0] == '"':
            return token.strip('"')
    
        if token[0] == '[':
            return self.string_rep(self.parse_array_literal(token))

        value = self.getvar(token)
        if value == None:
            error("Runtime", "No such string", f"Variable {token} not found.", self)
            return 0

        return self.string_rep(value)
    
    def string_rep(self, value):
        match value:
            case int():
                return str(value)
            case float():
                return str(value)
            case str():
                return value
            case list():
                # gets a string representation of a list, by mashing all of its elements together, separated by a space
                result = ''
                for item in value:
                    result += self.string_rep(item) + ' '
                
                return result.strip()
            case _:
                print('string conversion failed', self.pc_stack)
                return ''

    def get_int(self, token):
        try:
            # if it's already an int
            return int(token)
        except:

            try:
                result = int(self.getvar(token))
                return result
            except ValueError:
                error("Runtime", "Conversion Error", "Can't convert",str(type(self.getvar(token))), "to int.",self)
            except:
                error("Runtime", "No such integer", f"Variable {token} not found.", self)
                return 0

    def get_numeric(self, token):
        try:
            # if it's already a float
            result = float(token)
            return int(result) if result.is_integer() else result
        except:

            try:
                result = float(self.getvar(token))
                return int(result) if result.is_integer() else result
            except ValueError:
                error("Runtime", "Conversion Error", "Can't convert",str(type(self.getvar(token))), "to numeric.",self)
            except:
                error("Runtime", "No such number", f"Variable {token} not found.", self)
                return 0
        
    # set a variable, attribute, or glob with the given new_value
    def setvar(self, token:str, new_value):
        if token != "_return":
            if token in self.variables:
                self.variables[token] = new_value
                return
            
            if token in self.parent_obj.attributes:
                self.parent_obj.set(token, new_value)
                return
            
            if token in gobj.globs:
                gobj.globs[token] = new_value
                return
        
        # otherwise, just add a new variable
        self.variables[token] = new_value

    # get the value of a variable, attribute, or glob
    def getvar(self, token:str):
        # If it's static representing a raw string, return that
        if token[0] == "'":
            return gobj.statics[int(token.strip("'"))]

        try:
            return self.variables[token]
        except:
            try:
                return self.parent_obj.attributes[token]
            except:
                try:
                    return gobj.globs[token]
                except:
                    # no such variable
                    error("Runtime", "Cannot get var.", f"Var '{token}' does not exist in locals, attributes, or globs.", self)
                    

#endregion

#region SCRIPTSYSTEM

# class to run an object's scripts
class scriptsystem:

    # common dictionary to store all loaded scripts
    scripts = {}

    splitscripts = {}

    def __init__(self, parent:gobj, script:str):
        self.parent_obj:gobj = parent           # the object we'll be affecting with this stuff
        self.currentscript = [str]              # the current script to run
        self.functions = {}                     # store the name of the function and the index it starts at
        self.hats:list[tuple[str,int]] = []     # store the starting points of scripts and their indexes
        self.receives:dict[str,list[int]] = {}  # companion to 'hats'- stores the line numbers of the 'receive' messages
        self.playheads:list[playhead] = []      # playheads are individual script execution instances

        self.setscript(script)
        self.parent_obj.set('_self', self.parent_obj.immut_id)

        try:
            self.splitscript = scriptsystem.splitscripts[script]
        except:
            self.splitscript = {}
            scriptsystem.splitscripts[script] = self.splitscript

    # set the current script to the script with the specified name
    def setscript(self, scriptname):

        # if the script is not currently loaded, load it in.
        if not scriptname in scriptsystem.scripts:
            loaded_script = self.loadscriptfile(scriptname)

            if loaded_script == None:
                sys.exit()
                
            scriptsystem.scripts[scriptname] = loaded_script
        
        self.currentscript = scriptsystem.scripts[scriptname]
        self.initscript()

    # run through the script and save the labels as variables
    def initscript(self):
        for i, line in enumerate(self.currentscript):
            splitline = line.split(' ')
            match splitline[0]:
                case 'label':
                    # set the label as an attribute of the gobj, so its value can be accessed from any script
                    self.parent_obj.set(splitline[1], i)
                case 'start':
                    self.hats.append(('start', i))
                case 'receive':
                    self.hats.append((line, i))
                    try:
                        self.receives[line[8:]].append(i)
                    except:
                        self.receives[line[8:]] = [i]
                case 'trap':
                    self.hats.append(('trap',i))

        # go through and initialize starting scripts
        for hat in self.hats:
            if hat[0] == 'start':
                # instance a playhead at the start point
                self.playheads.append(playhead(hat[1], self.parent_obj))

    # load a script file into the scripts dictionary
    def loadscriptfile(self, filename):
        
        path = filename
        mylist = []

        scope_stack:list[int] = []
        ifendstack:list = []

        currentfunc = ""
        currentfuncvars = {}
        ignoring = 0

        forever_waits = -1

        includes = [] # just for output/debugging. Keep track of includes so it doesn't display those files more than once.

        with open(path, mode='r', encoding='utf_8') as file:
            linenum = 0
            stringcount = len(gobj.statics)

            for line in file:
                # analyze each line.
                strline = line.strip(' \t\n').lower()

                # skip blank lines
                if strline == '':
                    continue

                current = strline.split()[0].lower()
                if current == '#=' or current == 'ignore':
                    ignoring += 1
                if ignoring > 0:
                    # if we're ignoring, skip until endignore is reached
                    if current == '=#' or current == 'endignore':
                        ignoring -= 1
                    continue

                # skip comments
                if strline[0] == '#':
                    continue

                # Process raw strings
                if current != 'receive':
                    # separate the raw strings and store them in variables
                    line_string_indexes = []
                    in_string = False
                    save_string = False
                    start_index = 0
                    # Search for raw strings within the line
                    for i, char in enumerate(line.strip()):
                        # only bother doing this if the raw string contains spaces, capitals, enclosures, or commas
                        if in_string and (char in " ()[]{}," or char != char.lower()):
                            save_string = True
                        if char == '"':
                            if in_string:
                                if save_string:
                                    line_string_indexes.append((start_index, i+1))
                                in_string = False
                            else:
                                start_index = i
                                in_string = True
                                save_string = False

                    # replace the raw strings with their corresponding new variable names
                    for tup in reversed(line_string_indexes):
                        var_name = f"'{stringcount}"
                        raw_str = line.strip()[tup[0]:tup[1]]
                        if raw_str[0] != '"':
                            # silly workaround so it doesn't pretend var names are strings
                            continue
                        stripped_str = raw_str.strip('"')
                        if gobj.statics.count(stripped_str.strip('"')):
                            # use an existing variable name if the raw string has been previously loaded
                            var_name = f"'{gobj.statics.index(stripped_str)}"
                        else:
                            gobj.statics.append(stripped_str.replace("\\'", '"'))
                            stringcount += 1
                        
                        # has to happen either way
                        line = var_name.join(line.rsplit(raw_str, 1)) # replace the last instance of that string

                strline = line.strip(' \t\n').lower()

                # Process array literals
                space_removals = []
                enclosure_stack = []
                for i, char in enumerate(strline):
                    if char in "({[":
                        enclosure_stack.append(char)
                    elif char in ")}]":
                        enclosure_stack.pop()
                    elif char == " ":
                        if len(enclosure_stack) > 0 and enclosure_stack[-1] == '[':
                            space_removals.append(i)
                if len(space_removals) > 0:
                    working_str = ""
                    for i, char in enumerate(strline):
                        if i not in space_removals:
                            working_str += char
                    strline = working_str


                # how many lines of assembled code added for each line of written code
                addlines = 0

                # Process expressions
                if current != 'receive':
                    parse_stack = []
                    expr_endpoints = [0,0]

                    temp_var_count = 0

                    i = 0
                    while i < len(strline):
                        char = strline[i]
                        if char == '(':
                            if len(parse_stack) == 0 or parse_stack[-1][1] == '{':
                                parse_stack.append((i, '['))
                            else:
                                parse_stack.append((0, '('))
                        elif char == ')':
                            if parse_stack[-1][1] == '(':
                                parse_stack.pop()
                            elif parse_stack[-1][1] == '[':
                                # Evaluate expression
                                expr_endpoints = [parse_stack.pop()[0], i+1]
                                replace_string = strline[expr_endpoints[0]:expr_endpoints[1]]
                                expr_string = replace_string[1:-1]
                                
                                expr_var = f"_t{temp_var_count}_"
                                temp_var_count += 1
                                mylist.append(self.fixline(f"eval {expr_var} {infix_to_postfix(expr_string)}", currentfunc, currentfuncvars))
                                addlines += 1
                                strline = strline.replace(replace_string, expr_var, 1)
                                i -= (expr_endpoints[1] - expr_endpoints[0])


                        elif char == '{':
                            parse_stack.append((i, '{'))
                        elif char == '}':
                            # Evaluate function
                            expr_endpoints = [parse_stack.pop()[0], i+1]
                            replace_string = strline[expr_endpoints[0]: expr_endpoints[1]]
                            expr_string = replace_string[1:-1]

                            expr_var = f"_t{temp_var_count}_"
                            temp_var_count += 1

                            addlines += 2
                            mylist.append(self.fixline(f"{expr_string}", currentfunc, currentfuncvars))
                            mylist.append(self.fixline(f"setvar {expr_var} _return", currentfunc, currentfuncvars))

                            strline = strline.replace(replace_string, expr_var, 1)
                            i -= (expr_endpoints[1] - expr_endpoints[0])
                        i += 1

                splitline = strline.split(' ')    


                try:
                    # include, repeat, and endrepeat are not actual commands, but something like preprocessor directives (if you're a C guy). 
                    match splitline[0]:
                        case 'include':
                            # include just copies the contents of the file specified into the script you're loading
                            includes.append(linenum)

                            # make sure to use the same rules as other file load operations
                            fname = getpathname(splitline[1], 0)
                            includes.append(fname)

                            # if the script is not currently loaded, load it in.
                            if not fname in scriptsystem.scripts:
                                scriptsystem.scripts[fname] = self.loadscriptfile(fname)
            
                            additions = self.fix_include_jump_addresses(scriptsystem.scripts[fname], linenum)

                            # update the string count
                            stringcount = len(gobj.statics)

                            linenum += len(additions)
                            includes.append(linenum-1) # subtract 1 to make something work??? (outputs for includes)
                            mylist.extend(additions)
                        case 'repeat':
                            # repeat basically creates a for loop
                    
                            # expands to a 'jump if repeat is over'
                            # then the code
                            # then an unconditional jump back to the top

                            rep_var = f"_r{len(scope_stack)}{currentfunc}_"
                            newline = f"setvar {rep_var} {splitline[1]}"
                            jumpline = f'jump x if {rep_var} 0 <='
                            scope_stack.append(linenum + addlines)

                            mylist.append(self.fixline(newline, currentfunc, currentfuncvars))
                            mylist.append(jumpline)
                            addlines += 2
                        case 'endrepeat':
        
                            if len(scope_stack) == 0:
                                error("Load", "Floating endrepeat.", "", None, self.parent_obj.immut_id, self.parent_obj.script_file, [linenum], line)
                                return
                            
                            reversejump = scope_stack.pop()
                            rep_var = f"_r{len(scope_stack)}{currentfunc}_"

                            decrementline = f'set {rep_var} --'
                           
                            jumpline = 'jump '+str(reversejump)

                            # go back and edit the initial loop line
                            splitline = mylist[reversejump + 1].split(' ')
                            splitline[1] = str(linenum+1)
                            addline = ''
                            for item in splitline:
                                addline += item + ' '
                            addline = addline.strip()

                            mylist[reversejump + 1] = addline

                            mylist.append(decrementline)
                            mylist.append(jumpline)
                            addlines += 2
                        case 'while':
                            # while loop expansion

                            #                x is a placeholder, filled in when endwhile reached
                            newline = f"jump x if {infix_to_postfix(strline[6:])} not"
                            mylist.append(self.fixline(newline, currentfunc, currentfuncvars))
                            
                            scope_stack.append(linenum + addlines - 1)
                            scope_stack.append(linenum - 1)
                            addlines += 1
                        case 'loop':
                            # start the infinite loop check
                            forever_waits = 0

                            scope_stack.append(linenum-1)
                        case 'endloop':
                            reversejump = scope_stack.pop()

                            jumpline = 'jump '+ str(reversejump)
                            mylist.append(jumpline)
                            addlines += 1

                            if forever_waits == 0:
                                error("Load", "Infinite loop.", "", None, self.parent_obj.immut_id, self.parent_obj.script_file, [linenum], line)
                                return
                            else:
                                forever_waits = -1
                        case 'endwhile':
                            if len(scope_stack) == 0:
                                error("Load", "Floating endwhile.", "", None, self.parent_obj.immut_id, self.parent_obj.script_file, [linenum], line)
                                return
                            
                            reversejump = scope_stack.pop()

                            jumpline = 'jump '+ str(reversejump)

                            reversejump = scope_stack.pop()

                            # go back and edit the initial loop line
                            splitline = mylist[reversejump + 1].split(' ')
                            splitline[1] = str(linenum)
                            addline = ''
                            for item in splitline:
                                addline += item + ' '
                            addline = addline.strip()

                            mylist[reversejump + 1] = addline

                            mylist.append(jumpline)

                            addlines += 1
                        case 'if':
                            scope_stack.append(linenum + addlines)
                            ifendstack.append([])

                            newline = f"jump x if {infix_to_postfix(strline[3:])} not"
                            mylist.append(self.fixline(newline, currentfunc, currentfuncvars))
                            addlines += 1 
                        case 'elif':

                            mylist.append('jump x')
                            for i in range(1, addlines+1):
                                mylist[-i], mylist[-(i+1)] = mylist[-(i+1)], mylist[-i]
                            ifendstack[-1].append(linenum)

                            # next if condition
                            newline = f"jump x if {infix_to_postfix(strline[5:])} not"
                            mylist.append(self.fixline(newline, currentfunc, currentfuncvars))

                            # edit the previous if line
                            splitline = mylist[scope_stack[-1]].split(' ')
                            splitline[1] = str(linenum)

                            addline = ''
                            for item in splitline:
                                addline += item + ' '
                            mylist[scope_stack[-1]] = addline.strip()

                            # update the if stack
                            scope_stack[-1] = linenum + 1 + addlines

                            addlines += 2
                        case 'else':

                            mylist.append('jump x')
                            ifendstack[-1].append(linenum)

                            # edit the previous if line
                            splitline = mylist[scope_stack[-1]].split(' ')
                            splitline[1] = str(linenum)

                            addline = ''
                            for item in splitline:
                                addline += item + ' '
                            mylist[scope_stack[-1]] = addline.strip()

                            addlines += 1

                            scope_stack[-1] = -1
                        case 'endif':
                            if len(scope_stack) == 0:
                                error("Load", "Floating endif.", "", None, self.parent_obj.immut_id, self.parent_obj.script_file, [linenum], line)
                                return

                            num = scope_stack.pop()

                            if num != -1:
                                # edit the previous if line
                                splitline = mylist[num].split(' ')
                                splitline[1] = str(linenum-1)

                                addline = ''
                                for item in splitline:
                                    addline += item + ' '
                                mylist[num] = addline.strip()
                            
                            for index in ifendstack[-1]:
                                # edit the previous unconditional jump lines
                                splitline = mylist[index].split(' ')
                                splitline[1] = str(linenum-1)

                                addline = ''
                                for item in splitline:
                                    addline += item + ' '
                                mylist[index] = addline.strip()
                            
                            ifendstack.pop()
                        case 'def':
                            # helps with control flow expansions, so they don't break inside of functions
                            currentfunc = splitline[1]

                            # add the function parameters
                            addlines += len(splitline) - 1
                            for i in range(addlines - 1):
                                splitparam = splitline[i+2].split('=')
                                addline = 'setvar ' + currentfunc+'_'+splitparam[0]+' '
                                if len(splitparam) == 2:
                                    addline += splitparam[1]
                                    currentfuncvars[splitparam[0]] = splitparam[1]
                                else:
                                    addline += '0'
                                    currentfuncvars[splitparam[0]] = 0
                                mylist.append(addline)
                            
                            mylist.append('def '+currentfunc)
                        case _:

                            # these help with the repeat, while, and if expansion
                            # I was having trouble with repeats inside of functions, and this fixed the issues
                            if splitline[0] == 'return':
                                currentfunc = ""
                                currentfuncvars.clear()
                            
                            if forever_waits > -1 and splitline[0] == "wait":
                                forever_waits += 1

                            # the rest of the lines are actual code so we just add them to the list as normal
                            if len(strline) > 0:
                                addlines += 1
                                mylist.append(self.fixline(strline, currentfunc, currentfuncvars))
                                
                    linenum += addlines
                except Exception as e:
                    error("Load", "Other load error.", f"{e}", None, self.parent_obj.immut_id, self.parent_obj.script_file, [linenum], line)
                    traceback.print_exc()
                    return

        # for debugging, print the assembled code to a file
        with open("Output.txt", mode='a', encoding='utf_8') as outfile:
            outfile.write('\n'+filename+'\n')

            in_include = False
            include_index = 0
            for i, line in enumerate(mylist):
                if include_index >= len(includes):
                    outfile.write('\t'+str(i)+' '+ line+'\n')
                    continue
                if not in_include:

                    if i == includes[include_index]:
                        in_include = True
                        outfile.write(f"\tIncluding {includes[include_index+1]}, [{includes[include_index]}, {includes[include_index+2]}]\n")

                        include_index += 2
                    else:
                        outfile.write('\t'+str(i)+' '+ line+'\n')
                elif i == includes[include_index]:

                    include_index += 1
                    in_include = False

        return mylist

    def fixline(self, strline, currentfunc, currentfuncvars):
        splitline = strline.split(' ')
        if currentfunc == "":
            return strline
        else:
            # fix function parameter names
            for i, item in enumerate(splitline):
                splitbyequal = item.split('=')
                if len(splitbyequal) == 2 and not (splitbyequal[1] == ''):
                    # fix the var name in function call
                    if splitbyequal[1] in currentfuncvars:
                        splitline[i] = splitbyequal[0] + '=' + currentfunc + '_' + splitbyequal[1]

                if item in currentfuncvars:
                    
                    # replace parameter names in the function
                    splitline[i] = currentfunc + '_' + item
                if item[0] == '[':
                    # Fix parameter names in array literals
                    splititem = item[1:-1].split(',')
                    newlist='['
                    for j, var in enumerate(splititem):
                        if var in currentfuncvars:
                            splititem[j] = currentfunc + '_' + var
                        newlist += splititem[j]+','
                    newlist = f"{newlist[:-1]}]"
                    splitline[i] = newlist
                    
            addline = ''
            for item in splitline:
                addline += item + ' '
            addline = addline.strip()
            return addline

    def fix_include_jump_addresses(self, script_to_include:list[str], addr_offset:int):
        result_script = []
        for line in script_to_include:
            splitline = line.split()
            if splitline[0] == 'jump':
                # if splitline[1] is an int, add it to the addr_offset. If it's a string, leave it alone.
                try:
                    addr = int(splitline[1])
                    splitline[1] = str(addr+addr_offset)
                    result_script.append(' '.join(splitline))
                except:
                    result_script.append(line)
                pass
            else:
                result_script.append(line)
        return result_script

    # respond to messages. Instances a playhead if there is a matching message hat
    def respond(self, message:str, data):
        lmsg = message.lower()
        if lmsg in self.receives:
            for line_no in self.receives[lmsg]:
                new_ph = playhead(line_no, self.parent_obj)
                new_ph.variables['_message_data'] = data
                self.playheads.append(new_ph)

    def script_tick(self):
        
        self.parent_obj.set('_global_x', self.parent_obj.global_pos[0])
        self.parent_obj.set('_global_y', self.parent_obj.global_pos[1])

        ph_deletions = []
        for ph in self.playheads:

            if ph.wait_timer > 0:
                # if the script is waiting, we shouldn't do anything else but tick the timer
                ph.wait_timer -= 1

            # process lines until a wait is reached or the script ends
            while ph.wait_timer == 0 and ph.is_running:

                line_no = ph.pc_stack[ph.stacklen]

                try:
                    self.processline(self.currentscript[line_no], ph, line_no)
                    if ph.has_error:
                        ph.is_running = False
                except Exception as e:
                    # this is extremely rudimentary but at least it tells you what line caused the error
                    # although usually the error is caused when you try to refer to a nonexistent variable 
                    #   in which case the error was probably caused by a prior line
                    error("Runtime", "Python exception", f"Exception: {e}", ph)
                    if ph.parent_obj.attributes["_hide_errors"] != 1:
                        traceback.print_exc()
                    ph.is_running = False

                # go to the next line
                ph.pc_stack[ph.stacklen] += 1
            if not ph.is_running:
                ph_deletions.append(ph)
        
        # remove finished playheads
        for ph in ph_deletions:
            self.playheads.remove(ph)
    
    def processline(self, line:str, ph:playhead, line_no:int):
        # NOTE: the scripting system is not case-sensitive, so for example 'rEtUrN' is the same as 'return'

        try:
            splitline = self.splitscript[line_no]
        except:
            # split the line based on spaces
            splitline = line.lower().split(' ')
            self.splitscript[line_no] = splitline
        
        # if the line is 'def', skip_to will be set and the script will skip all the lines until a 'return' command is reached.
        if ph.skip_to:
            match splitline[0]:
                case ph.skip_to:
                    # go back to normal
                    ph.skip_to = None
                case _:
                    pass
            return

        match splitline[0]:
            case 'return':
                # gets rid of the last element in indexes, causing the script to return to where it was previously
                ph.pc_stack.pop()
                ph.stacklen -= 1
            case 'end':
                # end the script
                ph.is_running = False
            case 'setvar':
                # set a local variable to a value
                result = ph.get_any(splitline[2])
                ph.variables[splitline[1]] = result
            case 'set':
                # set a variable, attribute, or glob to a value

                # you add these modifiers to do increments and such
                try:
                    vartoken = splitline[1]
                    match splitline[2]:
                        case '++':
                            ph.setvar(vartoken, ph.getvar(vartoken) + 1)
                        case '--':
                            ph.setvar(vartoken, ph.getvar(vartoken) - 1)
                        case '+=':
                            ph.setvar(vartoken, ph.getvar(vartoken) + ph.get_numeric(splitline[3]))
                        case '-=':
                            ph.setvar(vartoken, ph.getvar(vartoken) - ph.get_numeric(splitline[3]))
                        case '*=':
                            ph.setvar(vartoken, ph.getvar(vartoken) * ph.get_numeric(splitline[3]))
                        case '/=':
                            ph.setvar(vartoken, ph.getvar(vartoken) / ph.get_numeric(splitline[3]))
                        case '//=':
                            ph.setvar(vartoken, ph.getvar(vartoken) // ph.get_numeric(splitline[3]))
                        case _:
                            result = ph.get_any(splitline[2])
                            #ph.variables[splitline[1]] = result
                            ph.setvar(vartoken, result)
                                
                except:
                    error("Runtime", "Invalid operation.", "Cannot perform increments on non-numeric types.",ph)
            case 'wait':
                # wait a specified number of frames
                ph.wait_timer = ph.get_int(splitline[1])
            case 'label':
                pass
            case 'setattribute':
                if len(splitline) == 4:
                    # specify an object to set the attribute of
                    add = 1
                    obj = ph.get_gobj(splitline[1])
                else:
                    add = 0
                    obj = self.parent_obj
                
                if obj == 0:
                    return

                # set an attribute in the parent object
                result = ph.get_any(splitline[2+add])
                obj.set(splitline[1+add], result)                     
            case 'getattribute':
                # for example: getattribute obj health h -> set variable 'h' to obj's attribute 'health'
                obj = ph.get_gobj(splitline[1])
                if len(splitline) == 4:
                    resultvar = splitline[3]
                else:
                    resultvar = "_return"
            
                if obj == 0:
                    error("Runtime", "ID not found.", f"No such object referred to by {splitline[1]}",ph)
                    ph.setvar(resultvar, 0)
                    return
                
                value = obj.get(splitline[2])

                if value == None:
                    error("Runtime", "Attribute not found.", f"No such attribute in {obj.immut_id} ({obj.script_file}): {splitline[2]}",ph)
                    ph.setvar(resultvar, 0)
                else:
                    ph.setvar(resultvar, value)
            case 'setglob':
                # same as setattribute but for global vars
                # set the value of a global variable in gobj.globs

                result = ph.get_any(splitline[2])
                gobj.globs[splitline[1]] = result      
            case 'getglob':
                # same as getattribute but for global vars
                if len(splitline) == 3:
                    resultvar = splitline[2]
                else:
                    resultvar = "_return"

                value = gobj.globs.get(splitline[1])
                if value == None:
                    error("Runtime", "Glob not found.", f"No such global variable: {splitline[2]}",ph)
                    ph.setvar(resultvar, 0)
                else:
                    ph.setvar(resultvar, value)
            case 'def':
                # define a function which can be called later
                currentindex = ph.stacklen
                self.functions[splitline[1]] = ph.pc_stack[currentindex]
                ph.skip_to = 'return'
            case 'log':
                # print out something to the console
                # to print variable values, just use their names
                for i in range(1, len(splitline)):
                    value = ph.get_string(splitline[i])
                    if value == None:
                        print(splitline[i], end=" ")
                    else:
                        print(value, end=" ")
                print()
            case 'broadcast':
                # send a message to all objects
                value = ph.get_string(splitline[1])

                if len(splitline) == 3:
                    # add data to the message. Otherwise, data will be 0.
                    data = ph.get_any(splitline[2])
                else:
                    data = 0
                
                gobj.messages.append(('"' + value + '"', data))
            case 'unicast':
                # send a message to one specific object
                obj = ph.get_gobj(splitline[1])
                value = ph.get_string(splitline[2])

                if len(splitline) == 4:
                    # add data to the message. Otherwise, data will be 0.
                    data = ph.get_any(splitline[3])
                else:
                    data = 0

                obj.scriptsys.respond('"' + value + '"', data)
            case 'jump':
                # Jumps to a specified line number or labeled position.
                # jump 5 if var 3 <, for example, jumps to line position 5 if var < 3
                # Jump conditions are in reverse Polish notation (i.e. postfix)

                if len(splitline) == 2:
                    # unconditional jump, no expression to evaluate
                    currentindex = ph.stacklen
                    jumpto = ph.get_int(splitline[1])
                    ph.pc_stack[currentindex] = jumpto
                else:
                    # conditional jump
                    condition = False

                    result = ph.postfix_eval(splitline[3:])
                    condition = not ph.postfix_check_false(result)
                     
                    if condition:
                        # perform the jump
                        currentindex = ph.stacklen
                        jumpto = ph.get_int(splitline[1])
                        ph.pc_stack[currentindex] = jumpto
            case 'eval':
                # evaluate a postfix expression and store the result in a variable
                expression = splitline[2:len(splitline)]
                result = ph.postfix_eval(expression)
                ph.setvar(splitline[1], result)
            case 'move':
                # move in a direction and speed
                dir = ph.get_numeric(splitline[1])
                mag = ph.get_numeric(splitline[2])

                self.parent_obj.move(self.parent_obj.calculatemotionvector(dir, mag))
            case 'setposition':
                # set position to specified coordinates
                current_x = ph.get_numeric('_x')
                current_y = ph.get_numeric('_y')
                new_x = ph.get_numeric(splitline[1])
                new_y = ph.get_numeric(splitline[2])
                self.parent_obj.set('_x', new_x)
                self.parent_obj.set('_y', new_y)
            
                differential = [new_x-current_x, new_y-current_y]
                self.parent_obj.global_pos[0] += differential[0]
                self.parent_obj.global_pos[1] += differential[1]
                
                self.parent_obj.move([0,0])
            case 'translate':
                delta_x = ph.get_numeric(splitline[1])
                delta_y = ph.get_numeric(splitline[2])
                self.parent_obj.move([delta_x, delta_y])
            case 'random':
                # example: random xpos 200 500
                # -sets xpos to a random number between 200 and 500

                if splitline[1] == 'seed':
                    # Seed the rng with the given number
                    srand = ph.get_int(splitline[2])
                    random.seed(srand)
                else:
                    n1 = ph.get_int(splitline[1])
                    n2 = ph.get_int(splitline[2])

                    if len(splitline) == 4:
                        resultvar = splitline[3]
                    else:
                        resultvar = "_return"

                    ph.setvar(resultvar, random.randint(n1, n2))
            case 'angle':
                # find the angle between 2 points
                # angle x1 y1 x2 y2 var
                # -sets var to the vector between point 1 and point 2
                origin:tuple[int,int] = (ph.get_numeric(splitline[1]), ph.get_numeric(splitline[2]))
                target:tuple[int,int] = (ph.get_numeric(splitline[3]), ph.get_numeric(splitline[4]))

                # format it so the origin would be (0,0)
                adjusted = (target[0]-origin[0], target[1]-origin[1])
                if adjusted[0] == 0:
                    if adjusted[1] > 0:
                        result = 90
                    else:
                        result = 270
                else:
                    rads = math.atan(adjusted[1]/adjusted[0])
                    
                    result = math.degrees(rads)
                    
                    if adjusted[0] < 0:
                        result += 180
                
                if len(splitline) == 6:
                    resultvar = splitline[5]
                else:
                    resultvar = "_return"
                ph.setvar(resultvar, result)
            case 'distance':
                origin:tuple[int,int] = (ph.get_numeric(splitline[1]), ph.get_numeric(splitline[2]))
                target:tuple[int,int] = (ph.get_numeric(splitline[3]), ph.get_numeric(splitline[4]))

                # apply distance formula to find distance between 2 points
                x = target[0] - origin[0]
                x = x ** 2
                y = target[1] - origin[1]
                y = y ** 2
                
                if len(splitline) == 6:
                    resultvar = splitline[5]
                else:
                    resultvar = "_return"
                ph.setvar(resultvar, math.sqrt(x + y))
            case 'delete':
                # delete the object running the script, as long as it's not the scene root
                if not self.parent_obj.is_root:
                    self.parent_obj.markdead()

                    # stop all scripts in the object
                    for item in self.playheads:
                        item.is_running = False
                else:
                    error("Runtime", "Invalid delete.", "Cannot delete the root object.",ph)
            case 'string':
                match splitline[1]:
                    case 'join':
                        # join two or more strings and store them in a variable
                        # ex: string join newstr "Hello " "world"
                        #--> newstr now equals "Hello world"
                        newstr = ""
                        for item in splitline[3:]:
                            newstr += ph.get_string(item)
                        
                        ph.setvar(splitline[2], newstr)
                    case 'split':
                        # split a string based on a delimiter
                        # ex: string split "hello world" " " newstr -> newstr is now ["hello", "world"]
                        string = ph.get_string(splitline[2])
                        
                        delim = ph.get_string(splitline[3])
                        strspl = string.split(delim)
                        
                        if len(splitline) == 5:
                            resultvar = splitline[4]
                        else:
                            resultvar = "_return"

                        ph.setvar(resultvar, strspl)
            case 'merge':
                # merge two or more lists into one
                # they will end up being stored in the variable holding the first one
                result = ph.get_list(splitline[1])
                for item in splitline[2:]:
                    result.extend(ph.get_list(item))
                ph.setvar(splitline[1], result)
            case 'append':
                # add something or things to the end of a list
                # append mylist 5 6 7 10
                if ph.getvar(splitline[1]) == None:
                    result = []
                else:
                    result = ph.get_list(splitline[1])
                for item in splitline[2:]:
                    result.append(ph.get_any(item))
                ph.setvar(splitline[1], result)
            case 'remove':
                # remove something from a list at a specified index
                # option to store the removed item in a variable
                # ex: remove mylist 5 var --> pop index 5 and store it in var
                result = ph.get_list(splitline[1])
                index = ph.get_int(splitline[2])

                if index >= 0 and index < len(result):
                    # we only want to do something if it's a valid index
                    element = result.pop(index)
                    if len(splitline) == 4:
                        # store popped element
                        resultvar = splitline[3]
                    else:
                        resultvar = "_return"
                    ph.setvar(resultvar, element)

                    # store the new array
                    ph.setvar(splitline[1], result)
                else:
                    error("Runtime", "Collection error.", f"Cannot remove index {index} from list {result} of length {len(result)}.",ph)
            case 'insert':
                # Insert an item into a list
                result = ph.get_list(splitline[1])
                index = ph.get_int(splitline[2])
                item = ph.get_any(splitline[3])

                if index >= 0 and index < len(result):
                    result.insert(index, item)
                    ph.setvar(splitline[1], result)
                else:
                    error("Runtime", "Collection error.", f"Cannot insert before index {index} with list {result} of length {len(result)}.",ph)
            case 'count':
                # count array_name value storage_var
                # Determine how many of an item is in a list
                array:list = ph.get_list(splitline[1])
                value = ph.get_any(splitline[2])

                result = array.count(value)
                if len(splitline) == 4:
                    resultvar = splitline[3]
                else:
                    resultvar = "_return"

                ph.setvar(resultvar,result)
            case 'copy':
                # copies a list
                list1:list = ph.get_list(splitline[1])

                if len(splitline) == 3:
                    resultvar = splitline[2]
                else:
                    resultvar = "_return"
                ph.setvar(resultvar, list1.copy())
            case 'getindex':
                # get the value at the specified index in a list
                mylist = ph.get_list(splitline[1])
                index = ph.get_int(splitline[2])

                if index >= 0 and index < len(mylist):
                    ph.setvar(splitline[3], mylist[index])
                else:
                    # no index, returns 0
                    error("Runtime", "Collection error.", f"Cannot get index {index} from list {mylist} of length {len(mylist)}.",ph)
                    
                    ph.setvar(splitline[3], 0)
            case 'setindex':
                # set the value at the specified list index
                mylist = ph.get_list(splitline[1])
                index = ph.get_int(splitline[2])

                if index >= 0 and index < len(mylist):
                    # you add these modifiers to do increments and such
                    try:
                        match splitline[3]:
                            case '++':
                                mylist[index] += 1
                            case '--':
                                mylist[index] -= 1
                            case '+=':
                                mylist[index] += ph.get_numeric(splitline[4])
                            case '-=':
                                mylist[index] -= ph.get_numeric(splitline[4])
                            case '*=':
                                mylist[index] *= ph.get_numeric(splitline[4])
                            case '/=':
                                mylist[index] /= ph.get_numeric(splitline[4])
                            case '//=':
                                mylist[index] //= ph.get_numeric(splitline[4])
                            case _:
                                mylist[index] = ph.get_any(splitline[3])
                                    
                    except:
                        error("Runtime", "Invalid operation.", "Cannot perform increments on non-numeric types.",ph)
                else:
                    # out of bounds, does nothing
                    error("Runtime", "Collection error.", f"Cannot get index {index} from list {mylist} of length {len(mylist)}.",ph)
            case 'instance':
                # instance a new gameobject with specified parent and attributes, and (optionally) store its ID in a variable
                # instance type(script) parent var attributes
                obj_parent:gobj = ph.get_gobj(splitline[2])
                obj_type = getpathname(ph.get_string(splitline[1]), 0)

                if len(splitline) == 3 or (len(splitline) >= 3 and '=' in splitline[3]):
                    resultvar = "_return"
                    startpoint = 3
                else:
                    resultvar = splitline[3]
                    startpoint = 4

                obj_attributes = {}

                
                transfer_att = '_transform_children'
                obj_attributes[transfer_att] = ph.get_int(transfer_att)

                for item in splitline[startpoint:]:
                    splitparam = item.split('=')
                    obj_attributes[splitparam[0]] = ph.get_any(splitparam[1])

                new_obj:gobj = gobj(obj_type, obj_attributes, obj_parent.immut_id)
                obj_parent.children.append(new_obj)

                # you can use '_' for the variable name if you don't want to save it
                if resultvar != '_':
                    ph.setvar(resultvar, new_obj.immut_id)
            case 'save':
                # save a file or image
                file_path = Path(getpathname(ph.get_string(splitline[2]), 3))
                file_path.parent.mkdir(parents=True,exist_ok=True)
                match splitline[1]:
                    # save a text file from a list
                    # save file "a.txt" contents

                    case 'file':
                        contents = ph.get_list(splitline[3])
                        filename = getpathname(ph.get_string(splitline[2]), 3)
                        with open(filename, mode='w', encoding='utf_8') as file:
                            for item in contents:
                                file.write(ph.string_rep(item)+'\n')
                    # save an image from the object's canvas
                    case 'canvas':
                        contents = ph.parent_obj.canvas
                        if contents == None:
                            error("Runtime", "Cannot save canvas.", "Object has no canvas.",ph)
                            return
                        
                        pygame.image.save(contents, getpathname(ph.get_string(splitline[2]), 1))
            case 'load':
                # load a sprite, sound, font, or text file
                match splitline[1]:
                    case 'sprite':
                        # ex: load sprite costumename source 0 0 16 32
                        costumename = ph.get_string(splitline[2])
                        
                        # get coordinates and dimensions of sprite to load
                        dim = []
                        if len(splitline) == 8:
                            for i in range(4):
                                dim.append(ph.get_int(splitline[i + 4]))
                        else:
                            dim.append(-1)
                        
                        if splitline[3] == '_self':
                            if ph.parent_obj.canvas == None:
                                error("Runtime", "Cannot load canvas.", "Object has no canvas.",ph)
                                return
                            # set the source image to be the canvas
                            atlas = ph.parent_obj.canvas.copy()
                        else:
                            # set the source image to be from a file
                            sourcefilename = getpathname(ph.get_string(splitline[3]), 1)
                            atlas = pygame.image.load(sourcefilename).convert_alpha()
                        
                        if dim[0] == -1:
                            gobj.sprites[costumename] = atlas
                        else:
                            subrect = pygame.Rect(dim[0], dim[1], dim[2], dim[3])

                            img = atlas.subsurface(subrect)
                            gobj.sprites[costumename] = img
                    case 'sound':
                        # ex: load sound "shoot" "shoot.ogg" 100
                        soundname = ph.get_string(splitline[2])
                        sourcefilename = getpathname(ph.get_string(splitline[3]), 2)
                        soundobj = pygame.mixer.Sound(sourcefilename)
                        if len(splitline) == 5:
                            millis = ph.get_int(splitline[4])
                        else:
                            #millis = soundobj.get_length() * 1000
                            millis = 0
                        
                        soundobj.set_volume(gobj.globs['_sfx_vol'])
                        gobj.sounds[soundname] = (soundobj, millis)
                    case 'file':
                        # ex: load file "scores.txt" scores_var
                        # stores a list of strings in scores_var, with one element being each line of the file
                        sourcefilename = getpathname(ph.get_string(splitline[2]), 3)
                        result = []
                        try:
                            with open(sourcefilename, mode='r', encoding='utf_8') as file:
                                for line in file:
                                    result.append(line.strip(' \t\n'))
                        except:
                            # Error message if file does not exist.
                            pass#error("Runtime", "Cannot open file.", f"File {sourcefilename} does not exist.",ph)
                        
                        if len(splitline) == 4:
                            resultvar = splitline[3]
                        else:
                            resultvar = "_return"
                        ph.setvar(resultvar, result)
                    case 'font':
                        # load font "fun font" "myfont.ttf"
                        sourcefilename = getpathname(ph.get_string(splitline[3]), 4)
                        fontname = ph.get_string(splitline[2])
                        try:
                            new_font = pygame.font.Font(sourcefilename,0)
                            gobj.fonts[fontname] = sourcefilename
                        except:
                            error("Runtime", "Cannot load font.", f"{sourcefilename} is not a valid font file.",ph)
            case 'unload':
                # unload a sprite, sound, or font 
                match splitline[1]:
                    case 'sprite':
                        # remove a sprite from the global sprites list
                        costumename = ph.get_string(splitline[2])
                        if costumename in gobj.sprites:
                            gobj.sprites.pop(costumename)
                    case 'sound':
                        # ex: load sound "shoot" "shoot.ogg" 100
                        soundname = ph.get_string(splitline[2])
                        if soundname in gobj.sounds:
                            gobj.sounds.pop(soundname)
                    case 'font':
                        fontname = ph.get_string(splitline[2])
                        if fontname in gobj.fonts:
                            gobj.fonts.pop(fontname)
            case 'setsprite':
                if self.parent_obj.render_surface == None:
                    width = ph.get_int('_width')
                    height = ph.get_int('_height')
                    self.parent_obj.render_surface = pygame.Surface((width,height)).convert_alpha()
                    self.parent_obj.render_rect = pygame.Rect((0,0), (width,height))
                    self.parent_obj.render_rect.center = self.parent_obj.global_pos

                match splitline[1]:
                    case "rect":
                        self.parent_obj.set('_sprite', 0)
                        size = (ph.get_int('_width'), ph.get_int('_height'))
                        stroke_width = ph.get_int('_draw_stroke')
                        color = self.parent_obj.get_color()
                        self.parent_obj.render_surface.fill(color=(0,0,0,0)) # clear the surface
                        draw_rect = pygame.Rect((0,0), size)
                        pygame.draw.rect(self.parent_obj.render_surface, color, draw_rect, stroke_width)
                    case "ellipse":
                        self.parent_obj.set('_sprite', 0)
                        size = (ph.get_int('_width'), ph.get_int('_height'))
                        stroke_width = ph.get_int('_draw_stroke')
                        color = self.parent_obj.get_color()
                        self.parent_obj.render_surface.fill(color=(0,0,0,0)) # clear the surface
                        draw_rect = pygame.Rect((0,0), size)
                        pygame.draw.ellipse(self.parent_obj.render_surface, color, draw_rect, stroke_width)
                    case _:
                        spritename = ph.get_string(splitline[1])
                        self.parent_obj.set('_sprite', spritename)
                        fliph = ph.get_int('_fliph')
                        flipv = ph.get_int('_flipv')
                        rot = ph.get_numeric('_rotation')
                        self.parent_obj.setsprite(spritename, fliph, flipv, rot, self.parent_obj.new_color_shift)
            case 'updatesprite':
                spritename = self.parent_obj.get('_sprite')
                fliph = ph.get_int('_fliph')
                flipv = ph.get_int('_flipv')
                rot = ph.get_int('_rotation')
                width = ph.get_int('_width')
                height = ph.get_int('_height')

                self.parent_obj.setsprite(spritename, fliph, flipv, rot, self.parent_obj.new_color_shift,width, height)
            case 'music':

                match splitline[1]:
                    case 'pause':
                        if not gobj.music_paused:
                            pygame.mixer_music.pause()
                            gobj.music_paused = True
                    case 'resume':
                        if gobj.music_paused:
                            pygame.mixer_music.unpause()
                            gobj.music_paused = False
                    case 'position':
                        current_pos = pygame.mixer_music.get_pos()
                        if len(splitline) > 2:
                            ph.setvar(splitline[2], current_pos - gobj.music_seek_offset)
                        else:
                            ph.setvar('_return', current_pos - gobj.music_seek_offset)
                    case 'seek':
                        old_position = pygame.mixer_music.get_pos() - gobj.music_seek_offset
                        new_position = ph.get_numeric(splitline[2])
                        gobj.music_seek_offset += (old_position - new_position)
                        print("offset:",gobj.music_seek_offset)
                        print("newpos", new_position)
                        pygame.mixer_music.set_pos(new_position / 1000)
                    case _:
                        # change the music track currently playing, with a specified fade-out time
                        track = ph.get_string(splitline[1])

                        fade = 0
                        if len(splitline) == 3:
                            fade = ph.get_int(splitline[2])

                        switchmusic(track, fade)
                        gobj.music_seek_offset = 0
                    
            case 'sound':
                match splitline[1]:
                    case 'pause':
                        pygame.mixer.pause()
                    case 'resume':
                        pygame.mixer.unpause()
                    case _:
                        # play a sound effect
                        self.parent_obj.playsound(ph.get_string(splitline[1]))
            case 'setcollider':
                # set the size of the collision box
                if self.parent_obj.collision_rect == None:
                    collider = pygame.Rect(0,0,0,0)
                    self.parent_obj.collision_rect = collider

                    # add the collider

                    # set the index id of the object. This is used to get the collided object when testing for collisions
                    self.parent_obj.c_index = gobj.collider_count
                    gobj.collider_count += 1
                    gobj.colliders.append(collider)
                    gobj.object_map.append(self.parent_obj.immut_id)

                else:
                    collider = self.parent_obj.collision_rect
                w = ph.get_int(splitline[1])
                h = ph.get_int(splitline[2])
                collider.w = w
                collider.h = h
                collider.center = self.parent_obj.global_pos
            case 'collide':
                self.cmd_collide(ph, splitline)
            case 'setmask':
                if ph.parent_obj.render_surface:
                    ph.parent_obj.collision_mask = pygame.mask.from_surface(ph.parent_obj.render_surface)
            case 'maskcollide':
                self.cmd_maskcollide(ph, splitline)    
            case 'stopscripts':
                # causes all other scripts in the gobj to end
                for item in self.playheads:
                    if item != ph:
                        item.is_running = False
            case 'stopall':
                # end the program, close window, etc.
                gobj._FINISHED = True
            case 'draw':
                self.cmd_draw(ph, splitline)
            case 'stamp':
                draw_obj:gobj = ph.get_gobj(splitline[1])

                if len(splitline) > 2:
                    obj = ph.get_gobj(splitline[2])
                else:
                    obj = ph.parent_obj

                if draw_obj == 0 or obj == 0:
                    return

                # ex: stamp _self -> stamps _self gobj onto canvas. Just like Scratch's 'stamp' function
                if draw_obj.canvas == None or list(draw_obj.canvas.get_size()) != gobj.resolution:
                    # create a canvas that spans the screen
                    draw_obj.canvas = pygame.Surface(gobj.resolution).convert_alpha()
                    draw_obj.canvas.fill(color=(0,0,0,0))
                    draw_obj.canvas_rect = pygame.Rect((0,0), gobj.resolution)
                
                # only stamp it if the object actually has something to stamp
                if obj.render_surface and obj.render_rect:
                    if obj.render_rect.colliderect((0,0), gobj.globs["_screen_resolution"]):
                        draw_obj.is_canvas_dirty = True
                        draw_obj.canvas.blit(obj.render_surface, obj.render_rect)
            case 'colorshift':
                shift_r = ph.get_int(splitline[1])
                shift_g = ph.get_int(splitline[2])
                shift_b = ph.get_int(splitline[3])

                if len(splitline) == 5:
                    shift_a = ph.get_int(splitline[4])
                else:
                    shift_a = 0
                
                self.parent_obj.new_color_shift=[shift_r,shift_g,shift_b,shift_a]           
            case 'getkey':
                # gets the input state of the specified key
                input = ph.get_string(splitline[1])
                try:
                    mapped = keymap[input]
                except:
                    error("Runtime", "Invalid input.", f"'{input}' is not a valid input key.",ph)
                    return
                
                if len(splitline) == 3:
                    resultvar = splitline[2]
                else:
                    resultvar = "_return"

                try:
                    ph.setvar(resultvar, keystates[mapped])
                except:
                    addkey(input)
                    ph.setvar(resultvar, 0)
            case 'fork':
                # spawn a playhead (start a new script at a position)
                startpoint = ph.get_int(splitline[1])
                self.playheads.append(playhead(startpoint, self.parent_obj))
            case 'callstack':
                # Puts the current call stack (a list of containing the current line and the lines of any functions currently executing) in a variable, or _return if none given.
                if len(splitline) == 2:
                    resultvar = splitline[1]
                else:
                    resultvar = "_return"
                
                ph.setvar(resultvar, ph.pc_stack.copy())
            case 'adopt' | 'kidnap':
                # Takes a child object from another object and adds it to its own child list. This cannot be done with the root object.
                obj:gobj = ph.get_gobj(splitline[1])
                if obj == 0:
                    error("Runtime", "Invalid Object", f"The object '{splitline[1]}' does not exist.", playhead=ph)
                    return
                if obj.immut_id == 0:
                    error("Runtime", "Invalid Adoption", f"The command 'adopt' is not valid for the root object.", playhead=ph)
                    return
                if not self.parent_obj.check_valid_adoption(obj.immut_id):
                    # Check to see if the object being adopted is either itself or one of its ancestors (which would cause a problem)
                    error("Runtime", "Invalid Adoption", f"Object '{self.parent_obj.immut_id}' cannot 'adopt' '{obj.immut_id}' (itself or its ancestor).", playhead=ph)
                    return
                # After we made it through the checks, we assume it's a valid adoption attempt
                prev_parent:gobj = gobj.objects[obj.parent_obj]
                prev_parent.children.remove(obj)

                self.parent_obj.children.append(obj)
                obj.parent_obj = self.parent_obj.immut_id
            case 'changelayer':
                # Re-order this object's children
                # Ex: changelayer obj1 front (move obj to the front layer, which renders on top)
                obj:gobj = ph.get_gobj(splitline[1])
                if obj in self.parent_obj.children:
                    parameter = splitline[2]
                    if parameter == 'front':
                        self.parent_obj.children.remove(obj)
                        self.parent_obj.children.append(obj)
                    elif parameter == 'back':
                        self.parent_obj.children.remove(obj)
                        self.parent_obj.children.insert(0, obj)
                    else:
                        parameter = ph.get_int(splitline[2])
                        current_index = self.parent_obj.children.index(obj)
                        new_index = (current_index + parameter) % len(self.parent_obj.children)

                        self.parent_obj.children.remove(obj)
                        self.parent_obj.children.insert(new_index, obj)

                else:
                    error("Runtime", "Cannot Change Layer", f"Object with ID '{obj.immut_id}' is not a child of '{self.parent_obj.immut_id}'", playhead=ph)
            case 'configure':
                # special command to edit things like window size or resolution, framerate, caption...
                match splitline[1]:
                    case 'fullscreen':
                        # configure fullscreen 1
                        sysvars['is_fullscreen'] = ph.get_int(splitline[2]) == 1
                        gobj.apply_fullscreen_change_flag = True
                    case 'screen_resolution':
                        new_value = [abs(ph.get_int(splitline[2])), abs(ph.get_int(splitline[3]))]
                        sysvars['screen_resolution'] = new_value
                        gobj.globs['_screen_resolution'] = new_value
                        gobj.resolution = new_value
                    case 'window_size':
                        new_value = [abs(ph.get_int(splitline[2])), abs(ph.get_int(splitline[3]))]
                        sysvars['window_size'] = new_value
                        gobj.globs['_window_size'] = new_value
                    case 'target_framerate':
                        new_value = abs(ph.get_int(splitline[2]))
                        if new_value == 0:
                            new_value = 1
                        sysvars['target_framerate'] = new_value
                    case 'hide_mouse':
                        sysvars['hide_mouse'] = ph.get_int(splitline[2]) == 1
                    case 'caption':
                        sysvars['caption'] = ph.get_string(splitline[2])
                    case 'busy_wait':
                        sysvars['busy_wait'] = (splitline[2] == '1')
                    case 'apply':
                        gobj.apply_sysvars_flag = True
                    case _:
                        return
            case _:
                try:
                    # default case, assume we're calling a function, so move the script index to the function start point
                    ph.pc_stack.append(self.functions[splitline[0]])
                    ph.stacklen += 1

                    # set function parameter variables
                    for item in splitline[1:]:
                        splitparam = item.split('=')
                        ph.variables[splitline[0]+'_'+splitparam[0]] = ph.get_any(splitparam[1])
                except KeyError:
                    error("Runtime", "Invalid Command", f"The command '{splitline[0]}' is not a built-in command or user-defined function.", playhead=ph)
                except IndexError:
                    error("Runtime", "Invalid Function Call", f"'{line}' is not a valid function call. Arguments must use the form '<name>=<value>'.", playhead=ph)

    def cmd_maskcollide(self, ph:playhead, splitline:list[str]):
        obj1:gobj; obj2:gobj
        if len(splitline) == 2:
            obj1 = ph.parent_obj
            obj2 = ph.get_gobj(splitline[1])
        else:
            obj1 = ph.get_gobj(splitline[1])
            obj2 = ph.get_gobj(splitline[2])

        result = 0
        if obj1.collision_mask and obj2.collision_mask:
            if obj1.render_rect.colliderect(obj2.render_rect):
                offset = (obj2.render_rect.left - obj1.render_rect.left, obj2.render_rect.top - obj1.render_rect.top)
                result = obj1.collision_mask.overlap(obj2.collision_mask, offset)
                if result:
                    result = list(result)
                else:
                    result = 0

        ph.setvar("_return", result)   

    def cmd_collide(self, ph:playhead, splitline:list[str]):
        obj:gobj = ph.get_gobj(splitline[1])
        if obj == 0:
            error("Runtime", "Invalid collision.", "No such object to collide.",ph)
            return
        if obj.collision_rect == None:
            error("Runtime", "Invalid collision.", "Object does not have a collider.",ph)
            return
        
        match splitline[2]:
            case 'all':
                obj.testcollisions(ph)
            case 'line':
                # collide with a line, coords given
                # ex: collide line 00 100 100 -> return true if the line from (0,0) to (100,100) intersects the collider

                line_coords = []
                for i in range(4):
                    line_coords.append(ph.get_int(splitline[i+3]))

                collider:pygame.Rect = obj.collision_rect
                clipped = collider.clipline(line_coords)
                if clipped == ():
                    ph.setvar("_return", 0)
                else:
                    ph.setvar("_return", 1)
            case 'point':
                # collide with a point

                point_coords = []
                for i in range(2):
                    point_coords.append(ph.get_int(splitline[i+3]))

                collision = obj.collision_rect.collidepoint(point_coords)
                if collision == False:
                    ph.setvar("_return", 0)
                else:
                    ph.setvar("_return", 1)
            case _:
                # collide with one other object
                other_obj = ph.get_gobj(splitline[2])
                if not type(other_obj) is gobj:
                    error("Runtime", "Invalid collision.", f"Can't test collision. No object with ID {other_obj}",ph)
                    return
                
                collider = obj.collision_rect

                other_collider:pygame.Rect = other_obj.collision_rect
                collision = collider.colliderect(other_collider)

                if collision == False:
                    ph.setvar("_return", 0)
                else:
                    ph.setvar("_return", 1)

    def cmd_draw(self, ph:playhead, splitline:list[str]):
        draw_obj:gobj = ph.get_gobj(splitline[1])
        if draw_obj == 0:
            return
        if draw_obj.canvas == None or list(draw_obj.canvas.get_size()) != gobj.resolution:
            # create a canvas that spans the screen
            draw_obj.canvas = pygame.Surface(gobj.resolution).convert_alpha()
            draw_obj.canvas.fill(color=(0,0,0,0))
            draw_obj.canvas_rect = pygame.Rect((0,0), gobj.resolution)
        
        # get the position to draw at
        draw_position = self.parent_obj.global_pos
        stroke_width = ph.get_int('_draw_stroke')
        color = self.parent_obj.get_color()
        centered = ph.get_int('_draw_centered')
        match splitline[2]:
            case 'rect':
                # ex: draw rect 10 10
                draw_size = [ph.get_int(splitline[3]), ph.get_int(splitline[4])]
                if centered == 1:
                    draw_position = [draw_position[0]-(draw_size[0]//2), draw_position[1]-(draw_size[1]//2)]
                
                rect_corner_args = [-1]*5
                arg_count = 0
                for i, n in enumerate(range(5, len(splitline))):
                    arg_count += 1
                    rect_corner_args[i] = ph.get_int(splitline[n])
                if arg_count == 1:
                    # only one corner argument, apply to all four corners.
                    for i in range(1, len(rect_corner_args)):
                        rect_corner_args[i] = rect_corner_args[1]

                draw_rect = pygame.Rect(draw_position, draw_size)
                if draw_rect.colliderect((0,0), gobj.resolution):
                    draw_obj.is_canvas_dirty = True
                    pygame.draw.rect(draw_obj.canvas, color, draw_rect, stroke_width, rect_corner_args[0], rect_corner_args[1], rect_corner_args[2], rect_corner_args[3], rect_corner_args[4])
            case 'polygon':
                # ex: draw _self polygon points
                # points is a list of int values. draw_stroke attribute will be used for width
                draw_points_list = ph.get_list(splitline[3])
                if len(draw_points_list)%2 != 0:
                    error("Runtime", "Cannot draw polygon.", f"{draw_points_list} is an incorrect argument for draw polygon.",ph)
                    return

                if centered:
                    # find max width and height, and offset the draw position accordingly
                    draw_position[0] -= max(draw_points_list[::2])//2
                    draw_position[1] -= max(draw_points_list[1::2])//2

                poly_points = []
                for i in range(0, len(draw_points_list), 2):
                    poly_points.append([draw_points_list[i]+draw_position[0], draw_points_list[i+1]+draw_position[1]])
                draw_rect = pygame.draw.polygon(draw_obj.canvas, color, poly_points, stroke_width)
                if draw_rect.colliderect((0,0), gobj.resolution):
                    draw_obj.is_canvas_dirty = True
            case 'ellipse':
                draw_size = [ph.get_int(splitline[3]), ph.get_int(splitline[4])]
                if centered == 1:
                    draw_position = [draw_position[0]-(draw_size[0]//2), draw_position[1]-(draw_size[1]//2)]                    

                draw_rect = pygame.Rect(draw_position, draw_size)
                if draw_rect.colliderect((0,0), gobj.resolution):
                    draw_obj.is_canvas_dirty = True
                    pygame.draw.ellipse(draw_obj.canvas, color, draw_rect, stroke_width)
            case 'line':
                # ex: draw line 0 0 100 100
                c1 = [ph.get_int(splitline[3]), ph.get_int(splitline[4])]
                c2 = [ph.get_int(splitline[5]), ph.get_int(splitline[6])]

                if self.parent_obj.get('_draw_antialiased') == 1:
                    pygame.draw.aaline(draw_obj.canvas, color, c1, c2, stroke_width)
                else:
                    pygame.draw.line(draw_obj.canvas, color, c1, c2, stroke_width)
                draw_obj.is_canvas_dirty = True
            case 'text':
                # ex: draw text "Hello!"
                # stroke_width is font size now.

                current_font = gobj.fonts.get(ph.get_string('_draw_font'))

                text_obj = pygame.font.Font(current_font, stroke_width)
                text = ph.get_string(splitline[3])
                text_surf = text_obj.render(text, self.parent_obj.get('_draw_antialiased')==1, color)
                if len(color) == 4:
                    text_surf.set_alpha(color[3])
                draw_size = text_surf.get_size()

                if centered == 1:
                    draw_position = [draw_position[0]-(draw_size[0]//2), draw_position[1]-(draw_size[1]//2)]
                draw_rect = pygame.Rect(draw_position, draw_size)
                if draw_rect.colliderect((0,0), gobj.resolution):
                    draw_obj.canvas.blit(text_surf, draw_rect)
                    draw_obj.is_canvas_dirty = True
            case 'clear':
                if draw_obj.is_canvas_dirty:
                    draw_obj.canvas.fill(color=(0,0,0,0))
                    draw_obj.is_canvas_dirty = False
            case _: # default case, try to draw a sprite
                sprite = gobj.sprites.get(ph.get_string(splitline[2]))
                if sprite != None:
                    
                    draw_size = sprite.get_size()
                    rotation = 0
                    fliph= False
                    flipv= False
                    if len(splitline) > 3: # rotation
                        rotation = ph.get_numeric(splitline[3])
                    if len(splitline) > 5: # fliph
                        fliph = ph.get_int(splitline[5]) == 1
                    if len(splitline) == 7: # flipv
                        flipv = ph.get_int(splitline[6]) == 1
                    if len(splitline) > 4: # scale factor
                        scale_factor = ph.get_numeric(splitline[4])
                        draw_size = (round(draw_size[0] * scale_factor), round(draw_size[1] * scale_factor))

                    draw_surf = pygame.transform.rotate(pygame.transform.flip(pygame.transform.scale(sprite, draw_size), fliph, flipv),-rotation)
                    draw_size = draw_surf.get_size()

                    if centered == 1:
                        draw_position = [draw_position[0]-(draw_size[0]//2), draw_position[1]-(draw_size[1]//2)]
                    
                    draw_rect = pygame.Rect(draw_position, draw_surf.get_size())
                    if draw_rect.colliderect((0,0), gobj.resolution):
                        draw_obj.is_canvas_dirty = True
                        draw_obj.canvas.blit(draw_surf, draw_rect)
#endregion

#endregion

#region ERROR REPORTING
# ================================================================================================

class error:
    last_errs:list = []

    def __init__(self, err_type:str, label:str, info:str, playhead:playhead=None, obj_id:int=0, script:str="", pc_stack:list[int]=[], code="", hide_errors=False):
        if playhead == None:
            self.err_type = err_type
            self.obj_id = obj_id
            self.script = script
            self.pc_stack = pc_stack
            self.hide_errors = hide_errors
            self.label = label
            if err_type == "Runtime":
                self.code = scriptsystem.scripts[script][pc_stack[-1]] # The code that caused the error.
            else:
                self.code = code
            self.info = info
            # error.last_errs.append(self)
            # if not hide_errors:
            #     self.print_err()

            if self.err_type != "Load":
                gobj.trap_error(obj_id, self.label)
        else:
            self.err_type = err_type
            self.obj_id = playhead.parent_obj.immut_id
            self.script = playhead.parent_obj.script_file
            self.pc_stack = playhead.pc_stack
            self.label = label
            self.info = info
            self.hide_errors = playhead.parent_obj.attributes['_hide_errors']
            playhead.has_error = True
            if err_type == "Runtime":
                self.code = scriptsystem.scripts[self.script][self.pc_stack[-1]] # The code that caused the error.
            else:
                self.code = code
        

        error.last_errs.append(self)
        if not self.hide_errors:
            self.print_err()

        if self.err_type != "Load":
            gobj.trap_error(self.obj_id, self.label)
    
    def print_err(self):
        print( f"\n{self.err_type} error: {self.label}\n"
              +f"Object ID: {self.obj_id}\n"
              +f"Script: {self.script} at line number(s): {self.pc_stack}\n"
              +f"Code: {self.code}\n"
              +f"{f"{self.info}\n" if self.info != "" else ""}")
#endregion

#region MUSIC
# ================================================================================================

# run the music
def runmusic():
    if gobj.music_paused:#gobj.globs['_paused']:
        return

    mus = gobj.globs['_music']

    if mus == 'silence':
        return
    pygame.mixer_music.set_volume(gobj.globs.get('_music_vol')/100)
    if not pygame.mixer_music.get_busy():
        path = getpathname(mus, 2)
        pygame.mixer_music.load(path)
        pygame.mixer_music.play()

# switch the music to something else with an optional fadeout
def switchmusic(music, fade=5000):
    gobj.globs['_music'] = music
    pygame.mixer_music.fadeout(fade)   
#endregion

#region INPUT HANDLING
# ================================================================================================
from pygame.locals import *

# Keystates interprets the key info from pygame into a more useful format
# with this, you can tell whether a key was pressed that frame, held, released that frame, or not held

keystates = {
}

# used to determine which keys are used in the game, loaded from scripts
keymap = {
    "backspace":K_BACKSPACE,
    "tab":K_TAB,
    "return":K_RETURN,
    "escape":K_ESCAPE,
    "space":K_SPACE,
    "quote":K_QUOTE,
    "comma":K_COMMA,
    "minus":K_MINUS,
    "equals":K_EQUALS,
    "period":K_PERIOD,
    "slash":K_SLASH,
    "backslash":K_BACKSLASH,
    "0":K_0,
    "1":K_1,
    "2":K_2,
    "3":K_3,
    "4":K_4,
    "5":K_5,
    "6":K_6,
    "7":K_7,
    "8":K_8,
    "9":K_9,
    "semicolon":K_SEMICOLON,
    "leftbracket":K_LEFTBRACKET,
    "rightbracket":K_RIGHTBRACKET,
    "grave":K_BACKQUOTE,
    "a":K_a,
    "b":K_b,
    "c":K_c,
    "d":K_d,
    "e":K_e,
    "f":K_f,
    "g":K_g,
    "h":K_h,
    "i":K_i,
    "j":K_j,
    "k":K_k,
    "l":K_l,
    "m":K_m,
    "n":K_n,
    "o":K_o,
    "p":K_p,
    "q":K_q,
    "r":K_r,
    "s":K_s,
    "t":K_t,
    "q":K_q,
    "r":K_r,
    "s":K_s,
    "t":K_t,
    "u":K_u,
    "v":K_v,
    "w":K_w,
    "x":K_x,
    "y":K_y,
    "z":K_z,
    "delete":K_DELETE,
    "up":K_UP,
    "down":K_DOWN,
    "left":K_LEFT,
    "right":K_RIGHT,
    "insert":K_INSERT,
    "home":K_HOME,
    "end":K_END,
    "pageup":K_PAGEUP,
    "pagedown":K_PAGEDOWN,
    "f1":K_F1,
    "f2":K_F2,
    "f3":K_F3,
    "f4":K_F4,
    "f5":K_F5,
    "f6":K_F6,
    "f7":K_F7,
    "f8":K_F8,
    "f9":K_F9,
    "f10":K_F10,
    "f11":K_F11,
    "f12":K_F12,
    "capslock":K_CAPSLOCK,
    "leftshift":K_LSHIFT,
    "rightshift":K_RSHIFT,
    "leftcontrol":K_LCTRL,
    "rightcontrol":K_RCTRL,
    "leftalt":K_LALT,
    "rightalt":K_RALT,
    # Arbitrary values for mouse input. Hope this works. Used the ascii values for capitals so hopefully there isn't a clash.
    "mouse_left":65,
    "mouse_right":67,
    "mouse_center":66,
}

def addkey(key:str):
    keycode = keymap.get(key)
    if keycode == None:
        print("Can't add key, name not recognized.")
        return
    
    # add the key
    keystates[keycode] = 0

# Keystates:
# 0: off, 2: pressed, 3: on, -1: released

def updatekeystates(keylist:list):
    for key in keystates:

        if key > 64 and key < 68:
            # update mouse stuff
            mouse_buttons = pygame.mouse.get_pressed()
            key_pressed = mouse_buttons[key-65]
        else:
            key_pressed = keylist[key]

        # if the key is pressed
        if key_pressed:
            if keystates[key] <= 0:
                keystates[key] = 2
            else:
                keystates[key] = 1
        # key is not pressed
        else:
            if keystates[key] >= 1:
                keystates[key] = -1
            else:
                keystates[key] = 0

#endregion

#region SYSTEM VARS
# ================================================================================================
sysvars:dict = {
    'screen_resolution':[480,360],
    'window_size':[480,360],    # stuff will be rendered according to the screen resolution then stretched to fit the window size
    'is_fullscreen':False,
    'target_framerate':60,
    'hide_mouse':False,
    'caption':'Patch Project',
    'busy_wait':True,
}

def apply_sysvars():
    if sysvars['is_fullscreen']:
        #flags = FULLSCREEN|SCALED|DOUBLEBUF
        flags = FULLSCREEN|SCALED
    else:
        #flags = DOUBLEBUF
        flags = 0
        
    display_screen = pygame.display.set_mode(sysvars['window_size'], flags)
    
    main_screen = pygame.Surface(sysvars['screen_resolution'])
    gobj.resolution = sysvars['screen_resolution']
    
    gobj.globs['_screen_resolution'] = gobj.resolution
    gobj.globs['_window_size'] = sysvars['window_size']

    pygame.mouse.set_visible(not sysvars['hide_mouse'])

    pygame.display.set_caption(sysvars['caption'])

    current_icon = gobj.sprites.get("_icon")
    if type(current_icon) is pygame.Surface:
        pygame.display.set_icon(current_icon)

    target_framerate = sysvars['target_framerate']

    return (display_screen, main_screen, target_framerate, sysvars['window_size'], sysvars['screen_resolution'], sysvars['busy_wait'])
#endregion

#region EXPRESSION PARSING
# ==============================================

'''
Expression parser

input: a string containing an expression
output: a string, containing the expression converted to postfix

Procedure: 
1: separate string into tokens (variable names, operators, numbers, parenthases)
2: apply Dijkstra's algorithm


(-56<?xp and xp !=yp)
->
( -56 < ?xp and xp != yp )
->
-56 ?xp < xp yp != and

'''

# In this scheme, '^' is power, '~' is xor.
operators = {'^', '*', '//', '/', '%', '+', '-', '<', '>', '<=', '>=', '==', '!=', '&', '|', '~', '<<', '>>', '`', 'and', 'or', 'not', 'len', 'sin', 'cos', 'tan', 'arcsin', 'arccos', 'arctan', 'lower', 'upper', 'abs', 'round', 'int', 'float', 'str'}
right_associative_ops = {'^'}
var_name_chars = '_0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ?.\'"[]'
namechar_set = {ch for ch in var_name_chars} # convert into a set for access speed

def checknumeric(item):
    try:
        float(item)
        return True
    except ValueError:
        return False

def infix_to_postfix(expr:str) -> str:
    token_list = tokenize(expr)

    return shunting_yard(token_list)

def tokenize(expr:str) -> list[str]:
    tokens = []
    cur_token = ""
    is_operator = False

    in_raw_string = False

    in_raw_array = 0

    for i, char in enumerate(expr):
        if in_raw_string:
            cur_token += char
            if char == '"':
                in_raw_string = False
                tokens.append(cur_token)
                cur_token = ""
        elif in_raw_array:
            cur_token += char
            if char == ']':
                in_raw_array -= 1
                if in_raw_array == 0:
                    tokens.append(cur_token)
                    cur_token = ""
            if char == '[':
                in_raw_array += 1
        else:
            if char in ['(', ')']:
                if cur_token != "":
                    tokens.append(cur_token)
                tokens.append(char)
                cur_token = ""
                continue
            else:
                if char in [' ', '\t']:
                    if cur_token != "":
                        tokens.append(cur_token)
                        cur_token = ""
                    continue
                elif char in namechar_set:
                    if cur_token != '' and is_operator:
                        tokens.append(cur_token)
                        cur_token = ""
                    is_operator = False

                    if char == '"':
                        in_raw_string = True
                    elif char == '[':
                        in_raw_array = True
                else:
                    if cur_token != '' and not is_operator:
                        tokens.append(cur_token)
                        cur_token = ""
                    is_operator = True

                cur_token += char

    if cur_token != "":
        tokens.append(cur_token)
    return tokens

def find_precedence(operator:str) -> int:
    r=0
    match operator:
        case 'and' | 'or':
            pass
        case 'not':
            r=1
        case '>' | '>=' | '<' | '<=' | '==' | '!=':
            r=2
        case '+' | '-' | '&' | '|' | '~':
            r=3
        case '*' | '/' | '//' | '%':
            r=4
        case '_':
            r=5
        case 'len' | 'sin' | 'cos' |'tan' | 'arcsin' | 'arccos' | 'arctan' | 'lower' | 'upper' | 'abs' | 'round'|'int'|'float'|'str':
            r=6
        case '^'|'`':
            r=7
    return r

# Implementation of Dijkstra's Shunting Yard algorithm for infix parsing
def shunting_yard(tokens:list[str]):
    op_stack = []
    output_list = []
    for i, item in enumerate(tokens):
        if item in operators:
            if item == '-' and (len(output_list) == 0 or tokens[i-1] == '(' or tokens[i-1] in operators):
                # Handle unary minus
                if i+1 < len(tokens) and checknumeric(tokens[i+1]):
                    # Treat negative numbers as numeric literals
                    tokens[i+1] = f"-{tokens[i+1]}"
                    continue

                #current_precedence = 4 # between multiply/divide and the functions
                output_list.append('0')
                item = "_"

            if len(op_stack) == 0 or op_stack[-1] == '(':
                op_stack.append(item)
            else:
                current_symbol = item
                
                current_precedence = find_precedence(current_symbol)
                top_precedence = find_precedence(op_stack[-1])
                if (current_precedence > top_precedence) or (current_precedence == top_precedence and item in right_associative_ops) or len(op_stack) == 0 or op_stack[-1] == '(':
                    op_stack.append(item)
                else:
                    while (current_precedence < top_precedence) or (current_precedence == top_precedence and item not in right_associative_ops) and op_stack[-1] != "(":
                        output_list.append(op_stack.pop())
                        current_symbol = item
                        if len(op_stack) == 0:
                            top_precedence = -1
                        else:
                            top_precedence = find_precedence(op_stack[-1])
                    op_stack.append(item)
        elif item == '(':
            op_stack.append(item)
        elif item == ')':
            popped = op_stack.pop()
            while(popped != '('):
                output_list.append(popped)
                popped = op_stack.pop()
        else:
            output_list.append(item)
    
    while len(op_stack) > 0:
        output_list.append(op_stack.pop())
    
    output = ''
    for item in output_list:
        if item == "_":
            item = "-"
        output += f"{item} "
    return output[:-1]

#endregion