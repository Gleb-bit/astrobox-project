# -*- coding: utf-8 -*-
from random import randint

from astrobox.core import Drone, MotherShip
from astrobox.themes.default import FIELD_HEIGHT, FIELD_WIDTH, MOTHERSHIP_HEALING_DISTANCE
from robogame_engine.geometry import Point


class FominDrone(Drone):
    SAFE_DISTANCE = 85
    CENTER_X = FIELD_WIDTH // 2
    CENTER_Y = FIELD_HEIGHT // 2
    OFFSET = [(70, -200), (-50, -130), (-140, -140), (-160, -50), (-160, 40),
              (-FIELD_WIDTH + 180, 30), (-10, -FIELD_HEIGHT + 150)]
    START_COORD = []
    CENTER_COORD = []
    NEW_COORD = []

    limit_health = 62
    my_team = []

    def __init__(self):
        super().__init__()
        self.target_object = None
        self.dist_to_object = None
        self.curr_position = None
        self.type = None

    def __prepare_center_coord(self):
        for i in range(-3, 4):
            coord = (FominDrone.CENTER_X, FominDrone.CENTER_Y + i * FominDrone.SAFE_DISTANCE)
            if coord not in FominDrone.CENTER_COORD:
                FominDrone.CENTER_COORD.append(coord)

    def __prepare_static_coord(self):
        div_x = 1
        div_y = 1
        if self.my_mothership.coord.x <= self.CENTER_X and self.my_mothership.coord.y <= self.CENTER_Y:
            div_x = -1
            div_y = -1
        elif self.my_mothership.coord.x > self.CENTER_X and self.my_mothership.coord.y <= self.CENTER_Y:
            div_y = -1
        elif self.my_mothership.coord.x <= self.CENTER_X and self.my_mothership.coord.y > self.CENTER_Y:
            div_x = -1

        for offset in FominDrone.OFFSET:
            x = self.my_mothership.coord.x + offset[0] * div_x
            y = self.my_mothership.coord.y + offset[1] * div_y
            if (x, y) not in FominDrone.START_COORD:
                FominDrone.START_COORD.append((x, y))

    @property
    def count_enemies(self):
        enemies = [1 for drone in self.scene.drones if self.team != drone.team and drone.is_alive]
        return len(enemies)

    @property
    def safe_distance(self):
        return self.SAFE_DISTANCE

    def _get_static_base_coord(self):
        self.__prepare_static_coord()
        coord = self.START_COORD[self.my_team.index(self)]
        position = Point(coord[0], coord[1])
        return position

    def _get_all_targets(self):
        all_enemies = [(drone, self.distance_to(drone), 'fire') for drone in self.scene.drones if
                       self.team != drone.team and drone.is_alive]
        bases = [(base, self.distance_to(base), 'fire') for base in self.scene.motherships if
                 base.team != self.team and base.is_alive]
        all_enemies.sort(key=lambda x: x[1])
        bases.sort(key=lambda x: x[1])
        all_enemies.extend(bases)

        asteroids = [(mothership, self.distance_to(mothership), 'collect') for mothership in self.scene.motherships
                     if not mothership.is_alive and not mothership.is_empty]
        asteroids.extend([(asteroid, self.distance_to(asteroid), 'collect') for asteroid in self.scene.asteroids
                          if not asteroid.is_empty])
        asteroids.sort(key=lambda x: x[1])
        asteroids.extend([(drone, self.distance_to(drone), 'collect') for drone in self.scene.drones
                          if not drone.is_alive and not drone.is_empty])

        all_enemies.extend(asteroids)

        if all_enemies:
            return all_enemies
        return None

    def is_crossfire(self, target):
        crossfire = []
        for teammate in self.my_team:
            if teammate != self:
                x, y = teammate.coord.x, teammate.coord.y
                x1, y1 = self.coord.x, self.coord.y
                x2, y2 = target.coord.x, target.coord.y

                dx1 = x2 - x1
                dy1 = y2 - y1
                dx = x - x1
                dy = y - y1
                S = int(dx1 * dy - dx * dy1)
                ab = (dx1 * dx1 + dy1 * dy1) ** 0.5
                h = int(abs(S / ab))

                if h < self.safe_distance * 0.45:
                    crossfire.append(True)
                else:
                    crossfire.append(False)

        return any(crossfire)

    def move_to(self, target):
        self.turn_to(target)
        self.move_at(target)

    def fire_action(self, target, distance):
        if self.count_enemies <= 2 and len(FominDrone.NEW_COORD) != len(self.my_team):
            coord = FominDrone.CENTER_COORD[self.my_team.index(self)]
            position = Point(coord[0], coord[1])
            if position not in FominDrone.NEW_COORD:
                self.curr_position = position
                FominDrone.NEW_COORD.append(position)
                self.move_to(position)
        elif target:
            self.turn_to(target)
            self.shoot(target)

    def defend_strategy(self):
        try:
            targets = self._get_all_targets()
            for target in targets:
                if not self.is_crossfire(target[0]) and target[-1] == 'fire':
                    self.target_object, self.dist_to_object, self.type = target
                    break
            else:
                self.target_object, self.dist_to_object, self.type = targets[0]

        except TypeError:
            self.target_object = None
            self.type = 'collect'
            self.move_to(self.my_mothership)

        else:
            if (self.health < self.limit_health
                    and self.distance_to(self.my_mothership) > MOTHERSHIP_HEALING_DISTANCE + 100):
                self.move_to(self.my_mothership)
                return

            if self.type == 'fire':
                self.fire_action(self.target_object, self.dist_to_object)
                return

            if self.type == 'collect':
                self.move_to(self.target_object)
                return

    def on_born(self):
        self.__prepare_center_coord()
        self.my_team.append(self)
        self.limit_health = FominDrone.limit_health
        self.curr_position = self._get_static_base_coord()
        self.move_to(self.curr_position)

    def shoot(self, object):
        self.turn_to(object)
        self.gun.shot(object)

    def on_stop_at_asteroid(self, asteroid):
        if self.type == 'collect':
            self.load_from(asteroid)
        else:
            self.defend_strategy()

    def on_load_complete(self):
        if self.is_full:
            self.move_to(self.my_mothership)
        else:
            self.defend_strategy()

    def on_stop_at_mothership(self, mothership):
        if self.type == 'collect':
            if mothership == self.my_mothership:
                self.unload_to(mothership)
            else:
                self.load_from(mothership)
        else:
            self.move_to(self.curr_position)

    def on_unload_complete(self):
        if self.target_object:
            self.defend_strategy()

    def on_stop_at_point(self, target):
        if self.type == 'collect':
            self.load_from(self.target_object)
        else:
            self.defend_strategy()

    def stop(self):
        self.defend_strategy()

    def on_stop(self):
        self.defend_strategy()

    def on_wake_up(self):
        self.defend_strategy()


drone_class = FominDrone
