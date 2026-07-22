import time
import unittest

from src.char.BaseChar import BaseChar, Elements
from src.char.Cartethyia import Cartethyia
from src.char.Ciaccona import Ciaccona
from src.char.HavocRover import HavocRover
from src.team.TeamRotation import TeamRotation, TeamRotationStep, select_team_rotation
from src.team.cartethyia_ciaccona_aero_rover import CartethyiaCiacconaAeroRoverRotation


def bare_char(char_cls, index, ring_index=-1):
    char = object.__new__(char_cls)
    char.index = index
    char.ring_index = ring_index
    char.is_current_char = False
    return char


class TestTeamRotation(unittest.TestCase):

    def test_cartethyia_team_plan_matches_requested_order(self):
        rotation = CartethyiaCiacconaAeroRoverRotation

        self.assertEqual(
            [step.char_cls for step in rotation.steps],
            [
                Cartethyia,
                HavocRover,
                Ciaccona,
                HavocRover,
                Cartethyia,
                Ciaccona,
                HavocRover,
                Ciaccona,
                Cartethyia,
            ],
        )
        self.assertEqual(
            [step.next_char_cls for step in rotation.steps],
            [
                HavocRover,
                Ciaccona,
                HavocRover,
                Cartethyia,
                Ciaccona,
                HavocRover,
                Ciaccona,
                Cartethyia,
                None,
            ],
        )
        self.assertEqual(
            [step.method for step in rotation.steps],
            [
                'perform_team_opening',
                'perform_team_aero_air_combo',
                'perform_team_plunge_forte',
                'perform_team_aero_air_combo',
                'perform_team_resonance_switch',
                'perform_team_plunge_forte',
                None,
                'perform_team_forte_echo_liberation',
                'perform_team_final_rotation',
            ],
        )
        self.assertNotIn('use_echo', rotation.steps[1].kwargs)

    def test_cartethyia_opening_attacks_during_second_liberation_transition(self):
        class Logger:
            def info(self, *_args, **_kwargs):
                pass

            def warning(self, *_args, **_kwargs):
                pass

        class Task:
            def find_one(self, **_kwargs):
                return False

        actions = []
        cartethyia = object.__new__(Cartethyia)
        cartethyia.task = Task()
        cartethyia.logger = Logger()
        cartethyia.is_cartethyia = True
        cartethyia.transform = False
        cartethyia.is_small = lambda: True
        cartethyia._sword2_half_feature = lambda: ('mat', 'box')
        def click_liberation(**kwargs):
            actions.append('R1')
            kwargs['animation_post_action']()
            return True

        cartethyia.click_liberation = click_liberation
        cartethyia.send_liberation_key = lambda **_kwargs: actions.append('R2')
        cartethyia.click = lambda **_kwargs: actions.append('A-during-R2')
        def acquire_sword2(**kwargs):
            actions.append(('A-until-N4', kwargs))
            return True

        cartethyia.acquire_sword2 = acquire_sword2

        self.assertTrue(cartethyia.perform_team_opening())
        self.assertEqual(actions[:4], ['R1', 'R2', 'R2', 'A-during-R2'])
        self.assertEqual(
            actions[4],
            ('A-until-N4', {
                'check_combat': False,
                'handle_airborne_interrupt': False,
                'threshold': 0.7,
                'initial_feature_state': False,
                'start_timeout_condition': cartethyia.is_small,
                'click_after_sleep': 0,
                'timeout_early': 0.5,
            }),
        )

    def test_ciaccona_plunge_normal_waits_for_one_forte_gain(self):
        class Task:
            def next_frame(self):
                pass

        actions = []
        forte = iter((0, 0, 1))
        ciaccona = Ciaccona(Task(), 0)
        ciaccona.judge_forte = lambda: next(forte)
        ciaccona.click_jump_with_click = lambda _delay: actions.append('plunge')
        ciaccona.click = lambda **_kwargs: actions.append('normal')
        ciaccona.check_combat = lambda: None

        self.assertTrue(ciaccona.perform_plunge_normal_forte())
        self.assertEqual(actions, ['plunge', 'normal'])

    def test_aero_rover_takeoff_sends_e_before_first_normal(self):
        class Task:
            def next_frame(self):
                pass

        actions = []
        flying = iter((False, True))
        rover = HavocRover(Task(), 0, ring_index=Elements.WIND)
        rover.send_resonance_key = lambda **_kwargs: actions.append('E')
        rover.record_resonance_use = lambda: actions.append('record-E')
        rover.wind_routine_flying = lambda: next(flying)
        rover.click = lambda **_kwargs: actions.append('ground-normal')

        self.assertTrue(rover.wind_routine_take_off())
        self.assertEqual(actions, ['E', 'record-E', 'ground-normal'])

    def test_aero_rover_confirms_second_takeoff_after_liberation(self):
        class Task:
            pass

        actions = []
        rover = HavocRover(Task(), 0, ring_index=Elements.WIND)
        rover.wind_routine_take_off = lambda: actions.append('E-takeoff') or True
        rover.wind_routine_click_while_flying = (
            lambda *_args, **_kwargs: actions.append('3A') or True)
        rover.click_liberation = lambda **_kwargs: actions.append('R') or True

        self.assertTrue(rover.perform_team_aero_air_combo(use_liberation=True))
        self.assertEqual(actions, ['E-takeoff', '3A', 'R', 'E-takeoff'])

    def test_cartethyia_team_requires_aero_rover_when_form_is_known(self):
        chars = [
            bare_char(Cartethyia, 0),
            bare_char(Ciaccona, 1),
            bare_char(HavocRover, 2, Elements.WIND),
        ]
        self.assertTrue(CartethyiaCiacconaAeroRoverRotation.matches(chars))

        chars[2].ring_index = Elements.HAVOC
        self.assertFalse(CartethyiaCiacconaAeroRoverRotation.matches(chars))

    def test_team_rotation_runs_complete_cycle_and_switches_to_explicit_target(self):
        class First(BaseChar):
            def team_action(self):
                self.task.actions.append('first-action')
                return True

        class Second(BaseChar):
            pass

        class Rotation(TeamRotation):
            required_char_classes = (First, Second)
            steps = (
                TeamRotationStep(
                    First,
                    method='team_action',
                    next_char_cls=Second,
                ),
                TeamRotationStep(Second),
            )

        class Task:
            def __init__(self):
                self.actions = []
                self.chars = [First(self, 0), Second(self, 1)]
                self.chars[0].is_current_char = True
                self.detected_index = 0
                self.in_liberation = False
                self.switch_char_time_out = 1

            def get_current_char(self, raise_exception=False):
                return next((char for char in self.chars if char.is_current_char), None)

            def send_key(self, key):
                if self.detected_index != key - 1:
                    self.actions.append(f'switch-{self.detected_index}-{key - 1}')
                self.detected_index = key - 1

            def in_team(self):
                return True, self.detected_index, len(self.chars)

            def next_frame(self):
                pass

        task = Task()
        rotation = Rotation(task)

        self.assertTrue(rotation.perform())
        self.assertEqual(task.actions, ['first-action', 'switch-0-1'])
        self.assertEqual(rotation.step_index, 0)
        self.assertTrue(task.chars[1].is_current_char)

    def test_select_team_rotation_reuses_only_the_same_combat(self):
        class Task:
            config = {'Use Team Rotation': True}

            def __init__(self):
                self.combat_start = time.time()
                self.chars = [
                    bare_char(Cartethyia, 0),
                    bare_char(Ciaccona, 1),
                    bare_char(HavocRover, 2, Elements.WIND),
                ]

        task = Task()
        rotation = select_team_rotation(task)
        self.assertIs(select_team_rotation(task), rotation)

        task.combat_start += 1
        self.assertIsNot(select_team_rotation(task), rotation)

if __name__ == '__main__':
    unittest.main()
