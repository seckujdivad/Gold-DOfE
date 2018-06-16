import tkinter as tk
import os
import sys
import functools

class Map:
    def __init__(self):
        pass

class Editor:
    def __init__(self, frame, pagemethods):
        self.frame = frame
        self.pagemethods = pagemethods
        
        class editors:
            class Text:
                def __init__(self, frame, editorobj):
                    self.frame = frame
                    self.editorobj = editorobj
                    
                    self.textentry = tk.Text(self.frame, **self.editorobj.uiobjs.pagemethods.uiobject.styling.get(font_size = 'small', object_type = tk.Text))
                    self.textentry.pack()
            
            library = {'Text': Text}
            
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
    
    def load(self, map_name):
        pass

class EditorTab:
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
        
        self.editor = self.editorobj.library[self.name](self.frame, self.editorobj)
    
    def show(self):
        if not self.editorobj.uiobjs.tabs_current == None:
            self.editorobj.uiobjs.tabs[self.editorobj.uiobjs.tabs_current].hide()
        self.frame.pack(fill = tk.BOTH)
        self.editorobj.uiobjs.tabs_current = self.index
    
    def hide(self):
        self.frame.pack_forget()
    
    def destroy(self):
        self.hide()
        self.header_frame.pack_forget()
        self.editorobj.uiobjs.tabs[self.editorobj.uiobjs.tabs_current] = None
        cont = True
        i = 0
        while cont:
            if not self.editorobj.uiobjs.tabs[i] == None:
                self.editorobj.uiobjs.tabs_current = None
                self.editorobj.uiobjs.tabs[i].show()
                cont = False
            i += 1
    
    def set_title(self, text):
        self.header_button.config(text = '{}: {}'.format(self.name, text))