import tkinter as tk
import os
import sys
import functools
import json

class Map:
    def __init__(self, name):
        self.name = name
        
        self.path = os.path.join(sys.path[0], 'server', 'maps', self.name)
        
    def get_text(self, path):
        'Gets text from a file in the map folder'
        with open(os.path.join(self.path, path), 'r') as file:
            text = file.read()
        return text
    
    def write_text(self, path, text):
        'Writes text to a file in the map folder'
        with open(os.path.join(self.path, path), 'w') as file:
            file.write(text)
    
    def get_json(self, path):
        'Gets data from a json file in the map folder and reads it'
        with open(os.path.join(self.path, path), 'r') as file:
            data = json.load(file)
        return data
    
    def write_json(self, path, data):
        'Writes data to a json file in the map folder'
        with open(os.path.join(self.path, path), 'w') as file:
            json.dump(data, file, sort_keys=True, indent='\t')

class Editor:
    def __init__(self, page):
        self.page = page
        self.frame = self.page.frame
        
        self.ui_styling = self.page._styling
        
        class editors:
            class _Template:
                """
                A template for making editors
                """
                def __init__(self, frame, editorobj, tabobj):
                    self.frame = frame
                    self.editorobj = editorobj
                    self.tabobj = tabobj
                    
                    self.ui_styling = self.editorobj.uiobjs.ui_styling
                    
            library = {'Text': Text,
                       'Tree': Tree,
                       'Layout': Layout,
                       'Materials': MaterialEditor,
                       'Config': ConfigEditor,
                       'Light maps': LightMap,
                       'Panel hitboxes': PanelHitbox} #all the types of tab
            
            @classmethod
            def create_new(self, name):
                'Make a new pane/tab'
                new_pane = EditorTab(name, self, len(self.uiobjs.tabs))
                new_pane.show()
                self.uiobjs.tabs.append(new_pane)
            
            uiobjs = None
        self.editors = editors
        
        class uiobjs:
            editor_pane_frame = tk.Frame(self.frame)
            editor_panes = []
            for name in self.editors.library: #make buttons to open new types of tab
                editor_panes.append(tk.Button(editor_pane_frame, text = name, command = functools.partial(self.editors.create_new, name), **self.ui_styling.get(font_size = 'small', object_type = tk.Button)))
            
            tabs_frame = tk.Frame(self.frame)
            tabs_current_frame = tk.Frame(self.frame)
            tabs = []
            tabs_current = None
            ui_styling = None
            return_to_menu_button = tk.Button(editor_pane_frame, text = 'Back', command = functools.partial(self.page._load_page, 'editor choose map'), **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
        self.uiobjs = uiobjs
        self.uiobjs.frame = self.frame
        self.editors.uiobjs = uiobjs
        self.uiobjs.ui_styling = self.ui_styling
        
        #pack all items
        i = 0
        for button in self.uiobjs.editor_panes:
            button.pack(side = tk.LEFT, fill = tk.Y)
            i += 1
        self.uiobjs.return_to_menu_button.pack(side = tk.RIGHT, fill = tk.Y)
        
        #specify the positions of the UI elements
        self.uiobjs.editor_pane_frame.grid(row = 0, column = 0, sticky = 'NESW')
        self.uiobjs.tabs_frame.grid(row = 1, column = 0, sticky = 'NESW')
        self.uiobjs.tabs_current_frame.grid(row = 2, column = 0, sticky = 'NESW')
        
        self.frame.rowconfigure(2, weight = 1)
        self.frame.columnconfigure(0, weight = 1)
    
    def load(self, map_name):
        'Specify the map file to be used. Must be called before the editor is interacted with'
        self.map = Map(map_name) #this handles most of the interactions with the map files
        self.editors.map = self.map
    
    def close(self):
        pass

class EditorTab:
    '''
    A tab for the editor
    '''
    def __init__(self, name, editorobj, index):
        self.name = name
        self.editorobj = editorobj
        self.index = index
        self.active = True #when a new tab is made, it is shown by default
        
        self.ui_styling = self.editorobj.uiobjs.ui_styling
        
        self.colour_idle = 'SystemButtonFace'
        self.colour_active = 'snow3'
        self.colour_close = 'red'
        self.colour_close_text = 'black'
        
        #construct UI
        self.header_frame = tk.Frame(self.editorobj.uiobjs.tabs_frame) #idk, the thing you click on to switch tabs
        self.header_button = tk.Button(self.header_frame, text = '####', command = self.show, **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
        self.header_close = tk.Button(self.header_frame, text = 'X', command = self.destroy, **self.ui_styling.get(font_size = 'small', object_type = tk.Button))
        
        self.set_title('######') #set a blank title for the tab (ready for the editor to specify one)
        
        self.header_button.pack(side = tk.LEFT)
        self.header_close.pack(side = tk.LEFT)
        self.header_frame.pack(side = tk.LEFT)
        
        self.frame = tk.Frame(self.editorobj.uiobjs.tabs_current_frame)
        
        self.editor = self.editorobj.library[self.name](self.frame, self.editorobj, self)
    
    def show(self):
        'Show the tab'
        if not self.editorobj.uiobjs.tabs_current == None: #hide the current tab if there is one
            self.editorobj.uiobjs.tabs[self.editorobj.uiobjs.tabs_current].hide()
        self.frame.pack(fill = tk.BOTH, expand = True) #show the frame that contains all the tab objects
        self.editorobj.uiobjs.tabs_current = self.index #set the current tab to this one
        
        self.header_frame.config(bg = self.colour_active)
        self.header_button.config(bg = self.colour_active)
        self.header_close.config(bg = self.colour_close, fg = self.colour_close_text)
        
        self.active = True #change mode
    
    def hide(self):
        'Hide the tab'
        self.frame.pack_forget() #hide the frame that contains all the objects that make up the tab
        
        self.header_frame.config(bg = self.colour_idle)
        self.header_button.config(bg = self.colour_idle)
        self.header_close.config(bg = self.colour_close, fg = self.colour_close_text)
        
        self.active = False #change mode
    
    def destroy(self):
        'Completely destroy the tab (close it)'
        self.hide() #remove pane containing editor
        self.header_frame.pack_forget() #remove tab from the list of tabs on the screen
        self.editorobj.uiobjs.tabs[self.index] = None #remove this tab from the list of tabs in memory
        
        #set the focus to none if there are no availabble tabs
        update_current = True
        self.editorobj.uiobjs.tabs_current = None
        for item in self.editorobj.uiobjs.tabs:
            if not item == None:
                item.show()
    
    def set_title(self, text):
        'Set the title of the tab'
        self.header_button.config(text = '{}: {}'.format(self.name, text))

