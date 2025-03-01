import socket, threading, json, pygame, sys

# Network settings
HOST = "2.tcp.ngrok.io"
PORT = 12577

# Game settings (must match the server)
GAME_WIDTH = 640
GAME_HEIGHT = 480
PADDLE_WIDTH = 10
PADDLE_HEIGHT = 80
BALL_RADIUS = 8

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Global game state and lock
game_state = None
state_lock = threading.Lock()

def receive_game_state(sock):
    global game_state
    file = sock.makefile()  # allows line-by-line reading
    while True:
        line = file.readline()
        if not line:
            break
        try:
            state = json.loads(line)
            with state_lock:
                game_state = state
        except Exception as e:
            print("Error parsing game state:", e)

def main():
    global game_state
    pygame.init()
    screen = pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT))
    pygame.display.set_caption("Multiplayer Pong")
    clock = pygame.time.Clock()
    
    # Connect to server
    host = HOST
    port = PORT
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    
    # Handle name prompt from server
    prompt = sock.recv(1024).decode()
    name = input(prompt)
    sock.sendall(name.encode())
    
    # Start thread to listen for game state updates
    threading.Thread(target=receive_game_state, args=(sock,), daemon=True).start()
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Send paddle movement commands on key press
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            sock.sendall("w".encode())
        elif keys[pygame.K_s]:
            sock.sendall("s".encode())
        
        screen.fill(BLACK)
        
        with state_lock:
            state = game_state.copy() if game_state else None
        
        if state:
            # Draw left paddle (player 1)
            paddle1_rect = pygame.Rect(0, state["paddle1_y"], PADDLE_WIDTH, PADDLE_HEIGHT)
            # Draw right paddle (player 2)
            paddle2_rect = pygame.Rect(GAME_WIDTH - PADDLE_WIDTH, state["paddle2_y"], PADDLE_WIDTH, PADDLE_HEIGHT)
            pygame.draw.rect(screen, WHITE, paddle1_rect)
            pygame.draw.rect(screen, WHITE, paddle2_rect)
            
            # Draw the ball
            pygame.draw.circle(screen, WHITE, (int(state["ball_x"]), int(state["ball_y"])), BALL_RADIUS)
            
            # Display scores and names
            font = pygame.font.Font(None, 36)
            score_text = font.render(
                f"{state['player_names'][0]}: {state['score1']}   {state['player_names'][1]}: {state['score2']}",
                True, WHITE)
            screen.blit(score_text, (GAME_WIDTH//2 - score_text.get_width()//2, 10))
            
            if state.get("game_over"):
                over_text = font.render(f"Game Over! Winner: {state['winner']}", True, WHITE)
                screen.blit(over_text, (GAME_WIDTH//2 - over_text.get_width()//2, GAME_HEIGHT//2 - over_text.get_height()//2))
        
        pygame.display.flip()
        clock.tick(30)
    
    sock.close()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()