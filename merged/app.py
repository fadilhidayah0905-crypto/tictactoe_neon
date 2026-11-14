from flask import (
    Flask, render_template, request,
    jsonify, session, redirect,
    url_for, send_from_directory
)
import random
import string
import time
import os

app = Flask(__name__)
app.secret_key = "tictactoe-theme-secret-key"

# =========================
# TEMA (MINECRAFT / NEON)
# =========================
THEMES = ["minecraft", "neon"]
DEFAULT_THEME = "neon"

THEMES_DIR = os.path.join(
    app.root_path, "static", "themes"
)

def get_theme():
    theme = session.get("theme", DEFAULT_THEME)

    if theme not in THEMES:
        theme = DEFAULT_THEME

    return theme

# Sisipkan variabel "theme" otomatis ke semua template
@app.context_processor
def inject_theme():
    return {"theme": get_theme()}

@app.after_request
def add_no_cache_headers(response):

    is_themed_asset = (
        request.path == "/static/style.css" or
        request.path == "/static/bg.jpg" or
        request.path.startswith("/static/sounds/")
    )

    if (request.path != "/" and
            not request.path.startswith("/static")) or \
            is_themed_asset:

        response.headers["Cache-Control"] = \
            "no-store, no-cache, must-revalidate"

        response.headers["Pragma"] = "no-cache"

    return response

# =========================
# PILIH / GANTI TEMA
# =========================
@app.route("/set_theme/<theme_name>")
def set_theme(theme_name):

    if theme_name in THEMES:
        session["theme"] = theme_name

    next_url = request.args.get("next") or url_for("menu")

    return redirect(next_url)

# =========================
# SERVE ASSET SESUAI TEMA YANG DIPILIH
# (style.css, bg.jpg, sounds/*.mp3)
# =========================
@app.route("/static/style.css")
def theme_style():
    return send_from_directory(
        os.path.join(THEMES_DIR, get_theme()),
        "style.css"
    )

@app.route("/static/bg.jpg")
def theme_bg():
    return send_from_directory(
        os.path.join(THEMES_DIR, get_theme()),
        "bg.jpg"
    )

@app.route("/static/sounds/<path:filename>")
def theme_sounds(filename):
    return send_from_directory(
        os.path.join(THEMES_DIR, get_theme(), "sounds"),
        filename
    )

# =========================
# LEVEL
# =========================
levels = {
    1: 3,
    2: 4,
    3: 5,
    4: 6,
    5: 7,
    6: 8,
    7: 9,
    8: 10,
    9: 11,
    10: 12
}

# =========================
# SYARAT MENANG SESUAI UKURAN PAPAN
# 3x3        -> 3 beruntun
# 4x4        -> 4 beruntun
# 5x5 - 7x7  -> 4 beruntun
# 8x8 - 12x12-> 5 beruntun
# =========================
def get_win_length(size):

    if size == 3:
        return 3

    if size == 4:
        return 4

    if size <= 7:
        return 4

    return 5

# =========================
# TIMER PER GILIRAN (OPSIONAL)
# =========================
# Bisa diatur antara 30-50 detik sesuai aturan.
TURN_SECONDS = 40

# =========================
# PLAYER (DEFAULT / FALLBACK)
# =========================
playerX = "🐱"
playerO = "🐶"

# =========================
# DAFTAR EMOJI KARAKTER YANG BISA DIPILIH
# =========================
EMOJI_CHOICES = [
    "🐱", "🐶", "🐰", "🦊",
    "🐼", "🦁", "🐯", "🐵",
    "🐧", "🐨"
]

def valid_symbol(symbol):

    return symbol in EMOJI_CHOICES

def pick_symbol(preferred, exclude=None):

    # PAKAI PILIHAN JIKA VALID DAN TIDAK BENTROK
    if preferred and valid_symbol(preferred) and preferred != exclude:

        return preferred

    # KALAU TIDAK VALID / BENTROK, PILIH ACAK YANG BEDA
    options = [
        e for e in EMOJI_CHOICES if e != exclude
    ]

    if not options:
        options = EMOJI_CHOICES

    return random.choice(options)

# =========================
# ROOM STORAGE
# =========================
rooms = {}

# =========================
# GENERATE PLAYER ID
# =========================
def generate_player_id():

    return ''.join(

        random.choices(

            string.ascii_letters +
            string.digits,

            k=16
        )
    )

# =========================
# GENERATE ROOM CODE
# =========================
def generate_room_code():

    while True:

        code = ''.join(

            random.choices(

                string.ascii_uppercase +
                string.digits,

                k=4
            )
        )

        if code not in rooms:

            return code

# =========================
# CREATE GAME
# =========================
def create_game(level, host_symbol=None, mode="multiplayer", use_timer=False):

    board_size = levels[level]

    board = [

        ["" for _ in range(board_size)]

        for _ in range(board_size)
    ]

    host_symbol = pick_symbol(host_symbol)

    game = {

        # level
        "level": level,

        # board
        "board_size": board_size,
        "board": board,

        # simbol host & guest (bisa dipilih pemain)
        "host_symbol": host_symbol,
        "guest_symbol": None,

        # player turn
        "current_player": host_symbol,
        "starting_player": host_symbol,

        # result
        "winner": "",
        "game_over": False,

        # move count
        "turns": 0,

        # room info
        "players": 1,

        # host guest
        "host_id": None,
        "guest_id": None,

        # mode: multiplayer / solo / progressive
        "mode": mode,

        # mode vs komputer (solo & progressive selalu lawan komputer)
        "vs_computer": False,

        # =========================
        # TIMER PER GILIRAN (OPSIONAL)
        # =========================
        "use_timer": bool(use_timer),
        "turn_seconds": TURN_SECONDS,
        "turn_deadline": None,

        # timestamp
        "created": time.time()
    }

    reset_turn_timer(game)

    return game

# =========================
# RESET WAKTU GILIRAN
# =========================
def reset_turn_timer(game):

    if game.get("use_timer"):

        game["turn_deadline"] = \
            time.time() + game.get(
                "turn_seconds", TURN_SECONDS
            )

    else:

        game["turn_deadline"] = None

# =========================
# CEK & TANGANI WAKTU GILIRAN HABIS
# KALAU WAKTU HABIS, GILIRAN OTOMATIS
# DIISI DENGAN LANGKAH ACAK
# =========================
def handle_turn_timeout(game):

    if not game.get("use_timer"):
        return None

    if game["game_over"]:
        return None

    deadline = game.get("turn_deadline")

    if deadline is None:
        return None

    if time.time() < deadline:
        return None

    board = game["board"]
    size = game["board_size"]

    empties = [
        (r, c)
        for r in range(size)
        for c in range(size)
        if board[r][c] == ""
    ]

    if not empties:
        return None

    row, col = random.choice(empties)

    symbol = game["current_player"]

    board[row][col] = symbol

    check_winner(game)

    if not game["game_over"]:

        if game["current_player"] == game["host_symbol"]:

            game["current_player"] = game["guest_symbol"]

        else:

            game["current_player"] = game["host_symbol"]

        reset_turn_timer(game)

    # KALAU LAWANNYA KOMPUTER, LANGSUNG JALANKAN GILIRAN KOMPUTER
    computer_move = computer_turn(game)

    return {
        "row": row,
        "column": col,
        "symbol": symbol,
        "computer_move": computer_move
    }

# =========================
# ARAH GARIS YANG DICEK: MENDATAR, MENURUN,
# DIAGONAL, DAN ANTI-DIAGONAL
# =========================
DIRECTIONS = [
    (0, 1),
    (1, 0),
    (1, 1),
    (1, -1)
]

# =========================
# CEK APAKAH ADA N-BERUNTUN DI PAPAN
# UNTUK SEBUAH SIMBOL (SESUAI win_len)
# MENGEMBALIKAN SIMBOL PEMENANG ATAU None
# =========================
def check_line_win(board, size, win_len):

    for r in range(size):

        for c in range(size):

            symbol = board[r][c]

            if symbol == "":
                continue

            for dr, dc in DIRECTIONS:

                count = 1

                rr, cc = r + dr, c + dc

                while 0 <= rr < size and \
                      0 <= cc < size and \
                      board[rr][cc] == symbol:

                    count += 1

                    if count >= win_len:

                        return symbol

                    rr += dr
                    cc += dc

    return None

# =========================
# AI: CARI SATU LANGKAH YANG BISA
# LANGSUNG MEMBUAT N-BERUNTUN (MENANG)
# UNTUK SEBUAH SIMBOL
# =========================
def find_winning_move(board, size, symbol, win_len):

    for r in range(size):

        for c in range(size):

            if board[r][c] != "":
                continue

            board[r][c] = symbol

            won = check_line_win(
                board, size, win_len
            ) == symbol

            board[r][c] = ""

            if won:
                return (r, c)

    return None

# =========================
# AI PICK BEST MOVE
# =========================
def ai_pick_move(game):

    board = game["board"]

    size = game["board_size"]

    win_len = get_win_length(size)

    computer_symbol = game["guest_symbol"]

    human_symbol = game["host_symbol"]

    # 1. AMBIL KEMENANGAN JIKA ADA
    move = find_winning_move(
        board, size, computer_symbol, win_len
    )

    if move:
        return move

    # 2. BLOK LAWAN JIKA MAU MENANG
    move = find_winning_move(
        board, size, human_symbol, win_len
    )

    if move:
        return move

    # 3. PILIH SEL KOSONG TERDEKAT DENGAN TENGAH
    empties = [
        (r, c)
        for r in range(size)
        for c in range(size)
        if board[r][c] == ""
    ]

    if not empties:
        return None

    center = (size - 1) / 2

    empties.sort(
        key=lambda rc:
        (rc[0] - center) ** 2 +
        (rc[1] - center) ** 2
    )

    best_distance = (
        (empties[0][0] - center) ** 2 +
        (empties[0][1] - center) ** 2
    )

    candidates = [
        rc for rc in empties
        if (
            (rc[0] - center) ** 2 +
            (rc[1] - center) ** 2
        ) == best_distance
    ]

    return random.choice(candidates)

# =========================
# JALANKAN GILIRAN KOMPUTER
# =========================
def computer_turn(game):

    if not game.get("vs_computer"):
        return None

    if game["game_over"]:
        return None

    if game["current_player"] != game["guest_symbol"]:
        return None

    move = ai_pick_move(game)

    if move is None:
        return None

    row, col = move

    game["board"][row][col] = game["guest_symbol"]

    check_winner(game)

    if not game["game_over"]:

        game["current_player"] = game["host_symbol"]

        reset_turn_timer(game)

    return {"row": row, "column": col}

# =========================
# CLEANUP ROOM
# =========================
def cleanup_rooms():

    now = time.time()

    delete_list = []

    for room_code, room in rooms.items():

        if room["players"] <= 0:

            delete_list.append(room_code)

            continue

        # room mati setelah 2 jam
        if now - room["created"] > 7200:

            delete_list.append(room_code)

    for room_code in delete_list:

        del rooms[room_code]

# =========================
# MENU
# =========================
@app.route("/")
def menu():

    cleanup_rooms()

    return render_template(
        "menu.html"
    )


# =========================
# LEVEL PAGE
# =========================
@app.route("/level")
def level_page():

    cleanup_rooms()

    return render_template(
        "level.html"
    )


# =========================
# GAME PAGE
# =========================
@app.route("/game")
def game():

    cleanup_rooms()

    return render_template(
        "game.html"
    )


# =========================
# CREATE ROOM
# =========================
@app.route(
    "/create_room",
    methods=["POST"]
)
def create_room():

    cleanup_rooms()

    data = request.json

    level = int(
        data["level"]
    )

    mode = data.get(
        "mode",
        "multiplayer"
    )

    host_symbol = data.get(
        "symbol"
    )

    use_timer = bool(
        data.get("use_timer", False)
    )

    # =========================
    # MODE BERTAHAP SELALU MULAI DARI LEVEL 1 (3x3)
    # =========================
    if mode == "progressive":

        level = 1

    room_code = generate_room_code()

    game = create_game(
        level,
        host_symbol,
        mode=mode,
        use_timer=use_timer
    )

    player_id = generate_player_id()

    game["host_id"] = player_id

    # =========================
    # MODE 1 PLAYER VS KOMPUTER
    # MODE BERTAHAP JUGA SELALU LAWAN KOMPUTER
    # =========================
    if mode in ("solo", "progressive"):

        game["vs_computer"] = True

        game["guest_id"] = "COMPUTER"

        game["guest_symbol"] = pick_symbol(
            None,
            exclude=game["host_symbol"]
        )

        game["players"] = 2

    rooms[room_code] = game

    return jsonify({

        "success": True,

        "room": room_code,

        "level": level,

        "mode": mode,

        "board_size":
        game["board_size"],

        "player_id":
        player_id,

        "symbol":
        game["host_symbol"],

        "use_timer":
        game["use_timer"],

        "turn_seconds":
        game["turn_seconds"],

        "emoji_choices":
        EMOJI_CHOICES
    })


# =========================
# JOIN ROOM
# =========================
@app.route(
    "/join_room",
    methods=["POST"]
)
def join_room():

    cleanup_rooms()

    data = request.json

    room = (
        data["room"]
        .strip()
        .upper()
    )

    if room not in rooms:

        return jsonify({

            "success": False,

            "message":
            "Room tidak ditemukan"
        })

    game = rooms[room]

    if game["players"] >= 2:

        return jsonify({

            "success": False,

            "message":
            "Room penuh"
        })

    player_id = generate_player_id()

    guest_symbol = pick_symbol(
        data.get("symbol"),
        exclude=game["host_symbol"]
    )

    game["guest_id"] = player_id

    game["guest_symbol"] = guest_symbol

    game["players"] = 2

    return jsonify({

        "success": True,

        "room": room,

        "level":
        game["level"],

        "board_size":
        game["board_size"],

        "player_id":
        player_id,

        "symbol":
        guest_symbol,

        "host_symbol":
        game["host_symbol"],

        "emoji_choices":
        EMOJI_CHOICES
    })


# =========================
# GET STATE
# =========================
@app.route("/state")
def get_state():

    cleanup_rooms()

    room = request.args.get(
        "room"
    )

    if room not in rooms:

        return jsonify({

            "success": False,

            "message":
            "Room tidak ditemukan"
        })

    game = rooms[room]

    timeout_result = handle_turn_timeout(game)

    return jsonify({

        "success": True,

        "board":
        game["board"],

        "board_size":
        game["board_size"],

        "current_player":
        game["current_player"],

        "winner":
        game["winner"],

        "game_over":
        game["game_over"],

        "players":
        game["players"],

        "level":
        game["level"],

        "mode":
        game.get("mode", "multiplayer"),

        "vs_computer":
        game.get("vs_computer", False),

        "host_symbol":
        game["host_symbol"],

        "guest_symbol":
        game["guest_symbol"],

        "use_timer":
        game.get("use_timer", False),

        "turn_seconds":
        game.get("turn_seconds", TURN_SECONDS),

        "turn_deadline":
        game.get("turn_deadline"),

        "timeout_move":
        timeout_result
    })

# =========================
# MOVE
# =========================
@app.route(
    "/move",
    methods=["POST"]
)
def move():

    data = request.json

    room = data["room"]

    row = data["row"]

    column = data["column"]

    player_id = data["player_id"]

    if room not in rooms:

        return jsonify({

            "success": False,

            "message":
            "Room tidak ditemukan"
        })

    game = rooms[room]

    if game["game_over"]:

        return jsonify({

            "success": False,

            "message":
            "Game selesai"
        })

    # HOST
    if player_id == game["host_id"]:

        symbol = game["host_symbol"]

    # GUEST
    elif player_id == game["guest_id"]:

        symbol = game["guest_symbol"]

    else:

        return jsonify({

            "success": False,

            "message":
            "Player tidak valid"
        })

    # CEK GILIRAN
    if symbol != game["current_player"]:

        return jsonify({

            "success": False,

            "message":
            "Bukan giliranmu"
        })

    # CEK KOTAK SUDAH TERISI
    if game["board"][row][column] != "":

        return jsonify({

            "success": False,

            "message":
            "Kotak sudah terisi"
        })

    game["board"][row][column] = symbol

    check_winner(game)

    if not game["game_over"]:

        if game["current_player"] == game["host_symbol"]:

            game["current_player"] = game["guest_symbol"]

        else:

            game["current_player"] = game["host_symbol"]

        reset_turn_timer(game)

    # =========================
    # BOARD SESAAT SETELAH GERAKAN MANUSIA
    # (SEBELUM KOMPUTER JALAN)
    # =========================
    player_board = [
        row_data[:] for row_data in game["board"]
    ]

    computer_move = computer_turn(game)

    return jsonify({

        "success": True,

        "board":
        game["board"],

        "player_board":
        player_board,

        "computer_move":
        computer_move,

        "current_player":
        game["current_player"],

        "winner":
        game["winner"],

        "game_over":
        game["game_over"],

        "mode":
        game.get("mode", "multiplayer"),

        "use_timer":
        game.get("use_timer", False),

        "turn_seconds":
        game.get("turn_seconds", TURN_SECONDS),

        "turn_deadline":
        game.get("turn_deadline")
    })


# =========================
# RESTART ROOM
# =========================
@app.route(
    "/restart",
    methods=["POST"]
)
def restart():

    data = request.json

    room = data["room"]

    if room not in rooms:

        return jsonify({

            "success": False
        })

    game = rooms[room]

    size = game["board_size"]

    game["board"] = [

        ["" for _ in range(size)]

        for _ in range(size)
    ]

    game["winner"] = ""

    game["game_over"] = False

    game["turns"] = 0

    game["current_player"] = \
        game["starting_player"]

    reset_turn_timer(game)

    computer_move = computer_turn(game)

    return jsonify({

        "success": True,

        "board":
        game["board"],

        "current_player":
        game["current_player"],

        "winner":
        game["winner"],

        "computer_move":
        computer_move,

        "use_timer":
        game.get("use_timer", False),

        "turn_seconds":
        game.get("turn_seconds", TURN_SECONDS),

        "turn_deadline":
        game.get("turn_deadline")
    })


# =========================
# NEXT LEVEL (LANJUT LEVEL TANPA KE MENU)
# =========================
@app.route(
    "/next_level",
    methods=["POST"]
)
def next_level():

    data = request.json

    room = data["room"]

    player_id = data.get(
        "player_id",
        ""
    )

    direction = data.get(
        "direction",
        "next"
    )

    if room not in rooms:

        return jsonify({

            "success": False,

            "message":
            "Room tidak ditemukan"
        })

    game = rooms[room]

    # HANYA HOST YANG BOLEH GANTI LEVEL
    if player_id != game["host_id"]:

        return jsonify({

            "success": False,

            "message":
            "Hanya host yang bisa mengganti level"
        })

    current_level = game["level"]

    if direction == "prev":

        new_level = current_level - 1

    else:

        new_level = current_level + 1

    if new_level < 1:

        return jsonify({

            "success": False,

            "message":
            "Sudah level paling awal"
        })

    if new_level > max(levels.keys()):

        return jsonify({

            "success": False,

            "message":
            "Sudah level maksimal"
        })

    board_size = levels[new_level]

    game["level"] = new_level

    game["board_size"] = board_size

    game["board"] = [

        ["" for _ in range(board_size)]

        for _ in range(board_size)
    ]

    game["winner"] = ""

    game["game_over"] = False

    game["turns"] = 0

    game["current_player"] = game["host_symbol"]

    game["starting_player"] = game["host_symbol"]

    reset_turn_timer(game)

    computer_move = computer_turn(game)

    return jsonify({

        "success": True,

        "level":
        new_level,

        "board_size":
        board_size,

        "board":
        game["board"],

        "current_player":
        game["current_player"],

        "winner":
        game["winner"],

        "computer_move":
        computer_move,

        "use_timer":
        game.get("use_timer", False),

        "turn_seconds":
        game.get("turn_seconds", TURN_SECONDS),

        "turn_deadline":
        game.get("turn_deadline")
    })


# =========================
# MODE BERTAHAP: LANJUT / ULANG LEVEL OTOMATIS
# - MENANG -> LANJUT KE LEVEL BERIKUTNYA
#   (KALAU SUDAH LEVEL 10 / 12x12, TETAP DI SITU)
# - KALAH  -> ULANG DARI LEVEL 1 (3x3)
# - SERI   -> ULANG LEVEL YANG SAMA
# =========================
@app.route(
    "/progressive_advance",
    methods=["POST"]
)
def progressive_advance():

    data = request.json

    room = data["room"]

    if room not in rooms:

        return jsonify({

            "success": False,

            "message":
            "Room tidak ditemukan"
        })

    game = rooms[room]

    if game.get("mode") != "progressive":

        return jsonify({

            "success": False,

            "message":
            "Bukan mode bertahap"
        })

    if not game["game_over"]:

        return jsonify({

            "success": False,

            "message":
            "Game belum selesai"
        })

    winner = game["winner"]

    max_level = max(levels.keys())

    # MENANG
    if winner == game["host_symbol"]:

        if game["level"] < max_level:

            new_level = game["level"] + 1
            outcome = "next_level"

        else:

            new_level = game["level"]
            outcome = "max_level"

    # SERI -> ULANG LEVEL YANG SAMA
    elif winner == "SERI":

        new_level = game["level"]
        outcome = "replay"

    # KALAH -> ULANG DARI LEVEL 1
    else:

        new_level = 1
        outcome = "restart_from_level_1"

    board_size = levels[new_level]

    game["level"] = new_level

    game["board_size"] = board_size

    game["board"] = [

        ["" for _ in range(board_size)]

        for _ in range(board_size)
    ]

    game["winner"] = ""

    game["game_over"] = False

    game["turns"] = 0

    game["current_player"] = game["host_symbol"]

    game["starting_player"] = game["host_symbol"]

    reset_turn_timer(game)

    computer_move = computer_turn(game)

    return jsonify({

        "success": True,

        "outcome": outcome,

        "level":
        new_level,

        "board_size":
        board_size,

        "board":
        game["board"],

        "current_player":
        game["current_player"],

        "winner":
        game["winner"],

        "computer_move":
        computer_move,

        "use_timer":
        game.get("use_timer", False),

        "turn_seconds":
        game.get("turn_seconds", TURN_SECONDS),

        "turn_deadline":
        game.get("turn_deadline")
    })


# =========================
# LEAVE ROOM
# =========================
@app.route(
    "/leave_room",
    methods=["POST"]
)
def leave_room():

    try:

        data = request.get_json()

        room = data["room"]

        player_id = data.get(
            "player_id",
            ""
        )

        if room not in rooms:

            return jsonify({
                "success": True
            })

        game = rooms[room]

        # HOST KELUAR
        if player_id == game["host_id"]:

            del rooms[room]

            return jsonify({
                "success": True
            })

        # GUEST KELUAR
        if player_id == game["guest_id"]:

            game["guest_id"] = None

            game["players"] = 1

            return jsonify({
                "success": True
            })

        return jsonify({
            "success": True
        })

    except:

        return jsonify({
            "success": True
        })


# =========================
# TENTUKAN SIAPA YANG MULAI RONDE BERIKUTNYA
# - JIKA ADA PEMENANG -> PEMENANG MULAI DULUAN LAGI
# - JIKA SERI -> GILIRAN MULAI BERGANTIAN SEPERTI BIASA
# =========================
def switch_starter(game):

    winner = game["winner"]

    # ADA PEMENANG -> PEMENANG MULAI RONDE BERIKUTNYA
    if winner and winner != "SERI":

        game["starting_player"] = winner

        return

    # SERI -> BERGANTIAN
    if game["starting_player"] == game["host_symbol"]:

        game["starting_player"] = game["guest_symbol"]

    else:

        game["starting_player"] = game["host_symbol"]


# =========================
# CHECK WINNER
# =========================
def check_winner(game):

    game["turns"] += 1

    board = game["board"]

    size = game["board_size"]

    # SYARAT PANJANG BERUNTUN SESUAI UKURAN PAPAN
    win_len = get_win_length(size)

    winner_symbol = check_line_win(
        board, size, win_len
    )

    if winner_symbol:

        game["winner"] = winner_symbol

        game["game_over"] = True

        switch_starter(game)

        return

    # DRAW (SERI) -> SEMUA KOTAK PENUH TANPA PEMENANG
    if game["turns"] >= size * size:

        game["winner"] = "SERI"

        game["game_over"] = True

        switch_starter(game)


# =========================
# MAIN
# =========================
if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=5000,

        debug=True
    )