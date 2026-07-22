import time
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
        return self.switch_immediately(current, target)

    def switch_immediately(self, current, target):
        """在合轴点立即发送切人，只等待目标角色位实际生效。"""
        if target.is_current_char:
            return True

        start = time.time()
        last_send = start
        self.task.send_key(target.index + 1)
        while time.time() - start < self.task.switch_char_time_out:
            in_team, current_index, _ = self.task.in_team()
            if in_team and current_index == target.index:
                self.task.in_liberation = False
                current.switch_out(con_full=False)
                target.has_intro = False
                target.has_sub_dps_intro = False
                target.is_current_char = True
                target.last_switch_in_time = time.time()
                logger.info(
                    f'{self.name} immediate switch {current} -> {target} '
                    f'end {target.last_switch_in_time - start:.3f}s')
                return True

            now = time.time()
            if now - last_send > 0.1:
                self.task.send_key(target.index + 1)
                last_send = now
            self.task.next_frame()

        logger.warning(f'{self.name} immediate switch failed {current} -> {target}')
        return False

    def fail_step(self, step, reason):
        self.disabled = True
        logger.warning(f'{self.name} disabled at step: {step.label}; reason={reason}')
        self.task.check_combat()
        return False

    def perform(self):
        if self.disabled or not self.steps:
            return False

        for _ in range(len(self.steps)):
            step = self.steps[self.step_index]
            char = self.char(step.char_cls)
            if char is None or not self.ensure_current_char(char):
                return self.fail_step(step, 'can not align current character')

            logger.info(
                f'{self.name} step {self.step_index + 1}/{len(self.steps)} start '
                f'label={step.label or step.char_cls.__name__}')
            if step.method:
                method = getattr(char, step.method, None)
                if not callable(method):
                    return self.fail_step(step, f'missing method {step.method}')
                if method(**step.kwargs) is False:
                    return self.fail_step(step, 'action failed')

            if step.next_char_cls is not None:
                next_char = self.char(step.next_char_cls)
                if next_char is None:
                    return self.fail_step(step, 'next character not found')
                if not self.switch_immediately(char, next_char):
                    return self.fail_step(step, 'switch failed')

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
