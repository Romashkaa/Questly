import hashlib
import base64

from . import _disk

disk = _disk.Disk()

hashes = disk["hashes"]
collections = hashes["collections"]
games = hashes["games"]
users = hashes["users"]

class Ids:
    @classmethod
    def make_collection_id(cls, user_id: int | str):
        user_id = str(user_id)
        max_index = 0 

        for collection_id_file in disk["users"][user_id]["author_ids"]:
            # USER_ID:INC 2461621604:1
            collection_id: str = collection_id_file.name
            index: int = int(collection_id.split(":")[1])

            if max_index < index:
                max_index = index

        new_index = max_index + 1

        return f"{user_id}:{new_index}"
    
    @classmethod
    def make_game_id(cls, user_id: str):
        max_index = 0 

        for game_id_file in disk["users"][user_id]["games"]:
            # USER_ID:INC 2461621604:1
            game_id: str = game_id_file.name
            index: int = int(game_id.split(":")[1])

            if max_index < index:
                max_index = index

        new_index = max_index + 1

        return f"{user_id}:{new_index}"
    
    @classmethod
    def get_game_id(cls, game_hash: str) -> str | None:
        game = games[game_hash]
        game_id = game.get_value(None)

        if isinstance(game_id, str):
            return game_id
    
    @classmethod
    def get_user_id(cls, user_hash: str):
        user = users[user_hash]
        user_id = user.get_value(None)
        
        if isinstance(user_id, str):
            return user_id
        
    @classmethod
    def get_collection_id(cls, collection_hash: str):
        collection = collections[collection_hash]
        collection_id = collection.get_value(None)
        
        if isinstance(collection_id, str):
            return collection_id
    
    @classmethod
    def get_user_id_from_id(cls, id: str):
        return id.split(":")[0]
        
    
def hash_id(id: str) -> str:
    h = hashlib.sha256(id.encode()).digest()
    return base64.urlsafe_b64encode(h).decode().rstrip("=")