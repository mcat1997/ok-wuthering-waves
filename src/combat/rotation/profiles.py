from src.combat.rotation.base import TeamRotationError, TeamRotationProfile, TeamRotationResult, TeamSignature


class AemeathDeniaChisaProfile(TeamRotationProfile):
    """Developer profile based on the BV1aDGe6JEwT 5R2 Aemeath/Denia/Chisa chart."""

    signature = TeamSignature.of('Aemeath', 'Denia', 'Chisa')
    startup_order = ('Chisa', 'Denia', 'Chisa', 'Denia', 'Chisa', 'Aemeath')
    cycle_order = ('Chisa', 'Denia', 'Chisa', 'Aemeath')

    def __init__(self):
        self.startup_done = False
        self.step_index = 0

    def perform_turn(self, context):
        order = self.cycle_order if self.startup_done else self.startup_order
        expected = order[self.step_index]
        current = context.current_char
        if current.name != expected:
            context.switch_to(expected)
            return TeamRotationResult.handled(f'switch to expected {expected}')

        self._perform_current_axis(context, current.name)
        self._advance()

        next_order = self.cycle_order if self.startup_done else self.startup_order
        next_name = next_order[self.step_index]
        if context.current_char.name != next_name:
            context.switch_to(next_name)
        return TeamRotationResult.handled(f'{current.name} axis step')

    def _advance(self):
        order = self.cycle_order if self.startup_done else self.startup_order
        self.step_index += 1
        if self.step_index >= len(order):
            self.startup_done = True
            self.step_index = 0

    def _perform_current_axis(self, context, char_name):
        if char_name == 'Chisa':
            return self._perform_chisa(context.current_char)
        if char_name == 'Denia':
            return self._perform_denia(context.current_char)
        if char_name == 'Aemeath':
            return self._perform_aemeath(context.current_char)
        raise TeamRotationError(f'unsupported axis char: {char_name}')

    def _perform_chisa(self, chisa):
        if chisa.has_intro:
            chisa.record_support_buff()
            chisa.continues_normal_attack(0.35)
        chisa.click_resonance(time_out=0.5)
        chisa.continues_normal_attack(0.35)
        if chisa.click_liberation():
            chisa.record_support_buff()
            chisa.continues_normal_attack(0.4)
        chisa.click_echo(time_out=0)
        if chisa.is_forte_full():
            chisa.perform_forte()

    def _perform_denia(self, denia):
        if denia.has_intro:
            denia.wait_intro(1.0)
        denia.click_resonance(time_out=0.5)
        denia.continues_normal_attack(0.35)
        if denia.click_liberation():
            denia.continues_normal_attack(0.25)
            denia.click_resonance(time_out=0.5)
        denia.click_echo(time_out=0)
        denia.continues_normal_attack(0.25)

    def _perform_aemeath(self, aemeath):
        if aemeath.has_intro:
            aemeath.record_intro_liberation()
            aemeath.continues_normal_attack(0.6)
        aemeath.click_echo(time_out=0)
        aemeath.perform_everything()
