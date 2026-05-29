import time
from dataclasses import dataclass, field
from typing import Any

from ok import Logger

from src.char.BaseChar import BaseChar

logger = Logger.get_logger(__name__)

_ACTION_META_KEYS = (
    'pre_delay',
    'post_delay',
    'attempts',
    'retry_delay',
    'required',
    'force_on_fail',
    'force_down_time',
    'force_post_sleep',
    'require_available',
    'require_lib2',
    'stop_on_fail',
    'until_con_full',
)
_ACTION_META_KEY_SET = set(_ACTION_META_KEYS)

_TRANSIENT_OUT_OF_COMBAT_REASONS = (
    'target enemy failed',
    'combat check not in combat',
    'sleep check not in combat',
    'not in_team while switching',
    'failed switch chars',
)


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
        if key not in _ACTION_META_KEY_SET
    }
    for key in _ACTION_META_KEYS:
        if action.kwargs.get(key):
            detail.append(f'{key}={action.kwargs[key]}')
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
    excluded = {*_ACTION_META_KEY_SET, *exclude}
    return {key: value for key, value in action.kwargs.items() if key not in excluded}


def _action_succeeded(result):
    if result is None:
        return True
    if isinstance(result, tuple):
        return bool(result[0]) if result else False
    if isinstance(result, bool):
        return result
    return True


def _is_required(action):
    return bool(action.kwargs.get('required', False))


def _is_transient_out_of_combat(reason):
    reason = (reason or '').lower()
    return any(transient in reason for transient in _TRANSIENT_OUT_OF_COMBAT_REASONS)


def _team_axis_resume_window(task):
    try:
        return float(task.config.get('Team Axis Resume Window', 12))
    except (TypeError, ValueError):
        return 12


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
    intro_actions: tuple[TeamAction, ...] = ()
    intro_retry_limit: int = 0


class TeamActionRunner:

    def __init__(self, task):
        self.task = task

    def run(self, char: BaseChar, action: TeamAction, context=''):
        handler = getattr(self, f'_run_{action.name}', None)
        if handler is None:
            raise ValueError(f'Unknown team action: {action.name}')
        attempts = max(1, int(action.kwargs.get('attempts', 1) or 1))
        retry_delay = action.kwargs.get('retry_delay', 0.2)
        result = None
        for attempt in range(1, attempts + 1):
            start = time.time()
            logger.info(
                f'team action start {context} char={char} action={_action_label(action)} '
                f'attempt={attempt}/{attempts}')
            try:
                pre_delay = action.kwargs.get('pre_delay', 0)
                if pre_delay > 0:
                    logger.info(f'team action pre delay {context} char={char} action={action.label or action.name} '
                                f'duration={pre_delay}s attempt={attempt}/{attempts}')
                    char.sleep(pre_delay)
                result = handler(char, action)
                success = _action_succeeded(result)
                post_delay = action.kwargs.get('post_delay', 0)
                if post_delay > 0 and (success or attempt == attempts):
                    logger.info(f'team action post delay {context} char={char} action={action.label or action.name} '
                                f'duration={post_delay}s attempt={attempt}/{attempts}')
                    char.sleep(post_delay)
            except Exception as e:
                logger.error(
                    f'team action failed {context} char={char} action={_action_label(action)} '
                    f'attempt={attempt}/{attempts} elapsed={time.time() - start:.2f}s error={e}')
                raise
            logger.info(
                f'team action end {context} char={char} action={_action_label(action)} '
                f'attempt={attempt}/{attempts} elapsed={time.time() - start:.2f}s '
                f'success={success} result={_short_value(result)}')
            if success:
                return result
            if attempt < attempts:
                logger.warning(
                    f'team action unsuccessful {context} char={char} action={_action_label(action)} '
                    f'attempt={attempt}/{attempts} retry_delay={retry_delay}s result={_short_value(result)}')
                if retry_delay > 0:
                    char.sleep(retry_delay)
        logger.warning(
            f'team action exhausted {context} char={char} action={_action_label(action)} '
            f'attempts={attempts} result={_short_value(result)}')
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
        char.continues_normal_attack(duration, interval=action.kwargs.get('interval', 0.1),
                                     until_con_full=action.kwargs.get('until_con_full', False))

    def _run_tap_normal_chain(self, char: BaseChar, action: TeamAction):
        duration = action.duration if action.duration > 0 else 0.7
        char.continues_normal_attack(duration, interval=action.kwargs.get('interval', 0.08),
                                     until_con_full=action.kwargs.get('until_con_full', False))

    def _run_build_con(self, char: BaseChar, action: TeamAction):
        duration = action.duration if action.duration > 0 else action.kwargs.get('time_out', 2.0)
        interval = action.kwargs.get('interval', 0.08)
        start_con = char.get_current_con()
        if start_con == 1:
            logger.info(f'team action build con already full char={char} current_con={start_con}')
            return True
        char.continues_normal_attack(duration, interval=interval, until_con_full=True)
        end_con = char.get_current_con()
        logger.info(
            f'team action build con end char={char} duration={duration}s interval={interval}s '
            f'start_con={start_con} end_con={end_con}')
        return end_con == 1

    def _run_resonance(self, char: BaseChar, action: TeamAction):
        kwargs = {'time_out': action.kwargs.get('time_out', 1)}
        kwargs.update(_action_kwargs(action))
        return char.click_resonance(**kwargs)

    def _run_enhanced_resonance(self, char: BaseChar, action: TeamAction):
        wait_time = action.kwargs.get('wait_time', 1.2)
        enhanced_available = getattr(char, 'enhance_e_available', None)
        wait_result = True
        if callable(enhanced_available):
            wait_result = self.task.wait_until(enhanced_available, time_out=wait_time, raise_if_not_found=False)
            logger.info(f'team action enhanced resonance wait char={char} timeout={wait_time}s result={wait_result}')
            if action.kwargs.get('require_available', False) and not wait_result:
                logger.warning(
                    f'team action enhanced resonance unavailable char={char} action={_action_label(action)} '
                    f'timeout={wait_time}s')
                return False
        kwargs = {'send_click': True, 'time_out': action.kwargs.get('time_out', 1.5)}
        kwargs.update(_action_kwargs(action, 'wait_time'))
        result = char.click_resonance(**kwargs)
        if _action_succeeded(result):
            record_enhance_e = getattr(char, 'record_enhance_e', None)
            if callable(record_enhance_e) and wait_result:
                record_enhance_e()
            return result
        if action.kwargs.get('force_on_fail', False):
            down_time = action.kwargs.get('force_down_time', 0.05)
            post_sleep = action.kwargs.get('force_post_sleep', 0)
            logger.warning(
                f'team action force enhanced resonance key char={char} action={_action_label(action)} '
                f'original_result={_short_value(result)} down_time={down_time} post_sleep={post_sleep}')
            char.check_combat()
            char.send_resonance_key(post_sleep=post_sleep, down_time=down_time)
            return True
        return result

    def _run_raw_resonance(self, char: BaseChar, action: TeamAction):
        down_time = action.kwargs.get('down_time', action.duration if action.duration > 0 else 0.05)
        post_sleep = action.kwargs.get('post_sleep', 0)
        char.check_combat()
        char.send_resonance_key(post_sleep=post_sleep, interval=action.kwargs.get('interval', -1),
                                down_time=down_time)
        return True

    def _run_liberation(self, char: BaseChar, action: TeamAction):
        char_liberation = getattr(char, 'lib', None)
        if action.kwargs.get('require_lib2', False):
            lib2_available = getattr(char, 'lib2_available', None)
            if callable(lib2_available):
                wait_time = action.kwargs.get('wait_time', 1.2)
                wait_result = self.task.wait_until(lib2_available, time_out=wait_time, raise_if_not_found=False)
                logger.info(f'team action liberation lib2 wait char={char} timeout={wait_time}s result={wait_result}')
                if not wait_result:
                    return False
        if callable(char_liberation):
            return char_liberation()
        kwargs = {'wait_if_cd_ready': action.kwargs.get('wait_if_cd_ready', 0)}
        kwargs.update(_action_kwargs(action, 'wait_time'))
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
        self.action_index = 0
        self.intro_retry_count = 0
        self.startup_done = False
        self.last_active_time = time.time()
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
        self.action_index = 0
        self.intro_retry_count = 0
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

    def _check_intro_ready(self, char: BaseChar, context: str, phase: str):
        try:
            current_con = char.get_current_con()
        except Exception as e:
            logger.warning(f'{context} intro readiness check failed phase={phase} char={char} error={e}')
            return False, 0
        if current_con > 0.8 and current_con != 1:
            logger.info(
                f'{context} intro readiness almost full phase={phase} char={char} '
                f'current_con={current_con:.2f}, wait and check again')
            char.sleep(0.05)
            next_frame = getattr(self.task, 'next_frame', None)
            if callable(next_frame):
                next_frame()
            current_con = char.get_current_con()
        ready = current_con == 1
        logger.info(
            f'{context} intro readiness phase={phase} char={char} '
            f'current_con={current_con} ready={ready}')
        return ready, current_con

    def ensure_intro_ready(self, char: BaseChar, step: TeamRotationStep, context: str):
        if not step.next_free_intro:
            return True

        ready, current_con = self._check_intro_ready(char, context, 'before-build')
        if ready:
            return True

        if not step.intro_actions:
            logger.warning(
                f'{context} intro required but current con is not full and no intro actions are configured '
                f'char={char} current_con={current_con}')
            return False

        for index, action in enumerate(step.intro_actions, start=1):
            intro_context = f'{context} intro-build {index}/{len(step.intro_actions)}'
            result = self.runner.run(char, action, context=intro_context)
            if not _action_succeeded(result):
                logger.warning(
                    f'{intro_context} action unsuccessful char={char} action={_action_label(action)} '
                    f'required={_is_required(action)} result={_short_value(result)}')
                if _is_required(action):
                    return False
            ready, current_con = self._check_intro_ready(char, context, f'after-build-{index}')
            if ready:
                return True

        logger.warning(
            f'{context} intro still not ready after build actions char={char} current_con={current_con} '
            f'actions={len(step.intro_actions)}')
        return False

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
        self.last_active_time = time.time()
        logger.info(
            f'{context} begin label={step.label or step.char_cls.__name__} '
            f'char={char} next={step.next_char_cls.__name__ if step.next_char_cls else None} '
            f'actions={len(step.actions)}')
        if not self.ensure_current_char(char):
            logger.warning(f'{context} failed to align char={char}, fallback to role axis')
            return False
        self.handle_intro(char)
        start_action_index = min(self.action_index, len(step.actions))
        if start_action_index > 0:
            if start_action_index >= len(step.actions):
                logger.warning(
                    f'{context} resume within step after actions, retry switch/advance '
                    f'label={step.label or step.char_cls.__name__}')
            else:
                logger.warning(
                    f'{context} resume within step action_index={start_action_index + 1}/{len(step.actions)} '
                    f'label={step.label or step.char_cls.__name__}')
        for index, action in enumerate(step.actions[start_action_index:], start=start_action_index):
            self.action_index = index
            try:
                result = self.runner.run(char, action, context=context)
            finally:
                self.last_active_time = time.time()
            if not _action_succeeded(result):
                logger.warning(
                    f'{context} action unsuccessful char={char} action={_action_label(action)} '
                    f'required={_is_required(action)} result={_short_value(result)}')
                if _is_required(action):
                    logger.warning(
                        f'{context} required action failed; hold current step and fallback to role axis '
                        f'startup_done={self.startup_done} startup_index={self.startup_index} '
                        f'loop_index={self.loop_index}')
                    return False
                if action.kwargs.get('stop_on_fail', False):
                    logger.warning(
                        f'{context} action failed with stop_on_fail; skip remaining actions and switch '
                        f'char={char} action={_action_label(action)} action_index={index}')
                    break
            self.action_index = index + 1

        if step.next_char_cls is not None:
            next_char = self.char(step.next_char_cls)
            if next_char is not None:
                if not self.ensure_intro_ready(char, step, context):
                    self.intro_retry_count += 1
                    self.action_index = len(step.actions)
                    limit = max(0, int(step.intro_retry_limit or 0))
                    logger.warning(
                        f'{context} hold step because required intro is not ready '
                        f'char={char} next={next_char} retry={self.intro_retry_count} '
                        f'limit={limit or "unbounded"}')
                    if limit > 0 and self.intro_retry_count >= limit:
                        logger.warning(
                            f'{context} intro retry limit exhausted; fallback to role axis '
                            f'char={char} next={next_char} retry={self.intro_retry_count}')
                        return False
                    self.last_active_time = time.time()
                    return True
                free_intro = False
                logger.info(
                    f'{context} switch request current={char} next={next_char} '
                    f'require_intro={step.next_free_intro} free_intro={free_intro}')
                self.task.switch_to_char(char, next_char, free_intro=free_intro)
            else:
                logger.warning(f'{context} missing next char {step.next_char_cls.__name__}, skip switch')
        logger.info(f'{context} end label={step.label or step.char_cls.__name__}')
        self.advance()
        self.last_active_time = time.time()
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
    if existing and existing.combat_start != combat_start and existing.still_matches():
        resume_window = _team_axis_resume_window(task)
        inactive_for = time.time() - getattr(existing, 'last_active_time', 0)
        reason = getattr(task, 'out_of_combat_reason', '')
        if resume_window > 0 and inactive_for <= resume_window and _is_transient_out_of_combat(reason):
            old_combat_start = existing.combat_start
            existing.combat_start = combat_start
            logger.warning(
                f'resumed team rotation {existing.name} after transient out-of-combat '
                f'old_combat_start={old_combat_start} new_combat_start={combat_start} '
                f'inactive_for={inactive_for:.2f}s window={resume_window}s reason={reason!r} '
                f'step={existing.step_context()} team={signature}')
            return existing
        logger.info(
            f'team rotation will reset instead of resume old={existing.name} '
            f'old_combat_start={existing.combat_start} new_combat_start={combat_start} '
            f'inactive_for={inactive_for:.2f}s window={resume_window}s reason={reason!r} team={signature}')
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
