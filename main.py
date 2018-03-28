import modules.ui
import modules.engine
import modules.logging
import modules.networking

class App:
    def __init__(self):
        self.ui = modules.ui.UI()
        self.ui.load(self.ui.uiobjects.menu)
        self.ui.set_title('Hydrophobes')
        self.ui.set_geometry('800x600')

if __name__ == '__main__':
    App()