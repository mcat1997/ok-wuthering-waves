import time
import unittest

from src.char.BaseChar import BaseChar, Elements
from src.char.Cartethyia import Cartethyia
from src.char.Ciaccona import Ciaccona
from src.char.HavocRover import HavocRover
from src.task.AutoCombatTask import AutoCombatTask
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

    def test_cartethyia_team_requires_aero_rover_when_form_is_known(self):
        chars = [
            bare_char(Cartethyia, 0),
            bare_char(Ciaccona, 1),
            bare_char(HavocRover, 2, Elements.WIND),
        ]
        self.assertTrue(CartethyiaCiacconaAeroRoverRotation.matches(chars))

        chars[2].ring_index = Elements.HAVOC
        self.assertFalse(CartethyiaCiacconaAeroRoverRotation.matches(chars))

    def test_team_rotation_runs_one_step_and_switches_to_explicit_target(self):
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

            def get_current_char(self, raise_exception=False):
                return next((char for char in self.chars if char.is_current_char), None)

            def switch_to_char(self, current, target):
                self.actions.append(f'switch-{current.index}-{target.index}')
                current.is_current_char = False
                target.is_current_char = True

        task = Task()
        rotation = Rotation(task)

        self.assertTrue(rotation.perform())
        self.assertEqual(task.actions, ['first-action', 'switch-0-1'])
        self.assertEqual(rotation.step_index, 1)
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

    def test_switch_to_char_does_not_use_heuristic_target_selection(self):
        combat = AutoCombatTask.__new__(AutoCombatTask)
        current = BaseChar(combat, 0)
        heuristic_target = BaseChar(combat, 1)
        explicit_target = BaseChar(combat, 2)
        combat.chars = [current, heuristic_target, explicit_target]
        current.is_current_char = True
        combat.in_liberation = False
        combat.update_lib_portrait_icon = lambda: None
        combat.check_combat = lambda: None
        combat.log_debug = lambda *args, **kwargs: None
        combat.click = lambda: None
        combat.sleep = lambda *args, **kwargs: None
        combat.add_freeze_duration = lambda *args, **kwargs: None
        combat.send_key = lambda key: setattr(combat, 'detected_index', key - 1)
        combat.in_team = lambda: (True, getattr(combat, 'detected_index', current.index), 3)
        current.get_current_con = lambda: 0
        current.is_con_full = lambda: False
        current.f_break = lambda **kwargs: None

        combat.switch_to_char(current, explicit_target)

        self.assertTrue(explicit_target.is_current_char)
        self.assertFalse(heuristic_target.is_current_char)
        self.assertEqual(combat.detected_index, explicit_target.index)


if __name__ == '__main__':
    unittest.main()
