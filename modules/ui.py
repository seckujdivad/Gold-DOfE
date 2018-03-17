import tkinter as tk
import threading
import time
import json
import os
import sys
import functools

class UI:
    def __init__(self):
        self.ready = {'tkthread': False}
        
        threading.Thread(target = self.tkthread).start() #start tkinter window in separate thread
        clearpass = False
        while not clearpass: #wait for all threads to check in before returning
            clearpass = True
            for name in self.ready:
                if not self.ready[name]:
                    clearpass = False
    
    def tkthread(self):
        self.root = tk.Tk() #create tkinter window
        
        class styling: #consistent styling tools
            @classmethod
            def get(self, font_size = 'medium', object_type = tk.Label, relief = 'default'):
                'Get styling for a specific type of widget'
                output = {}
                if object_type == tk.Button:
                    output['overrelief'] = self.reliefs[relief]['overrelief']
                output['relief'] = self.reliefs[relief]['relief']
                output['font'] = self.fonts[font_size]
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
                
            fonts = {'small': ('', 8),
                     'medium': ('', 15),
                     'large': ('', 25)} #default fonts
            reliefs = {'default': {'relief': tk.FLAT,
                                   'overrelief': tk.GROOVE}} #default reliefs
        self.styling = styling        
        
        class main: #store data to do with ui
            title = ''
            geometry = None
            current = None
            page_frame = tk.Frame(self.root)
            page_frame.pack(fill = tk.BOTH, expand = True)
        
        class uiobjects:
            class menu: #menu ui
                config = {'name': 'Menu'}
                
                @classmethod
                def on_load(self):
                    self.frame.pack(fill = tk.BOTH, expand = True)
                    with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
                        settingsdict = json.load(file)
                    text_ = f"Name: {settingsdict['user']['name']}, PIL rendering: {settingsdict['graphics']['PILrender']}"
                    self.label_userdata.config(text = text_)
                
                @classmethod
                def on_close(self):
                    self.frame.pack_forget()
                
                def load_settings(ui_object):
                    ui_object.load(ui_object.uiobjects.settings)
                    
                frame = tk.Frame(main.page_frame)
                label_title = tk.Label(frame, text = 'Working title', **self.styling.get(font_size = 'large', object_type = tk.Label))
                button_play = tk.Button(frame, text = 'New game', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_load = tk.Button(frame, text = 'Load save', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_connect = tk.Button(frame, text = 'Connect to a server', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_host = tk.Button(frame, text = 'Host a server', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_settings = tk.Button(frame, text = 'Change settings', command = functools.partial(load_settings, self), **self.styling.get(font_size = 'medium', object_type = tk.Button))
                label_userdata = tk.Label(frame, text = 'Loading...', **self.styling.get(font_size = 'small', object_type = tk.Label))
                
                label_title.grid(row = 0, column = 0, sticky = 'NESW')
                button_play.grid(row = 1, column = 0, sticky = 'NESW')
                button_load.grid(row = 2, column = 0, sticky = 'NESW')
                button_connect.grid(row = 3, column = 0, sticky = 'NESW')
                button_host.grid(row = 4, column = 0, sticky = 'NESW')
                button_settings.grid(row = 5, column = 0, sticky = 'NESW')
                label_userdata.grid(row = 6, column = 0, sticky = 'NESW')
                self.styling.set_weight(frame, 1, 7)
                
            class settings:
                config = {'name': 'Settings'}
                
                @classmethod
                def on_load(self):
                    self.frame.pack(fill = tk.BOTH, expand = True)
                    
                    with open(os.path.join(sys.path[0], 'user', 'config.json'), 'r') as file:
                        settingsdict = json.load(file)
                    if settingsdict['graphics']['PILrender']:
                        self.pilrender_flipswitch.on_option_press(0)
                    else:
                        self.pilrender_flipswitch.on_option_press(1)
                
                @classmethod
                def on_close(self):
                    self.frame.pack_forget()
                
                frame = tk.Frame(main.page_frame)
                
                '''username_label
                username_entry'''
                pilrender_label = tk.Label(frame, text = 'PIL rendering', **self.styling.get(font_size = 'medium', object_type = tk.Label))
                pilrender_flipswitch = TkFlipSwitch(frame, options = [{'text': 'On', 'command': print},
                                                                      {'text': 'Off', 'command': print}], **self.styling.get(font_size = 'medium', object_type = tk.Button))
                pilrender_label.grid(row = 0, column = 0, sticky = 'NESW')
                pilrender_flipswitch.grid(row = 0, column = 1, sticky = 'NESW')
                self.styling.set_weight(frame, 2, 1, dorows = False)
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
    
    def load(self, page, *pageargs, **pagekwargs):
        'Load a page'
        if (not self.uiobjects.main.current == None) and 'on_close' in dir(self.uiobjects.main.current):
            self.uiobjects.main.current.on_close() #close current page if one exists
        self.uiobjects.main.current = page #set loading page as current page
        if 'on_load' in dir(page):
            page.on_load(*pageargs, **pagekwargs) #run the load function for the page
        page.config['methods'].set_title(page.config["name"]) #set correct window title
    
    def set_title(self, title):
        self.uiobjects.main.title = title
        if self.uiobjects.main.current == None:
            self.uiobjects.root.title(self.uiobjects.main.title)
        elif self.uiobjects.main.current.config['methods'].current_title == None:
            self.uiobjects.root.title(self.uiobjects.main.title)
        else:
            self.uiobjects.main.current.config['methods'].set_title(self.uiobjects.main.current.config['methods'].current_title)
    
    def set_geometry(self, geometry):
        self.uiobjects.main.geometry = geometry
        self.root.geometry(self.uiobjects.main.geometry)

class PageMethods:
    def __init__(self, uiobject, page):
        self.uiobject = uiobject
        self.page = page
        
        self.current_title = None
    
    def set_title(self, title = None):
        if not title == None:
            self.current_title = title
        self.uiobject.root.title(f'{self.uiobject.uiobjects.main.title} - {self.current_title}')

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
        if not self.state == index:
            for button in self.buttons:
                button.config(state = tk.NORMAL, **self.filtered_args)
            self.buttons[index].config(relief = tk.FLAT, state = tk.DISABLED)
            self.state = index

            if run_binds:
                self.internal_args['options'][index]['command']()