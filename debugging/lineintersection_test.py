import tkinter as tk

import modules.lineintersection

class Debugger:
    def __init__(self, toplevel):
        self.toplevel = toplevel

        self._canvas = tk.Canvas(self.toplevel, width = 400, height = 300, bg = 'white')
        self._canvas.pack()
        
        self._selected = 0
        self._lines = [Line(self._canvas), Line(self._canvas)]
        self._point = self._canvas.create_oval(0, 0, 0, 0, fill = 'yellow', outline = 'black')

        self._canvas.bind('<Button-1>', self.mouse_clicked)
        self._canvas.bind('<Right>', self.arrow_right)
        self._canvas.bind('<Left>', self.arrow_left)
        self._canvas.bind('<Enter>', self.take_focus)
        self._canvas.bind('<Leave>', self.lose_focus)

        self._canvas.create_text(200, 100, text = 'Arrow keys to cycle through points\nMouse1 to place')
    
    def destroy(self):
        self.toplevel.pack_forget()
    
    def arrow_left(self, event = None):
        self._selected = (self._selected - 1) % 4
    
    def arrow_right(self, event = None):
        self._selected = (self._selected + 1) % 4
    
    def mouse_clicked(self, event):
        if self._selected == 0:
            self._lines[0].update(x0 = event.x, y0 = event.y)
        
        elif self._selected == 1:
            self._lines[0].update(x1 = event.x, y1 = event.y)
        
        elif self._selected == 2:
            self._lines[1].update(x0 = event.x, y0 = event.y)

        elif self._selected == 3:
            self._lines[1].update(x1 = event.x, y1 = event.y)

        result = modules.lineintersection.wrap_np_seg_intersect(self._lines[0].coords, self._lines[1].coords)
        print(result)

        if result == False or result is None:
            self._canvas.coords(self._point, 0, 0, 0, 0)
        
        else:
            self._canvas.coords(self._point, result[0] - 5, result[1] - 5, result[0] + 5, result[1] + 5)


    def take_focus(self, event = None):
        self._canvas.focus_set()
    
    def lose_focus(self, event = None):
        self._canvas.winfo_toplevel().focus_set()

class Line:
    def __init__(self, canvas):
        self._canvas = canvas

        self.coords = [[0, 0], [0, 0]]

        self._line = None

        self.update(0, 0, 0, 0)
    
    def update(self, x0 = None, y0 = None, x1 = None, y1 = None):
        if x0 is None:
            x0 = self.coords[0][0]
        
        if y0 is None:
            y0 = self.coords[0][1]
        
        if x1 is None:
            x1 = self.coords[1][0]
        
        if y1 is None:
            y1 = self.coords[1][1]
        
        self.coords = [[x0, y0], [x1, y1]]

        if self._line is None:
            self._line = self._canvas.create_line(x0, y0, x1, y1)
        
        else:
            self._canvas.coords(self._line, x0, y0, x1, y1)