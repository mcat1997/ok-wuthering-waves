from dataclasses import dataclass, field
from typing import Any

from ok import Logger

from src.char.BaseChar import BaseChar

logger = Logger.get_logger(__name__)


@dataclass(frozen=True)
class TeamRotationStep:
    char_cls: type[BaseChar]
    method: str | None = None
    next_char_cls: type[BaseChar] | None = None
    label: str = ''
    kwargs: dict[str, Any] = field(default_factory=dict)
    fallback_on_fail: bool = False


class TeamRotation:
    name = 'Team Rotation'
    required_char_classes: tuple[type[BaseChar], ...] = ()
    steps: tuple[TeamRotationStep, ...] = ()

    def __init__(self, task):
        self.task = task
        self.combat_start = getattr(task, 'combat_start', 0)
        self.step_index = 0
        self.disabled = False

    @classmethod
    def matches(cls, chars):
        present = [char for char in chars if char is not None]
        return len(present) == len(cls.required_char_classes) and all(
            any(isinstance(char, required) for char in present)
            for required in cls.required_char_classes
        )

    def still_matches(self):
        return self.matches(getattr(self.task, 'chars', []))

    def char(self, char_cls):
        for char in self.task.chars:
            if isinstance(char, char_cls):
                return char
        return None

    def ensure_current_char(self, target):
        if target.is_current_char:
            return True
        current = self.task.get_current_char(raise_exception=False)
        if current is None:
            return False
        self.task.switch_to_char(current, target)
        return target.is_current_char

    def perform(self):
        if self.disabled or not self.steps:
            return False
        step = self.steps[self.step_index]
        char = self.char(step.char_cls)
        if char is None or not self.ensure_current_char(char):
            logger.warning(f'{self.name} can not align step {self.step_index}: {step.label}')
            return False

        logger.info(
            f'{self.name} step {self.step_index + 1}/{len(self.steps)} start '
            f'label={step.label or step.char_cls.__name__}')
        if step.method:
            method = getattr(char, step.method, None)
            if not callable(method):
                logger.warning(f'{self.name} missing method char={char} method={step.method}')
                return False
            result = method(**step.kwargs)
            if result is False:
                if step.fallback_on_fail:
                    self.disabled = True
                    logger.warning(f'{self.name} disabled after step failure: {step.label}')
                    return False
                logger.warning(f'{self.name} holds failed step: {step.label}')
                return True

        if step.next_char_cls is not None:
            next_char = self.char(step.next_char_cls)
            if next_char is None:
                return False
            self.task.switch_to_char(char, next_char)

        self.step_index = (self.step_index + 1) % len(self.steps)
        logger.info(f'{self.name} step end next_step={self.step_index + 1}/{len(self.steps)}')
        return True


def select_team_rotation(task):
    if not task.config.get('Use Team Rotation', True):
        return None

    from src.team.cartethyia_ciaccona_aero_rover import CartethyiaCiacconaAeroRoverRotation

    combat_start = getattr(task, 'combat_start', 0)
    existing = getattr(task, '_team_rotation', None)
    if existing and existing.still_matches() and existing.combat_start == combat_start:
        return None if existing.disabled else existing

    for rotation_cls in (CartethyiaCiacconaAeroRoverRotation,):
        if rotation_cls.matches(getattr(task, 'chars', [])):
            rotation = rotation_cls(task)
            task._team_rotation = rotation
            logger.info(f'selected team rotation {rotation.name}')
            return rotation

    task._team_rotation = None
    return None
