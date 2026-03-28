from dataclasses import dataclass
from typing import Literal


@dataclass
class PertSpec:
    ptype: Literal["KO", "AC", "OE"]
    gene: str
