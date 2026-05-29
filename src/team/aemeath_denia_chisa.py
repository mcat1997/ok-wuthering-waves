from src.char.Aemeath import Aemeath
from src.char.Chisa import Chisa
from src.char.Denia import Denia
from src.team.TeamRotation import TeamAction, TeamRotation, TeamRotationStep


def action(name, label='', count=0, duration=0, **kwargs):
    return TeamAction(name=name, label=label, count=count, duration=duration, kwargs=kwargs)


class AemeathDeniaChisaRotation(TeamRotation):
    name = '1C Aemeath / Denia / Chisa'
    required_char_classes = (Aemeath, Denia, Chisa)

    startup_steps = (
        TeamRotationStep(
            Chisa,
            (action('resonance', 'E', time_out=0.5),),
            next_char_cls=Denia,
            label='千咲 E',
        ),
        TeamRotationStep(
            Denia,
            (
                action('resonance', 'E', post_delay=0.35),
                action('liberation', 'R', wait_if_cd_ready=0.4),
                action('normal', '2A', count=2),
            ),
            next_char_cls=Chisa,
            label='达妮娅 E-R-2A',
        ),
        TeamRotationStep(
            Chisa,
            (
                action('liberation', 'R'),
                action('normal_chain', 'a3', duration=0.35),
            ),
            next_char_cls=Denia,
            label='千咲 R-a3',
        ),
        TeamRotationStep(
            Denia,
            (action('normal_chain', 'a3a4', duration=0.45),),
            next_char_cls=Chisa,
            label='达妮娅 a3a4',
        ),
        TeamRotationStep(
            Chisa,
            (
                action('normal_chain', 'a4a5', duration=0.55),
                action('echo', 'Q', post_delay=0.25),
                action('enhanced_resonance', '强化E', pre_delay=0.15, post_delay=0.15,
                       time_out=0.4, force_on_fail=True, force_down_time=0.12),
            ),
            next_char_cls=Denia,
            label='千咲 a4a5-Q-强化E',
        ),
        TeamRotationStep(
            Denia,
            (
                action('normal', '2A', count=2, post_delay=0.25),
                action('enhanced_resonance', '强化E', pre_delay=0.15, required=True,
                       attempts=2, retry_delay=0.25),
                action('liberation', 'R2', wait_if_cd_ready=0.4, attempts=2, retry_delay=0.25),
            ),
            next_char_cls=Chisa,
            label='达妮娅 2A-强化E-R2',
        ),
        TeamRotationStep(
            Chisa,
            (
                action('tap_normal_chain', '点按a2a3', duration=0.8),
                action('forte', '电锯终结', required=True, attempts=2, retry_delay=0.25),
            ),
            next_char_cls=Aemeath,
            next_free_intro=True,
            label='千咲 点按a2a3-电锯终结-变奏',
        ),
        TeamRotationStep(
            Aemeath,
            (
                action('echo', 'Q', post_delay=0.15),
                action('normal_chain', 'a3a4', duration=0.45),
                action('liberation', 'R1', pre_delay=0.15, wait_if_cd_ready=0.4,
                       required=True, attempts=2, retry_delay=0.25),
                action('execute', '1链重击', duration=0.8),
                action('enhanced_resonance', '强化E', required=True, attempts=2, retry_delay=0.25),
                action('execute', '处决'),
                action('normal_chain', 'a3a4', duration=0.45),
                action('enhanced_resonance', '强化E', required=True, attempts=2, retry_delay=0.25),
                action('heavy', '快速重击', duration=0.45),
                action('liberation', 'R2', wait_if_cd_ready=0.4, attempts=2, retry_delay=0.25),
                action('resonance', 'E'),
                action('normal', '2A', count=2),
                action('resonance', 'E'),
            ),
            next_char_cls=Chisa,
            next_free_intro=True,
            label='爱弥斯 Q-a3a4-R1-重击-强化E-处决-a3a4-强化E-重击-R2-E-2A-E',
        ),
    )

    loop_steps = (
        TeamRotationStep(
            Chisa,
            (
                action('resonance', 'E'),
                action('normal_chain', 'a3', duration=0.35),
            ),
            next_char_cls=Denia,
            label='千咲 E-a3',
        ),
        TeamRotationStep(
            Denia,
            (action('resonance', 'E'),),
            next_char_cls=Aemeath,
            label='达妮娅 E',
        ),
        TeamRotationStep(
            Aemeath,
            (
                action('normal_chain', 'a2a3', duration=0.45),
                action('resonance', 'E'),
            ),
            next_char_cls=Chisa,
            label='爱弥斯 a2a3-E',
        ),
        TeamRotationStep(
            Chisa,
            (
                action('normal_chain', 'a4a5', duration=0.55),
                action('echo', 'Q', post_delay=0.25),
            ),
            next_char_cls=Denia,
            label='千咲 a4(a5)-Q',
        ),
        TeamRotationStep(
            Denia,
            (
                action('liberation', 'R', wait_if_cd_ready=0.4),
                action('normal', '2A', count=2),
            ),
            next_char_cls=Chisa,
            label='达妮娅 R-2A',
        ),
        TeamRotationStep(
            Chisa,
            (
                action('liberation', 'R', wait_if_cd_ready=0.4, attempts=2, retry_delay=0.25),
                action('enhanced_resonance', '强化E', pre_delay=0.15, post_delay=0.15,
                       time_out=0.4, force_on_fail=True, force_down_time=0.12),
            ),
            next_char_cls=Aemeath,
            label='千咲 R-强化E',
        ),
        TeamRotationStep(
            Aemeath,
            (
                action('normal_chain', 'a2a3', duration=0.45),
                action('resonance', 'E'),
            ),
            next_char_cls=Chisa,
            label='爱弥斯 a2a3-E',
        ),
        TeamRotationStep(
            Chisa,
            (
                action('tap_normal_chain', '点按a2a3', duration=0.8),
                action('forte', '电锯终结', required=True, attempts=2, retry_delay=0.25),
            ),
            next_char_cls=Denia,
            next_free_intro=True,
            label='千咲 点按a2a3-电锯终结-变奏',
        ),
        TeamRotationStep(
            Denia,
            (
                action('normal', '2A', count=2, post_delay=0.25),
                action('enhanced_resonance', '强化E', pre_delay=0.15, required=True,
                       attempts=2, retry_delay=0.25),
                action('liberation', 'R2', wait_if_cd_ready=0.4, attempts=2, retry_delay=0.25),
            ),
            next_char_cls=Aemeath,
            next_free_intro=True,
            label='达妮娅 2A-强化E-R2-变奏',
        ),
        TeamRotationStep(
            Aemeath,
            (
                action('echo', 'Q', post_delay=0.15),
                action('normal_chain', 'a3a4', duration=0.45),
                action('liberation', 'R1', pre_delay=0.15, wait_if_cd_ready=0.4,
                       required=True, attempts=2, retry_delay=0.25),
                action('execute', '1链重击', duration=0.8),
                action('enhanced_resonance', '强化E', required=True, attempts=2, retry_delay=0.25),
                action('execute', '处决'),
                action('normal_chain', 'a3a4', duration=0.45),
                action('enhanced_resonance', '强化E', required=True, attempts=2, retry_delay=0.25),
                action('heavy', '快速重击', duration=0.45),
                action('liberation', 'R2', wait_if_cd_ready=0.4, attempts=2, retry_delay=0.25),
                action('resonance', 'E'),
                action('normal', '2A', count=2),
                action('resonance', 'E'),
            ),
            next_char_cls=Chisa,
            next_free_intro=True,
            label='爱弥斯 Q-a3a4-R1-重击-强化E-处决-a3a4-强化E-重击-R2-E-2A-E',
        ),
    )
