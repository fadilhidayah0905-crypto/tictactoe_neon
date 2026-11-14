const boardElement =
document.getElementById("board");

const statusText =
document.getElementById("status");

const playerCountText =
document.getElementById("playerCount");

const levelTitleText =
document.getElementById("levelTitle");

const timerText =
document.getElementById("timerText");

// =========================
// ROOM DATA
// =========================

const roomCode =
localStorage.getItem("roomCode");

const playerId =
localStorage.getItem("playerId");

const playerSymbol =
localStorage.getItem("playerSymbol");

const gameMode =
localStorage.getItem("gameMode") || "multiplayer";

const isHost =
localStorage.getItem("isHost") === "true";

// =========================
// BOARD
// =========================

let boardSize = 0;

let boardReady = false;

let gameOver = false;

// =========================
// TIMER GILIRAN
// =========================

let useTimer = false;

let turnDeadline = null;

let timerIntervalId = null;

// =========================
// PENANDA SUPAYA progressiveAdvance()
// TIDAK DIPANGGIL BERULANG-ULANG
// =========================

let progressiveHandled = false;

// =========================
// SOUND
// =========================

const clickSound =
new Audio("/static/sounds/click.mp3");

const winSound =
new Audio("/static/sounds/win.mp3");

const drawSound =
new Audio("/static/sounds/draw.mp3");

// =========================
// PLAY CLICK
// =========================

function playClick(){

    try{

        clickSound.currentTime = 0;

        clickSound.play();

    }
    catch(err){}
}

// =========================
// CREATE BOARD
// =========================

function createBoard(size){

    boardElement.innerHTML = "";

    boardElement.className =
    "board";

    if(size >= 8 && size < 11){

        boardElement.classList.add(
            "large"
        );
    }

    if(size >= 11){

        boardElement.classList.add(
            "xlarge"
        );
    }

    boardElement.style.gridTemplateColumns =
    `repeat(${size}, auto)`;

    for(let row=0; row<size; row++){

        for(let col=0; col<size; col++){

            const cell =
            document.createElement("div");

            cell.classList.add(
                "cell"
            );

            cell.dataset.row =
            row;

            cell.dataset.col =
            col;

            cell.addEventListener(
                "click",
                () => {

                    sendMove(
                        row,
                        col
                    );
                }
            );

            boardElement.appendChild(
                cell
            );
        }
    }
}

// =========================
// UPDATE BOARD
// =========================

function updateBoard(board){

    const cells =
    document.querySelectorAll(
        ".cell"
    );

    let index = 0;

    for(let row=0;
        row<board.length;
        row++){

        for(let col=0;
            col<board[row].length;
            col++){

            cells[index].innerHTML =
            board[row][col];

            index++;
        }
    }
}

// =========================
// TIMER: TAMPILKAN SISA WAKTU GILIRAN
// =========================

function applyTimerData(data){

    useTimer =
    !!data.use_timer;

    turnDeadline =
    data.turn_deadline || null;

    if(!timerText) return;

    if(!useTimer || data.game_over){

        timerText.innerHTML = "";

        return;
    }

    tickTimerDisplay();
}

function tickTimerDisplay(){

    if(!timerText) return;

    if(!useTimer || !turnDeadline || gameOver){

        timerText.innerHTML = "";

        return;
    }

    const remaining =
    Math.max(
        0,
        Math.ceil(turnDeadline - (Date.now()/1000))
    );

    timerText.innerHTML =
    "⏱️ Sisa waktu giliran: " +
    remaining +
    " detik";
}

if(!timerIntervalId){

    timerIntervalId = setInterval(
        tickTimerDisplay,
        1000
    );
}

// =========================
// SEND MOVE
// =========================

async function sendMove(
    row,
    column
){

    if(gameOver)
        return;

    try{

        const response =
        await fetch(
            "/move",
            {
                method:"POST",

                cache:"no-store",

                headers:{
                    "Content-Type":
                    "application/json"
                },

                body:JSON.stringify({

                    room:roomCode,

                    player_id:
                    playerId,

                    row:row,

                    column:column

                })
            }
        );

        const data =
        await response.json();

        if(!data.success){

            return;
        }

        applyTimerData(data);

        // =========================
        // MODE SOLO / BERTAHAP: TAMPILKAN GERAKAN
        // KOMPUTER DENGAN JEDA SEBENTAR
        // =========================
        if(
            (gameMode === "solo" || gameMode === "progressive") &&
            data.computer_move &&
            data.player_board
        ){

            updateBoard(
                data.player_board
            );

            statusText.innerHTML =
            "🤖 Giliran Komputer...";

            setTimeout(() => {

                updateBoard(
                    data.board
                );

                updateGameStatus(
                    data
                );

            }, 500);

            return;
        }

        updateBoard(
            data.board
        );

        updateGameStatus(
            data
        );
    }
    catch(err){

        console.log(err);
    }
}

// =========================
// UPDATE STATUS
// =========================

function updateGameStatus(data){

    gameOver =
    data.game_over;

    if(timerText && data.game_over){

        timerText.innerHTML = "";
    }

    if(data.game_over){

        if(data.winner === "SERI"){

            try{

                drawSound.play();

            }
            catch(err){}

            statusText.innerHTML =
            gameMode === "progressive"
            ? "🤝 SERI — main ulang level ini..."
            : "🤝 PERMAINAN SERI — klik Restart untuk main lagi";
        }

        else{

            try{

                winSound.play();

            }
            catch(err){}

            if(gameMode === "progressive"){

                statusText.innerHTML =

                data.winner === playerSymbol
                ? "🎉 KAMU MENANG! Lanjut ke level berikutnya..."
                : "😵 KAMU KALAH! Mengulang dari Level 1...";
            }
            else{

                statusText.innerHTML =

                "🎉 PEMENANG : " +

                data.winner;
            }
        }

        // =========================
        // MODE BERTAHAP: OTOMATIS LANJUT / ULANG
        // =========================
        if(gameMode === "progressive" && !progressiveHandled){

            progressiveHandled = true;

            setTimeout(
                progressiveAdvance,
                1800
            );
        }

        return;
    }

    if(gameMode === "solo" || gameMode === "progressive"){

        if(data.current_player === playerSymbol){

            statusText.innerHTML =
            "🎮 Giliran Kamu";
        }
        else{

            statusText.innerHTML =
            "🤖 Giliran Komputer...";
        }

        return;
    }

    statusText.innerHTML =

    "Giliran : " +

    data.current_player;
}

// =========================
// MODE BERTAHAP: LANJUT / ULANG LEVEL OTOMATIS
// =========================

async function progressiveAdvance(){

    try{

        const response =
        await fetch(
            "/progressive_advance",
            {
                method:"POST",

                headers:{
                    "Content-Type":
                    "application/json"
                },

                body:JSON.stringify({

                    room:roomCode

                })
            }
        );

        const data =
        await response.json();

        progressiveHandled = false;

        if(!data.success){
            return;
        }

        gameOver = false;

        if(boardSize !== data.board_size){

            boardSize =
            data.board_size;

            createBoard(boardSize);
        }

        updateBoard(data.board);

        if(levelTitleText){

            levelTitleText.innerHTML =
            "Level " + data.level;

            localStorage.setItem(
                "selectedLevel",
                data.level
            );
        }

        applyTimerData(data);

        updateGameStatus(data);
    }
    catch(err){

        console.log(err);

        progressiveHandled = false;
    }
}

// =========================
// GET STATE
// =========================

async function getState(){

    try{

        const response =
        await fetch(

            "/state?room=" +

            roomCode,

            { cache: "no-store" }
        );

        const data =
        await response.json();

        if(!data.success){

            alert(
                "Room telah ditutup"
            );

            localStorage.removeItem(
                "roomCode"
            );

            window.location.href =
            "/";

            return;
        }

        if(gameMode === "solo" || gameMode === "progressive"){

            const myEmoji =
            data.host_symbol || playerSymbol;

            const cpuEmoji =
            data.guest_symbol || "🤖";

            playerCountText.innerHTML =

            myEmoji +
            " Kamu &nbsp;VS&nbsp; Komputer " +
            cpuEmoji +

            (gameMode === "progressive"
                ? " &nbsp;·&nbsp; 📈 Mode Bertahap"
                : "");
        }
        else{

            playerCountText.innerHTML =

            "Player : " +

            data.players +

            " / 2";

            // Menunggu pemain

            if(data.players < 2){

                statusText.innerHTML =

                "Menunggu pemain kedua...";

                return;
            }
        }

        if(levelTitleText && data.level){

            levelTitleText.innerHTML =
            "Level " + data.level;

            localStorage.setItem(
                "selectedLevel",
                data.level
            );
        }

        if(!boardReady ||
            boardSize !==
            data.board_size
        ){

            boardSize =
            data.board_size;

            boardReady = true;

            createBoard(
                boardSize
            );
        }

        updateBoard(
            data.board
        );

        applyTimerData(data);

        updateGameStatus(
            data
        );
    }
    catch(err){

        console.log(err);
    }
}

// =========================
// RESTART
// =========================

async function restartGame(){

    playClick();

    try{

        const response =
        await fetch(
            "/restart",
            {
                method:"POST",

                headers:{
                    "Content-Type":
                    "application/json"
                },

                body:JSON.stringify({

                    room:roomCode

                })
            }
        );

        const data =
        await response.json();

        gameOver = false;

        progressiveHandled = false;

        updateBoard(
            data.board
        );

        applyTimerData(data);

        updateGameStatus(
            data
        );
    }
    catch(err){

        console.log(err);
    }
}

// =========================
// LEVEL BERIKUTNYA
// =========================

async function nextLevel(){

    playClick();

    if(gameMode !== "solo" && !isHost){

        alert(
            "Hanya host yang bisa mengganti level"
        );

        return;
    }

    try{

        const response =
        await fetch(
            "/next_level",
            {
                method:"POST",

                headers:{
                    "Content-Type":
                    "application/json"
                },

                body:JSON.stringify({

                    room:roomCode,

                    player_id:
                    playerId,

                    direction:
                    "next"

                })
            }
        );

        const data =
        await response.json();

        if(!data.success){

            alert(
                data.message ||
                "Gagal mengganti level"
            );

            return;
        }

        gameOver = false;

        progressiveHandled = false;

        boardSize =
        data.board_size;

        createBoard(
            boardSize
        );

        boardReady = true;

        updateBoard(
            data.board
        );

        levelTitleText.innerHTML =
        "Level " + data.level;

        localStorage.setItem(
            "selectedLevel",
            data.level
        );

        applyTimerData(data);

        updateGameStatus(
            data
        );
    }
    catch(err){

        console.log(err);
    }
}

// =========================
// LEAVE ROOM
// =========================

async function leaveRoom(redirectTo){

    playClick();

    try{

        await fetch(
            "/leave_room",
            {
                method:"POST",

                headers:{
                    "Content-Type":
                    "application/json"
                },

                body:JSON.stringify({

                    room:roomCode,

                    player_id:
                    playerId

                })
            }
        );

    }
    catch(err){}

    const preservedMode =
    gameMode;

    localStorage.removeItem(
        "roomCode"
    );

    localStorage.removeItem(
        "playerId"
    );

    localStorage.removeItem(
        "playerSymbol"
    );

    localStorage.removeItem(
        "gameMode"
    );

    localStorage.removeItem(
        "isHost"
    );

    if(redirectTo === "level"){

        if(preservedMode === "solo"){

            window.location.href =
            "/level?mode=solo";
        }
        else if(preservedMode === "progressive"){

            window.location.href =
            "/level?mode=progressive";
        }
        else{

            window.location.href =
            "/level";
        }
    }
    else{

        window.location.href =
        "/";
    }
}

// =========================
// MENU
// =========================

function goToMainMenu(){

    leaveRoom("menu");
}

function goToLevelMenu(){

    leaveRoom("level");
}

// =========================
// AUTO UPDATE
// =========================

setInterval(

    getState,

    1000

);

// =========================
// START
// =========================

window.onload = function(){

    getState();
};