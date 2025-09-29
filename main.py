import pygame, sys, pytmx

# Inicializando pygame y el mixer para audio
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.mixer.init()
pygame.init()

# configuraciones de la pantalla
WIDTH, HEIGHT = 1024, 768
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Prueba")

# Clock para manejar FPS
clock = pygame.time.Clock()

# Estado del juego
in_menu = True

# cargar assets
fondo_menu = pygame.image.load("assets/prueba_fondo.png").convert()
personaje = pygame.image.load("assets/borrador_robot.png").convert_alpha()
pygame.mixer.music.load("media/music/menu.mp3")
sonido_salto = pygame.mixer.Sound("media/audio/salto.mp3")
canal_movimiento = pygame.mixer.Channel(1)
sonido_movimiento = pygame.mixer.Sound("media/audio/movimiento.mp3")
sonido_movimiento.set_volume(0.4)

# Variables del personaje
player_x, player_y = 100, 300
player_rect = pygame.Rect(player_x, player_y, personaje.get_width(), personaje.get_height())
vel_x, vel_y = 0, 0
velocidad_movimiento = 3
GRAVEDAD = 0.5
en_suelo = False
direccion = "derecha"

# Cámara
cam_x = 0
zoom = 2  # Nivel de zoom (2 = 200%)

# Carga de animaciones

frames_de_pie = [
    pygame.image.load("assets/animations/idle/de_pie1.png").convert_alpha(),
    pygame.image.load("assets/animations/idle/de_pie2.png").convert_alpha(),
    pygame.image.load("assets/animations/idle/de_pie3.png").convert_alpha(),
    pygame.image.load("assets/animations/idle/de_pie4.png").convert_alpha(),
    ]

frames_correr = [
    pygame.image.load("assets/animations/running/corriendo1.png").convert_alpha(),
    pygame.image.load("assets/animations/running/corriendo2.png").convert_alpha(),
    pygame.image.load("assets/animations/running/corriendo3.png").convert_alpha(),
    pygame.image.load("assets/animations/running/corriendo4.png").convert_alpha(),
    pygame.image.load("assets/animations/running/corriendo5.png").convert_alpha(),
]

# Velocidad de animaciones 

frame_index = 0
frame_delay = 0.15  # Cuántos frames esperar antes de cambiar la imagen

# Cargar mapa Tiled

tmx_data = pytmx.util_pygame.load_pygame("assets/maps/mapa1.tmx")

tmx_width = tmx_data.width * tmx_data.tilewidth
tmx_height = tmx_data.height * tmx_data.tileheight
world_surface = pygame.Surface((tmx_width, tmx_height), pygame.SRCALPHA)

# Crear lista de rectángulos para colisiones
collision_rects = []
for x, y, gid in tmx_data.get_layer_by_name("layers_suelo"):
    if gid != 0:
        tile_rect = pygame.Rect(
            x * tmx_data.tilewidth,
            y * tmx_data.tileheight,
            tmx_data.tilewidth,
            tmx_data.tileheight,
        )
        collision_rects.append(tile_rect)

# Punto de inicio del jugador

spawn_point = None
for obj in tmx_data.objects:
    if obj.name == "player":
        spawn_point = (obj.x, obj.y)
        break

if spawn_point:
    player_x, player_y = spawn_point
    player_rect.topleft = (player_x, player_y)

pygame.mixer.music.play(-1) # Reproducir música en bucle

while True: 
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
    
    keys = pygame.key.get_pressed()

    if in_menu:
        screen.blit(fondo_menu, (0, 0))
        if keys[pygame.K_RETURN]:
            in_menu = False
            pygame.mixer.music.stop()
            #pygame.mixer.music.load("media/music/tema1.mp3")
            #pygame.mixer.music.play(-1)
    else:
        # Movimiento horizontal del jugador
        vel_x = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
        player_x += vel_x * velocidad_movimiento
        player_rect.x = player_x

        if vel_x != 0 and en_suelo:
            if not canal_movimiento.get_busy():
                canal_movimiento.play(sonido_movimiento, loops=-1)  
        else:
            canal_movimiento.stop()

        # --- Colisiones en eje X ---
        for tile in collision_rects:
            if player_rect.colliderect(tile):
                if vel_x > 0:  # moviéndose a la derecha
                    player_rect.right = tile.left
                    player_x = player_rect.x
                elif vel_x < 0:  # moviéndose a la izquierda
                    player_rect.left = tile.right
                    player_x = player_rect.x

        # Movimiento vertical del jugador
        vel_y += GRAVEDAD
        player_y += vel_y
        player_rect.y = player_y
        en_suelo = False


        # --- Colisiones en eje Y ---
        for tile in collision_rects:
            if player_rect.colliderect(tile):
                if vel_y > 0:  # cayendo
                    player_rect.bottom = tile.top
                    player_y = player_rect.y
                    vel_y = 0
                    en_suelo = True
                elif vel_y < 0:  # golpeando desde abajo
                    player_rect.top = tile.bottom
                    player_y = player_rect.y
                    vel_y = 0

        # Detección de a donde mira el personaje
        if vel_x > 0:
            direccion = "derecha"
        elif vel_x < 0:
            direccion = "izquierda"

        # Reiniciar al caer fuera de la pantalla
        if player_y > HEIGHT:
            player_x, player_y = spawn_point
            player_rect.topleft = (player_x, player_y)
            vel_x, vel_y = 0, 0
            pygame.mixer.music.rewind() # Reiniciar música

        # Saltar
        if keys[pygame.K_SPACE] and en_suelo:
            vel_y = -15
            vel_x *= 0.5  # Reducir velocidad horizontal al saltar
            sonido_salto.play()

        # camara centrada en el jugador
        cam_x = player_rect.centerx - WIDTH // 2
        cam_y = player_rect.centery - HEIGHT // 2

        #Limitar cámara a los bordes del mapa
        cam_x = max(0, min(cam_x, tmx_width - WIDTH))
        cam_y = max(0, min(cam_y, tmx_height - HEIGHT))

        # --------------------------
        # Manejo de animaciones
        # --------------------------
        if vel_x != 0:
            frame_index += frame_delay
            if frame_index >= len(frames_correr):
                frame_index = 0
            frame_actual = frames_correr[int(frame_index)]
        else:
            frame_index += frame_delay
            if frame_index >= len(frames_de_pie):
                frame_index = 0
            frame_actual = frames_de_pie[int(frame_index)]

        # Voltear imagen si mira a la izquierda
        if direccion == "izquierda":
            frame_actual = pygame.transform.flip(frame_actual, True, False)

        # --------------------------
        # Dibujar Mapa
        # --------------------------
        screen.fill((0, 0, 0))  # Fondo negro antes de pintar
        world_surface.fill((0, 0, 0, 0))
        for layer in tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, gid in layer:
                    tile = tmx_data.get_tile_image_by_gid(gid)
                    if tile:
                        world_surface.blit(tile, (x * tmx_data.tilewidth, y * tmx_data.tileheight))
            
            elif isinstance(layer, pytmx.TiledImageLayer):
                if layer.image:
                    x = getattr(layer, "offsetx", 0)
                    y = getattr(layer, "offsety", 0)
                    world_surface.blit(layer.image, (x,y))
        
        # Dibujar jugador en world_surface
        world_surface.blit(frame_actual, (player_x - cam_x, player_y))

        # Dibujar rectangulo del jugador en pantalla (Hit-box)

        # pygame.draw.rect(world_surface, (255, 0, 0), 
        #         (player_x - cam_x, player_y, player_rect.width, player_rect.height), 2)

        # Definir càmara (rect que sigue al jugador)

        cam_width = WIDTH // zoom
        cam_height = HEIGHT // zoom 
        cam_x = max(0, min(player_rect.centerx - cam_width // 2, tmx_width - cam_width))
        cam_y = max(0, min(player_rect.centery - cam_height // 2, tmx_height - cam_height))
        camera_rect = pygame.Rect(cam_x, cam_y, cam_width, cam_height)

        # Recortar y escalar 
        screen.blit(pygame.transform.scale(world_surface.subsurface(camera_rect), (WIDTH, HEIGHT)), (0, 0))

    pygame.display.flip()
    clock.tick(60)  # Limitar a 60 FPS
