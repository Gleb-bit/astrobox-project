# -*- coding: utf-8 -*-

# pip install -r requirements.txt

from astrobox.space_field import SpaceField
from hangar_2020.martynov_v_l import MartynovDrone
from hangar_2020.okhotnikov_f_n import OkhotnikovFNDrone
from hangar_2020.kochetov_m_v import KochetovDrone
from hangar_2020.ilyin_e_i import IlyinDrone
# from hangar_2020.khizhov_d_s import KhizhovDrone
# from hangar_2020.glazov_v_s import GlazovDrone
# from vader import VaderDrone
# from stage_04_soldiers.devastator import DevastatorDrone
# from hangar_2020.pestov_m_e import PestovDrone
# from hangar_2020.vorobyev_v_s import VorobyevDrone

NUMBER_OF_DRONES = 5
# TEST COMMIT
if __name__ == '__main__':
    scene = SpaceField(
        field=(1200, 1200),
        speed=15,
        asteroids_count=15,
        can_fight=True,
        # headless=not False
    )

    # 1 этап
    # 202 - IlyinDrone /dead/
    # 200 - DevastatorDrone /dead/
    # 100 - KochetovDrone
    # 0 - MartynovDrone

    # team_1 = [IlyinDrone() for _ in range(NUMBER_OF_DRONES)]
    # team_2 = [DevastatorDrone() for _ in range(NUMBER_OF_DRONES)]
    # team_3 = [KochetovDrone() for _ in range(NUMBER_OF_DRONES)]
    # team_4 = [MartynovDrone() for _ in range(NUMBER_OF_DRONES)]

    # 2 этап
    # 102 - MartynovDrone
    # 0 - GlazovDrone /dead/
    # 0 - DevastatorDrone /dead/
    # 0 - VorobyevDrone /dead/

    # team_1 = [MartynovDrone() for _ in range(NUMBER_OF_DRONES)]
    # team_2 = [GlazovDrone() for _ in range(NUMBER_OF_DRONES)]
    # team_3 = [DevastatorDrone() for _ in range(NUMBER_OF_DRONES)]
    # team_4 = [VorobyevDrone() for _ in range(NUMBER_OF_DRONES)]

    # 3 этап

    # 100 - IlyinDrone /dead/
    # 100 - DevastatorDrone /dead/
    # 100 - KhizhovDrone /dead/
    # 0 - MartynovDrone

    # team_1 = [IlyinDrone() for _ in range(NUMBER_OF_DRONES)]
    # team_2 = [DevastatorDrone() for _ in range(NUMBER_OF_DRONES)]
    # team_3 = [KhizhovDrone() for _ in range(NUMBER_OF_DRONES)]
    # team_4 = [MartynovDrone() for _ in range(NUMBER_OF_DRONES)]

    # 4 этап
    # 423 - IlyinDrone /dead/
    # 233 - OkhotnikovFNDrone /dead/
    # 100 - GlazovDrone /dead/
    # 0 - MartynovDrone

    team_4 = [IlyinDrone() for _ in range(NUMBER_OF_DRONES)]
    team_2 = [OkhotnikovFNDrone() for _ in range(NUMBER_OF_DRONES)]
    team_3 = [KochetovDrone() for _ in range(NUMBER_OF_DRONES)]
    team_1 = [MartynovDrone() for _ in range(NUMBER_OF_DRONES)]

    # 4 этап
    # 256 - IlyinDrone /dead/
    # 213 - MartynovDrone /dead/
    # 100 - DevastatorDrone /dead/
    # 0 - KhizhovDrone /dead/

    # team_1 = [IlyinDrone() for _ in range(NUMBER_OF_DRONES)]
    # team_2 = [MartynovDrone() for _ in range(NUMBER_OF_DRONES)]
    # team_3 = [DevastatorDrone() for _ in range(NUMBER_OF_DRONES)]
    # team_4 = [KhizhovDrone() for _ in range(NUMBER_OF_DRONES)]

    # 5 этап
    # 1399 - PestovDrone
    # 0 - MartynovDrone /dead/

    # team_1 = [PestovDrone() for _ in range(NUMBER_OF_DRONES)]
    # team_2 = [MartynovDrone() for _ in range(NUMBER_OF_DRONES)]

    scene.go()

# зачёт!
