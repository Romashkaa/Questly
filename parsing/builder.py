from .token import Token
from .nodes import *

class BuilderError(Exception):
    pass

class Builder:
    def __init__(self, ast: Ast, src: str):
        self.src = src
        self.ast = ast
        self.game = {
            "info": {},
            "scenes": {},
            "meta": {
                "src": self.src
            }
        }

    def build(self) -> dict:
        self.ensure_single_info_block()
        self.check_init_scene()
        self.check_unique_scene_names()

        for item in self.ast.body:
            match item:
                case InfoBlock():
                    self.analyze_info(item)
                case SceneBlock():
                    self.analyze_scene(item)

        return self.game

    def ensure_single_info_block(self):
        info_count = 0

        for node in self.ast.body:
            if isinstance(node, InfoBlock):
                info_count += 1

        if info_count == 0:
            raise BuilderError("Missing required '$ info { ... }' block at the beginning of the script")
        elif info_count > 1:
            raise BuilderError("Multiple 'info' blocks found; only one is allowed")
        
    def check_init_scene(self):
        for node in self.ast.body:
            if isinstance(node, SceneBlock) and node.name == "init":
                return

        raise BuilderError("Missing required '@ init { ... }' scene (entry point)")
    
    def check_unique_scene_names(self):
        seen = set()
    
        for node in self.ast.body:
            if isinstance(node, SceneBlock):
                if node.name in seen:
                    raise BuilderError(f"Duplicate scene name '@ {node.name}' found")
                seen.add(node.name)

    def type_name(self, t: type | tuple[type, ...]) -> str:
        if isinstance(t, tuple):
            return " or ".join(x.__name__ for x in t)
        return t.__name__

    def analyze_info(self, info: InfoBlock):
        result = {}

        requirements = (
            ("name", str),
        )

        optional = (
            ("description", str),
            ("version", (float, int)),
            ("creator", str),
            ("start_button", str),
            ("title", str),
            ("message", str)
        )

        # required fields
        for key, typ in requirements:
            if key not in info.fields:
                raise BuilderError(f"Missing required field '{key}' in info block")
            val = info.fields[key]
            if not isinstance(val, typ):
                raise BuilderError(f"Field '{key}' must be of type {self.type_name(typ)}")
            result[key] = val

        # optional fields
        for key, typ in optional:
            if key in info.fields:
                val = info.fields[key]
                if not isinstance(val, typ):
                    raise BuilderError(f"Field '{key}' must be of type {self.type_name(typ)}")
                result[key] = val

        if "tags" in info.fields:
            try:
                result["tags"] = list(map(str, info.fields["tags"]))
            except:
                raise BuilderError("Tags must be of type list[str], but has a different")

        self.game["info"] = result

    def analyze_scene(self, scene: SceneBlock):
        name: str = scene.name
        fields: dict[str, Any] = scene.fields

        # required fields
        required: tuple[tuple[str, type], ...] = (
            ("title", str),
            ("message", str),
        )

        # optional fields
        optional: tuple[tuple[str, type | tuple[type, ...], Any], ...] = (
            ("image", str, None),
            ("use_italics", bool, False),
            ("parse_mode", str, "Markdown")
        )

        scene_data: dict[str, Any] = {"name": name}

        # check required fields
        for key, typ in required:
            if key not in fields:
                raise BuilderError(
                    f"Scene '@ {name}' must contain '{key}' field\n\n"
                    f"Example:\n"
                    f"@ {name}" + " {\n"
                    + "\n".join(f"  {k} = \"...\";" for k, _ in required)
                    + "\n}"
                )
            val = fields[key]
            if not isinstance(val, typ):
                raise BuilderError(f"Field '{key}' in scene '@ {name}' must be of type {self.type_name(typ)}")
            scene_data[key] = val

        # check optional fields
        for key, typ, default in optional:
            if key in fields:
                val = fields[key]
                if not isinstance(val, typ):
                    raise BuilderError(f"Field '{key}' in scene '@ {name}' must be of type {self.type_name(typ)}")
                scene_data[key] = val
            else:
                scene_data[key] = default

        scene_data["buttons"] = {}

        # handle buttons if present
        if "buttons" in fields:
            buttons_block = fields["buttons"]
            buttons: dict[str, str] = buttons_block.get("buttons", [])

            width = buttons_block.get("width", 1) # row_width
            scene_data["row_width"] = int(width)

            for label, target in buttons.items():

                if label in scene_data["buttons"]:
                    raise BuilderError(f"Duplicate button label '{label}' in scene '@ {name}'")

                scene_data["buttons"][label] = target

        self.game["scenes"][scene.name] = scene_data

