# -*- coding: utf-8 -*-
from collections import defaultdict

from astrobox.core import *
from abc import ABC, abstractmethod
from astrobox.themes.default import MOTHERSHIP_HEALING_DISTANCE
from robogame_engine.geometry import Point, Vector

theme.FIELD_WIDTH = 1200
theme.FIELD_HEIGHT = 1200


class Strategy(ABC):
    half_width_x = theme.FIELD_WIDTH / 2
    half_height_y = theme.FIELD_HEIGHT / 2

    def __init__(self, drone_ref):
        self.drone_ref = drone_ref
        self.asteroid = None
        self.label_angle = None
        self.state_retreat = None

        self.actions_mapping = {
            "on_born": self.on_born,
            "on_stop_at_asteroid": self.on_stop_at_asteroid,
            "on_load_complete": self.on_load_complete,
            "on_stop_at_mothership": self.on_stop_at_mothership,
            "on_unload_complete": self.on_unload_complete,
            "on_stop_at_point": self.on_stop_at_point,
            "on_hearbeat": self.on_hearbeat,
            "on_stop": self.on_stop,
            "on_wake_up": self.on_wake_up
        }

    def implement_strategy(self, message, **kwargs):
        self.actions_mapping[message](**kwargs)

    @abstractmethod
    def on_born(self, **kwargs):
        pass

    @abstractmethod
    def on_stop_at_asteroid(self, **kwargs):
        pass

    @abstractmethod
    def on_load_complete(self, **kwargs):
        pass

    @abstractmethod
    def on_stop_at_mothership(self, **kwargs):
        pass

    @abstractmethod
    def on_unload_complete(self, **kwargs):
        pass

    @abstractmethod
    def on_stop_at_point(self, **kwargs):
        pass

    @abstractmethod
    def on_hearbeat(self, **kwargs):
        pass

    @abstractmethod
    def on_stop(self, **kwargs):
        pass

    @abstractmethod
    def on_wake_up(self, **kwargs):
        pass

    def get_count_of_enemies_without_turrets(self):
        enemies = [drone for drone in self.drone_ref.scene.drones if
                   drone.team != self.drone_ref.team and drone.is_alive]
        enemy_count = len([1 for drone in enemies if not Strategy.is_drone_turret(drone)])
        Strategy.enemy_count = enemy_count
        return enemy_count

    @staticmethod
    def is_drone_turret(drone):
        """
        Если у вражеского дрона космобаза уничтожена, то он турелью быть не может.
        """
        if drone.my_mothership.is_alive:
            dist = drone.distance_to(drone.my_mothership)
            if dist <= MOTHERSHIP_HEALING_DISTANCE + 50:
                return True
            else:
                return False
        else:
            return False

    def get_count_of_enemies_all(self):
        enemies = [drone for drone in self.drone_ref.scene.drones if
                   drone.team != self.drone_ref.team and drone.is_alive]
        enemy_count = len([1 for enemy in enemies])
        Defender.enemy_count = enemy_count
        return enemy_count


class Collector(Strategy):
    asteroid_visit_attempts = defaultdict()

    def on_born(self, **kwargs):
        self.drone_ref.target = self.get_nearest_asteroid_or_mothership()
        self.drone_ref.move_at(self.drone_ref.target)
        pass

    def on_stop_at_asteroid(self, **kwargs):
        self.drone_ref.load_from(self.drone_ref.target)
        self.check_if_asteroid_payload_enough_for_ship(self.drone_ref.target)

    def on_load_complete(self, **kwargs):
        if not self.drone_ref.is_full:
            self.drone_ref.target = self.get_the_asteroid_for_effective_cargo_fulfill()
            self.drone_ref.move_at(self.drone_ref.target)
        else:
            self.drone_ref.target = self.drone_ref.my_mothership
            self.drone_ref.move_at(self.drone_ref.target)

    def on_stop_at_mothership(self, **kwargs):
        if self.drone_ref.target:
            if self.drone_ref.team != self.drone_ref.target.team:
                self.drone_ref.load_from(self.drone_ref.target)
            else:
                self.drone_ref.unload_to(self.drone_ref.my_mothership)
                self.drone_ref.target = self.get_nearest_asteroid_or_mothership()
                self.drone_ref.turn_to(self.drone_ref.target)

    def on_unload_complete(self, **kwargs):
        if self.drone_ref.target is not None:
            self.drone_ref.move_at(self.drone_ref.target)

    def on_stop_at_point(self, **kwargs):
        pass

    @staticmethod
    def update_asteroid_visit(asteroid):
        if asteroid.coord not in Collector.asteroid_visit_attempts.keys():
            Collector.asteroid_visit_attempts[asteroid.coord] = 1
        else:
            Collector.asteroid_visit_attempts[asteroid.coord] += 1

    def get_nearest_asteroid_or_mothership(self):

        team_targets = [tmmate.target for tmmate in self.drone_ref.teammates if isinstance(tmmate.target, Asteroid)]

        dists = []
        for asteroid in self.drone_ref.asteroids:
            if (asteroid.payload > 0 and 0 < self.drone_ref.distance_to(asteroid)) and asteroid not in team_targets \
                    and Collector.asteroid_visit_attempts.get(asteroid.coord, 0) < 3:
                dists.append((asteroid, self.drone_ref.distance_to(asteroid)))

        dists_mships = []
        for mship in self.drone_ref.scene.motherships:
            if mship.payload > 0 and 0 < self.drone_ref.distance_to(mship) and not mship.is_alive:
                dists_mships.append((mship, self.drone_ref.distance_to(mship)))

        dists.extend(dists_mships)

        if len(dists):
            sorted_dists = sorted(dists, key=lambda x: x[1])
            if len(sorted_dists) > 0:
                asteroid = sorted_dists[0][0]
                Collector.update_asteroid_visit(asteroid)
                return asteroid

            else:
                return self.get_the_remnant_from_current_position()
        else:
            return self.get_the_remnant_from_current_position()

    def get_the_asteroid_for_effective_cargo_fulfill(self):
        team_targets = [teammate.target for teammate in self.drone_ref.teammates if
                        isinstance(teammate.target, Asteroid)]

        dists = []
        for asteroid in self.drone_ref.asteroids:
            if (asteroid.payload > 0 and 0 < self.drone_ref.distance_to(asteroid)) and asteroid not in team_targets \
                    and Collector.asteroid_visit_attempts.get(asteroid.coord, 0) < 3:
                dists.append((asteroid, self.drone_ref.distance_to(asteroid) +
                              asteroid.distance_to(self.drone_ref.my_mothership)))

        if len(dists):
            asteroid = sorted(dists, key=lambda x: x[1])[0][0]
            Collector.update_asteroid_visit(asteroid)
            return asteroid
        else:
            return self.get_the_remnant_from_current_position()

    def check_if_asteroid_payload_enough_for_ship(self, asteroid):
        if self.drone_ref.payload + asteroid.payload >= 100:
            self.drone_ref.turn_to(self.drone_ref.my_mothership)
        else:
            self.drone_ref.target = self.get_the_asteroid_for_effective_cargo_fulfill()

    def get_the_remnant_from_current_position(self):
        """
        если хоть что-то осталось на карте, и это недалеко от корабля с местом в трюме, то летим к нему
        опять-таки проверяем, что этот астероид не занят никем;
        """
        team_targets = [teammate.target for teammate in self.drone_ref.teammates if
                        isinstance(teammate.target, Asteroid)]

        dists = []
        for asteroid in self.drone_ref.asteroids:
            if (asteroid.payload > 0 and 0 < self.drone_ref.distance_to(asteroid)) and asteroid not in team_targets \
                    and Collector.asteroid_visit_attempts.get(asteroid.coord, 0) < 3:
                dists.append((asteroid, self.drone_ref.distance_to(asteroid)))

        if len(dists):
            asteroid = sorted(dists, key=lambda x: x[1])[0][0]
            Collector.update_asteroid_visit(asteroid)
            return asteroid
        else:
            return self.drone_ref.my_mothership

    def on_stop(self, **kwargs):
        self.on_wake_up()

    def on_hearbeat(self, **kwargs):
        self.return_for_heal()

    def on_wake_up(self, **kwargs):
        self.drone_ref.target = self.get_nearest_asteroid_or_mothership()
        self.drone_ref.move_at(self.drone_ref.target)

    def return_for_heal(self):
        if self.drone_ref.health < 75:
            if self.drone_ref.my_mothership:
                point_mothership = Point(self.drone_ref.my_mothership.coord.x, self.drone_ref.my_mothership.coord.y)
                self.drone_ref.move_at(point_mothership)


class Defender(Strategy):
    composition = {1: (0, 280),
                   2: (70, 240),
                   3: (140, 140),
                   4: (210, 70),
                   5: (280, 0)}

    selected_aim = None
    enemy_count = 0

    def take_start_position(self):
        x, y = Defender.composition[self.drone_ref.serial_number]

        if self.drone_ref.label_angle == 'angle#1':
            x, y = self.drone_ref.my_mothership.x + x, self.drone_ref.my_mothership.y + y
        elif self.drone_ref.label_angle == 'angle#2':
            x, y = self.drone_ref.my_mothership.x + x, self.drone_ref.my_mothership.y - y
        elif self.drone_ref.label_angle == 'angle#3':
            x, y = self.drone_ref.my_mothership.x - x, self.drone_ref.my_mothership.y - y
        elif self.drone_ref.label_angle == 'angle#4':
            x, y = self.drone_ref.my_mothership.x - x, self.drone_ref.my_mothership.y + y

        point_start = Point(x, y)
        self.drone_ref.move_at(point_start)

    def on_born(self, **kwargs):
        self.take_start_position()
        self.drone_ref.target = self.get_aim_for_shooting()

    def on_stop_at_asteroid(self, **kwargs):
        self.next_action()

    def on_load_complete(self, **kwargs):
        self.next_action()

    def on_stop_at_mothership(self, **kwargs):
        self.next_action()

    def on_unload_complete(self, **kwargs):
        self.next_action()

    def on_stop_at_point(self, **kwargs):
        self.next_action()

    def on_stop(self, **kwargs):
        self.next_action()

    def on_hearbeat(self, **kwargs):
        self.return_for_heal()

    def on_wake_up(self, **kwargs):
        self.next_action()

    def return_for_heal(self):
        if self.drone_ref.health < 50:
            point_mothership = Point(self.drone_ref.my_mothership.x, self.drone_ref.my_mothership.y)
            self.drone_ref.move_at(point_mothership)

    def next_action(self):
        if self.drone_ref.distance_to(self.drone_ref.my_mothership) < 10:
            self.take_start_position()
            return
        if self.drone_ref.distance_to(self.drone_ref.target) > self.drone_ref.gun.shot_distance + 20 or \
                not self.drone_ref.target.is_alive or self.drone_ref.target is None:
            self.drone_ref.target = self.get_aim_for_shooting()
        else:
            self.drone_ref.turn_to(self.drone_ref.target)
            self.drone_ref.gun.shot(self.drone_ref.target)

    def get_aim_for_shooting(self):
        dists = self.get_sorted_distances_to_aims()
        if len(dists):
            aim = dists[0][0]
            return aim
        else:
            return Point(self.drone_ref.x, self.drone_ref.y)

    def get_sorted_distances_to_aims(self):

        aims = []
        aims.extend(self.drone_ref.scene.drones)
        aims.extend(self.drone_ref.scene.motherships)

        aims = filter(lambda x: x.team != self.drone_ref.team, aims)
        aims = filter(lambda x: x.is_alive, aims)
        aims = filter(lambda x: isinstance(x, Drone), aims)

        dists = [(aim,
                  self.drone_ref.distance_to(aim))
                 for aim in aims if
                 (0 < self.drone_ref.distance_to(aim))
                 ]

        sorted_dists = sorted(dists, key=lambda x: (x[1]))
        return sorted_dists


class Peacemaker(Strategy):
    composition_center_counter3 = {1: (theme.FIELD_WIDTH - 500, theme.FIELD_HEIGHT - 100),
                                   2: (theme.FIELD_WIDTH - 400, theme.FIELD_HEIGHT - 200),
                                   3: (theme.FIELD_WIDTH - 300, theme.FIELD_HEIGHT - 300),
                                   4: (theme.FIELD_WIDTH - 200, theme.FIELD_HEIGHT - 400),
                                   5: (theme.FIELD_WIDTH - 100, theme.FIELD_HEIGHT - 500)}

    composition_center_counter2 = {1: (100, theme.FIELD_HEIGHT - 100),
                                   2: (200, theme.FIELD_HEIGHT - 200),
                                   3: (300, theme.FIELD_HEIGHT - 300),
                                   4: (400, theme.FIELD_HEIGHT - 400),
                                   5: (500, theme.FIELD_HEIGHT - 500)}

    composition_center_counter4 = {1: (theme.FIELD_WIDTH - 550, 100),
                                   2: (theme.FIELD_WIDTH - 450, 250),
                                   3: (theme.FIELD_WIDTH - 350, 400),
                                   4: (theme.FIELD_WIDTH - 250, 550),
                                   5: (theme.FIELD_WIDTH - 150, 700)}

    composition_center_counter1 = {1: (100, 600),
                                   2: (200, 500),
                                   3: (300, 400),
                                   4: (400, 300),
                                   5: (500, 200)}

    selected_aim = None
    enemy_count = 0

    def take_start_position(self):
        x, y = 0, 0
        if self.drone_ref.label_angle == 'angle#1':
            x, y = Peacemaker.composition_center_counter1[self.drone_ref.serial_number]
        elif self.drone_ref.label_angle == 'angle#2':
            x, y = Peacemaker.composition_center_counter2[self.drone_ref.serial_number]
        elif self.drone_ref.label_angle == 'angle#3':
            x, y = Peacemaker.composition_center_counter3[self.drone_ref.serial_number]
        elif self.drone_ref.label_angle == 'angle#4':
            x, y = Peacemaker.composition_center_counter4[self.drone_ref.serial_number]

        point_start = Point(self.drone_ref.my_mothership.x, self.drone_ref.my_mothership.y) + Vector(x, y)
        self.drone_ref.move_at(point_start)

    def on_born(self, **kwargs):
        self.take_start_position()

    def on_stop_at_asteroid(self, **kwargs):
        self.next_action()

    def on_load_complete(self, **kwargs):
        self.next_action()

    def on_stop_at_mothership(self, **kwargs):
        self.next_action()

    def on_unload_complete(self, **kwargs):
        self.next_action()

    def on_stop_at_point(self, **kwargs):
        self.next_action()

    def on_stop(self, **kwargs):
        self.next_action()

    def on_hearbeat(self, **kwargs):
        self.next_action()

    def on_wake_up(self, **kwargs):
        self.next_action()

    def return_for_heal(self):
        if self.drone_ref.health < 75:
            point_mothership = Point(self.drone_ref.my_mothership.x, self.drone_ref.my_mothership.y)
            self.drone_ref.move_at(point_mothership)

    def next_action(self):
        if self.drone_ref.health < 55:
            point_mothership = Point(self.drone_ref.my_mothership.x, self.drone_ref.my_mothership.y)
            self.drone_ref.move_at(point_mothership)
            return

        if self.drone_ref.target is None or not self.drone_ref.target.is_alive:
            self.drone_ref.target = self.get_aim_for_shooting()
            return

        if self.drone_ref.distance_to(self.drone_ref.target) > self.drone_ref.gun.shot_distance + 10:
            self.approach_enemy()
            return
        else:
            self.drone_ref.turn_to(self.drone_ref.target)
            self.drone_ref.gun.shot(self.drone_ref.target)
            return

    def get_aim_for_shooting(self):
        dists = self.get_sorted_distances_to_aims()
        if len(dists):
            aim = dists[0][0]
            return aim
        else:
            return None

    def get_sorted_distances_to_aims(self):

        aims = []
        aims.extend(self.drone_ref.scene.drones)
        aims.extend(self.drone_ref.scene.motherships)

        aims = filter(lambda x: x.team != self.drone_ref.team, aims)
        aims = filter(lambda x: x.is_alive, aims)
        aims = filter(lambda x: isinstance(x, Drone), aims)

        dists = [(aim,
                  self.drone_ref.distance_to(aim))
                 for aim in aims if
                 (0 < self.drone_ref.distance_to(aim))
                 ]

        sorted_dists = sorted(dists, key=lambda x: (x[1]))
        return sorted_dists

    def approach_enemy(self):

        if self.drone_ref.target:
            x_target, y_target = self.drone_ref.target.x, self.drone_ref.target.y
            comp = None
            if x_target >= Strategy.half_width_x and y_target >= Strategy.half_height_y:
                comp = Peacemaker.composition_center_counter3
            elif x_target >= Strategy.half_width_x and y_target <= Strategy.half_height_y:
                comp = Peacemaker.composition_center_counter4
            elif x_target <= Strategy.half_width_x and y_target >= Strategy.half_height_y:
                comp = Peacemaker.composition_center_counter2
            elif x_target <= Strategy.half_width_x and y_target <= Strategy.half_height_y:
                comp = Peacemaker.composition_center_counter1

            x, y = comp[self.drone_ref.serial_number]

            point_start = Point(x, y)

            self.drone_ref.move_at(point_start)

        else:
            self.get_aim_for_shooting()


class MothershipKiller(Strategy):
    composition_center_counter3 = {1: (theme.FIELD_WIDTH - 200, theme.FIELD_HEIGHT - 50),
                                   2: (theme.FIELD_WIDTH - 200, theme.FIELD_HEIGHT - 100),
                                   3: (theme.FIELD_WIDTH - 200, theme.FIELD_HEIGHT - 200),
                                   4: (theme.FIELD_WIDTH - 200, theme.FIELD_HEIGHT - 300),
                                   5: (theme.FIELD_WIDTH - 200, theme.FIELD_HEIGHT - 400)}

    composition_center_counter2 = {1: (300, theme.FIELD_HEIGHT - 50),
                                   2: (300, theme.FIELD_HEIGHT - 100),
                                   3: (300, theme.FIELD_HEIGHT - 200),
                                   4: (300, theme.FIELD_HEIGHT - 300),
                                   5: (300, theme.FIELD_HEIGHT - 400)}

    composition_center_counter4 = {1: (theme.FIELD_WIDTH - 200, 100),
                                   2: (theme.FIELD_WIDTH - 200, 200),
                                   3: (theme.FIELD_WIDTH - 200, 300),
                                   4: (theme.FIELD_WIDTH - 200, 400),
                                   5: (theme.FIELD_WIDTH - 200, 500)}

    composition_center_counter1 = {1: (300, 100),
                                   2: (300, 200),
                                   3: (300, 300),
                                   4: (300, 400),
                                   5: (300, 500)}

    selected_aim = None
    enemy_count = 0

    def take_start_position(self):
        x, y = 0, 0
        if self.drone_ref.label_angle == 'angle#1':
            x, y = MothershipKiller.composition_center_counter1[self.drone_ref.serial_number]
        elif self.drone_ref.label_angle == 'angle#2':
            x, y = MothershipKiller.composition_center_counter2[self.drone_ref.serial_number]
        elif self.drone_ref.label_angle == 'angle#3':
            x, y = MothershipKiller.composition_center_counter3[self.drone_ref.serial_number]
        elif self.drone_ref.label_angle == 'angle#4':
            x, y = MothershipKiller.composition_center_counter4[self.drone_ref.serial_number]

        point_start = Point(self.drone_ref.my_mothership.x, self.drone_ref.my_mothership.y) + Vector(x, y)
        self.drone_ref.move_at(point_start)

    def on_born(self, **kwargs):
        self.take_start_position()

    def on_stop_at_asteroid(self, **kwargs):
        self.next_action()

    def on_load_complete(self, **kwargs):
        self.next_action()

    def on_stop_at_mothership(self, **kwargs):
        self.next_action()

    def on_unload_complete(self, **kwargs):
        self.next_action()

    def on_stop_at_point(self, **kwargs):
        self.next_action()

    def on_stop(self, **kwargs):
        self.next_action()

    def on_hearbeat(self, **kwargs):
        self.next_action()

    def on_wake_up(self, **kwargs):
        self.next_action()

    def return_for_heal(self):
        if self.drone_ref.health < 75:
            point_mothership = Point(self.drone_ref.my_mothership.x, self.drone_ref.my_mothership.y)
            self.drone_ref.move_at(point_mothership)

    def next_action(self):
        self.drone_ref.target = self.get_aim_for_shooting()
        if self.drone_ref.health < 65:
            point_mothership = Point(self.drone_ref.my_mothership.x, self.drone_ref.my_mothership.y)
            self.drone_ref.move_at(point_mothership)
            return

        if self.drone_ref.distance_to(self.drone_ref.my_mothership) < 10:
            self.take_start_position()
            return

        if self.drone_ref.target is None or not self.drone_ref.target.is_alive:
            self.drone_ref.target = self.get_aim_for_shooting()

        if self.drone_ref.distance_to(self.drone_ref.target) > self.drone_ref.gun.shot_distance + 10:
            self.approach_enemy()
            return
        else:
            self.drone_ref.turn_to(self.drone_ref.target)
            self.drone_ref.gun.shot(self.drone_ref.target)
            return

    def get_aim_for_shooting(self):
        dists = self.get_sorted_distances_to_aims()
        if len(dists):
            aim = dists[0][0]
            return aim
        else:
            return None

    def get_sorted_distances_to_aims(self):
        aims = []
        aims.extend(self.drone_ref.scene.motherships)
        aims = filter(lambda x: x.team != self.drone_ref.team, aims)
        aims = filter(lambda x: x.is_alive, aims)
        dists = [(aim,
                  self.drone_ref.distance_to(aim))
                 for aim in aims if
                 (0 < self.drone_ref.distance_to(aim) and aim.payload > 0)
                 ]

        sorted_dists = sorted(dists, key=lambda x: (x[1]))
        return sorted_dists

    def approach_enemy(self):
        if self.drone_ref.target:
            x_target, y_target = self.drone_ref.target.x, self.drone_ref.target.y
            cmp = None
            if x_target >= Strategy.half_width_x and y_target >= Strategy.half_height_y:
                cmp = MothershipKiller.composition_center_counter3
            elif x_target >= Strategy.half_width_x and y_target <= Strategy.half_height_y:
                cmp = MothershipKiller.composition_center_counter4
            elif x_target <= Strategy.half_width_x and y_target >= Strategy.half_height_y:
                cmp = MothershipKiller.composition_center_counter2
            elif x_target <= Strategy.half_width_x and y_target <= Strategy.half_height_y:
                cmp = MothershipKiller.composition_center_counter1

            x, y = cmp[self.drone_ref.serial_number]

            point_start = Point(x, y)
            self.drone_ref.move_at(point_start)
        else:
            self.get_aim_for_shooting()


class VorobyevDrone(Drone):
    my_team = []
    serial_number = 1
    drone_states = {}

    def __init__(self, **kwargs):
        self._strategy = None
        self.serial_number = VorobyevDrone.serial_number
        VorobyevDrone.serial_number += 1
        super(VorobyevDrone, self).__init__(**kwargs)
        self.collect_strategy = Collector(drone_ref=self)
        self.defend_strategy = Defender(drone_ref=self)
        self.peacemaker_strategy = Peacemaker(drone_ref=self)
        self.mship_killer_strategy = MothershipKiller(drone_ref=self)
        self.label_angle = None

    @property
    def strategy(self):
        return self._strategy

    @strategy.setter
    def strategy(self, strategy) -> None:
        self._strategy = strategy

    def move_at(self, target, speed=None, **kwargs):
        super(VorobyevDrone, self).move_at(target, speed=speed)

    def on_born(self, **kwargs):
        self.detect_angle_location_on_start()
        self.my_team.append(self)
        self.strategy = self.defend_strategy
        self._strategy.implement_strategy(message="on_born", **kwargs)

    def on_stop_at_asteroid(self, asteroid, **kwargs):
        self._strategy.implement_strategy(message="on_stop_at_asteroid", **kwargs)

    def on_load_complete(self, **kwargs):
        self._strategy.implement_strategy(message="on_load_complete", **kwargs)

    def on_stop_at_mothership(self, mothership, **kwargs):
        self._strategy.implement_strategy(message="on_stop_at_mothership", **kwargs)

    def on_unload_complete(self, **kwargs):
        self._strategy.implement_strategy(message="on_unload_complete", **kwargs)

    def on_stop_at_point(self, target, **kwargs):
        self._strategy.implement_strategy(message="on_stop_at_point", **kwargs)

    def on_stop(self, **kwargs):
        self._strategy.implement_strategy(message="on_stop", **kwargs)

    def on_wake_up(self, **kwargs):
        self._strategy.implement_strategy(message="on_wake_up", **kwargs)

    def on_hearbeat(self, **kwargs):
        if(self.strategy.get_count_of_enemies_without_turrets() <= 2 and self.strategy.get_count_of_enemies_all() <= 2)\
                and len(self.teammates) >= 1:
            current_strategies = [teammate.strategy.__class__.__name__ for teammate in self.teammates if
                                  teammate.is_alive]
            current_strategies.append(self.strategy.__class__.__name__)
            if 'Collector' not in map(lambda x: x.strategy.__class__.__name__,
                                      self.teammates) and not isinstance(self.strategy, Collector) and \
                    len(current_strategies) > 1:
                chosen_one = random.choice(self.teammates)
                chosen_one.strategy = chosen_one.collect_strategy

            if len(self.teammates) >= 2 and list(map(lambda x: x.strategy.__class__.__name__, self.teammates)).count(
                    'Peacemaker') <= 3 and self.strategy.get_count_of_enemies_without_turrets() <= 1:
                for teammate in self.teammates:
                    if not isinstance(teammate.strategy, Collector):
                        teammate.strategy = teammate.peacemaker_strategy

        if len(self.teammates) == 0:
            self.strategy = self.defend_strategy
            self.target = None

        mship_count = len([1 for mship in self.scene.motherships if
                           (mship.payload > 0 and 0 < self.distance_to(mship) and mship.team != self.team
                            and mship.is_alive)])

        if self.strategy.get_count_of_enemies_all() == 0 and mship_count > 0:
            for teammate in self.teammates:
                if not isinstance(teammate.strategy, MothershipKiller) and not isinstance(teammate.strategy, Collector):
                    teammate.strategy = teammate.mship_killer_strategy

        if mship_count == 0 and self.strategy.get_count_of_enemies_all() == 0:
            for teammate in self.teammates:
                if not isinstance(teammate.strategy, Collector):
                    teammate.strategy = teammate.collect_strategy

        self._strategy.implement_strategy(message="on_hearbeat", **kwargs)

    def detect_angle_location_on_start(self):
        my_mship_coords = self.my_mothership.coord
        all_mship_coords = [(m.coord.x, m.coord.y) for m in self.scene.motherships]
        if min(all_mship_coords) == (my_mship_coords.x, my_mship_coords.y):
            self.label_angle = 'angle#1'
        if max(all_mship_coords) == (my_mship_coords.x, my_mship_coords.y):
            self.label_angle = 'angle#3'
        if my_mship_coords.x > my_mship_coords.y:
            self.label_angle = 'angle#4'
        if my_mship_coords.x < my_mship_coords.y:
            self.label_angle = 'angle#2'

    def distance_to(self, obj):
        if obj is None:
            return 9999
        else:
            return super(VorobyevDrone, self).distance_to(obj)


drone_class = VorobyevDrone