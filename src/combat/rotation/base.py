import time
from dataclasses import dataclass

from ok import Logger

logger = Logger.get_logger(__name__)


class TeamRotationError(Exception):
    """Expected failure inside a team rotation profile."""


@dataclass(frozen=True)
class TeamSignature:
    names: tuple[str, ...]

    @classmethod
    def of(cls, *names):
        return cls(tuple(sorted(str(name) for name in names if name)))

    @classmethod
    def from_chars(cls, chars):
        return cls.of(*(getattr(char, 'name', None) for char in chars if char is not None))


@dataclass(frozen=True)
class TeamRotationResult:
    status: str
    reason: str = ''

    @classmethod
    def handled(cls, reason=''):
        return cls('handled', reason)

    @classmethod
    def fallback(cls, reason=''):
        return cls('fallback', reason)

    @classmethod
    def disable(cls, reason=''):
        return cls('disable', reason)

    @property
    def handled_current_turn(self):
        return self.status == 'handled'

    @property
    def should_disable(self):
        return self.status == 'disable'


class TeamRotationProfile:
    signature = TeamSignature.of()
    max_turn_seconds = 8

    @property
    def name(self):
        return self.__class__.__name__

    def matches(self, signature):
        return self.signature == signature

    def perform_turn(self, context):
        return TeamRotationResult.fallback('profile has no action')


class TeamRotationRegistry:
    def __init__(self, profiles=None):
        self._profile_classes = []
        for profile in profiles or []:
            self.register(profile)

    def register(self, profile):
        profile_class = profile if isinstance(profile, type) else profile.__class__
        if profile_class not in self._profile_classes:
            self._profile_classes.append(profile_class)

    def match(self, chars):
        signature = chars if isinstance(chars, TeamSignature) else TeamSignature.from_chars(chars)
        for profile_class in self._profile_classes:
            profile = profile_class()
            if profile.matches(signature):
                return profile
        return None


class TeamRotationContext:
    def __init__(self, task, profile):
        self.task = task
        self.profile = profile

    @property
    def current_char(self):
        return self.task.get_current_char(raise_exception=True)

    @property
    def chars(self):
        return [char for char in getattr(self.task, 'chars', []) if char is not None]

    def char(self, name):
        for char in self.chars:
            if char.name == name:
                return char
        return None

    def default_perform(self):
        self.current_char.perform()

    def normal_attack(self, duration, interval=0.1):
        self.current_char.continues_normal_attack(duration, interval=interval)

    def click_resonance(self, **kwargs):
        return self.current_char.click_resonance(**kwargs)

    def click_liberation(self, **kwargs):
        return self.current_char.click_liberation(**kwargs)

    def click_echo(self, **kwargs):
        return self.current_char.click_echo(**kwargs)

    def switch_to(self, name, has_intro=None):
        target = self.char(name)
        if target is None:
            raise TeamRotationError(f'rotation target not found: {name}')

        current = self.current_char
        if current == target:
            logger.info(f'team rotation switch already current: {self.profile.name} {name}[{target.index}]')
            return target

        if has_intro is None:
            has_intro = current.is_con_full()
        if hasattr(self.task, '_apply_intro_flags'):
            self.task._apply_intro_flags(current, target, has_intro)
        logger.info(
            f'team rotation switch request: {self.profile.name} '
            f'{current.name}[{current.index}] -> {target.name}[{target.index}] has_intro={has_intro}')

        def send_switch_key():
            if hasattr(current, 'f_break'):
                current.f_break(check_f_on_switch=True)
            self.task.send_key(target.index + 1)
            if hasattr(self.task, 'click'):
                self.task.click()

        def target_is_current():
            in_team, current_index, _ = self.task.in_team()
            return in_team and current_index == target.index

        send_switch_key()
        switched = True
        if hasattr(self.task, 'wait_until'):
            switched = self.task.wait_until(
                target_is_current,
                post_action=send_switch_key,
                time_out=getattr(self.task, 'switch_char_time_out', 1),
                raise_if_not_found=False,
            )
        if not switched or not target_is_current():
            raise TeamRotationError(f'failed to switch to rotation target: {name}')

        current.switch_out(con_full=has_intro)
        if has_intro and hasattr(self.task, 'add_freeze_duration'):
            current_time = time.time()
            self.task.add_freeze_duration(current_time, target.intro_motion_freeze_duration, -100)
            current.last_outro_time = current_time
        for char in self.chars:
            char.is_current_char = char == target
        target.last_switch_in_time = time.time()
        logger.info(f'team rotation switch success: {self.profile.name} current={target.name}[{target.index}]')
        return target


class TeamRotationRunner:
    def __init__(self, task, passthrough_exceptions=()):
        self.task = task
        self.passthrough_exceptions = passthrough_exceptions

    def perform_turn(self):
        profile = getattr(self.task, 'team_rotation_profile', None)
        if profile is None:
            logger.debug('team rotation skipped: no profile')
            return self.task.perform_default_turn()
        if getattr(self.task, 'team_rotation_disabled', False):
            logger.debug(
                f'team rotation skipped: profile disabled {profile.name} '
                f'reason={getattr(self.task, "team_rotation_fallback_reason", "")}')
            return self.task.perform_default_turn()

        context = TeamRotationContext(self.task, profile)
        start = time.time()
        try:
            result = profile.perform_turn(context)
        except self.passthrough_exceptions:
            raise
        except TeamRotationError as e:
            return self._disable_and_fallback(str(e))
        except Exception as e:
            logger.error(f'team rotation profile failed: {profile.name}', e)
            return self._disable_and_fallback(str(e))

        elapsed = time.time() - start
        if elapsed > profile.max_turn_seconds:
            return self._disable_and_fallback(f'turn timeout: {elapsed:.2f}s')

        if result.handled_current_turn:
            logger.info(f'team rotation handled: {profile.name} {result.reason}')
            return True

        reason = result.reason or 'profile fallback'
        logger.info(f'team rotation fallback: {profile.name} {reason}')
        if result.should_disable:
            self.task.team_rotation_disabled = True
            self.task.team_rotation_fallback_reason = reason
        return self.task.perform_default_turn()

    def _disable_and_fallback(self, reason):
        self.task.team_rotation_disabled = True
        self.task.team_rotation_fallback_reason = reason
        logger.warning(f'team rotation disabled: {reason}')
        return self.task.perform_default_turn()
