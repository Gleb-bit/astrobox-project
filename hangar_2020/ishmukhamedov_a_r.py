# -*- coding: utf-8 -*-
from enum import IntEnum
from math import sin, cos, pi
from typing import Optional, List
from robogame_engine.geometry import Vector, Point
from astrobox.core import Drone, Asteroid, MotherShip

# Атрибуты дрона / Астероида

# coord - координаты собственного местоположения
# direction - курс корабля
# my_mathership - космобаза приписки
# asteroids - список всех астероидов на поле
# payload - кол-во элериума в трюме
# free_space - свободного места в трюме
# fullness - процент загрузки
# is_empty - трюм пустой
# is_full - трюм полностью забит элериумом


# Методы дрона
# turn_to(obj) - повернуться к объекту/точке
# move_at(obj) - двигаться к объекту/точке
# stop() – остановиться
# load_from(obj) - загрузить элериум от объекта в трюм
# unload_to(obj) - разгрузить элериум из трюма в объект
# distance_to(obj) - рассчет расстояния до объекта/точки
# near(obj) - дрон находится рядом с объектом/точкой


class Commander:

    _instance = None
    _enemy: Drone = None
    _attack_points: List[Point] = []
    _enemies: List[Drone] = []
    _drones: List[Drone] = []
    _excluded_points: List[Point] = []

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self, drone: Drone):
        self._drones.append(drone)

    @property
    def enemy(self) -> Drone:
        return self._enemy

    @enemy.setter
    def enemy(self, enemy: Drone):
        self._enemy = enemy

    @property
    def attack_points(self) -> List[Point]:
        return self._attack_points

    @attack_points.setter
    def attack_points(self, points: List[Point]):
        self._attack_points = points

    @property
    def excluded_points(self) -> list:
        return self._excluded_points

    @property
    def enemies(self):
        return self._enemies

    @enemies.setter
    def enemies(self, enemies: List[Drone]):
        self._enemies = enemies

    @property
    def has_enemy(self):
        if self.enemy:
            return True

        return False

    @staticmethod
    def get_attack_points(center: Point, radius: int, size: int) -> list:
        """
            Возвращает точки атаки вокруг обозначенного центра
        """

        angles = int(360 / radius)
        size = size

        points = list()
        x, y = center.x, center.y

        for i in range(angles):
            x1 = x + size * cos(90 + (2 * pi * i) / angles)
            y1 = y + size * sin(90 + (2 * pi * i) / angles)
            points.append(Point(x1, y1))

        points = [point for point in points if int(point.x) in range(1200) and int(point.y) in range(600)]

        return points

    def get_attack_point(self, drone):
        """
            Выбирает незанятую точку атаки для дрона
        :param drone:
        :return:
        """

        if self.enemy and not self.enemy.is_alive:
            self._excluded_points = []

        self.enemies = [enemy for enemy in drone.scene.drones
                        if enemy not in drone.teammates and enemy != drone and enemy.is_alive]

        if not self.enemies:
            self.enemies = [mother_ship for mother_ship in drone.scene.motherships
                            if mother_ship != drone.my_mothership and mother_ship.is_alive]

        if not self.enemies:
            drone.mode = DroneMode.DRONE_HARVESTER
            return drone.mothership

        closest_enemy = self.enemies[0]

        for enemy in self.enemies:
            if drone.distance_to(enemy) < drone.distance_to(closest_enemy):
                closest_enemy = enemy

        self.enemy = closest_enemy

        if closest_enemy.state.target_point:
            self.attack_points = self.get_attack_points(closest_enemy.state.target_point,
                                                        drone.radius,
                                                        drone.gun.shot_distance/4)
        elif type(closest_enemy) == MotherShip:
            self.attack_points = self.get_attack_points(closest_enemy.coord,
                                                        drone.radius/2,
                                                        drone.gun.shot_distance/2)
        else:
            self.attack_points = self.get_attack_points(Point(600, 300), drone.radius, drone.gun.shot_distance/2)

        for attack_point in self.attack_points:
            for excluded_point in self.excluded_points:
                if attack_point.x == excluded_point.x and attack_point.y == excluded_point.y:
                    break
            else:
                point = attack_point
                self.excluded_points.append(point)
                break
        else:
            point = drone.coord

        return point


class DroneMode(IntEnum):
    DRONE_HARVESTER = 1
    DRONE_INTERCEPTOR = 2


class IshmukhamedovDrone(Drone):

    _mode: DroneMode = DroneMode.DRONE_HARVESTER

    full_travel: int = 0
    empty_travel: int = 0
    underload_travel: int = 0

    _commander: Optional[Commander] = None
    _attack_point: Optional[Point] = None

    _target: Optional[Asteroid] = None
    _teammates_targets: list = []
    except_targets: list = []

    def move_at(self, target, speed=None):
        if isinstance(target, Point):
            vec = Vector.from_points(self.coord, target, module=1)
        else:
            self.target = target
            vec = Vector.from_points(self.coord, target.coord, module=1)

        self.vector = vec
        super().move_at(target=target, speed=speed)

    @property
    def mode(self) -> DroneMode:
        return self._mode

    @mode.setter
    def mode(self, mode: DroneMode):
        self._mode = mode

    @property
    def target(self):
        """
            Метод-свойство возвращает астероид-цель.
        :return: Asteroid
        """
        return self._target

    @target.setter
    def target(self, target):
        self._target = target

    @property
    def teammates_targets(self) -> List[Asteroid]:
        """
            Возвращает список астероидов к которым летят другие дроиды из команды
        :return:
        """
        self._teammates_targets = []
        for teammate in self.teammates:
            self._teammates_targets.append(teammate.target)

        return self._teammates_targets

    def available_targets(self) -> List[Asteroid]:
        targets = [obj for obj in self.scene.objects
                   if obj.team != self.team and not obj.is_empty and obj not in self.except_targets]

        return targets

    def closest_target(self) -> Optional[Asteroid]:
        """
            Возвращает ближайщий к дрону астероид
        :return: Asteroid
        """
        asteroids = self.available_targets()

        if not asteroids:
            return None

        closest = asteroids[0]

        for asteroid in asteroids:
            if self.distance_to(closest) > self.distance_to(asteroid):
                closest = asteroid

        return closest

    def count_teammates(self, asteroid):
        """
            Считает количество дронов-однокомандников, летящих на один и тот-же астероид
        :param asteroid: Астероид для которого надо провести подсчет
        :return: Количество в виде dict('quantity': int, 'teammates': list, 'free_space': int)
        """
        free_space = 0
        teammates = [teammate for teammate in self.teammates if teammate.target == asteroid]

        for teammate in teammates:
            free_space += teammate.free_space

        return {'quantity': len(teammates), 'teammates': teammates, 'free_space': free_space}

    def get_target(self):
        closest = self.closest_target()

        if not closest:
            return []

        if closest not in self.teammates_targets:
            self.target = closest
        else:
            closest_info = self.count_teammates(closest)
            if closest.payload > closest_info['free_space']:
                self.target = closest
            else:
                if self.target:
                    if self.target in self.except_targets:
                        self.except_targets.remove(self.target)

                self.except_targets.append(closest)
                self.target = self.closest_target()

        return self.target

    @property
    def attack_point(self) -> Point:
        return self._attack_point

    @attack_point.setter
    def attack_point(self, point: Point):
        self._attack_point = point

    def shot(self, enemy):
        vector = Vector.from_points(self.coord, enemy.coord, module=1)
        self.vector = vector
        able_to_shot = True

        for teammate in self.teammates:
            vector = Vector.from_points(self.coord, teammate.coord, module=1)
            difference = abs(self.vector.direction - vector.direction)
            distance = self.distance_to(teammate)
            if difference < 15 and distance < self.gun.shot_distance:
                able_to_shot = False
                break

        if able_to_shot and self.distance_to(enemy) <= self.gun.shot_distance:
            self.gun.shot(enemy)
        else:
            self.move_at(self.attack_point)

    def _calculate_statistics(self, destination):
        if self.is_empty:
            IshmukhamedovDrone.empty_travel += self.distance_to(destination)
        elif self.is_full:
            IshmukhamedovDrone.full_travel += self.distance_to(destination)
        else:
            IshmukhamedovDrone.underload_travel += self.distance_to(destination)

    def get_statistics(self):
        stat = [self.empty_travel, self.full_travel, self.underload_travel]
        return stat

    @property
    def commander(self) -> Commander:
        return self._commander

    @commander.setter
    def commander(self, commander: Commander):
        self._commander = commander

    def on_hearbeat(self):
        self.scene._prev_endgame_state['countdown'] = 260

    def on_born(self):
        self.commander = Commander(drone=self)

        if self.have_gun:
            self.mode = DroneMode.DRONE_INTERCEPTOR
            self.attack_point = self.commander.get_attack_point(drone=self)
            self.move_at(self.attack_point)
        else:
            self.move_at(self.get_target())

    def on_stop(self):
        if self.mode == DroneMode.DRONE_INTERCEPTOR:
            if self.health < 75:
                self.move_at(self.my_mothership)
            else:
                if self.distance_to(self.commander.enemy) <= self.gun.shot_distance:
                    if self.commander.enemy.is_alive:
                        self.shot(self.commander.enemy)
                    else:
                        self.attack_point = self.commander.get_attack_point(drone=self)
                        self.move_at(self.attack_point)
                else:
                    self.attack_point = self.commander.get_attack_point(drone=self)
                    self.move_at(self.attack_point)
        else:
            self.move_at(self.my_mothership)

    def on_stop_at_target(self, target):
        for asteroid in self.asteroids:
            if asteroid.near(target):
                self.on_stop_at_asteroid(asteroid)
                return
        else:
            for ship in self.scene.motherships:
                if ship.near(target):
                    if ship == self.my_mothership:
                        self.on_stop_at_mothership(ship)
                    else:
                        self.on_stop_at_enemy_mothership(ship)

                    return

        self.on_stop_at_point(target)

    def on_stop_at_enemy_mothership(self, mothership):
        if not mothership.is_alive:
            self.load_from(mothership)

    def on_stop_at_point(self, target):
        if self.mode == DroneMode.DRONE_HARVESTER:
            enemy_drones = [drone for drone in self.scene.drones if drone not in self.teammates and not drone.is_empty]
            for drone in enemy_drones:
                if drone.near(target):
                    self.on_stop_at_enemy_drone(drone)
                    return

    def on_stop_at_asteroid(self, asteroid):
        if self.mode == DroneMode.DRONE_INTERCEPTOR:
            self.on_stop()
        else:
            self.load_from(asteroid)

    def on_stop_at_enemy_drone(self, drone):
        self.load_from(drone)

    def on_load_complete(self):
        if self.is_full:
            self.move_at(self.my_mothership)
        else:
            target = self.get_target()
            if target:
                self.move_at(target)
            else:
                self.move_at(self.my_mothership)

        self.target = None

    def on_stop_at_mothership(self, mothership):
        if self.mode == DroneMode.DRONE_INTERCEPTOR:
            self.attack_point = self.commander.get_attack_point(drone=self)
            self.move_at(self.attack_point)
        else:
            if self.is_empty:
                target = self.get_target()
                if target:
                    self.move_at(target)
                else:
                    self.on_stop()
            else:
                if mothership is self.my_mothership:
                    self.unload_to(mothership)
                else:
                    self.load_from(mothership)

    def on_unload_complete(self):
        target = self.get_target()
        if target:
            self.move_at(target)
        else:
            self.stop()

    def on_wake_up(self):
        if self.mode == DroneMode.DRONE_INTERCEPTOR:
            self.on_stop()
        else:
            self.move_at(self.my_mothership)


drone_class = IshmukhamedovDrone