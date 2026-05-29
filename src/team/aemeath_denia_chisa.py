from src.char.Aemeath import Aemeath
from src.char.Chisa import Chisa
from src.char.Denia import Denia
from src.team.TeamRotation import TeamAction, TeamRotation, TeamRotationStep


def action(name, label='', count=0, duration=0, **kwargs):
    return TeamAction(name=name, label=label, count=count, duration=duration, kwargs=kwargs)


class AemeathDeniaChisaRotation(TeamRotation):
    name = '1C Aemeath / Denia / Chisa'
    version = '2026-05-29-state-driven-v1'
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
                action('normal', '2A', count=2, interval=0.22, post_delay=0.1),
            ),
            next_char_cls=Chisa,
            label='达妮娅 E-R-2A',
        ),
        TeamRotationStep(
            Chisa,
            (
                action('liberation', 'R'),
                action('normal_chain', 'a3', duration=0.55),
            ),
            next_char_cls=Denia,
            label='千咲 R-a3',
        ),
        TeamRotationStep(
            Denia,
            (action('normal_chain', 'a3a4', duration=0.85),),
            next_char_cls=Chisa,
            label='达妮娅 a3a4',
        ),
        TeamRotationStep(
            Chisa,
            (
                action('normal_chain', 'a4a5', duration=1.0),
                action('echo', 'Q', post_delay=0.25),
                action('enhanced_resonance', '强化E', pre_delay=0.15, post_delay=0.15,
                       time_out=0.8, required=True, attempts=2, retry_delay=0.2),
            ),
            next_char_cls=Denia,
            label='千咲 a4a5-Q-强化E',
        ),
        TeamRotationStep(
            Denia,
            (
                action('normal', '2A', count=2, interval=0.22, post_delay=0.25),
                action('char_method', '强化E-R2-E状态链',
                       method='perform_resonance_liberation_chain',
                       required=True, attempts=3, retry_delay=0.2),
            ),
            next_char_cls=Chisa,
            label='达妮娅 2A-强化E-R2',
        ),
        TeamRotationStep(
            Chisa,
            (
                action('char_method', '点按a2a3-电锯终结状态链',
                       method='perform_forte_outro_chain', build_time=2.4,
                       build_interval=0.08, tap_resonance=True,
                       required=True, attempts=2, retry_delay=0.25),
            ),
            next_char_cls=Aemeath,
            next_free_intro=True,
            label='千咲 点按a2a3-电锯终结-变奏',
            intro_actions=(
                action('build_con', '补协奏到变奏', duration=2.4, interval=0.08),
            ),
            intro_retry_limit=3,
        ),
        TeamRotationStep(
            Aemeath,
            (
                action('echo', 'Q', post_delay=0.15),
                action('normal_chain', 'a3a4', duration=0.45),
                action('liberation', 'R1', pre_delay=0.15, wait_if_cd_ready=0.4,
                       required=True, attempts=2, retry_delay=0.25),
                action('execute', '1链重击', duration=0.8, post_delay=0.35),
                action('char_method', '强化E-处决状态链',
                       method='perform_enhanced_resonance', wait_time=1.6,
                       tap_while_wait=True, resonance_while_wait=False,
                       resonance_wait_interval=0.18, stop_on_fail=True),
                action('normal_chain', 'a3a4', duration=0.45),
                action('char_method', '强化E-处决状态链',
                       method='perform_enhanced_resonance', wait_time=1.6,
                       tap_while_wait=True, resonance_while_wait=False,
                       resonance_wait_interval=0.18, stop_on_fail=True),
                action('execute', '快速重击', duration=0.45, post_delay=0.25),
                action('liberation', 'R2', wait_if_cd_ready=0.4, attempts=2, retry_delay=0.25,
                       wait_time=2.0, require_lib2=True, stop_on_fail=True),
                action('resonance', 'E'),
                action('normal', '2A', count=2),
                action('resonance', 'E'),
            ),
            next_char_cls=Chisa,
            label='爱弥斯 Q-a3a4-R1-重击-强化E-处决-a3a4-强化E-重击-R2-E-2A-E',
        ),
    )

    loop_steps = (
        TeamRotationStep(
            Chisa,
            (
                action('resonance', 'E'),
                action('normal_chain', 'a3', duration=0.55),
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
                action('normal_chain', 'a4a5', duration=1.0),
                action('echo', 'Q', post_delay=0.25),
            ),
            next_char_cls=Denia,
            label='千咲 a4(a5)-Q',
        ),
        TeamRotationStep(
            Denia,
            (
                action('liberation', 'R', wait_if_cd_ready=0.4),
                action('normal', '2A', count=2, interval=0.22, post_delay=0.1),
            ),
            next_char_cls=Chisa,
            label='达妮娅 R-2A',
        ),
        TeamRotationStep(
            Chisa,
            (
                action('liberation', 'R', wait_if_cd_ready=0.4, attempts=2, retry_delay=0.25),
                action('enhanced_resonance', '强化E', pre_delay=0.15, post_delay=0.15,
                       time_out=0.8, required=True, attempts=2, retry_delay=0.2),
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
                action('char_method', '点按a2a3-电锯终结状态链',
                       method='perform_forte_outro_chain', build_time=2.4,
                       build_interval=0.08, tap_resonance=True,
                       required=True, attempts=2, retry_delay=0.25),
            ),
            next_char_cls=Denia,
            next_free_intro=True,
            label='千咲 点按a2a3-电锯终结-变奏',
            intro_actions=(
                action('build_con', '补协奏到变奏', duration=2.4, interval=0.08),
            ),
            intro_retry_limit=3,
        ),
        TeamRotationStep(
            Denia,
            (
                action('normal', '2A', count=2, interval=0.22, post_delay=0.25),
                action('char_method', '强化E-R2-E状态链',
                       method='perform_resonance_liberation_chain',
                       required=True, attempts=3, retry_delay=0.2),
            ),
            next_char_cls=Aemeath,
            next_free_intro=True,
            label='达妮娅 2A-强化E-R2-变奏',
            intro_actions=(
                action('build_con', '补协奏到变奏', duration=3.0, interval=0.08,
                       click_resonance_if_ready=True),
            ),
            intro_retry_limit=2,
        ),
        TeamRotationStep(
            Aemeath,
            (
                action('echo', 'Q', post_delay=0.15),
                action('normal_chain', 'a3a4', duration=0.45),
                action('liberation', 'R1', pre_delay=0.15, wait_if_cd_ready=0.4,
                       required=True, attempts=2, retry_delay=0.25),
                action('execute', '1链重击', duration=0.8, post_delay=0.35),
                action('char_method', '强化E-处决状态链',
                       method='perform_enhanced_resonance', wait_time=1.6,
                       tap_while_wait=True, resonance_while_wait=False,
                       resonance_wait_interval=0.18, stop_on_fail=True),
                action('normal_chain', 'a3a4', duration=0.45),
                action('char_method', '强化E-处决状态链',
                       method='perform_enhanced_resonance', wait_time=1.6,
                       tap_while_wait=True, resonance_while_wait=False,
                       resonance_wait_interval=0.18, stop_on_fail=True),
                action('execute', '快速重击', duration=0.45, post_delay=0.25),
                action('liberation', 'R2', wait_if_cd_ready=0.4, attempts=2, retry_delay=0.25,
                       wait_time=2.0, require_lib2=True, stop_on_fail=True),
                action('resonance', 'E'),
                action('normal', '2A', count=2),
                action('resonance', 'E'),
            ),
            next_char_cls=Chisa,
            label='爱弥斯 Q-a3a4-R1-重击-强化E-处决-a3a4-强化E-重击-R2-E-2A-E',
        ),
    )
