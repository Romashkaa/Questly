import telebot.types # type: ignore
import telekit
import typing

from database import database
import mixins

# ---------------------------
#  Structures
# ---------------------------

class StartHandler(mixins.RunningMixin):

    _creator: database.User
    _game: database.Game

    # ------------------------------------------
    # Initialization
    # ------------------------------------------

    @classmethod
    def init_handler(cls, bot: telebot.TeleBot) -> None:
        """
        Initializes the message handler for the '/start' command.
        """
        @bot.message_handler(commands=['start']) # type: ignore
        def handler(message: telebot.types.Message) -> None: # type: ignore
            cls(message).handle()

    # ------------------------------------------
    # Handling Logic
    # ------------------------------------------

    def handle(self) -> None:
        self.choose_creator()

    def choose_creator(self):
        creators = dict(database.Users.name_id())

        self.chain.sender.set_title("🧑‍💻 Pick an Author")
        self.chain.sender.set_message("Choose an author to explore their amazing creations!")

        @self.chain.inline_keyboard(creators)
        def _(message, creator: str):
            self._creator = database.User(creator)
            self.choose_game()

        self.chain.edit()
    
    def choose_game(self):
        games = {game.name: game for game in self._creator.game_objects}

        self.chain.sender.set_title("💿 Pick a Game")
        self.chain.sender.set_message(f"{self._creator.name} has created the following games.\n\nWhich one will you play?") # self._creator.name

        @self.chain.inline_keyboard(games)
        def _(message, game: database.Game):
            self._game = game
            self.prepare()

        self.chain.edit()

    def prepare(self):
        self.run()

    def back(self):
        self.choose_game()