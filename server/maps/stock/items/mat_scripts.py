import modules.items

class ItemScriptFireball(modules.items.ItemScript):
    def __init__(self, name, server):
        super().__init__(name, server)
    
    def _tick(self):
        output = {}
        if self.attributes.first_tick:
            output['type'] = 'add'
            output['position'] = [self.attributes.pos.x, self.attributes.pos.y]
            output['rotation'] = self.attributes.rotation
            output['new'] = True
        
        elif not self.inside_map():
            to_send_loop['type'] = 'remove'
        
        elif self.attributes.velocity.x != 0 or self.attributes.velocity.y != 0:
            self.attributes.pos.x += self.attributes.velocity.x
            self.attributes.pos.y += self.attributes.velocity.y
            
            to_send_loop['type'] = 'update position'
            to_send_loop['position'] = [self.attributes.pos.x, self.attributes.pos.y]
        
        return output