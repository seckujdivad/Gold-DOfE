import tkinter as tk
import multiprocessing as mp
import os
import sys
import json
import threading
import time
import random
import math

class CanvasController:
    def __init__(self, canvas, game = None, layers = None):
        self.canvas = canvas
        self.game = game
        
        self.winfo_width = self.canvas.winfo_width
        self.winfo_height = self.canvas.winfo_height
        self.find_overlapping = self.canvas.find_overlapping
        self.config = self.canvas.config
        self.bind = self.canvas.bind
        self.unbind = self.canvas.unbind
        self.unbind_all = self.canvas.unbind_all
        
        if layers is None:
            layers = ['user', 'layers.json']
        
        self.layers = []
        self.reserved_args = ['layer']
        
        with open(os.path.join(sys.path[0], *layers), 'r') as file:
            self.layer_config = json.load(file) #load user defined order for screen items to be rendered in
        
        self.global_time = time.time()
        
    def create_rectangle(self, *coords, **args):
        'Wrapper function to provide tk canvas-like syntax'
        return self._create('rectangle', coords, args)
    
    def create_image(self, *coords, **args):
        'Wrapper function to provide tk canvas-like syntax'
        return self._create('image', coords, args)
    
    def create_text(self, *coords, **args):
        return self._create('text', coords, args)
    
    def create_window(self, *coords, **args):
        return self._create('window', coords, args)
    
    def create_line(self, *coords, **args):
        return self._create('line', coords, args)
    
    def _create(self, obj_type, coords, args):
        if not 'layer' in args:
            args['layer'] = 0
        
        if type(args['layer']) == str: #layer is string, use lookup table
            if args['layer'] in self.layer_config:
                args['layer'] = self.layer_config[args['layer']]
            else:
                raise ValueError('Couldn\'t find layer name "{}" in config'.format(args['layer'])) #layer not in lookup table
            
        while not len(self.layers) >= args['layer'] + 1:
            self.layers.append([]) #make layer if it doesn't exist
        
        filtered_args = {} #remove arguments that are reserved for controller (layer etc) and pass the rest on to the canvas
        for key in args:
            if not key in self.reserved_args:
                filtered_args[key] = args[key]
        
        if obj_type == 'rectangle': #call relevant canvas function
            obj = self.canvas.create_rectangle(*coords, **filtered_args)
        elif obj_type == 'image':
            obj = self.canvas.create_image(*coords, **filtered_args)
        elif obj_type == 'text':
            obj = self.canvas.create_text(*coords, **filtered_args)
        elif obj_type == 'window':
            obj = self.canvas.create_window(*coords, **filtered_args)
        elif obj_type == 'line':
            obj = self.canvas.create_line(*coords, **filtered_args)
        
        self.layers[args['layer']].append({'object': obj})
        
        ## objects are always created on the top of their layer
        
        if not len(self.layers) == args['layer'] + 1: ## logic to find next highest tag and move just below it
            next_layer = None
            for i in range(len(self.layers) - 1, args['layer'], -1):
                if not len(self.layers[i]) == 0:
                    next_layer = i
            if next_layer == None:
                if len(self.layers) == 1:
                    lower_to = None
                    for i in range(args['layer']):
                        if not len(self.layers[i]) == 0:
                            lower_to = self.layers[i][len(self.layers[args['layer']]) - 1]
                    if not lower_to == None:
                        self.canvas.tag_lower(obj, lower_to['object'])
                else:
                    self.canvas.tag_lower(obj, self.layers[args['layer']][len(self.layers[args['layer']]) - 2]['object'])
            else:
                self.canvas.tag_lower(obj, self.layers[next_layer][0]['object'])
        
        return obj
    
    def delete(self, obj):
        'Delete item from canvas'
        to_remove = []
        for a in range(len(self.layers)):
            for b in range(len(self.layers[a])):
                if self.layers[a][b]['object'] == obj:
                    to_remove.append([a, b])
        
        self.canvas.delete(obj)
        
        to_remove.reverse()
        for a, b in to_remove:
            self.layers[a].pop(b)
        
    def coords(self, obj, *coords):
        'Set the coordinates of something on the canvas'
        self.canvas.coords(obj, *coords)
    
    def itemconfigure(self, obj, **args):
        'Configure an item on the canvas'
        self.canvas.itemconfigure(obj, **args)
    
    def winfo_width(self):
        return self.canvas.winfo_width()
    
    def winfo_height(self):
        return self.canvas.winfo_height()

class Model:
    '''
    Model:
    Similar in function to canvas.create_image
    canvas_controller - CanvasController object to render to
    mdl_name - name of model in map files
    map_path - path to map files
    layer - string or int for canvas controller
    '''
    def __init__(self, canvas_controller, mdl_name, map_path, layer):
        self.mdl_name = mdl_name
        self.map_path = map_path
        self.canvas_controller = canvas_controller
        self.layer = layer
        
        ## make data structures
        class attributes:
            class pos: #current coordinates
                x = 0
                y = 0
                
            class offscreen: #coordinates where the model is guaranteed to be offscreen
                x = 0
                y = 0
                
            rotation = 0 #current rotation (0-359)
            rotation_steps = 0 #number of different rotations to make
            
            transparency = 0 #current transparency (0-255)
            transparency_steps = 0 #number of different transparencies to make
            
            class offset: #amount that each layer of a stacked model is offset by
                x = 0
                y = 0
            
            baseimages = {} #images before any effects have been applied to them
            imageobjs = {} #image objects with effects that can be used to create canvas objects
            canvobjs = {} #references to canvas objects created from imageobjs
            
            uses_PIL = False
            
            animation = None
            
            class anim_controller:
                playing_onetime = False
                revert_to = None
                sync = False
            
            class snap:
                use = False
                x = 1
                y = 1
                
            interps_per_second = 0
                
            render_quality = 0 #0-3 - render quality as defined in the user's config
            image_set = None #e.g. idle
            
            num_layers = 0 #number of image layers loaded into memory
            num_layers_total = 0 #number of image layers that exist on the disk
            
            running = True
        self.attributes = attributes
        
        class cfgs:
            model = {}
            user = {}
            map = {}
        self.cfgs = cfgs
        
        class pillow:
            image = None
            image_chops = None
            photoimage = None
            gifimage = None
        self.pillow = pillow
        
        ## load data into structures
        #load configs
        with open(os.path.join(self.map_path, 'models', self.mdl_name, 'list.json'), 'r') as file:
            self.cfgs.model = json.load(file)
        
        with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
            self.cfgs.user = json.load(file)
        
        with open(os.path.join(self.map_path, 'list.json'), 'r') as file:
            self.cfgs.map = json.load(file)
        
        #translate data from cfgs into model data structures
        self.attributes.offscreen.x = self.cfgs.model['offscreen'][0]
        self.attributes.offscreen.y = self.cfgs.model['offscreen'][1]
        
        if 'offsets' in self.cfgs.model:
            self.attributes.offset.x = self.cfgs.model['offsets'][0]
            self.attributes.offset.y = self.cfgs.model['offsets'][1]
        
        self.attributes.pos.x = self.attributes.offscreen.x
        self.attributes.pos.y = self.attributes.offscreen.y
        
        self.attributes.uses_PIL = self.cfgs.user['graphics']['PILrender']
        self.attributes.render_quality = self.cfgs.user['graphics']['model quality']
        self.attributes.rotation_steps = self.cfgs.model['rotations'][self.attributes.render_quality]
        self.attributes.num_layers = self.cfgs.model['layers'][self.attributes.render_quality]
        
        self.attributes.interps_per_second = self.cfgs.user['network']['interpolations per second']
        
        ##load grid snap values
        if 'use grid' in self.cfgs.model:
            self.attributes.snap.use = self.cfgs.model['use grid']
            
        if self.cfgs.map['grid']['force']:
            self.attributes.snap.use = self.cfgs.map['grid']['force value']
        self.attributes.snap.x = self.cfgs.map['grid']['mult']['x']
        self.attributes.snap.y = self.cfgs.map['grid']['mult']['y']
        
        #load animation profiles
        self.attributes.image_set = self.cfgs.model['default textures']
        
        if not 'animation' in self.cfgs.model:
            self.cfgs.model['animation'] = {'profiles': {},
                                            'ranks': [self.attributes.image_set]}
        
        if not self.attributes.image_set in self.cfgs.model['animation']['profiles']:
            self.cfgs.model['animation']['profiles'][self.attributes.image_set] = {'frames': 1,
                                                                                   'delay': 1000,
                                                                                   'variation': 0,
                                                                                   "sync": False}
        
        self.attributes.animation = AnimAttr(self.attributes, self.cfgs.model['animation'])
        
        #load steps for graphics prerenderer
        if 'transparencies' in self.cfgs.model:
            self.attributes.transparency_steps = self.cfgs.model['transparencies'][self.attributes.render_quality]
        else:
            self.attributes.transparency_steps = 1
        
        if 'rotations' in self.cfgs.model:
            self.attributes.rotation_steps = self.cfgs.model['rotations'][self.attributes.render_quality]
        else:
            self.attributes.rotation_steps = 1
            
        #load PIL modules
        if self.attributes.uses_PIL:
            self.pillow.image = __import__('PIL.Image').Image
            self.pillow.image_chops = __import__('PIL.ImageChops').ImageChops
            self.pillow.photoimage = __import__('PIL.ImageTk').ImageTk.PhotoImage
            self.pillow.gifimage = __import__('PIL.GifImagePlugin').GifImagePlugin.GifImageFile
        
        ##load textures
        #check for no PIL textures
        if not self.attributes.uses_PIL:
            if 'no PIL textures' in self.cfgs.model:
                self.cfgs.model['textures'] = self.cfgs.model['no PIL textures']
                
        #get names of textures
        tex_names = {}
        for tex_set in self.cfgs.model['textures']:
            tex_names[tex_set] = []
            if type(self.cfgs.model['textures'][tex_set]) == str:
                if os.path.isdir(os.path.join(self.map_path, 'models', self.mdl_name, self.cfgs.model['textures'][tex_set])):
                    tex_names[tex_set] = [os.path.join(self.cfgs.model['textures'][tex_set], path) for path in os.listdir(os.path.join(self.map_path, 'models', self.mdl_name, self.cfgs.model['textures'][tex_set]))]
                else:
                    tex_names[tex_set] = [self.cfgs.model['textures'][tex_set]]
            else:
                tex_names[tex_set] = self.cfgs.model['textures'][tex_set]
            
            self.attributes.baseimages[tex_set] = []
            self.attributes.imageobjs[tex_set] = []
            self.attributes.canvobjs[tex_set] = []
        
        filtered_tex_names = {}
        for name in tex_names:
            self.attributes.num_layers_total = len(tex_names[name])
            mult = self.attributes.num_layers_total / self.attributes.num_layers
            filtered_tex_names[name] = []
            for i in range(self.attributes.num_layers):
                filtered_tex_names[name].append(tex_names[name][int(i * mult)])
        
        tex_names = filtered_tex_names
        
        #load textures
        default_set = self.attributes.image_set
        
        for tex_set in tex_names:
            for name in tex_names[tex_set]:
                self.attributes.image_set = tex_set
                if self.attributes.uses_PIL:
                    if self.attributes.animation.frames == 1:
                        self.attributes.baseimages[tex_set].append([self.pillow.image.open(os.path.join(self.map_path, 'models', self.mdl_name, name))])
                    else:
                        if type(name) == list:
                            self.attributes.baseimages[tex_set].append([self.pillow.image.open(os.path.join(self.map_path, 'models', self.mdl_name, subname)) for subname in name])
                        
                        else:
                            frames = []
                            for i in range(self.attributes.animation.frames):
                                frame = self.pillow.gifimage(os.path.join(self.map_path, 'models', self.mdl_name, name))
                                frame.seek(i)
                                frames.append(frame)
                            
                            self.attributes.baseimages[tex_set].append(frames)
                else:
                    if self.attributes.animation.frames == 1:
                        self.attributes.baseimages[tex_set].append([tk.PhotoImage(file = os.path.join(self.map_path, 'models', self.mdl_name, name))])
                    else:
                        if type(name) == list:
                            self.attributes.baseimages[tex_set].append([tk.PhotoImage(file = os.path.join(self.map_path, 'models', self.mdl_name, subname)) for subname in name])
                        else:
                            self.attributes.baseimages[tex_set].append([tk.PhotoImage(file = os.path.join(self.map_path, 'models', self.mdl_name, name), format = 'gif -index {}'.format(i)) for i in range(self.attributes.animation.frames)])
        
        self.attributes.image_set = default_set
        
        #apply transformations to textures
        for tex_set in self.attributes.baseimages:
            for images in self.attributes.baseimages[tex_set]:
                if self.attributes.uses_PIL:
                    rotations = []
                    for rot in range(1, self.attributes.rotation_steps + 1, 1):
                        current_rotation = rot / (self.attributes.rotation_steps / 360)
                        
                        images_rotated = []
                        for image in images:
                            images_rotated.append(self.apply_rotation(image, current_rotation))
                        
                        
                        if self.attributes.transparency_steps == 1:
                            transparencies = [[self.pillow.photoimage(image_rotated) for image_rotated in images_rotated]]
                        else:
                            transparencies = []
                            
                            for transp in range(self.attributes.transparency_steps):
                                transparencies.append([self.pillow.photoimage(self.apply_transparency(image_rotated, transp / (self.attributes.transparency_steps / 256))) for image_rotated in images_rotated])
                            
                        rotations.append(transparencies)
                        
                    self.attributes.imageobjs[tex_set].append(rotations)
                        
                else:
                    self.attributes.imageobjs[tex_set].append([[images]]) #no PIL means no transformations can be applied
        
        #make canvas objects
        for tex_set in self.attributes.imageobjs:
            for rotations in self.attributes.imageobjs[tex_set]:
                new_rotations = []
                for transparencies in rotations:
                    new_transparencies = []
                    for frames in transparencies:
                        new_frames = []
                        for image_ in frames:
                            new_frames.append(self.canvas_controller.create_image(self.attributes.offscreen.x, self.attributes.offscreen.y, image = image_, layer = self.layer))
                        new_transparencies.append(new_frames)
                    new_rotations.append(new_transparencies)
                self.attributes.canvobjs[tex_set].append(new_rotations)
        
        ## start animation player if necessary
        if self.attributes.animation.run_loop:
            threading.Thread(target = self._anim_player, name = 'Model animation player', daemon = True).start()
        
        # start interpolation thread
        self._set_pipe, pipe = mp.Pipe()
        threading.Thread(target = self._set_handler, args = [pipe], name = 'Interpolation handler', daemon = True).start()
        
        ## call set
        self.set(force = True)
    
    def apply_rotation(self, image_, angle):
        return image_.rotate(0 - angle)
    
    def apply_transparency(self, image_, transparency):
        try:
            return self.pillow.image_chops.multiply(image_, self.pillow.image.new('RGBA', image_.size, color = (255, 255, 255, int(transparency))))
        except ValueError:
            raise ValueError('Model texture doesn\'t have an alpha channel - make sure it uses 32 bit colour')
    
    def increment(self, x = None, y = None, rotation = None, transparency = None, frame = None, force = False, timeframe = None):
        self.set(x, y, rotation, transparency, frame, force, True, timeframe)
    
    def set(self, x = None, y = None, rotation = None, transparency = None, frame = None, force = False, image_set = None, increment = False, timeframe = None):
        action = Action()
        if timeframe is None:
            action.add(x, y, rotation, transparency, frame, force, image_set, increment)
            
        else:
            slots = timeframe * self.attributes.interps_per_second
            
            if x is None:
                xinc = None
            else:
                xinc = x / slots
            
            if y is None:
                yinc = None
            else:
                yinc = y / slots
            
            if rotation is None:
                rotationinc = None
            else:
                rotationinc = rotation / slots
            
            if transparency is None:
                transparencyinc = None
            else:
                transparencyinc = transparency / slots
                
            for i in range(int(slots)):
                action.add(xinc, yinc, rotationinc, transparencyinc, frame, force, image_set, True)
            action.add(x, y, rotation, transparency, frame, force, image_set, increment)
            
            action.delay = timeframe / slots
        self._set_pipe.send(action)
    
    def _set_handler(self, pipe):
        current_action = None
        while self.attributes.running:
            if current_action is None:
                current_action = pipe.recv()
                current_action.goto(0)
                
            else:
                frame = current_action.current()
                arg_slice = frame[:7]
                
                print(arg_slice[0])
                
                if frame[7]: #increment
                    self._increment(*arg_slice)
                else:
                    self._set(*arg_slice)
                
                if current_action.frame == len(frame) - 1:
                    del current_action
                    current_action = None
    
    def _increment(self, x, y, rotation, transparency, frame, force, image_set):
        if x is not None:
            x += self.attributes.pos.x
            
        if y is not None:
            y += self.attributes.pos.y
        
        if rotation is not None:
            rotation += self.attributes.rotation
        
        if transparency is not None:
            transparency += self.attributes.transparency
        
        if frame is not None:
            frame += self.attributes.animation.current_frame
            
        if image_set is not None:
            x += self.attributes.image_set
        
        self._set(x, y, rotation, transparency, frame, force, image_set)
    
    def _set(self, x, y, rotation, transparency, frame, force, image_set):
        if image_set is None:
            prev_image_set = None
        else:
            prev_image_set = self.attributes.image_set
            self.attributes.image_set = image_set
    
        if x is not None:
            self.attributes.pos.x = x
        
        if y is not None:
            self.attributes.pos.y = y
        
        if rotation is None:
            prev_rotation = None
        else:
            prev_rotation = self.attributes.rotation
            self.attributes.rotation = rotation
        
        if transparency is None:
            prev_transparency = None
        else:
            prev_transparency = self.attributes.transparency
            self.attributes.transparency = transparency
        
        if frame is None:
            prev_frame = None
        else:
            prev_frame = self.attributes.animation.current_frame
            self.attributes.animation.current_frame = frame
        
        #check if the function has been called with any arguments at all
        if x is None and y is None and rotation is None and transparency is None and frame is None and not force:
            return None
        
        #check if only the positions were changed
        if ((rotation is None) ^ (rotation == prev_rotation)) and ((transparency is None) ^ (transparency == prev_transparency)) and ((frame is None) ^ (frame == prev_frame)) and ((image_set is None) ^ (image_set == prev_image_set)):
            for i in range(len(self.attributes.canvobjs)):
                self.canvas_controller.coords(self.get_object(self.attributes.image_set, i, self.attributes.rotation, self.attributes.transparency, self.attributes.animation.current_frame), self.attributes.pos.x, self.attributes.pos.y)
        else: #too many parameters were changed, replace all images
            #if previous is equal to current, set to current
            if prev_rotation is None:
                prev_rotation = self.attributes.rotation
            
            if prev_transparency is None:
                prev_transparency = self.attributes.transparency
            
            if prev_frame is None:
                prev_frame = self.attributes.animation.current_frame
            
            if prev_image_set is None:
                prev_image_set = self.attributes.image_set
            
            #move currently onscreen objects offscreen
            for i in range(len(self.attributes.canvobjs[prev_image_set])):
                self.canvas_controller.coords(self.get_object(prev_image_set, i, prev_rotation, prev_transparency, prev_frame), self.attributes.offscreen.x, self.attributes.offscreen.y)
            
            #move currently offscreen objects offscreen
            for i in range(len(self.attributes.canvobjs[self.attributes.image_set])):
                x = self.attributes.pos.x + self.get_offsets(i)[0]
                y = self.attributes.pos.y + self.get_offsets(i)[1]
                
                if self.attributes.snap.use:
                    x, y = self.snap_coords(x, y)
                
                self.canvas_controller.coords(self.get_object(self.attributes.image_set, i, self.attributes.rotation, self.attributes.transparency, self.attributes.animation.current_frame), x, y)
    
    def get_object(self, image_set, index, rotation, transparency, frame):
        if not self.attributes.uses_PIL:
            return self.attributes.canvobjs[image_set][index][0][0][frame]
        else:
            return self.attributes.canvobjs[image_set][index][int((rotation / 360) * self.attributes.rotation_steps)][int((transparency / 256) * self.attributes.transparency_steps)][frame]
    
    def get_offsets(self, i):
        real_index = int(i * (self.attributes.num_layers_total / self.attributes.num_layers))
        return self.attributes.offset.x * real_index, self.attributes.offset.y * real_index
    
    def destroy(self):
        for image_set in self.attributes.canvobjs:
            for layers in self.attributes.canvobjs[image_set]:
                for rotations in layers:
                    for transparencies in rotations:
                        for obj in transparencies:
                            self.canvas_controller.delete(obj)
        
        self.attributes.animation.cont = False
        self.attributes.running = False
    
    def _anim_player(self):
        if self.attributes.animation.sync:
            time.sleep(self.attributes.animation.delay - ((time.time() - self.canvas_controller.global_time) % self.attributes.animation.delay))
        
        while self.attributes.animation.cont:
            time.sleep(self.attributes.animation.delay + random.choice([0, self.attributes.animation.variation, 0 - self.attributes.animation.variation]))
            
            if self.attributes.anim_controller.playing_onetime and self.attributes.animation.frames - 1 == self.attributes.animation.current_frame:
                self.attributes.anim_controller.playing_onetime = False
                self.set(image_set = self.attributes.anim_controller.revert_to, frame = 0)
                self.attributes.anim_controller.revert_to = None
            
            self.increment(frame = 1)
    
    def snap_coords(self, x, y):
        x /= self.attributes.snap.x
        y /= self.attributes.snap.y
        
        x = math.floor(x)
        y = math.floor(y)
        
        x += 0.5
        y += 0.5
        
        x *= self.attributes.snap.x
        y *= self.attributes.snap.y
        
        return int(x), int(y)
    
    def play_anim(self, name, ignore_precedence = False):
        'Plays an animation once through. If the animation is already playing, it will reset to the start'
        if self.attributes.animation.is_higher(name, self.attributes.image_set) or not ignore_precedence:
            self.attributes.anim_controller.playing_onetime = True
            
            if not self.attributes.image_set == name:
                self.attributes.anim_controller.revert_to = self.attributes.image_set
            
            self.set(image_set = name, frame = 0)
    
    def loop_anim(self, name):
        'Loop an animation. This will force the selected animation'
        self.attributes.anim_controller.playing_onetime = False
        self.attributes.anim_controller.revert_to = self.attributes.image_set
        self.set(image_set = name, frame = 0)
    
    setpos = set

class AnimAttr:
    """
    Controls animation data
    """
    def __init__(self, attributes, profiles):
        self._attributes = attributes
        
        self._profiles = profiles['profiles']
        self._ranks = profiles['ranks']
        
        self.cont = True
        self.current_frame = 0
    
    def __getattr__(self, key):
        if key in ['frames', 'variation', 'delay']:
            return self._profiles[self._attributes.image_set][key]
        
        elif key == 'run_loop':
            return max([self._profiles[key]['frames'] for key in self._profiles]) > 1
        
        elif key == 'sync':
            if 'sync' in self._profiles[self._attributes.image_set]:
                return self._profiles[self._attributes.image_set]['sync']
            else:
                return False
        
        else:
            raise AttributeError('Attribute "{}" does not exist'.format(key))
    
    def __setattr__(self, key, value):
        if key in ['frames', 'variation', 'delay', 'sync']:
            self._profiles[self._attributes.image_set][key] = value
            
        else:
            self.__dict__[key] = value
    
    def is_higher(self, anim0, anim1):
        'Checks if anim0 takes precendence over anim1'
        if anim0 == anim1:
            return False
        elif anim0 in self._ranks and anim1 in self._ranks:
            return self._ranks.index(anim0) < self._ranks.index(anim1)

class Action:
    def __init__(self):
        self._actions = []
        self.frame = 0
        self.delay = 0
    
    def add(self, x, y, rotation, transparency, frame, force, image_set, increment):
        self._actions.append([x, y, rotation, transparency, frame, force, image_set, increment])
        print('x', x)
    
    def goto(self, index):
        return self.frame
    
    def current(self, autoscroll = True):
        frame = self.frame
        
        if autoscroll:
            self.frame = (self.frame + 1) % len(self)
        
        return self._actions[frame]
    
    def __len__(self):
        return len(self._actions)