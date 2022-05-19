import pyglet
from pyglet.window import key as KEY
from math import sin, cos, tan, sqrt
from maps import *

##### - some useful functions - #####

# math library using radians for calculate sin, cos, etc. Now i can use sinr() instead of sin()
def to_rad(degrees):
    return degrees/57.296
def sinr(degrees):
    return sin(to_rad(degrees))
def cosr(degrees):
    return cos(to_rad(degrees))
def tanr(degrees):
    return tan(to_rad(degrees))
# for correct use math formuls angle always should be from 0 to 359
def normalize_angle(angle):
    return angle%360 if angle>0 else 360-abs(angle)
# i cant use color upper than 255 or below 0
def normalize_peace_of_color(c):
    if c<0: c=0
    elif c>255: c=255
    return c
def normalize_color(color):
    r,g,b = color
    return((normalize_peace_of_color(r), normalize_peace_of_color(g), normalize_peace_of_color(b)))

# ================= settings ================= #
#                                              #
#                      ||                      #
#                      \/                      #

# window
screen_width, screen_height = 1000, 700
screen = pyglet.window.Window(screen_width, screen_height, 'raycasting demo', vsync=True)
#screen.set_location(900, 150) # temporary solution for more comfortable debugging (remove this line when program is done)

# important params
render_distance = 900
fps_max = 60.0 # it must be float
amt_rays = 100 # it must be upper than 2
fov = 60 # it must be less 180

# walls
ray_width = screen_width/amt_rays
block_size = 32
walls = []

# some params for raycasting
dist_to_screen = amt_rays / (2 * tanr(fov / 2))
proj_coeff = dist_to_screen * block_size * ray_width * 1.3
delta_angle = fov/amt_rays
ray_params = []

# other
ysize = map_height * block_size
xsize = map_widht * block_size
half_fov = fov / 2
temp_fov = 90 - half_fov
scaled_height = int(screen_height * 1.4)
batch = pyglet.graphics.Batch()
info_batch = pyglet.graphics.Batch()
info_bg = pyglet.shapes.Rectangle(0, 0, 550, 30, color=(0,0,0), batch=info_batch)
direction_label = pyglet.text.Label('angle: ', x=100, y=10, bold=1, color=(0,255,0,255), batch=info_batch)
fps_label = pyglet.text.Label('fps: ', x=0, y=10, bold=1, color=(0,255,0,255), batch=info_batch)
xpos_label = pyglet.text.Label('Xpos: ', x=250, y=10, bold=1, color=(0,255,0,255), batch=info_batch)
ypos_label = pyglet.text.Label('Ypos: ', x=400, y=10, bold=1, color=(0,255,0,255), batch=info_batch)
ceiling = pyglet.shapes.Rectangle(0, screen_height/2, screen_width, screen_height/2, batch=batch, color=(180,180,250))
floor = pyglet.shapes.Rectangle(0, 0, screen_width, screen_height/2, batch=batch, color=(50,200,50))
max_recursion_amt = 8

class Player:
    x, y = 0.0, 0.0
    controls = dict(left_rotation=False, right_rotation=False, move_forward=False, 
                    move_backward=False, move_left=False, move_right=False)
    move_speed = 3.1
    rotate_speed = 3.5
    direction = 0.0
    horizont_height = screen_height / 2
    def update_param(self):
        self.direction = normalize_angle(self.direction) # holding direction only from 0 to 360
player = Player()

# map init
for y in range(map_height):
    for x in range(map_widht):
        cur_block = wall_map[y][x]
        if cur_block == startpos: player.x, player.y = (x+1)*block_size, (map_height-(y+1))*block_size

#                      /\                      #
#                      ||                      #
#                                              #
# ================= settings ================= #

# optimal scaling wall height
def get_wall_height(distance, angle):
    try:
        height = int(proj_coeff / (distance * sinr(angle)))
        return height
    except:
        return scaled_height
# optimal shadowing walls
def get_shadow_color(distance, color):
    r,g,b = color
    shadow_scale = 0.24*distance
    r,g,b = int(r-shadow_scale),int(g-shadow_scale),int(b-shadow_scale)
    return normalize_color((r,g,b))

def vertical_rc(angle, max_distance, xm, x1, y1):
    # verticals
    symV = default_wall
    distanceV = -1
    SINa = sinr(angle)
    COSa = cosr(angle)
    CTGa = COSa/SINa
    if angle < 180:
        dx = 1
        x = xm + block_size
    else:
        dx = -1
        x = xm
    while(distanceV <= max_distance): 
        y = y1 + (x-x1)*CTGa
        distanceV = (x-x1)/SINa
        imap, jmap = int(ysize-y)//block_size, int(x+dx)//block_size
        xray, yray = x, y
        if 0 <= imap < map_height and 0 <= jmap < map_widht and wall_map[imap][jmap] not in nothing_str: 
            symV = wall_map[imap][jmap]
            break
        x += block_size * dx
    return distanceV, symV, xray, yray

def horizontal_rc(angle, max_distance, ym, x1, y1):
    # horizontals
    symH = default_wall
    distanceH = -1
    SINa = sinr(angle)
    COSa = cosr(angle)
    CTGa = COSa/SINa
    if angle < 90 or angle > 270:
        dy = 1
        y = ym + block_size
    else:
        dy = -1
        y = ym
    while(distanceH <= max_distance):
        x = x1 + (y-y1)/CTGa
        distanceH = (y-y1)/COSa
        imap, jmap = int(ysize-y-dy)//block_size, int(x)//block_size
        xray, yray = x, y
        if 0 <= imap < map_height and 0 <= jmap < map_widht and wall_map[imap][jmap] not in nothing_str: 
            symH = wall_map[imap][jmap]
            break
        y += block_size * dy
    return distanceH, symH, xray, yray

def oneray_rc(angle, add_dist, x1, y1, ray, amt):
    global ray_params
    xm, ym = x1//block_size*block_size, y1//block_size*block_size
    max_distance = render_distance - add_dist

    distanceV, symV, xV, yV = vertical_rc(angle, max_distance, xm, x1, y1)
    distanceH, symH, xH, yH = horizontal_rc(angle, max_distance, ym, x1, y1)

    if amt > max_recursion_amt: return
    
    # vertical
    if symV not in nothing_str and distanceV <= max_distance and distanceV < distanceH and distanceV >= 0: 

        if symV in walls_str: return([distanceV+add_dist, ray, 'V', symV])

        elif symV == mirror_block:
            amt += 1
            ray_params.append([distanceV+add_dist, ray, 'V', symV])
            return(oneray_rc(normalize_angle(normalize_angle(360-angle)), distanceV+add_dist, xV, yV, ray, amt))

    # horizontal
    elif symH not in nothing_str and distanceH <= max_distance and distanceH < distanceV and distanceH >= 0: 

        if symH in walls_str: return([distanceH+add_dist, ray, 'H', symH])
        
        elif symH == mirror_block:
            amt += 1
            ray_params.append([distanceH+add_dist, ray, 'H', symH])
            return(oneray_rc(normalize_angle(normalize_angle(180-angle)), distanceH+add_dist, xH, yH, ray, amt))

def rc():
    global ray_params
    ray_params = []
    x1, y1 = player.x, player.y
    angle = player.direction-half_fov
    angle = normalize_angle(angle)
    for ray in range(amt_rays+1):
        angle += delta_angle
        if angle == 90 or 270: angle += 0.001
        angle = normalize_angle(angle)

        # if the ray collided with wall
        test = oneray_rc(angle, 0, x1, y1, ray, 1)
        if test != None:
            ray_params.append(test)

def draw_walls():
    global walls, ray_params
    walls = []
    for param in ray_params:
        distance, ray, VorH, sym_wall = param
        wall_height = get_wall_height(distance, temp_fov+ray*delta_angle)
        color = (255,255,255)
        if sym_wall == border_wall:
            if VorH == 'V': color = (255,200,0)
            else: color = (225,170,0)
        elif sym_wall == default_wall:
            if VorH == 'V': color = (150,150,255)
            else: color = (120,120,225)
        elif sym_wall == mirror_block:
            if VorH == 'V': color = (210,210,210)
            else: color = (180,180,180)
        color = get_shadow_color(distance, color)
        walls.append(pyglet.shapes.Rectangle((ray-1)*ray_width, player.horizont_height-wall_height/2, ray_width, wall_height, batch=batch, color=color))

@screen.event
def on_draw():
    screen.clear()
    batch.draw()
    info_batch.draw()

@screen.event
def on_key_press(key, mod):
    if key == KEY.LEFT: player.controls['left_rotation'] = 1
    elif key == KEY.RIGHT: player.controls['right_rotation'] = 1
    elif key == KEY.W: player.controls['move_forward'] = 1
    elif key == KEY.S: player.controls['move_backward'] = 1
    elif key == KEY.A: player.controls['move_left'] = 1
    elif key == KEY.D: player.controls['move_right'] = 1
@screen.event
def on_key_release(key, mod):
    if key == KEY.LEFT: player.controls['left_rotation'] = 0
    elif key == KEY.RIGHT: player.controls['right_rotation'] = 0
    elif key == KEY.W: player.controls['move_forward'] = 0
    elif key == KEY.S: player.controls['move_backward'] = 0
    elif key == KEY.A: player.controls['move_left'] = 0
    elif key == KEY.D: player.controls['move_right'] = 0

def update(dt):
    if player.controls['left_rotation']: 
        player.direction -= player.rotate_speed
        player.update_param()
    if player.controls['right_rotation']: 
        player.direction += player.rotate_speed
        player.update_param()
    if player.controls['move_forward']:
        player.x += sinr(player.direction)*player.move_speed
        player.y += cosr(player.direction)*player.move_speed
    if player.controls['move_backward']:
        player.x -= sinr(player.direction)*player.move_speed
        player.y -= cosr(player.direction)*player.move_speed
    if player.controls['move_right']:
        player.x += sinr(normalize_angle(player.direction+90))*player.move_speed
        player.y += cosr(normalize_angle(player.direction+90))*player.move_speed
    if player.controls['move_left']:
        player.x -= sinr(normalize_angle(player.direction+90))*player.move_speed
        player.y -= cosr(normalize_angle(player.direction+90))*player.move_speed

    rc()
    draw_walls()

    fps_label.text = 'fps: ' + str(format(pyglet.clock.get_fps(), '.1f'))
    direction_label.text = 'angle: ' + str(format(player.direction, '.3f'))
    xpos_label.text = 'Xpos: ' + str(format(player.x, '.3f'))
    ypos_label.text = 'Ypos: ' + str(format(player.y, '.3f'))

pyglet.clock.schedule_interval(update, 1/fps_max) # frame rate limit

if __name__ == "__main__":
    pyglet.app.run()


#
# + mirrors
#   highest walls
# + shadows
#   visual borders
# 
# 
# 
# 
#   texturing walls
#   texturing floor
#   texturing ceil
# 
# 