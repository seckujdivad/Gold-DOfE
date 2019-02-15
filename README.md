# Gold DOfE
This is the project for the "skills" section of my Gold Duke of Edinburgh's Award.

## Current Features
* Level editor
  * Material editor
  * Level layout editor
  * Panel hitbox editor
  * Lighting renderer
* Networked play
* Static lighting
* Multiple gamemodes
* Basic combat

## Planned Features
* Entity editor
* More weapons
* Sounds
* Particle effects
* Areas in levels that have scripts attached to them

## How To Play
Start a local game by going to "Connect to a server" and picking a server on your local machine. Remember to go to settings and click "install required packages" before playing. Tweak with the graphical quality settings and the server hitbox precision settings for the best performance on your machine.

## Acknowledgements
### Line clipping
The line clipping code is taken from [this question](https://stackoverflow.com/questions/563198/how-do-you-detect-where-two-line-segments-intersect/565282#565282) answered by [Gareth Rees](https://stackoverflow.com/users/68063/gareth-rees) and implemented in Python by [Ibraim Ganiev](https://stackoverflow.com/users/1030820/ibraim-ganiev). The code is [here](modules/lineintersection.py), along with a few wrappers (wrap_np_seg_intersect and does_intersect) added by me.
