from importlib import util
import tkinter as tk
import threading
import time
import json
import os
import sys
import functools
import typing

import modules.modloader

class UI:
    def __init__(self, autostart = True):
        self.ready = {'tkthread': False}
        self.triggers = {}
        
        self.root = None
        
        class styling: #consistent styling tools
            @classmethod
            def get(cls, font_size = 'medium', object_type: typing.Union[typing.Type[tk.Label],
                                                                         typing.Type[tk.Button],
                                                                         typing.Type[tk.Canvas],
                                                                         typing.Type[tk.Scrollbar],
                                                                         typing.Type[tk.Frame],
                                                                         typing.Type[tk.Text],
                                                                         typing.Type[tk.Entry],
                                                                         typing.Type[tk.Spinbox],
                                                                         typing.Type[tk.Listbox]] = tk.Label, relief = 'default', fonts = 'default') -> dict:
                'Get styling for a specific type of widget'
                output = {}
                if object_type == tk.Button:
                    output['overrelief'] = cls.reliefs[relief]['overrelief']
                
                output['relief'] = cls.reliefs[relief]['relief']
            
                if not object_type in [tk.Canvas, tk.Scrollbar, tk.Frame]:
                    output['font'] = cls.fonts[fonts][font_size]
                
                return output
            
            @classmethod
            def set_weight(cls, frame, width, height, weight_ = 1, dorows = True, docolumns = True):
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
        
        class pages:
            title = ''
            base_title = ''
            top_title = ''
            window_geometry = None
            current = None
            uninitialised = []
            pages = {}
            page_frame = None
        self.pages = pages
        
        self.mod_loader = modules.modloader.ModLoader(os.path.join(sys.path[0], 'ui'))
        
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
        
        self.pages.page_frame = tk.Frame(self.root)
        self.pages.page_frame.pack(fill = tk.BOTH, expand = True)
        
        self.pages.uninitialised = self.mod_loader.load('UI')
        
        for cls in self.pages.uninitialised:
            cls = cls(tk.Frame(self.pages.page_frame), self)
            
            if cls.internal_name is not None:
                self.pages.pages[cls.internal_name] = cls
        
        self.ready['tkthread'] = True
        self.root.mainloop()
        
        self.call_trigger('window closed')
    
    def load(self, page):
        'Load a page'
        if self.pages.current is not None:
            self.pages.pages[self.pages.current].on_close()
        
        if page in self.pages.pages:
            self.pages.current = page
            self.pages.pages[self.pages.current].on_load()
            self.set_title(self.pages.pages[self.pages.current].name)
        
        else:
            print('Page {} has not been loaded'.format(page))
    
    def set_title(self, title):
        if title is None:
            self.pages.top_title = ''
            title = self.pages.base_title
        
        else:
            self.pages.top_title = title
            title = '{} - {}'.format(self.pages.base_title, self.pages.top_title)
        
        self.pages.title = title
        self.root.title(self.pages.title)
    
    def set_base_title(self, base_title):
        self.pages.base_title = base_title
        self.set_title(self.pages.top_title)
    
    def set_geometry(self, geometry):
        self.pages.window_geometry = geometry
        self.root.geometry(self.pages.window_geometry)
    
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
                    return function()

                else:
                    return function(*args)
                    
        else:
            raise ValueError('Trigger "{}" hasn\'t been registered'.format(string))


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
        self.frame = frame
        self._ui = ui

        self.name = None
        self.internal_name = None
        self._active = False
        
        self._call_trigger = self._ui.call_trigger
        self._set_trigger = self._ui.set_trigger
        self._clear_triggers = self._ui.clear_triggers

        self._styling = self._ui.styling
        self._load_page = self._ui.load
        
        class _elements:
            pass
        self._elements = _elements
        
        class _vars:
            pass
        self._vars = _vars
        
    def on_load(self):
        self._active = True
        self.frame.pack(fill = tk.BOTH, expand = True)
        self._on_load()
    
    def on_close(self):
        self._active = False
        self._on_close()
        self.frame.pack_forget()
    
    def _on_load(self):
        'Empty method. To be overwritten by the inheriting class'
        pass
    
    def _on_close(self):
        'Empty method. To be overwritten by the inheriting class'
        pass