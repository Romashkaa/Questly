from . import _disk, hashing

disk = _disk.Disk()

class DatabaseError(Exception):
    pass

class Settings:
    settings = disk["settings"]

    @classmethod
    def token(cls):
        return str(cls.settings["token"].get_value(""))
    
type GameID = str
type CollectionID = str
type UserID = str
    
class Games:
    games = disk["games"]

    @classmethod
    def create(cls, user_id: UserID | int, data: dict, update_game_id: str | None=None):
        user_id = str(user_id)

        if update_game_id:
            game_id: str = update_game_id
        else:
            game_id: str = hashing.Ids.make_game_id(user_id)

        # hashes/
        #     collections/
        #         CollectionHash = CollectionID
                
        #     games/
        #         GameHash = GameID

        #     users/
        #         UserHash = UserID
        
        game_hash: str = hashing.hash_id(game_id)
        hashing.games[game_hash].set_value(game_id)

        user_hash: str = hashing.hash_id(user_id)
        hashing.users[user_hash].set_value(user_id)

        # games/
        #     GameID/
        #         creator: UserID

        #         data: dict
        #         source: str
        #         scenes: dict

        #         info/
        #             name: str
        #             description: str
        #             ...

        #         stars/
        #             USER_ID: int = 0-5

        #         collections/
        #             CollectionID

        game = cls.games[game_id]
        game.clear()

        game["creator"].set_value(user_id)
        game["info"].mkdir()
        game["stars"].mkdir()
        game["collections"].mkdir()
        game["data"].set_value(data)
        game["source"].set_value(data["meta"]["src"])
        game["scenes"].set_value(data["scenes"])
        game["scenes"].set_value(data["scenes"])

        for k, v in data["info"].items():
            game["info"][k].set_value(v)

        # users/
        #     UserID/
        #         ...
        #         games/
        #             GameID

        disk["users"][user_id]["games"][game_id].set_value(True)
        
        return game_id

    @classmethod
    def get(cls, game_id: str):
        try:
            return Game(game_id)
        except:
            return None

class GameNotFound(DatabaseError):
    pass

class GameFieldTypeFound(DatabaseError):
    pass

class Game:
    name: str
    description: str
    version: int
    creator: str
    script_creator: str
    tags: list
    data: dict
    source: str
    scenes: dict
    title: str
    message: str
    start_button: str

    def __init__(self, game_id: str):
        self.game_id = game_id

        try:
            self._load()
        except GameFieldTypeFound as ex:
            raise GameNotFound()

    def _load(self):
        # games/
        #     GameID/
        #         creator: UserID

        #         data: dict
        #         source: str
        #         scenes: dict

        #         info/
        #             name: str
        #             description: str
        #             ...

        #         stars/
        #             USER_ID: int = 0-5

        #         collections/
        #             CollectionID
        game = disk["games"][self.game_id]
        self._game_dir = game

        self.creator = game["creator"].get_value_no_default() # type: ignore
        if not isinstance(self.creator, str):
            raise GameFieldTypeFound("creator")
        
        self.data = game["data"].get_value_no_default()
        if not isinstance(self.data, dict):
            raise GameFieldTypeFound("data")
        
        self.source = game["source"].get_value_no_default() # type: ignore
        if not isinstance(self.source, str):
            raise GameFieldTypeFound("source")
        
        self.scenes = game["scenes"].get_value_no_default()
        if not isinstance(self.scenes, dict):
            raise GameFieldTypeFound("scenes")
        
        self.name = game["info"]["name"].get_value_no_default() # type: ignore
        if not isinstance(self.name, str):
            raise GameFieldTypeFound("name")        
                
        self.description = game["info"]["description"].get_value_no_default() # type: ignore
        if not isinstance(self.description, str):
            raise GameFieldTypeFound("description")        
                
        self.script_creator = game["info"]["creator"].get_value_no_default() # type: ignore
        if not isinstance(self.script_creator, str):
            raise GameFieldTypeFound("script_creator | info.creator")        
                
        self.tags = game["info"]["tags"].get_value() # type: ignore
        if not isinstance(self.tags, list):
            self.tags = []

        self.version = game["info"]["version"].get_value() # type: ignore
        if not isinstance(self.version, (int, float)):
            self.version = 0
        
        self.title = game["info"]["title"].get_value() # type: ignore
        if not isinstance(self.title, str):
            self.title = f"🎮 Play in \"{self.name}\""

        self.message = game["info"]["message"].get_value() # type: ignore
        if not isinstance(self.message, str):
            self.message = "Press the button below to start!"

        self.start_button = game["info"]["start_button"].get_value() # type: ignore
        if not isinstance(self.start_button, str):
            self.start_button = "🕹️ Play"
        
    @property
    def stars(self):
        stars: dict[str, int] = {}

        for user_id, stars_count in self._game_dir["stars"].name_value():
            if isinstance(stars_count, int):
                stars[user_id] = stars_count

        return stars

    @property
    def collections(self):
        collections: list = []

        for collection_id, _ in self._game_dir["stars"].name_value():
            collections.append(collection_id)

        return collections

class User:
    def __init__(self, user_id: str | int):
        self.user_id = str(user_id)
        self._user_dir = disk["users"][self.user_id]

    # users/
    #     UserID/
    #         info/
    #             ...
    #         settings/
    #             ...
            
    #         games/
    #             GameID

    #         collections/
    #             CollectionID

    #         starred/
    #             GameID = 0-5 (stars)

    #         progress/
    #             GameID = "scene name"

    def create(self, name: str):
        self._user_dir["info"]["name"].set_value(name)

    @property
    def name(self):
        value = self._user_dir["info"]["name"].get_value()

        if isinstance(value, str):
            return value
        
        return "Anon"

    @property
    def about(self):
        value = self._user_dir["info"]["about"].get_value()

        if isinstance(value, str):
            return value
        
        return "..."

    @property
    def games(self) -> list[GameID]:
        value = self._user_dir["games"].names()
        return list(value)
    
    @property
    def game_objects(self):
        for game_id in self._user_dir["games"].names():
            try:
                yield Game(game_id)
            except DatabaseError:
                continue

    @property
    def collections(self) -> list[GameID]:
        value = self._user_dir["collections"].names()
        return list(value)
    
    @property
    def exists(self) -> bool:
        return self._user_dir["info"]["name"].exists()
    

class Users:
    @classmethod
    def ids(cls) -> list[str]:
        return list(disk["users"].names())
    
    @classmethod
    def name_id(cls):
        for user_dir in disk["users"]:
            id: str = user_dir.name
            name = user_dir["info"]["name"].get_value()

            if not isinstance(name, str):
                continue

            yield (name, id)


"""

Games.create(UserID, ast: dict) -> GameID | None
Games.delete(GameID) -> bool
Games.get(GameID) -> Game | None

Game(GameID) -> Game | RaiseError
Game(GameID).name -> str
Game(GameID).set_name(name: str) -> bool

Users.all, get, ...

User(user_id)
. games = ""
. name  = ""
. about = ""
. user_id
. ...
"""