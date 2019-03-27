# Gold DOfE
This is the project for the "skills" section of my Gold Duke of Edinburgh's Award.

## Current Features
* Level editor
  * Material editor
  * Level layout editor
  * Panel hitbox editor
  * Lighting renderer
* Modular engine
  * Graphical improvements
    * Layers
    * Transparency
    * Rotation
    * Animation
    * Optional 'pixel grid' to snap to
  * Networked play
  * Static precalculated lighting
  * Collisions and clipping

## Planned Features
* Entity editor
* More weapons
* Sounds
* Particle effects

## How To Play
1. Install [Python](https://www.python.org/), making sure that the tkinter package is installed (this should happen by default)
2. Open "launcher.pyw"
3. Click on "Connect to a server"
4. Choose "Local PC (localhost:normal) - limited to local network" and click "connect" to host a server on your own machine

### Controls
|Key            |Action               |
|---            |---                  |
|WASD\Arrow keys|Move around          |
|Mouse button 1 |Use current item     |
|Keys 1-5       |Choose inventory slot|

### Playing against friends
1. Find their IP (type "ipconfig" into the command line on Windows)
2. Go to "Connect to a server"
3. Type it into the "address" box
4. Give it a memorable name
5. Click on "open to LAN"
6. Click on "add server"

If the server owner has any custom settings (port, tickrate etc), set these in the labelled boxes.

### Recommended packages
Remember to go to settings and click "install required packages" before playing for the best experience. Tweak with the graphical quality settings and the server hitbox precision settings for the best performance on your machine.

## Acknowledgements
### Line clipping
The line clipping code is taken from [this question](https://stackoverflow.com/questions/563198/how-do-you-detect-where-two-line-segments-intersect/565282#565282) answered by [Gareth Rees](https://stackoverflow.com/users/68063/gareth-rees) and implemented in Python by [Ibraim Ganiev](https://stackoverflow.com/users/1030820/ibraim-ganiev). The code is [here](modules/lineintersection.py), along with a few wrappers (wrap_np_seg_intersect and does_intersect) added by me.

### Serialisable flags
The serialisable flags code is taken from [here](http://code.activestate.com/recipes/473863-a-threadingevent-you-can-pickle/), but I don't think it actually works yet. It might be removed in the future. All the code taken is [here](modules/event.py).
