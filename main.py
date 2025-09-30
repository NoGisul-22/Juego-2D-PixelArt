# main.py
import pygame, sys, pytmx, math
from pathlib import Path

# -----------------------
# Configuración básica
# -----------------------
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
pygame.mixer.init()
pygame.mixer.music.set_volume(0.1)  # volumen música
WIDTH, HEIGHT = 1024, 768
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("RUSTWALKER")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont("dejavusans", 40)

ASSET_DIR = Path("assets")
MEDIA_DIR = Path("media")

# DEBUG visual (pon True para ver si on_ground se está calculando)
DEBUG = False

# Helper de carga con fallback
def load_image(path, convert_alpha=True):
    try:
        img = pygame.image.load(str(path))
        return img.convert_alpha() if convert_alpha else img.convert()
    except Exception as e:
        print(f"Error cargando imagen: {path}, {e}")
        w, h = (64, 64)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((255, 0, 255, 128))
        pygame.draw.line(surf, (0, 0, 0), (0, 0), (w, h), 3)
        pygame.draw.line(surf, (0, 0, 0), (0, h), (w, 0), 3)
        return surf

def load_sound(path):
    try:
        return pygame.mixer.Sound(path)
    except Exception:
        return None

# -----------------------
# Clases principales
# -----------------------
class Camera:
    def __init__(self, world_w, world_h, screen_w, screen_h, zoom=1):
        self.world_w = world_w
        self.world_h = world_h
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.zoom = zoom
        cam_w = min(screen_w // zoom, max(1, world_w))
        cam_h = min(screen_h // zoom, max(1, world_h))
        self.rect = pygame.Rect(0, 0, cam_w, cam_h)

    def update(self, target_rect):
        # centrar en el jugador
        self.rect.centerx = target_rect.centerx
        self.rect.centery = target_rect.centery

        # limitar para no salirse del mundo
        self.rect.clamp_ip(pygame.Rect(0, 0, self.world_w, self.world_h))


class Player:
    def __init__(self, x, y):
        # guardar spawn original
        self.start_pos = (x, y)

        # sprites (placeholders)
        self.sprite_idle = load_image(ASSET_DIR/"borrador_robot.png")
        self.sprite_attack = load_image(ASSET_DIR/"animations/attack/atk1.png")

        self.image = self.sprite_idle
        self.rect = self.image.get_rect(topleft=(x, y))

        # posición como float para física suave
        self.pos = pygame.Vector2(float(self.rect.x), float(self.rect.y))
        self.vel_x = 0.0
        self.vel_y = 0.0

        # físicas
        self.speed = 250.0
        self.jump_impulse = 770.0
        self.gravity = 2200.0

        self.on_ground = False
        self.is_jumping = False   # 🔹 flag de si está en animación de salto
        self.image = self.sprite_idle
        self.rect = self.image.get_rect(topleft=(x, y))
        self.direction = 1  # 1 derecha, -1 izquierda

        # animaciones
        self.frames_idle = [
            load_image(ASSET_DIR/"animations/idle/de_pie1.png"),
            load_image(ASSET_DIR/"animations/idle/de_pie2.png"),
        ]
        self.frames_run = [
            load_image(ASSET_DIR/"animations/running/corriendo1.png"),
            load_image(ASSET_DIR/"animations/running/corriendo2.png"),
        ]
        self.frames_jump = [
            load_image(ASSET_DIR/"animations/jump/jump1.png"),
            load_image(ASSET_DIR/"animations/jump/jump2.png"),
            load_image(ASSET_DIR/"animations/jump/jump3.png"),
            load_image(ASSET_DIR/"animations/jump/jump4.png"),
        ]
        self.frames_attack = [
            load_image(ASSET_DIR/"animations/attack/atack1.png"),
            load_image(ASSET_DIR/"animations/attack/atack2.png"),
            load_image(ASSET_DIR/"animations/attack/atack3.png"),
            load_image(ASSET_DIR/"animations/attack/atack4.png"),
            load_image(ASSET_DIR/"animations/attack/atack5.png"),
            load_image(ASSET_DIR/"animations/attack/atack6.png"),
            load_image(ASSET_DIR/"animations/attack/atack7.png"),
            load_image(ASSET_DIR/"animations/attack/atack8.png"),
            load_image(ASSET_DIR/"animations/attack/atack9.png"),
            load_image(ASSET_DIR/"animations/attack/atack10.png"),
            load_image(ASSET_DIR/"animations/attack/atack11.png"),
        ]

        self.frame_idx = 0.0
        self.frame_speed = 8.0

        # ataque
        self.attack_cooldown = 1.5  # segundos entre ataques
        self.attack_timer = 0.0
        self.is_attacking = False
        self.attack_laser_fired = False  # para evitar disparar varias veces en la misma animación
        self.attack_delay = 0.5  # segundos hasta que el láser se dispara en la animación
        self.attack_delay_timer = 0.0
        self.attack_requested = False


    def update(self, dt, keys, collision_rects):
        dt_s = dt / 1000.0
        # solo moverse si NO está atacando
        if not self.is_attacking:
            ax = (1 if keys[pygame.K_RIGHT] else 0) - (1 if keys[pygame.K_LEFT] else 0)
            self.vel_x = ax * self.speed
            if ax != 0:
                self.direction = 1 if ax > 0 else -1
        else:
            # bloqueo: no se mueve horizontalmente
            self.vel_x = 0


        # salto (activar animación aquí SOLO cuando empieza)
        if not self.is_attacking and keys[pygame.K_SPACE] and self.on_ground:
            self.vel_y = -self.jump_impulse
            self.on_ground = False
            self.is_jumping = True   # 🔹 ahora sí marcamos que está en salto
            self.frame_idx = 0.0     # reiniciar anim de salto
            if hasattr(self, 'sound_jump') and self.sound_jump:
                pygame.mixer.Sound.play(self.sound_jump)


        #  gravedad
        self.vel_y += self.gravity * dt_s

        # movimiento X
        self.pos.x += self.vel_x * dt_s
        self.rect.x = int(self.pos.x)
        self._collide_axis(collision_rects, axis="x")

        # movimiento Y
        prev_bottom = self.rect.bottom
        self.pos.y += self.vel_y * dt_s
        self.rect.y = int(self.pos.y)
        self.on_ground = False
        self._collide_axis(collision_rects, axis="y", prev_bottom=prev_bottom)

        # 🔹 si aterrizó, se cancela animación de salto
        if self.on_ground and self.is_jumping:
            self.is_jumping = False

        # ---------------------
        # Animaciones
        # ---------------------

        if self.is_jumping:
            # animación de salto (frames 0-2 al inicio, frame 3 en el aire)
            if self.frame_idx < len(self.frames_jump) - 1:
                self.frame_idx += self.frame_speed * dt_s
                idx = min(int(self.frame_idx), len(self.frames_jump)-2)  # 0..2
            else:
                idx = len(self.frames_jump) - 1  # último frame fijo
            self.image = self.frames_jump[idx]

        elif self.vel_x != 0 and self.on_ground:
            self.frame_idx += self.frame_speed * dt_s
            frames = self.frames_run if self.frames_run else [self.sprite_idle]
            self.image = frames[int(self.frame_idx) % len(frames)]

        else:
            self.frame_idx += self.frame_speed * dt_s
            frames = self.frames_idle if self.frames_idle else [self.sprite_idle]
            self.image = frames[int(self.frame_idx) % len(frames)]

        # dirección
        if self.direction == -1:
            self.image = pygame.transform.flip(self.image, True, False)

        # cooldown ataque
        if self.attack_timer > 0.0:
            self.attack_timer = max(0.0, self.attack_timer - dt_s)

        # animación de ataque (tiene prioridad)
        if self.is_attacking:
            self.frame_idx += self.frame_speed * dt_s
            idx = int(self.frame_idx)
            if idx >= len(self.frames_attack):
                # animación terminó
                self.is_attacking = False
                self.frame_idx = 0.0
                self.image = self.frames_idle[0]
            else:
                img = self.frames_attack[idx]
                # 🔹 flip solo si está mirando a la izquierda
                if self.direction == -1:
                    img = pygame.transform.flip(img, True, False)
                self.image = img


    def _collide_axis(self, rects, axis, prev_bottom=None):
        """
        rects: lista de pygame.Rect (colisiones)
        axis: "x" o "y"
        prev_bottom: bottom del rect antes del movimiento vertical (int) - se usa para detectar aterrizajes
        """
        for r in rects:
            if self.rect.colliderect(r):
                if axis == "x":
                    if self.vel_x > 0:
                        self.rect.right = r.left
                    elif self.vel_x < 0:
                        self.rect.left = r.right
                    # sincronizar pos con rect para evitar drift
                    self.pos.x = float(self.rect.x)
                    self.vel_x = 0.0
                else:  # eje y
                    # 1) Si venimos desde arriba (prev_bottom <= r.top) -> aterrizaje
                    landed = False
                    if prev_bottom is not None and prev_bottom <= r.top:
                        landed = True
                    # 2) si la velocidad vertical es positiva (estamos cayendo) -> también aterrizamos
                    if self.vel_y > 0 or landed:
                        # colocar al jugador encima de la plataforma
                        self.rect.bottom = r.top
                        self.on_ground = True
                        self.pos.y = float(self.rect.y)
                        self.vel_y = 0.0
                    elif self.vel_y < 0:
                        # golpeo la cabeza por debajo
                        self.rect.top = r.bottom
                        self.pos.y = float(self.rect.y)
                        self.vel_y = 0.0
                    else:
                        # caso extremo: vel_y == 0 y prev_bottom > r.top (ya estaba dentro)
                        # hacemos una corrección defensiva (p. ej. si queda superpuesto por 1-2px)
                        if self.rect.bottom > r.top and self.rect.top < r.top:
                            # empujar hacia arriba y marcar como on_ground
                            self.rect.bottom = r.top
                            self.on_ground = True
                            self.pos.y = float(self.rect.y)
                            self.vel_y = 0.0

    def attack_ready(self):
        return self.attack_timer <= 0.0

    def do_attack(self):
        self.attack_timer = self.attack_cooldown

    def reset(self):
        """Reinicia al jugador en la posición inicial"""
        self.rect.topleft = self.start_pos
        self.pos = pygame.Vector2(float(self.rect.x), float(self.rect.y))
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.on_ground = False
        self.attack_timer = 0.0
        self.frame_idx = 0.0

class Laser:
    def __init__(self, x, y, direction, speed=200, length=100):
        self.pos = pygame.Vector2(x, y)
        self.start_x = x            # <<< guardamos posición inicial
        self.direction = direction  # 1 = derecha, -1 = izquierda
        self.speed = speed          # px/s
        self.length = length        # longitud máxima del láser
        self.active = True
        # Rect para colisión (por si no se desea usar un sprite)
        #self.rect = pygame.Rect(self.pos.x, self.pos.y - 4, 16, 8)  

        # cargar imagen del láser - en caso de no querer usar un rect
        self.image = load_image(ASSET_DIR/"animations/bullet/bala.png")
        # ajustar rect según tamaño de la imagen
        self.rect = self.image.get_rect(center=(x, y))

    def update(self, dt):
        dt_s = dt / 1000.0
        # avanzar en X
        self.pos.x += self.speed * dt_s * self.direction
        self.rect.x = int(self.pos.x)

        # desactivar si ha recorrido más que su longitud
        if abs(self.pos.x - self.start_x) > self.length:
            self.active = False

    def draw(self, surf, camera):
    # calcular posición relativa a la cámara
        screen_pos = (self.rect.x - camera.rect.x, self.rect.y - camera.rect.y)
        surf.blit(self.image, screen_pos)


class Enemy:
    def __init__(self, x, y, w=32, h=32, speed=100, frames=None):
        self.frames = frames or []
        self.frame_idx = 0.0
        self.frame_speed = 6.0  # frames por segundo
        self.image = self.frames[0] if self.frames else load_image(ASSET_DIR/"enemy_placeholder.png")

        # usar centro para que las rutas funcionen correctamente
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = speed  # pixels/segundo
        self.path = []      # lista de puntos [(x,y), ...]
        self.path_idx = 0
        self.forward = True
        self.hp = 1
        self.dead = False

    def update(self, dt):
        if self.dead: return

        # Animación
        if self.frames:
            self.frame_idx += self.frame_speed * (dt / 1000.0)
            self.image = self.frames[int(self.frame_idx) % len(self.frames)]

        # Movimiento por ruta
        if not self.path: return

        target = pygame.Vector2(self.path[self.path_idx])
        pos = pygame.Vector2(self.rect.center)
        dir_vec = target - pos
        dist = dir_vec.length()

        if dist < 2:
            # cambiar de punto
            if self.forward:
                self.path_idx += 1
                if self.path_idx >= len(self.path):
                    self.path_idx = max(0, len(self.path)-1)
                    self.forward = False
            else:
                self.path_idx -= 1
                if self.path_idx < 0:
                    self.path_idx = 0
                    self.forward = True
        else:
            vel = dir_vec.normalize() * self.speed * (dt / 1000.0)
            self.rect.centerx += vel.x
            self.rect.centery += vel.y

    def reset(self):
        self.rect.center = self.path[0] if self.path else self.rect.center
        self.path_idx = 0
        self.forward = True
        self.dead = False
        self.hp = 1
        self.frame_idx = 0.0

    def draw(self, surf, camera):
        if self.dead: return
        screen_pos = (self.rect.x - camera.rect.x, self.rect.y - camera.rect.y)
        surf.blit(self.image, screen_pos)

class Explosion:
    def __init__(self, x, y, frames, frame_speed=12.0):
        self.frames = frames
        self.frame_idx = 0.0
        self.frame_speed = frame_speed  # frames por segundo
        self.image = self.frames[0] if self.frames else None
        self.rect = self.image.get_rect(center=(x, y)) if self.image else pygame.Rect(x, y, 32, 32)
        self.finished = False

    def update(self, dt):
        if self.finished: return
        self.frame_idx += self.frame_speed * (dt / 1000.0)
        idx = int(self.frame_idx)
        if idx >= len(self.frames):
            self.finished = True
        else:
            self.image = self.frames[idx]

    def draw(self, surf, camera):
        if self.finished: return
        screen_pos = (self.rect.x - camera.rect.x, self.rect.y - camera.rect.y)
        surf.blit(self.image, screen_pos)


class Dron(Enemy):
    def __init__(self, x, y):
        frames = [
            load_image(ASSET_DIR/"animations/enemies/dron/dron1.png"),
            load_image(ASSET_DIR/"animations/enemies/dron/dron2.png"),
            load_image(ASSET_DIR/"animations/enemies/dron/dron3.png"),
            load_image(ASSET_DIR/"animations/enemies/dron/dron4.png"),
            load_image(ASSET_DIR/"animations/enemies/dron/dron5.png"),
            load_image(ASSET_DIR/"animations/enemies/dron/dron6.png"),
            load_image(ASSET_DIR/"animations/enemies/dron/dron7.png"),
        ]
        super().__init__(x, y, w=48, h=24, speed=180, frames=frames)  # velocidad pixels/sec

class Slime(Enemy):
    def __init__(self, x, y):
        frames = [
            load_image(ASSET_DIR/"animations/enemies/slime/slime1.png"),
            load_image(ASSET_DIR/"animations/enemies/slime/slime2.png"),
            load_image(ASSET_DIR/"animations/enemies/slime/slime3.png"),
            load_image(ASSET_DIR/"animations/enemies/slime/slime4.png"),
            load_image(ASSET_DIR/"animations/enemies/slime/slime5.png"),
        ]
        super().__init__(x, y, w=32, h=24, speed=120, frames=frames)

def is_on_ground(player, collision_rects):
    """Devuelve True si hay suelo justo debajo del jugador"""
    test_rect = player.rect.move(0, 2)  # desplazamos 2px hacia abajo
    for r in collision_rects:
        if test_rect.colliderect(r):
            return True
    return False


# -----------------------
# Motor del juego
# -----------------------
class Game:
    def __init__(self, map_paths):
        self.maps = map_paths           # lista de rutas TMX
        self.map_backgrounds = {
            "Mapa1": ASSET_DIR/"map1.png",
            "Mapa2": ASSET_DIR/"map2.png"
           }   # fondos por mapa 
        self.map_music = {
            "Mapa1": MEDIA_DIR/"music/map1.mp3",
            "Mapa2": MEDIA_DIR/"music/map2.mp3"
        }
        self.current_map_index = 0      # índice del mapa actual
        self.world_completed = False
        self.level_transition_timer = 0.0  # tiempo que mostramos mensaje "Completado"
        # estados
        self.state = "menu"  # "menu" o "playing"
        # cargar primer mapa
        self._load_map(self.maps[self.current_map_index])
        # spawn
        sp = self._find_object_by_name("player")
        sx, sy = (sp.x, sp.y) if sp else (100, 100)
        self.player = Player(sx, sy)
        self.player.sound_jump = load_sound(MEDIA_DIR/"audio"/"salto.mp3")
        # camara
        self.camera = Camera(self.world_w, self.world_h, WIDTH, HEIGHT, zoom=1)
        # ataques
        self.lasers = []
        # Cargar frames de explosión
        self.explosion_frames = [
            load_image(ASSET_DIR/"animations/explosion/explosion1.png"),
            load_image(ASSET_DIR/"animations/explosion/explosion2.png"),
            load_image(ASSET_DIR/"animations/explosion/explosion3.png"),
            load_image(ASSET_DIR/"animations/explosion/explosion4.png"),
            load_image(ASSET_DIR/"animations/explosion/explosion5.png"),
        ]
        self.explosions = []  # lista de explosiones activas    
        # cargar enemigos desde objetos
        self.enemies = []
        self._load_enemies_from_tiled()
        # hud / mundo
        self.world_name = "MUNDO 1"
        self.world_completed = False

        # assets UI/menu
        self.menu_bg = load_image(ASSET_DIR/"portada.jpeg", convert_alpha=False)
        self.music_menu = self._load_music_safe(MEDIA_DIR/"music"/"menu.mp3")
        self.sound_jump = load_sound(MEDIA_DIR/"audio"/"salto.mp3")
        self.sound_move = load_sound(MEDIA_DIR/"audio"/"movimiento.mp3")
        self.sound_attack = load_sound(MEDIA_DIR/"audio"/"ataque.mp3")
        self.sound_explosion = load_sound(MEDIA_DIR/"audio"/"explosion.mp3")        
        self.sound_move.set_volume(0.1) # Volumen más bajo para el movimiento
        self.sound_jump.set_volume(0.8) # Volumen medio para el salto
        self.sound_attack.set_volume(0.3) # Volumen medio para el ataque
        self.sound_explosion.set_volume(0.7) # Volumen más alto para la explosión
        # canales de sonido dedicados
        self.move_channel = pygame.mixer.Channel(1)
        self.jump_channel = pygame.mixer.Channel(2)
        self.explosion_channel = pygame.mixer.Channel(3)
        self.attack_channel = pygame.mixer.Channel(4)
        if self.music_menu:
            pygame.mixer.music.load(str(self.music_menu))
            pygame.mixer.music.play(-1)

        # optimization: precompute tile surface? We'll draw visible tiles only.
        self.tile_cache = None

        # menu cursor
        self.menu_options = ["INICIAR", "SALIR"]
        self.menu_idx = 0

    def _load_map(self, map_path):
        self.tmx = pytmx.util_pygame.load_pygame(map_path)
        self.world_w = self.tmx.width * self.tmx.tilewidth
        self.world_h = self.tmx.height * self.tmx.tileheight
        self.collision_rects = self._load_collision_rects()

        # spawn jugador
        sp = self._find_object_by_name("player")
        sx, sy = (sp.x, sp.y) if sp else (100, 100)
        if hasattr(self, "player"):
            self.player.reset()
            self.player.start_pos = (sx, sy)
        else:
            self.player = Player(sx, sy)

        # cámara
        self.camera = Camera(self.world_w, self.world_h, WIDTH, HEIGHT, zoom=1)

        # enemigos
        self.enemies = []
        self._load_enemies_from_tiled()

        # HUD
        self.world_name = f"MUNDO {self.current_map_index + 1}"

        # asignar fondo automáticamente según diccionario
        bg_file = self.map_backgrounds.get(map_path.stem)
        if bg_file:
            self.bg_image = load_image(bg_file, convert_alpha=False)
        else:
            self.bg_image = None

        # cargar música específica del mapa
        music_file = self.map_music.get(map_path.stem)
        if music_file and music_file.exists():
            try:
                pygame.mixer.music.load(str(music_file))
                pygame.mixer.music.play(-1)
            except Exception as e:
                print(f"No se pudo reproducir música para {map_path.stem}: {e}")
        else:
            pygame.mixer.music.stop()  # si no hay música, parar


    def _load_music_safe(self, p):
        try:
            return str(p)
        except Exception:
            return None

    def _find_object_by_name(self, name):
        for obj in self.tmx.objects:
            if obj.name == name:
                return obj
        return None

    def _load_collision_rects(self):
        rects = []
        # intentamos varias nombres usuales (español/inglés) y si no, tomamos la primera capa de tiles
        layer = None
        candidates = ["layers_suelo", "suelo", "collision", "colisiones",
                  "Collision", "Capa de colisiones", "Capa de patrones 1", "capa de patrones 1"]
        for c in candidates:
            try:
                layer = self.tmx.get_layer_by_name(c)
                break
            except Exception:
                layer = None

        if layer is None:
            # fallback: primera capa de tiles visible
            for lay in self.tmx.layers:
                if isinstance(lay, pytmx.TiledTileLayer):
                    layer = lay
                    break

        if layer:
            tw = self.tmx.tilewidth
            th = self.tmx.tileheight
            # iterar por todos los tiles de esa capa
            for x, y, gid in layer:
                if gid:
                    rects.append(pygame.Rect(x * tw, y * th, tw, th))
        else:
            # fallback final: buscar objetos tipo/nombre 'collision'
            for obj in self.tmx.objects:
                t = (obj.type or "").lower()
                n = (obj.name or "").lower()
                if t == "collision" or n == "collision":
                    rects.append(pygame.Rect(obj.x, obj.y, obj.width, obj.height))

        # DEBUG: imprime cuántos rects de colisión tenemos (puedes comentar)
        if DEBUG:
            print("Collision rects:", len(rects))

        return rects

    def _parse_route_prop(self, prop):
        # acepta "x1,y1;x2,y2"
        pts = []
        if not prop: return pts
        for seg in prop.split(";"):
            try:
                x, y = seg.split(",")
                pts.append((float(x), float(y)))
            except:
                continue
        return pts

    def _load_enemies_from_tiled(self):
        print("Objetos en TMX:")
        for obj in self.tmx.objects:
            print(f"Nombre: {obj.name}, Tipo: {obj.type}, X: {obj.x}, Y: {obj.y}, Puntos: {getattr(obj,'points',None)}")

        for obj in self.tmx.objects:
            name = (obj.name or "").lower()
            typ = (obj.type or "").lower()

            # determinar tipo de enemigo
            if name in ("dron", "slime") or typ in ("dron", "slime"):
                x, y = obj.x, obj.y
                if name == "dron" or typ == "dron":
                    e = Dron(x, y)
                else:
                    e = Slime(x, y)

                # si el objeto tiene polyline
                if hasattr(obj, "points") and obj.points:
                    e.path = [(px, py) for (px, py) in obj.points]
                else:
                    # propiedad 'route' tipo "x1,y1;x2,y2"
                    route_prop = getattr(obj, "properties", {}).get("route")
                    if route_prop:
                        pts = []
                        for seg in route_prop.split(";"):
                            try:
                                px, py = seg.split(",")
                                pts.append((float(px), float(py)))
                            except:
                                continue
                        e.path = pts
                    else:
                        # fallback: patrulla horizontal simple
                        e.path = [(x, y), (x + 128, y)]

                self.enemies.append(e)


    def draw_map_region(self, surf, camera):
        # dibuja solo tiles visibles dentro de camera.rect
        tw, th = self.tmx.tilewidth, self.tmx.tileheight
        left = max(0, camera.rect.x // tw - 1)
        right = min(self.tmx.width, (camera.rect.right // tw) + 2)
        top = max(0, camera.rect.y // th - 1)
        bottom = min(self.tmx.height, (camera.rect.bottom // th) + 2)

        for layer in self.tmx.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                for x in range(left, right):
                    for y in range(top, bottom):
                        gid = layer.data[y][x]
                        if gid:
                            tile = self.tmx.get_tile_image_by_gid(gid)
                            if tile:
                                sx = x*tw - camera.rect.x
                                sy = y*th - camera.rect.y
                                surf.blit(tile, (sx, sy))
            elif isinstance(layer, pytmx.TiledImageLayer):
                if layer.image:
                    sx = getattr(layer, "offsetx", 0) - camera.rect.x
                    sy = getattr(layer, "offsety", 0) - camera.rect.y
                    surf.blit(layer.image, (sx, sy))

    def run(self):
        running = True
        while running:
            dt = clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if self.state == "menu":
                        if event.key == pygame.K_UP:
                            self.menu_idx = (self.menu_idx - 1) % len(self.menu_options)
                        elif event.key == pygame.K_DOWN:
                            self.menu_idx = (self.menu_idx + 1) % len(self.menu_options)
                        elif event.key == pygame.K_RETURN:
                            if self.menu_options[self.menu_idx] == "INICIAR":
                                self.state = "playing"
                                pygame.mixer.music.stop()
                                self._load_map(self.maps[self.current_map_index])
                            elif self.menu_options[self.menu_idx] == "SALIR":
                                running = False
                    else:
                        # atajos en juego
                        if event.key == pygame.K_n:
                            # marcar mundo completado (ejemplo)
                            self.world_completed = True
                            self.level_transition_timer = 2.0  # segundos para transición
                        if event.key == pygame.K_ESCAPE:
                            self.reset_to_menu()
                            if self.music_menu:
                                pygame.mixer.music.load(self.music_menu)
                                pygame.mixer.music.play(-1)

            keys = pygame.key.get_pressed()
            if self.state == "menu":
                self.update_menu(keys)
                self.render_menu()
            else:
                self.update_game(keys, dt)
                self.render_game()

            pygame.display.flip()
        pygame.quit()
        sys.exit()

    def update_menu(self, keys):
        # opcional: animaciones o música ya está corriendo
        pass

    def render_menu(self):
        screen.fill((0,0,0))
        if self.menu_bg:
            screen.blit(pygame.transform.scale(self.menu_bg, (WIDTH, HEIGHT)), (0,0))
        # dibujar opciones
        title_surf = FONT.render("RUSTWALKER", True, (0,255,0))
        screen.blit(title_surf, (WIDTH//2 - title_surf.get_width()//2, 80))
        for i, opt in enumerate(self.menu_options):
            col = (255,255,0) if i == self.menu_idx else (0,255,0)
            txt = FONT.render(opt, True, col)
            screen.blit(txt, (WIDTH//2 - txt.get_width()//2, 240 + i*40))

    def update_game(self, keys, dt):
        # actualizar jugador
        self.player.update(dt, keys, self.collision_rects)

        # sonido de movimiento en suelo (usando chequeo real bajo el jugador)
        if abs(self.player.vel_x) > 0.1 and is_on_ground(self.player, self.collision_rects) and self.sound_move:
            if not self.move_channel.get_busy():
                self.move_channel.play(self.sound_move, loops=-1)
        else:
            if self.move_channel:
                self.move_channel.stop()

        # detectar la pulsación de Z
        attack_rect = None
        if keys[pygame.K_z] and self.player.attack_ready() and not self.player.attack_requested:
            self.player.attack_requested = True
            self.player.do_attack()
            self.player.is_attacking = True
            self.player.frame_idx = 0.0
            self.player.attack_delay_timer = self.player.attack_delay  # 0.5 s
            self.attack_channel.play(self.sound_attack)

        # manejar delay de ataque
        if self.player.attack_requested:
            self.player.attack_delay_timer -= dt / 1000.0
            if self.player.attack_delay_timer <= 0:
                # ataque listo, disparar láser
                self.player.attack_requested = False  # reset

                # crear el láser
                laser = Laser(
                    x=self.player.rect.centerx - 10,
                    y=self.player.rect.centery + 20,
                    direction=self.player.direction,
                    speed=500,
                    length=380
                )
                self.lasers.append(laser)



        # actualizar láseres
        for laser in self.lasers[:]:
            laser.update(dt)
            for e in self.enemies:
                if not e.dead and laser.rect.colliderect(e.rect):
                    e.hp -= 1
                    e.dead = (e.hp <= 0)
                    self.explosion_channel.play(self.sound_explosion)  # sonido de explosión
                    
                    # crear explosión en el centro del enemigo
                    explosion = Explosion(e.rect.centerx, e.rect.centery, self.explosion_frames)
                    self.explosions.append(explosion)

                    laser.active = False  # el láser desaparece al impactar
            if not laser.active:
                self.lasers.remove(laser)   

        # colisiones con enemigos
        for e in self.enemies:
            e.update(dt)
            if attack_rect and not e.dead:
                if attack_rect.colliderect(e.rect):
                    e.hp -= 1
                    e.dead = (e.hp <= 0)

        for e in self.enemies:
            if not e.dead and self.player.rect.colliderect(e.rect):
                # si el jugador colisiona con un enemigo vivo, reiniciar
                self.player.reset()
                #reiniciar enemigos tambien
                for en in self.enemies:
                    en.reset()
                break # no necesitamos chequear más

        # reinicio si cae
        if self.player.rect.top > self.world_h + 200:
            self.player.reset()
            for e in self.enemies:
                e.reset()

        # cámara
        self.camera.update(self.player.rect)

        # guardar el attack_rect para dibujar en render
        self._attack_rect = attack_rect
        if self.world_completed:
            self.level_transition_timer -= dt / 1000.0
            if self.level_transition_timer <= 0:
                # pasar al siguiente mapa
                self.current_map_index += 1
                if self.current_map_index >= len(self.maps):
                    # volver al menú
                    self.reset_to_menu()
                else:
                    self._load_map(self.maps[self.current_map_index])
                self.world_completed = False

        for exp in self.explosions[:]:
            exp.update(dt)
            if exp.finished:
                self.explosions.remove(exp)



    def render_game(self):
        # limpiar pantalla
        if self.bg_image:
            bg_x = -self.camera.rect.x * 0.5  # mueve la mitad de rápido
            bg_y = -self.camera.rect.y * 0.5
            screen.blit(pygame.transform.scale(self.bg_image, (WIDTH, HEIGHT)), (0,0))
        else:
            screen.fill((0,0,0))

        # surface temporal del tamaño de la cámara
        cam_surface = pygame.Surface((self.camera.rect.w, self.camera.rect.h)).convert_alpha()
        cam_surface.fill((0,0,0,0))

        # dibujar tiles visibles en relación a la cámara
        self.draw_map_region(cam_surface, self.camera)

        # dibujar enemigos
        for e in self.enemies:
            if not e.dead:
                ex = e.rect.x - self.camera.rect.x
                ey = e.rect.y - self.camera.rect.y
                cam_surface.blit(e.image, (ex, ey))

        # dibujar jugador
        px = self.player.rect.x - self.camera.rect.x
        py = self.player.rect.y - self.camera.rect.y
        cam_surface.blit(self.player.image, (px, py)) 
         
         # dibujar láseres
        for laser in self.lasers:
            laser.draw(cam_surface, self.camera)

        # dibujar explosiones
        for exp in self.explosions:
            exp.draw(cam_surface, self.camera)


        # escalar la cámara a la pantalla final
        screen.blit(pygame.transform.scale(cam_surface, (WIDTH, HEIGHT)), (0,0))

        # HUD: nombre del mundo
        txt = FONT.render(self.world_name + (" - COMPLETADO" if self.world_completed else ""), True, (255,255,255))
        screen.blit(txt, (10,10))

        # dibujar hitbox de ataque (relativa a la cámara)
        if getattr(self, "_attack_rect", None):
            ar = self._attack_rect
            scr_rect = pygame.Rect(ar.x - self.camera.rect.x, ar.y - self.camera.rect.y, ar.w, ar.h)
            pygame.draw.rect(screen, (255, 100, 0), scr_rect, 2)

        # debug: dibujar colisiones
        if DEBUG:
            for r in self.collision_rects:
                rr = pygame.Rect(r.x - self.camera.rect.x, r.y - self.camera.rect.y, r.w, r.h)
                pygame.draw.rect(screen, (0,255,0), rr, 1)
            # indicador on_ground
            col = (0,255,0) if self.player.on_ground else (255,0,0)
            pygame.draw.circle(screen, col, (30, 30), 8)

        if self.world_completed:
            msg = FONT.render("¡MUNDO COMPLETADO!", True, (255, 255, 0))
            screen.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2 - msg.get_height()//2))

    def reset_to_menu(self):
        self.state = "menu"
        self.current_map_index = 0
        self.world_completed = False
        self.level_transition_timer = 0.0
        # reiniciar jugador y enemigos del primer mapa
        self._load_map(self.maps[self.current_map_index])
        self.player.reset()
        for e in self.enemies:
            e.reset()
        # música del menú
        if self.music_menu:
            pygame.mixer.music.load(self.music_menu)
            pygame.mixer.music.play(-1)



# -----------------------
# Ejecutar
# -----------------------
if __name__ == "__main__":
    mapfiles = [
        ASSET_DIR/"maps"/"Mapa1.tmx",
        ASSET_DIR/"maps"/"Mapa2.tmx",
    ]
    mapfiles = [m for m in mapfiles if m.exists()]
    if not mapfiles:
        print("No se encontraron mapas.")
        pygame.quit()
        sys.exit()
    
    game = Game(mapfiles)
    game.run()
