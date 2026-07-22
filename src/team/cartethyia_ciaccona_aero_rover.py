from src.char.BaseChar import Elements
from src.char.Cartethyia import Cartethyia
from src.char.Ciaccona import Ciaccona
from src.char.HavocRover import HavocRover
from src.team.TeamRotation import TeamRotation, TeamRotationStep


def step(char_cls, method=None, next_char_cls=None, label='', **kwargs):
    return TeamRotationStep(
        char_cls,
        method=method,
        next_char_cls=next_char_cls,
        label=label,
        kwargs=kwargs,
    )


class CartethyiaCiacconaAeroRoverRotation(TeamRotation):
    name = 'Cartethyia / Ciaccona / Rover: Aero'
    required_char_classes = (Cartethyia, Ciaccona, HavocRover)

    @classmethod
    def matches(cls, chars):
        if not super().matches(chars):
            return False
        rover = next(char for char in chars if isinstance(char, HavocRover))
        return rover.ring_index in (-1, Elements.WIND)

    steps = (
        step(
            Cartethyia,
            'perform_team_opening',
            next_char_cls=HavocRover,
            label='卡提希娅 R1-R2-4A+声骸',
        ),
        step(
            HavocRover,
            'perform_team_aero_air_combo',
            next_char_cls=Ciaccona,
            label='气动漂泊者 E-空中3A+声骸',
            use_echo=True,
        ),
        step(
            Ciaccona,
            'perform_team_plunge_forte',
            next_char_cls=HavocRover,
            label='夏空 下落-A-回路-E',
            use_resonance=True,
        ),
        step(
            HavocRover,
            'perform_team_aero_air_combo',
            next_char_cls=Cartethyia,
            label='气动漂泊者 E-空中3A-R-E',
            use_liberation=True,
        ),
        step(
            Cartethyia,
            'perform_team_resonance_switch',
            next_char_cls=Ciaccona,
            label='卡提希娅 E',
        ),
        step(
            Ciaccona,
            'perform_team_plunge_forte',
            next_char_cls=HavocRover,
            label='夏空 下落-A-回路',
        ),
        step(
            HavocRover,
            next_char_cls=Ciaccona,
            label='漂泊者瞬切夏空',
        ),
        step(
            Ciaccona,
            'perform_team_forte_echo_liberation',
            next_char_cls=Cartethyia,
            label='夏空 重击回路+声骸-R',
        ),
        step(
            Cartethyia,
            'perform_team_final_rotation',
            label='卡提希娅双形态完整爆发',
        ),
    )
