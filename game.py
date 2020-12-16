# -*- coding: utf-8 -*-

# pip install -r requirements.txt

from astrobox.space_field import SpaceField

from hangar_2019.khizhov_d_s import KhizhovDrone
from hangar_2020.kachanov_v_a_package import KachanovDrone
from hangar_2020.kochetov_m_v import KochetovDrone
from hangar_2020.okhotnikov_f_n import OkhotnikovFNDrone

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
    team4 = [KachanovDrone() for _ in range(NUMBER_OF_DRONES)]

    scene.go()

# Первый этап: зачёт!
