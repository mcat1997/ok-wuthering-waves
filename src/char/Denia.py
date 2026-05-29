from src.char.BaseChar import BaseChar


class Denia(BaseChar):

    def perform_resonance_liberation_chain(self, wait_intro=False):
        if wait_intro and self.has_intro:
            self.wait_intro(1.2)
        resonance_result = None
        if self.resonance_available():
            resonance_result = self.click_resonance()
        liberation_result = self.click_liberation(wait_if_cd_ready=0.6)
        follow_resonance_result = None
        if liberation_result:
            follow_resonance_result = self.click_resonance(time_out=0.8)
        self.logger.info(
            f'denia resonance liberation chain resonance={resonance_result} '
            f'liberation={liberation_result} follow_resonance={follow_resonance_result}')
        return bool(liberation_result)

    def do_perform(self):
        if self.has_intro:
            self.wait_intro(1.2)
        if self.resonance_available() and self.click_resonance()[0]:
            pass
        if self.click_liberation():
            self.click_resonance()
        self.click_echo()
        self.switch_next_char()
