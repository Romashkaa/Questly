from dataclasses import dataclass, field
from typing import Any

# ---------------------------
#  Base AST node
# ---------------------------

@dataclass
class Node:
	type: str

# ---------------------------
#  Game root
# ---------------------------

@dataclass
class Ast(Node):
	body: list = field(default_factory=list)

	def __init__(self):
		super().__init__(type="ast")
		self.body = []

# ---------------------------
#  Info block
# ---------------------------

@dataclass
class InfoBlock(Node):
	name: str
	fields: dict[str, Any] = field(default_factory=dict)

	def __init__(self, name: str):
		super().__init__(type="info")
		self.name = name
		self.fields = {}

# ---------------------------
#  Scene block
# ---------------------------

@dataclass
class SceneBlock(Node):
	name: str
	fields: dict[str, Any] = field(default_factory=dict)

	def __init__(self, name: str):
		super().__init__(type="scene")
		self.name = name
		self.fields = {}