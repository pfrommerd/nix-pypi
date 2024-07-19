from dataclasses import dataclass

from typing import Iterable

class NixExporter:
    def expression(self, recipes : Iterable[Recipe]) -> str:
        pass