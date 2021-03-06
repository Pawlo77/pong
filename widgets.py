from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty, ColorProperty, StringProperty, BooleanProperty, ObjectProperty
from kivy.vector import Vector
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.clock import Clock

from settings import settings


class HoverableButton(Button):
    hovered = BooleanProperty(False)
    border_point= ObjectProperty(None)

    def __init__(self, **kwargs):
        super(HoverableButton, self).__init__(**kwargs)
        self.register_event_type('on_enter')
        self.register_event_type('on_leave')
        Window.bind(mouse_pos=self.on_mouse_pos)

    def on_mouse_pos(self, *args):
        if not self.get_root_window():
            return # do proceed if I'm not displayed <=> If have no parent
        pos = args[1]
        # Next line to_widget allow to compensate for relative layout
        inside = self.collide_point(*self.to_widget(*pos))
        if self.hovered == inside:
            # We have already done what was needed
            return
        self.border_point = pos
        self.hovered = inside
        if inside:
            self.dispatch('on_enter')
        else:
            self.dispatch('on_leave')

    def on_enter(self): # change color to red if mouse above us
        self.color = "red"

    def on_leave(self): # go back to white
        self.color = "white"


class TickingPopup(Popup):
    exit_text = StringProperty("Back")
    title = StringProperty("Ticking Popup")
    time = NumericProperty(10)

    def alive(self, *dt): # closes automatically after pre-defined amount of time
        self.time -= 1
        if self.time <= 0:
            self.back_up()
            return

    def back_up(self): # close call
        self.countdown.cancel()
        self.dismiss()

    def open(self, **kwargs):
        super(TickingPopup, self).open(**kwargs)
        self.countdown = Clock.schedule_interval(self.alive, 1)


class AcceptPopup(TickingPopup):
    client_name = StringProperty("")
    main_text = StringProperty("")
    minor_text = StringProperty("")
    btn_text = StringProperty("")

    def __init__(self, client_name, client_address, root, **kwargs):
        super(AcceptPopup, self).__init__(**kwargs)
        self.client_name = client_name
        self.client_address = client_address
        self.root = root
        self.title = "Accept a game"
        self.time = settings.accept_timeout
        self.waiting = False
        self.main_text = f"Are sure you want to play against {client_name} ?"
        self.minor_text = f"Decide in {self.time} seconds..."
        self.btn_text = "Play"

    def alive(self, *dt):
        super(AcceptPopup, self).alive(*dt)
        if self.waiting: # we wait for client to mark that he is ready for the game
            self.minor_text = f"Timeout in {self.time} seconds..."
            self.btn_text = "".join(["." for _ in range(self.time % 4)])
        else: # decide if we accept game from a client
            self.minor_text = f"Decide in {self.time} seconds..."

    def accept(self):
        self.root.server.accept_game(self.client_address)
        self.root.time = max(10, self.root.time) # make sure server won't timeout during waiting
        self.time = max(10, self.time) # make sure this popup won'r close during deciding time
        self.waiting = True
        self.main_text = f"Waiting for a connection with {self.client_name}"
        self.minor_text = f"Timeout in {self.time} seconds..."
        self.btn_text = "-"

    def back_up(self, keep_client=False):
        if not keep_client:
            self.client_address = self.root.server.client_address = None
        super().back_up()


class JoinPopup(TickingPopup):
    def __init__(self, server_name, root, **kwargs):
        super(JoinPopup, self).__init__(**kwargs)
        self.root = root
        self.exit_text = "Abandon"
        self.title = f"Joining a game of {server_name}..."
        self.time = settings.joining_timeout

    def back_up(self, abandon=True):
        super().back_up()
        if abandon:
            self.root.client.abandon() # notify server that we don't want to join him anymore


class ErrorPopup(Popup): # popup to inform user that doesn't provide any interaction
    error = StringProperty("")

    def __init__(self, title, error, **kwargs):
        super(ErrorPopup, self).__init__(**kwargs)
        self.title = title
        self.error = error


class Paddle(Widget): 
    score = NumericProperty(0)
    color = ColorProperty("white")
    move_direction = NumericProperty(0)
    name = StringProperty("")
    bot = BooleanProperty(False)
    
    def bounce_ball(self, ball):
        if self.collide_widget(ball):
            velocity_x, velocity_y = ball.velocity

            bounced = settings.speedup * Vector(-1 * velocity_x, velocity_y)
            ball.velocity = bounced.x, bounced.y

            return True
        return False

    def reward(self):
        self.color = "green"
        self.score += 1

    def reset(self, root, *dt):
        self.move_direction = 0 # stop moving
        self.color = "white"
        self.center_y = root.center_y

    @staticmethod
    def move(me, root):
        if me.move_direction == 1: # up
            new = me.top + settings.moveSpeed * root.height
            me.top = min(new, root.top) # don't move out the screen
        elif me.move_direction == -1: # down
            new = me.y - settings.moveSpeed * root.height
            me.y = max(new, root.y) # don't move out the screen


class Ball(Widget):
    velocity_x = NumericProperty(0)     
    velocity_y = NumericProperty(0)    
    velocity = ReferenceListProperty(velocity_x, velocity_y)

    def resize(self, _, newSize): # adjust size if window resized during game
        r = newSize[1] / 20
        self.size = (r, r)    

    def move(self): 
        self.pos = Vector(*self.velocity) + self.pos

