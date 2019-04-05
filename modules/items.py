import json
import os
import sys
import math

import modules.bettercanvas


class Item(modules.bettercanvas.Model):
    def __init__(self, canvas_controller, item_name, map_path, layer):
        self.item_name = item_name
        
        with open(os.path.join(map_path, 'items', item_name), 'r') as file:
            item_cfg = json.load(file)
        
        super().__init__(canvas_controller, item_cfg['model'], map_path, layer)
        
        self.cfgs.item = item_cfg
        
        self.attributes.ticket = None


class ItemScript:
    internal_name = ''
    
    def __init__(self, name, server):
        self.server = server
        
        class attributes:
            name = None
            display_name = None
            first_tick = True
            ticket = None
            tickrate = 0
            creator = None
            dist_travelled = 0
            max_dist = None
            
            class damage:
                last = None
            
            class pos:
                x = 0
                y = 0
            
            rotation = 0
            
            class velocity:
                x = 0
                y = 0
                delay = 0.05
            
            class hitbox:
                shape = None
                radius = 0
        self.attributes = attributes
        
        class cfgs:
            current_map = {}
            item = {}
        self.cfgs = cfgs
        
        with open(os.path.join(sys.path[0], 'server', 'maps', self.server.serverdata.map, 'items', name), 'r') as file:
            self.cfgs.item = json.load(file)
       
        self.attributes.name = name
        self.cfgs.current_map = self.server.serverdata.mapdata
        self.attributes.tickrate = self.server.serverdata.tickrate
        
        if self.cfgs.item['hitbox']['type'] == 'circular':
            self.attributes.hitbox.shape = 'circle'
            self.attributes.hitbox.radius = self.cfgs.item['hitbox']['radius']
    
    def inside_map(self):
        if self.attributes.hitbox.shape == 'circle':
            clips_x_high = self.attributes.pos.x > self.cfgs.current_map['geometry'][0] + self.attributes.hitbox.radius
            clips_x_low = self.attributes.pos.x < 0 - self.attributes.hitbox.radius
            clips_y_high = self.attributes.pos.y > self.cfgs.current_map['geometry'][1] + self.attributes.hitbox.radius
            clips_y_low = self.attributes.pos.y < 0 - self.attributes.hitbox.radius

            return not (clips_x_high or clips_x_low or clips_y_high or clips_y_low)
        
        else:
            raise ValueError('Hitbox type "{}" not recognised'.format(self.attributes.hitbox.shape))

    def tick(self):
        result = self._tick()
        self.attributes.first_tick = False
        
        if type(result) == dict:
            if len(result) == 0:
                result = None
            else:
                result['ticket'] = self.attributes.ticket
                
                if result['type'] == 'add':
                    result['file name'] = self.attributes.name
        
            return result

    def _tick(self):
        return {}
    
    def touching_player(self, client):
        if self.attributes.hitbox.shape == 'circle':
            if self._dist_between(client.metadata.pos.x, client.metadata.pos.y, self.attributes.pos.x, self.attributes.pos.y) <= self.attributes.hitbox.radius:
                return True
        return False
    
    def _dist_between(self, x0, y0, x1, y1):
        return math.hypot(x1 - x0, y1 - y0)
    
    def set_velocity(self, vel):
        self.attributes.velocity.x = vel * math.cos(math.radians(self.attributes.rotation))
        self.attributes.velocity.y = vel * math.sin(math.radians(self.attributes.rotation))