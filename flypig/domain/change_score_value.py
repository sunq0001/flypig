from flypig.shared.base import ValueObject

class ChangeLevel(ValueObject):
    def __init__(self, level: str = "info") -> None:
        self._level = level
    def __str__(self) -> str:
        return self._level

class ChangeScore(ValueObject):
    def __init__(self, score: float = 0.0) -> None:
        self._score = score
    @property
    def score(self) -> float:
        return self._score
    def is_high_risk(self) -> bool:
        return self._score < 0.3
