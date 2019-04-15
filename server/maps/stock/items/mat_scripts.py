import time
import math

import modules.items

class Generic(modules.items.ItemScript):
    def __init__(self, name, server):
        super().__init__(name, server)
        
        self.attributes.damage.destroyed_after = self.cfgs.item['destroyed after damage']
        self.attributes.damage.cooldown = self.cfgs.item['damage cooldown']
        self.attributes.damage.entities = self.cfgs.item['damage']
        self.attributes.display_name = self.cfgs.item['display name']
        self.attributes.max_dist = self.cfgs.item['range']
    
    def _tick(self):
        output = []
        if self.attributes.first_tick:
            output.append({'type': 'add',
                           'position': [self.attributes.pos.x, self.attributes.pos.y],
                           'rotation': self.attributes.rotation,
                           'new': True})

        elif (not self.inside_map()) or (self.attributes.max_dist is not None and self.attributes.dist_travelled >= self.attributes.max_dist):
            output.append({'type': 'remove'})
        
        elif self.attributes.velocity.x != 0 or self.attributes.velocity.y != 0:
            result = self._pos_update()
            if result is not None:
                for d in result:
                    output.append(d)
        
        for client in self.server.clients:
            damage_dealt = False
            if client.metadata.active and client.metadata.mode == 'player':
                if self.touching_player(client):
                    if self.attributes.damage.last is not None:
                        if (time.time() - self.attributes.damage.last) > self.attributes.damage.cooldown:
                            damage_dealt = True
                    else:
                        damage_dealt = True
            
            if damage_dealt and not self.attributes.creator == client:
                result = self._damage_dealt(client)
                if result is not None:
                    for d in result:
                        output.append(d)
                    
        return output
    
    def _pos_update(self):
        output = []
        if self.attributes.velocity.x != 0 or self.attributes.velocity.y != 0:
            vchange_x = self.attributes.velocity.x / self.attributes.tickrate
            vchange_y = self.attributes.velocity.y / self.attributes.tickrate
            self.attributes.pos.x += vchange_x
            self.attributes.pos.y += vchange_y
            
            self.attributes.dist_travelled += math.hypot(vchange_x, vchange_y)
            
            output.append({'type': 'update position',
                           'position': [self.attributes.pos.x, self.attributes.pos.y]})
            return output
        else:
            return None
    
    def _damage_dealt(self, client):
        client.increment_health(0 - self.attributes.damage.entities['player'], self.attributes.display_name, self.attributes.creator.metadata.username)
        self.attributes.damage.last = time.time()
        
        client.push_health()
        
        if self.attributes.damage.destroyed_after:
            return [{'type': 'remove'}]
        else:
            return None


class ItemScriptFireball(Generic):
    def __init__(self, name, server):
        super().__init__(name, server)
        
    internal_name = 'fireball'
    
    def _damage_dealt(self, client):
        client.increment_health(0 - self.attributes.damage.entities['player'], self.attributes.display_name, self.attributes.creator.metadata.username)
        self.attributes.damage.last = time.time()
        
        client.push_health()
        
        if self.attributes.damage.destroyed_after:
            self.attributes.velocity.x /= 4
            self.attributes.velocity.y /= 4
            return [{'type': 'animation', 'loop': False, 'animation': 'explode'},
                    {'type': 'remove', 'delay': 0.5}]
        else:
            return None


class ItemScriptSword(Generic):
    def __init__(self, name, server):
        super().__init__(name, server)
    
    internal_name = 'swordswipe'