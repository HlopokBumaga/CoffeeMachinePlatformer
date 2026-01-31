import arcade
from arcade.camera import Camera2D
from pyglet.graphics import Batch

# == Constants ==

SCREEN_W = 1280
SCREEN_H = 720
TITLE = "Coffee Machine Platformer"

GRAVITY = 2
MOVE_SPEED = 8
JUMP_SPEED = 23

COYOTE_TIME = 0.08
JUMP_BUFFER = 0.12
MAX_JUMPS = 1

CAMERA_LERP = 0.12
WORLD_COLOR = arcade.color.WHITE

PLAYER_PATH = "Materials/Sprite/CoffeeMachine/standart.png"
BOB_PATH = "Materials/Sprite/Bob/CoffeeBob.png"

JUMP_PATH = "Materials/Sounds/Jump.wav"
BOB_SOUND_PATH = "Materials/Sounds/CoffeeBean.wav"
DEAD_PATH = "Materials/Sounds/dead.wav"
COFFEE_PATH = "Materials/Sounds/Portal.wav"

BULLET_SPEED = 6.5

# == Player ==


class CoffeeMachinePlayer(arcade.Sprite):
    def __init__(self):
        super().__init__(PLAYER_PATH, scale=0.12)

        self.player_list = arcade.SpriteList()

        self.spawn_point = (128, 256)

        self.player_frame_time = 0.0
        self.player_current_frame = 0
        self.player_frame_duration = 0.1
        self.player_facing_right = True
        self.player_is_walking = False
        self.player_is_jumping = False

    # == Load textures for animation ==
    def load_player_textures(self):
        self.player_idle_texture = arcade.load_texture(PLAYER_PATH)

        self.player_walk_textures = [
            arcade.load_texture(f"Materials/Sprite/CoffeeMachine/Animation/{i}.png") 
            for i in range(1, 7)
        ]

        self.player_jump_texture = arcade.load_texture(PLAYER_PATH)
    
    # == Animation ==
    def update_player_animation(self, dt, grounded, moving_x):
        
        self.player_frame_time += dt
        
        # States
        self.player_is_walking = grounded and moving_x
        self.player_is_jumping = not grounded
        
        # Player facing
        if moving_x:
            if self.change_x > 0:
                self.player_facing_right = True
            elif self.change_x < 0:
                self.player_facing_right = False
        
        # == Animation ==
        if self.player_is_walking:
            if self.player_frame_time >= self.player_frame_duration:
                self.player_frame_time = 0
                self.player_current_frame = (self.player_current_frame + 1) % 6

                if not self.player_facing_right:
                    self.texture = self.player_walk_textures[self.player_current_frame].flip_left_right()
                else:
                    self.texture = self.player_walk_textures[self.player_current_frame]
        elif self.player_is_jumping:
            if not self.player_facing_right:
                self.texture = self.player_jump_texture.flip_left_right()
            else:
                self.texture = self.player_jump_texture
        else:
            if not self.player_facing_right:
                self.texture = self.player_idle_texture.flip_left_right()
            else:
                self.texture = self.player_idle_texture


class Bullet(arcade.Sprite):
    def __init__(self, x, y, direction):
        super().__init__(BOB_PATH, scale=0.05)  
        self.center_x = x
        self.center_y = y
        self.change_x = BULLET_SPEED * direction

    
    def update(self, dt):
        self.center_x += self.change_x


# == Game ==


class Platformer(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_W, SCREEN_H, TITLE, antialiasing=True)
        arcade.set_background_color(WORLD_COLOR)

        # == Cameras ==
        self.world_camera = Camera2D()
        self.gui_camera = Camera2D()

        # == Sprites ==
        self.walls = None

        self.spikes = None

        self.cups = None

        # == Player ==
        self.player = None

        # == Bullet ==
        self.bullets = None

        # == Physics ==
        self.engine = None

        # == Physics data ==
        self.left = self.right = self.jump_pressed = False
        self.jump_buffer_timer = 0.0
        self.time_since_ground = 999.0
        self.jumps_left = MAX_JUMPS

        # == Text ==
        self.cups_taked = 0
        self.level = 1
        self.batch = Batch()
        self.text_info = arcade.Text(
            "A, D — ходьба • SPACE — прыжок • F - выстрел",
            16,
            16,
            arcade.color.GRAY,
            14,
            batch=self.batch,
        )
        self.name_game = arcade.Text(
            "Coffee Machine Platfromer",
            16,
            690,
            arcade.color.BLACK,
            20,
            batch=self.batch,
        )

        # == Data ==
        self.deaths = 0

        # == Sound ==
        self.jump_sound = arcade.load_sound(JUMP_PATH,False)
        self.bob_sound = arcade.load_sound(BOB_SOUND_PATH,False)
        self.dead_sound = arcade.load_sound(DEAD_PATH,False)
        self.coffee_sound = arcade.load_sound(COFFEE_PATH,False)

    # == Player and Game setup ==
    def setup(self, death=False):
        if death:
            arcade.play_sound(self.dead_sound,1.0,-1,False)

        self.cups_taked = 0

        # == Player ==
        self.player = CoffeeMachinePlayer()
        self.player.player_list.clear()
        self.player.center_x, self.player.center_y = self.player.spawn_point
        self.player.player_list.append(self.player)
        self.player.load_player_textures()

        # == Load tile map from Tiled ==
        map_name = "Materials/Sprite/Levels/lvl1.tmx"
        tile_map = arcade.load_tilemap(map_name, scaling=0.5)

        self.walls = tile_map.sprite_lists["Walls"]
        self.spikes = tile_map.sprite_lists["Spikes"]
        self.cups = tile_map.sprite_lists["CoffeeCups"]

        # == Physics ==
        self.engine = arcade.PhysicsEnginePlatformer(
            player_sprite=self.player,
            gravity_constant=GRAVITY,
            walls=self.walls,
            platforms=None
        )

        # == Reset physics data ==
        self.jump_buffer_timer = 0
        self.time_since_ground = 999.0
        self.jumps_left = MAX_JUMPS

        self.bullets = arcade.SpriteList()

        # == Texts ==
        self.cup_info = arcade.Text(
            f"Наполнено чашек: {self.cups_taked} / 3",
            16,
            642,
            arcade.color.BLACK,
            16,
            batch=self.batch,
        )

        self.level_info = arcade.Text(
            f"Уровень: {self.level}",
            16,
            665,
            arcade.color.BLACK,
            17,
            batch=self.batch,
        )

    def on_draw(self):
        self.clear()

        # == World drawing ==
        self.world_camera.use()

        # == Structures ==
        self.walls.draw()
        self.spikes.draw()
        self.cups.draw()

        self.player.player_list.draw()

        # == Bullets drawing ==
        self.bullets.draw()

        # == GUI ==
        self.gui_camera.use()
        self.batch.draw()
    
    def shoot(self):   
        offset_x = (self.player.width // 2 + 10) * (1 if self.player.player_facing_right else -1)

        bullet = Bullet(
            self.player.center_x + offset_x,
            self.player.center_y + 8,
            1 if self.player.player_facing_right else -1
        )

        self.bullets.append(bullet)


    def on_key_press(self, key, modifiers):
        if key == arcade.key.A:
            self.left = True
        elif key == arcade.key.D:
            self.right = True
        elif key == arcade.key.SPACE:
            self.jump_pressed = True
            self.jump_buffer_timer = JUMP_BUFFER

            arcade.play_sound(self.jump_sound,1.0,-1,False)
        elif key == arcade.key.F:
            self.shoot()

            arcade.play_sound(self.bob_sound,1.0,-1,False)

    def on_key_release(self, key, modifiers):
        if key == arcade.key.A:
            self.left = False
        elif key == arcade.key.D:
            self.right = False
        elif key == arcade.key.SPACE:
            self.jump_pressed = False
            if self.player.change_y > 0:
                self.player.change_y *= 0.45

    def on_update(self, dt: float):
        # == Horizontal moving ==

        if self.cups_taked == 3:
            if self.level != 3:
                self.level += 1
                self.setup()
            else:
                print("Конец игры!")

        if self.jump_buffer_timer > 0:
            self.jump_buffer_timer -= dt
        
        move = 0
        moving_x = False

        if self.left and not self.right:
            move = -MOVE_SPEED
            moving_x = True
        elif self.right and not self.left:
            move = MOVE_SPEED
            moving_x = True

        self.player.change_x = move

        grounded = self.engine.can_jump(y_distance=6)

        if grounded:
            self.time_since_ground = 0
            self.jumps_left = MAX_JUMPS
        else:
            self.time_since_ground += dt

        want_jump = self.jump_pressed or (self.jump_buffer_timer > 0)

        if want_jump:
            can_coyote = self.time_since_ground <= COYOTE_TIME
            if grounded or can_coyote:
                self.engine.jump(JUMP_SPEED)
                self.jump_buffer_timer = 0

        self.engine.update()

        self.bullets.update()

        self.player.update_player_animation(dt, grounded, moving_x)

        for cup in self.cups:
            if arcade.check_for_collision_with_list(cup, self.bullets):
                cup.remove_from_sprite_lists()
                self.cups_taked += 1
                self.cup_info.text = f"Наполнено чашек: {self.cups_taked} / 3"
                
                arcade.play_sound(self.coffee_sound,1.0,-1,False)

        for bullet in self.bullets:
            if arcade.check_for_collision_with_list(bullet, self.walls):
                bullet.remove_from_sprite_lists()
            
            if arcade.check_for_collision_with_list(bullet, self.cups):
                bullet.remove_from_sprite_lists()
        
        for spike in self.spikes:
            if arcade.check_for_collision(spike, self.player):
                self.deaths += 1
                self.setup(True)

        target = (self.player.center_x, self.player.center_y)
        cx, cy = self.world_camera.position
        smooth = (
            cx + (target[0] - cx) * CAMERA_LERP,
            cy + (target[1] - cy) * CAMERA_LERP,
        )

        half_w = self.world_camera.viewport_width / 2
        half_h = self.world_camera.viewport_height / 2

        world_w = 1700
        world_h = 2000
        cam_x = max(half_w, min(world_w - half_w, smooth[0]))
        cam_y = max(half_h, min(world_h - half_h, smooth[1]))

        self.world_camera.position = (cam_x, cam_y)
        self.gui_camera.position = (SCREEN_W / 2, SCREEN_H / 2)


def main():
    game = Platformer()
    game.setup()
    arcade.run()


if __name__ == "__main__":
    main()