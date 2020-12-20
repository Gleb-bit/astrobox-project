# -*- coding: utf-8 -*-
import math
import random
from abc import abstractmethod, ABC

from astrobox.core import Drone
from robogame_engine import GameObject
from robogame_engine.geometry import Point, Vector
from robogame_engine.theme import theme


class GlazovDrone(Drone):
    my_team = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.job = None
        self.gun_range = 580
        self.used = set()
        self.stats_dict = {}
        self.stats_dict[self.id] = {}
        self.condition = 'normal'
        self.target = None
        self.destination = None
        self.ready = False
        self.no_enemies = False
        self.destinations = {
            1: {'x': -30, 'y': 190},
            2: {'x': 50, 'y': 150},
            3: {'x': 120, 'y': 110},
            4: {'x': 160, 'y': 40},
            5: {'x': 190, 'y': -30}}

    def on_born(self):
        self.my_team.append(self)
        self.my_number = len(self.my_team)
        coord = self.my_mothership.coord
        destination = self.destinations[self.my_number]
        if coord.x <= 100 and coord.y <= 100:
            self.start_destination = Point(coord.x + destination['x'], coord.y + destination['y'])
        if coord.x <= 100 and coord.y > 100:
            self.start_destination = Point(coord.x + destination['x'], coord.y - destination['y'])
        if coord.x > 100 and coord.y <= 100:
            self.start_destination = Point(coord.x - destination['x'], coord.y + destination['y'])
        if coord.x > 100 and coord.y > 100:
            self.start_destination = Point(coord.x - destination['x'], coord.y - destination['y'])

        if self.my_number <= 1:
            self.job = Worker(self)
        else:
            self.job = Fighter(self)

        self.job.after_born()

    def on_heartbeat(self):
        if self.no_enemies:
            self.job = Worker(self)
        if self.health <= 70:
            self.go_healing()
        elif self.health >= 95 and self.condition == 'wounded':
            self.job.return_after_healing()
        self.job.doing_heartbeat()

    def go_healing(self):
        self.condition = 'wounded'
        self.job.destination = self.my_mothership
        if str(self.coord) != str(self.job.destination):
            self.move_at(self.job.destination)

    def on_wake_up(self):
        self.job.next_action()

    def on_stop_at_asteroid(self, asteroid):
        self.job.on_stop_at_asteroid(asteroid)

    def on_stop_at_point(self, target):
        self.job.on_stop_at_point(target)

    def on_load_complete(self):
        self.job.on_load_complete()

    def on_stop_at_mothership(self, mothership):
        self.job.on_stop_at_mothership(mothership)

    def on_unload_complete(self):
        self.job.next_action()


class Job(ABC):

    def __init__(self, unit: GlazovDrone):
        self.unit = unit
        self.destination = None

    @abstractmethod
    def after_born(self):
        pass

    @abstractmethod
    def next_action(self):
        pass

    @abstractmethod
    def on_stop_at_asteroid(self, asteroid):
        pass

    @abstractmethod
    def on_stop_at_mothership(self, mothership):
        pass

    @abstractmethod
    def on_stop_at_point(self, target):
        pass


class Worker(Job):

    def __init__(self, unit: GlazovDrone):
        super().__init__(unit)
        self.start_destination = self.unit.start_destination
        self.enemy_count = 0

    def _get_my_asteroid(self, dist):
        soldier = self.unit
        not_empty_asteroids = [asteroid for asteroid in soldier.scene.asteroids if not asteroid.is_empty]
        not_empty_asteroids.extend([mothership for mothership in soldier.scene.motherships
                                    if not mothership.is_alive and not mothership.is_empty])
        not_empty_asteroids.extend(
            [drone for drone in soldier.scene.drones if not drone.is_alive and not drone.is_empty])
        for delete in self.unit.used:
            if delete in not_empty_asteroids and delete.payload == 0:
                not_empty_asteroids.remove(delete)

        if len(not_empty_asteroids) == 0:
            return soldier.my_mothership

        if dist == 'distance_far':
            asteroid = self.__max_distance(not_empty_asteroids)
        elif dist == 'distance_near':
            asteroid = self.__min_distance(not_empty_asteroids)
        elif dist == 'distance_average':
            asteroid = self.__avg_distance(not_empty_asteroids)
        elif dist == 'distance_random':
            asteroid = self.__rand_distance(not_empty_asteroids)

        else:
            asteroid = self.__rand_distance(not_empty_asteroids)
        self.unit.used.add(asteroid)
        return asteroid

    def next_action(self):
        self.on_unload_complete()

    def after_born(self):
        self.unit.destination = self._get_my_asteroid(dist='distance_near')
        self.unit.move_at(self.unit.destination)
        return self.start_destination

    def return_after_healing(self):
        soldier = self.unit
        soldier.condition = 'normal'
        soldier.destination = None
        soldier.target = None
        if soldier.payload < 90:
            soldier.destination = self._get_my_asteroid(dist='distance_near')
        else:
            soldier.destination = soldier.my_mothership
        soldier.move_at(soldier.destination)

    def on_stop_at_asteroid(self, asteroid):
        self.unit.load_from(asteroid)

    def on_stop_at_mothership(self, mothership):
        if mothership == self.unit.my_mothership:
            self.unit.unload_to(mothership)
        elif mothership != self.unit.my_mothership:
            self.unit.load_from(mothership)

    def on_stop_at_point(self, target):
        dead_drones = [drone for drone in self.unit.scene.drones if not drone.is_alive and not drone.is_empty]
        for drone in dead_drones:
            if drone.near(target): self.unit.load_from(drone)

    def on_unload_complete(self):
        soldier = self.unit
        soldier.target = self._get_my_asteroid(dist='distance_near')
        soldier.move_at(soldier.target)

    def on_load_complete(self):
        soldier = self.unit

        if not hasattr(soldier.target, 'payload'):
            soldier.target = self._get_my_asteroid(dist='distance_near')

        if soldier.payload < 90 and soldier.target.payload <= 0:
            soldier.target = self._get_my_asteroid(dist='distance_near')
            soldier.move_at(soldier.target)
        else:
            soldier.move_at(soldier.my_mothership)

    def doing_heartbeat(self):
        pass

    def __max_distance(self, not_empty_asteroids):
        max_distance = 0
        target = None
        for asteroid in not_empty_asteroids:
            if asteroid.payload > 0 and self.unit.distance_to(asteroid) > max_distance:
                max_distance = self.unit.distance_to(asteroid)
                target = asteroid
        return target

    def __min_distance(self, not_empty_asteroids):
        min_distance = 100000
        target = None
        for asteroid in not_empty_asteroids:
            if self.unit.distance_to(asteroid) < min_distance:
                min_distance = self.unit.distance_to(asteroid)
                target = asteroid

        return target

    def __avg_distance(self, not_empty_asteroids):
        distance_list = []
        for asteroid in not_empty_asteroids:
            distance_list.append((self.unit.distance_to(asteroid), asteroid))
        distance_list = sorted(distance_list)
        half_length = (len(distance_list) // 2)
        avg = distance_list[half_length][1]
        return avg

    def __rand_distance(self, not_empty_asteroids):
        distance_list = []
        for asteroid in not_empty_asteroids:
            distance_list.append((self.unit.distance_to(asteroid), asteroid))
        asteroids_count = len(self.unit.asteroids)

        if len(distance_list) >= asteroids_count + 1:
            distance_list = sorted(distance_list[0:len(distance_list) // 2 - asteroids_count])
        else:
            distance_list = sorted(distance_list[0:len(distance_list)])
        random_asteroid = random.randint(0, len(distance_list) - 1)
        rand = distance_list[random_asteroid][1]
        return rand


class Fighter(Job):
    def __init__(self, unit: GlazovDrone):
        super().__init__(unit)
        self.enemies_on_born = self.count_enemies()
        self.condition = 'normal'
        self.target = None
        self.ready = False
        self.start_destination = None
        self.enemy_count = None

    def after_born(self):
        soldier = self.unit
        soldier.move_at(soldier.start_destination)
        soldier.destination = None

    def return_after_healing(self):
        soldier = self.unit
        soldier.condition = 'normal'
        self.after_born()
        return

    def next_action(self):
        self.fight()

    def fight(self):
        soldier = self.unit
        soldier.target = self.get_target()

        if not soldier.destination:
            soldier.destination = self.get_place_for_attack(soldier, soldier.target)

        if self.enemies_on_born >= 10 and self.enemy_count >= 4:
            if not self.friendly_fire(soldier.target):
                soldier.gun.shot(soldier.target)
            self.turn_to_target(soldier)

        elif self.enemies_on_born == 5 and self.enemy_count > 2:
            if not self.friendly_fire(soldier.target):
                soldier.gun.shot(soldier.target)
            self.turn_to_target(soldier)
        elif self.enemies_on_born == 5 and self.enemy_count == 2:
            if soldier.my_number == 1:
                soldier.no_enemies = True
            if not self.friendly_fire(soldier.target):
                soldier.gun.shot(soldier.target)
            self.turn_to_target(soldier)

        else:
            if soldier.my_number == 1:
                soldier.no_enemies = True
            soldier.target = self.get_target()
            self.finish_them()

    def turn_to_target(self, soldier):
        soldier.target = self.get_target()
        soldier.turn_to(soldier.target)

    def fighter_attack(self):
        soldier = self.unit
        if soldier.distance_to(soldier.my_mothership) >= 60:
            soldier.gun.shot(soldier.target)

    def doing_heartbeat(self):
        soldier = self.unit
        if str(soldier.start_destination) == str(soldier.coord) and not soldier.ready:
            soldier.destination = None
            soldier.target = None
            soldier.ready = True

    def get_place_for_attack(self, soldier, target):
        if isinstance(target, GameObject):
            vec = Vector.from_points(target.coord, soldier.coord)
        elif isinstance(target, Point):
            vec = Vector.from_points(target, soldier.coord)
        else:
            raise Exception("target must be GameObject or Point!".format(target, ))
        dist = vec.module
        _koef = 1 / dist
        norm_vec = Vector(vec.x * _koef, vec.y * _koef)
        vec_gunshot = norm_vec * min(self.unit.gun_range, int(dist))
        purpose = Point(target.coord.x + vec_gunshot.x, target.coord.y + vec_gunshot.y)
        angles = [0, 60, -60, 30, -30, 15, -15, 45, -45]
        random.shuffle(angles)
        for ang in angles:
            place = self.get_place_near(purpose, target, ang)
            if place and self.valide_place(place):
                return place
        return None

    def get_place_near(self, point, target, angle):
        vec = Vector(point.x - target.x, point.y - target.y)
        vec.rotate(angle)
        return Point(target.x + vec.x, target.y + vec.y)

    def valide_place(self, point: Point):
        soldier = self.unit
        is_valide = 60 < point.x < (theme.FIELD_WIDTH - 60) and 60 < point.y < (theme.FIELD_HEIGHT - 60)
        for partner in soldier.my_team:
            if not partner.is_alive or partner is self.unit:
                continue
            is_valide = is_valide and (partner.distance_to(point) >= 50)
        return is_valide

    def friendly_fire(self, enemy):
        for i in range(int(self.unit.distance_to(enemy))):
            rab = math.sqrt((int(enemy.coord.x) - int(self.unit.coord.x)) ** 2 +
                            (int(enemy.coord.y) - int(self.unit.coord.y)) ** 2)
            k = i / rab
            c_x = int(self.unit.coord.x) + (int(enemy.coord.x) - int(self.unit.coord.x)) * k
            c_y = int(self.unit.coord.y) + (int(enemy.coord.y) - int(self.unit.coord.y)) * k
            drone_list_copy = self.unit.my_team.copy()
            drone_list_copy.remove(self.unit)
            drone_list_copy = [drone for drone in drone_list_copy if drone.is_alive]
            for drone in drone_list_copy:
                drone.radius = 50
                if drone.near(Point(c_x, c_y)):
                    return True
                else:
                    continue
        return False

    def on_stop_at_asteroid(self, asteroid):
        self.next_action()

    def on_stop_at_mothership(self, mothership):
        self.next_action()

    def on_stop_at_point(self, target):
        self.next_action()

    def get_target(self):
        enemies = None
        soldier = self.unit
        enemies = [(drone, soldier.distance_to(drone), drone.id) for drone in soldier.scene.drones if
                   soldier.team != drone.team and drone.is_alive]
        bases = [(base, soldier.distance_to(base), base.id) for base in soldier.scene.motherships if
                 base.team != soldier.team and base.is_alive]
        bases.sort(key=lambda x: x[2])
        enemies.sort(key=lambda x: x[1])

        basa = None
        enemy = None
        self.enemy_count = len(enemies)

        if len(enemies) > 0:
            chosen_one = enemies[0]
            enemy = chosen_one[0]

        if len(bases) > 0:
            chosen_one = bases[0]
            basa = chosen_one[0]

        if self.enemy_count <= 2 and len(bases) >= 1:
            return self.attack_base_if_only_two_enemies_left(basa, soldier)
        if self.enemy_count == 0 and len(bases) == 0:
            return self.harvest_elerium_when_no_bases_and_enemies_left(soldier)
        else:
            return self.attack_enemy(enemy, soldier)

    def attack_enemy(self, enemy, soldier):
        soldier.target = enemy
        return soldier.target

    def harvest_elerium_when_no_bases_and_enemies_left(self, soldier):
        self.unit.target = self.unit.my_mothership
        self.unit.destination = self.unit.my_mothership
        self.unit.no_enemies = True
        return

    def attack_base_if_only_two_enemies_left(self, basa, soldier):
        soldier.target = basa
        return soldier.target

    def count_enemies(self):
        soldier = self.unit
        enemies = [(drone, soldier.distance_to(drone), drone.id) for drone in soldier.scene.drones if
                   soldier.team != drone.team and drone.is_alive]
        return len(enemies)

    def finish_them(self):
        soldier = self.unit
        if str(soldier.coord) != str(soldier.destination):
            soldier.move_at(soldier.destination)
            return

        elif soldier.distance_to(soldier.target) > soldier.gun_range and str(soldier.coord) == str(
                soldier.destination):
            soldier.destination = self.get_place_for_attack(soldier, soldier.target)
            soldier.move_at(soldier.destination)
            return

        if soldier.distance_to(soldier.target) <= soldier.gun_range + 100 and str(soldier.coord) == str(
                soldier.destination):
            if not self.friendly_fire(soldier.target):
                soldier.turn_to(soldier.target)
                self.fighter_attack()
                return

        if not soldier.target.is_alive:
            soldier.target = None
            soldier.destination = None
            return


drone_class = GlazovDrone
