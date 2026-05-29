import time
import unittest
from config import config
from ok.test.TaskTestCase import TaskTestCase
from src.Labels import Labels
from src.char.BaseChar import BaseChar, CharType, SwitchPriority, get_default_buff_time
from src.char.CharFactory import _get_buff_time, _get_char_type, char_dict, char_names
from src.char.Aemeath import Aemeath
from src.char.Chisa import Chisa
from src.char.Ciaccona import Ciaccona
from src.char.Denia import Denia
from src.char.Linnai import Linnai
from src.char.Phrolova import Phrolova
from src.char.Verina import Verina
from src.team import TeamRotation, TeamRotationStep, select_team_rotation
from src.team.TeamRotation import TeamAction, TeamActionRunner
from src.team.aemeath_denia_chisa import AemeathDeniaChisaRotation
from src.task.AutoCombatTask import AutoCombatTask

config['debug'] = True


def return_true():
    return True


class BlockedChar(BaseChar):
    def get_switch_priority(self, current_char=None, has_intro=False, target_low_con=False):
        return SwitchPriority.NO


class ForcedChar(BaseChar):
    def get_switch_priority(self, current_char=None, has_intro=False, target_low_con=False):
        return SwitchPriority.MUST


class TestChar(TaskTestCase):
    task_class = AutoCombatTask
    config = config

    def test_char_type_config(self):
        class Task:
            char_config = {}

        task = Task()
        self.assertEqual(BaseChar(None, 0).char_type, CharType.MAIN_DPS)
        self.assertEqual(BaseChar(None, 0).buff_time, 0)
        self.assertEqual(BaseChar(None, 0, char_type=CharType.HEALER).buff_time,
                         get_default_buff_time(CharType.HEALER))
        self.assertEqual(BaseChar(None, 0, char_type=CharType.SUB_DPS, buff_time=11).buff_time, 11)
        self.assertEqual(char_dict[Labels.char_mortefi]['char_type'], CharType.SUB_DPS)
        self.assertEqual(char_dict[Labels.char_mortefi]['buff_time'], get_default_buff_time(CharType.SUB_DPS))
        self.assertEqual(char_dict[Labels.char_chisa]['buff_time'], 12)
        self.assertEqual(_get_char_type(task, char_dict[Labels.char_iuno]), CharType.SUB_DPS)
        self.assertEqual(_get_buff_time(task, char_dict[Labels.char_iuno]), get_default_buff_time(CharType.SUB_DPS))
        self.assertEqual(_get_buff_time(task, dict(char_dict[Labels.char_mortefi], buff_time=12)), 12)

        task.char_config = {'Iuno C6': True}
        self.assertEqual(_get_char_type(task, char_dict[Labels.char_iuno]), CharType.MAIN_DPS)
        self.assertEqual(_get_buff_time(task, char_dict[Labels.char_iuno]), 0)

    def test_auto_combat_warms_char_features_only_once(self):
        task = AutoCombatTask.__new__(AutoCombatTask)
        task.char_features_warmed_up = False
        loaded = []
        task.get_feature_by_name = loaded.append

        task.warm_up_char_features()
        task.warm_up_char_features()

        self.assertTrue(task.char_features_warmed_up)
        self.assertEqual(loaded, list(char_names))

    def test_switch_priority_rules(self):
        class Task:
            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                if start < 0:
                    return 10000
                return time.time() - start

        task = Task()
        combat = AutoCombatTask.__new__(AutoCombatTask)
        current = BaseChar(task, 0, char_type=CharType.MAIN_DPS)
        healer = BaseChar(task, 1, char_type=CharType.HEALER)
        sub_dps = BaseChar(task, 2, char_type=CharType.SUB_DPS)
        main_dps = BaseChar(task, 3, char_type=CharType.MAIN_DPS)
        combat.chars = [current, healer, sub_dps, main_dps]

        self.assertEqual(combat._choose_switch_target(current, False), healer)

        healer.last_buff_time = time.time()
        self.assertEqual(combat._choose_switch_target(current, False), sub_dps)

        sub_dps.last_buff_time = time.time()
        healer.last_buff_time = time.time() - 10
        self.assertEqual(combat._choose_switch_target(current, False), healer)

        combat.chars = [current, healer, sub_dps]
        healer.last_switch_in_time = 1
        sub_dps.last_switch_in_time = 2
        healer.last_buff_time = -1
        self.assertEqual(combat._choose_switch_target(current, False), healer)

        combat.chars = [current, healer, sub_dps, main_dps]
        current.set_char_type(CharType.SUB_DPS)
        self.assertEqual(combat._choose_switch_target(current, False), healer)
        self.assertEqual(combat._choose_switch_target(current, True), main_dps)

        current.last_perform = time.time()
        healer.last_buff_time = -1
        self.assertEqual(combat._choose_switch_target(current, False), healer)
        current.last_perform = 0

        current.set_char_type(CharType.HEALER)
        self.assertEqual(combat._choose_switch_target(current, False), healer)

        current.last_perform = time.time()
        healer.last_buff_time = time.time()
        sub_dps.last_buff_time = -1
        self.assertEqual(combat._choose_switch_target(current, False), sub_dps)
        self.assertEqual(combat._choose_switch_target(current, True), main_dps)
        current.last_perform = 0

        forced = ForcedChar(task, 4, char_type=CharType.MAIN_DPS)
        task.chars = [current, healer, sub_dps, main_dps, forced]
        self.assertTrue(current.need_fast_perform())
        task.chars = [current, healer, sub_dps, main_dps]
        self.assertFalse(current.need_fast_perform())

        current.set_char_type(CharType.MAIN_DPS)
        healer.last_buff_time = -1
        self.assertEqual(combat._choose_switch_target(current, True), main_dps)

        healer.last_buff_time = time.time()
        sub_dps.last_buff_time = -1
        self.assertEqual(combat._choose_switch_target(current, True), main_dps)

        combat.chars = [current, healer, sub_dps]
        self.assertEqual(combat._choose_switch_target(current, True), sub_dps)
        combat.chars = [current, healer, sub_dps, main_dps]

        combat._apply_intro_flags(sub_dps, current, True)
        self.assertTrue(current.has_intro)
        self.assertTrue(current.has_sub_dps_intro)

        combat._apply_intro_flags(healer, current, True)
        self.assertTrue(current.has_intro)
        self.assertFalse(current.has_sub_dps_intro)

    def test_chisa_support_intro_records_buff_and_switches_immediately(self):
        class Task:
            char_config = {'Chisa DPS': False}

        class TrackingChisa(Chisa):
            def __init__(self, task):
                super().__init__(task, 0)
                self.actions = []

            def click_echo(self, **kwargs):
                self.actions.append(('echo', kwargs))

            def click_liberation(self):
                self.actions.append(('liberation', {}))
                return True

            def click_resonance(self, **kwargs):
                self.actions.append(('resonance', kwargs))

            def switch_next_char(self):
                self.actions.append(('switch', {}))

        chisa = TrackingChisa(Task())
        chisa.has_intro = True
        chisa.do_perform()

        self.assertGreater(chisa.last_buff_time, 0)
        self.assertEqual(chisa.actions, [('echo', {'time_out': 0}), ('switch', {})])

    def test_verina_heavy_attack_has_eight_second_interval(self):
        class Task:
            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                return time.time() - start

        class TrackingVerina(Verina):
            def __init__(self, task):
                super().__init__(task, 0)
                self.heavy_count = 0
                self.click_count = 0

            def is_con_full(self):
                return False

            def click_liberation(self, **kwargs):
                return False

            def click_resonance(self, **kwargs):
                return False, None

            def click_echo(self, **kwargs):
                return False

            def is_mouse_forte_full(self):
                return True

            def heavy_attack(self, duration=0.6):
                self.heavy_count += 1

            def click(self):
                self.click_count += 1

        verina = TrackingVerina(Task())
        self.assertFalse(verina.do_cycle())
        self.assertEqual(verina.heavy_count, 1)

        self.assertTrue(verina.do_cycle())
        self.assertEqual(verina.heavy_count, 1)
        self.assertEqual(verina.click_count, 1)

        verina.last_heavy = time.time() - verina.HEAVY_ATTACK_INTERVAL
        self.assertFalse(verina.do_cycle())
        self.assertEqual(verina.heavy_count, 2)

    def test_chisa_support_liberation_records_buff_without_dps_sequence(self):
        class Task:
            char_config = {'Chisa DPS': False}

        class TrackingChisa(Chisa):
            def __init__(self, task):
                super().__init__(task, 0)
                self.actions = []

            def flying(self):
                return False

            def click_echo(self, **kwargs):
                self.actions.append(('echo', kwargs))

            def click_liberation(self):
                self.actions.append(('liberation', {}))
                return True

            def click_resonance(self, **kwargs):
                self.actions.append(('resonance', kwargs))

            def switch_next_char(self):
                self.actions.append(('switch', {}))

        chisa = TrackingChisa(Task())
        chisa.do_perform()

        self.assertGreater(chisa.last_buff_time, 0)
        self.assertEqual(chisa.actions, [
            ('echo', {'time_out': 0}),
            ('liberation', {}),
            ('switch', {}),
        ])

    def test_chisa_support_outro_does_not_invent_skill_buff(self):
        class Task:
            char_config = {'Chisa DPS': False}

        chisa = Chisa(Task(), 0, char_type=CharType.HEALER, buff_time=12)
        chisa.switch_out(con_full=True)
        self.assertEqual(chisa.last_buff_time, -1)

        chisa.record_support_buff()
        buff_time = chisa.last_buff_time
        chisa.switch_out(con_full=True)
        self.assertEqual(chisa.last_buff_time, buff_time)

    def test_chisa_dps_config_keeps_dps_rotation(self):
        class Task:
            char_config = {'Chisa DPS': True}

        class TrackingChisa(Chisa):
            def __init__(self, task):
                super().__init__(task, 0)
                self.called = False

            def do_dps_perform(self):
                self.called = True

        chisa = TrackingChisa(Task())
        chisa.do_perform()
        self.assertTrue(chisa.called)

    def test_aemeath_stored_intro_unlocks_lib1_within_fourteen_seconds_and_is_consumed(self):
        class Task:
            combat_start = time.time()

            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                return time.time() - start

            def find_one(self, template, threshold=None):
                return False

        class TrackingAemeath(Aemeath):
            def click_liberation(self, **kwargs):
                return True

            def f_break(self):
                pass

        aemeath = TrackingAemeath(Task(), 0)
        aemeath.has_intro = True
        aemeath.record_intro_liberation()
        self.assertTrue(aemeath.lib())
        self.assertEqual(aemeath.intro_liberation_time, -1)

        expired = TrackingAemeath(Task(), 0)
        expired.intro_liberation_time = time.time() - expired.INTRO_LIBERATION_DELAY - 0.1
        self.assertFalse(expired.lib())

        aemeath.last_liber = time.time() - aemeath.LIBERATION_FORCE_DURATION
        self.assertTrue(aemeath.lib())

    def test_aemeath_force_liberation_starts_at_combat_entry_and_lib2_bypasses_cooldown(self):
        class Task:
            def __init__(self):
                self.combat_start = time.time()
                self.lib2 = False

            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                return time.time() - start

            def find_one(self, template, threshold=None):
                return self.lib2 and template == 'aemeath_lib2'

        class TrackingAemeath(Aemeath):
            def click_liberation(self, **kwargs):
                return True

            def f_break(self):
                pass

        task = Task()
        aemeath = TrackingAemeath(task, 0)
        task.combat_start = time.time() - aemeath.LIBERATION_FORCE_DURATION + 0.1
        self.assertFalse(aemeath.lib())

        task.combat_start = time.time() - aemeath.LIBERATION_FORCE_DURATION
        self.assertTrue(aemeath.lib())

        aemeath.pending_lib2 = True
        task.lib2 = True
        self.assertTrue(aemeath.lib())
        self.assertFalse(aemeath.pending_lib2)

    def test_aemeath_heavy_prepares_lib2_only_when_liberation_cooldown_is_ready(self):
        class Task:
            def __init__(self):
                self.lib2 = False

            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                return time.time() - start

            def find_one(self, template, threshold=None):
                return self.lib2 and template == 'aemeath_lib2'

        class TrackingAemeath(Aemeath):
            def has_long_action(self):
                return True

            def heavy_wait_highlight_down(self):
                return True

            def click_liberation(self, **kwargs):
                return True

            def f_break(self):
                pass

        task = Task()
        aemeath = TrackingAemeath(task, 0)
        self.assertTrue(aemeath.handle_heavy())
        self.assertFalse(aemeath.pending_lib2)

        aemeath.last_liber = time.time()
        self.assertTrue(aemeath.handle_heavy())
        self.assertFalse(aemeath.pending_lib2)

        aemeath.last_liber = time.time() - aemeath.LIBERATION_COOLDOWN
        self.assertTrue(aemeath.handle_heavy())
        self.assertTrue(aemeath.pending_lib2)

        aemeath.last_enhance_e = time.time() - 13
        self.assertTrue(aemeath.should_wait_for_enhance_e())
        aemeath.last_liber = time.time()
        task.lib2 = True
        self.assertTrue(aemeath.lib())
        self.assertFalse(aemeath.pending_lib2)
        self.assertFalse(aemeath.should_wait_for_enhance_e())

    def test_aemeath_switch_priority_and_wait_near_lib2_cooldown(self):
        class Task:
            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                return time.time() - start

        aemeath = Aemeath(Task(), 0)
        self.assertFalse(aemeath.should_wait_for_lib2())
        self.assertEqual(aemeath.get_switch_priority(), SwitchPriority.NORMAL)

        aemeath.last_liber = time.time() - (
                aemeath.LIBERATION_COOLDOWN - aemeath.LIB2_PREPARE_WINDOW - 0.1)
        self.assertFalse(aemeath.should_wait_for_lib2())
        self.assertEqual(aemeath.get_switch_priority(), SwitchPriority.NORMAL)

        aemeath.last_liber = time.time() - (aemeath.LIBERATION_COOLDOWN - aemeath.LIB2_PREPARE_WINDOW + 0.1)
        self.assertTrue(aemeath.should_wait_for_lib2())
        self.assertEqual(aemeath.get_switch_priority(), SwitchPriority.MUST)

        aemeath.record_heavy_liberation()
        aemeath.last_liber = time.time()
        self.assertEqual(aemeath.get_switch_priority(), SwitchPriority.MUST)

        class NoLoopAemeath(Aemeath):
            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                return 100

        waiting = NoLoopAemeath(Task(), 0)
        waiting.last_liber = time.time()
        waiting.perform_everything()
        self.assertTrue(waiting.should_wait)

        ordinary = NoLoopAemeath(Task(), 0)
        ordinary.should_wait_for_enhance_e = lambda: False
        ordinary.perform_everything()
        self.assertFalse(ordinary.should_wait)

        overdue = NoLoopAemeath(Task(), 0)
        overdue.should_wait_for_enhance_e = lambda: True
        overdue.perform_everything()
        self.assertTrue(overdue.should_wait)

    def test_aemeath_initial_lib2_cooldown_starts_at_combat_entry(self):
        class Task:
            def __init__(self):
                self.combat_start = time.time()

            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                return time.time() - start

        task = Task()
        aemeath = Aemeath(task, 0)
        self.assertGreater(aemeath.lib2_cooldown_left(), aemeath.LIB2_PREPARE_WINDOW)
        self.assertFalse(aemeath.should_wait_for_lib2())
        self.assertEqual(aemeath.get_switch_priority(), SwitchPriority.NORMAL)

        task.combat_start = time.time() - (
                aemeath.LIBERATION_COOLDOWN - aemeath.LIB2_PREPARE_WINDOW + 0.1)
        self.assertTrue(aemeath.should_wait_for_lib2())
        self.assertEqual(aemeath.get_switch_priority(), SwitchPriority.MUST)

    def test_aemeath_recent_stored_intro_attempts_lib1_before_enhance_e(self):
        class Task:
            def find_one(self, template, threshold=None):
                return template == 'aemeath_e1'

        class TrackingAemeath(Aemeath):
            def __init__(self, task):
                super().__init__(task, 0)
                self.actions = []
                self.done = False

            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                return 100 if self.done else time.time() - start

            def click_liberation(self, **kwargs):
                self.actions.append('lib1')
                return True

            def handle_heavy(self):
                return False

            def cycle_start(self):
                pass

            def cycle_sleep(self):
                self.done = True

            def f_break(self):
                pass

        aemeath = TrackingAemeath(Task())
        aemeath.intro_liberation_time = time.time() - aemeath.INTRO_LIBERATION_DELAY + 0.1
        aemeath.perform_everything()
        self.assertEqual(aemeath.actions, ['lib1'])
        self.assertEqual(aemeath.intro_liberation_time, -1)

    def test_switch_priority_hooks(self):
        class Task:
            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                if start < 0:
                    return 10000
                return time.time() - start

        task = Task()
        combat = AutoCombatTask.__new__(AutoCombatTask)
        current = BaseChar(task, 0, char_type=CharType.MAIN_DPS)
        healer = BlockedChar(task, 1, char_type=CharType.HEALER)
        sub_dps = BaseChar(task, 2, char_type=CharType.SUB_DPS)
        forced = ForcedChar(task, 3, char_type=CharType.SUB_DPS)
        combat.chars = [current, healer, sub_dps, forced]

        self.assertEqual(current.get_switch_priority(), SwitchPriority.NORMAL)
        self.assertEqual(combat._choose_switch_target(current, False), forced)

        forced.last_switch_time = time.time()
        self.assertEqual(combat._choose_switch_target(current, False), forced)
        forced.last_switch_time = -1

        combat.chars = [current, healer, sub_dps]
        self.assertEqual(combat._choose_switch_target(current, False), sub_dps)

        sub_dps = BlockedChar(task, 2, char_type=CharType.SUB_DPS)
        combat.chars = [current, healer, sub_dps]
        self.assertEqual(combat._choose_switch_target(current, False), current)

        main_dps = BaseChar(task, 4, char_type=CharType.MAIN_DPS)
        combat.chars = [current, main_dps, forced]
        self.assertEqual(combat._choose_switch_target(current, True), forced)

        blocked_main_dps = BlockedChar(task, 4, char_type=CharType.MAIN_DPS)
        allowed_sub_dps = BaseChar(task, 2, char_type=CharType.SUB_DPS)
        combat.chars = [current, blocked_main_dps, allowed_sub_dps]
        self.assertEqual(combat._choose_switch_target(current, True), allowed_sub_dps)

    def test_intro_refresh_reselects_must_target_before_switch_key_is_sent(self):
        class Task:
            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                if start < 0:
                    return 10000
                return time.time() - start

            def get_current_con(self):
                return 0

            def is_con_full(self):
                return True

        class IntroBlockedChar(BaseChar):
            def get_switch_priority(self, current_char=None, has_intro=False, target_low_con=False):
                return SwitchPriority.NO if has_intro else SwitchPriority.NORMAL

        class IntroForcedChar(BaseChar):
            def get_switch_priority(self, current_char=None, has_intro=False, target_low_con=False):
                return SwitchPriority.MUST if has_intro else SwitchPriority.NORMAL

        task = Task()
        combat = AutoCombatTask.__new__(AutoCombatTask)
        current = BaseChar(task, 0, char_type=CharType.MAIN_DPS)
        blocked = IntroBlockedChar(task, 1, char_type=CharType.HEALER)
        forced = IntroForcedChar(task, 2, char_type=CharType.MAIN_DPS)
        combat.chars = [current, blocked, forced]
        actions = []
        combat.sent_keys = []
        combat.in_liberation = False
        combat.update_lib_portrait_icon = lambda: None
        combat.check_combat = lambda: None
        combat.log_debug = lambda *args, **kwargs: None
        combat.click = lambda: None
        combat.sleep = lambda *args, **kwargs: None
        combat.add_freeze_duration = lambda *args, **kwargs: None
        current.f_break = lambda **kwargs: actions.append('f_break')

        def send_key(key):
            actions.append('switch_key')
            combat.sent_keys.append(key)

        combat.send_key = send_key
        combat.in_team = lambda: (True, combat.sent_keys[-1] - 1 if combat.sent_keys else current.index, 3)

        combat.switch_next_char(current)

        self.assertEqual(combat.sent_keys, [forced.index + 1])
        self.assertEqual(actions, ['f_break', 'switch_key'])
        self.assertTrue(forced.has_intro)
        self.assertGreater(current.last_outro_time, 0)

    def test_intro_refresh_does_not_switch_to_newly_blocked_only_target(self):
        class Task:
            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                if start < 0:
                    return 10000
                return time.time() - start

            def get_current_con(self):
                return 0

            def is_con_full(self):
                return True

        class IntroBlockedChar(BaseChar):
            def get_switch_priority(self, current_char=None, has_intro=False, target_low_con=False):
                return SwitchPriority.NO if has_intro else SwitchPriority.NORMAL

        task = Task()
        combat = AutoCombatTask.__new__(AutoCombatTask)
        current = BaseChar(task, 0, char_type=CharType.MAIN_DPS)
        blocked = IntroBlockedChar(task, 1, char_type=CharType.HEALER)
        combat.chars = [current, blocked]
        combat.sent_keys = []
        combat.update_lib_portrait_icon = lambda: None
        combat.check_combat = lambda: None
        combat.in_team = lambda: (True, current.index, 2)
        combat.send_key = lambda key: combat.sent_keys.append(key)
        combat.sleep = lambda *args, **kwargs: None
        current.f_break = lambda **kwargs: None
        current.continues_normal_attack = lambda *args, **kwargs: None

        combat.switch_next_char(current)

        self.assertEqual(combat.sent_keys, [])

    def test_non_intro_switch_breaks_after_success_before_switch_time_is_recorded(self):
        class Task:
            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                if start < 0:
                    return 10000
                return time.time() - start

            def get_current_con(self):
                return 0

            def is_con_full(self):
                return False

        task = Task()
        combat = AutoCombatTask.__new__(AutoCombatTask)
        current = BaseChar(task, 0, char_type=CharType.MAIN_DPS)
        target = BaseChar(task, 1, char_type=CharType.HEALER)
        combat.chars = [current, target]
        actions = []
        switched = []
        f_break_time = []
        combat.in_liberation = False
        combat.update_lib_portrait_icon = lambda: None
        combat.check_combat = lambda: None
        combat.log_debug = lambda *args, **kwargs: None
        combat.click = lambda: None
        combat.sleep = lambda *args, **kwargs: None

        def f_break(**kwargs):
            actions.append('f_break')
            f_break_time.append(time.time())

        def send_key(key):
            actions.append('switch_key')
            switched.append(key)

        current.f_break = f_break
        combat.send_key = send_key
        combat.in_team = lambda: (True, target.index if switched else current.index, 2)

        combat.switch_next_char(current)

        self.assertEqual(switched, [target.index + 1])
        self.assertEqual(actions, ['switch_key', 'f_break'])
        self.assertGreaterEqual(current.last_switch_time, f_break_time[0])

    def test_non_main_char_can_chain_to_an_unbuffed_other_buffer(self):
        class Task:
            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                if start < 0:
                    return 10000
                return time.time() - start

        task = Task()
        combat = AutoCombatTask.__new__(AutoCombatTask)
        main_dps = BaseChar(task, 0, char_type=CharType.MAIN_DPS)
        healer = BaseChar(task, 1, char_type=CharType.HEALER)
        sub_dps = BaseChar(task, 2, char_type=CharType.SUB_DPS)
        combat.chars = [main_dps, healer, sub_dps]

        self.assertEqual(combat._choose_switch_target(healer, False), sub_dps)
        self.assertEqual(combat._choose_switch_target(healer, True), main_dps)
        self.assertEqual(combat._choose_switch_target(sub_dps, False), healer)
        self.assertEqual(combat._choose_switch_target(sub_dps, True), main_dps)

        healer.last_buff_time = time.time()
        self.assertEqual(combat._choose_switch_target(healer, False), sub_dps)
        self.assertEqual(combat._choose_switch_target(sub_dps, False), main_dps)

    def test_non_intro_current_action_time_does_not_override_buff_rotation(self):
        class Task:
            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                if start < 0:
                    return 10000
                return time.time() - start

        task = Task()
        combat = AutoCombatTask.__new__(AutoCombatTask)
        main_dps = BaseChar(task, 0, char_type=CharType.MAIN_DPS)
        healer = BaseChar(task, 1, char_type=CharType.HEALER)
        sub_dps = BaseChar(task, 2, char_type=CharType.SUB_DPS)
        combat.chars = [main_dps, healer, sub_dps]

        sub_dps.last_perform = time.time()
        healer.last_buff_time = time.time()
        self.assertEqual(combat._choose_switch_target(sub_dps, False), main_dps)

    def test_main_dps_prefers_lowest_buff_remaining_eligible_buffer(self):
        class Task:
            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                if start < 0:
                    return 10000
                return time.time() - start

        task = Task()
        combat = AutoCombatTask.__new__(AutoCombatTask)
        main_dps = BaseChar(task, 0, char_type=CharType.MAIN_DPS)
        healer = BaseChar(task, 1, char_type=CharType.HEALER)
        sub_dps = BaseChar(task, 2, char_type=CharType.SUB_DPS)
        combat.chars = [main_dps, healer, sub_dps]

        healer.last_buff_time = time.time() - 15
        sub_dps.last_buff_time = time.time() - 1
        self.assertEqual(combat._choose_switch_target(main_dps, False), healer)

        healer.last_buff_time = time.time()
        sub_dps.last_buff_time = -1
        self.assertEqual(combat._choose_switch_target(main_dps, True), sub_dps)

        sub_dps.last_switch_time = time.time()
        self.assertEqual(combat._choose_switch_target(main_dps, False), healer)

    def test_non_main_chain_does_not_target_char_in_switch_cd(self):
        class Task:
            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                if start < 0:
                    return 10000
                return time.time() - start

        task = Task()
        combat = AutoCombatTask.__new__(AutoCombatTask)
        main_dps = BaseChar(task, 0, char_type=CharType.MAIN_DPS)
        healer = BaseChar(task, 1, char_type=CharType.HEALER)
        sub_dps = BaseChar(task, 2, char_type=CharType.SUB_DPS)
        combat.chars = [main_dps, healer, sub_dps]

        sub_dps.last_switch_time = time.time()
        self.assertEqual(combat._choose_switch_target(healer, False), main_dps)

    def test_ciaccona_can_switch_after_liberation_when_only_target_has_switch_cd(self):
        class Task:
            name = None

            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                if start < 0:
                    return 10000
                return time.time() - start

        task = Task()
        combat = AutoCombatTask.__new__(AutoCombatTask)
        ciaccona = Ciaccona(task, 0, char_type=CharType.SUB_DPS)
        main_dps = BaseChar(task, 1, char_type=CharType.MAIN_DPS)
        combat.chars = [ciaccona, main_dps]

        ciaccona.in_liberation = True
        ciaccona.last_liberation = time.time()
        main_dps.last_switch_time = time.time()
        self.assertEqual(combat._choose_switch_target(ciaccona, False), main_dps)

    def test_intro_switches_to_main_dps_ignoring_target_switch_cd(self):
        class Task:
            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                if start < 0:
                    return 10000
                return time.time() - start

        task = Task()
        combat = AutoCombatTask.__new__(AutoCombatTask)
        healer = BaseChar(task, 0, char_type=CharType.HEALER)
        sub_dps = BaseChar(task, 1, char_type=CharType.SUB_DPS)
        main_dps = BaseChar(task, 2, char_type=CharType.MAIN_DPS)
        combat.chars = [healer, sub_dps, main_dps]

        main_dps.last_switch_time = time.time()
        self.assertEqual(combat._choose_switch_target(healer, False), sub_dps)
        self.assertEqual(combat._choose_switch_target(healer, True), main_dps)

    def test_intro_switch_target_order_and_blocked_targets_are_respected(self):
        class Task:
            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                if start < 0:
                    return 10000
                return time.time() - start

        task = Task()
        combat = AutoCombatTask.__new__(AutoCombatTask)
        current = BaseChar(task, 0, char_type=CharType.HEALER)
        healer = BaseChar(task, 1, char_type=CharType.HEALER)
        sub_dps = BaseChar(task, 2, char_type=CharType.SUB_DPS)
        main_dps = BaseChar(task, 3, char_type=CharType.MAIN_DPS)
        forced = ForcedChar(task, 4, char_type=CharType.HEALER)

        for char in (healer, sub_dps, main_dps, forced):
            char.last_switch_time = time.time()
        combat.chars = [current, healer, sub_dps, main_dps, forced]
        self.assertEqual(combat._choose_switch_target(current, True), forced)

        combat.chars = [current, healer, sub_dps, main_dps]
        self.assertEqual(combat._choose_switch_target(current, True), main_dps)

        blocked_main_dps = BlockedChar(task, 3, char_type=CharType.MAIN_DPS)
        combat.chars = [current, healer, sub_dps, blocked_main_dps]
        self.assertEqual(combat._choose_switch_target(current, True), sub_dps)

        blocked_sub_dps = BlockedChar(task, 2, char_type=CharType.SUB_DPS)
        combat.chars = [current, healer, blocked_sub_dps, blocked_main_dps]
        self.assertEqual(combat._choose_switch_target(current, True), healer)

        blocked_healer = BlockedChar(task, 1, char_type=CharType.HEALER)
        combat.chars = [current, blocked_healer, blocked_sub_dps, blocked_main_dps]
        self.assertEqual(combat._choose_switch_target(current, True), current)

    def test_priority_hooks_for_ciaccona_and_phrolova(self):
        class Task:
            name = None

            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                if start < 0:
                    return 10000
                return time.time() - start

        task = Task()
        current = BaseChar(task, 0, char_name=Labels.char_cantarella)

        ciaccona = Ciaccona(task, 1)
        ciaccona.attribute = 2
        ciaccona.in_liberation = True
        ciaccona.last_liberation = time.time() - 5
        self.assertEqual(ciaccona.get_switch_priority(current_char=current, has_intro=False), SwitchPriority.NO)

        phrolova = Phrolova(task, 2)
        phrolova.last_liberation = time.time() - 5
        self.assertEqual(phrolova.get_switch_priority(current_char=current, has_intro=False), SwitchPriority.NO)

        phrolova.last_liberation = time.time() - 15
        self.assertEqual(phrolova.get_switch_priority(current_char=current, has_intro=True), SwitchPriority.MUST)
        self.assertEqual(phrolova.get_switch_priority(current_char=current, has_intro=False), SwitchPriority.NO)

        phrolova.last_liberation = time.time() - 25
        self.assertEqual(phrolova.get_switch_priority(current_char=current, has_intro=True), SwitchPriority.MUST)

    def test_linnai_waits_after_resonance_kick(self):
        class Task:
            def wait_until(self, condition, post_action=None, time_out=0, **kwargs):
                return condition()

            def jump(self):
                pass

        class TestLinnai(Linnai):
            def __init__(self):
                super().__init__(Task(), 0)
                self.actions = []
                self.resonance_clicks = 0

            def check_res(self):
                return True

            def is_color_full(self):
                return True

            def is_forte_full(self):
                return False

            def is_con_full(self):
                return False

            def click_resonance(self, **kwargs):
                self.resonance_clicks += 1
                return True, 0, False

            def click_liberation(self, **kwargs):
                return False

            def click(self, *args, **kwargs):
                pass

            def sleep(self, sec, check_combat=True):
                self.actions.append(('sleep', sec))

            def wait_down(self, click=True):
                self.actions.append(('wait_down', click))

        linnai = TestLinnai()
        self.assertTrue(linnai.perform_under_intro())
        self.assertEqual(linnai.resonance_clicks, 2)
        self.assertEqual(linnai.actions, [('sleep', 0.3), ('wait_down', True),
                                          ('sleep', 0.3), ('wait_down', True)])

    def test_intro_does_not_switch_to_phrolova_during_liberation_lock(self):
        class Task:
            name = None

            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                if start < 0:
                    return 10000
                return time.time() - start

        task = Task()
        combat = AutoCombatTask.__new__(AutoCombatTask)
        current = BaseChar(task, 0, char_name='char_shorekeeper', char_type=CharType.HEALER)
        phrolova = Phrolova(task, 1, char_type=CharType.MAIN_DPS)
        phrolova.last_liberation = time.time() - 5
        combat.chars = [current, phrolova]

        self.assertEqual(phrolova.get_switch_priority(current_char=current, has_intro=True), SwitchPriority.NO)
        self.assertEqual(combat._choose_switch_target(current, True), current)

    def test_switch_to_char_uses_explicit_target(self):
        class Task:
            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                if start < 0:
                    return 10000
                return time.time() - start

            def get_current_con(self):
                return 0

            def is_con_full(self):
                return False

        task = Task()
        combat = AutoCombatTask.__new__(AutoCombatTask)
        current = BaseChar(task, 0, char_type=CharType.MAIN_DPS)
        default_target = BaseChar(task, 1, char_type=CharType.HEALER)
        explicit_target = BaseChar(task, 2, char_type=CharType.SUB_DPS)
        combat.chars = [current, default_target, explicit_target]
        combat.sent_keys = []
        combat.in_liberation = False
        combat.update_lib_portrait_icon = lambda: None
        combat.check_combat = lambda: None
        combat.log_debug = lambda *args, **kwargs: None
        combat.click = lambda: None
        combat.sleep = lambda *args, **kwargs: None
        combat.add_freeze_duration = lambda *args, **kwargs: None
        current.f_break = lambda **kwargs: None
        combat.send_key = lambda key: combat.sent_keys.append(key)
        combat.in_team = lambda: (True, combat.sent_keys[-1] - 1 if combat.sent_keys else current.index, 3)

        combat.switch_to_char(current, explicit_target, free_intro=True)

        self.assertEqual(combat.sent_keys, [explicit_target.index + 1])
        self.assertTrue(explicit_target.has_intro)
        self.assertFalse(default_target.is_current_char)
        self.assertTrue(explicit_target.is_current_char)

    def test_select_team_rotation_matches_aemeath_denia_chisa_and_resets_per_combat(self):
        class Task:
            def __init__(self):
                self.config = {'Use Team Axis': True}
                self.char_config = {}
                self.combat_start = time.time()
                self.chars = [
                    Aemeath(self, 0),
                    Denia(self, 1),
                    Chisa(self, 2),
                ]

            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                if start < 0:
                    return 10000
                return time.time() - start

            def find_one(self, *args, **kwargs):
                return False

        task = Task()
        rotation = select_team_rotation(task)
        self.assertIsInstance(rotation, AemeathDeniaChisaRotation)
        self.assertIs(select_team_rotation(task), rotation)

        task.combat_start += 1
        self.assertIsNot(select_team_rotation(task), rotation)

        task.config['Use Team Axis'] = False
        self.assertIsNone(select_team_rotation(task))

    def test_select_team_rotation_resumes_after_transient_target_loss(self):
        class Task:
            def __init__(self):
                self.config = {'Use Team Axis': True, 'Team Axis Resume Window': 12}
                self.char_config = {}
                self.combat_start = time.time()
                self.out_of_combat_reason = ''
                self.chars = [
                    Aemeath(self, 0),
                    Denia(self, 1),
                    Chisa(self, 2),
                ]

            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                if start < 0:
                    return 10000
                return time.time() - start

            def find_one(self, *args, **kwargs):
                return False

        task = Task()
        rotation = select_team_rotation(task)
        rotation.startup_index = 6
        rotation.last_active_time = time.time() - 2

        task.out_of_combat_reason = 'target enemy failed'
        task.combat_start += 5

        self.assertIs(select_team_rotation(task), rotation)
        self.assertEqual(rotation.startup_index, 6)
        self.assertEqual(rotation.combat_start, task.combat_start)

    def test_select_team_rotation_does_not_resume_after_non_transient_end(self):
        class Task:
            def __init__(self):
                self.config = {'Use Team Axis': True, 'Team Axis Resume Window': 12}
                self.char_config = {}
                self.combat_start = time.time()
                self.out_of_combat_reason = 'end condition reached'
                self.chars = [
                    Aemeath(self, 0),
                    Denia(self, 1),
                    Chisa(self, 2),
                ]

            def time_elapsed_accounting_for_freeze(self, start, intro_motion_freeze=False):
                if start < 0:
                    return 10000
                return time.time() - start

            def find_one(self, *args, **kwargs):
                return False

        task = Task()
        rotation = select_team_rotation(task)
        rotation.last_active_time = time.time() - 2
        task.combat_start += 5

        self.assertIsNot(select_team_rotation(task), rotation)

    def test_aemeath_denia_chisa_loop_follows_tutorial_switch_order(self):
        self.assertEqual(
            [step.char_cls for step in AemeathDeniaChisaRotation.loop_steps],
            [Chisa, Denia, Aemeath, Chisa, Denia, Chisa, Aemeath, Chisa, Denia, Aemeath],
        )
        self.assertEqual(
            [step.next_char_cls for step in AemeathDeniaChisaRotation.loop_steps],
            [Denia, Aemeath, Chisa, Denia, Chisa, Aemeath, Chisa, Denia, Aemeath, Chisa],
        )

    def test_team_rotation_runs_one_step_and_switches_fixed_target(self):
        class First(BaseChar):
            pass

        class Second(BaseChar):
            pass

        class Rotation(TeamRotation):
            required_char_classes = (First, Second)
            startup_steps = (
                TeamRotationStep(
                    First,
                    (TeamAction(name='wait', duration=0),),
                    next_char_cls=Second,
                    next_free_intro=True,
                    label='first',
                ),
            )
            loop_steps = (
                TeamRotationStep(
                    Second,
                    (TeamAction(name='wait', duration=0),),
                    next_char_cls=First,
                    label='second',
                ),
            )

        class Task:
            config = {'Use Team Axis': True}

            def __init__(self):
                self.skip_combat_check = False
                self.combat_start = time.time()
                self.chars = [First(self, 0), Second(self, 1)]
                self.chars[0].is_current_char = True
                self.switches = []

            def sleep(self, *args, **kwargs):
                pass

            def get_current_char(self, raise_exception=False):
                for char in self.chars:
                    if char.is_current_char:
                        return char
                return None

            def switch_to_char(self, current, target, free_intro=False):
                self.switches.append((current, target, free_intro))
                current.is_current_char = False
                target.has_intro = free_intro
                target.is_current_char = True

        task = Task()
        rotation = Rotation(task)
        self.assertTrue(rotation.perform())
        self.assertTrue(rotation.startup_done)
        self.assertEqual(task.switches, [(task.chars[0], task.chars[1], True)])

        self.assertTrue(rotation.perform())
        self.assertEqual(task.switches[-1], (task.chars[1], task.chars[0], False))

    def test_team_rotation_runs_intro_hook_once_per_switch_in(self):
        class IntroChar(BaseChar):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.intro_records = 0

            def record_intro_liberation(self):
                self.intro_records += 1

        class Rotation(TeamRotation):
            required_char_classes = (IntroChar,)
            startup_steps = (
                TeamRotationStep(
                    IntroChar,
                    (TeamAction(name='wait', duration=0),),
                    label='intro',
                ),
            )

        class Task:
            config = {'Use Team Axis': True}

            def __init__(self):
                self.combat_start = time.time()
                self.chars = [IntroChar(self, 0)]
                self.chars[0].is_current_char = True
                self.chars[0].has_intro = True
                self.chars[0].last_switch_in_time = 123

            def sleep(self, *args, **kwargs):
                pass

            def get_current_char(self, raise_exception=False):
                return self.chars[0]

        task = Task()
        rotation = Rotation(task)

        self.assertTrue(rotation.perform())
        self.assertEqual(task.chars[0].intro_records, 1)

        rotation.startup_done = False
        rotation.startup_index = 0
        self.assertTrue(rotation.perform())
        self.assertEqual(task.chars[0].intro_records, 1)

    def test_team_rotation_required_action_failure_holds_step(self):
        class First(BaseChar):
            pass

        class Second(BaseChar):
            pass

        class Rotation(TeamRotation):
            required_char_classes = (First, Second)
            startup_steps = (
                TeamRotationStep(
                    First,
                    (TeamAction(name='wait', kwargs={'required': True}),),
                    next_char_cls=Second,
                    label='first',
                ),
            )

        class Task:
            config = {'Use Team Axis': True}

            def __init__(self):
                self.combat_start = time.time()
                self.chars = [First(self, 0), Second(self, 1)]
                self.chars[0].is_current_char = True
                self.switches = []

            def get_current_char(self, raise_exception=False):
                for char in self.chars:
                    if char.is_current_char:
                        return char
                return None

            def switch_to_char(self, current, target, free_intro=False):
                self.switches.append((current, target, free_intro))

        task = Task()
        rotation = Rotation(task)
        rotation.runner.run = lambda *args, **kwargs: False

        self.assertFalse(rotation.perform())
        self.assertEqual(rotation.startup_index, 0)
        self.assertFalse(rotation.startup_done)
        self.assertEqual(task.switches, [])

    def test_team_rotation_resumes_interrupted_step_at_failed_action(self):
        class First(BaseChar):
            pass

        class Second(BaseChar):
            pass

        class Rotation(TeamRotation):
            required_char_classes = (First, Second)
            startup_steps = (
                TeamRotationStep(
                    First,
                    (
                        TeamAction(name='wait', label='first'),
                        TeamAction(name='wait', label='second'),
                    ),
                    next_char_cls=Second,
                    label='first-step',
                ),
            )

        class Task:
            config = {'Use Team Axis': True}

            def __init__(self):
                self.combat_start = time.time()
                self.chars = [First(self, 0), Second(self, 1)]
                self.chars[0].is_current_char = True
                self.switches = []

            def get_current_char(self, raise_exception=False):
                for char in self.chars:
                    if char.is_current_char:
                        return char
                return None

            def switch_to_char(self, current, target, free_intro=False):
                self.switches.append((current, target, free_intro))
                current.is_current_char = False
                target.is_current_char = True

        task = Task()
        rotation = Rotation(task)
        calls = []
        interrupted = {'value': False}

        def run_action(_char, action, context=''):
            calls.append(action.label)
            if action.label == 'second' and not interrupted['value']:
                interrupted['value'] = True
                raise RuntimeError('interrupted')
            return True

        rotation.runner.run = run_action

        with self.assertRaises(RuntimeError):
            rotation.perform()

        self.assertEqual(rotation.action_index, 1)
        self.assertEqual(calls, ['first', 'second'])

        self.assertTrue(rotation.perform())
        self.assertEqual(calls, ['first', 'second', 'second'])
        self.assertTrue(rotation.startup_done)
        self.assertEqual(task.switches, [(task.chars[0], task.chars[1], False)])

    def test_team_action_runner_retries_false_results(self):
        class Task:
            def __init__(self):
                self.skip_combat_check = False
                self.sleeps = []

            def sleep(self, sec):
                self.sleeps.append(sec)

        task = Task()
        char = BaseChar(task, 0)
        runner = TeamActionRunner(task)
        calls = []

        def run_probe(_char, _action):
            calls.append(1)
            return len(calls) == 2

        runner._run_probe = run_probe

        result = runner.run(char, TeamAction(name='probe', kwargs={'attempts': 3, 'retry_delay': 0}))

        self.assertTrue(result)
        self.assertEqual(len(calls), 2)

    def test_aemeath_lib(self):
        self.task.do_reset_to_false()
        self.set_image('tests/images/aemeath_lib.png')
        in_combat = self.task.in_combat()
        self.assertTrue(in_combat)
        liberation_available = self.task.available('liberation')
        self.assertTrue(liberation_available)

    def test_switch_cd(self):
        self.task.do_reset_to_false()
        self.set_image('tests/images/combat_has_cd.png')
        self.task.load_chars()
        self.assertTrue(len(self.task.chars) > 0)
        self.assertEqual(self.task.chars[0].name, 'Aemeath')

        self.set_image('ok_templates/char_iuno.png')
        self.task.load_chars()
        self.assertTrue(len(self.task.chars) > 0)
        self.assertEqual(self.task.chars[0].name, 'Iuno')

    def test_luhesi_cd(self):
        self.task.do_reset_to_false()
        self.set_image('tests/images/luhesi_lib_in_cd.png')
        self.task.load_chars()
        self.assertTrue(len(self.task.chars) > 0)
        self.assertEqual(self.task.chars[0].name, 'Luhesi')

        has_cd = self.task.chars[0].has_cd('liberation')
        time.sleep(1)
        self.task.screenshot('click_liberation', show_box=True)
        self.assertTrue(has_cd)


if __name__ == '__main__':
    unittest.main()
