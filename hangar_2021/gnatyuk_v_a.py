# -*- coding: utf-8 -*-
from math import acos, degrees
from abc import ABC, abstractmethod

from astrobox.core import Drone, Unit
import logging

from robogame_engine.geometry import Point, Vector
from stage_04_soldiers.devastator import DevastatorDrone

logging.basicConfig(filename='my_drone.log', filemode='w', level=logging.INFO)


class GnatDrone(Drone):
    my_team = []
    empty_distance = 0
    full_distance = 0
    partial_distance = 0
    DANGER_DISTANCE_TO_BASE = 100

    def __init__(self, name, **kwargs):
        super().__init__(**kwargs)
        self.name = name
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
        self.my_team.append(self)
        self.asteroid_to_collect = self._get_my_asteroid()
        self.target = self.asteroid_to_collect
        self.measure_distance()
        self.move_at(self.target)

    def attack(self, victim=None):
        if victim is None:
            self.victim = self.get_victim()
            if self.distance_to(self.mothership) <= self.DANGER_DISTANCE_TO_BASE:
                self.target = self.get_attack_point()
                self.move_at(self.target)
                return

            devastators = [drone for drone in self.scene.drones if
                           drone.is_alive and isinstance(drone, DevastatorDrone)]
            if len(devastators) < 3:  # TODO возможно нужно добавить проверку на стейт у девастаторов
                for devastator in devastators:
                    if self.distance_to(devastator) < self.attack_range:
                        # self.victim = devastator
                        # break
                        self.shoot(devastator)
                        return
                else:
                    self.target = self.get_attack_point(base=True)
                if round(self.x) == self.target.x and round(self.y) == self.target.y:
                    self.shoot(self.victim)
                return

            if self.victim:
                self.shoot(self.victim)
            else:
                self.collect_from_destroyed()
        else:
            self.shoot(victim)

    def get_attack_point(self, base=False):  # TODO
        if base:
            base_target = self.surround_base()
            if base_target:
                return base_target
        defend_coord = self.get_coord(self.my_mothership)
        return Point(self.my_mothership.coord.x + defend_coord[0], self.my_mothership.coord.y + defend_coord[1])

    def shoot(self, victim):
        self.turn_to(victim)
        if self.distance_to(victim) >= self.attack_range:
            return
        for partner in self.my_team:
            if partner is self:
                continue
            if (partner.near(victim) and partner.is_alive) or \
                    (self.get_angle(partner, victim) < 20 and self.distance_to(partner) < self.distance_to(victim)):
                return
        self.gun.shot(victim)

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
                    if asteroid.payload >= 90:
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
        if asteroid.payload == 0:
            return
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
        if self.name < 2:
            self.strategy = Military()
            print('now im military')
            self.target = self.get_attack_point()
        else:
            self.target = self._get_my_asteroid()

        self.measure_distance()
        self.move_at(self.target)

    def on_wake_up(self):
        if isinstance(self.strategy, Collector):
            self.target = self._get_my_asteroid()
            if self.target is self.my_mothership:
                self.strategy = Military()
                print('now im military')
        self.strategy.act(self)

    def on_heartbeat(self):
        current_health = self.meter_2
        if current_health < 0.5:
            self.strategy = Mover()
            self.target = self.my_mothership
            return

        if self.target is None:
            self.target = self.get_attack_point()

        if round(self.coord.x) == self.target.x and round(self.coord.y) == self.target.y \
                and isinstance(self.target, Point):
            self.strategy = Military()
        else:
            self.strategy = Collector()
        self.strategy.act(self)

    def measure_distance(self):
        if self.is_full:
            self.full_distance += int(self.distance_to(self.target))
        elif self.is_empty:
            self.empty_distance += int(self.distance_to(self.target))
        else:
            self.partial_distance += int(self.distance_to(self.target))
        logging.info(f'{self.name} - {self.empty_distance} - {self.partial_distance} - {self.full_distance}')

    def collect_from_destroyed(self):
        pass

    def on_stop_at_point(self, target):
        pass

    def get_victim(self):
        enemies = [drone for drone in self.scene.drones if (drone not in self.my_team and drone.is_alive)]
        enemies_bases = [base for base in self.scene.motherships if (base is not self.my_mothership and base.is_alive)]
        enemies.extend(enemies_bases)
        distance_to_enemies = sorted([(self.distance_to(enemy), enemy) for enemy in enemies], key=lambda x: x[0])[0]
        if enemies:
            victim = distance_to_enemies[1]
            return victim
        return None

    def surround_base(self):
        enemies_bases = [base for base in self.scene.motherships if (base is not self.my_mothership and base.is_alive)]
        base_to_attack = max([(base.payload, base) for base in enemies_bases], key=lambda x: x[0])[1]
        if base_to_attack.payload < (self.my_mothership.payload * 0.95):
            return
            # self.target = self.get_attack_point()
            # return self.target

        defend_coord = self.get_coord(base_to_attack)
        return Point(base_to_attack.coord.x + defend_coord[0], base_to_attack.coord.y + defend_coord[1])

    def get_coord(self, base):
        defend_coords = [[130, 40], [40, 130], [110, 110], [-40, 180], [180, -40]]
        defend_coord = defend_coords[self.name]

        if base.coord.x > 90:
            defend_coord[0] *= -1
        if base.coord.y > 90:
            defend_coord[1] *= -1
        return defend_coord

    def who_is_fire(self):
        enemy_drones = [drone for drone in self.scene.drones
                        if drone not in self.my_team and drone.have_gun and drone.is_alive]
        candidats = []
        for drone in enemy_drones:
            if drone.gun_cooldown >= 0:
                candidats.append([drone, drone.gun_cooldown])
        if candidats:
            self.shoot(candidats[0][0])

    def get_angle(self, partner, victim):
        def scalar(v1, v2):
            return v1.x * v2.x + v1.y * v2.y

        to_partner = Vector(partner.x - self.x, partner.y - self.y)
        to_victim = Vector(victim.x - self.x, victim.y - self.y)
        cos_partner_victim = scalar(to_partner, to_victim) / (to_partner.module * to_victim.module)
        return degrees(acos(cos_partner_victim))


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
        drone.attack()


class Mover(Strategy):

    def act(self, drone):
        # move_at
        drone.move_at(drone.target)


drone_class = GnatDrone
