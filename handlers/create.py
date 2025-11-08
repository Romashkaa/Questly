import telebot.types
import telekit
import typing

from database import database
import parsing
import mixins

class CreateHandler(mixins.RunningMixin):

    # ------------------------------------------
    # Initialization
    # ------------------------------------------

    _game_code: str
    _game_id: str
    _game_to_update: database.Game | None

    _creator: database.User
    _game: database.Game

    @classmethod
    def init_handler(cls, bot: telebot.TeleBot) -> None:
        """
        Initializes the message handler for the '/create' command.
        """
        @bot.message_handler(commands=['create'])
        def handler(message: telebot.types.Message) -> None:
            cls(message).maybe_updated()

    # ------------------------------------------
    # Handling Logic
    # ------------------------------------------

    def load_creator(self):
        user = database.User(self.user.chat_id)

        if not user.exists:
            user.create(str(self.user.get_username())[1:])

        self._creator = user

    def maybe_updated(self):
        self.load_creator()

        games = {game.name: game for game in self._creator.game_objects}

        self.chain.sender.set_title("👀 Update or create a game?")
        self.chain.sender.set_message("Which one would you like to update, or create a new one?")

        keyboard: dict[str, database.Game | None] = games.copy() # type: ignore
        keyboard["🆕 Create a new one"] = None

        @self.chain.inline_keyboard(keyboard)
        def _(message, game: database.Game | None):
            self._game_to_update = game
            self.chain.set_inline_keyboard({})
            self.entry_code()

        self.chain.edit()

    def entry_code(self):
        self.chain.sender.set_title("💾 Upload your game file")
        self.chain.sender.set_message("You can send a \".js\" or \".txt\" file. It will be analyzed and checked")

        @self.chain.entry(delete_user_response=True)
        def _(message):
            if message.content_type != 'document':
                return self.exception(TypeError(f"Not a text file, this is {message.content_type}."))
            
            file_name = message.document.file_name
            allowed_extensions = ('.txt', '.js')

            if not file_name.endswith(allowed_extensions):
                self.exception(ValueError("Only .txt or .js files are allowed"))

            try:
                file_info = self.bot.get_file(message.document.file_id)
                downloaded_file = self.bot.download_file(str(file_info.file_path))

                text = downloaded_file.decode('utf-8')

                self.parse(text)
            except Exception as exception:
                return self.exception(exception)
        
        self.chain.edit()

    def parse(self, text):
        self._game_code = text

        try:
            data = parsing.analyze(self._game_code)
        except Exception as exception:
            return self.exception(exception)

        current_game_name = data["info"]["name"]
        game_id: str | None = None

        if isinstance(self._game_to_update, database.Game):
            # update
            for old_game in self._creator.game_objects:
                if (current_game_name == old_game.name) and (old_game.game_id != self._game_to_update.game_id):
                    raise AssertionError(f"Game named '{current_game_name}' already exists")

            game_id = self._game_to_update.game_id
        else:
            # new game, but i need to check it
            for old_game in self._creator.game_objects:
                if current_game_name == old_game.name:
                    game_id = old_game.game_id

        self._game_id = database.Games.create(self.user.chat_id, data, game_id)
        self._game_to_update = None
        self.success(str(current_game_name), bool(game_id))

    
    # def cancel(self, message):
    #     self.chain.sender.set_title("❌ Cancelled")
    #     self.chain.sender.set_message("Game creation has been cancelled")
    #     self.chain.set_inline_keyboard(
    #         {
    #             "🔁 Try again": lambda _: self.entry_code(),
    #         }
    #     )
    #     self.chain.edit()

    def exception(self, exception):
        self.chain.sender.set_title(f"🥴 {type(exception).__name__}")
        self.chain.sender.set_message(str(exception))
        self.chain.set_inline_keyboard(
            {
                "🔁 Try again": lambda _: self.entry_code,
            }
        )
        self.chain.edit()

    def success(self, name: str, updated: bool):
        self.chain.sender.set_title(f"{'✏️' if updated else '✅'} Game {'updated' if updated else 'created'} successfully")
        self.chain.sender.set_message(
            f"Your game <b>\"{name}\"</b> has been {'updated' if updated else 'uploaded'} successfully!"
        )
        self.chain.set_inline_keyboard(
            {
                "🎮 Play": lambda _: self.play()
            }
        )
        self.chain.edit()

    def play(self):
        self._game = database.Game(self._game_id)
        self.run()

    def back(self):
        self.chain.sender.set_title("❌ Cancelled")
        self.chain.sender.set_message("Game testing has been cancelled")
        self.chain.set_inline_keyboard(
            {
                "🔁 Try again": lambda _: self.play(),
            }
        )
        self.chain.edit()
