import time, cv2
import numpy as np
from src.char.BaseChar import BaseChar, SwitchPriority, forte_white_color


class Cartethyia(BaseChar):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_cartethyia = True
        self.buffs = {'sword1': None, 'sword2': None, 'sword3': None}
        self.template_shape = None
        self.try_mid_air_attack_once = False
        self.transform = False
        self.res_time = -1
        self.n4_time = -1
        self.init_template()

    @property
    def intro_motion_freeze_duration(self):
        return 0.6 if self.is_cartethyia else 0.78

    @intro_motion_freeze_duration.setter
    def intro_motion_freeze_duration(self, _):
        pass

    def init_template(self):
        self.template_shape = self.task.frame.shape[:2]
        template = self.task.get_feature_by_name('forte_cartethyia_sword3')
        original_mat = template.mat
        h = original_mat.shape[0]
        self.sword3_half_mat = original_mat[:int(h * 0.5)]
        target_box = self.task.get_box_by_name('forte_cartethyia_sword3')
        target_box.height = int(h * 0.6)
        self.sword3_half_box = target_box

    def on_combat_end(self, chars):
        if not self.is_cartethyia:
            next_char = str((self.index + 1) % len(chars) + 1)
            self.logger.debug(f'on_combat_end {self.index} switch next char: {next_char}')
            start = time.time()
            while time.time() - start < 6:
                self.task.load_chars()
                current_char = self.task.get_current_char(raise_exception=False)
                if not isinstance(current_char, type(self)):
                    break
                else:
                    self.task.send_key(next_char)
                self.sleep(0.2, False)
            self.logger.debug(f'on_combat_end {self.index} switch end')

    def get_switch_priority(self, current_char=None, has_intro=False, target_low_con=False):
        if not self.is_cartethyia:
            return SwitchPriority.MUST
        return super().get_switch_priority(current_char, has_intro, target_low_con)

    def do_perform(self):
        self.transform = False
        if self.has_intro:
            self.continues_normal_attack(1.2)
        else:
            self.click_echo(time_out=0)
        if self.is_small():
            self.logger.info(f'is cartethyia')
            self.wait_down()
            if self.acquire_missing_buffs():
                return self.switch_next_char()
            self.check_combat()
            self.try_mid_air_attack()
            self.check_combat()
            if self.click_liberation():
                self.is_cartethyia = False
                self.last_res = -1
                self.transform = True
            elif not self.is_small():
                self.transform = True
        else:
            self.logger.info(f'is fleurdelys')
        if self.click_resonance_with_lib_big():
            pass
        else:
            time_out = 1.1 if self.is_small() else self.fleurdelys_n4_duration()
            start = time.time()
            while time.time() - start < time_out:
                if self.try_lib_big():
                    return self.switch_next_char()
                self.click_with_interval()
                self.check_combat()
                self.task.next_frame()
            self.n4_time = time.time()
        self.try_lib_big()
        self.switch_next_char()

    def fleurdelys_n4_duration(self):
        if not self.transform and self.has_intro:
            duration = 3.9 - (time.time() - self.last_perform)
        elif self.transform or self.is_first_engage() or \
                self.time_elapsed_accounting_for_freeze(self.n4_time, intro_motion_freeze=True) < 1.5:
            duration = 3.25
        elif (backswing := self.time_elapsed_accounting_for_freeze(self.res_time, intro_motion_freeze=True)) < 2.5:
            duration = 2 + max(0, 1.6 - backswing)
        else:
            duration = 1.9 - (time.time() - self.last_perform)
        self.n4_time = -1
        self.res_time = -1
        self.logger.debug(f'fleurdelys_n4_duration {duration}')
        return duration

    def click_resonance_with_lib_big(self, allow_lib_big=True):
        if self.has_cd('resonance'):
            return False
        clicked = False
        self.logger.debug(f'click_resonance start')
        last_click = 0
        resonance_click_time = 0
        while True:
            if resonance_click_time != 0 and time.time() - resonance_click_time > 8:
                self.task.in_liberation = False
                self.logger.error(f'click_resonance too long, breaking {time.time() - resonance_click_time}')
                self.task.screenshot('click_resonance too long, breaking')
                break
            self.check_combat()
            now = time.time()
            current_resonance = self.current_resonance()
            if not self.resonance_available():
                self.logger.debug(f'click_resonance not available break')
                break
            self.logger.debug(f'click_resonance resonance_available click {current_resonance}')

            if now - last_click > 0.1:
                if current_resonance > 0 and self.resonance_available():
                    if current_resonance < 0.17 and time.time() - resonance_click_time < 2.5:
                        self.click()
                        continue
                    if resonance_click_time == 0:
                        clicked = True
                        resonance_click_time = now
                    self.send_resonance_key()
                last_click = now
            if allow_lib_big and self.try_lib_big():
                break
            self.task.next_frame()
        if clicked:
            self.record_resonance_use()
            self.res_time = time.time()
        return clicked

    def _team_sword2_half_feature(self):
        template = self.task.get_feature_by_name('forte_cartethyia_sword2')
        h = template.mat.shape[0]
        box = self.task.get_box_by_name('forte_cartethyia_sword2')
        box.height = int(h * 0.6)
        return template.mat[:int(h * 0.5)], box

    def perform_team_normal_four(self, use_echo=False, time_out=3.5):
        """持续输入四段普攻，以第二把剑出现作为末段可合轴点。"""
        half_mat, half_box = self._team_sword2_half_feature()
        sword2_at_start = bool(self.task.find_one(template=half_mat, box=half_box, threshold=0.85))
        duration = min(time_out, 2.2) if sword2_at_start else time_out
        echo_used = False
        start = time.time()
        while time.time() - start < duration:
            self.click(interval=0.1, after_sleep=0.01)
            if use_echo and not echo_used and self.echo_available():
                echo_used = self.click_echo(time_out=0)
            self.check_combat()
            self.task.next_frame()
            if not sword2_at_start and self.task.find_one(
                    template=half_mat, box=half_box, threshold=0.85):
                return True
        self.logger.warning(
            f'cartethyia team normal four used timing fallback sword2_at_start={sword2_at_start}')
        return True

    def perform_team_opening(self):
        """小卡 R1-R2 回到普通形态，随后四段普攻并在其中释放声骸。"""
        if self.is_small():
            if not self.click_liberation(wait_if_cd_ready=0.4):
                return False
            self.is_cartethyia = False
            self.transform = True

        ready = self.task.wait_until(
            self.is_lib_big_available, time_out=2, raise_if_not_found=False)
        if not ready or not self.click_liberation(wait_if_cd_ready=0.4):
            return False
        self.is_cartethyia = True
        self.transform = False
        return self.perform_team_normal_four(use_echo=True)

    def perform_team_resonance_switch(self):
        """确认 E 已按下后立即交由队伍轴切人。"""
        ready = self.task.wait_until(self.resonance_available, time_out=0.5, raise_if_not_found=False)
        if not ready:
            return False
        self.send_resonance_key(after_sleep=0.05)
        self.record_resonance_use()
        return True

    def _perform_team_plunge(self, time_out=2):
        start = time.time()
        was_available = bool(self.is_mid_air_attack_available())
        while time.time() - start < time_out:
            self.task.jump(after_sleep=0.08)
            self.click(interval=0.1)
            available = bool(self.is_mid_air_attack_available())
            if was_available and not available:
                self.sleep(0.35)
                return True
            was_available = was_available or available
            self.task.next_frame()
        self.logger.warning('cartethyia team plunge used timing fallback')
        return True

    def _team_cast_liberation(self, to_small):
        if not self.click_liberation(wait_if_cd_ready=0.5):
            return False
        self.is_cartethyia = to_small
        self.transform = not to_small
        if not to_small:
            self.last_res = -1
        return True

    def _team_fleurdelys_normals_then_lib2(self):
        duration = max(0.5, self.fleurdelys_n4_duration())
        start = time.time()
        while time.time() - start < duration:
            self.click_with_interval()
            self.check_combat()
            self.task.next_frame()

        ready = self.task.wait_until(
            self.is_lib_big_available,
            post_action=self.click_with_interval,
            time_out=1.5,
            raise_if_not_found=False,
        )
        if not ready:
            return False
        return self._team_cast_liberation(to_small=True)

    def _team_acquire_three_swords_and_plunge(self):
        self.perform_team_normal_four()

        self.task.mouse_down()
        start = time.time()
        while time.time() - start < 1.5:
            if self.task.find_one('forte_cartethyia_sword1', threshold=0.9):
                break
            self.task.next_frame()
        self.task.mouse_up()
        self.check_combat()

        self.click_resonance(send_click=False, time_out=1)
        return self._perform_team_plunge()

    def perform_team_final_rotation(self):
        """执行夏空大招后的卡提希娅完整双形态爆发。"""
        self._perform_team_plunge()
        if self.is_small() and not self._team_cast_liberation(to_small=False):
            return False

        self.click_resonance_with_lib_big(allow_lib_big=False)
        if not self._team_fleurdelys_normals_then_lib2():
            return False

        self._team_acquire_three_swords_and_plunge()
        if self.is_small() and not self._team_cast_liberation(to_small=False):
            return False
        return self._team_fleurdelys_normals_then_lib2()

    def is_mid_air_attack_available(self):
        if self.is_cartethyia:
            box = self.task.box_of_screen_scaled(3840, 2160, 2298, 1997, 2361, 2022, name='inner_cartethyia_space',
                                                 hcenter=True)
            self.task.draw_boxes(box.name, box)
            if self.task.calculate_color_percentage(forte_white_color, box) > 0.15:
                cropped = box.crop_frame(self.task.frame)
                gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
                mean_val = np.mean(gray)
                contrast_val = np.std(gray)
                self.logger.debug(f'cartethyia_space mean {mean_val} contrast {contrast_val}')
                return mean_val > 190 and contrast_val < 45

    def try_mid_air_attack(self, timeout=2):
        self.get_sword_buffs()
        if self.liberation_available() or all(self.buffs.values()) or self.try_mid_air_attack_once:
            pass
        else:
            return
        if self.is_mid_air_attack_available():
            self.logger.info('perform mid-air attack')
            start = time.time()
            while True:
                self.task.jump(after_sleep=0.1)
                if self.echo_available():
                    self.click_echo(time_out=0)
                self.task.click(after_sleep=0.1)
                if not self.is_mid_air_attack_available():
                    self.sleep(0.4)
                    break
                if time.time() - start > timeout:
                    break
                self.sleep(0.1)
        elif self.try_mid_air_attack_once:
            start = time.time()
            while time.time() - start < 0.8:
                self.task.jump(after_sleep=0.1)
                if self.echo_available():
                    self.click_echo(time_out=0)
                self.task.click(after_sleep=0.1)
        self.try_mid_air_attack_once = False

    def is_small(self):
        if self.template_shape != self.task.frame.shape[:2]:
            self.init_template()
        self.is_cartethyia = bool(self.task.find_one(template=self.sword3_half_mat,
                                                     box=self.sword3_half_box, threshold=0.5))
        return self.is_cartethyia

    def try_lib_big(self):
        if self.is_lib_big_available():
            if self.click_liberation():
                self.is_cartethyia = True
                self.click_resonance()
                return True

    def is_lib_big_available(self):
        if big := self.task.find_one('lib_cartethyia_big'):
            self.logger.debug('lib cartethyia big available {}'.format(big.confidence))
            self._liberation_available = True
            return True

    def get_sword_buffs(self):
        self.buffs = {
            'sword1': bool(self.task.find_one('forte_cartethyia_sword1', threshold=0.9)),
            'sword2': bool(self.task.find_one('forte_cartethyia_sword2', threshold=0.9)),
            'sword3': bool(self.task.find_one('forte_cartethyia_sword3', threshold=0.9)),
        }
        self.logger.debug(f"buffs {self.buffs}")
        return self.buffs

    def acquire_missing_buffs(self):
        self.get_sword_buffs()
        if all(self.buffs.values()):
            return False
        if has_perform_action := not all(self.buffs[k] for k in ['sword2', 'sword3']):
            self.logger.info('acquire missing buffs')
        if not self.buffs.get('sword2'):
            template = self.task.get_feature_by_name('forte_cartethyia_sword2')
            h = template.mat.shape[0]
            half_mat = template.mat[:int(h * 0.5)]
            half_box = self.task.get_box_by_name('forte_cartethyia_sword2')
            half_box.height = int(h * 0.6)
            time_out = 3.5
            if try_once := bool(self.task.find_one(template=half_mat, box=half_box, threshold=0.85)):
                time_out = 2 if not self.is_first_engage() else 2.5
            start = time.time()
            interrupt_handled = False
            while time.time() - start < time_out:
                if not try_once and self.task.find_one(template=half_mat, box=half_box, threshold=0.85):
                    break
                if not interrupt_handled and self.flying():
                    time_out = 2.5 if time_out == 2 else time_out
                    interrupt_handled = True
                    self.task.wait_until(lambda: not self.flying(), time_out=3)
                    start = time.time()
                self.click(interval=0.1, after_sleep=0.01)
                self.check_combat()
                self.task.next_frame()
            self.logger.debug(f'sword2: click duration {time.time() - start}')
        res = False
        if not self.buffs.get('sword3'):
            res = self.click_resonance()[0]
            self.check_combat()
        if self.liberation_available():
            res and self.sleep(0.2)
        elif has_perform_action:
            return True
        if not self.buffs.get('sword1'):
            if not has_perform_action:
                self.logger.info('acquire missing buffs')
            self.task.mouse_down()
            start = time.time()
            while time.time() - start < 1.5:
                if self.task.find_one('forte_cartethyia_sword1', threshold=0.9):
                    break
                self.task.next_frame()
            self.task.mouse_up()
            self.check_combat()
            self.logger.debug(f'sword1: heavy_att duration {time.time() - start}')
        if not any(self.buffs.values()):
            self.try_mid_air_attack_once = True
        return not self.liberation_available()
