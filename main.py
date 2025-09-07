import pygame, sys

# Inicializando pygame (sin audio)
# pygame.mixer.pre_init(44100, -16, 2, 512)
# pygame.mixer.init()
pygame.init()

# configuraciones de la pantalla
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Prueba")

# Clock para manejar FPS
clock = pygame.time.Clock()

# Estado del juego
in_menu = True

# cargar assets
fondo_menu = pygame.image.load("assets/prueba_fondo.png").convert()
personaje = pygame.image.load("assets/borrador_robot.png").convert_alpha()
# pygame.mixer.music.load("media/music/menu.mp3")

# Variables del personaje
player_x, player_y = 100, 300
player_rect = pygame.Rect(player_x, player_y, personaje.get_width(), personaje.get_height())
vel_x, vel_y = 0, 0
velocidad_movimiento = 5
GRAVEDAD = 0.5 
en_suelo = False

# Ejemplo: Rectángulo para colisiones
suelo_rect = pygame.Rect(0, 500, 2000, 100)

# Cámara
cam_x = 0

# pygame.mixer.music.play(-1) # Reproducir música en bucle

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
            # pygame.mixer.music.stop()
    else:
        # Movimiento horizontal del jugador
        vel_x = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
        player_x += vel_x * velocidad_movimiento
        player_rect.x = player_x

        # Movimiento vertical del jugador
        vel_y += GRAVEDAD
        player_y += vel_y
        player_rect.y = player_y


        # Colisiones con el suelo
        if player_rect.colliderect(suelo_rect):
            if vel_y > 0:
                player_y = suelo_rect.top - personaje.get_height()
                player_rect.y = player_y
                vel_y = 0
                en_suelo = True
                print("Tocando suelo") 
            else:
                en_suelo = False
        else:
            en_suelo = False
            print("En el aire") 

        # Reiniciar al caer fuera de la pantalla
        if player_y > HEIGHT:
            player_x, player_y = 100, 300
            player_rect.topleft = (player_x, player_y)
            vel_x, vel_y = 0, 0

        # Saltar
        if keys[pygame.K_SPACE] and en_suelo:
            vel_y = -10

        # camara centrada en el jugador
        cam_x = player_x - WIDTH // 2

        # Dibujar todo
        screen.fill((135, 206, 235))  # Cielo
        pygame.draw.rect(screen, (50, 200, 50), suelo_rect.move(-cam_x, 0))  # Suelo
        screen.blit(personaje, (player_x - cam_x, player_y))

    pygame.display.flip()
    clock.tick(60)  # Limitar a 60 FPS
