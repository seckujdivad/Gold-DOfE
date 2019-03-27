import random

class Script:
    def __init__(self, panel = None):
        self.binds = {'when touching': [self.when_touching],
                      'on enter': [lambda entity: print('entered')],
                      'on leave': [lambda entity: print('left')],
                      'when outside map': [self.goto_centre]}
        self.panel = panel
        
        if type(panel) == list:
            print(panel)
            raise Exception('')
    
    def when_touching(self, entity):
        print(entity.attributes.pos.x, entity.attributes.pos.y)
        entity.set(random.randrange(50, 750), random.randrange(50, 550))
        
        if self.panel is not None:
            self.panel.play_anim('active')
    
    def goto_centre(self, entity):
        entity.set(x = 400, y = 300)
        entity.attributes.pos.velocity.x = 0
        entity.attributes.pos.velocity.y = 0