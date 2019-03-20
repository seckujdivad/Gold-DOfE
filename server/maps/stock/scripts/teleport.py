import random

class Script:
    def __init__(self, panel):
        self.binds = {'when touching': [self.when_touching],
                      'on enter': [lambda entity: print('entered')],
                      'on leave': [lambda entity: print('left')],
                      'player': {'when outside map': [self.when_touching]}}
        self.panel = panel
    
    def when_touching(self, entity):
        print(entity.pos.x, entity.pos.y)
        entity.setpos(random.randrange(50, 750), random.randrange(50, 550))
        self.panel.play_anim('active')