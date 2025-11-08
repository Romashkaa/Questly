from dataclasses import dataclass

# ---------------------------
#  Helper structures
# ---------------------------

@dataclass
class Token:
	type: str
	value: str
	position: int