# -*- coding: utf-8 -*-avsivkov
"""Модуль содержит класс дрона 'SivkovDrone', управляющий его поведением"""

from astrobox.core import Drone, MotherShip
from robogame_engine.geometry import Point, Vector
from astrobox.themes.default import MOTHERSHIP_HEALING_DISTANCE
from robogame_engine.theme import theme
from math import tan, sin, radians


class SivkovDrone(Drone):
    """Дрон"""
    total_drones = 0
    first_enemy_base = None
    second_enemy_base = None
    diagonal_enemy_base = None
    number_of_teams = None
    base_position = None
    ignore_list = []
    attack_direction = None
    position_handler = None
    change_position = True
    total_enemies = None
    sector_available = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        SivkovDrone.total_drones += 1
        self.serial_number = SivkovDrone.total_drones
        self.enemy = None
        self.target = None
        self.role = None
        self.position = None
        self.total_shots = 0
        self.trouble = 0
        self.retreat = False
        self.fly_on_drone = False

    def on_born(self):
        """Начало деятельности дрона"""
        if self.serial_number == 1:
            self._data_collection()

    def on_stop_at_asteroid(self, asteroid):
        """Дрон приземлился на астеройд"""
        if self.role == 'driller':
            if self.fly_on_drone:
                self.on_stop_at_point(self.target)
            else:
                self.target = None
                self.load_from(asteroid)

    def on_stop_at_point(self, target):
        if isinstance(self.target, Drone) and self.target.payload:
            self.load_from(self.target)
            self.target = None
            self.fly_on_drone = False

    def game_step(self):
        """Если больно бежим на базу"""
        super().game_step()
        if self.role != 'defender' and self.is_alive:
            if self.health < 100:
                self._retreat()
            elif self._can_take:
                self.target = None
                self.role = 'collector'
                self._tactic__robbery()
            elif self.target and self.target.payload:
                self._retreat_strategy()
            else:
                self.target = None
        else:
            if self.health < 30:
                self.move_at(self.my_mothership)

    def _retreat(self):
        """Дрон отступает"""
        self.retreat = True
        if self.role != 'collector':
            self.trouble += 1
        self.move_at(self.my_mothership)

    def _retreat_strategy(self):
        """Логика дрона при отступлении"""
        if self.trouble > 350:
            self.trouble = 0
            SivkovDrone.ignore_list.append(self.target.id)
            self.target = None
        elif self.target.id in SivkovDrone.ignore_list or not self.target.payload:
            self.target = None
        elif self.retreat:
            if self.payload > 50:
                self.target = None
            elif self.health == 100:
                self.move_at(self.target)
            self.retreat = False

    def on_load_complete(self):
        """Загрузка руды завершена"""
        if self.role == 'driller':
            if self.free_space:
                self._get_asteroid()
                if self.target:
                    self.move_at(self.target)
            if not self.target or not self.free_space:
                self.move_at(self.my_mothership)

    def on_stop_at_mothership(self, mothership):
        """Дрон приземлился на главный корабль"""
        if self.role == 'driller':
            if self.payload:
                self.trouble = 0
                self.unload_to(mothership)
            elif self._can_take:
                self.role = 'collector'
                self._tactic__robbery()
            elif not self.payload:
                if self.target and (self.target.id in SivkovDrone.ignore_list or not self.target.payload):
                    self.target = None

    def on_unload_complete(self):
        """Выгрузка руды завершена"""
        if self.role == 'driller':
            self._get_asteroid()
            if self.target:
                self.move_at(self.target)
            else:
                self.role = 'defender'

    def on_wake_up(self):
        """Дрон бездействует"""
        if self.role == 'driller':
            if self.target:
                if self.distance_to(self.target) < 10:
                    self.load_from(self.target)
                else:
                    self.move_at(self.target)
            elif not self.target:
                self._get_asteroid()
                if not self.target:
                    self.role = 'defender'
            else:
                self.move_at(self.my_mothership)
        else:
            self._tactic__defense()

    def _data_collection(self):
        """Собирает необходимые данные для координации дронов"""
        SivkovDrone.base_position = get_bases_position(base=self.my_mothership)
        self._get_position_handler()
        SivkovDrone.number_of_teams = len(self.scene.drones) // SivkovDrone.total_drones
        SivkovDrone.total_enemies = SivkovDrone.number_of_teams - 1
        self._explore_enemy_position()
        SivkovDrone.position_handler.get_available_sector(drone=self)

    def _get_position_handler(self):
        """Подбирает класс-обработчик позиций дронов для текущего полложения базы"""
        if SivkovDrone.base_position == ('right', 'down'):
            SivkovDrone.position_handler = PositionRightDown(mothership=self.my_mothership)
        elif SivkovDrone.base_position == ('left', 'down'):
            SivkovDrone.position_handler = PositionLeftDown(mothership=self.my_mothership)
        elif SivkovDrone.base_position == ('left', 'up'):
            SivkovDrone.position_handler = PositionLeftUp(mothership=self.my_mothership)
        else:
            SivkovDrone.position_handler = PositionRightUp(mothership=self.my_mothership)

    def _explore_enemy_position(self):
        """Собирает данные о расположении врагов"""
        work_list = [(self.distance_to(base), base) for base in self.scene.motherships if self.team != base.team]
        work_list.sort(key=lambda x: x[0])
        if work_list[0][1].coord.y != self.my_mothership.coord.y:
            SivkovDrone.first_enemy_base = work_list[0][1]
        else:
            SivkovDrone.second_enemy_base = work_list[0][1]
        if SivkovDrone.number_of_teams < 4 and len(work_list) > 1:
            if work_list[1][1].coord.x != self.my_mothership.coord.x \
                    and work_list[1][1].coord.y != self.my_mothership.coord.y:
                SivkovDrone.diagonal_enemy_base = work_list[1][1]
            else:
                if SivkovDrone.first_enemy_base:
                    SivkovDrone.second_enemy_base = work_list[1][1]
                else:
                    SivkovDrone.first_enemy_base = work_list[1][1]
        else:
            if len(work_list) > 1:
                if SivkovDrone.first_enemy_base:
                    SivkovDrone.second_enemy_base = work_list[1][1]
                else:
                    SivkovDrone.first_enemy_base = work_list[1][1]
            if len(work_list) > 2:
                SivkovDrone.diagonal_enemy_base = work_list[-1][1]
        get_attack_direction()

    def _get_asteroid(self):
        """Выдаёт дрону астеройд"""
        self.trouble = 0
        work_list = [(self.distance_to(asteroid), asteroid) for asteroid in self.asteroids if asteroid.payload
                     and self.position_handler.target_available(target=asteroid)]
        work_list.sort(key=lambda x: x[0])
        for asteroid in work_list:
            if asteroid[1].payload == 0:
                continue
            elif asteroid[1].id in SivkovDrone.ignore_list:
                continue
            else:
                self.target = asteroid[1]
                break
        if not self.target:
            crashed_drones = [(self.distance_to(drone), drone) for drone in self.scene.drones if not drone.is_alive
                              and self.position_handler.target_available(target=drone) and drone.payload
                              and drone.id not in SivkovDrone.ignore_list]
            if crashed_drones:
                crashed_drones.sort(key=lambda x: x[0])
                self.target = crashed_drones[0][1]
                self.fly_on_drone = True

    def _tactic__defense(self):
        """Тактика обороны"""
        self._count_enemies()
        SivkovDrone.position_handler.get_available_sector(drone=self)
        if self.role not in ['defender', 'collector', 'driller']:
            self.position = SivkovDrone.position_handler.get_position(position=self.serial_number)
            self.role = 'defender'
        elif self.serial_number in [4, 5] and self._are_asteroids_available() and not self._can_take:
            self.role = 'driller'
        elif self.role == 'defender':
            if self.distance_to(self.position) > 5:
                self.move_at(self.position)
            elif self.serial_number == 3 and self.my_mothership.health < 1000 and SivkovDrone.change_position:
                if SivkovDrone.attack_direction == 'up/down':
                    SivkovDrone.attack_direction = 'left/right'
                else:
                    SivkovDrone.attack_direction = 'up/down'
                SivkovDrone.change_position = False
                self.position = SivkovDrone.position_handler.get_position(position=self.serial_number)
            elif self._can_take and ((self.serial_number not in [1, 2] and self.my_mothership.health > 1500)
                                     or self.serial_number not in [1, 2, 3]):
                self.role = 'collector'
                self._get_target()
                self.move_at(self.target)
            elif self.enemy and self._checking_the_trajectory_of_the_shot(enemy=self.enemy):
                self._shoot()
            else:
                self.enemy = None
                self._get_enemy()
        elif self.role == 'collector':
            self._tactic__robbery()

    @property
    def _can_take(self):
        """Проверяет безопасно ли тащить рессурс с вражеской базы"""
        if (SivkovDrone.first_enemy_base and not SivkovDrone.first_enemy_base.is_alive
            and SivkovDrone.first_enemy_base.payload) \
                or (SivkovDrone.second_enemy_base and not SivkovDrone.second_enemy_base.is_alive
                    and SivkovDrone.second_enemy_base.payload):
            return True
        return False

    def _are_asteroids_available(self):
        """Проверяет доступны ли астеройды с рудой"""
        asteroids = [asteroid for asteroid in self.asteroids if asteroid.payload
                     and self.position_handler.target_available(target=asteroid)
                     and asteroid.id not in SivkovDrone.ignore_list]
        crashed_drones = [drone for drone in self.scene.drones if not drone.is_alive and drone.payload
                          and self.position_handler.target_available(target=drone)
                          and drone.id not in SivkovDrone.ignore_list]
        if (asteroids or crashed_drones) and self.role != 'collector':
            return True
        return False

    def _checking_the_trajectory_of_the_shot(self, enemy):
        """Проверяет не попадёт ли выстрел в союзника"""
        if self.distance_to(enemy) > self.gun.shot_distance:
            return False
        vector_to_enemy = Vector.from_points(self.coord, enemy.coord)
        for teammate in self.teammates:
            if teammate.is_alive:
                vector_to_teammate = Vector.from_points(self.coord, teammate.coord)
                if vector_to_teammate.module < vector_to_enemy.module \
                        and abs(vector_to_enemy.direction - vector_to_teammate.direction) < 180:
                    degree = abs(vector_to_enemy.direction - vector_to_teammate.direction) / 2
                    if (2 * vector_to_teammate.module * tan(radians(degree)) * sin(radians(90 - degree))) \
                            < self.radius + 10:
                        return False
        else:
            if self._all_teammates_at_home:
                self._fire_adjustment(enemy=enemy)
            else:
                self.turn_to(enemy)
            return True

    def _count_enemies(self):
        """Проверяет уменьшилось ли количество врагов"""
        number_of_enemies = len([base for base in self.scene.motherships if base.team != self.team
                                 and self.danger_from_enemy_mothership(base)])
        if number_of_enemies < SivkovDrone.total_enemies:
            if SivkovDrone.ignore_list:
                SivkovDrone.ignore_list = []
            SivkovDrone.total_enemies = number_of_enemies
        if SivkovDrone.number_of_teams == 2 and not SivkovDrone.sector_available:
            enemies = len([drone for drone in self.scene.drones if drone.team != self.team and drone.is_alive])
            if len(self.teammates) + 1 - enemies >= 2:
                SivkovDrone.sector_available = True
                SivkovDrone.ignore_list = []

    def _fire_adjustment(self, enemy):
        """Добавляет небольшое отклонение при наведении на врага"""
        if isinstance(enemy, MotherShip) and self.serial_number in [1, 2, 4, 5]:
            self._drunk_shooter(enemy=enemy)
        else:
            enemy_base = [base for base in self.scene.motherships if base.team == enemy.team]
            x = get_target_coordinate(coordinate=enemy.coord.x, base_coordinate=enemy_base[0].coord.x)
            y = get_target_coordinate(coordinate=enemy.coord.y, base_coordinate=enemy_base[0].coord.y)
            self.turn_to(Point(x, y))

    def _drunk_shooter(self, enemy):
        """Стреляет не очевидным способом по главному кораблю"""
        enemy_position = get_bases_position(enemy)
        correction_x, correction_y = SivkovDrone.position_handler.get_correction()
        if self.base_position[0] != enemy_position[0]:
            if self.serial_number == 1:
                self.turn_to(Point(enemy.coord.x, enemy.coord.y - correction_y))
            elif self.serial_number == 4:
                self.turn_to(Point(enemy.coord.x, enemy.coord.y + correction_y))
        else:
            if self.serial_number == 2:
                self.turn_to(Point(enemy.coord.x + correction_x, enemy.coord.y))
            elif self.serial_number == 5:
                self.turn_to(Point(enemy.coord.x - correction_x, enemy.coord.y))

    def _tactic__robbery(self):
        """Сбор рессурсов (грабёж)"""
        if not self.target:
            self._get_target()
            if not self.target:
                self.role = 'defender'
        elif self.my_mothership.health < 1000 and self.serial_number == 3:
            self.role = 'defender'
        elif self.payload and self.distance_to(self.my_mothership) < 20:
            self.unload_to(self.my_mothership)
        elif self.distance_to(self.my_mothership) < 20:
            if self.target.payload:
                self.move_at(self.target)
            else:
                self.target = None
        elif self.payload == 100 or self.target.payload == 0:
            self.move_at(self.my_mothership)
        elif self.distance_to(self.target) < 20 and self.free_space:
            self.load_from(self.target)
        else:
            self.move_at(self.my_mothership)

    def _get_enemy(self):
        """Определяет дрону цель"""
        self.total_shots = 0
        self._get_enemy_drone()
        if not self.enemy:
            self._get_enemy_base()

    def _get_enemy_base(self):
        """Ищет подходящую вражескую базу"""
        enemy_base = [(self.distance_to(base), base) for base in self.scene.motherships if
                      base.team != self.team and base.is_alive]
        if enemy_base:
            enemy_base.sort(key=lambda x: x[0])
            for base in enemy_base:
                if self._checking_the_trajectory_of_the_shot(enemy=base[1]):
                    self.enemy = base[1]
                    break

    def _get_enemy_drone(self):
        """Ищет подходящего вражеского дрона"""
        enemies = [(self.distance_to(drone), drone) for drone in self.scene.drones if drone.team != self.team
                   and drone.is_alive]
        if enemies:
            enemies.sort(key=lambda x: x[0])
            for enemy in enemies:
                base = [base for base in self.scene.motherships if base.team == enemy[1].team and base.is_alive]
                if base:
                    vector = Vector.from_points(enemy[1].coord, base[0].coord)
                    if vector.module < MOTHERSHIP_HEALING_DISTANCE:
                        continue
                if self._checking_the_trajectory_of_the_shot(enemy=enemy[1]):
                    self.enemy = enemy[1]
                    break

    def _get_target(self):
        """Определяет цель для сбора рессурса"""
        self.trouble = 0
        enemy_bases = [(self.distance_to(base), base) for base in self.scene.motherships if base.team != self.team
                       and base.payload and not base.is_alive and base.id not in SivkovDrone.ignore_list]
        if enemy_bases:
            self.target = enemy_bases[0][1]

    def _shoot(self):
        """Дрон делает выстрел"""
        if SivkovDrone.number_of_teams == 2:
            shots = 1
        else:
            shots = 3
        if self.enemy.is_alive and self.total_shots < shots:
            self.total_shots += 1
            self.gun.shot(self.enemy)
        else:
            self.enemy = None
            self._get_enemy()

    @property
    def _all_teammates_at_home(self):
        """Проверяет все ли союзники находяться в пределах действия защиты от базы"""
        total_drone = len([drone for drone in self.teammates if drone.is_alive])
        drones_at_home = []
        for teammate in self.teammates:
            vector = Vector.from_points(teammate.coord, self.my_mothership.coord)
            if vector.module < MOTHERSHIP_HEALING_DISTANCE:
                drones_at_home.append(teammate)
        if total_drone == len(drones_at_home):
            return True
        return False

    def _enemies_scanner(self, base):
        """Проверяет живы ли дроны, относящися к запрашиваемой базе"""
        enemies = [drone for drone in self.scene.drones if drone.team == base.team and drone.is_alive]
        if enemies:
            return True
        return False

    def danger_from_enemy_mothership(self, base):
        """Проверяет несёт ли команда, которой принадлежит база угрозу"""
        if base and base.is_alive and self._enemies_scanner(base=base):
            return True
        return False


def get_bases_position(base):
    """Определяет в каком углу расположена база"""
    if base.x == 90 and base.y == 90:
        return 'left', 'down'
    elif base.y == 90 and base.x != 90:
        return 'right', 'down'
    elif base.x == 90 and base.y != 90:
        return 'left', 'up'
    else:
        return 'right', 'up'


def get_attack_direction():
    """Определяет позицию предполагаемого 'основного' врага"""
    if SivkovDrone.first_enemy_base:
        SivkovDrone.attack_direction = 'up/down'
    else:
        SivkovDrone.attack_direction = 'left/right'


def get_target_coordinate(coordinate, base_coordinate):
    """Возращает измененную координату для стрельбы с упреждением"""
    correction = 40
    if coordinate - base_coordinate > 200:
        coord = coordinate - correction
    elif base_coordinate - coordinate > 200:
        coord = coordinate + correction
    else:
        coord = coordinate
    return coord


class PositionRightDown:
    """Позиция правый нижний угол"""

    def __init__(self, mothership):
        self.available_x = None
        self.available_y = None
        self.mothership = mothership
        self.correction = 78

    def get_correction(self):
        """Даёт корректировку методу _drunk_shooter"""
        return -self.correction, self.correction

    def target_available(self, target):
        """Проверяет находиться ли цель в секторе для сбора рессурсов"""
        if SivkovDrone.number_of_teams == 2 and not SivkovDrone.sector_available:
            if target.coord.x > self.available_x and 400 < target.coord.y < self.available_y:
                return True
            return False
        else:
            if target.coord.x > self.available_x and target.coord.y < self.available_y:
                return True
            return False

    def get_available_sector(self, drone):
        """Определяет сектор для сбора рессурса"""
        self.get_available_x(drone)
        self.get_available_y(drone)

    def get_available_y(self, drone):
        if not SivkovDrone.danger_from_enemy_mothership(drone, SivkovDrone.diagonal_enemy_base) \
                and not SivkovDrone.danger_from_enemy_mothership(drone, SivkovDrone.first_enemy_base):
            self.available_y = theme.FIELD_HEIGHT
        elif not SivkovDrone.danger_from_enemy_mothership(drone, SivkovDrone.first_enemy_base):
            self.available_y = theme.FIELD_HEIGHT if theme.FIELD_WIDTH - theme.FIELD_HEIGHT >= 500 \
                else theme.FIELD_HEIGHT - 1 / 2 * theme.FIELD_HEIGHT
        else:
            self.available_y = theme.FIELD_HEIGHT - 2 / 3 * theme.FIELD_HEIGHT

    def get_available_x(self, drone):
        if not SivkovDrone.danger_from_enemy_mothership(drone, SivkovDrone.diagonal_enemy_base) \
                and not SivkovDrone.danger_from_enemy_mothership(drone, SivkovDrone.second_enemy_base):
            self.available_x = 0
        elif not SivkovDrone.danger_from_enemy_mothership(drone, SivkovDrone.second_enemy_base):
            self.available_x = theme.FIELD_WIDTH - 1 / 2 * theme.FIELD_WIDTH
        else:
            self.available_x = theme.FIELD_WIDTH - 2 / 3 * theme.FIELD_WIDTH if SivkovDrone.number_of_teams == 2 \
                else theme.FIELD_WIDTH - 1 / 3 * theme.FIELD_WIDTH

    def get_position(self, position):
        """Определяет позицию дрона в обороне"""
        if position == 1:
            return Point(self.mothership.coord.x - 167, self.mothership.coord.y + 109)
        elif position == 2:
            return Point(self.mothership.coord.x - 109, self.mothership.coord.y + 167)
        elif position == 3 and SivkovDrone.attack_direction == 'up/down':
            return Point(self.mothership.coord.x - 30, self.mothership.coord.y + 197)
        elif position == 3 and SivkovDrone.attack_direction == 'left/right':
            return Point(self.mothership.coord.x - 197, self.mothership.coord.y + 30)
        elif position == 4:
            return Point(self.mothership.coord.x - 194, self.mothership.coord.y - 47)
        elif position == 5:
            return Point(self.mothership.coord.x + 47, self.mothership.coord.y + 194)


class PositionLeftDown(PositionRightDown):
    """Позиция левый нижний угол"""

    def get_correction(self):
        return self.correction, -self.correction

    def target_available(self, target):
        if SivkovDrone.number_of_teams == 2 and not SivkovDrone.sector_available:
            if target.coord.x < self.available_x and 400 < target.coord.y < self.available_y:
                return True
            return False
        else:
            if target.coord.x < self.available_x and target.coord.y < self.available_y:
                return True
            return False

    def get_available_x(self, drone):
        if not SivkovDrone.danger_from_enemy_mothership(drone, SivkovDrone.diagonal_enemy_base) \
                and not SivkovDrone.danger_from_enemy_mothership(drone, SivkovDrone.second_enemy_base):
            self.available_x = theme.FIELD_WIDTH
        elif not SivkovDrone.danger_from_enemy_mothership(drone, SivkovDrone.second_enemy_base):
            self.available_x = theme.FIELD_WIDTH - 1 / 2 * theme.FIELD_WIDTH
        else:
            self.available_x = theme.FIELD_WIDTH - 1 / 3 * theme.FIELD_WIDTH if SivkovDrone.number_of_teams == 2 \
                else theme.FIELD_WIDTH - 2 / 3 * theme.FIELD_WIDTH

    def get_position(self, position):
        if position == 1:
            return Point(self.mothership.coord.x + 167, self.mothership.coord.y + 109)
        elif position == 2:
            return Point(self.mothership.coord.x + 109, self.mothership.coord.y + 167)
        elif position == 3 and SivkovDrone.attack_direction == 'up/down':
            return Point(self.mothership.coord.x + 30, self.mothership.coord.y + 197)
        elif position == 3 and SivkovDrone.attack_direction == 'left/right':
            return Point(self.mothership.coord.x + 197, self.mothership.coord.y + 30)
        elif position == 4:
            return Point(self.mothership.coord.x + 194, self.mothership.coord.y - 47)
        elif position == 5:
            return Point(self.mothership.coord.x - 47, self.mothership.coord.y + 194)


class PositionLeftUp(PositionLeftDown):
    """Позиция левый верхний угол"""

    def get_correction(self):
        return self.correction, self.correction

    def target_available(self, target):
        if target.coord.x < self.available_x and target.coord.y > self.available_y:
            return True
        return False

    def get_available_y(self, drone):
        if not SivkovDrone.danger_from_enemy_mothership(drone, SivkovDrone.diagonal_enemy_base) \
                and not SivkovDrone.danger_from_enemy_mothership(drone, SivkovDrone.first_enemy_base):
            self.available_y = 0
        elif not SivkovDrone.danger_from_enemy_mothership(drone, SivkovDrone.first_enemy_base):
            self.available_y = 0 if theme.FIELD_WIDTH - theme.FIELD_HEIGHT >= 500 \
                else theme.FIELD_HEIGHT - 1 / 2 * theme.FIELD_HEIGHT
        else:
            self.available_y = theme.FIELD_HEIGHT - 1 / 3 * theme.FIELD_HEIGHT

    def get_position(self, position):
        if position == 1:
            return Point(self.mothership.coord.x + 167, self.mothership.coord.y - 109)
        elif position == 2:
            return Point(self.mothership.coord.x + 109, self.mothership.coord.y - 167)
        elif position == 3 and SivkovDrone.attack_direction == 'up/down':
            return Point(self.mothership.coord.x + 30, self.mothership.coord.y - 197)
        elif position == 3 and SivkovDrone.attack_direction == 'left/right':
            return Point(self.mothership.coord.x + 197, self.mothership.coord.y - 30)
        elif position == 4:
            return Point(self.mothership.coord.x + 194, self.mothership.coord.y + 47)
        elif position == 5:
            return Point(self.mothership.coord.x - 47, self.mothership.coord.y - 194)


class PositionRightUp(PositionRightDown):
    """Позиция правый верхний угол"""

    def get_correction(self):
        return -self.correction, self.correction

    def target_available(self, target):
        if target.coord.x > self.available_x and target.coord.y > self.available_y:
            return True
        return False

    def get_available_y(self, drone):
        if not SivkovDrone.danger_from_enemy_mothership(drone, SivkovDrone.diagonal_enemy_base) \
                and not SivkovDrone.danger_from_enemy_mothership(drone, SivkovDrone.first_enemy_base):
            self.available_y = 0
        elif not SivkovDrone.danger_from_enemy_mothership(drone, SivkovDrone.first_enemy_base):
            self.available_y = 0 if theme.FIELD_WIDTH - theme.FIELD_HEIGHT >= 500 \
                else theme.FIELD_HEIGHT - 1 / 2 * theme.FIELD_HEIGHT
        else:
            self.available_y = theme.FIELD_HEIGHT - 1 / 3 * theme.FIELD_HEIGHT

    def get_position(self, position):
        if position == 1:
            return Point(self.mothership.coord.x - 167, self.mothership.coord.y - 109)
        elif position == 2:
            return Point(self.mothership.coord.x - 109, self.mothership.coord.y - 167)
        elif position == 3 and SivkovDrone.attack_direction == 'up/down':
            return Point(self.mothership.coord.x - 30, self.mothership.coord.y - 197)
        elif position == 3 and SivkovDrone.attack_direction == 'left/right':
            return Point(self.mothership.coord.x - 197, self.mothership.coord.y - 30)
        elif position == 4:
            return Point(self.mothership.coord.x - 194, self.mothership.coord.y + 47)
        elif position == 5:
            return Point(self.mothership.coord.x + 47, self.mothership.coord.y - 194)


drone_class = SivkovDrone
