import tkinter as tk
import os
import json
import sys

import modules.ui

class UIMenu(modules.ui.UIObject):
    def __init__(self, frame, ui):
        super().__init__(frame, ui)
        
        self.name = 'Menu'
        self.internal_name = 'menu'
        
        #generate
        self._elements.label_title = tk.Label(self.frame, text = 'Hydrophobes', **self._styling.get(font_size = 'large', object_type = tk.Label))
        self._elements.button_editor = tk.Button(self.frame, text = 'Map editor', **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.button_connect = tk.Button(self.frame, text = 'Connect to a server', **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.button_host = tk.Button(self.frame, text = 'Host a server', **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.button_settings = tk.Button(self.frame, text = 'Change client settings', **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.button_server_settings = tk.Button(self.frame, text = 'Change server settings', **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.button_quit = tk.Button(self.frame, text = 'Quit', **self._styling.get(font_size = 'medium', object_type = tk.Button))
        self._elements.label_userdata = tk.Label(self.frame, text = 'Loading...', **self._styling.get(font_size = 'small', object_type = tk.Label))
                
        self._elements.label_title.grid(row = 0, column = 0, sticky = 'NESW')
        self._elements.button_editor.grid(row = 1, column = 0, sticky = 'NESW')
        self._elements.button_connect.grid(row = 2, column = 0, sticky = 'NESW')
        self._elements.button_host.grid(row = 3, column = 0, sticky = 'NESW')
        self._elements.button_settings.grid(row = 4, column = 0, sticky = 'NESW')
        self._elements.button_server_settings.grid(row = 5, column = 0, sticky = 'NESW')
        self._elements.button_quit.grid(row = 6, column = 0, sticky = 'NESW')
        self._elements.label_userdata.grid(row = 7, column = 0, sticky = 'NESW')
        self._styling.set_weight(self.frame, 1, 8)
        
    def _on_load(self):
        with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
            settingsdict = json.load(file)
            
        pilrender_msg = settingsdict['graphics']['PILrender']
        if not pilrender_msg:
            pilrender_msg = 'False (WARNING! - disables sprite rotation)'
            
        text_ = 'Name: {}, PIL rendering: {} \nGo to settings to make sure all packages have been installed'.format(settingsdict['user']['name'], pilrender_msg)
        self._elements.label_userdata.config(text = text_)
        
        self._elements.button_editor.config(command = lambda: self._load_page('editor'))
        self._elements.button_connect.config(command = lambda: self._load_page('server connect'))
        self._elements.button_host.config(command = lambda: self._load_page('server host'))
        self._elements.button_settings.config(command = lambda: self._load_page('client settings'))
        self._elements.button_server_settings.config(command = lambda: self._load_page('server settings'))
        self._elements.button_quit.config(command = lambda: self._call_trigger('quit'))