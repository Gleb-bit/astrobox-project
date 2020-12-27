# -*- coding: utf-8 -*-
import math
from abc import ABC, abstractmethod

from astrobox.core import Drone, MotherShip
from astrobox.themes.default import MOTHERSHIP_HEALING_DISTANCE
from robogame_engine.geometry import Point, Vector
from robogame_engine.states import StateTurning, StateMoving
from robogame_engine.theme import theme


class IlyinDrone(Drone):
    def __init__(self, **kwargs):
        super(IlyinDrone, self).__init__(**kwargs)
        self.empty_distance = 0
        self.partial_distance = 0
        self.full_distance = 0
        self.max_health = self.health
        self.value_list = None
        if Guard.squad_size == 0 or Gatherer.squad_size >= Guard.squad_size:
            self.role = Guard(self)
        else:
            self.role = Gatherer(self)

    def on_born(self):
        if isinstance(self.role, Gatherer):
            self.role.act()
            self.role.position = self.choose_destination()

    def choose_destination(self):
        if self.health <= self.max_health * .7:
            return self.my_mothership
        if self.free_space == 0:
            return self.my_mothership
        best_object = None
        best_value = 0
        for value in self.value_list:
            if self.near(value) and value.payload > 0:
                return value
            if not self.near(value):
                object_value = self._get_object_value(value)
                if object_value > best_value:
                    best_object = value
                    best_value = object_value
        if best_object is None:
            return self.my_mothership
        return best_object

    def _get_object_value(self, value):
        distance = self.distance_to(value)
        potential_payload = self._get_potential_payload(value)
        asteroid_value = potential_payload / distance
        return asteroid_value

    def _get_potential_payload(self, value):
        elirium_reserve = 0
        for mate in self.teammates:
            if mate.role.position == value:
                elirium_reserve += mate.free_space
        return value.payload - elirium_reserve

    def on_stop_at_asteroid(self, asteroid):
        if isinstance(self.role, Gatherer):
            if asteroid.payload > 0:
                self.load_from(asteroid)
            else:
                self.on_stop_at_point(asteroid)

    def on_stop_at_target(self, target):
        for asteroid in self.asteroids:
            if asteroid.near(target) and asteroid.payload > 0:
                self.on_stop_at_asteroid(asteroid)
                return
        else:
            for ship in self.scene.motherships:
                if ship.near(target):
                    self.on_stop_at_mothership(ship)
                    return
        self.on_stop_at_point(target)

    def on_stop_at_point(self, target):
        if isinstance(self.role, Gatherer):
            for wreck in self.scene.drones:
                if wreck.near(target) and wreck.payload > 0:
                    self.load_from(wreck)

    def on_load_complete(self):
        self.role.position = self.choose_destination()
        self.move_at(self.role.position)

    def on_stop_at_mothership(self, mothership):
        if isinstance(self.role, Gatherer):
            if mothership == self.my_mothership:
                self.unload_to(mothership)
            else:
                self.load_from(mothership)

    def on_unload_complete(self):
        self.role.position = self.choose_destination()
        self.move_at(self.role.position)

    def on_wake_up(self):
        if isinstance(self.role, Gatherer):
            self.role.position = self.choose_destination()
            if self.role.position:
                self.move_at(self.role.position)

    def move_at(self, target, speed=None):
        if self.is_empty:
            self.empty_distance += self.distance_to(target)
        elif self.is_full:
            self.full_distance += self.distance_to(target)
        else:
            self.partial_distance += self.distance_to(target)
        super(IlyinDrone, self).move_at(target, speed)

    def on_heartbeat(self):
        self.role.act()

    def shoot(self, enemy):
        if not isinstance(self.state, (StateTurning, StateMoving)):
            self.gun.shot(enemy)


class Behaviour(ABC):
    def __init__(self, drone):
        self.drone = drone
        self.position = None

    @abstractmethod
    def act(self):
        pass

    @classmethod
    def _get_distance(cls, coord1, coord2):
        start_x, start_y = coord1.x, coord1.y
        end_x, end_y = coord2.x, coord2.y
        return ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** .5

    def _in_danger_zone(self, value):
        for mothership in self.drone.scene.motherships:
            if mothership != self.drone.mothership:
                if self._get_distance(value, mothership) < self.drone.gun.shot_distance + \
                        MOTHERSHIP_HEALING_DISTANCE + self.drone.radius:
                    for enemy in self.drone.scene.drones:
                        if enemy.team == mothership.team:
                            if enemy.is_alive:
                                return True
        return False

    def _winning(self):
        team_payload = 0
        enemy_payload = 0
        team_payload += self.drone.mothership.payload
        for mate in self.drone.scene.drones:
            if mate.team == self.drone.team:
                team_payload += mate.payload
        for enemy_mothership in self.drone.scene.motherships:
            if enemy_mothership != self.drone.mothership:
                enemy_payload += enemy_mothership.payload
                for enemy in self.drone.scene.drones:
                    if enemy.team == enemy_mothership.team:
                        enemy_payload += enemy.payload
            if team_payload <= enemy_payload:
                return False
            else:
                enemy_payload = 0
        return True

    def _enemies_near_mothership(self):
        for enemy in self.drone.scene.drones:
            if enemy.team != self.drone.team:
                if enemy.is_alive:
                    if self._get_distance(self.drone.mothership.coord, enemy.coord) - \
                            MOTHERSHIP_HEALING_DISTANCE * .8 < self.drone.gun.shot_distance:
                        return True
        return False

    @classmethod
    def _in_safezone(cls, enemy):
        if not isinstance(enemy, MotherShip):
            if enemy.distance_to(enemy.my_mothership) <= MOTHERSHIP_HEALING_DISTANCE and enemy.mothership.is_alive:
                return True
        return False

    def _no_enemies_left(self):
        for drone in self.drone.scene.drones:
            if drone.team != self.drone.team:
                if drone.is_alive:
                    return False
        return True


class Warrior(Behaviour):
    formation_range = Drone.radius * 2
    warriors = []
    squad_size = 0
    anchors = {}
    target: Drone = None
    formation_angle = 0

    def __init__(self, drone: IlyinDrone):
        super().__init__(drone)
        self.warriors.append(self.drone)
        Warrior.squad_size = len(self.warriors)
        self.formation_size = (self.drone.radius * len(self.warriors)) + \
                              (self.formation_range * len(self.warriors) - 1)
        self._initialise_data()
        self.position = None
        self.banzai = False

    def act(self):
        self._check_warriors()
        if self.drone.is_alive:
            if self.drone.health <= self.drone.max_health * .5:
                if self.exchange():
                    return
            self._to_position()
            if self._enemies_near_mothership():
                for warrior in self.warriors:
                    warrior.role = Guard(warrior)
                    self.warriors.remove(warrior)
                    Warrior.squad_size = len(self.warriors)
                return
            if self._target_is_valid():
                if abs(self.drone.coord.x - self.position.x) <= 10 and abs(self.drone.coord.y - self.position.y) <= 10:
                    self.drone.turn_to(self.target)
                    self.drone.shoot(self.target)
                if self.banzai and self._in_safezone(self.target):
                    potential_target = self._suicide_attack(priority=True)
                    if potential_target is not None:
                        Warrior.target = potential_target
            else:
                self._get_new_target()
            if Warrior.target is None and self._no_enemies_left():
                self.drone.role = Gatherer(self.drone)
            elif self._no_values_left():
                if not self._winning():
                    self.banzai = True
            if Gatherer.squad_size == 0 and Warrior.squad_size + Guard.squad_size > 1:
                self.anchors.pop(self.drone.id)
                self.warriors.remove(self.drone)
                self.drone.role = Gatherer(self.drone)
            if self._no_enemies_left():
                self.banzai = False

    def _check_warriors(self):
        for warrior in self.warriors:
            if not warrior.is_alive:
                warrior.role.exchange()

    def exchange(self):
        if Gatherer.squad_size > 1:
            gatherer = self._get_closest_gatherer()
            if gatherer is not None:
                gatherer.role.formation_size = self.formation_size
                self.anchors[gatherer.id] = self.anchors.pop(self.drone.id)
                self.warriors.remove(self.drone)
                Gatherer.gatherers.remove(gatherer)
                gatherer.role = Warrior(gatherer)
                gatherer.role.formation_size = self.formation_size
                self.drone.role = Gatherer(self.drone)
        else:
            self.drone.role = Guard(self.drone)
            self.warriors.remove(self.drone)
            Warrior.squad_size = len(self.warriors)
        return True

    def _get_closest_gatherer(self):
        nearest = None
        best_distance = None
        for gatherer in Gatherer.gatherers:
            if gatherer.health >= gatherer.max_health * .5:
                position = self.position or Point(self.drone.coord.x, self.drone.coord.y)
                to_position = gatherer.distance_to(position)
                if best_distance is None or to_position < best_distance:
                    nearest = gatherer
                    best_distance = to_position
        return nearest

    def _to_position(self):
        if self.target is None or self.anchors[self.drone.id].get('deadspace_central') is None:
            self.position = self.anchors[self.drone.id]['deadspace'] = self.anchors[self.drone.id]['mothership']
            self.anchors[self.drone.id]['deadspace_central'] = self.anchors[self.drone.id]['mothership_central']
        else:
            enemy_angle = self._get_formation_angle()
            if abs(math.degrees(self.formation_angle) - math.degrees(enemy_angle)) > 35:
                Warrior.formation_angle = enemy_angle
                for warrior in self.warriors:
                    warrior.role.position = warrior.role.rotate(enemy_angle)
                    warrior.move_at(warrior.role.position)
            else:
                if self.position is None:
                    self.position = self.anchors[self.drone.id]['deadspace']
        if not (abs(self.drone.coord.x - self.position.x) <= 10 and abs(self.drone.coord.y - self.position.y) <= 10):
            self.drone.move_at(self.position)

    def _get_new_target(self, priority_target=False):
        if self.banzai and priority_target:
            Warrior.target = self._look_around() or self._suicide_attack(priority_target)
        else:
            Warrior.target = self._look_around()  # search for enemies nearby
        if Warrior.target is None:  # no enemies nearby, reset formation
            Warrior.formation_angle = 0
            self.position = None
            Warrior.target = self._look_around(near=False)  # search for valid enemies not nearby
        if Warrior.target is None and self.banzai:
            Warrior.target = self._suicide_attack()
        if Warrior.target is not None:
            self._get_formation_anchor()
        elif self._no_enemies_left():
            for enemy_mothership in self.drone.scene.motherships:
                if enemy_mothership != self.drone.mothership and enemy_mothership.is_alive \
                        and not self._in_danger_zone(enemy_mothership):
                    Warrior.target = enemy_mothership
                    self._get_formation_anchor()

    def _look_around(self, near=True):
        nearest = None
        best_distance = None
        best_angle = None
        for enemy in self.drone.scene.drones:
            if enemy.team != self.drone.team:
                if not self._in_safezone(enemy) and enemy.is_alive:
                    to_enemy = self.drone.distance_to(enemy)
                    if near and self._target_in_range(enemy):
                        enemy_angle = self._get_formation_angle(target=enemy)
                        angle_difference = abs(math.degrees(self.formation_angle) - math.degrees(enemy_angle))
                        if best_angle is None or angle_difference < best_angle:
                            if best_distance is None or to_enemy < best_distance:
                                best_angle = angle_difference
                                best_distance = to_enemy
                                nearest = enemy
                    else:
                        if best_distance is None or to_enemy < best_distance:
                            best_distance = to_enemy
                            nearest = enemy
        return nearest

    def _suicide_attack(self, priority=False):
        priority_target = None
        priority_best_distance = None
        nearest = None
        best_distance = None
        for enemy in self.drone.scene.drones:
            if enemy.team != self.drone.team:
                if enemy.is_alive:
                    to_enemy = self.drone.distance_to(enemy)
                    if not enemy.near(enemy.my_mothership):
                        if priority_best_distance is None or to_enemy < priority_best_distance:
                            priority_target = enemy.mothership
                            priority_best_distance = to_enemy
                    elif best_distance is None or to_enemy < best_distance:
                        best_distance = to_enemy
                        nearest = enemy
        if priority:
            return priority_target
        else:
            return priority_target or nearest

    def _get_formation_anchor(self):
        enemy_angle = self._get_formation_angle()
        to_enemy = self.drone.distance_to(self.target)
        comfort_range = self.drone.gun.shot_distance * .9
        radius = to_enemy if to_enemy < comfort_range else comfort_range
        x = self.target.coord.x - radius * math.cos(enemy_angle)
        y = self.target.coord.y - radius * math.sin(enemy_angle)
        if self.formation_size // 2 + x > theme.FIELD_WIDTH:
            x = theme.FIELD_WIDTH - self.formation_size // 2
        elif x - self.formation_size // 2 < 0:
            x = self.formation_size // 2
        if self.formation_size // 2 + y > theme.FIELD_HEIGHT:
            y = theme.FIELD_HEIGHT - self.formation_size // 2
        elif y - self.formation_size // 2 < 0:
            y = self.formation_size // 2
        central = Point(x, y)
        for warrior in self.warriors:
            self.anchors[warrior.id]['deadspace_central'] = central
            warrior.role.set_default_formation_anchors(central=central, coord_name='deadspace')
            warrior.role.position = self.anchors[warrior.id]['deadspace']

    def _target_in_range(self, target=None):
        enemy = target or self.target
        if self.position.distance_to(enemy) <= self.drone.gun.shot_distance:
            return True
        return False

    def _initialise_data(self):
        if self.anchors.get(self.drone.id) is None:
            self.anchors[self.drone.id] = {}
        self.get_anchors()

    def get_anchors(self):
        if self.anchors[self.drone.id].get('mothership') is None:
            self._get_mothership_anchor()

    def set_default_formation_anchors(self, central, coord_name):
        y = central.y
        iteration = 1
        while True:
            for drone_id, drone_data in self.anchors.items():
                if drone_id != self.drone.id:
                    drone_position = drone_data.get(coord_name)
                    if drone_position is not None and drone_position.x == central.x and drone_position.y == y:
                        if iteration % 2:
                            y += self.formation_range * iteration
                        else:
                            y -= self.formation_range * iteration
                        break
            else:
                self.anchors[self.drone.id][coord_name] = Point(central.x, y)
                break
            iteration += 1

    def _get_mothership_anchor(self):
        left_anchor = Point(self.formation_size // 2, theme.FIELD_HEIGHT // 2)
        right_anchor = Point(theme.FIELD_WIDTH - self.formation_size // 2, theme.FIELD_HEIGHT // 2)
        if self._get_distance(self.drone.mothership.coord, left_anchor) < \
                self._get_distance(self.drone.mothership.coord, right_anchor):
            central = left_anchor
        else:
            central = right_anchor
        self.anchors[self.drone.id][f'mothership_central'] = central
        self.set_default_formation_anchors(central, 'mothership')

    def _get_formation_angle(self, target=None):
        enemy = target or self.target
        formation_center = self.anchors[self.drone.id]['deadspace_central']
        return math.atan2(enemy.coord.y - formation_center.y, enemy.coord.x - formation_center.x)

    def rotate(self, angle):
        center = self.anchors[self.drone.id]['deadspace_central']
        start_pos = self.anchors[self.drone.id]['deadspace']
        x = center.x + (start_pos.x - center.x) * math.cos(angle) - (start_pos.y - center.y) * math.sin(angle)
        y = center.y + (start_pos.x - center.x) * math.sin(angle) + (start_pos.y - center.y) * math.cos(angle)
        return Point(x, y)

    def _target_is_valid(self):
        if self.target is not None and self.target.is_alive and self._target_in_range():
            if not self._in_safezone(self.target) or self.banzai:
                if isinstance(self.target, MotherShip) and not (self._no_enemies_left() or self.banzai):
                    return False
                return True
        return False

    def _no_values_left(self):
        for asteroid in self.drone.asteroids:
            if asteroid.payload > 0:
                return False
        for wreck in self.drone.scene.drones:
            if not wreck.is_alive and wreck.team != self.drone.team and wreck.payload > 0:
                return False
        for motherwreck in self.drone.scene.motherships:
            if not motherwreck.is_alive and motherwreck.payload != 0:
                return False
        return True


class Gatherer(Behaviour):
    gatherers = []
    squad_size = 0

    def __init__(self, drone: IlyinDrone):
        super().__init__(drone)
        self.gatherers.append(self.drone)
        self.treat_level = 'green'
        Gatherer.squad_size = len(self.gatherers)

    def act(self):
        self._check_health()
        self._check_treat_level()
        self._prepare_value_list()
        if self.position is None:
            self.position = self.drone.choose_destination()
            self.drone.move_at(self.position)

    def _check_health(self):
        if self.drone.health <= self.drone.max_health * .7:
            self.drone.move_at(self.drone.mothership)
        if not self.drone.is_alive and self.drone in self.gatherers:
            self.gatherers.remove(self.drone)
            Gatherer.squad_size = len(self.gatherers)

    def _check_treat_level(self):
        treat_level = None
        for enemy in self.drone.scene.drones:
            if enemy.team != self.drone.team:
                if not self._winning():
                    if not self._yellow_value_list():
                        self.treat_level = 'green'
                    else:
                        self.treat_level = 'yellow'
                    return
                elif enemy.is_alive and not self._in_safezone(enemy):
                    self.treat_level = 'red'
                    return
                elif enemy.is_alive:
                    treat_level = 'yellow'
                elif treat_level != 'yellow':
                    treat_level = 'green'
        self.treat_level = treat_level

    def _prepare_value_list(self):
        value_list = []
        if self.treat_level == 'yellow':
            value_list = self._yellow_value_list()
        elif self.treat_level == 'green':
            for asteroid in self.drone.asteroids:
                if asteroid.payload != 0:
                    value_list.append(asteroid)
            for wreck in self.drone.scene.drones:
                if not wreck.is_alive and wreck.team != self.drone.team and wreck.payload != 0:
                    value_list.append(wreck)
            for motherwreck in self.drone.scene.motherships:
                if not motherwreck.is_alive and motherwreck.payload != 0:
                    value_list.append(motherwreck)
        self.drone.value_list = value_list

    def _yellow_value_list(self):
        value_list = []
        for asteroid in self.drone.asteroids:
            if not self._in_danger_zone(asteroid) and asteroid.payload != 0:
                value_list.append(asteroid)
        for wreck in self.drone.scene.drones:
            if not wreck.is_alive and wreck.payload != 0 and not self._in_danger_zone(wreck):
                value_list.append(wreck)
        return value_list

    @classmethod
    def _in_safezone(cls, enemy):
        if enemy.distance_to(enemy.my_mothership) <= MOTHERSHIP_HEALING_DISTANCE:
            return True
        return False


class Guard(Behaviour):
    guards = []
    squad_size = 0

    def __init__(self, drone: IlyinDrone):
        super().__init__(drone)
        self.guards.append(self.drone)
        Guard.squad_size = len(self.guards)
        self.target = None

    def act(self):
        if self.position is None:
            self.position = self._get_position()
        if self.drone.is_alive:
            if not (abs(self.drone.coord.x - self.position.x) <= 10 and abs(
                    self.drone.coord.y - self.position.y) <= 10):
                self.drone.move_at(self.position)
            if self._target_is_valid():
                if abs(self.drone.coord.x - self.position.x) <= 10 and abs(self.drone.coord.y - self.position.y) <= 10:
                    self.drone.turn_to(self.target)
                    self.drone.shoot(self.target)
            else:
                self._get_new_target()

    def _get_position(self):
        radius = MOTHERSHIP_HEALING_DISTANCE * .9
        for angle in range(0, 361, 45):
            x = int(self.drone.mothership.coord.x + radius * math.cos(math.radians(angle)))
            y = int(self.drone.mothership.coord.y + radius * math.sin(math.radians(angle)))
            if x in range(0, theme.FIELD_WIDTH + 1) and y in range(0, theme.FIELD_HEIGHT + 1):
                for guard in self.guards:
                    if guard != self.drone:
                        reserved_position = guard.role.position
                        if reserved_position is not None and reserved_position.x == x and reserved_position.y == y:
                            break
                else:
                    return Point(x, y)

    def _target_in_range(self, target=None):
        enemy = target or self.target
        if enemy is not None and self.position.distance_to(enemy) <= self.drone.gun.shot_distance + self.drone.radius:
            return True
        return False

    def _target_is_valid(self, target=None):
        try:
            target = target or self.target
            if target is not None and target.is_alive and self._target_in_range(target):
                if not self._in_safezone(target) and not self._friendly_fire(target):
                    if isinstance(target, MotherShip) and not self._no_enemies_in_range():
                        return False
                    return True
            return False
        except Exception as exc:
            print(exc)
            return False

    def _no_enemies_in_range(self):
        for enemy in self.drone.scene.drones:
            if enemy.team != self.drone.team and enemy.is_alive:
                if self._target_in_range(enemy) and not self._in_safezone(enemy) and not self._friendly_fire(enemy):
                    return False
        return True

    def _friendly_fire(self, enemy):
        enemy_vector = Vector.from_points(self.drone.coord, enemy.coord)
        for mate in self.drone.teammates:
            if self.drone.near(mate):
                return True
            mate_vector = Vector.from_points(self.drone.coord, mate.coord)
            scalar = int(enemy_vector.x * mate_vector.x + enemy_vector.y * mate_vector.y)
            modules = int(enemy_vector.module * mate_vector.module)
            angle = math.degrees(math.acos(min(scalar / modules, 1)))
            if angle < 20 and self.drone.distance_to(enemy) > self.drone.distance_to(mate) \
                    and not isinstance(mate.state, StateMoving):
                return True
        return False

    def _get_new_target(self):
        self.target = None
        for guard in self.guards:
            if guard != self.drone and self._target_is_valid(guard.role.target):
                self.target = guard.role.target
        if self.target is None:
            self.target = self._target_nearest_enemy()
        if self.target is None:
            if not self._winning() and self.drone.health == self.drone.max_health \
                    and not self._enemies_near_mothership():
                Warrior.target = self.target
                for guard in self.guards:
                    guard.role = Warrior(guard)
                    self.guards.remove(guard)
                    Guard.squad_size = len(self.guards)
                return
        if self._no_enemies_left():
            self.drone.role = Warrior(self.drone)

    def _target_nearest_enemy(self):
        nearest = None
        best_distance = None
        for enemy in self.drone.scene.drones:
            if enemy.team != self.drone.team:
                if not self._in_safezone(enemy) and enemy.is_alive and not self._friendly_fire(enemy):
                    to_enemy = self.drone.distance_to(enemy)
                    if best_distance is None or to_enemy < best_distance:
                        best_distance = to_enemy
                        nearest = enemy
        if nearest is None or not (self._enemies_near_mothership() and self._target_in_range(nearest)):
            for mothership in self.drone.scene.motherships:
                if mothership.team != self.drone.team:
                    if mothership.is_alive and self._target_in_range(mothership):
                        return mothership
        return nearest

    def _target_enemy_mothership(self):
        for mothership in self.drone.scene.motherships:
            if mothership.team != self.drone.team:
                if mothership.is_alive and self._target_in_range(mothership):
                    return mothership


drone_class = IlyinDrone
