import json
import os

import modules.bettercanvas

class Item(modules.bettercanvas.Model):
    def __init__(self, canvas_controller, item_name, map_path, layer):
        self.item_name = item_name
        
        with open(os.path.join(map_path, 'items', item_name), 'r') as file:
            item_cfg = json.load(file)
        
        super().__init__(canvas_controller, item_cfg['model'], map_path, layer)
        
        self.cfgs.item = item_cfg
        
        self.attributes.ticket = None