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
    def __init__(self, canvas, game = None, layers = None, get_pil = False):
        self.canvas = canvas
        self.game = game
        
        self.winfo_width = self.canvas.winfo_width
        self.winfo_height = self.canvas.winfo_height
        self.find_overlapping = self.canvas.find_overlapping
        self.config = self.canvas.config
        self.bind = self.canvas.bind
        self.unbind = self.canvas.unbind
        self.unbind_all = self.canvas.unbind_all
        
        self.global_time = 0
        
        class pillow:
            image = None
            image_chops = None
            photoimage = None
            gifimage = None
        self.pillow = pillow
        
        if get_pil:
            self.pillow.image = __import__('PIL.Image').Image
            self.pillow.image_chops = __import__('PIL.ImageChops').ImageChops
            self.pillow.photoimage = __import__('PIL.ImageTk').ImageTk.PhotoImage
            self.pillow.gifimage = __import__('PIL.GifImagePlugin').GifImagePlugin.GifImageFile
        
        if layers is None:
            layers = ['user', 'layers.json']
        
        self.layers = []
        self.reserved_args = ['layer']
        
        with open(os.path.join(sys.path[0], *layers), 'r') as file:
            self.layer_config = json.load(file) #load user defined order for screen items to be rendered in
        
        self.reset_time()
        
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
        
        if obj_type == 'image': #call relevant canvas function
            obj = self.canvas.create_image(*coords, **filtered_args)
        elif obj_type == 'text':
            obj = self.canvas.create_text(*coords, **filtered_args)
        elif obj_type == 'window':
            obj = self.canvas.create_window(*coords, **filtered_args)
        elif obj_type == 'line':
            obj = self.canvas.create_line(*coords, **filtered_args)
        else:
            obj = self.canvas.create_rectangle(*coords, **filtered_args)
        
        self.layers[args['layer']].append({'object': obj})
        
        ## objects are always created on the top of their layer
        
        if not len(self.layers) == args['layer'] + 1: ## logic to find next highest tag and move just below it
            next_layer = None
            for i in range(len(self.layers) - 1, args['layer'], -1):
                if not len(self.layers[i]) == 0:
                    next_layer = i
            if next_layer is None:
                if len(self.layers) == 1:
                    lower_to = None
                    for i in range(args['layer']):
                        if not len(self.layers[i]) == 0:
                            lower_to = self.layers[i][len(self.layers[args['layer']]) - 1]
                    if not lower_to is None:
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
    
    def reset_time(self):
        self.set_time(time.time())
    
    def set_time(self, value):
        self.global_time = value

class Model:
    '''
    Model:
    Similar in function to canvas.create_image
    canvas_controller - CanvasController object to render to
    mdl_name - name of model in map files
    map_path - path to map files
    layer - string or int for canvas controller
    '''
    def __init__(self, canvas_controller, mdl_name, map_path, layer, autoplay_anims = True):
        self.mdl_name = mdl_name
        self.map_path = map_path
        self.canvas_controller = canvas_controller
        self.layer = layer
        
        ## make data structures
        class attributes:
            profile = None #e.g. idle
            profiles = {}
            profile_ranks = []
            
            class pos: #current coordinates
                x = 0
                y = 0
                
            rotation = 0 #current rotation (0-359)
            transparency = 0 #current transparency (0-255)
            
            interps_per_second = 0
            render_quality = 0 #0-3 - render quality as defined in the user's config
            uses_PIL = False
            force_grid = None #none means don't force, boolean will force to that value
            
            class anim_controller:
                playing_onetime = False
                revert_to = None
                sync = False
                revert_frame = None
                onetime_start = None
                
                frame = 0
                run_loop = False
            
            class snap:
                x = 1
                y = 1
            
            running = True
        self.attributes = attributes
        
        class cfgs:
            model = {}
            user = {}
            map = {}
        self.cfgs = cfgs
        
        class _set_queue_output:
            ticket = 0
            outputs = {}
        self._set_queue_output = _set_queue_output
        
        ## load data into structures
        #load configs
        with open(os.path.join(self.map_path, 'models', self.mdl_name, 'list.json'), 'r') as file:
            self.cfgs.model = json.load(file)
        
        with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
            self.cfgs.user = json.load(file)
        
        with open(os.path.join(self.map_path, 'list.json'), 'r') as file:
            self.cfgs.map = json.load(file)
        
        ### Load profile data
        for name in self.cfgs.model['profiles']:
            self.attributes.profiles[name] =  MdlProfile(self, self.cfgs.model['profiles'][name])
        
        self.attributes.profile_ranks = self.cfgs.model['ranks']
        self.attributes.profile = self.cfgs.model['default']
        
        self.attributes.uses_PIL = self.cfgs.user['graphics']['PILrender']
        self.attributes.render_quality = self.cfgs.user['graphics']['model quality']
        self.attributes.interps_per_second = self.cfgs.user['network']['interpolations per second']
        
        self.attributes.snap.x = self.cfgs.map['grid']['mult']['x']
        self.attributes.snap.y = self.cfgs.map['grid']['mult']['y']
        
        if self.cfgs.map['grid']['force']:
            self.attributes.force_grid = self.cfgs.map['grid']['force value']
        
        self.pillow = self.canvas_controller.pillow
        
        self.attributes.pos.x = self.attributes.profiles[self.attributes.profile].offscreen.x
        self.attributes.pos.y = self.attributes.profiles[self.attributes.profile].offscreen.y
        
        ## start animation player if necessary
        if self.attributes.anim_controller.run_loop and autoplay_anims:
            self.start_anims()
        
        # start interpolation thread
        self._set_pipe, pipe = mp.Pipe()
        threading.Thread(target = self._set_handler, args = [pipe], name = 'Interpolation handler', daemon = True).start()
        
        ## call set
        self.set(force = True)
    
    def increment(self, x = None, y = None, rotation = None, transparency = None, frame = None, force = False, timeframe = None, wait = False):
        return self.set(x, y, rotation, transparency, frame, force, None, True, timeframe, wait)
    
    def set(self, x = None, y = None, rotation = None, transparency = None, frame = None, force = False, image_set = None, increment = False, timeframe = None, wait = False):
        if ([x, y, rotation, transparency, frame, image_set] != [None] * 6) or force:
            action = {'items': [],
                      'delay': 0}
            
            if wait:
                action['ticket'] = self._set_queue_output.ticket
                self._set_queue_output.ticket += 1
            
            if timeframe is None:
                action['items'].append([x, y, rotation, transparency, frame, force, image_set, increment])
                
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
                    action['items'].append([xinc, yinc, rotationinc, transparencyinc, frame, force, image_set, True])
               
                if not increment:
                    action['items'].append([x, y, rotation, transparency, frame, force, image_set, False])
                
                action['delay'] = timeframe / slots
            
            try:
                self._set_pipe.send(action)
                
                if 'ticket' in action:
                    while not action['ticket'] in self._set_queue_output.outputs:
                        pass
                    
                    output = self._set_queue_output.outputs[action['ticket']]
                    self._set_queue_output.outputs.pop(action['ticket'])
                    return output
                
            except BrokenPipeError:
                self.attributes.running = False
    
    def _set_handler(self, pipe):
        current_action = None
        current_frame = 0
        last_output = None
        
        while self.attributes.running:
            if current_action is None:
                current_action = pipe.recv()
                current_frame = 0
                
            else:
                arg_slice = current_action['items'][current_frame][:7]
                
                if current_action['items'][current_frame][7]: #increment
                    last_output = self._increment(*arg_slice)
                else:
                    last_output = self._set(*arg_slice)
                
                current_frame += 1
                if current_frame == len(current_action['items']):
                    if 'ticket' in current_action:
                        self._set_queue_output.outputs[current_action['ticket']] = last_output
                    
                    current_action = None
                else:
                    time.sleep(current_action['delay'])
    
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
            frame = (frame + self.attributes.animation.current_frame) % self.attributes.animation.frames
        
        self._set(x, y, rotation, transparency, frame, force, image_set)
    
    def _set(self, x, y, rotation, transparency, frame, force, image_set):
        prev_image_set = self.attributes.image_set
        if image_set is not None:
            self.attributes.image_set = image_set

        prev_x = self.attributes.pos.x
        if x is not None:
            self.attributes.pos.x = x
            
        prev_y = self.attributes.pos.y
        if y is not None:
            self.attributes.pos.y = y
        
        prev_rotation = self.attributes.rotation
        if rotation is not None:
            self.attributes.rotation = rotation
            
        prev_transparency = self.attributes.transparency
        if transparency is not None:
            self.attributes.transparency = transparency
        
        prev_frame = self.attributes.animation.current_frame
        if frame is not None:
            self.attributes.animation.current_frame = frame
        
        #check if the function has been called with any arguments at all
        if x is None and y is None and rotation is None and transparency is None and frame is None and not force:
            return None
        
        #find what fields were changed
        if force:
            fields_changed = ['x', 'y', 'image set', 'rotation', 'transparency', 'frame']
        
        else:
            fields_changed = []
            if (prev_image_set is None and image_set is not None) or self.attributes.image_set != prev_image_set:
                fields_changed.append('image set')
            
            if (prev_x is None and x is not None) or self.snap_coords(self.attributes.pos.x, 0)[0] != self.snap_coords(prev_x, 0)[0]:
                fields_changed.append('x')
            
            if (prev_y is None and y is not None) or self.snap_coords(0, self.attributes.pos.y)[1] != self.snap_coords(0, prev_y)[1]:
                fields_changed.append('y')
                
            if (prev_rotation is None and rotation is not None) or int((self.attributes.rotation / 360) * self.attributes.rotation_steps) != int((prev_rotation / 360) * self.attributes.rotation_steps):
                fields_changed.append('rotation')
            
            if (prev_transparency is None and transparency is not None) or int((self.attributes.transparency / 256) * self.attributes.transparency_steps) != int((prev_transparency / 256) * self.attributes.transparency_steps):
                fields_changed.append('transparency')
            
            if prev_frame is None or self.attributes.animation.current_frame != prev_frame:
                fields_changed.append('frame')
        
        #check if only the positions were changed
        if len(fields_changed) > 0: #make sure at least one field was changed
            if False not in [key in ['x', 'y'] for key in fields_changed]:
                for i in range(len(self.attributes.canvobjs[self.attributes.image_set])):
                    xpos = self.attributes.pos.x + self.get_offsets(i)[0]
                    ypos = self.attributes.pos.y + self.get_offsets(i)[1]
                    
                    if self.attributes.snap.use:
                        xpos, ypos = self.snap_coords(xpos, ypos)
                    
                    self.canvas_controller.coords(self.get_object(self.attributes.image_set, i, self.attributes.rotation, self.attributes.transparency, self.attributes.animation.current_frame), xpos, ypos)
                    
            else: #too many parameters were changed, replace all images
                #move currently onscreen objects offscreen
                for i in range(len(self.attributes.canvobjs[prev_image_set])):
                    self.canvas_controller.coords(self.get_object(prev_image_set, i, prev_rotation, prev_transparency, prev_frame), self.attributes.offscreen.x, self.attributes.offscreen.y)
                    
                #move currently offscreen objects onscreen
                for i in range(len(self.attributes.canvobjs[self.attributes.image_set])):
                    x = self.attributes.pos.x + self.get_offsets(i)[0]
                    y = self.attributes.pos.y + self.get_offsets(i)[1]
                    
                    if self.attributes.snap.use:
                        x, y = self.snap_coords(x, y)
                    
                    self.canvas_controller.coords(self.get_object(self.attributes.image_set, i, self.attributes.rotation, self.attributes.transparency, self.attributes.anim_controller.frame), x, y)
    
    def get_object(self, profile, frame, layer, rotation, transparency):
        return self.attributes.profiles[profile].get_obj(frame, layer, rotation, transparency)
    
    def destroy(self):
        current_profile = self.attributes.profiles[self.attributes.profile]
        for layer in range(len(current_profile.canvobjs)):
            self.canvas_controller.coords(self.get_object(self.attributes.profile, self.attributes.anim_controller.frame, layer, self.attributes.rotation, self.attributes.transparency), current_profile.offscreen.x, current_profile.offscreen.y)
        
        for profile_name in self.attributes.profiles:
            self.attributes.profiles[profile_name].destroy()
        
        self.attributes.anim_controller.run_loop = False
        self.attributes.running = False
    
    def _anim_player(self):
        if self.attributes.profiles[self.attributes.profile].animation.sync:
            time.sleep((self.attributes.profiles[self.attributes.profile].animation.delay * self.attributes.profiles[self.attributes.profile].animation.frames) - ((time.time() - self.canvas_controller.global_time) % (self.attributes.profiles[self.attributes.profile].animation.delay * self.attributes.profiles[self.attributes.profile].animation.frames)))
        
        while self.attributes.anim_controller.run_loop:
            time.sleep(self.attributes.profiles[self.attributes.profile].animation.delay + random.choice([0, self.attributes.profiles[self.attributes.profile].animation.variation, 0 - self.attributes.profiles[self.attributes.profile].animation.variation]))
            
            if self.attributes.anim_controller.playing_onetime and self.attributes.profiles[self.attributes.profile].animation.frames - 1 == self.attributes.anim_controller.frame:
                time_elapsed = time.time() - self.attributes.anim_controller.onetime_start
                old_anim_delay = self.attributes.profiles[self.attributes.profile].animation.delay
                old_anim_length = self.attributes.profiles[self.attributes.profile].animation.frames
                
                self.set(image_set = self.attributes.anim_controller.revert_to, frame = 0, wait = True)
                
                new_elapsed = time.time() - self.attributes.anim_controller.onetime_start
                
                frames_elapsed = new_elapsed / self.attributes.profiles[self.attributes.profile].animation.delay
                
                self.set(frame = math.ceil(frames_elapsed) % self.attributes.profiles[self.attributes.profile].animation.frames)
                
                time.sleep((self.attributes.profiles[self.attributes.profile].animation.delay - (time.time() - self.attributes.anim_controller.onetime_start - (old_anim_delay * old_anim_length))) % self.attributes.profiles[self.attributes.profile].animation.delay)
                
                self.attributes.anim_controller.playing_onetime = False
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
        if self.compare_profiles(self.attributes.profile, name) or not ignore_precedence:
            self.attributes.anim_controller.playing_onetime = True
            self.attributes.anim_controller.onetime_start = time.time()
            
            if not self.attributes.profile == name:
                self.attributes.anim_controller.revert_to = self.attributes.profile
                self.attributes.anim_controller.revert_frame = self.attributes.anim_controller.frame
            
            self.set(image_set = name, frame = 0)
    
    def loop_anim(self, name):
        'Loop an animation. This will force the selected animation'
        self.attributes.anim_controller.playing_onetime = False
        self.attributes.anim_controller.revert_to = self.attributes.profile
        self.set(image_set = name, frame = 0)
    
    def start_anims(self):
        if self.attributes.anim_controller.run_loop:
            threading.Thread(target = self._anim_player, name = 'Model animation player', daemon = True).start()
    
    def compare_profiles(self, prof0, prof1):
        """Checks if profile 0 is takes precedence over profile 1"""
        
        if prof0 == prof1:
            return False
        
        elif prof0 in self.attributes.profile_ranks and prof1 in self.attributes.profile_ranks:
            return self.attributes.profile_ranks.index(prof0) < self.attributes.profile_ranks.index(prof1)
        
        elif prof0 in self.attributes.profile_ranks:
            return True
        
        elif prof1 in self.attributes.profile_ranks:
            return False
    
    setpos = set
    

class MdlProfile:
    def __init__(self, model, data = None):
        self.model = model
        self._cfg = data
        
        class offscreen:
            x = 0
            y = 0
        self.offscreen = offscreen
        
        class offset:
            x = 0
            y = 0
        self.offset = offset
        
        self.rotations = [1, 1, 1, 1]
        self.transparencies = [1, 1, 1, 1]
        self.layers = [1, 1, 1, 1]
        
        self.num_existing_layers = 0
        self.use_grid = False
        
        class animation:
            frames = 1
            delay = 0
            variation = 0
            sync = False
        self.animation = animation
        
        self.imgs = []
        self.transformed_imgs = []
        self.canvobjs = []
        
        if data is not None:
            self.load(data)
    
    def load(self, profile):
        self._cfg = profile
        
        #unpack data
        self.offscreen.x = self._cfg['offscreen'][0]
        self.offscreen.y = self._cfg['offscreen'][1]
        
        self.offset.x = self._cfg['offset'][0]
        self.offset.y = self._cfg['offset'][1]
        
        self.rotations = self._cfg['rotations']
        self.transparencies = self._cfg['transparencies']
        self.use_grid = self._cfg['use grid']
        self.layers = self._cfg['layers']
        
        self.animation.frames = self._cfg['animation']['frames']
        self.animation.delay = self._cfg['animation']['delay']
        self.animation.variation = self._cfg['animation']['variation']
        self.animation.sync = self._cfg['animation']['sync']
        
        if not self.model.attributes.uses_pil and 'no PIL textures' in self._cfg:
            self._cfg['textures'] = self._cfg['no PIL textures']
        
        #load textures
        ##find the names of the textures
        img_names = []
        if type(self._cfg['textures']) == str:
            img_names = [[os.path.join(frame, name) for name in os.listdir(os.path.join(self.model.map_path, 'models', self.model.mdl_name, frame)) if os.path.isfile(os.path.join(self.model.map_path, 'models', self.model.mdl_name, frame, name))] for frame in os.listdir(os.path.join(self.model.map_path, 'models', self.model.mdl_name, self._cfg['textures']))] #unpack a two-level tree of animations then layers
        else:
            for frame in self._cfg['textures']:
                if type(frame) == str:
                    if frame.endswith('.gif'):
                        img_names.append(frame)
                    else:
                        img_names.append([name for name in os.listdir(os.path.join(self.model.map_path, 'models', self.model.mdl_name, frame)) if os.path.isfile(os.path.join(self.model.map_path, 'models', self.model.mdl_name, frame, name))])
            
                else:
                    img_names.append(frame)
        
        ##load the textures into memory
        if type(img_names[0]) == str: #list of gifs - load with flipped dimensions
            layer_indexes = [i for i in range(len(img_names)) if float(i / math.ceil(len(img_names) / self.layers[self.model.attributes.render_quality])).is_integer()]
            self.num_existing_layers = len(img_names)
            
            self.imgs = [[] for i in range(self.animation.frames)]
            
            for layer in img_names:
                if img_names.index(layer) in layer_indexes:
                    for i in range(self.animation.frames):
                        if self.model.attributes.uses_pil:
                            tex = self.model.pillow.gifimage(os.path.join(self.model.map_path, 'models', self.model.mdl_name, layer))
                            tex.seek(i)
                            self.imgs[i].append(tex)
                        
                        else:
                            self.imgs[i].append(tk.PhotoImage(file = os.path.join(self.model.map_path, 'models', self.model.mdl_name, layer), format = 'gif -index {}'.format(i)))
            
        else:
            layer_indexes = [i for i in range(len(img_names[0])) if float(i / math.ceil(len(img_names[0]) / self.layers[self.model.attributes.render_quality])).is_integer()]
            self.num_existing_layers = len(img_names[0])
            
            for frame in img_names:
                current_slot = []
                for name in frame:
                    if frame.index(name) in layer_indexes:
                        if self.model.attributes.uses_pil:
                            current_slot.append(self.model.pillow.image.open(os.path.join(self.model.map_path, 'models', self.model.mdl_name, name)))
                        
                        else:
                            current_slot.append(tk.PhotoImage(file = os.path.join(self.model.map_path, 'models', self.model.mdl_name, name)))
                self.imgs.append(current_slot)
        
        ##apply operations to textures
        if self.model.attributes.uses_pil:
            rotation_values = [value / (self.rotations[self.model.attributes.render_quality] / 360) - 1 for value in range(1, self.rotations[self.model.attributes.render_quality] + 1, 1)]
            transparency_values = [value / (self.transparencies[self.model.attributes.render_quality] / 256) - 1 for value in range(1, self.transparencies[self.model.attributes.render_quality] + 1, 1)]
        else:
            rotation_values = [0]
            transparency_values = [255]
        
        for frame in self.imgs:
            this_frame = []
            for layer in frame:
                this_layer = []
                for rotation in rotation_values:
                    this_rotation = []
                    for transparency in transparency_values:
                        this_rotation.append(self.apply_to(layer, rotation, transparency))
                    this_layer.append(this_rotation)
                this_frame.append(this_layer)
            self.transformed_imgs.append(this_frame)
            
            if len(this_frame) > 1:
                self.model.attributes.anim_controller.run_loop = True
        
        #make canvas objects
        for frame in self.transformed_imgs:
            new_layers = []
            for layer in frame:
                new_rotations = []
                for rotation in layer:
                    new_transparencies = []
                    for image_ in rotation:
                        new_transparencies.append(self.model.canvas_controller.create_image(self.offscreen.x, self.offscreen.y, image = image_, layer = self.model.layer))
                    new_rotations.append(new_transparencies)
                new_layers.append(new_rotations)
            self.canvobjs.append(new_layers)
    
    def apply_to(self, image, rotation, transparency):
        if not rotation == 0:
            image.rotate(0 - rotation)
        
        if not transparency == 255:
            try:
                return self.model.pillow.image_chops.multiply(image, self.model.pillow.image.new('RGBA', image.size, color = (255, 255, 255, int(transparency))))
            except ValueError:
                raise ValueError('Model texture doesn\'t have an alpha channel - make sure it uses 32 bit colour')
    
    def get_obj(self, frame, layer, rotation, transparency):
        if self.model.attributes.uses_pil:
            return self.canvobjs[frame][layer][int(rotation / 360) * self.rotations[self.model.attributes.render_quality]][int(transparency / 360) * self.transparencies[self.model.attributes.render_quality]]
        else:
            return self.canvobjs[frame][layer][0][0]
    
    def get_offset(self, layer):
        real_index = int(layer * (self.num_existing_layers / len(self.canvobjs[0])))
        return self.offset.x * real_index, self.offset.y * real_index
    
    def destroy(self):
        for frame in self.canvobjs:
            for layer in frame:
                for rotation in layer:
                    for canvobj in rotation:
                        self.model.canvas_controller.delete(canvobj)