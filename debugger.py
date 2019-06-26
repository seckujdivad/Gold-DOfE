import tkinter as tk

import debugging.lineintersection_test

class App:
    def __init__(self):
        self.root = tk.Tk()

        self._current_app = None

        class _elements:
            frame_parent = tk.Frame(self.root)

            button_lineint = tk.Button(self.root, text = 'Line intersection', command = lambda: self._change_app('lineintersection'))
        self._elements = _elements

        self._elements.frame_parent.pack(fill = tk.BOTH, expand = True)
        self._elements.button_lineint.pack(fill = tk.X, expand = True)

        self.root.mainloop()
    
    def _change_app(self, name):
        if not self._current_app == None:
            self._current_app.destroy()
        
        if name == 'lineintersection':
            self._current_app = debugging.lineintersection_test.Debugger(tk.Frame(self._elements.frame_parent))
            self._current_app.toplevel.pack(fill = tk.BOTH, expand = True)

if __name__ == '__main__':
    App()