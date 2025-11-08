import telebot.types # type: ignore
import telekit
import typing

from database import database

class RunningMixin(telekit.Handler):
    """
        Define this method:
            >>> "⬅️ Back": self.back() # Called when cancelled or crashes

        You need to provide two values:
            >>> self._creator: database.User
            >>> self._game: database.Game

        Then call `run`:
            >>> self.run()
    """
    _creator: database.User
    _game: database.Game

    # ------------------------------------------
    # Handling Logic
    # ------------------------------------------

    def run(self):
        try:
            self.chain.sender.set_title(self._game.title)
            self.chain.sender.set_message(
                f"<blockquote>{self._game.description}</blockquote>\n\n"
                f"👤 Author: {self._game.script_creator}\n"
                f"🧩 Version: {self._game.version}\n\n" +\
                (f"📌 Tags: {", ".join(self._game.tags)}\n\n" if self._game.tags else "") +\
                self._game.message
            )
            self.chain.set_inline_keyboard(
                {
                    "⬅️ Back":               lambda _: self.back(),
                    self._game.start_button: lambda _: self.prepare_scene("init")()
                }, row_width=2
            )
            self._scenes = self._game.scenes
            self._history = []
            self.chain.edit()
        except Exception as exception:
            self.exception(exception)

    def back(self):
        pass

    def exception(self, exception):
        self.chain.sender.set_title(f"🤷 {type(exception).__name__}")
        self.chain.sender.set_message(str(exception))
        self.chain.set_inline_keyboard(
            {
                "⬅️ Back": lambda _: self.back(),
            }
        )
        self.chain.edit()

    def prepare_scene(self, _scene_name: str):
        def render():
            # magic scenes logic

            scene_name = _scene_name

            match scene_name:
                case "back":
                    if self._history:
                        self._history.pop() # current
                    if self._history:
                        scene_name = self._history.pop()
            
            self._history.append(scene_name)

            # main logic
            scene = self._scenes[scene_name]
            
            chain: telekit.Chain = self.get_child()

            chain.sender.set_parse_mode(scene.get("parse_mode", "Markdown"))
            chain.sender.set_use_italics(scene.get("use_italics", False))

            chain.sender.set_title(scene.get("title", "[ Title ]"))
            chain.sender.set_message(scene.get("message", "[ Message ]"))
            chain.sender.set_photo(scene.get("image", None))

            # keyboard
            keyboard: dict = {}

            for btn_label, btn_scene in scene.get("buttons", {}).items():
                keyboard[btn_label] = self.prepare_scene(btn_scene)

            chain.set_inline_keyboard(keyboard, scene.get("row_width", 1))
            chain.edit()

        return lambda message=None: render()

