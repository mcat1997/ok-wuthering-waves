import time
from dataclasses import dataclass, field
from typing import Any

from ok import Logger

from src.char.BaseChar import BaseChar

logger = Logger.get_logger(__name__)


def _team_signature(chars):
    return ','.join(f'{char.__class__.__name__}[{char.index}]' for char in chars if char is not None) or 'empty'


def _short_value(value):
    text = repr(value)
    if len(text) > 160:
        return text[:157] + '...'
    return text


def _action_label(action):
    detail = [action.label or action.name]
    if action.count:
        detail.append(f'count={action.count}')
    if action.duration:
        detail.append(f'duration={action.duration}')
    visible_kwargs = {
        key: value for key, value in action.kwargs.items()
        if key not in {'pre_delay', 'post_delay'}
    }
    if action.kwargs.get('pre_delay'):
        detail.append(f'pre_delay={action.kwargs["pre_delay"]}')
    if action.kwargs.get('post_delay'):
        detail.append(f'post_delay={action.kwargs["post_delay"]}')
    if visible_kwargs:
        detail.append(f'kwargs={visible_kwargs}')
    return ' '.join(detail)


def _log_once(task, key, message, level='info'):
    logged = getattr(task, '_team_rotation_log_keys', set())
    if key in logged:
        return
    getattr(logger, level)(message)
    logged.add(key)
    task._team_rotation_log_keys = logged


def _action_kwargs(action, *exclude):
    excluded = {'pre_delay', 'post_delay', *exclude}
    return {key: value for key, value in action.kwargs.items() if key not in excluded}


@dataclass(frozen=True)
class TeamAction:
    name: str
    label: str = ''
    count: int = 0
    duration: float = 0
    kwargs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TeamRotationStep:
    char_cls: type[BaseChar]
    actions: tuple[TeamAction, ...]
    next_char_cls: type[BaseChar] | None = None
    next_free_intro: bool = False
    label: str = ''


class TeamActionRunner:

    def __init__(self, task):
        self.task = task

    def run(self, char: BaseChar, action: TeamAction, context=''):
        handler = getattr(self, f'_run_{action.name}', None)
        if handler is None:
            raise ValueError(f'Unknown team action: {action.name}')
        start = time.time()
        logger.info(f'team action start {context} char={char} action={_action_label(action)}')
        try:
            pre_delay = action.kwargs.get('pre_delay', 0)
            if pre_delay > 0:
                logger.info(f'team action pre delay {context} char={char} action={action.label or action.name} '
                            f'duration={pre_delay}s')
                char.sleep(pre_delay)
            result = handler(char, action)
            post_delay = action.kwargs.get('post_delay', 0)
            if post_delay > 0:
                logger.info(f'team action post delay {context} char={char} action={action.label or action.name} '
                            f'duration={post_delay}s')
                char.sleep(post_delay)
        except Exception as e:
            logger.error(
                f'team action failed {context} char={char} action={_action_label(action)} '
                f'elapsed={time.time() - start:.2f}s error={e}')
            raise
        logger.info(
            f'team action end {context} char={char} action={_action_label(action)} '
            f'elapsed={time.time() - start:.2f}s result={_short_value(result)}')
        return result

    def _run_wait(self, char: BaseChar, action: TeamAction):
        char.sleep(action.duration)

    def _run_normal(self, char: BaseChar, action: TeamAction):
        count = action.count if action.count > 0 else 1
        interval = action.kwargs.get('interval', 0.12)
        for _ in range(count):
            char.normal_attack()
            char.sleep(interval)

    def _run_normal_chain(self, char: BaseChar, action: TeamAction):
        duration = action.duration if action.duration > 0 else 0.6
        char.continues_normal_attack(duration, interval=action.kwargs.get('interval', 0.1))

    def _run_tap_normal_chain(self, char: BaseChar, action: TeamAction):
        duration = action.duration if action.duration > 0 else 0.7
        char.continues_normal_attack(duration, interval=action.kwargs.get('interval', 0.08))

    def _run_resonance(self, char: BaseChar, action: TeamAction):
        kwargs = {'time_out': action.kwargs.get('time_out', 1)}
        kwargs.update(_action_kwargs(action))
        return char.click_resonance(**kwargs)

    def _run_enhanced_resonance(self, char: BaseChar, action: TeamAction):
        wait_time = action.kwargs.get('wait_time', 1.2)
        enhanced_available = getattr(char, 'enhance_e_available', None)
        if callable(enhanced_available):
            wait_result = self.task.wait_until(enhanced_available, time_out=wait_time, raise_if_not_found=False)
            logger.info(f'team action enhanced resonance wait char={char} timeout={wait_time}s result={wait_result}')
        kwargs = {'send_click': True, 'time_out': action.kwargs.get('time_out', 1.5)}
        kwargs.update(_action_kwargs(action, 'wait_time'))
        return char.click_resonance(**kwargs)

    def _run_liberation(self, char: BaseChar, action: TeamAction):
        char_liberation = getattr(char, 'lib', None)
        if callable(char_liberation):
            return char_liberation()
        kwargs = {'wait_if_cd_ready': action.kwargs.get('wait_if_cd_ready', 0)}
        kwargs.update(_action_kwargs(action))
        return char.click_liberation(**kwargs)

    def _run_echo(self, char: BaseChar, action: TeamAction):
        kwargs = {'time_out': action.kwargs.get('time_out', 0)}
        kwargs.update(_action_kwargs(action))
        return char.click_echo(**kwargs)

    def _run_heavy(self, char: BaseChar, action: TeamAction):
        duration = action.duration if action.duration > 0 else 0.6
        return char.heavy_attack(duration)

    def _run_execute(self, char: BaseChar, action: TeamAction):
        handle_heavy = getattr(char, 'handle_heavy', None)
        if callable(handle_heavy) and handle_heavy():
            return True
        duration = action.duration if action.duration > 0 else 1.0
        return char.heavy_attack(duration)

    def _run_forte(self, char: BaseChar, action: TeamAction):
        perform_forte = getattr(char, 'perform_forte', None)
        if callable(perform_forte):
            return perform_forte()
        return char.heavy_click_forte(char.is_forte_full)

    def _run_f_break(self, char: BaseChar, action: TeamAction):
        return char.f_break()


class TeamRotation:
    required_char_classes: tuple[type[BaseChar], ...] = ()
    startup_steps: tuple[TeamRotationStep, ...] = ()
    loop_steps: tuple[TeamRotationStep, ...] = ()
    name = 'Team Rotation'

    def __init__(self, task):
        self.task = task
        self.runner = TeamActionRunner(task)
        self.combat_start = getattr(task, 'combat_start', 0)
        self.startup_index = 0
        self.loop_index = 0
        self.startup_done = False
        logger.info(
            f'{self.name} init combat_start={self.combat_start} '
            f'team={_team_signature(getattr(task, "chars", []))} '
            f'startup_steps={len(self.startup_steps)} loop_steps={len(self.loop_steps)}')

    @classmethod
    def matches(cls, chars):
        if not cls.required_char_classes:
            return False
        present = [char for char in chars if char is not None]
        return all(any(isinstance(char, required) for char in present) for required in cls.required_char_classes)

    def still_matches(self):
        return self.matches(getattr(self.task, 'chars', []))

    def char(self, char_cls: type[BaseChar]):
        for char in self.task.chars:
            if isinstance(char, char_cls):
                return char
        return None

    def current_step(self):
        if not self.startup_done and self.startup_steps:
            return self.startup_steps[self.startup_index]
        if not self.loop_steps:
            return None
        return self.loop_steps[self.loop_index]

    def step_context(self):
        if not self.startup_done and self.startup_steps:
            return f'{self.name} startup {self.startup_index + 1}/{len(self.startup_steps)}'
        if self.loop_steps:
            return f'{self.name} loop {self.loop_index + 1}/{len(self.loop_steps)}'
        return f'{self.name} no-step'

    def advance(self):
        before = self.step_context()
        if not self.startup_done and self.startup_steps:
            self.startup_index += 1
            if self.startup_index >= len(self.startup_steps):
                self.startup_done = True
                self.loop_index = 0
            logger.info(f'{self.name} advance {before} -> {self.step_context()}')
            return
        if self.loop_steps:
            self.loop_index = (self.loop_index + 1) % len(self.loop_steps)
            logger.info(f'{self.name} advance {before} -> {self.step_context()}')

    def ensure_current_char(self, target: BaseChar):
        if target.is_current_char:
            logger.info(f'{self.name} current char aligned target={target}')
            return True
        current = self.task.get_current_char(raise_exception=False)
        if current is None:
            logger.warning(f'{self.name} can not align current char because current char is unknown')
            return False
        logger.info(f'{self.name} align current char {current} -> {target}')
        self.task.switch_to_char(current, target)
        return target.is_current_char

    def handle_intro(self, char: BaseChar):
        if not char.has_intro:
            return
        intro_key = getattr(char, 'last_switch_in_time', -1)
        if getattr(char, '_team_rotation_intro_key', None) == intro_key:
            return
        logger.info(f'{self.name} intro hook char={char} switch_in={intro_key}')
        record_intro_liberation = getattr(char, 'record_intro_liberation', None)
        if callable(record_intro_liberation):
            logger.info(f'{self.name} record intro liberation char={char}')
            record_intro_liberation()
        char._team_rotation_intro_key = intro_key

    def perform(self):
        step = self.current_step()
        if step is None:
            logger.warning(f'{self.name} no current step, fallback to role axis')
            return False
        char = self.char(step.char_cls)
        if char is None:
            logger.warning(f'{self.name} missing char for step {step.label}')
            return False

        context = self.step_context()
        logger.info(
            f'{context} begin label={step.label or step.char_cls.__name__} '
            f'char={char} next={step.next_char_cls.__name__ if step.next_char_cls else None} '
            f'actions={len(step.actions)}')
        if not self.ensure_current_char(char):
            logger.warning(f'{context} failed to align char={char}, fallback to role axis')
            return False
        self.handle_intro(char)
        for action in step.actions:
            self.runner.run(char, action, context=context)

        if step.next_char_cls is not None:
            next_char = self.char(step.next_char_cls)
            if next_char is not None:
                logger.info(
                    f'{context} switch request current={char} next={next_char} '
                    f'free_intro={step.next_free_intro}')
                self.task.switch_to_char(char, next_char, free_intro=step.next_free_intro)
            else:
                logger.warning(f'{context} missing next char {step.next_char_cls.__name__}, skip switch')
        logger.info(f'{context} end label={step.label or step.char_cls.__name__}')
        self.advance()
        return True


def select_team_rotation(task):
    chars = getattr(task, 'chars', [])
    combat_start = getattr(task, 'combat_start', 0)
    signature = _team_signature(chars)
    if not task.config.get('Use Team Axis'):
        _log_once(task, (combat_start, 'disabled', signature),
                  f'team rotation disabled combat_start={combat_start} team={signature}')
        return None

    from src.team.aemeath_denia_chisa import AemeathDeniaChisaRotation

    existing = getattr(task, '_team_rotation', None)
    if existing and existing.combat_start == combat_start and existing.still_matches():
        return existing
    if existing and existing.combat_start == combat_start and not existing.still_matches():
        _log_once(task, (combat_start, 'lost-match', signature),
                  f'team rotation lost match old={existing.name} team={signature}', level='warning')

    for rotation_cls in (AemeathDeniaChisaRotation,):
        if rotation_cls.matches(chars):
            rotation = rotation_cls(task)
            task._team_rotation = rotation
            logger.info(f'selected team rotation {rotation.name} combat_start={combat_start} team={signature}')
            return rotation

    task._team_rotation = None
    _log_once(task, (combat_start, 'no-match', signature),
              f'no team rotation matched combat_start={combat_start} team={signature}')
    return None
