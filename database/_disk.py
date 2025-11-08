import os, json, shutil, ast
from fs.osfs import OSFS
from typing import Union, List, Optional

PATH = str
FS_PATH = str
PATH_EXT = str
FS_PATH_EXT = str

DIRECTORY = "directory"
FILE = "file"
TYPE = str  # "directory" | "file"

DB_PATH = "database/data"


from datetime import datetime

def get_current_time_info() -> dict[str, str | float | int]:
    now = datetime.now()
    return {
        "year": now.year,
        "month": now.month,
        "day": now.day,
        "hour": now.hour,
        "minute": now.minute,
        "second": now.second,
        "time": f"{now.hour:02}:{now.minute:02}:{now.second:02}",
        "timestamp": now.timestamp()
    }

def update_versions(disk: "Disk", file: "File"):
    pass


# -----------------------------
# ExtractedFile
# -----------------------------
class ExtractedFile:
    def __init__(
        self,
        name: str,
        type: TYPE,
        value=None,
        meta: Optional[dict] = None,
        children: Optional[List["ExtractedFile"]] = None,
    ):
        self.name = name
        self.type = type
        self.value = value
        self.meta = meta or {}
        self.children = children or []

    def __repr__(self):
        return f"<ExtractedFile {self.type} {self.name}>"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "value": self.value,
            "meta": self.meta,
            "children": [c.to_dict() for c in self.children],
        }


# -----------------------------
# Meta API
# -----------------------------
class MetaData:
    def __init__(self, parent: "Meta", key: str):
        self.parent = parent
        self.key = key or ""

    def _parts(self) -> List[str]:
        return [p for p in self.key.split("/") if p != ""]

    def _get_container_and_key(self, create: bool = False):
        node = self.parent.data
        parts = self._parts()
        if not parts:
            return node, None
        for p in parts[:-1]:
            if not isinstance(node, dict):
                if create:
                    node = {}
                else:
                    return None, None
            if p not in node:
                if create:
                    node[p] = {}
                else:
                    return None, None
            node = node[p]
        last = parts[-1]
        return node, last

    @property
    def value(self):
        node, last = self._get_container_and_key(create=False)
        if node is None:
            return None
        if last is None:
            return node
        return node.get(last)

    def set(self, value):
        node, last = self._get_container_and_key(create=True)
        if node is None:
            self.parent.data = value if isinstance(value, dict) else {}
        else:
            if last is None:
                self.parent.data = dict(value) if isinstance(value, dict) else {}
            else:
                node[last] = value
        self.parent.save()
        return self

    def add(self, subkey, value):
        node, last = self._get_container_and_key(create=True)
        if last is None:
            target = node
        else:
            target = node.get(last)
            if not isinstance(target, dict):
                target = {}
                node[last] = target
        target[subkey] = value
        self.parent.save()
        return self

    def get(self, subkey, default=None):
        new_key = f"{self.key}/{subkey}" if self.key else subkey
        md = MetaData(self.parent, new_key)
        if default is not None and md.value is None:
            md.set(default)
        return md
    
    def __getitem__(self, key):
        return self.get(key, {})
    
    def delete(self):
        node, last = self._get_container_and_key(create=False)
        if node is None or last is None:
            return False
        if last in node:
            del node[last]
            self.parent.save()
            return True
        return False


class Meta:
    def __init__(self, file: "File"):
        self.file = file
        self.data = self.file.disk._read_meta(self.file) or {}

    def all(self) -> dict:
        return self.data

    def get(self, key: str, default=None) -> MetaData:
        if key not in self.data and default is not None:
            self.data[key] = default
            self.save()
        return MetaData(self, key)
    
    def __getitem__(self, key: str) -> MetaData:
        return self.get(key, {})

    def set(self, meta: dict):
        if not isinstance(meta, dict):
            raise TypeError("meta must be a dict")
        self.data = dict(meta)
        self.save()
        return self

    def set_highlight(self, lang: str):
        self.data["highlight"] = lang
        self.save()

    def save(self):
        update_versions(self.file.disk, self.file)
        self.file.disk._write_meta(self.file, self.data)


# -----------------------------
# File API
# -----------------------------
class File:
    def __init__(self, disk: "Disk", path: PATH):
        self.disk = disk
        self.path = path
        self.fs_path = disk._fs_path(path)
        self.fs_path_ext = disk._resolve_path(self.fs_path)
        self.meta = Meta(self)

    @property
    def name(self) -> str:
        return os.path.basename(self.path)

    @property
    def dir(self) -> "File":
        return File(self.disk, os.path.dirname(self.path))
    
    @property
    def type(self) -> Optional[TYPE]:
        if self.is_directory():
            return DIRECTORY
        if self.is_file():
            return FILE
        return None

    def exists(self) -> bool:
        return self.fs_path_ext is not None and os.path.exists(self.fs_path_ext)

    def is_file(self) -> bool:
        return bool(self.fs_path_ext) and os.path.isfile(self.fs_path_ext)

    def is_directory(self) -> bool:
        return bool(self.fs_path_ext) and os.path.isdir(self.fs_path_ext)

    @property
    def value(self):
        return self.get_value()

    def get_meta(self) -> dict:
        return self.meta.all()

    def get(self, subpath: str) -> "File":
        if self.exists() and self.is_file():
            saved_meta = self.meta.all() or {}
            self.disk.delete_data(self.path, delete_meta=True)
            os.makedirs(self.fs_path, exist_ok=True)
            self.fs_path_ext = self.fs_path
            self.meta = Meta(self)
            if saved_meta:
                self.meta.set(saved_meta)
        new_path = os.path.join(self.path, subpath)
        return File(self.disk, new_path)

    def __getitem__(self, subpath: str) -> "File":
        return self.get(subpath)

    def all(self):
        if not self.exists() or self.is_file():
            return
            yield
        for name in os.listdir(self.fs_path_ext):
            if name == ".DS_Store" or name.endswith(".meta.json"):
                continue
            base, _ = os.path.splitext(name)
            yield self.get(base)

    def __iter__(self):
        yield from self.all()

    def name_value(self):
        for f in self.all():
            yield (f.name, f.get_value())

    def names(self):
        for f in self.all():
            yield f.name

    def listdir(self) -> List["File"]:
        return [f for f in self.all()]

    def get_value(self, default=None):
        if not self.exists():
            return default
        if self.is_directory():
            return {f: self.get(f).type for f in os.listdir(self.fs_path_ext) if f != ".DS_Store"}
        if self.fs_path_ext.endswith(".py"):
            try:
                with open(self.fs_path_ext, "r", encoding="utf-8") as f:
                    return ast.literal_eval(f.read())
            except Exception:
                return default
        try:
            with open(self.fs_path_ext, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return default
        
    def get_value_no_default(self):
        if not self.exists():
            raise Exception()
        if self.is_directory():
            return {f: self.get(f).type for f in os.listdir(self.fs_path_ext) if f != ".DS_Store"}
        if self.fs_path_ext.endswith(".py"):
            try:
                with open(self.fs_path_ext, "r", encoding="utf-8") as f:
                    return ast.literal_eval(f.read())
            except Exception:
                raise Exception()
        try:
            with open(self.fs_path_ext, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            raise Exception()

    def set_value(self, value):
        if self.disk._is_protected(self.path):
            raise PermissionError(f"Path '{self.path}' is protected and cannot be modified")
        saved_meta = self.meta.all() or {}
        if self.exists() and self.is_directory():
            shutil.rmtree(str(self.fs_path_ext))
        os.makedirs(os.path.dirname(self.fs_path), exist_ok=True)
        is_py = not isinstance(value, str)
        new_fs_path_ext = self.fs_path + (".py" if is_py else ".txt")
        for ext in [".txt", ".py"]:
            alt = self.fs_path + ext
            if alt != new_fs_path_ext and os.path.exists(alt):
                os.remove(alt)
        with open(new_fs_path_ext, "w", encoding="utf-8") as f:
            if new_fs_path_ext.endswith(".py"):
                f.write(str(value))
            else:
                f.write(str(value))
        self.fs_path_ext = new_fs_path_ext
        self.meta = Meta(self)
        if saved_meta:
            self.meta.set(saved_meta)
        else:
            self.meta.save()
        return self
    
    def push_value(self, push):
        value = self.get_value()
        if not isinstance(value, str):
            value = ""
        self.set_value(value + str(push))
    
    def delete(self, delete_meta: bool = True):
        if self.disk._is_protected(self.path):
            raise PermissionError(f"Path '{self.path}' is protected and cannot be deleted!")
        if self.exists():
            self.disk.delete_data(self.path, delete_meta=delete_meta)
        return self

    def mkdir(self, children: Optional[List[Union[ExtractedFile, "File"]]] = None):
        if self.disk._is_protected(self.path):
            raise PermissionError(f"Path '{self.path}' is protected and cannot be modified")
        if self.exists() and self.is_file():
            os.remove(self.fs_path_ext)
        os.makedirs(self.fs_path, exist_ok=True)
        self.fs_path_ext = self.fs_path
        self.meta = Meta(self)
        if children:
            for ch in children:
                if isinstance(ch, ExtractedFile):
                    sub = self.get(ch.name)
                    if ch.type == FILE:
                        sub.mkfile({"value": ch.value, "meta": ch.meta})
                    else:
                        sub.mkdir(ch.children)
                        if ch.meta:
                            sub.meta.set(ch.meta)
                elif isinstance(ch, File):
                    ext = ch.extract()
                    sub = self.get(ext.name)
                    sub.set(ext)
        return self

    def mkfile(self, data: dict):
        if self.disk._is_protected(self.path):
            raise PermissionError(f"Path '{self.path}' is protected and cannot be modified")
        if self.exists():
            self.disk.delete_data(self.path, delete_meta=True)
        self.set_value(data.get("value", ""))
        if "meta" in data:
            self.meta.set(data["meta"])
        return self

    def extract(self) -> Optional[ExtractedFile]:
        if self.is_file():
            return ExtractedFile(name=self.name, type=FILE, value=self.get_value(), meta=self.meta.all())
        if self.is_directory():
            children = []
            for ch in os.listdir(self.fs_path_ext):
                if ch == ".DS_Store":
                    continue
                children.append(self.get(ch).extract())
            return ExtractedFile(name=self.name, type=DIRECTORY, meta=self.meta.all(), children=children)
        return None

    def set(self, other: Union["File", ExtractedFile]):
        if self.disk._is_protected(self.path):
            raise PermissionError(f"Path '{self.path}' is protected and cannot be modified")
        if isinstance(other, ExtractedFile):
            if other.type == FILE:
                self.mkfile({"value": other.value, "meta": other.meta})
            else:
                self.mkdir()
                for child in other.children:
                    self.get(child.name).set(child)
                if other.meta:
                    self.meta.set(other.meta)
        elif isinstance(other, File):
            extracted = other.extract()
            if extracted:
                self.set(extracted)
        return self
    
    def boolean(self, default: bool=False, update: bool=False) -> bool:
        value = self.get_value(default)
        boolean: bool = str(value).lower() in ("true", "t")
        if update:
            self.set_value(boolean)
        return boolean
    
    def clear(self, ignore: list[str]=[]):
        """
        Clear the folder if it exists. 
        If it's a file, replace it with an empty folder.
        Works only for folders.
        """
        # Check protection
        if self.disk._is_protected(self.path):
            raise PermissionError(f"Path '{self.path}' is protected and cannot be modified")

        # If path exists
        if self.exists():
            if self.is_directory():
                # Clear all contents inside the folder
                for file in self:
                    if file.name not in ignore:
                        file.delete()
            else:
                # Delete the file to replace with a folder
                os.remove(str(self.fs_path_ext)) 

        # Ensure folder exists
        self.mkdir()
        return self


# -----------------------------
# Disk API
# -----------------------------
class Disk:
    def __init__(self):
        self.root = DB_PATH
        self.fs = OSFS(self.root, create=True)

    def _fs_path(self, path: PATH) -> FS_PATH:
        return os.path.join(self.root, path.lstrip("/"))

    def _resolve_path(self, fs_path: FS_PATH) -> Optional[FS_PATH_EXT]:
        if os.path.exists(fs_path):
            return fs_path
        for ext in [".txt", ".py"]:
            if os.path.exists(fs_path + ext):
                return fs_path + ext
        if os.path.isdir(fs_path):
            return fs_path
        return None

    def _meta_path(self, fs_path_ext: FS_PATH_EXT, type: TYPE) -> str:
        if type == DIRECTORY:
            return os.path.join(fs_path_ext, ".meta.json")
        base, _ = os.path.splitext(os.path.basename(fs_path_ext))
        return os.path.join(os.path.dirname(fs_path_ext), f".{base}.meta.json")
    
    def home(self):
        return File(self, "")

    def get(self, path: PATH) -> File:
        return File(self, path)

    def __getitem__(self, path: PATH) -> File:
        return self.get(path)

    @property
    def meta(self) -> Meta:
        return Meta(self.get("."))

    def listdir(self, path: PATH = ".") -> List[File]:
        return self.get(path).listdir()
    
    def _is_protected(self, path: PATH) -> bool:
        # for p in state.State.REC_PROTECTED_DIRS:
        #     if path.startswith(f"{p}/"):
        #         return True
            
        # norm = path.strip("/")
        # for p in state.State.PROTECTED_DIRS:
        #     if norm == p.strip("/") or norm.startswith(p.strip("/") + "/"):
        #         return True
            
        return False

    def delete_data(self, path: PATH, delete_meta: bool = True):
        if self._is_protected(path):
            raise PermissionError(f"Path '{path}' is protected and cannot be deleted")
    
        f = self.get(path)
        update_versions(self, f)
        if not f.exists():
            return
        if f.is_directory():
            shutil.rmtree(f.fs_path_ext)
        elif f.is_file():
            os.remove(f.fs_path_ext)
        if delete_meta:
            meta_path = self._meta_path(f.fs_path_ext, f.type)
            if os.path.exists(meta_path):
                os.remove(meta_path)
        f.fs_path_ext = None

    def _read_meta(self, file: File) -> dict:
        if not file.fs_path_ext:
            return {}
        path = self._meta_path(file.fs_path_ext, file.type)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_meta(self, file: File, meta: dict):
        if self._is_protected(file.path):
            raise PermissionError(f"Path '{file.path}' is protected and cannot be deleted")
        
        if not file.fs_path_ext:
            return
        
        # meta.update({"timestamp": get_current_time_info()})

        if not meta:
            return
        
        path = self._meta_path(file.fs_path_ext, file.type)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    def set_value(self, path: str, value) -> File:
        return self.get(path).set_value(value)
    
    def get_value(self, path: str, default=None):
        return self.get(path).get_value(default)
    
    def clear(self):
        if os.path.exists(self.root):
            shutil.rmtree(self.root)
        os.makedirs(self.root, exist_ok=True)

# -----------------------------
# RAM
# -----------------------------

raw_ram = {}

class Ram:
    raw = raw_ram

    def get(self, key: str, default=None):
        return raw_ram.get(key, default)

    def set(self, key, value):
        raw_ram[key] = value