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

PLAYER_PATH = "Materials/Sprite/CoffeeMachine/standart.png"
BLOCK_PATH = "Materials/Sprite/Blocks/block.png"

BULLET_PATH = "Materials/Sprite/Bob/bullet.png"
BULLET_TEXTURES = [
    arcade.load_texture(f"Materials/Sprite/Bob/{i}.png")
    for i in range(1, 8)
]

SHOOT_COOLDOWN = 0.5  
BULLET_SPEED = 5

# == Player ==


class CoffeeMachinePlayer(arcade.Sprite):
    def __init__(self):
        super().__init__(PLAYER_PATH, scale=0.12)

        self.player_list = arcade.SpriteList()

        self.spawn_point = (128, 256)
        self.player_is_shooting = False
        self.shoot_current_frame = 0
        self.shoot_frame_time = 0.0
        self.shoot_frame_duration = 0.06
        self.player_frame_time = 0.0
        self.player_current_frame = 0
        self.player_frame_duration = 0.1
        self.player_facing_right = True
        self.player_is_walking = False
        self.player_is_jumping = False

        # == Load textures for animation ==
    def load_player_textures(self):
        self.player_idle_texture = arcade.load_texture(PLAYER_PATH)

        # === SHOOT animation ===
        self.player_shoot_textures = [
            arcade.load_texture(f"Materials/Sprite/Bob/{i}.png")
            for i in range(1, 8)
        ]

        # === Walk animation ===
        self.player_walk_textures = [
        arcade.load_texture(f"Materials/Sprite/CoffeeMachine/Animation/{i}.png")
        for i in range(1, 7)
        ]

        self.player_jump_texture = self.player_idle_texture

        # == Animation Shoot ==
    def start_shoot_animation(self):
        self.player_is_shooting = True
        self.shoot_current_frame = 0
        self.shoot_frame_time = 0.0
    
    def update_player_animation(self, dt, grounded, moving_x):
        
        # ===== SHOOT (priority) =====
        if self.player_is_shooting:
            self.shoot_frame_time += dt

            if self.shoot_frame_time >= self.shoot_frame_duration:
                self.shoot_frame_time = 0
                self.shoot_current_frame += 1

                if self.shoot_current_frame >= len(self.player_shoot_textures):
                    self.player_is_shooting = False
                    return

            texture = self.player_shoot_textures[self.shoot_current_frame]
            if not self.player_facing_right:
                texture = texture.flip_left_right()

            self.texture = texture
            return
        
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


class ShootEffect(arcade.Sprite):
    def __init__(self, x, y, facing_right):
        super().__init__(scale=0.1)
        self.textures = BULLET_TEXTURES
        self.texture = self.textures[0]

        self.center_x = x
        self.center_y = y

        self.frame = 0
        self.time = 0
        self.frame_duration = 0.05
        self.facing_right = facing_right

    def update(self, delta_time: float = 1/60):
        self.time += delta_time
        if self.time >= self.frame_duration:
            self.time = 0
            self.frame += 1

            if self.frame >= len(self.textures):
                self.remove_from_sprite_lists()
                return

            tex = self.textures[self.frame]
            if not self.facing_right:
                tex = tex.flip_left_right()
            self.texture = tex





class Bullet(arcade.Sprite):
    def __init__(self, x, y, direction):
        super().__init__(scale=0.07)  
        self.textures = BULLET_TEXTURES
        self.texture = self.textures[0]


        self.center_x = x
        self.center_y = y
        self.change_x = BULLET_SPEED * direction

        self.frame = 0
        self.frame_time = 0.0
        self.frame_duration = 0.06

    
    def update(self, delta_time: float = 1/60):
        self.center_x += self.change_x

        self.frame_time += delta_time
        if self.frame_time >= self.frame_duration:
            self.frame_time = 0
            self.frame = (self.frame + 1) % len(self.textures)
            self.texture = self.textures[self.frame]


class Platformer(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_W, SCREEN_H, TITLE, antialiasing=True)
        arcade.set_background_color(WORLD_COLOR)
        # Bullets
        self.shot_fired_this_animation = False
        self.shoot_timer = 0.0
        self.shoot_effects = arcade.SpriteList()


        # == Cameras ==
        self.world_camera = Camera2D()
        self.gui_camera = Camera2D()

        # == Sprites ==
        self.walls = arcade.SpriteList()
        self.platforms = arcade.SpriteList()

        # == Player ==
        self.player = None
        
        # == Bullets ==
        self.bullets = arcade.SpriteList()

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
            "A, D — ходьба • SPACE — прыжок • F — стрельба",
            16,
            16,
            arcade.color.GRAY,
            14,
            batch=self.batch,
        )

    # == Player and Game setup ==
    def setup(self):
        # == Player ==
        self.player = CoffeeMachinePlayer()
        self.player.player_list.clear()
        self.player.center_x, self.player.center_y = self.player.spawn_point
        self.player.player_list.append(self.player)
        self.player.load_player_textures()

        # == Load tile map from Tiled ==
        map_name = "Materials/Sprite/Test.tmx"
        tile_map = arcade.load_tilemap(map_name, scaling=0.5)

        self.walls = tile_map.sprite_lists["Walls"]

        # == Physics ==
        self.engine = arcade.PhysicsEnginePlatformer(
            player_sprite=self.player,
            gravity_constant=GRAVITY,
            walls=self.walls,
            platforms=self.platforms
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
        self.bullets.draw()
        self.shoot_effects.draw()

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
        elif key == arcade.key.F:
            self.shoot()


    def on_key_release(self, key, modifiers):
        if key == arcade.key.A:
            self.left = False
        elif key == arcade.key.D:
            self.right = False
        elif key == arcade.key.SPACE:
            self.jump_pressed = False
            if self.player.change_y > 0:
                self.player.change_y *= 0.45
    
    def shoot(self):
        if self.shoot_timer > 0:
            return

        self.shoot_timer = SHOOT_COOLDOWN
        
        effect = ShootEffect(
            self.player.center_x + (1 if self.player.player_facing_right else -1) * (self.player.width // 2),
            self.player.center_y + 16,
            self.player.player_facing_right
        )

        self.player.start_shoot_animation()
        self.shot_fired_this_animation = False
        self.shoot_effects.append(effect)   
        self.player.start_shoot_animation()

    def on_update(self, dt):
        # ===== Timers =====
        if self.shoot_timer > 0:
            self.shoot_timer -= dt

        if self.jump_buffer_timer > 0:
            self.jump_buffer_timer -= dt
         # ===== Horizontal movement =====
        move = 0
        moving_x = False

        if self.left and not self.right:
            move = -MOVE_SPEED
            moving_x = True
        elif self.right and not self.left:
            move = MOVE_SPEED
            moving_x = True

        self.player.change_x = move 
        # ===== Jumping =====
        grounded_before = self.engine.can_jump(y_distance=6)

        if grounded_before:
            self.time_since_ground = 0
            self.jumps_left = MAX_JUMPS
        else:
            self.time_since_ground += dt
        
        want_jump = self.jump_pressed or (self.jump_buffer_timer > 0)

        if want_jump:
            can_coyote = self.time_since_ground <= COYOTE_TIME
            if grounded_before or can_coyote:
                self.engine.jump(JUMP_SPEED)
                self.jump_buffer_timer = 0
        # ===== Physics =====
        self.engine.update()
        
        # === Fire bullet on shoot frame ===
        if self.player.player_is_shooting:
            if (
                self.player.shoot_current_frame == 2  # 3-й кадр
                and not self.shot_fired_this_animation
            ):
                direction = 1 if self.player.player_facing_right else -1
                bullet = Bullet(
                    self.player.center_x + direction * (self.player.width // 2 + 10),
                    self.player.center_y + 8,
                    direction
                )
                self.bullets.append(bullet)
                self.shot_fired_this_animation = True


        # ===== Ground check AFTER physics (for animation) =====
        grounded = self.engine.can_jump(y_distance=6)

        # ===== Bullets =====
        self.bullets.update()
        
        # ===== Shoot effects =====
        self.shoot_effects.update()

        for bullet in self.bullets:
            if arcade.check_for_collision_with_list(bullet, self.walls):
                bullet.remove_from_sprite_lists()
        

        self.player.update_player_animation(dt, grounded, moving_x)
            # ===== Camera =====
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