class Script:
    def __init__(self, panel):
        self.binds = {'when touching': [self.when_touching],
                      'on enter': [lambda entity: print('entered')],
                      'on leave': [lambda entity: print('left')],
                      'player': {'when outside map': [self.when_touching]}}
        self.panel = panel
    
    def when_touching(self, entity):
        print(entity.pos.x, entity.pos.y)
        entity.setpos(400, 300)
        self.panel['model'].play_anim('active')