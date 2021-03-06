import socket

class Settings():
    fps = 60
    speed = 0.01 # ball speed
    speedup = 1.05 # ball speeds up every time it bounce off paddle
    moveSpeed = 0.015 # paddle move speed
    botMoveSpeed = 0.004 # bot is slower than real player
    startPaddleSize = 0.3
    rounds_to_win = 10
    time_to_start = 5
    time_to_unpause = 3

    transition_duration = 1.5

    PORT = 8000
    MAX_PORT = 8001
    HOST = socket.gethostbyname(socket.gethostname())
    conn_data_limit = 1024
    encoding = "utf-8"
    key = "7fZmv`UXa75@K7e$3+g@"

    connection_timeout = 1
    socket_timeout = 0.1
    accept_timeout = 10 # time tha user has to accept the game in AcceptPopup
    waiting_timeout = 180 # time during after server will be closed if it hadn't started the game
    joining_timeout = 180 # time during after JoinPopup will dissapear

    server_frequency = 1 # waiting time between server loops in ms for rest
    server_time_refresh = 0 # waiting time between server loops in ms for players

    debug = False
    verbose = False

    def handle_error(self, e): 
        if self.debug:
            print(e)

    def inform(self, msg):
        if self.verbose:
            print(msg)

    def allowed(self, address):
        if address:
            return address[0] == self.HOST and self.PORT <= address[1] <= self.MAX_PORT
        return False


settings = Settings()


all = {
    "key": settings.key
}

ALIVE = {"free": None,}
LEAVE = {"left": True,}

WAITING = {"waiting": True,}
REQUEST_GAME = {"ok": True,}
REQUEST_RECIVED = {"understood": True,}
BUSY = {"allowed": False,}
ABANDON = {"bye": True,}

GAME_ACCEPTED = {"allowed": True,}
GAME_START = {"start": True,}