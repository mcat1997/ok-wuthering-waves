import time

from ok import Logger

from src.combat.rotation.base import TeamRotationError, TeamRotationProfile, TeamRotationResult, TeamSignature


logger = Logger.get_logger(__name__)


class AemeathDeniaChisaProfile(TeamRotationProfile):
    """Developer profile based on the BV1aDGe6JEwT 5R2 Aemeath/Denia/Chisa chart."""

    max_turn_seconds = 30
    signature = TeamSignature.of('Aemeath', 'Denia', 'Chisa')
    startup_plan = (
        ('Chisa', 'E', '_chisa_start_e'),
        ('Denia', 'E-R-2A', '_denia_e_r_2a'),
        ('Chisa', 'R-a3', '_chisa_r_a3'),
        ('Denia', 'a3a4', '_denia_a3a4'),
        ('Chisa', 'a4a5-Q-enhancedE', '_chisa_a4a5_q_enhanced_e'),
        ('Denia', '2A-enhancedE-R2', '_denia_2a_enhanced_e_r2'),
        ('Chisa', 'tap-a2a3-finish', '_chisa_finish'),
        ('Aemeath', 'Q-a3a4-R1', '_aemeath_q_a3a4_r1'),
        ('Aemeath', 'one-chain-heavy-enhancedE', '_aemeath_one_chain_heavy_enhanced_e'),
        ('Aemeath', 'execute-a3a4-enhancedE', '_aemeath_execute_a3a4_enhanced_e'),
        ('Aemeath', 'fastHeavy-R2', '_aemeath_fast_heavy_r2_startup'),
        ('Aemeath', 'E-2A-E', '_aemeath_e_2a_e'),
    )
    cycle_plan = (
        ('Chisa', 'E-a3', '_chisa_e_a3'),
        ('Denia', 'E', '_denia_e'),
        ('Aemeath', 'a2a3-E', '_aemeath_a2a3_e'),
        ('Chisa', 'a4(a5)-(Q)', '_chisa_a4a5_q'),
        ('Denia', 'R-2A', '_denia_r_2a'),
        ('Chisa', 'R-enhancedE', '_chisa_r_enhanced_e'),
        ('Aemeath', 'a2a3-E', '_aemeath_a2a3_e'),
        ('Chisa', 'tap-a2a3-finish', '_chisa_finish'),
        ('Denia', '2A-enhancedE-R2', '_denia_2a_enhanced_e_r2'),
        ('Aemeath', 'Q-a3a4-R1', '_aemeath_q_a3a4_r1'),
        ('Aemeath', 'one-chain-heavy-enhancedE', '_aemeath_one_chain_heavy_enhanced_e'),
        ('Aemeath', 'execute-a3a4-enhancedE', '_aemeath_execute_a3a4_enhanced_e'),
        ('Aemeath', 'fastHeavy-R2', '_aemeath_fast_heavy_r2_cycle'),
        ('Aemeath', 'E-2A-E', '_aemeath_e_2a_e'),
    )

    def __init__(self):
        self.startup_done = False
        self.step_index = 0
        self.aemeath_r1_casted = False

    def perform_turn(self, context):
        plan = self.cycle_plan if self.startup_done else self.startup_plan
        phase = 'cycle' if self.startup_done else 'startup'
        expected, label, action_name = plan[self.step_index]
        current = context.current_char
        elapsed = self._combat_elapsed(current)
        logger.info(
            f'team rotation step: {self.name} phase={phase} step={self.step_index} action={label} '
            f'current={current.name}[{current.index}] expected={expected} combat_elapsed={elapsed:.2f}s')
        if current.name != expected:
            context.switch_to(expected)
            return TeamRotationResult.handled(f'switch to expected {expected}')

        self._perform_action(context, action_name, label)
        self._advance()

        next_plan = self.cycle_plan if self.startup_done else self.startup_plan
        next_name = next_plan[self.step_index][0]
        if context.current_char.name != next_name:
            context.switch_to(next_name)
        return TeamRotationResult.handled(f'{current.name} {label}')

    def _advance(self):
        order = self.cycle_plan if self.startup_done else self.startup_plan
        self.step_index += 1
        if self.step_index >= len(order):
            self.step_index = 0
            if not self.startup_done:
                self.startup_done = True
                logger.info(f'team rotation phase advanced: {self.name} startup_done={self.startup_done}')
            else:
                logger.info(f'team rotation cycle completed: {self.name}')

    def _perform_action(self, context, action_name, label):
        action = getattr(self, action_name, None)
        if action is None:
            raise TeamRotationError(f'unsupported chart action: {action_name}')
        logger.info(
            f'team rotation action start: {self.name} {context.current_char.name} {label} '
            f'combat_elapsed={self._combat_elapsed(context.current_char):.2f}s')
        action(context.current_char)
        logger.info(
            f'team rotation action end: {self.name} {context.current_char.name} {label} '
            f'combat_elapsed={self._combat_elapsed(context.current_char):.2f}s')

    def _combat_elapsed(self, char):
        combat_start = getattr(getattr(char, 'task', None), 'combat_start', -1)
        if combat_start is None or combat_start < 0:
            return -1
        return time.time() - combat_start

    def _tap_frame(self, char):
        if hasattr(char, 'click'):
            char.click(interval=0.1)
        elif hasattr(char, 'task') and hasattr(char.task, 'click'):
            char.task.click(interval=0.1)
        if hasattr(char, 'task') and hasattr(char.task, 'next_frame'):
            char.task.next_frame()
        elif hasattr(char, 'sleep'):
            char.sleep(0.05)

    def _wait_frames_until(self, char, predicate, max_frames, label):
        for frame in range(max_frames):
            if predicate():
                logger.info(
                    f'team rotation wait state ready: {self.name} {char.name} {label} '
                    f'frames={frame} combat_elapsed={self._combat_elapsed(char):.2f}s')
                return True
            self._tap_frame(char)
        ready = predicate()
        logger.info(
            f'team rotation wait state end: {self.name} {char.name} {label} '
            f'ready={ready} frames={max_frames} combat_elapsed={self._combat_elapsed(char):.2f}s')
        return ready

    def _supports_sleep_without_combat_check(self, char):
        task = getattr(char, 'task', None)
        return task is not None and hasattr(task, 'skip_combat_check') and hasattr(task, 'click')

    def _with_task_skip_combat_check(self, char, action):
        task = getattr(char, 'task', None)
        if task is None or not hasattr(task, 'skip_combat_check'):
            return action()

        old_skip = task.skip_combat_check
        task.skip_combat_check = True
        try:
            return action()
        finally:
            task.skip_combat_check = old_skip

    def _normal_without_combat_check(self, char, duration, until_con_full=False, interval=0.1):
        start = time.time()
        while time.time() - start < duration:
            if until_con_full and char.is_con_full():
                return
            char.task.click()
            char.sleep(interval, check_combat=False)

    def _normal(self, char, duration, label, until_con_full=False, check_combat=False):
        logger.info(f'team rotation normal: {self.name} {char.name} {label} duration={duration}')
        if not check_combat and self._supports_sleep_without_combat_check(char):
            return self._normal_without_combat_check(char, duration, until_con_full=until_con_full)
        return char.continues_normal_attack(duration, until_con_full=until_con_full)

    def _resonance(self, char, label, **kwargs):
        ret = char.click_resonance(**kwargs)
        logger.info(f'team rotation resonance: {self.name} {char.name} {label} ret={ret}')
        return ret

    def _liberation(self, char, label, **kwargs):
        ret = char.click_liberation(**kwargs)
        logger.info(f'team rotation liberation: {self.name} {char.name} {label} ret={ret}')
        return ret

    def _tap_liberation(self, char, label, after_sleep=0.15):
        if not getattr(char.task, 'use_liberation', True):
            logger.info(f'team rotation liberation tap skipped: {self.name} {char.name} {label} use_liberation=False')
            return False
        available = char.liberation_available() if hasattr(char, 'liberation_available') else True
        if not available:
            logger.info(f'team rotation liberation tap unavailable: {self.name} {char.name} {label}')
            return False
        if hasattr(char, 'send_liberation_key'):
            char.send_liberation_key()
        else:
            char.click_liberation(wait_if_cd_ready=0)
        if hasattr(char, 'record_liberation_use'):
            char.record_liberation_use()
        if after_sleep > 0 and hasattr(char, 'sleep'):
            char.sleep(after_sleep, check_combat=False)
        logger.info(f'team rotation liberation tap: {self.name} {char.name} {label}')
        return True

    def _echo(self, char, label, **kwargs):
        ret = char.click_echo(**kwargs)
        logger.info(f'team rotation echo: {self.name} {char.name} {label} ret={ret}')
        return ret

    def _heavy(self, char, duration, label):
        logger.info(f'team rotation heavy: {self.name} {char.name} {label} duration={duration}')
        if hasattr(char, 'heavy_attack'):
            self._with_task_skip_combat_check(char, lambda: char.heavy_attack(duration))
        else:
            self._normal(char, duration, label)

    def _send_aemeath_liberation_key(self, aemeath, label, after_sleep=0.05):
        if not getattr(aemeath.task, 'use_liberation', True):
            logger.info(f'team rotation aemeath liberation key skipped: {self.name} {label} use_liberation=False')
            return False
        if hasattr(aemeath, 'send_liberation_key'):
            try:
                aemeath.send_liberation_key(after_sleep=after_sleep)
            except TypeError:
                aemeath.send_liberation_key()
            sent = True
        else:
            sent = aemeath.click_liberation(wait_if_cd_ready=0)
        if sent and hasattr(aemeath, 'record_liberation_use'):
            aemeath.record_liberation_use()
        logger.info(
            f'team rotation aemeath liberation key: {self.name} {label} sent={sent} '
            f'combat_elapsed={self._combat_elapsed(aemeath):.2f}s')
        return sent

    def _cast_aemeath_r1(self, aemeath):
        available = aemeath.liberation_available() if hasattr(aemeath, 'liberation_available') else True
        if not available:
            logger.warning(f'team rotation aemeath R1 unavailable: {self.name}')
            return False
        if hasattr(aemeath, 'lib2_available') and aemeath.lib2_available():
            logger.warning(
                f'team rotation aemeath R1 slot continues: {self.name} lib2 template visible before chart R1')
        sent = self._send_aemeath_liberation_key(aemeath, 'R1')
        if sent and hasattr(aemeath, 'record_liberation'):
            aemeath.record_liberation(False)
        logger.info(f'team rotation aemeath R1 tap: {self.name} ret={sent}')
        return sent

    def _perform_aemeath_one_chain_heavy(self, aemeath, r1_casted):
        if not r1_casted:
            logger.warning(
                f'team rotation one-chain heavy preserved: {self.name} R1 was not confirmed, skip stored heavy')
            return False
        if not hasattr(aemeath, 'handle_heavy'):
            logger.warning(f'team rotation one-chain heavy unavailable: {self.name} no handle_heavy')
            return False
        start = time.time()
        while not aemeath.has_long_action() and time.time() - start < 1.8:
            self._tap_frame(aemeath)
        if not aemeath.has_long_action():
            logger.warning(
                f'team rotation one-chain heavy unavailable: {self.name} no enhanced heavy window after R1')
            return False
        ret = self._with_task_skip_combat_check(aemeath, aemeath.handle_heavy)
        logger.info(
            f'team rotation one-chain heavy: {self.name} ret={ret} '
            f'combat_elapsed={self._combat_elapsed(aemeath):.2f}s')
        if ret and hasattr(aemeath, 'f_break'):
            aemeath.f_break()
        return ret

    def _cast_aemeath_r2(self, aemeath, label, max_frames=36):
        available = True
        if hasattr(aemeath, 'lib2_available'):
            available = self._wait_frames_until(aemeath, aemeath.lib2_available, max_frames, f'{label}-available')
        if not available:
            logger.warning(
                f'team rotation aemeath R2 unavailable: {self.name} {label} '
                f'combat_elapsed={self._combat_elapsed(aemeath):.2f}s')
            return False
        sent = self._send_aemeath_liberation_key(aemeath, label)
        consumed = True
        if sent and hasattr(aemeath, 'lib2_available'):
            consumed = self._wait_frames_until(aemeath, lambda: not aemeath.lib2_available(), 12, f'{label}-consumed')
            if not consumed:
                logger.warning(
                    f'team rotation aemeath R2 consume state not observed: {self.name} {label} '
                    f'combat_elapsed={self._combat_elapsed(aemeath):.2f}s')
        ret = bool(sent)
        if ret:
            if hasattr(aemeath, 'record_liberation'):
                aemeath.record_liberation(True)
            if hasattr(aemeath, 'f_break'):
                aemeath.f_break()
        logger.info(
            f'team rotation aemeath R2: {self.name} {label} ret={ret} '
            f'combat_elapsed={self._combat_elapsed(aemeath):.2f}s')
        return ret

    def _enhanced_e(self, char, label, **kwargs):
        ret = self._resonance(char, label, **kwargs)
        clicked = ret[0] if isinstance(ret, tuple) else bool(ret)
        if clicked and hasattr(char, 'record_enhance_e'):
            char.record_enhance_e()
        return ret

    def _chisa_start_e(self, chisa):
        self._resonance(chisa, 'E', time_out=0.6)
        self._normal(chisa, 0.25, 'settle')

    def _chisa_e_a3(self, chisa):
        self._resonance(chisa, 'E', time_out=0.6)
        self._normal(chisa, 0.35, 'a3')

    def _chisa_e_a(self, chisa):
        self._chisa_e_a3(chisa)

    def _chisa_r_a3(self, chisa):
        if self._tap_liberation(chisa, 'R'):
            chisa.record_support_buff()
        self._normal(chisa, 0.35, 'a3')

    def _chisa_a4a5_q(self, chisa):
        self._normal(chisa, 0.55, 'a4a5')
        self._echo(chisa, 'Q', time_out=0)

    def _chisa_a4a5_q_enhanced_e(self, chisa):
        self._chisa_a4a5_q(chisa)
        self._resonance(chisa, 'enhancedE', time_out=0.6)

    def _chisa_r_enhanced_e(self, chisa):
        if self._tap_liberation(chisa, 'R', after_sleep=0.2):
            chisa.record_support_buff()
            self._normal(chisa, 0.25, 'post-R')
        self._resonance(chisa, 'enhancedE', time_out=0.6)

    def _chisa_finish(self, chisa):
        self._normal(chisa, 1.6, 'tap-a2a3-finish', until_con_full=True)
        if chisa.has_intro:
            chisa.record_support_buff()
        if chisa.is_forte_full():
            chisa.perform_forte()

    def _denia_e(self, denia):
        if denia.has_intro:
            denia.wait_intro(1.0)
        self._resonance(denia, 'E', time_out=0.6)

    def _denia_e_r_2a(self, denia):
        if denia.has_intro:
            denia.wait_intro(1.0)
        self._resonance(denia, 'E', time_out=0.6)
        self._tap_liberation(denia, 'R')
        self._normal(denia, 0.25, '2A')

    def _denia_2a(self, denia):
        self._normal(denia, 0.25, '2A')

    def _denia_a3a4(self, denia):
        self._normal(denia, 0.5, 'a3a4')

    def _denia_r_2a(self, denia):
        self._tap_liberation(denia, 'R')
        self._normal(denia, 0.25, '2A')

    def _denia_q_r_2a(self, denia):
        self._echo(denia, 'Q', time_out=0)
        self._denia_r_2a(denia)

    def _denia_2a_enhanced_e_r2(self, denia):
        if denia.has_intro:
            denia.wait_intro(0.8)
        self._normal(denia, 0.3, '2A')
        self._resonance(denia, 'enhancedE', time_out=0.7)
        if self._tap_liberation(denia, 'R2', after_sleep=0.2):
            self._normal(denia, 0.25, 'post-R2')

    def _aemeath_a2a3_e(self, aemeath):
        if aemeath.has_intro:
            aemeath.record_intro_liberation()
            self._normal(aemeath, 0.35, 'intro settle')
        self._normal(aemeath, 0.45, 'a2a3')
        self._enhanced_e(
            aemeath,
            'E',
            has_animation=True,
            send_click=True,
            animation_min_duration=0.5,
            time_out=1.5,
        )

    def _aemeath_q_a3a4_r1(self, aemeath):
        if aemeath.has_intro:
            aemeath.record_intro_liberation()
            self._normal(aemeath, 0.45, 'intro settle')
        self._echo(aemeath, 'Q', time_out=0)
        self._normal(aemeath, 0.55, 'a3a4')
        self.aemeath_r1_casted = self._cast_aemeath_r1(aemeath)

    def _aemeath_q_2a_r(self, aemeath):
        self._aemeath_q_a3a4_r1(aemeath)

    def _aemeath_one_chain_heavy_enhanced_e(self, aemeath):
        heavy_done = self._perform_aemeath_one_chain_heavy(aemeath, self.aemeath_r1_casted)
        self.aemeath_r1_casted = False
        if not heavy_done:
            logger.warning(f'team rotation aemeath one-chain step skipped before enhancedE: {self.name}')
            return
        self._enhanced_e(
            aemeath,
            'enhancedE-after-heavy',
            has_animation=True,
            send_click=True,
            animation_min_duration=0.5,
            time_out=1.5,
        )

    def _aemeath_enhanced_e(self, aemeath):
        self._enhanced_e(
            aemeath,
            'enhancedE',
            has_animation=True,
            send_click=True,
            animation_min_duration=0.5,
            time_out=1.5,
        )

    def _aemeath_execute(self, aemeath):
        self._normal(aemeath, 0.35, 'execute')

    def _aemeath_execute_2a(self, aemeath):
        self._normal(aemeath, 0.55, 'execute-2A')

    def _aemeath_2a_enhanced_e(self, aemeath):
        self._normal(aemeath, 0.3, '2A')
        self._enhanced_e(
            aemeath,
            'enhancedE-after-2A',
            has_animation=True,
            send_click=True,
            animation_min_duration=0.5,
            time_out=1.5,
        )

    def _aemeath_3a_enhanced_e(self, aemeath):
        self._normal(aemeath, 0.45, '3A')
        self._enhanced_e(
            aemeath,
            'enhancedE-after-3A',
            has_animation=True,
            send_click=True,
            animation_min_duration=0.5,
            time_out=1.5,
        )

    def _aemeath_execute_a3a4_enhanced_e(self, aemeath):
        self._normal(aemeath, 0.55, 'execute-a3a4')
        self._enhanced_e(
            aemeath,
            'enhancedE-after-execute-a3a4',
            has_animation=True,
            send_click=True,
            animation_min_duration=0.5,
            time_out=1.5,
        )

    def _aemeath_fast_heavy_r2_startup(self, aemeath):
        self._aemeath_fast_heavy_r2(aemeath, r2_wait_frames=48)

    def _aemeath_fast_heavy_r2_cycle(self, aemeath):
        self._aemeath_fast_heavy_r2(aemeath, r2_wait_frames=36)

    def _aemeath_fast_heavy_r2(self, aemeath, r2_wait_frames=36):
        if hasattr(aemeath, 'handle_heavy') and aemeath.handle_heavy():
            if hasattr(aemeath, 'f_break'):
                aemeath.f_break()
        else:
            self._heavy(aemeath, 0.25, 'fast-heavy')
        self._cast_aemeath_r2(aemeath, 'R2', max_frames=r2_wait_frames)

    def _aemeath_e_2a_e(self, aemeath):
        self._enhanced_e(
            aemeath,
            'E',
            has_animation=True,
            send_click=True,
            animation_min_duration=0.5,
            time_out=1.2,
        )
        self._normal(aemeath, 0.3, '2A')
        self._enhanced_e(
            aemeath,
            'final-E',
            has_animation=True,
            send_click=True,
            animation_min_duration=0.5,
            time_out=1.2,
        )
