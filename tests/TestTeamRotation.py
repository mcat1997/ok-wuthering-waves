import logging
import sys
import types
import unittest

_OK_STUBBED = False
try:
    import ok  # noqa
except ImportError:
    _OK_STUBBED = True
    ok_stub = types.ModuleType('ok')

    class _Logger:
        @staticmethod
        def get_logger(name):
            return logging.getLogger(name)

    ok_stub.Logger = _Logger
    sys.modules['ok'] = ok_stub

from src.combat.rotation import (
    AemeathDeniaChisaProfile,
    TeamRotationError,
    TeamRotationProfile,
    TeamRotationRegistry,
    TeamRotationRunner,
    TeamSignature,
)

if _OK_STUBBED:
    AutoCombatTask = None
else:
    from src.task.AutoCombatTask import AutoCombatTask

if _OK_STUBBED:
    sys.modules.pop('ok', None)


class RecordingChar:
    def __init__(self, name, index, current=False):
        self.name = name
        self.index = index
        self.is_current_char = current
        self.has_intro = False
        self.last_switch_in_time = -1
        self.actions = []

    def perform(self):
        self.actions.append(('perform', self.name))

    def is_con_full(self):
        return False

    def switch_out(self, con_full=False):
        self.actions.append(('switch_out', self.name, con_full))
        self.is_current_char = False

    def click_resonance(self, **kwargs):
        self.actions.append(('resonance', self.name, kwargs))
        return True, 0, False

    def continues_normal_attack(self, duration, interval=0.1, **kwargs):
        self.actions.append(('normal', self.name, duration))

    def click_liberation(self, **kwargs):
        self.actions.append(('liberation', self.name, kwargs))
        return True

    def send_liberation_key(self):
        self.actions.append(('send_liberation', self.name))

    def record_liberation_use(self):
        self.actions.append(('record_liberation_use', self.name))

    def liberation_available(self):
        return True

    def click_echo(self, **kwargs):
        self.actions.append(('echo', self.name, kwargs))
        return True

    def is_forte_full(self):
        return False

    def perform_forte(self):
        self.actions.append(('forte', self.name))
        return True

    def wait_intro(self, *args, **kwargs):
        self.actions.append(('wait_intro', self.name))

    def record_support_buff(self):
        self.actions.append(('support_buff', self.name))

    def record_intro_liberation(self):
        self.actions.append(('intro_liberation', self.name))

    def click(self, **kwargs):
        self.actions.append(('click', self.name, kwargs))

    def sleep(self, *args, **kwargs):
        pass

    def perform_everything(self):
        self.actions.append(('aemeath_everything', self.name))


class RotationTask:
    def __init__(self, chars):
        self.chars = chars
        self.sent_keys = []
        self.team_rotation_profile = None
        self.team_rotation_disabled = False
        self.team_rotation_fallback_reason = ''

    def get_current_char(self, raise_exception=False):
        for char in self.chars:
            if char.is_current_char:
                return char
        if raise_exception:
            raise RuntimeError('no current char')

    def perform_default_turn(self):
        self.get_current_char(raise_exception=True).perform()
        return True

    def send_key(self, key, *args, **kwargs):
        self.sent_keys.append(key)
        for char in self.chars:
            char.is_current_char = char.index == key - 1

    def wait_until(self, fun, time_out=0, raise_if_not_found=False, **kwargs):
        return fun()

    def in_team(self):
        current = self.get_current_char(raise_exception=False)
        return True, current.index if current else -1, len(self.chars)

    def _apply_intro_flags(self, current, target, has_intro):
        target.has_intro = has_intro


class BadProfile(TeamRotationProfile):
    signature = TeamSignature.of('Aemeath', 'Denia', 'Chisa')

    def __init__(self):
        self.calls = 0

    def perform_turn(self, context):
        self.calls += 1
        raise TeamRotationError('bad profile')


class AutoCombatRunTask:
    def __init__(self):
        self.config = {'Use Liberation': True}
        self.scene = self
        self.load_char_calls = 0
        self.turns = 0
        self.ended = False
        self.team_rotation_profile = None
        self.in_combat_calls = 0

    def warm_up_char_features(self):
        pass

    def in_team(self, fun):
        return fun()

    def in_team_and_world(self):
        return True

    def in_world(self):
        return True

    def in_combat(self):
        self.in_combat_calls += 1
        return self.in_combat_calls <= 2

    def load_chars(self):
        self.load_char_calls += 1
        self.team_rotation_profile = AemeathDeniaChisaProfile()
        return True

    def perform_current_turn(self):
        if self.team_rotation_profile is None:
            raise AssertionError('auto combat performed before team rotation profile refresh')
        self.turns += 1

    def combat_end(self):
        self.ended = True

    def log_error(self, *args, **kwargs):
        raise AssertionError(args)


class TestTeamRotation(unittest.TestCase):
    def make_team(self, current='Chisa'):
        return [
            RecordingChar('Aemeath', 0, current == 'Aemeath'),
            RecordingChar('Denia', 1, current == 'Denia'),
            RecordingChar('Chisa', 2, current == 'Chisa'),
        ]

    def test_signature_matches_team_regardless_of_order(self):
        signature = TeamSignature.from_chars(self.make_team())
        self.assertTrue(AemeathDeniaChisaProfile().matches(signature))

        shuffled = [self.make_team()[2], self.make_team()[0], self.make_team()[1]]
        self.assertEqual(signature, TeamSignature.from_chars(shuffled))

    def test_registry_returns_a_fresh_matching_profile(self):
        registry = TeamRotationRegistry([AemeathDeniaChisaProfile])
        first = registry.match(self.make_team())
        second = registry.match(self.make_team())

        self.assertIsInstance(first, AemeathDeniaChisaProfile)
        self.assertIsInstance(second, AemeathDeniaChisaProfile)
        self.assertIsNot(first, second)

    def test_runner_without_profile_uses_default_turn(self):
        task = RotationTask(self.make_team(current='Aemeath'))
        runner = TeamRotationRunner(task)

        self.assertTrue(runner.perform_turn())
        self.assertEqual(task.chars[0].actions, [('perform', 'Aemeath')])

    def test_profile_starts_with_chisa_axis_and_switches_to_denia(self):
        task = RotationTask(self.make_team(current='Chisa'))
        task.team_rotation_profile = AemeathDeniaChisaProfile()
        runner = TeamRotationRunner(task)

        self.assertTrue(runner.perform_turn())
        chisa_actions = [action[0] for action in task.chars[2].actions]
        self.assertIn('resonance', chisa_actions)
        self.assertIn('normal', chisa_actions)
        self.assertEqual(task.sent_keys, [2])
        self.assertTrue(task.chars[1].is_current_char)

    def test_aemeath_profile_uses_chart_step_counts(self):
        profile = AemeathDeniaChisaProfile()

        self.assertEqual(len(profile.startup_plan), 12)
        self.assertEqual(len(profile.cycle_plan), 14)
        self.assertFalse(hasattr(profile, 'startup_aemeath_entry_seconds'))
        self.assertEqual(
            [step[:2] for step in profile.startup_plan],
            [
                ('Chisa', 'E'),
                ('Denia', 'E-R-2A'),
                ('Chisa', 'R-a3'),
                ('Denia', 'a3a4'),
                ('Chisa', 'a4a5-Q-enhancedE'),
                ('Denia', '2A-enhancedE-R2'),
                ('Chisa', 'tap-a2a3-finish'),
                ('Aemeath', 'Q-a3a4-R1'),
                ('Aemeath', 'one-chain-heavy-enhancedE'),
                ('Aemeath', 'execute-a3a4-enhancedE'),
                ('Aemeath', 'fastHeavy-R2'),
                ('Aemeath', 'E-2A-E'),
            ],
        )
        self.assertEqual(
            [step[:2] for step in profile.cycle_plan],
            [
                ('Chisa', 'E-a3'),
                ('Denia', 'E'),
                ('Aemeath', 'a2a3-E'),
                ('Chisa', 'a4(a5)-(Q)'),
                ('Denia', 'R-2A'),
                ('Chisa', 'R-enhancedE'),
                ('Aemeath', 'a2a3-E'),
                ('Chisa', 'tap-a2a3-finish'),
                ('Denia', '2A-enhancedE-R2'),
                ('Aemeath', 'Q-a3a4-R1'),
                ('Aemeath', 'one-chain-heavy-enhancedE'),
                ('Aemeath', 'execute-a3a4-enhancedE'),
                ('Aemeath', 'fastHeavy-R2'),
                ('Aemeath', 'E-2A-E'),
            ],
        )

    def test_profile_normal_attack_sleeps_without_combat_check(self):
        class Task:
            def __init__(self):
                self.skip_combat_check = False
                self.clicks = 0
                self.skip_seen = []

            def click(self):
                self.clicks += 1

            def sleep(self, sec):
                self.skip_seen.append(self.skip_combat_check)

        class Char(RecordingChar):
            def __init__(self):
                super().__init__('Chisa', 2, True)
                self.task = Task()

            def sleep(self, sec, check_combat=True):
                if not check_combat:
                    self.task.skip_combat_check = True
                self.task.sleep(sec)
                self.task.skip_combat_check = False

        char = Char()

        AemeathDeniaChisaProfile()._normal(char, 0.21, 'test')

        self.assertGreaterEqual(char.task.clicks, 2)
        self.assertTrue(char.task.skip_seen)
        self.assertTrue(all(char.task.skip_seen))

    def test_chisa_r_enhanced_e_uses_nonblocking_liberation_tap(self):
        chisa = RecordingChar('Chisa', 2, True)
        chisa.task = types.SimpleNamespace(use_liberation=True, combat_start=-1)

        AemeathDeniaChisaProfile()._chisa_r_enhanced_e(chisa)
        actions = [action[0] for action in chisa.actions]

        self.assertIn('send_liberation', actions)
        self.assertIn('record_liberation_use', actions)
        self.assertIn('support_buff', actions)
        self.assertIn('resonance', actions)
        self.assertNotIn('liberation', actions)

    def test_denia_r2_uses_nonblocking_liberation_tap(self):
        denia = RecordingChar('Denia', 1, True)
        denia.task = types.SimpleNamespace(use_liberation=True, combat_start=-1)

        AemeathDeniaChisaProfile()._denia_2a_enhanced_e_r2(denia)
        actions = [action[0] for action in denia.actions]

        self.assertIn('send_liberation', actions)
        self.assertIn('record_liberation_use', actions)
        self.assertIn('resonance', actions)
        self.assertNotIn('liberation', actions)

    def test_aemeath_burst_preserves_one_chain_heavy_when_r1_fails(self):
        class AemeathChar(RecordingChar):
            def __init__(self):
                super().__init__('Aemeath', 1, True)
                self.task = types.SimpleNamespace(use_liberation=True, combat_start=-1, skip_combat_check=False)
                self.skip_seen = []

            def click_liberation(self, **kwargs):
                self.actions.append(('liberation', self.name, kwargs))
                return False

            def lib(self):
                self.actions.append(('lib', self.name))
                return False

            def liberation_available(self):
                return False

            def handle_heavy(self):
                self.skip_seen.append(self.task.skip_combat_check)
                self.actions.append(('handle_heavy', self.name))
                return True

            def has_long_action(self):
                return True

        aemeath = AemeathChar()
        profile = AemeathDeniaChisaProfile()
        profile._aemeath_q_a3a4_r1(aemeath)
        profile._aemeath_one_chain_heavy_enhanced_e(aemeath)
        actions = [action[0] for action in aemeath.actions]

        self.assertNotIn('send_liberation', actions)
        self.assertNotIn('handle_heavy', actions)
        self.assertNotIn('heavy', actions)

    def test_aemeath_r1_slot_keeps_chart_r_when_lib2_template_is_visible(self):
        class AemeathChar(RecordingChar):
            def __init__(self):
                super().__init__('Aemeath', 1, True)
                self.task = types.SimpleNamespace(use_liberation=True, combat_start=-1, skip_combat_check=False)
                self.skip_seen = []

            def lib2_available(self):
                self.actions.append(('lib2_available', self.name))
                return True

            def handle_heavy(self):
                self.skip_seen.append(self.task.skip_combat_check)
                self.actions.append(('handle_heavy', self.name))
                return True

            def has_long_action(self):
                return True

            def record_liberation(self, is_lib2):
                self.actions.append(('record_liberation', self.name, is_lib2))

            def f_break(self):
                self.actions.append(('f_break', self.name))

        aemeath = AemeathChar()
        profile = AemeathDeniaChisaProfile()
        profile._aemeath_q_a3a4_r1(aemeath)
        self.assertTrue(profile.aemeath_r1_casted)
        self.assertIn(('record_liberation', 'Aemeath', False), aemeath.actions)

        profile._aemeath_one_chain_heavy_enhanced_e(aemeath)
        actions = [action[0] for action in aemeath.actions]

        self.assertEqual(actions.count('send_liberation'), 1)
        self.assertIn('handle_heavy', actions)
        self.assertEqual(aemeath.skip_seen, [True])
        self.assertFalse(aemeath.task.skip_combat_check)
        self.assertIn('resonance', actions)
        self.assertFalse(profile.aemeath_r1_casted)

    def test_aemeath_r2_uses_detected_r2_state_directly(self):
        class AemeathChar(RecordingChar):
            def __init__(self):
                super().__init__('Aemeath', 1, True)
                self.task = types.SimpleNamespace(use_liberation=True, combat_start=-1)

            def lib2_available(self):
                self.actions.append(('lib2_available', self.name))
                return not any(action[0] == 'send_liberation' for action in self.actions)

            def lib(self):
                self.actions.append(('lib', self.name))
                return False

            def record_liberation(self, is_lib2):
                self.actions.append(('record_liberation', self.name, is_lib2))

            def f_break(self):
                self.actions.append(('f_break', self.name))

        aemeath = AemeathChar()
        ret = AemeathDeniaChisaProfile()._cast_aemeath_r2(aemeath, 'R2', max_frames=2)
        actions = [action[0] for action in aemeath.actions]

        self.assertTrue(ret)
        self.assertIn('send_liberation', actions)
        self.assertNotIn('lib', actions)
        self.assertIn(('record_liberation', 'Aemeath', True), aemeath.actions)

    def test_aemeath_r2_records_key_send_when_icon_lingers(self):
        class AemeathChar(RecordingChar):
            def __init__(self):
                super().__init__('Aemeath', 1, True)
                self.task = types.SimpleNamespace(use_liberation=True, combat_start=-1, next_frame=lambda: None)

            def lib2_available(self):
                self.actions.append(('lib2_available', self.name))
                return True

            def record_liberation(self, is_lib2):
                self.actions.append(('record_liberation', self.name, is_lib2))

            def f_break(self):
                self.actions.append(('f_break', self.name))

        aemeath = AemeathChar()
        ret = AemeathDeniaChisaProfile()._cast_aemeath_r2(aemeath, 'R2', max_frames=1)
        actions = [action[0] for action in aemeath.actions]

        self.assertTrue(ret)
        self.assertIn('send_liberation', actions)
        self.assertIn(('record_liberation', 'Aemeath', True), aemeath.actions)

    def test_aemeath_profile_allows_long_aemeath_axis(self):
        self.assertGreaterEqual(AemeathDeniaChisaProfile.max_turn_seconds, 20)

    def test_profile_switches_to_expected_char_when_current_does_not_match(self):
        task = RotationTask(self.make_team(current='Aemeath'))
        task.team_rotation_profile = AemeathDeniaChisaProfile()
        runner = TeamRotationRunner(task)

        self.assertTrue(runner.perform_turn())
        self.assertEqual(task.sent_keys, [3])
        self.assertTrue(task.chars[2].is_current_char)
        self.assertEqual(task.chars[0].actions, [('switch_out', 'Aemeath', False)])

    def test_profile_error_disables_until_combat_is_refreshed(self):
        task = RotationTask(self.make_team(current='Chisa'))
        bad_profile = BadProfile()
        task.team_rotation_profile = bad_profile
        runner = TeamRotationRunner(task)

        self.assertTrue(runner.perform_turn())
        self.assertTrue(task.team_rotation_disabled)
        self.assertEqual(task.team_rotation_fallback_reason, 'bad profile')
        self.assertEqual(task.get_current_char().actions[-1], ('perform', 'Chisa'))

        self.assertTrue(runner.perform_turn())
        self.assertEqual(bad_profile.calls, 1)

    @unittest.skipIf(AutoCombatTask is None, 'AutoCombatTask requires ok-script')
    def test_auto_combat_refreshes_team_rotation_before_turn(self):
        task = AutoCombatRunTask()

        self.assertTrue(AutoCombatTask.run(task))
        self.assertEqual(task.load_char_calls, 1)
        self.assertEqual(task.turns, 1)
        self.assertTrue(task.ended)


if __name__ == '__main__':
    unittest.main()
