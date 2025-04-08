import random
import pygame
import socket
import threading
import queue
import sys

pygame.init()

width = 500
height = 500

cols = 25
rows = 20

win = pygame.display.set_mode((width, height))
pygame.display.set_caption("Snake Game")

font = pygame.font.SysFont("comicsans", 30)


# Thread-safe queue to store commands received from TCP socket
command_queue = queue.Queue()


def tcp_server(host="localhost", port=8899):
    last_command = None
    """TCP server that listens for movement commands and puts them into a queue."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((host, port))
        server_socket.listen(1)
        print(f"Server listening on {host}:{port}")

        while True:
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
                            if command != last_command:
                                command_queue.put(command)
                            last_command = command
                            print(f"Command received: {command}")
            print("Client disconnected.")


# Start the TCP server in a separate thread
server_thread = threading.Thread(target=tcp_server, daemon=True)
server_thread.start()


class Cube:
    rows = 20
    w = 500

    def __init__(self, start, dirnx=1, dirny=0, color=(255, 0, 0)):
        self.pos = start
        self.dirnx = dirnx
        self.dirny = dirny  # "L", "R", "U", "D"
        self.color = color

    def move(self, dirnx, dirny):
        self.dirnx = dirnx
        self.dirny = dirny
        self.pos = (self.pos[0] + self.dirnx, self.pos[1] + self.dirny)

    def draw(self, surface, eyes=False):
        dis = self.w // self.rows
        i = self.pos[0]
        j = self.pos[1]

        pygame.draw.rect(
            surface, self.color, (i * dis + 1, j * dis + 1, dis - 2, dis - 2)
        )
        if eyes:
            centre = dis // 2
            radius = 3
            circleMiddle = (i * dis + centre - radius, j * dis + 8)
            circleMiddle2 = (i * dis + dis - radius * 2, j * dis + 8)
            pygame.draw.circle(surface, (0, 0, 0), circleMiddle, radius)
            pygame.draw.circle(surface, (0, 0, 0), circleMiddle2, radius)


class Snake:
    body = []
    turns = {}

    def __init__(self, color, pos):
        # pos is given as coordinates on the grid ex (1,5)
        self.color = color
        self.head = Cube(pos)
        self.body.append(self.head)
        self.dirnx = 1
        self.dirny = 0

    def move(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()

        command = None
        if not command_queue.empty():
            command = command_queue.get()

        if command == "left" and self.dirnx == 0:
            self.dirnx = -1
            self.dirny = 0
            self.turns[self.head.pos[:]] = [self.dirnx, self.dirny]
        elif command == "right" and self.dirnx == 0:
            self.dirnx = 1
            self.dirny = 0
            self.turns[self.head.pos[:]] = [self.dirnx, self.dirny]
        elif command == "up" and self.dirny == 0:
            self.dirny = -1
            self.dirnx = 0
            self.turns[self.head.pos[:]] = [self.dirnx, self.dirny]
        elif command == "down" and self.dirny == 0:
            self.dirny = 1
            self.dirnx = 0
            self.turns[self.head.pos[:]] = [self.dirnx, self.dirny]

        for i, c in enumerate(self.body):
            p = c.pos[:]
            if p in self.turns:
                turn = self.turns[p]
                c.move(turn[0], turn[1])
                if i == len(self.body) - 1:
                    self.turns.pop(p)
            else:
                c.move(c.dirnx, c.dirny)

    def reset(self, pos):
        self.head = Cube(pos)
        self.body = []
        self.body.append(self.head)
        self.turns = {}
        self.dirnx = 1
        self.dirny = 0

    def addCube(self):
        tail = self.body[-1]
        dx, dy = tail.dirnx, tail.dirny

        if dx == 1 and dy == 0:
            self.body.append(Cube((tail.pos[0] - 1, tail.pos[1])))
        elif dx == -1 and dy == 0:
            self.body.append(Cube((tail.pos[0] + 1, tail.pos[1])))
        elif dx == 0 and dy == 1:
            self.body.append(Cube((tail.pos[0], tail.pos[1] - 1)))
        elif dx == 0 and dy == -1:
            self.body.append(Cube((tail.pos[0], tail.pos[1] + 1)))

        self.body[-1].dirnx = dx
        self.body[-1].dirny = dy

    def draw(self, surface):
        for i, c in enumerate(self.body):
            if i == 0:
                c.draw(surface, True)
            else:
                c.draw(surface)


def redrawWindow():
    global win
    win.fill((0, 0, 0))
    drawGrid(width, rows, win)
    s.draw(win)
    snack.draw(win)
    pygame.display.update()


def drawGrid(w, rows, surface):
    sizeBtwn = w // rows

    x = 0
    y = 0
    for l in range(rows):
        x = x + sizeBtwn
        y = y + sizeBtwn

        pygame.draw.line(surface, (255, 255, 255), (x, 0), (x, w))
        pygame.draw.line(surface, (255, 255, 255), (0, y), (w, y))


def randomSnack(rows, item):
    positions = item.body

    while True:
        x = random.randrange(1, rows - 1)
        y = random.randrange(1, rows - 1)
        if len(list(filter(lambda z: z.pos == (x, y), positions))) > 0:
            continue
        else:
            break

    return (x, y)


def draw_text(text, font, color, surface, pos):
    textobj = font.render(text, True, color)
    surface.blit(textobj, pos)


def start_menu():
    """Display a start menu until the player presses a key."""
    running = True
    while running:
        win.fill((0, 0, 0))
        draw_text(
            "Press any key to start",
            font,
            (255, 255, 255),
            win,
            (width // 2 - 150, height // 2),
        )
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                running = False


def game_over_screen(score):
    """Display game over screen with the current score and a restart button."""
    over_font = pygame.font.SysFont("comicsans", 50)
    button_font = pygame.font.SysFont("comicsans", 30)

    # Button dimensions
    button_width, button_height = 150, 50
    button_rect = pygame.Rect(
        width // 2 - button_width // 2, height // 2 + 40, button_width, button_height
    )

    waiting = True
    while waiting:
        win.fill((0, 0, 0))
        draw_text(
            "Game Over!",
            over_font,
            (255, 0, 0),
            win,
            (width // 2 - 120, height // 2 - 100),
        )
        draw_text(
            "Score: " + str(score),
            font,
            (255, 255, 255),
            win,
            (width // 2 - 60, height // 2 - 50),
        )

        # Draw Restart button
        pygame.draw.rect(win, (0, 255, 0), button_rect)
        draw_text(
            "Restart",
            button_font,
            (0, 0, 0),
            win,
            (button_rect.x + 20, button_rect.y + 10),
        )

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if button_rect.collidepoint(event.pos):
                    waiting = False


def end_game():
    while not command_queue.empty():
        command_queue.get_nowait()


def restart_game():
    while not command_queue.empty():
        command_queue.get_nowait()
    s.reset((10, 10))


def main():
    global s, snack, win
    s = Snake((255, 0, 0), (10, 10))
    snack = Cube(randomSnack(rows, s), color=(0, 255, 0))
    flag = True
    clock = pygame.time.Clock()

    while flag:
        pygame.time.delay(10)
        clock.tick(4)
        s.move()
        headPos = s.head.pos
        if headPos[0] >= 20 or headPos[0] < 0 or headPos[1] >= 20 or headPos[1] < 0:
            print("Score:", len(s.body))
            end_game()
            game_over_screen(len(s.body))
            # Reset snake and snack after game over
            restart_game()
            snack = Cube(randomSnack(rows, s), color=(0, 255, 0))
            continue

        if s.body[0].pos == snack.pos:
            s.addCube()
            snack = Cube(randomSnack(rows, s), color=(0, 255, 0))
            score = len(s.body)

        for x in range(len(s.body)):
            if s.body[x].pos in list(map(lambda z: z.pos, s.body[x + 1 :])):
                print("Score:", len(s.body))
                end_game()
                game_over_screen(len(s.body))
                restart_game()
                break

        redrawWindow()


if __name__ == "__main__":
    start_menu()
    main()
    pygame.quit()
