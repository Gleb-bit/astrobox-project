# -*- coding: utf-8 -*-

# pip install -r requirements.txt

from astrobox.space_field import SpaceField
from khizhov_d_s import KhizhovDrone
from surkova_e_n import SurkovaDrone
from kochetov_m_v import KochetovDrone
from kharitonov import KharitonovDrone
from zhukov_i_p import ZhukovDrone
from ishmukhamedov_a_r import IshmukhamedovDrone
from sivkov_a_v import SivkovDrone
from okhotnikov_f_n import OkhotnikovFNDrone
from vinogradov import VinogradovDrone
from ilyin_e_i import IlyinDrone
from devastator import DevastatorDrone


NUMBER_OF_DRONES = 5


if __name__ == '__main__':
    scene = SpaceField(
        field=(1200, 1200),
        speed=5,
        asteroids_count=10,
        can_fight=True,
    )
    team1 = [OkhotnikovFNDrone() for _ in range(NUMBER_OF_DRONES)]
    team2 = [KhizhovDrone() for _ in range(NUMBER_OF_DRONES)]
    team3 = [KochetovDrone() for _ in range(NUMBER_OF_DRONES)]
    team4 = [SivkovDrone() for _ in range(NUMBER_OF_DRONES)]
    scene.go()

# Первый этап: зачёт!
