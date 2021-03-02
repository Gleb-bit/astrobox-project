# -*- coding: utf-8 -*-
from math import acos, degrees
from abc import ABC, abstractmethod

from astrobox.core import Drone, Unit
import logging

from robogame_engine.geometry import Point, Vector


# logging.basicConfig(filename='my_drone.log', filemode='w', level=logging.INFO)


class GnatDrone(Drone):
    my_team = []
    empty_distance = 0
    full_distance = 0
    partial_distance = 0
    DANGER_DISTANCE_TO_BASE = 100

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = None
        self._strategy = Collector()
        self.attack_range = self.gun.shot_distance
        self.asteroid_to_collect = None
        self.target = None
        self.victim = None
        self.previous_health = 1

    @property
    def strategy(self):
        return self._strategy

    @strategy.setter
    def strategy(self, strategy) -> None:
        self._strategy = strategy

    def on_born(self):
        self.name = len(self.my_team)
        self.my_team.append(self)
        self.asteroid_to_collect = self._get_my_asteroid()
        self.target = self.asteroid_to_collect
        self.measure_distance()
        self.move_at(self.target)

    def _get_my_asteroid(self):
        best_asteroids = []
        not_collecting_asteroids = []
        for asteroid in self.asteroids:
            if not asteroid.is_empty:
                for drone in self.my_team:
                    if drone.target is asteroid:
                        break
                else:
                    not_collecting_asteroids.append(asteroid)
                    if asteroid.payload >= self.free_space:
                        best_asteroids.append(asteroid)
        if best_asteroids:
            best_asteroid = min([(self.distance_to(asteroid), asteroid) for asteroid in best_asteroids])[1]
        else:
            if not_collecting_asteroids:
                best_asteroid = min([(self.distance_to(aster), aster) for aster in not_collecting_asteroids])[1]
            else:
                return self.my_mothership
        return best_asteroid

    def on_stop_at_asteroid(self, asteroid):
        # if asteroid.payload == 0:
        #     self.target = self._get_my_asteroid()
        if asteroid.payload > self.free_space:
            self.target = self.my_mothership
        else:
            self.target = self._get_my_asteroid()
        self.turn_to(self.target)
        self.load_from(asteroid)

    def on_load_complete(self):
        if not self.is_full:
            self.target = self._get_my_asteroid()
        else:
            self.target = self.my_mothership
        self.measure_distance()
        self.move_at(self.target)

    def on_stop_at_mothership(self, mothership):
        if mothership is self.my_mothership:
            if isinstance(self.target, Unit):
                if self.target.is_empty:
                    self.target = self._get_my_asteroid()
            self.turn_to(self.asteroids[0])
            self.unload_to(mothership)
        else:
            self.load_from(mothership)

    def on_unload_complete(self):
        free_elerium = sum([asteroid.payload for asteroid in self.scene.asteroids])
        if not free_elerium:
            self.strategy = Military()
        else:
            self.target = self._get_my_asteroid()
            self.move_at(self.target)

        self.strategy.act(self)

        self.measure_distance()

    def on_wake_up(self):
        if isinstance(self.strategy, Collector):
            self.target = self._get_my_asteroid()
            if self.target is self.my_mothership:
                self.strategy = Military()
        self.strategy.act(self)

    def on_heartbeat(self):
        current_health = self.meter_2
        if current_health < 0.5:
            self.strategy = Mover()
            self.target = self.my_mothership
            self.strategy.act(self)
            return

        if self.on_position():
            self.strategy = Military()
        else:
            self.strategy = Collector()
        self.strategy.act(self)

    def on_position(self):
        if round(self.coord.x) == self.target.x and round(self.coord.y) == self.target.y \
                and isinstance(self.target, Point):
            return True
        return False

    def measure_distance(self):
        if self.is_full:
            self.full_distance += int(self.distance_to(self.target))
        elif self.is_empty:
            self.empty_distance += int(self.distance_to(self.target))
        else:
            self.partial_distance += int(self.distance_to(self.target))
        # logging.info(f'{self.name} - {self.empty_distance} - {self.partial_distance} - {self.full_distance}')

    def on_stop_at_point(self, target):
        pass


class Strategy(ABC):

    @abstractmethod
    def act(self, drone):
        pass


class Collector(Strategy):

    def act(self, drone):
        # collect
        if drone.fullness == 1 or drone.asteroid_to_collect.is_empty:
            drone.move_at(drone.target)


class Military(Strategy):

    def act(self, drone):
        # attack
        if drone.target is None or (drone.target is drone.my_mothership and drone.fullness == 0):
            drone.target = self.get_attack_point(drone)
        if drone.on_position():
            self.attack(drone)
        else:
            drone.move_at(drone.target)

    def attack(self, drone, victim=None):
        if victim is None:
            drone.victim = self.get_victim(drone)
            if drone.distance_to(drone.mothership) <= drone.DANGER_DISTANCE_TO_BASE:
                drone.target = self.get_attack_point(drone)
                drone.move_at(drone.target)
                return

            if drone.victim:
                self.shoot(drone, drone.victim)
            else:
                self.collect_from_destroyed()
        else:
            self.shoot(drone, victim)

    def get_attack_point(self, drone, base=False):  # TODO
        if base:
            base_target = self.surround_base(drone)
            if base_target:
                return base_target
        defend_coord = self.get_coord(drone, drone.my_mothership)
        return Point(drone.my_mothership.coord.x + defend_coord[0], drone.my_mothership.coord.y + defend_coord[1])

    def shoot(self, drone, victim):
        drone.turn_to(victim)
        if drone.distance_to(victim) > drone.attack_range \
                or abs(self.get_angle_Ox(drone, victim) - drone.direction) > 5:  # TODO
            return
        for partner in drone.my_team:
            if partner is drone or not partner.is_alive:
                continue
            if partner.near(victim) \
                    or (self.get_angle(drone, partner, victim) < 20
                        and drone.distance_to(partner) < drone.distance_to(victim)):
                return
        drone.gun.shot(victim)

    def get_victim(self, drone):
        enemies = [d for d in drone.scene.drones if (d not in drone.my_team and d.is_alive)
                   and not d.near(d.mothership)]
        enemies_bases = [base for base in drone.scene.motherships if
                         (base is not drone.my_mothership and base.is_alive)]

        if enemies:
            nearest_enemy = sorted([(drone.distance_to(enemy), enemy) for enemy in enemies], key=lambda x: x[0])[0]
            if nearest_enemy[0] <= drone.attack_range:
                return nearest_enemy[1]
        if enemies_bases:
            nearest_enemy_base = sorted([(drone.distance_to(enemy), enemy)
                                         for enemy in enemies_bases], key=lambda x: x[0])[0]
            return nearest_enemy_base[1]
        return None

    def surround_base(self, drone):
        enemies_bases = [base for base in drone.scene.motherships if
                         (base is not drone.my_mothership and base.is_alive)]
        base_to_attack = max([(base.payload, base) for base in enemies_bases], key=lambda x: x[0])[1]
        if base_to_attack.payload < (drone.my_mothership.payload * 0.95):
            return

        defend_coord = self.get_coord(drone, base_to_attack)
        return Point(base_to_attack.coord.x + defend_coord[0], base_to_attack.coord.y + defend_coord[1])

    def get_coord(self, drone, base):
        defend_coords = [[130, 40], [40, 130], [110, 110], [-40, 180], [180, -40]]
        defend_coord = defend_coords[drone.name]

        if base.coord.x > 90:
            defend_coord[0] *= -1
        if base.coord.y > 90:
            defend_coord[1] *= -1
        return defend_coord

    def who_is_fire(self, drone):
        enemy_drones = [drone for drone in drone.scene.drones
                        if drone not in drone.my_team and drone.have_gun and drone.is_alive]
        candidats = []
        for drone in enemy_drones:
            if drone.gun_cooldown >= 0:
                candidats.append([drone, drone.gun_cooldown])
        if candidats:
            self.shoot(drone, candidats[0][0])

    def get_angle(self, drone, partner, victim):
        def scalar(v1, v2):
            return v1.x * v2.x + v1.y * v2.y

        to_partner = Vector(partner.x - drone.x, partner.y - drone.y)
        to_victim = Vector(victim.x - drone.x, victim.y - drone.y)
        cos_partner_victim = scalar(to_partner, to_victim) / (to_partner.module * to_victim.module)
        return degrees(acos(cos_partner_victim))

    def get_angle_Ox(self, drone, victim):
        def scalar(v1, v2):
            return v1.x * v2.x + v1.y * v2.y

        v1 = Vector(victim.x - drone.x, victim.y - drone.y)
        v2 = Vector(1200, 0)

        cos = scalar(v1, v2) / (v1.module * v2.module)
        return degrees(acos(cos))

    def collect_from_destroyed(self):
        pass


class Mover(Strategy):

    def act(self, drone):
        # move_at
        drone.move_at(drone.target)


drone_class = GnatDrone
