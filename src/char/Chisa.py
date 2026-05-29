import time

from src.char.BaseChar import BaseChar


class Chisa(BaseChar):

    def perform_forte_outro_chain(self, build_time=2.0, build_interval=0.08, tap_resonance=True):
        if self.flying() and not self.liberation_available() and not self.resonance_available():
            self.wait_down()
        start = time.time()
        resonance_clicks = 0
        while time.time() - start < build_time and not self.is_forte_full():
            if tap_resonance and self.resonance_available():
                clicked = self.click_resonance(time_out=0.5)[0]
                resonance_clicks += 1 if clicked else 0
                if clicked:
                    continue
            self.click()
            self.check_combat()
            self.sleep(build_interval)
            self.task.next_frame()
        full_before_forte = self.is_forte_full()
        if not full_before_forte:
            self.logger.info(
                f'chisa forte outro chain forte not full build_time={build_time} '
                f'resonance_clicks={resonance_clicks}')
            return False
        result = self.perform_forte()
        self.check_f_on_switch = False
        con = self.get_current_con()
        self.logger.info(
            f'chisa forte outro chain result={result} con={con} '
            f'build_time={build_time} resonance_clicks={resonance_clicks}')
        return result

    def do_perform(self):
        if not self.task.char_config.get("Chisa DPS"):
            return self.do_fast_support()
        return self.do_dps_perform()

    def do_fast_support(self):
        self.check_f_on_switch = True
        if self.has_intro:
            self.record_support_buff()
            self.click_echo(time_out=0)
            return self.switch_next_char()

        if self.flying() and not self.liberation_available() and not self.resonance_available():
            self.wait_down()
        self.click_echo(time_out=0)
        if self.click_liberation():
            self.record_support_buff()
            return self.switch_next_char()

        self.click_resonance(time_out=0.5)
        return self.switch_next_char()

    def record_support_buff(self):
        """Track the buff granted by Chisa's Intro Skill or Resonance Liberation."""
        self.last_buff_time = time.time()

    def switch_out(self, con_full=False):
        support_buff_time = self.last_buff_time
        super().switch_out(con_full=con_full)
        if not self.task.char_config.get("Chisa DPS"):
            self.last_buff_time = support_buff_time

    def do_dps_perform(self):
        timeout = 2.5
        self.check_f_on_switch = True
        if self.has_intro:
            self.continues_normal_attack(0.8)
            timeout = 2.3
        if self.flying() and not self.liberation_available() and not self.resonance_available():
            self.wait_down()
        self.click_echo()
        start = time.time()
        under_liber = False
        while time.time() - start < timeout:
            if time.time() - start < 0.5 and self.click_liberation():
                start = time.time()
                under_liber = True
                timeout = 10
                self.sleep(0.2)
            if time.time() - start < 0.5 and not self.is_forte_full() and self.click_resonance()[0]:
                start = time.time()
                if timeout != 10:
                    timeout = 1.7
            if (under_liber or self.task.char_config.get("Chisa DPS")) and self.is_forte_full() and self.perform_forte():
                self.check_f_on_switch = False
                return self.switch_next_char()
            self.click()
            self.check_combat()
            self.task.next_frame()
        self.switch_next_char()

    def perform_forte(self):
        if self.flying():
            self.wait_down()
        self.task.send_key(self.get_resonance_key(), down_time=1.2)
        if self.is_forte_full():
            return False
        self.heavy_attack(3.5)
        return True
