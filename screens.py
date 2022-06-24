from kivy.properties import NumericProperty, ObjectProperty, ReferenceListProperty, BooleanProperty, StringProperty, ColorProperty, NumericProperty, ListProperty
from kivy.vector import Vector
from kivy.core.window import Window
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock

from random import randint, choice
from functools import partial
from _thread import *

from settings import Settings
from widgets import ErrorPopup, AcceptPopup, JoinPopup
from bot import Bot
from server import Server
from client import Client
from helpers import EventManager

class MyScreen():
    def __init__(self):
        self.settings = Settings()

    def add_action(self, name, data):
        self.actions.append((name, data))


class MenuScreen(Screen, MyScreen):
    pass


class ConnectScreen(Screen, MyScreen):
    pass


class NameScreen(Screen, MyScreen):
    next_screen = StringProperty("")
    username = ObjectProperty(None)
    username_border_col = ColorProperty("white")

    def validate(self):
        if len(self.username.text.strip()) > 0: # if provided and doesn't consists of whitespaces
            # remove whitespaces and keep only 10 first characters
            username = self.username.text.strip()
            username = username[:10] + "..." if len(username) > 10 else username

            self.manager.transition.duration = Settings.transition_duration
            self.manager.transition.direction = "left"
            self.manager.current = self.next_screen
            self.manager.current_screen.initialize(username)
            self.reset()
        else:
            self.username_border_col = "red"

    def reset(self): 
        self.username_border_col = "white"
        self.username.text = ""


class ServerScreen(Screen, MyScreen):
    dots = NumericProperty(0) # to change number of dots on the end of screen's title 
    time = NumericProperty(Settings.waiting_timeout)
    clients_list = ListProperty([])

    def __init__(self, **kwargs):
        super(ServerScreen, self).__init__(**kwargs)
        self.reset(True)

    def reset(self, initial=False):
        if not initial:
            self.server.reset()
            if self.accept is not None:
                self.accept.back_up()
            if self.ticking is not None:
                self.ticking.cancel()
        else:
            self.server = Server()
            self.accept = None
            self.ticking = None
        self.dots = 0
        self.clients_list = []
        self.actions = [] # all must be O(1)
        self.time = Settings.waiting_timeout # shut down the server after specified time if is doesn't start a game

    def initialize(self, server_name):
        self.reset()
        self.ticking = Clock.schedule_interval(self.tick, 1)# administrates all actions
        self.server.initialize(server_name, self)
        if not self.server.working:
            self.manager.current = "connect"
            ErrorPopup("Server error", "Unable to create server, try again later.").open()
            self.reset()

    def remove_client(self, address): # remove client from list if it is present
        for idx, entry in enumerate(self.clients_list):
            if entry["address"] == address:
                self.clients_list.pop(idx)
                return

    def add_client(self, client_name, client_address):
        self.clients_list.append({
            "text": client_name, "address": client_address, "root": self
        })

    def tick(self, *dt):
        self.time -= 1
        self.dots = (self.dots + 1) % 4

        if self.time <= 0:
            self.manager.current = "connect"
            ErrorPopup("Server closed", "Your server was closed bacause you exceeded connection time.").open()
            self.reset()

        while len(self.actions):
            name, data = self.actions.pop(0)
            match name:
                case "REMOVE":
                    self.remove_client(data)
                case "ADD":
                    self.add_client(*data)
                case "ERROR":
                    if self.accept is not None: # if accept popup is active or might be active
                        self.accept.back_up()
                    ErrorPopup(*data).open()
                case "START":
                    self.ticking.cancel() # we can't reset here, server will be lost
                    self.accept.back_up()
                    self.manager.transition.duration = Settings.transition_duration
                    self.manager.transition.direction = "up"
                    self.manager.current = "game"
                    self.manager.current_screen.set_up("server", data)

    def handler(self, client_name, client_address):
        self.accept = AcceptPopup(client_name, client_address, self)
        self.accept.open()


class ClientScreen(Screen, MyScreen):
    servers_list = ListProperty([])
    dots = NumericProperty(0) # to change number of dots on the end of screen's title 

    def __init__(self, **kwargs):
        super(ClientScreen, self).__init__(**kwargs)
        self.reset(True)

    def reset(self, initial=False):
        if not initial and self.ticking is not None:
            self.ticking.cancel()
        else:
            self.ticking = None
        if not initial:
            self.client.reset()
            if self.join is not None:
                self.join.dismiss()
        else:
            self.client = Client()
            self.join = None
        self.dots = 0
        self.servers_list = []
        self.actions = [] # each action must be O(1)

    def initialize(self, client_name):
        self.reset()
        self.client.initialize(client_name, self)
        self.ticking = Clock.schedule_interval(self.tick, 1)

    def add_server(self, server_name, server_address):
        self.servers_list.append({
            "text": server_name, "address": server_address, "root": self
        })

    def remove_server(self, server_address): # remove server from the list if present
        for idx, entry in enumerate(self.servers_list):
            if entry["address"] == server_address:
                self.servers_list.pop(idx)
                return

    def tick(self, *dt):
        self.dots = (self.dots + 1) % 4

        while len(self.actions):
            name, data = self.actions.pop(0)
            match name:
                case "REMOVE":
                    self.remove_server(data)
                case "ADD":
                    self.add_server(*data)
                case "STOP WAITING": # server we wait for is unavailable
                    self.join.back_up(False)
                    ErrorPopup(*data).open()
                case "START":
                    self.ticking.cancel() # we can't reset here, client will be lost
                    self.join.back_up(False) # back up but don't abandon the server
                    self.manager.transition.duration = Settings.transition_duration
                    self.manager.transition.direction = "up"
                    self.manager.current = "game"
                    self.manager.current_screen.set_up("client", data)

    def handler(self, server_name, server_address):
        self.client.request_game(server_address) # send request to a server
        self.join = JoinPopup(server_name, self) 
        self.join.open()
        

class StatsScreen(Screen, MyScreen):
    pass


class PauseScreen(Screen, MyScreen):
    def abort(self):
        game = self.manager.get_screen("game")

        if game.internet is not None:
            game.internet.abandon()
        else:
            game.add_action("LEAVE", None)

    def exit_(self):
        game = self.manager.get_screen("game")
        
        if game.internet is not None:
            game.internet.abandon()
        Clock.schedule_once(exit, 0.5)


class GameScreen(Screen, MyScreen, EventManager):
    ball = ObjectProperty(None)
    player1 = ObjectProperty(None)
    player2 = ObjectProperty(None)
    players = ReferenceListProperty(player1, player2)
    streak = NumericProperty(0)
    cc = BooleanProperty(False)
    gg = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(GameScreen, self).__init__(**kwargs)
        self.reset(True)

    def reset(self, initial=False):
        Settings.inform(f"Resetting the game ({initial}).")
        if initial:
            self.keyboard = Window.request_keyboard(None, self)
            self.ticking = None
            self.reseting_players = None
            self.counting = None
            self.serving = None
        else:
            for player in self.players: 
                player.score = 0
            for event in [self.ticking, self.counting, self.serving, self.reseting_players]:
                if event is not None:
                    event.cancel()
            self.reset_players()
            self.keyboard.unbind(on_key_down=self.on_key_down, on_key_up=self.on_key_up)

        self.started = False
        self.cc = self.gg = False # marks if countdown or turn is active
        self.cache_streak = self.streak = 0
        self.internet = None # client or server handling connections 
        self.actions = [] # all must be O(1)

    def set_up(self, opt, internet=None):
        Settings.inform(f"Setting up a game: {opt}")
        self.opt = opt
        self.internet = internet

        match opt:
            case "solo":
                self.player1.move = Bot.move
                self.player1.name = "Bot"
                self.player2.name = "You"
            case "offline":
                self.player1.name = "Player 1"
                self.player2.name = "Player 2"
            case "server":
                self.internet.screen = self
                self.player1.name = internet.client_name
                self.player2.name = internet.server_name
            case "client":
                self.internet.screen = self
                self.player1.name = internet.server_name
                self.player2.name = internet.client_name

        self.keyboard.bind(on_key_down=self.on_key_down, on_key_up=self.on_key_up)
        self.ticking = Clock.schedule_interval(self.tick, 1. / Settings.fps) # administrates all game dependencies
        if self.opt in ["server", "offline", "solo"]:
            self.start()

    def tick(self, *dt):
        permission = self.handle_actions() # permission will be False in case of leaving
        if permission:
            self.handle_game_action() 
            self.send_data()
        
    def start_countdown(self, callback, callback_data, duration):
        if not self.cc: # if it wasn't paused during another countdown
            self.cache_streak = self.streak
        self.cc = True
        self.streak = duration
        self.counting = Clock.schedule_interval(partial(self.countdown, callback, callback_data), 1)

    def countdown(self, callback, callback_data, *dt):
        if self.streak == 0: # countdown timeout
            self.counting.cancel()
            self.streak = self.cache_streak
            self.cc = False # mark countdown as finished
            callback(*callback_data)
        else:
            self.streak -= 1

    def start(self):
        self.ball.center = self.center
        self.start_countdown(self.serve, [choice([-1, 1])], 1)

    def pause(self):
        if self.gg: # if during round
            self.gg = False
        elif self.cc: # if during countdown
            self.cc = False
            self.counting.cancel()
        elif self.serving is not None:
            self.serving.cancel()

    def unpause(self): 
        if not self.started:
            self.start()
        else:
            self.start_countdown(self.unpause_helper, [], 3)

    def unpause_helper(self):
        self.streak = self.cache_streak
        self.gg = True # mark turn started
        
    def serve(self, direction, *dt):
        Settings.inform(f"Serving a ball (direction -> {direction})")
        self.started = True
        self.gg = True
        self.ball.center = self.center
        self.ball.velocity = Vector(direction * self.height * Settings.speed, 0).rotate(randint(-60, 60))

    def turn_end(self, winner, direction):
        Settings.inform(f"Turn ended. ({winner.name} has won)")
        self.gg = False # mark turn end
        self.streak = 0 # reset streak
        self.ball.center = self.center # pause now won't take twice the same turn end
        winner.reward()
                            
        self.reseting_players = Clock.schedule_once(self.reset_players, 1) # reset players after 1 s so player could prepare
        self.serving = Clock.schedule_once(partial(self.serve, direction), 1) # start next turn after 1 s so player could prepare

    def reset_players(self, *dt): # set all players in starting positions and set their color to white
        for player in self.players:
            player.reset(self)
