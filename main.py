import arcade
from arcade.camera import Camera2D
from pyglet.graphics import Batch

# == Constants ==

SCREEN_W = 1280
SCREEN_H = 720
TITLE = "Coffee Machine Platformer"

GRAVITY = 2
MOVE_SPEED = 6
JUMP_SPEED = 20

COYOTE_TIME = 0.08
JUMP_BUFFER = 0.12
MAX_JUMPS = 1

CAMERA_LERP = 0.12
WORLD_COLOR = arcade.color.WHITE

PLAYER_PATH = "Materials\Sprite\CoffeeMachine\standart.png"
BLOCK_PATH = "Materials\Sprite\Blocks\\block.png"

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

        self.player_walk_textures = []
        for i in range(1, 7):
            texture = arcade.load_texture(f"Materials/Sprite/CoffeeMachine/Animation/{i}.png")
            self.player_walk_textures.append(texture)

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


# == Game ==


class Platformer(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_W, SCREEN_H, TITLE, antialiasing=True)
        arcade.set_background_color(WORLD_COLOR)

        # == Cameras ==
        self.world_camera = Camera2D()
        self.gui_camera = Camera2D()

        # == Sprites ==
        self.walls = arcade.SpriteList(use_spatial_hash=True)
        self.platforms = arcade.SpriteList()

        # == Player ==
        self.player = None

        # == Physics ==
        self.engine = None

        # == Physics data ==
        self.left = self.right = self.jump_pressed = False
        self.jump_buffer_timer = 0.0
        self.time_since_ground = 999.0
        self.jumps_left = MAX_JUMPS

        # == Text ==
        self.score = 0
        self.batch = Batch()
        self.text_info = arcade.Text(
            "A, D — ходьба • SPACE — прыжок",
            16,
            16,
            arcade.color.GRAY,
            14,
            batch=self.batch,
        )

    # == Player and Game setup ==
    def setup(self):
        self.player = CoffeeMachinePlayer()

        self.player.player_list.clear()
        
        self.player.center_x, self.player.center_y = self.player.spawn_point
        self.player.player_list.append(self.player)

        self.player.load_player_textures()

        # == Test world ==
        for x in range(0, 1600, 64):
            tile = arcade.Sprite(BLOCK_PATH, scale=0.1)
            tile.center_x = x
            tile.center_y = 64
            self.walls.append(tile)

        # == Physics ==
        self.engine = arcade.PhysicsEnginePlatformer(
            player_sprite=self.player,
            gravity_constant=GRAVITY,
            walls=self.walls,
            platforms=self.platforms,
        )

        # == Reset physics data ==
        self.jump_buffer_timer = 0
        self.time_since_ground = 999.0
        self.jumps_left = MAX_JUMPS

    def on_draw(self):
        self.clear()

        # == World drawing ==
        self.world_camera.use()
        self.walls.draw()
        self.platforms.draw()
        self.player.player_list.draw()

        # == GUI ==
        self.gui_camera.use()
        self.batch.draw()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.A:
            self.left = True
        elif key == arcade.key.D:
            self.right = True
        elif key == arcade.key.SPACE:
            self.jump_pressed = True
            self.jump_buffer_timer = JUMP_BUFFER

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

        if self.jump_buffer_timer > 0:
            self.jump_buffer_timer -= dt

        want_jump = self.jump_pressed or (self.jump_buffer_timer > 0)

        if want_jump:
            can_coyote = self.time_since_ground <= COYOTE_TIME
            if grounded or can_coyote:
                self.engine.jump(JUMP_SPEED)
                self.jump_buffer_timer = 0

        self.engine.update()

        self.player.update_player_animation(dt, grounded, moving_x)

        target = (self.player.center_x, self.player.center_y)
        cx, cy = self.world_camera.position
        smooth = (
            cx + (target[0] - cx) * CAMERA_LERP,
            cy + (target[1] - cy) * CAMERA_LERP,
        )

        half_w = self.world_camera.viewport_width / 2
        half_h = self.world_camera.viewport_height / 2

        world_w = 2000
        world_h = 900
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