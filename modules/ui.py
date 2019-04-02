from tkinter import messagebox
from typing import Type, Union
import tkinter as tk
import threading
import time
import json
import os
import sys
import functools
import shutil

class UI:
    def __init__(self, autostart = True):
        self.ready = {'tkthread': False}
        self.triggers = {}
        
        self.root = None
        
        if autostart:
            threading.Thread(target = self.tkthread).start() #start tkinter window in separate thread
            self.wait_for_checkin()
    
    def wait_for_checkin(self):
        clearpass = False
        while not clearpass:  # wait for all threads to check in before returning
            time.sleep(0.05)
            clearpass = True
            for name in self.ready:
                if not self.ready[name]:
                    clearpass = False
    
    def tkthread(self):
        self.root = tk.Tk() #create tkinter window
        
        class styling: #consistent styling tools
            @classmethod
            def get(self, font_size = 'medium', object_type: Union[Type[tk.Label],
                                                                   Type[tk.Button],
                                                                   Type[tk.Canvas],
                                                                   Type[tk.Scrollbar],
                                                                   Type[tk.Frame],
                                                                   Type[tk.Text],
                                                                   Type[tk.Entry],
                                                                   Type[tk.Spinbox],
                                                                   Type[tk.Listbox]] = tk.Label, relief = 'default', fonts = 'default') -> dict:
                'Get styling for a specific type of widget'
                output = {}
                if object_type == tk.Button:
                    output['overrelief'] = self.reliefs[relief]['overrelief']
                
                output['relief'] = self.reliefs[relief]['relief']
            
                if not object_type in [tk.Canvas, tk.Scrollbar]:
                    output['font'] = self.fonts[fonts][font_size]
                
                return output
            
            @classmethod
            def set_weight(self, frame, width, height, weight_ = 1, dorows = True, docolumns = True):
                'Set uniform weighting across a frame'
                for cheight in range(height):
                    if dorows:
                        frame.rowconfigure(cheight, weight = weight_)
                    for cwidth in range(width):
                        if docolumns:
                            frame.columnconfigure(cwidth, weight = weight_)
            fonts = {}
            reliefs = {}
            with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
                settingsdata = json.load(file)
            for style_type in settingsdata['styling']:
                fonts[style_type] = settingsdata['styling'][style_type]['fonts']
                reliefs[style_type] = settingsdata['styling'][style_type]['reliefs']
        self.styling = styling        
        
        class main: #store data to do with ui
            title = ''
            geometry = None
            current = None
            page_frame = tk.Frame(self.root)
            page_frame.pack(fill = tk.BOTH, expand = True)
            
            class editor:
                config = {'name': 'Editor'}
                
                @classmethod
                def on_load(self):
                    self.frame.pack(fill = tk.BOTH, expand = True)
                    self.config['methods'].uiobject.call_trigger('start editor', [self.frame, self.config['methods']])
                
                @classmethod
                def on_close(self):
                    self.config['methods'].uiobject.call_trigger('close editor', [])
                    self.frame.pack_forget()
                
                frame = tk.Frame(main.page_frame)
            
            class server_settings:
                config = {'name': 'Server settings'}
                
                @classmethod
                def on_load(self):
                    self.button_close.config(command = self.choose_accept)
                    self.button_cancel.config(command = self.choose_cancel)
                    self.button_reset_default.config(command = self.choose_reset_default)
                    
                    self.frame.pack(fill = tk.BOTH, expand = True)
                    
                    self.fetch_settings(os.path.join(sys.path[0], 'server', 'config.json'))
                
                @classmethod
                def on_close(self):
                    self.frame.pack_forget()
                
                @classmethod
                def choose_cancel(self):
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.menu)
                
                @classmethod
                def choose_accept(self):
                    self.push_settings(os.path.join(sys.path[0], 'server', 'config.json'))
                       
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.menu)
                
                @classmethod
                def choose_reset_default(self):
                    self.fetch_settings(os.path.join(sys.path[0], 'server', 'default_config.json'))
                
                @classmethod
                def push_settings(self, path):
                    with open(path, 'r') as file:
                        settingsdict = json.load(file)
                    
                    settingsdict['network']['accurate hit detection'] = bool(self.hitbox_precision_flipswitch.state)
                    settingsdict['network']['tickrate'] = int(self.vars.tickrate.get())
                    settingsdict['network']['port'] = int(self.vars.port.get())
                    
                    with open(os.path.join(sys.path[0], 'server', 'config.json'), 'w') as file:
                       json.dump(settingsdict, file, sort_keys=True, indent='\t')
                
                @classmethod
                def fetch_settings(self, path):
                    with open(path, 'r') as file:
                        settingsdict = json.load(file)
                    
                    self.hitbox_precision_flipswitch.on_option_press(settingsdict['network']['accurate hit detection'])
                    self.vars.tickrate.set(settingsdict['network']['tickrate'])
                    self.vars.port.set(settingsdict['network']['port'])
                    
                #variables
                class vars:
                    tickrate = tk.IntVar()
                    port = tk.IntVar()
                self.vars = vars
                
                frame = tk.Frame(main.page_frame)
                
                settings_frame = tk.Frame(frame)
                
                widget_row = 0
                
                #network
                cat_network = tk.Label(settings_frame, text = 'Network', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                hitbox_precision_label = tk.Label(settings_frame, text = 'Hitbox precision', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                hitbox_precision_flipswitch = TkFlipSwitch(settings_frame, options = [{'text': 'Low (stock python)'},
                                                                                      {'text': 'High (requires numpy)'}], **self.styling.get(font_size = 'medium', object_type = tk.Button))
                tickrate_label = tk.Label(settings_frame, text = 'Tickrate', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                tickrate_spinbox = tk.Spinbox(settings_frame, from_ = 1, to = 1024, textvariable = self.vars.tickrate, **self.styling.get(font_size = 'medium', object_type = tk.Spinbox))
                port_label = tk.Label(settings_frame, text = 'Port', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                port_spinbox = tk.Spinbox(settings_frame, from_ = 1024, to = 49151, textvariable = self.vars.port, **self.styling.get(font_size = 'medium', object_type = tk.Spinbox))
                
                cat_network.grid(row = widget_row, column = 0, columnspan = 2, sticky = 'NESW')
                hitbox_precision_label.grid(row = widget_row + 1, column = 0, sticky = 'NESW')
                hitbox_precision_flipswitch.grid(row = widget_row + 1, column = 1, sticky = 'NESW')
                tickrate_label.grid(row = widget_row + 2, column = 0, sticky = 'NESW')
                tickrate_spinbox.grid(row = widget_row + 2, column = 1, sticky = 'NESW')
                port_label.grid(row = widget_row + 3, column = 0, sticky = 'NESW')
                port_spinbox.grid(row = widget_row + 3, column = 1, sticky = 'NESW')
                
                widget_row += 4
                
                #functional buttons
                button_close = tk.Button(frame, text = 'Accept', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_cancel = tk.Button(frame, text = 'Cancel', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_reset_default = tk.Button(frame, text = 'Reset to default', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                
                settings_frame.grid(row = 0, column = 0, columnspan = 3, sticky = 'NESW')
                button_close.grid(row = 2, column = 0, sticky = 'NESW')
                button_cancel.grid(row = 2, column = 1, sticky = 'NESW')
                button_reset_default.grid(row = 2, column = 2, sticky = 'NESW')
                
                #set weights
                self.styling.set_weight(settings_frame, 2, widget_row, dorows = False)
                frame.columnconfigure(0, weight = 1)
                frame.columnconfigure(1, weight = 1)
                frame.columnconfigure(2, weight = 1)
                frame.rowconfigure(0, weight = 1)
            
            class server_host:
                config = {'name': 'Hosting server'}
                
                @classmethod
                def on_load(self):
                    self.frame.pack(fill = tk.BOTH, expand = True)
                    self.config['methods'].uiobject.call_trigger('host server', [self.console_frame])
                    
                    self.button_exit.config(command = self.choose_exit)
                
                @classmethod
                def on_close(self):
                    self.config['methods'].uiobject.call_trigger('close server', [])
                    self.frame.pack_forget()
                
                @classmethod
                def choose_exit(self):
                    self.config['methods'].uiobject.load(self.config['methods'].uiobject.uiobjects.menu)
                
                frame = tk.Frame(main.page_frame)
                
                console_frame = tk.Frame(frame)
                button_exit = tk.Button(frame, text = 'Exit', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                
                console_frame.grid(column = 0, row = 0, sticky = 'NESW')
                button_exit.grid(column = 0, row = 1, sticky = 'NESW')
                
                self.styling.set_weight(frame, 1, 2, dorows = False)
                frame.rowconfigure(0, weight = 1)
            
            class settings_debug:
                config = {'name': 'Settings - Debug'}
                
                @classmethod
                def on_load(self):
                    self.frame.pack(fill = tk.BOTH, expand = True)
                
                @classmethod
                def on_close(self):
                    self.frame.pack_forget()
                
                frame = tk.Frame(main.page_frame)
                
        uiobjects.main = main
        self.uiobjects = uiobjects
        
        #apply additional setup to pages
        for itemname in dir(self.uiobjects):
            ismagicvariable = itemname.startswith('__') and itemname.endswith('__')
            isspecialcase = itemname in ['main']
            if not (ismagicvariable or isspecialcase):
                item = self.uiobjects.__getattribute__(self.uiobjects, itemname) #get class from name
                if not 'config' in dir(item):
                    item.config = {'name': itemname}
                item.config['methods'] = PageMethods(self, item)
        
        self.ready['tkthread'] = True
        self.root.mainloop()
        
        self.call_trigger('window closed')
    
    def load(self, page, *pageargs, **pagekwargs):
        'Load a page'
        if self.uiobjects.main.current is not None and 'on_close' in dir(self.uiobjects.main.current):
            self.uiobjects.main.current.on_close() #close current page if one exists
        self.uiobjects.main.current = page #set loading page as current page
        if 'on_load' in dir(page):
            page.on_load(*pageargs, **pagekwargs) #run the load function for the page
        page.config['methods'].set_title(page.config["name"]) #set correct window title
    
    def set_title(self, title):
        self.uiobjects.main.title = title
        if self.uiobjects.main.current is None:
            self.uiobjects.root.title(self.uiobjects.main.title)
            
        elif self.uiobjects.main.current.config['methods'].current_title is None:
            self.uiobjects.root.title(self.uiobjects.main.title)
            
        else:
            self.uiobjects.main.current.config['methods'].set_title(self.uiobjects.main.current.config['methods'].current_title)
    
    def set_geometry(self, geometry):
        self.uiobjects.main.geometry = geometry
        self.root.geometry(self.uiobjects.main.geometry)
    
    def set_trigger(self, string, function):
        if string in self.triggers:
            self.triggers[string].append(function)
        else:
            self.triggers[string] = [function]
    
    def clear_triggers(self, string):
        if string in self.triggers:
            self.triggers.pop(string)
    
    def call_trigger(self, string, args = None):
        if string in self.triggers:
            for function in self.triggers[string]:
                if args is None:
                    function()
                else:
                    function(*args)
        else:
            raise ValueError('Trigger "{}" hasn\'t been registered'.format(string))

class PageMethods:
    def __init__(self, uiobject, page):
        self.uiobject = uiobject
        self.page = page
        
        self.current_title = None
    
    def set_title(self, title = None):
        if title is not None:
            self.current_title = title
        self.uiobject.root.title('{} - {}'.format(self.uiobject.uiobjects.main.title, self.current_title))

class TkFlipSwitch:
    def __init__(self, container, **kwargs):
        self.container = container

        self.required_internal_args = ['options']
        self.state = 0
        
        self.filtered_args = {}
        self.internal_args = {}
        for key in kwargs:
            if key in self.required_internal_args:
                self.internal_args[key] = kwargs[key]
            else:
                self.filtered_args[key] = kwargs[key]

        for arg in self.required_internal_args:
            if not arg in self.internal_args:
                raise TypeError('Missing keyword argument "{}"'.format(arg))

        self.frame = tk.Frame(container)
        self.buttons = []
        for option in self.internal_args['options']:
            self.buttons.append(tk.Button(self.frame, text = option['text'], command = functools.partial(self.on_option_press, len(self.buttons)), **self.filtered_args))

        self.on_option_press(self.state, run_binds = False)

        for i in range(len(self.buttons)):
            self.buttons[i].grid(column = i, row = 0, sticky = 'NESW')
            self.frame.columnconfigure(i, weight = 1)
        self.frame.rowconfigure(0, weight = 1)

        self.pack = self.frame.pack
        self.grid = self.frame.grid
        self.destroy = self.frame.destroy
        self.pack_forget = self.frame.pack_forget

    def on_option_press(self, index, run_binds = True):
        for button in self.buttons:
            button.config(state = tk.NORMAL, **self.filtered_args)
        self.buttons[index].config(relief = tk.FLAT, state = tk.DISABLED)
        self.state = index
        
        if run_binds and 'command' in self.internal_args['options'][index] and (not self.internal_args['options'][index]['command'] is None):
            self.internal_args['options'][index]['command']()

class UIObject:
    def __init__(self, frame, ui):
        self.name = ''
        self.internal_name = ''
        self.frame = frame
        self._ui = ui
        
        self._call_trigger = self._ui.call_trigger
        self._styling = self._ui.styling
        self._load_page = self._ui.load
        
        class _elements:
            pass
        self._elements = _elements
        
        class _vars:
            pass
        self._vars = _vars
        
    def on_load(self):
        self.frame.pack(fill = tk.BOTH, expand = True)
        self._on_load()
    
    def on_close(self):
        self._on_close()
        self.frame.pack_forget()
    
    def _on_load(self):
        'Empty method. To be overwritten by the inheriting class'
        pass
    
    def _on_close(self):
        'Empty method. To be overwritten by the inheriting class'
        pass