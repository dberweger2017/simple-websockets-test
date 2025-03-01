import socket, threading, time, json

# Game settings
GAME_WIDTH = 640
GAME_HEIGHT = 480
PADDLE_WIDTH = 10
PADDLE_HEIGHT = 80
BALL_RADIUS = 8
WIN_SCORE = 10
PADDLE_SPEED = 5
BALL_SPEED = 5

# Initial positions
paddle1_y = GAME_HEIGHT // 2 - PADDLE_HEIGHT // 2
paddle2_y = GAME_HEIGHT // 2 - PADDLE_HEIGHT // 2
ball_x = GAME_WIDTH // 2
ball_y = GAME_HEIGHT // 2
ball_vx = BALL_SPEED  # start moving right
ball_vy = BALL_SPEED

score1 = 0
score2 = 0

# Player commands (set to 'w' or 's')
player1_cmd = None
player2_cmd = None

# Locks for thread safety
lock1 = threading.Lock()
lock2 = threading.Lock()

players = []  # list of sockets
player_names = ["", ""]

def handle_client(conn, player_num):
    global player1_cmd, player2_cmd
    try:
        # Ask for player's name
        conn.sendall("Enter your name: ".encode())
        name = conn.recv(1024).decode().strip()
        player_names[player_num - 1] = name
        conn.sendall(f"Welcome, {name}! Use W and S to move.\n".encode())
        print(f"Player {player_num} connected: {name}")
        while True:
            data = conn.recv(1024).decode().strip()
            if not data:
                break
            cmd = data[0].lower()  # only use first character
            if player_num == 1:
                with lock1:
                    player1_cmd = cmd
            else:
                with lock2:
                    player2_cmd = cmd
    except Exception as e:
        print(f"Player {player_num} error: {e}")
    finally:
        conn.close()

def broadcast(state_str):
    for p in players:
        try:
            p.sendall(state_str.encode())
        except:
            pass

def game_loop():
    global paddle1_y, paddle2_y, ball_x, ball_y, ball_vx, ball_vy, score1, score2
    global player1_cmd, player2_cmd

    last_speedup_time = time.time()  # track when to speed up the ball
    
    while score1 < WIN_SCORE and score2 < WIN_SCORE:
        # Process inputs
        with lock1:
            cmd1 = player1_cmd
            player1_cmd = None
        with lock2:
            cmd2 = player2_cmd
            player2_cmd = None
        
        if cmd1 == 'w':
            paddle1_y = max(0, paddle1_y - PADDLE_SPEED)
        elif cmd1 == 's':
            paddle1_y = min(GAME_HEIGHT - PADDLE_HEIGHT, paddle1_y + PADDLE_SPEED)
        
        if cmd2 == 'w':
            paddle2_y = max(0, paddle2_y - PADDLE_SPEED)
        elif cmd2 == 's':
            paddle2_y = min(GAME_HEIGHT - PADDLE_HEIGHT, paddle2_y + PADDLE_SPEED)
        
        # Speed up the ball by 1% every 2 seconds (keeping its direction)
        current_time = time.time()
        if current_time - last_speedup_time >= 2:
            ball_vx *= 1.01
            ball_vy *= 1.01
            last_speedup_time = current_time
        
        # Move ball
        ball_x += ball_vx
        ball_y += ball_vy

        # Bounce off top and bottom
        if ball_y - BALL_RADIUS <= 0 or ball_y + BALL_RADIUS >= GAME_HEIGHT:
            ball_vy = -ball_vy

        # Check collision with left paddle
        if ball_vx < 0 and ball_x - BALL_RADIUS <= PADDLE_WIDTH:
            if paddle1_y <= ball_y <= paddle1_y + PADDLE_HEIGHT:
                ball_vx = -ball_vx
            else:
                score2 += 1
                ball_x, ball_y = GAME_WIDTH // 2, GAME_HEIGHT // 2
                ball_vx = BALL_SPEED  # reset speed after score
                ball_vy = BALL_SPEED
                last_speedup_time = time.time()
                time.sleep(1)

        # Check collision with right paddle
        if ball_vx > 0 and ball_x + BALL_RADIUS >= GAME_WIDTH - PADDLE_WIDTH:
            if paddle2_y <= ball_y <= paddle2_y + PADDLE_HEIGHT:
                ball_vx = -ball_vx
            else:
                score1 += 1
                ball_x, ball_y = GAME_WIDTH // 2, GAME_HEIGHT // 2
                ball_vx = -BALL_SPEED  # reset speed after score
                ball_vy = BALL_SPEED
                last_speedup_time = time.time()
                time.sleep(1)
        
        # Build game state dictionary
        state = {
            "paddle1_y": paddle1_y,
            "paddle2_y": paddle2_y,
            "ball_x": ball_x,
            "ball_y": ball_y,
            "score1": score1,
            "score2": score2,
            "game_over": False,
            "player_names": player_names,
        }
        state_str = json.dumps(state) + "\n"
        broadcast(state_str)
        time.sleep(0.03)  # about 30 fps
    
    # Game over state
    winner = player_names[0] if score1 >= WIN_SCORE else player_names[1]
    state = {
        "paddle1_y": paddle1_y,
        "paddle2_y": paddle2_y,
        "ball_x": ball_x,
        "ball_y": ball_y,
        "score1": score1,
        "score2": score2,
        "game_over": True,
        "winner": winner,
        "player_names": player_names,
    }
    state_str = json.dumps(state) + "\n"
    broadcast(state_str)
    print(f"Game over! Winner: {winner}")

def main():
    global players
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', 9999))
    server.listen(2)
    print("Server listening on port 9999. Waiting for 2 players...")
    
    while len(players) < 2:
        conn, addr = server.accept()
        players.append(conn)
        player_num = len(players)
        threading.Thread(target=handle_client, args=(conn, player_num), daemon=True).start()
        print(f"Player {player_num} connected from {addr}")
    
    game_loop()
    server.close()

if __name__ == "__main__":
    main()