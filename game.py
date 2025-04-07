import pygame
import socket
import threading
import queue

# Game settings
SCREEN_WIDTH, SCREEN_HEIGHT = 640, 480
PLAYER_SIZE = 50
MOVE_DISTANCE = 50

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("TCP Controlled Pygame")

# Player starting position (centered)
player_x = SCREEN_WIDTH // 2 - PLAYER_SIZE // 2
player_y = SCREEN_HEIGHT // 2 - PLAYER_SIZE // 2

# Thread-safe queue to store commands received from TCP socket
command_queue = queue.Queue()


def tcp_server(host="localhost", port=9999):
    """TCP server that listens for movement commands and puts them into a queue."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"Server listening on {host}:{port}")

    client_socket, addr = server_socket.accept()
    print(f"Connection from {addr}")

    with client_socket:
        buffer = ""
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            buffer += data.decode("utf-8")
            # Process any complete command lines
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                command = line.strip().lower()
                if command in ["left", "right", "up", "down"]:
                    command_queue.put(command)
                    print(f"Command received: {command}")
    print("Client disconnected.")
    server_socket.close()


# Start the TCP server in a separate thread
server_thread = threading.Thread(target=tcp_server, daemon=True)
server_thread.start()

# Main game loop
running = True
clock = pygame.time.Clock()

while running:
    clock.tick(30)  # Limit frame rate to 30 FPS

    # Process Pygame events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Process commands from the TCP socket
    while not command_queue.empty():
        cmd = command_queue.get()
        if cmd == "left":
            player_x -= MOVE_DISTANCE
        elif cmd == "right":
            player_x += MOVE_DISTANCE
        elif cmd == "up":
            player_y -= MOVE_DISTANCE
        elif cmd == "down":
            player_y += MOVE_DISTANCE

    # Make sure the player stays within bounds
    player_x = max(0, min(player_x, SCREEN_WIDTH - PLAYER_SIZE))
    player_y = max(0, min(player_y, SCREEN_HEIGHT - PLAYER_SIZE))

    # Update game display
    screen.fill((0, 0, 0))  # Fill the screen with black
    pygame.draw.rect(
        screen, (0, 255, 0), (player_x, player_y, PLAYER_SIZE, PLAYER_SIZE)
    )
    pygame.display.flip()

pygame.quit()
