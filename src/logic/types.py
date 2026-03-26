from dataclasses import dataclass
from typing import Literal


@dataclass
class Var:
    label: str
    symbol: str
    chromosome: str


@dataclass
class PertSpec:
    ptype: Literal["KO", "AC", "OE"]
    gene: str
