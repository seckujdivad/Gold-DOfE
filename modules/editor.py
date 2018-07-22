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
        with open(os.path.join(self.path, path), 'r') as file:
            text = file.read()
        return text
    
    def write_text(self, path, text):
        with open(os.path.join(self.path, path), 'w') as file:
            file.write(text)

class Editor:
    def __init__(self, frame, pagemethods):
        self.frame = frame
        self.pagemethods = pagemethods
        
        class editors:
            class _Template:
                """
                A template for making editors
                """
                def __init__(self, frame, editorobj, tabobj):
                    self.frame = frame
                    self.editorobj = editorobj
                    self.tabobj = tabobj
                    
            class Text:
                '''
                Edit a text file in the map directory
                '''
                def __init__(self, frame, editorobj, tabobj):
                    self.frame = frame
                    self.editorobj = editorobj
                    self.tabobj = tabobj
                    
                    self.toprow = tk.Frame(self.frame)
                    self.path = tk.Entry(self.toprow, **self.editorobj.uiobjs.pagemethods.uiobject.styling.get(font_size = 'small', object_type = tk.Entry))
                    self.save = tk.Button(self.toprow, text = 'Save', command = self.save_text, **self.editorobj.uiobjs.pagemethods.uiobject.styling.get(font_size = 'small', object_type = tk.Button))
                    self.reload = tk.Button(self.toprow, text = 'Reload', command = self.reload_text, **self.editorobj.uiobjs.pagemethods.uiobject.styling.get(font_size = 'small', object_type = tk.Button))
                    
                    self.path.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
                    self.save.pack(side = tk.RIGHT, fill = tk.Y)
                    self.reload.pack(side = tk.RIGHT, fill = tk.Y)
                    
                    self.textentry = tk.Text(self.frame, **self.editorobj.uiobjs.pagemethods.uiobject.styling.get(font_size = 'small', object_type = tk.Text))
                    
                    self.toprow.grid(row = 0, column = 0, sticky = 'NESW')
                    self.textentry.grid(row = 1, column = 0, sticky = 'NESW')
                    
                    self.frame.rowconfigure(1, weight = 1)
                    self.frame.columnconfigure(0, weight = 1)
                
                def reload_text(self):
                    path = self.path.get()
                    self.textentry.delete(0.0, tk.END)
                    self.textentry.insert(tk.END, self.editorobj.map.get_text(self.path.get()))
                    
                    self.tabobj.set_title(path)
                
                def save_text(self):
                    try:
                        text = self.textentry.get(0.0, tk.END)
                    except tk.TclError:
                        text = ''
                    path = self.path.get()
                    self.editorobj.map.write_text(path, text)
                    self.tabobj.set_title(path)
            
            class Tree:
                '''
                View the entire map directory, copy file paths
                '''
                def __init__(self, frame, editorobj, tabobj):
                    self.frame = frame
                    self.editorobj = editorobj
                    self.tabobj = tabobj
                    
                    self.all_paths = []
                    
                    self.list_frame = tk.Frame(self.frame)
                    self.list_list = tk.Listbox(self.list_frame, font = ('Courier New', 9))
                    self.list_bar = tk.Scrollbar(self.list_frame, command = self.list_list.yview)
                    self.list_list.config(yscrollcommand = self.list_bar.set)
                    
                    self.button_copy = tk.Button(self.frame, text = 'Copy', command = self.copy_selection_to_clipboard, **self.editorobj.uiobjs.pagemethods.uiobject.styling.get(font_size = 'medium', object_type = tk.Button))
                    self.button_open = tk.Button(self.frame, text = 'Open with system', command = self.open_selection_with_system, **self.editorobj.uiobjs.pagemethods.uiobject.styling.get(font_size = 'medium', object_type = tk.Button))
                    
                    self.list_bar.pack(side = tk.RIGHT, fill = tk.Y)
                    self.list_list.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
                    
                    self.list_frame.grid(row = 0, column = 0, columnspan = 2, sticky = 'NESW')
                    self.button_copy.grid(row = 1, column = 0, sticky = 'NESW')
                    self.button_open.grid(row = 1, column = 1, sticky = 'NESW')
                    self.editorobj.uiobjs.pagemethods.uiobject.styling.set_weight(self.frame, 2, 2)
                    self.frame.rowconfigure(1, weight = 0)
                    
                    self.tabobj.set_title(self.editorobj.map.name)
                    
                    self.populate_list()
                    
                def populate_list(self):
                    with open(os.path.join(self.editorobj.map.path, 'editorcfg.json'), 'r') as file:
                        cfg = json.load(file)
                        
                    all_items, self.all_paths = self.index_dir('', 0, cfg['ignore'])
                    
                    for item in all_items:
                        self.list_list.insert(tk.END, item)
                
                def index_dir(self, path, depth, ignore):
                    map_path = self.editorobj.map.path
                    output = []
                    prefix = '    ' * depth
                    paths = []
                    for item in os.listdir(os.path.join(map_path, path)):
                        if os.path.isdir(os.path.join(map_path, path, item)):
                            paths.append(os.path.join(path, item))
                            output.append('+{}{}'.format(prefix, item))
                            if not os.path.join(path, item) in ignore:
                                noutput, npaths = self.index_dir(os.path.join(path, item), depth + 1, ignore)
                                output += noutput
                                paths += npaths
                        else:
                            paths.append(os.path.join(path, item))
                            if depth == 0:
                                output.append(' {}{}'.format(prefix, item))
                            else:
                                output.append('|{}{}'.format(prefix, item))
                        #paths.append(os.path.join(path, item))
                    return output, paths
                
                def copy_selection_to_clipboard(self, event = None):
                    selection = self.list_list.curselection()
                    if not selection == ():
                        text = self.all_paths[selection[0]]
                        self.set_clipboard(text)
                
                def open_selection_with_system(self, event = None):
                    selection = self.list_list.curselection()
                    if not selection == ():
                        text = self.all_paths[selection[0]]
                        os.system('start "" "{}"'.format(os.path.join(self.editorobj.map.path, text)))
                
                def set_clipboard(self, text):
                    self.editorobj.uiobjs.pagemethods.uiobject.root.clipboard_clear()
                    self.editorobj.uiobjs.pagemethods.uiobject.root.clipboard_append(text)
            
            library = {'Text': Text,
                       'Tree': Tree}
            
            @classmethod
            def create_new(self, name):
                new_pane = EditorTab(name, self, len(self.uiobjs.tabs))
                new_pane.show()
                self.uiobjs.tabs.append(new_pane)
            
            uiobjs = None
        self.editors = editors
        
        class uiobjs:
            editor_pane_frame = tk.Frame(self.frame)
            editor_panes = []
            for name in self.editors.library:
                editor_panes.append(tk.Button(editor_pane_frame, text = name, command = functools.partial(self.editors.create_new, name), **self.pagemethods.uiobject.styling.get(font_size = 'small', object_type = tk.Button)))
            
            tabs_frame = tk.Frame(self.frame)
            tabs_current_frame = tk.Frame(self.frame)
            tabs = []
            tabs_current = None
        self.uiobjs = uiobjs
        self.uiobjs.frame = self.frame
        self.uiobjs.pagemethods = self.pagemethods
        self.editors.uiobjs = uiobjs
        
        #pack all items
        i = 0
        for button in self.uiobjs.editor_panes:
            button.grid(row = 0, column = i, sticky = 'NESW')
            i += 1
        self.pagemethods.uiobject.styling.set_weight(self.uiobjs.editor_pane_frame, len(self.uiobjs.editor_panes) - 1, 0)
        
        self.uiobjs.editor_pane_frame.grid(row = 0, column = 0, sticky = 'NESW')
        self.uiobjs.tabs_frame.grid(row = 1, column = 0, sticky = 'NESW')
        self.uiobjs.tabs_current_frame.grid(row = 2, column = 0, sticky = 'NESW')
        
        self.frame.rowconfigure(2, weight = 1)
        self.frame.columnconfigure(0, weight = 1)
    
    def load(self, map_name):
        self.map = Map(map_name)
        self.editors.map = self.map

class EditorTab:
    '''
    A tab for the editor
    '''
    def __init__(self, name, editorobj, index):
        self.name = name
        self.editorobj = editorobj
        self.index = index
        self.active = True
        
        self.header_frame = tk.Frame(self.editorobj.uiobjs.tabs_frame) #idk, the thing you click on to switch tabs
        self.header_button = tk.Button(self.header_frame, text = '####', command = self.show, **self.editorobj.uiobjs.pagemethods.uiobject.styling.get(font_size = 'small', object_type = tk.Button))
        self.header_close = tk.Button(self.header_frame, text = 'X', command = self.destroy, **self.editorobj.uiobjs.pagemethods.uiobject.styling.get(font_size = 'small', object_type = tk.Button))
        
        self.set_title('######')
        
        self.header_button.pack(side = tk.LEFT)
        self.header_close.pack(side = tk.LEFT)
        self.header_frame.pack(side = tk.LEFT)
        
        self.frame = tk.Frame(self.editorobj.uiobjs.tabs_current_frame)
        
        self.editor = self.editorobj.library[self.name](self.frame, self.editorobj, self)
    
    def show(self):
        if not self.editorobj.uiobjs.tabs_current == None:
            self.editorobj.uiobjs.tabs[self.editorobj.uiobjs.tabs_current].hide()
        self.frame.pack(fill = tk.BOTH, expand = True)
        self.editorobj.uiobjs.tabs_current = self.index
        self.active = True
    
    def hide(self):
        self.frame.pack_forget()
        self.active = False
    
    def destroy(self):
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
        self.header_button.config(text = '{}: {}'.format(self.name, text))