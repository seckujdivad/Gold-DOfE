import tkinter as tk
import threading
import time

class UI:
    def __init__(self):
        self.ready = {'tkthread': False}
        
        threading.Thread(target = self.tkthread).start() #start tkinter window in separate thread
        clearpass = False
        while not clearpass:
            clearpass = True
            for name in self.ready:
                if not self.ready[name]:
                    clearpass = False
    
    def tkthread(self):
        self.root = tk.Tk() #create tkinter window
        
        class styling:
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
            def set_weight(self, frame, width, height, weight_ = 1):
                'Set uniform weighting across a frame'
                for cheight in range(height):
                    frame.rowconfigure(cheight, weight = weight_)
                    for cwidth in range(width):
                        frame.columnconfigure(cwidth, weight = weight_)
                
            fonts = {'small': ('', 8),
                     'medium': ('', 15),
                     'large': ('', 25)}
            reliefs = {'default': {'relief': tk.FLAT,
                                   'overrelief': tk.GROOVE}}
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
                    
                frame = tk.Frame(main.page_frame)
                label_title = tk.Label(frame, text = 'Working title', **self.styling.get(font_size = 'large', object_type = tk.Label))
                button_play = tk.Button(frame, text = 'New game', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_load = tk.Button(frame, text = 'Load save', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_connect = tk.Button(frame, text = 'Connect to a server', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                button_host = tk.Button(frame, text = 'Host a server', **self.styling.get(font_size = 'medium', object_type = tk.Button))
                
                label_title.grid(row = 0, column = 0, sticky = 'NESW')
                button_play.grid(row = 1, column = 0, sticky = 'NESW')
                button_load.grid(row = 2, column = 0, sticky = 'NESW')
                button_connect.grid(row = 3, column = 0, sticky = 'NESW')
                button_host.grid(row = 4, column = 0, sticky = 'NESW')
                self.styling.set_weight(frame, 1, 5)
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
    
    def load(self, page):
        'Load a page'
        if (not self.uiobjects.main.current == None) and 'on_close' in dir(self.uiobjects.current):
            self.uiobjects.main.current.on_close() #close current page if one exists
        self.uiobjects.main.current = page #set loading page as current page
        if 'on_load' in dir(page):
            page.on_load() #run the load function for the page
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