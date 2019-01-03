import tkinter as tk
import os
import sys
import json
import threading
import time
import random

class CanvasController:
    def __init__(self, canvas, game):
        self.canvas = canvas
        self.game = game
        
        self.layers = []
        self.reserved_args = ['layer']
        
        with open(os.path.join(sys.path[0], 'user', 'layers.json'), 'r') as file:
            self.layer_config = json.load(file) #load user defined order for screen items to be rendered in
        
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
            
            class animation:
                frames = 1
                delay = 1
                current_frame = 0
                variation = 0
                cont = True
                
            render_quality = 0 #0-3 - render quality as defined in the user's config
            image_set = None
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
        
        self.attributes.pos.x = self.attributes.offscreen.x
        self.attributes.pos.y = self.attributes.offscreen.y
        
        self.attributes.uses_PIL = self.cfgs.user['graphics']['PILrender']
        self.attributes.render_quality = self.cfgs.user['graphics']['model quality']
        self.attributes.rotation_steps = self.cfgs.model['rotations'][self.attributes.render_quality]
        
        if 'animation' in self.cfgs.model:
            self.attributes.animation.frames = self.cfgs.model['animation']['frames']
            self.attributes.animation.delay = self.cfgs.model['animation']['delay']
            self.attributes.animation.variation = self.cfgs.model['animation']['variation']
        
        if 'transparencies' in self.cfgs.model:
            self.attributes.transparency_steps = self.cfgs.model['transparencies'][self.attributes.render_quality]
        else:
            self.attributes.transparency_steps = 1
        
        if 'rotations' in self.cfgs.model:
            self.attributes.rotation_steps = self.cfgs.model['rotations'][self.attributes.render_quality]
        else:
            self.attributes.rotation_steps = 1
        
        if 'frames' in self.cfgs.model:
            self.attributes.animation_frames = self.cfgs.model['frames'][self.attributes.render_quality]
        else:
            self.attributes.animation_frames = 1
            
        #load PIL modules
        if self.attributes.uses_PIL:
            self.pillow.image = __import__('PIL.Image').Image
            self.pillow.image_chops = __import__('PIL.ImageChops').ImageChops
            self.pillow.photoimage = __import__('PIL.ImageTk').ImageTk.PhotoImage
        
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
                    tex_names[tex_set] = os.listdir(os.path.join(self.map_path, 'models', self.mdl_name, self.cfgs.model['textures'][tex_set]))
                else:
                    tex_names[tex_set] = [self.cfgs.model['textures'][tex_set]]
            else:
                tex_names[tex_set] = self.cfgs.model['textures'][tex_set]
            
            self.attributes.baseimages[tex_set] = []
            self.attributes.imageobjs[tex_set] = []
            self.attributes.canvobjs[tex_set] = []
        
        #write in default texture name
        self.attributes.image_set = self.cfgs.model['default textures']
        
        #load textures
        for tex_set in tex_names:
            for name in tex_names[tex_set]:
                if self.attributes.uses_PIL:
                    if self.attributes.animation.frames == 1:
                        self.attributes.baseimages[tex_set].append([self.pillow.image.open(os.path.join(self.map_path, 'models', self.mdl_name, name))])
                    else:
                        frames = []
                        for i in range(self.attributes.animation.frames):
                            frame = self.pillow.image.open(os.path.join(self.map_path, 'models', self.mdl_name, name))
                            frame.seek(i)
                            frames.append(frame)
                        
                        self.attributes.baseimages[tex_set].append(frames)
                else:
                    if self.attributes.animation.frames == 1:
                        self.attributes.baseimages[tex_set].append([tk.PhotoImage(file = os.path.join(self.map_path, 'models', self.mdl_name, name))])
                    else:
                        self.attributes.baseimages[tex_set].append([tk.PhotoImage(file = os.path.join(self.map_path, 'models', self.mdl_name, name), format = 'gif -index {}'.format(i)) for i in range(self.attributes.animation.frames)])
        
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
                    self.attributes.imageobjs[tex_set].append([[image]]) #no PIL means no transformations can be applied
        
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
        if self.attributes.animation.frames > 1:
            threading.Thread(target = self._anim_player, name = 'Model animation player', daemon = True).start()
        
        ## call set
        self.set(force = True)
    
    def apply_rotation(self, image_, angle):
        return image_.rotate(0 - angle)
    
    def apply_transparency(self, image_, transparency):
        try:
            return self.pillow.image_chops.multiply(image_, self.pillow.image.new('RGBA', image_.size, color = (255, 255, 255, int(transparency))))
        except ValueError:
            raise ValueError('Model texture doesn\'t have an alpha channel - make sure it uses 32 bit colour')
    
    def increment(self, x = None, y = None, rotation = None, transparency = None, frame = None, force = False):
        args = {}
        
        if not x == None:
            args['x'] = self.attributes.pos.x + x
            
        if not y == None:
            args['y'] = self.attributes.pos.y + y
            
        if not rotation == None:
            args['rotation'] = self.attributes.rotation + rotation
            
        if not transparency == None:
            args['transparency'] = self.attributes.transparency + transparency
        if not frame == None:
            args['frame'] = (self.attributes.animation.current_frame + frame) % self.attributes.animation.frames
        
        args['force'] = force
            
        self.set(**args)
    
    def set(self, x = None, y = None, rotation = None, transparency = None, frame = None, force = False, image_set = None):
        if image_set == None:
            prev_image_set = None
        else:
            prev_image_set = self.attributes.image_set
            self.attributes.image_set = image_set
    
        if x == None:
            prev_x = None
        else:
            prev_x = self.attributes.pos.x
            self.attributes.pos.x = x
        
        if y == None:
            prev_y = None
        else:
            prev_y = self.attributes.pos.y
            self.attributes.pos.y = y
        
        if rotation == None:
            prev_rotation = None
        else:
            prev_rotation = self.attributes.rotation
            self.attributes.rotation = rotation
        
        if transparency == None:
            prev_transparency = None
        else:
            prev_transparency = self.attributes.transparency
            self.attributes.transparency = transparency
        
        if frame == None:
            prev_frame = None
        else:
            prev_frame = self.attributes.animation.current_frame
            self.attributes.animation.current_frame = frame
        
        #check if the function has been called with any arguments at all
        if x == None and y == None and rotation == None and transparency == None and frame == None and not force:
            return None
        
        #check if only the positions were changed
        if ((rotation == None) ^ (rotation == prev_rotation)) and ((transparency == None) ^ (transparency == prev_transparency)) and ((frame == None) ^ (frame == prev_frame)) and ((image_set == None) ^ (image_set == prev_image_set)):
            for i in range(len(self.attributes.canvobjs)):
                self.canvas_controller.coords(self.get_object(self.attributes.image_set, i, self.attributes.rotation, self.attributes.transparency, self.attributes.animation.current_frame), self.attributes.pos.x, self.attributes.pos.y)
        else: #too many parameters were changed, replace all images
            #if previous is equal to current, set to current
            if prev_x == None:
                prev_x = self.attributes.pos.x
            
            if prev_y == None:
                prev_y = self.attributes.pos.y
            
            if prev_rotation == None:
                prev_rotation = self.attributes.rotation
            
            if prev_transparency == None:
                prev_transparency = self.attributes.transparency
            
            if prev_frame == None:
                prev_frame = self.attributes.animation.current_frame
            
            if prev_image_set == None:
                prev_image_set = self.attributes.image_set
            
            #move currently onscreen objects offscreen
            for i in range(len(self.attributes.canvobjs)):
                self.canvas_controller.coords(self.get_object(prev_image_set, i, prev_rotation, prev_transparency, prev_frame), self.attributes.offscreen.x, self.attributes.offscreen.y)
            
            #move currently offscreen objects offscreen
            for i in range(len(self.attributes.canvobjs)):
                self.canvas_controller.coords(self.get_object(self.attributes.image_set, i, self.attributes.rotation, self.attributes.transparency, self.attributes.animation.current_frame), self.attributes.pos.x, self.attributes.pos.y)
    
    def get_object(self, image_set, index, rotation, transparency, frame):
        return self.attributes.canvobjs[image_set][index][int((rotation / 360) * self.attributes.rotation_steps)][int((transparency / 256) * self.attributes.transparency_steps)][frame]
    
    def destroy(self):
        for image_set in self.attributes.canvobjs:
            for layers in self.attributes.canvobjs[image_set]:
                for rotations in layers:
                    for transparencies in rotations:
                        for obj in transparencies:
                            self.canvas_controller.delete(obj)
        
        self.attributes.animation.cont = False
    
    def _anim_player(self):
        while self.attributes.animation.cont:
            time.sleep(self.attributes.animation.delay + random.choice([0, self.attributes.animation.variation, 0 - self.attributes.animation.variation]))
            self.increment(frame = 1)
    
    setpos = set