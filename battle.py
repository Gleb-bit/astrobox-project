# -*- coding: utf-8 -*-

from astrobox.space_field import SpaceField

from hangar_2019.ishmukhamedov import drone_class as Drone1
from hangar_2019.kharitonov import drone_class as Drone2
from hangar_2019.vinogradov import drone_class as Drone3
# from hangar_2019.marchenko import drone_class as Drone4


NUMBER_OF_DRONES = 5

if __name__ == '__main__':
    scene = SpaceField(
        speed=15,
        field=(1200, 600),
        asteroids_count=50,
        headless=True,
    )
    team_1 = [Drone1() for _ in range(NUMBER_OF_DRONES)]
    team_2 = [Drone2() for _ in range(NUMBER_OF_DRONES)]
    team_3 = [Drone3() for _ in range(NUMBER_OF_DRONES)]
    # team_4 = [Drone4() for _ in range(NUMBER_OF_DRONES)]
    scene.go()
