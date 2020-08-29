# -*- coding: utf-8 -*-
"""Модуль содержит логику поведения дрона 'SivkovDrone'"""

from astrobox.core import Drone, MotherShip
from robogame_engine.geometry import Point, Vector
from astrobox.themes.default import MOTHERSHIP_HEALING_DISTANCE
from robogame_engine.theme import theme
from math import tan, sin, radians, sqrt
from abc import ABC, abstractmethod

# НАСТРОЙКИ ДРОНА

# Общие параметры
BOTTOM_LINE_HEALTH_FOR_PEACEFUL_SHIP = 100
BOTTOM_LINE_HEALTH_FOR_WARSHIP = 30
NUMBER_OF_UNSUCCESSFUL_ATTEMPTS = 75
SUFFICIENT_SHIP_LOADING = 50
REQUIRED_NUMBER_OF_ENEMY_ACTIVITY_CHECKS = 25
NUMBER_SHOTS_BEFORE_CHANGE_ENEMY = 3
MAXIMUM_NUMBER_OF_ENEMIES_TO_START_COLLECTING = 7
CORECTION_SHOTS_FOR_ATTACK_MOTHERSHIP = 78
DISTANCE_ENEMY_TO_MOTHERSHIP__FOR_PREEMPTION_SHOT = 200
PREEMPTION_SHOT = 25
SAFE_ZONE_FOR_COLLECTING = 250
AVAILABLE_SECTOR__ONE_NEAREST_TEAM_DISABLED = 1 / 2
AVAILABLE_SECTOR__TWO_NEAREST_TEAM_ACTIVE = 1 / 3

# Тактика атаки
NUMBER_SHOTS_BEFORE_CHANGE_ENEMY__TACTIC_ASSAULT = 15
MINIMUM_STAGE_HEIGHT_FOR_SUCCESS = 700
SECTOR_TO_SELECT_THE_ENEMY = (90, 300)
MINIMAL_COORDINATE_NEAR_MOTHERSHIP = 192
DISTANCE_BETWEEN_DRONES = 80
DISTANCE_FOR_FIRST_DRONE = 47
CORRECTION_TO_THE_POSITION_OF_THE_OUTERMOST_SHIPS = 10

# При игре один на один
AVAILABLE_SECTOR__TWO_TEAM__START = 2 / 3
NUMBER_SHOTS_BEFORE_CHANGE_ENEMY__TWO_TEAM = 1
NUMERICAL_SUPERIORITY__TWO_TEAM = 2
SHELLING_SECTOR__TWO_TEAM = 350

# Позиция x для дронов в тактике защиты (положение 1: левый нижний угол)
POSITION_ONE = 167
POSITION_TWO = 109
POSITION_THREE__UR_DOWN = 30
POSITION_THREE__LEFT_RIGHT = 197
POSITION_FOUR = 194
POSITION_FIVE = 47


class SivkovDrone(Drone):

    """Основной класс дрона"""

    total_drones = 0
    first_enemy_base = None
    second_enemy_base = None
    diagonal_enemy_base = None
    number_of_teams = None
    base_position = None
    ignore_list = []
    attack_direction = None
    position_handler = None
    total_enemies = None
    sector_available = False
    one_enemy = None
    no_active_enemies = 0
    shots_at_enemy = 0
    victim = None
    targets = []
    checking_enemy_bases_health = 2000

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        SivkovDrone.total_drones += 1
        self.serial_number = SivkovDrone.total_drones
        self.enemy = None
        self.target = None
        self.tactic = None
        self.position = None
        self.total_shots = 0
        self.trouble = 0
        self.retreat = False
        self.fly_on_drone = False
        self.first_flight = True
        self.has_position = False

    def on_born(self):
        """Начало деятельности дрона"""
        if self.serial_number == 1:
            self._data_collection()
        if SivkovDrone.number_of_teams == 2:
            self.tactic = TacticDefense(drone=self)
            self.first_flight = False

    def on_stop_at_asteroid(self, asteroid):
        """Дрон приземлился на астеройд"""
        if not self.tactic:
            if self.fly_on_drone:
                self.on_stop_at_point(self.target)
            else:
                self.load_from(asteroid)
                self.turn_to(self.my_mothership)
                self.target = None

    def on_stop_at_point(self, target):
        """Дрон приземлился у разбитого дрона"""
        if isinstance(self.target, Drone) and self.target.payload:
            self.load_from(self.target)
            self.turn_to(self.my_mothership)
            self.target = None
            self.fly_on_drone = False

    def on_load_complete(self):
        """Загрузка руды завершена"""
        if not self.tactic:
            self._get_asteroid()
            if self.target:
                self.move_at(self.target)
            elif not self.free_space:
                self.move_at(self.my_mothership)

    def on_stop_at_mothership(self, mothership):
        """Дрон приземлился на главный корабль"""
        if self.payload:
            self.trouble = 0
            self.unload_to(mothership)
        if not self.tactic:
            if self.can_take:
                self.tactic = TacticRobbery(drone=self)
            elif self.target and (self.target.id in SivkovDrone.ignore_list or not self.target.payload):
                self.target = None
        if self.first_flight:
            self.first_flight = False
            self.tactic = TacticDefense(drone=self)

    def on_unload_complete(self):
        """Выгрузка руды завершена"""
        self.target = None
        if not self.tactic:
            self._get_asteroid()
            if self.target:
                self.move_at(self.target)
            else:
                self.tactic = TacticDefense(drone=self)

    def on_wake_up(self):
        """Дрон бездействует"""
        if not self.tactic:
            self._driller_wake_up()
        else:
            self.tactic.run()

    def _driller_wake_up(self):
        """Будит дрона сборщика"""
        if self.target:
            if self.distance_to(self.target) < 10:
                self.load_from(self.target)
            else:
                self.move_at(self.target)
        elif not self.target:
            self._get_asteroid()
            if not self.target:
                self.tactic = TacticDefense(drone=self)
        else:
            self.move_at(self.my_mothership)

    def game_step(self):
        """Если больно бежим на базу"""
        super().game_step()
        if not isinstance(self.tactic, (TacticDefense, TacticAssault)) and self.is_alive:
            if self.health < BOTTOM_LINE_HEALTH_FOR_PEACEFUL_SHIP:
                self._retreat()
            elif self.can_take and not isinstance(self.tactic, TacticRobbery):
                self.target = None
                self.tactic = TacticRobbery(drone=self)
            elif self.payload == 100:
                self.move_at(self.my_mothership)
            elif self.target:
                self._processing_target()
        else:
            if self.health < BOTTOM_LINE_HEALTH_FOR_WARSHIP:
                self.move_at(self.my_mothership)

    def _processing_target(self):
        """Проверка цели"""
        if self.target.payload:
            self._retreat_strategy()
        else:
            self.target = None
            self.move_at(self.my_mothership)

    def _retreat(self):
        """Дрон отступает"""
        self.retreat = True
        self.trouble += 1
        self.move_at(self.my_mothership)

    def _retreat_strategy(self):
        """Логика дрона при отступлении"""
        if self.trouble > NUMBER_OF_UNSUCCESSFUL_ATTEMPTS:
            self.trouble = 0
            SivkovDrone.ignore_list.append(self.target.id)
            self.target = None
        elif self.target.id in SivkovDrone.ignore_list or not self.target.payload:
            self.target = None
        elif self.retreat:
            if self.payload > SUFFICIENT_SHIP_LOADING:
                self.target = None
            elif self.health == 100:
                self.move_at(self.target)
            self.retreat = False

    def _data_collection(self):
        """Собирает необходимые данные для координации дронов"""
        SivkovDrone.base_position = get_bases_position(base=self.my_mothership)
        self._get_position_handler()
        SivkovDrone.number_of_teams = len(self.scene.drones) // SivkovDrone.total_drones
        SivkovDrone.total_enemies = len([drone for drone in self.scene.drones if drone.team != self.team
                                         and drone.is_alive])
        self._explore_enemy_position()
        SivkovDrone.position_handler.get_available_sector(drone=self)

    def _get_position_handler(self):
        """Подбирает класс-обработчик позиций дронов для текущего полложения базы"""
        if SivkovDrone.base_position == ('right', 'down'):
            SivkovDrone.position_handler = PositionRightDown(mothership=self.my_mothership, drone=self)
        elif SivkovDrone.base_position == ('left', 'down'):
            SivkovDrone.position_handler = PositionLeftDown(mothership=self.my_mothership, drone=self)
        elif SivkovDrone.base_position == ('left', 'up'):
            SivkovDrone.position_handler = PositionLeftUp(mothership=self.my_mothership, drone=self)
        else:
            SivkovDrone.position_handler = PositionRightUp(mothership=self.my_mothership, drone=self)

    def _explore_enemy_position(self):
        """Собирает данные о расположении врагов"""
        work_list = [(self.distance_to(base), base) for base in self.scene.motherships if self.team != base.team]
        work_list.sort(key=lambda x: x[0])
        if work_list[0][1].coord.y != self.my_mothership.coord.y:
            SivkovDrone.first_enemy_base = work_list[0][1]
        else:
            SivkovDrone.second_enemy_base = work_list[0][1]
        if SivkovDrone.number_of_teams < 4 and len(work_list) > 1:
            self._explore_enemy_position__less_than_four_teams(work_list)
        else:
            explore_enemy_position__four_teams(work_list)
        get_attack_direction()

    def _explore_enemy_position__less_than_four_teams(self, work_list):
        """Изучает расположение вражеских команд"""
        if work_list[1][1].coord.x != self.my_mothership.coord.x \
                and work_list[1][1].coord.y != self.my_mothership.coord.y:
            SivkovDrone.diagonal_enemy_base = work_list[1][1]
        else:
            if SivkovDrone.first_enemy_base:
                SivkovDrone.second_enemy_base = work_list[1][1]
            else:
                SivkovDrone.first_enemy_base = work_list[1][1]

    def _get_asteroid(self):
        """Выдаёт дрону астеройд"""
        self.trouble = 0
        if self.first_flight:
            work_list = [(self.distance_to(asteroid), asteroid) for asteroid in self.asteroids if asteroid.payload
                         and not self.position_handler.target_available(target=asteroid)]

        else:
            work_list = [(self.distance_to(asteroid), asteroid) for asteroid in self.asteroids if asteroid.payload
                         and self.position_handler.target_available(target=asteroid)]
        work_list.sort(key=lambda x: x[0])
        for asteroid in work_list:
            if asteroid[1].payload == 0 or asteroid[1].id in SivkovDrone.targets:
                continue
            elif asteroid[1].id in SivkovDrone.ignore_list:
                continue
            else:
                self.target = asteroid[1]
                if self.first_flight:
                    SivkovDrone.targets.append(asteroid[1].id)
                break
        if not self.target:
            crashed_drones = [(self.distance_to(drone), drone) for drone in self.scene.drones if not drone.is_alive
                              and self.position_handler.target_available(target=drone) and drone.payload
                              and drone.id not in SivkovDrone.ignore_list]
            if crashed_drones:
                crashed_drones.sort(key=lambda x: x[0])
                self.target = crashed_drones[0][1]
                self.fly_on_drone = True

    @property
    def can_take(self):
        """Проверяет безопасно ли тащить рессурс с вражеской базы"""
        if (SivkovDrone.first_enemy_base and not SivkovDrone.first_enemy_base.is_alive
            and SivkovDrone.first_enemy_base.payload) \
                or (SivkovDrone.second_enemy_base and not SivkovDrone.second_enemy_base.is_alive
                    and SivkovDrone.second_enemy_base.payload):
            return True
        return False

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

    def danger_from_enemy_mothership(self, base):
        """Проверяет несёт ли угрозу команда, которой принадлежит база"""
        if base and base.is_alive and self._enemies_scanner(base=base):
            return True
        return False

    def _enemies_scanner(self, base):
        """Проверяет живы ли дроны, относящися к запрашиваемой базе"""
        enemies = [drone for drone in self.scene.drones if drone.team == base.team and drone.is_alive]
        if enemies:
            return True
        return False

    def checking_the_trajectory_of_the_shot(self, enemy):
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
                            < self.radius + 10 or self.distance_to(teammate) < 45:
                        return False
        else:
            if self._all_teammates_at_home:
                self._fire_adjustment(enemy=enemy)
            else:
                self.turn_to(enemy)
            return True

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
        if self.base_position[0] != enemy_position[0]:
            correction_y = SivkovDrone.position_handler.correction_y
            if self.serial_number == 1:
                self.turn_to(Point(enemy.coord.x, enemy.coord.y - correction_y))
            elif self.serial_number == 4:
                self.turn_to(Point(enemy.coord.x, enemy.coord.y + correction_y))
        else:
            correction_x = SivkovDrone.position_handler.correction_x
            if self.serial_number == 2:
                self.turn_to(Point(enemy.coord.x + correction_x, enemy.coord.y))
            elif self.serial_number == 5:
                self.turn_to(Point(enemy.coord.x - correction_x, enemy.coord.y))

    def checking_enemy_activity(self):
        """Проверяет активность вражеских команд"""
        enemies = [drone for drone in self.scene.drones if drone.is_alive and drone.team != self.team]
        if enemies:
            self._analysis_of_the_situation(enemies)

    def _analysis_of_the_situation(self, enemies):
        """Увеличивает значение или сбрасывает счётчик активности врагов"""
        work_list = []
        for enemy in enemies:
            enemy_base = [base for base in self.scene.motherships if base.team == enemy.team]
            vector = Vector.from_points(enemy.coord, enemy_base[0].coord)
            if vector.module < MOTHERSHIP_HEALING_DISTANCE and enemy_base[0].is_alive:
                continue
            else:
                work_list.append(enemy)
        flag = True
        if SivkovDrone.first_enemy_base.health < SivkovDrone.checking_enemy_bases_health:
            flag = False
        SivkovDrone.checking_enemy_bases_health = SivkovDrone.first_enemy_base.health
        if not work_list and flag:
            SivkovDrone.no_active_enemies += 1
        else:
            SivkovDrone.no_active_enemies = 0


class Tactic(ABC):

    """Базовый класс для всех тактик"""

    def __init__(self, drone):
        self.drone = drone

    @abstractmethod
    def run(self):
        """Основная логика"""
        pass


class TacticDefense(Tactic):

    """Тактика обороны"""

    def run(self):
        checking_attack_direction()
        if self.drone.serial_number == 4 and SivkovDrone.number_of_teams != 2:
            self._checking_defense()
        self._count_enemies()
        if SivkovDrone.number_of_teams == 4:
            self.drone.checking_enemy_activity()
        SivkovDrone.position_handler.get_available_sector(drone=self.drone)
        if self.drone.payload:
            self.drone.move_at(self.drone.my_mothership)
        elif not self.drone.has_position:
            self.drone.position = SivkovDrone.position_handler.get_position(position=self.drone.serial_number)
            self.drone.has_position = True
        elif self._can_drill_asteroids:
            if SivkovDrone.targets:
                SivkovDrone.targets = []
            self.drone.tactic = None
        elif self.drone.distance_to(self.drone.position) > 10:
            self.drone.move_at(self.drone.position)
        elif self._can_rob_enemy:
            self.drone.tactic = TacticRobbery(drone=self.drone)
        elif self._can_attack_enemy(position='up/down'):
            self.drone.tactic = TacticAssault(drone=self.drone)
            SivkovDrone.victim = SivkovDrone.first_enemy_base.team
        elif self._can_attack_enemy(position='left/right'):
            self.drone.tactic = TacticAssault(drone=self.drone)
            SivkovDrone.victim = SivkovDrone.second_enemy_base.team
        elif self.drone.enemy and self.drone.checking_the_trajectory_of_the_shot(enemy=self.drone.enemy):
            self._shoot()
        else:
            self.drone.enemy = None
            self._get_enemy()

    def _checking_defense(self):
        """Проверка эффективности защиты"""
        if self._checking_teammate(serial_number=5):
            self._checking_teammate(serial_number=3)

    def _checking_teammate(self, serial_number):
        """Проверяет жив ли союзник"""
        teammate = [drone for drone in self.drone.scene.drones if drone.team == self.drone.team
                    and drone.serial_number == serial_number and not drone.is_alive]
        if teammate:
            self.drone.serial_number = serial_number
            self.drone.position = SivkovDrone.position_handler.get_position(position=self.drone.serial_number)
            return False
        return True

    def _count_enemies(self):
        """Проверяет уменьшилось ли количество врагов"""
        number_of_enemies = len([drone for drone in self.drone.scene.drones if drone.team != self.drone.team
                                 and drone.is_alive])
        if number_of_enemies < SivkovDrone.total_enemies:
            SivkovDrone.ignore_list = []
            SivkovDrone.total_enemies = number_of_enemies
        if SivkovDrone.number_of_teams == 2 and not SivkovDrone.sector_available:
            enemies = len(
                [drone for drone in self.drone.scene.drones if drone.team != self.drone.team and drone.is_alive])
            if len(self.drone.teammates) + 1 - enemies >= NUMERICAL_SUPERIORITY__TWO_TEAM:
                SivkovDrone.sector_available = True
                SivkovDrone.ignore_list = []

    @property
    def _can_drill_asteroids(self):
        """Пора бурить астеройды?"""
        if ((self.drone.serial_number in [4, 5] and SivkovDrone.number_of_teams > 2) or
            (self.drone.serial_number in [5, 2] and SivkovDrone.number_of_teams == 2)) \
                and self._are_asteroids_available() and not self.drone.can_take:
            return True
        return False

    @property
    def _can_rob_enemy(self):
        """Пора грабить врага?"""
        if self.drone.can_take and ((self.drone.serial_number not in [1, 2] and self.drone.my_mothership.health > 1500)
                                    or self.drone.serial_number not in [1, 2, 3]):
            return True
        return False

    def _can_attack_enemy(self, position):
        """Пора атаковать врага?"""
        if position == 'up/down':
            if SivkovDrone.number_of_teams != 2 \
                    and SivkovDrone.no_active_enemies >= REQUIRED_NUMBER_OF_ENEMY_ACTIVITY_CHECKS \
                    and not self._are_asteroids_available() and not self.drone.can_take \
                    and SivkovDrone.first_enemy_base.is_alive and SivkovDrone.total_drones >= 5 \
                    and SivkovDrone.attack_direction == 'up/down':
                return True
            return False
        else:
            if SivkovDrone.number_of_teams != 2 \
                    and SivkovDrone.no_active_enemies >= REQUIRED_NUMBER_OF_ENEMY_ACTIVITY_CHECKS \
                    and not self._are_asteroids_available() and not self.drone.can_take \
                    and SivkovDrone.second_enemy_base.is_alive and SivkovDrone.total_drones >= 5 \
                    and SivkovDrone.attack_direction == 'left/right':
                return True
            return False

    def _get_enemy(self):
        """Определяет дрону цель"""
        self.drone.total_shots = 0
        self._get_enemy_drone()
        if not self.drone.enemy:
            self._get_enemy_base()

    def _get_enemy_drone(self):
        """Ищет подходящего вражеского дрона"""
        enemies = [(self.drone.distance_to(drone), drone) for drone in self.drone.scene.drones if
                   drone.team != self.drone.team
                   and drone.is_alive]
        if enemies:
            enemies.sort(key=lambda x: x[0])
            self._analysis_of_the_enemy_location(enemies)

    def _analysis_of_the_enemy_location(self, enemies):
        """Проверяет массив врагов и выдаёт дрону цель"""
        for enemy in enemies:
            base = [base for base in self.drone.scene.motherships if base.team == enemy[1].team and base.is_alive]
            if base:
                vector = Vector.from_points(enemy[1].coord, base[0].coord)
                if vector.module < MOTHERSHIP_HEALING_DISTANCE:
                    continue
            if self.drone.checking_the_trajectory_of_the_shot(enemy=enemy[1]):
                self.drone.enemy = enemy[1]
                break

    def _get_enemy_base(self):
        """Ищет подходящую вражескую базу"""
        enemy_base = [(self.drone.distance_to(base), base) for base in self.drone.scene.motherships if
                      base.team != self.drone.team and base.is_alive]
        if enemy_base:
            enemy_base.sort(key=lambda x: x[0])
            self._analysis_of_the_enemy_base_location(enemy_base)

    def _analysis_of_the_enemy_base_location(self, enemy_base):
        """Проверяет массив вражеских баз и выдаёт дрону цель"""
        for base in enemy_base:
            if self.drone.checking_the_trajectory_of_the_shot(enemy=base[1]):
                self.drone.enemy = base[1]
                break

    def _are_asteroids_available(self):
        """Проверяет доступны ли астеройды с рудой"""
        work_list = []
        asteroids = [asteroid for asteroid in self.drone.asteroids if asteroid.payload
                     and self.drone.position_handler.target_available(target=asteroid)
                     and asteroid.id not in SivkovDrone.ignore_list]
        crashed_drones = [drone for drone in self.drone.scene.drones if not drone.is_alive and drone.payload
                          and self.drone.position_handler.target_available(target=drone)
                          and drone.id not in SivkovDrone.ignore_list]
        enemies = [enemy for enemy in self.drone.scene.drones if enemy.is_alive and enemy.team != self.drone.team]
        for asteroid in asteroids:
            if asteroid.coord.x < SAFE_ZONE_FOR_COLLECTING and asteroid.coord.y < SAFE_ZONE_FOR_COLLECTING:
                work_list.append(asteroid)
        for crashed_drone in crashed_drones:
            if crashed_drone.coord.x < SAFE_ZONE_FOR_COLLECTING and crashed_drone.coord.y < SAFE_ZONE_FOR_COLLECTING:
                work_list.append(crashed_drone)
        if asteroids or crashed_drones:
            if len(enemies) > MAXIMUM_NUMBER_OF_ENEMIES_TO_START_COLLECTING and not work_list:
                return False
            return True
        return False

    def _shoot(self):
        """Дрон делает выстрел"""
        if SivkovDrone.number_of_teams == 2:
            shots = NUMBER_SHOTS_BEFORE_CHANGE_ENEMY__TWO_TEAM
        else:
            shots = NUMBER_SHOTS_BEFORE_CHANGE_ENEMY
        if self.drone.enemy.is_alive and self.drone.total_shots < shots:
            self.drone.total_shots += 1
            self.drone.gun.shot(self.drone.enemy)
        else:
            self.drone.enemy = None
            self._get_enemy()


class TacticAssault(Tactic):

    """Тактика атаки"""

    def run(self):
        self.drone.checking_enemy_activity()
        self._command_check()
        if self.is_it_time_to_change_the_enemy:
            SivkovDrone.shots_at_enemy = 0
            SivkovDrone.one_enemy = None
        if SivkovDrone.total_drones < 5 or SivkovDrone.no_active_enemies < REQUIRED_NUMBER_OF_ENEMY_ACTIVITY_CHECKS:
            self._run_other_tactic(tactic=TacticDefense)
        elif not SivkovDrone.one_enemy:
            self._get_general_enemy()
            if not SivkovDrone.one_enemy:
                self._get_enemy_base_or_last_drones()
        elif SivkovDrone.one_enemy and self.drone.enemy != SivkovDrone.one_enemy \
                or self.drone.distance_to(self.drone.enemy) <= (self.drone.gun.shot_distance - 100):
            self.drone.enemy = SivkovDrone.one_enemy
            if SivkovDrone.attack_direction == 'up/down':
                self.drone.position = SivkovDrone.position_handler.get_position_attack(
                    coordinate='x', serial_number=self.drone.serial_number)
            else:
                self.drone.position = SivkovDrone.position_handler.get_position_attack(
                    coordinate='y', serial_number=self.drone.serial_number)
        elif self.drone.distance_to(self.drone.position) > 10:
            self.drone.move_at(self.drone.position)
        elif self.drone.enemy and self.drone.enemy.is_alive:
            self._shoot_to_the_enemy()
        else:
            self.drone.move_at(self.drone.my_mothership)

    def _command_check(self):
        """Уточняет количество живых членов команды"""
        SivkovDrone.total_drones = len(
            [drone for drone in self.drone.scene.drones if drone.team == self.drone.team and drone.is_alive])

    @property
    def is_it_time_to_change_the_enemy(self):
        """Проверяет не пора ли сменить врага"""
        if SivkovDrone.one_enemy and not SivkovDrone.one_enemy.is_alive \
                or SivkovDrone.shots_at_enemy >= NUMBER_SHOTS_BEFORE_CHANGE_ENEMY__TACTIC_ASSAULT:
            return True
        return False

    def _run_other_tactic(self, tactic):
        """Переводит дронов в тактику защиты"""
        self.drone.has_position = False
        self.drone.tactic = tactic(drone=self.drone)
        SivkovDrone.victim = None
        self.drone.move_at(self.drone.my_mothership)

    def _get_general_enemy(self):
        """Ищет подходящего вражеского дрона"""
        if theme.FIELD_HEIGHT >= MINIMUM_STAGE_HEIGHT_FOR_SUCCESS or self.drone.attack_direction == 'left/right':
            enemies = [(self.drone.distance_to(drone), drone) for drone in self.drone.scene.drones if
                       drone.team == SivkovDrone.victim and drone.is_alive]
        else:
            enemies = [(self.drone.coord.x, drone) for drone in self.drone.scene.drones if
                       drone.team == SivkovDrone.victim and drone.is_alive
                       and self.drone.position_handler.enemy_in_attack_sector(enemy=drone)]
        if enemies:
            enemies.sort(key=lambda x: x[0])
            SivkovDrone.one_enemy = enemies[0][1]

    def _get_enemy_base_or_last_drones(self):
        """Выдаёт в качестве цели вражесскую базу или остатки врагов"""
        base = [base for base in self.drone.scene.motherships if
                base.team == SivkovDrone.victim and base.is_alive]
        if base:
            SivkovDrone.one_enemy = base[0]
        else:
            enemies = [(self.drone.distance_to(enemy), enemy) for enemy in self.drone.scene.drones if
                       enemy.is_alive and enemy.team == SivkovDrone.victim]
            if enemies:
                enemies.sort(key=lambda x: x[0])
                SivkovDrone.one_enemy = enemies[0][1]
            else:
                self._collecting_trophies()

    def _collecting_trophies(self):
        """Запускает тактику грабежа"""
        if self.drone.serial_number in [1, 2]:
            self._run_other_tactic(tactic=TacticDefense)
        else:
            self._run_other_tactic(tactic=TacticRobbery)

    def _shoot_to_the_enemy(self):
        """Дрон стреляет"""
        self.drone.turn_to(self.drone.enemy)
        vector = Vector.from_points(self.drone.coord, self.drone.enemy.coord)
        if abs(self.drone.direction - vector.direction) <= 5 and self.drone.checking_the_trajectory_of_the_shot(
                enemy=self.drone.enemy):
            self.drone.gun.shot(self.drone.enemy)
        SivkovDrone.shots_at_enemy += 1


class TacticRobbery(Tactic):

    """Тактика грабежа"""

    def run(self):
        if not self.drone.target:
            self._get_target()
            if not self.drone.target:
                self.drone.tactic = TacticDefense(drone=self.drone)
        elif self.drone.my_mothership.health < 1000 and self.drone.serial_number == 3:
            self.drone.tactic = TacticDefense(drone=self.drone)
        elif self.drone.payload and self.drone.distance_to(self.drone.my_mothership) < 10:
            self.drone.unload_to(self.drone.my_mothership)
        elif self.drone.distance_to(self.drone.my_mothership) < 10:
            if self.drone.target.payload:
                self.drone.move_at(self.drone.target)
            else:
                self.drone.target = None
        elif self.drone.payload == 100 or self.drone.target.payload == 0:
            self.drone.move_at(self.drone.my_mothership)
        elif self.drone.distance_to(self.drone.target) < 10 and self.drone.free_space:
            self.drone.load_from(self.drone.target)
        else:
            self.drone.move_at(self.drone.my_mothership)

    def _get_target(self):
        """Определяет цель для сбора рессурса"""
        self.drone.trouble = 0
        enemy_bases = [(self.drone.distance_to(base), base) for base in self.drone.scene.motherships if
                       base.team != self.drone.team
                       and base.payload and not base.is_alive and base.id not in SivkovDrone.ignore_list]
        if enemy_bases:
            self.drone.target = enemy_bases[0][1]


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
    correction = PREEMPTION_SHOT
    if coordinate - base_coordinate > DISTANCE_ENEMY_TO_MOTHERSHIP__FOR_PREEMPTION_SHOT:
        coord = coordinate - correction
    elif base_coordinate - coordinate > DISTANCE_ENEMY_TO_MOTHERSHIP__FOR_PREEMPTION_SHOT:
        coord = coordinate + correction
    else:
        coord = coordinate
    return coord


def explore_enemy_position__four_teams(work_list):
    """Собирает данные о расположении врагов"""
    if len(work_list) > 1:
        if SivkovDrone.first_enemy_base:
            SivkovDrone.second_enemy_base = work_list[1][1]
        else:
            SivkovDrone.first_enemy_base = work_list[1][1]
    if len(work_list) > 2:
        SivkovDrone.diagonal_enemy_base = work_list[-1][1]


def checking_attack_direction():
    """Проверяет актуальность направления атаки"""
    if not SivkovDrone.second_enemy_base.is_alive and not SivkovDrone.first_enemy_base.is_alive:
        SivkovDrone.attack_direction = 'up/down'
    elif SivkovDrone.attack_direction == 'up/down' and not SivkovDrone.first_enemy_base.is_alive:
        SivkovDrone.attack_direction = 'left/right'
    elif SivkovDrone.attack_direction == 'left/right' and not SivkovDrone.second_enemy_base.is_alive:
        SivkovDrone.attack_direction = 'up/down'


class Position:

    """Базовый класс для всех обработчиков позиций"""

    def __init__(self, mothership, drone):
        self.available_x = None
        self.available_y = None
        self.mothership = mothership
        self.correction = CORECTION_SHOTS_FOR_ATTACK_MOTHERSHIP
        self.shot_distance = drone.gun.shot_distance

    @property
    def correction_x(self):
        """Даёт корректировку методу _drunk_shooter"""
        return

    @property
    def correction_y(self):
        """Даёт корректировку методу _drunk_shooter"""
        return

    def target_available(self, target):
        """Проверяет находиться ли цель в секторе для сбора рессурсов"""
        if SivkovDrone.number_of_teams == 2 and not SivkovDrone.sector_available:
            if self._checking_target_x(target=target) and self._checking_target_for_two_teams_y(target=target):
                return True
            return False
        elif self._target_in_safe_zone_x(target=target) and self._target_in_safe_zone_y(target=target):
            return True
        else:
            if self._checking_target_x(target=target) and self._checking_target_y(target=target):
                return True
            return False

    def _checking_target_x(self, target):
        return

    def _checking_target_for_two_teams_y(self, target):
        return

    def _checking_target_y(self, target):
        return

    def _target_in_safe_zone_x(self, target):
        return

    def _target_in_safe_zone_y(self, target):
        return

    def get_available_sector(self, drone):
        """Определяет сектор для сбора рессурса"""
        self._get_available_x(drone=drone)
        self._get_available_y(drone=drone)

    def _get_available_x(self, drone):
        pass

    def _get_available_y(self, drone):
        pass

    def get_position(self, position):
        """Определяет позицию дрона в обороне"""
        return Point(self._get_x(position=position), self._get_y(position=position))

    def _get_x(self, position):
        pass

    def _get_y(self, position):
        pass

    def get_position_attack(self, coordinate, serial_number):
        """Определяет позицию дрона в атаке"""
        if coordinate == 'x':
            return self._get_position_attack_front_y(serial_number=serial_number,
                                                     x=self._get_position_attack_front_x(serial_number=serial_number))
        else:
            return self._get_position_attack_flank_x(serial_number=serial_number,
                                                     y=self._get_position_attack_flank_y(serial_number=serial_number))

    def _get_position_attack_front_x(self, serial_number):
        pass

    def _get_position_attack_front_y(self, serial_number, x):
        pass

    def _get_position_attack_flank_y(self, serial_number):
        pass

    def _get_position_attack_flank_x(self, serial_number, y):
        pass

    def enemy_in_attack_sector(self, enemy):
        """Проверяет заслоняет ли вражеский дрон собой свою базу"""
        if self._enemy_in_attack_sector_x(enemy=enemy) and self._enemy_in_attack_sector_y(enemy=enemy):
            return True
        return False

    def _enemy_in_attack_sector_x(self, enemy):
        pass

    def _enemy_in_attack_sector_y(self, enemy):
        pass


class PositionLeft(Position):

    """Позиция левый край"""

    @property
    def correction_x(self):
        return self.correction

    def _checking_target_x(self, target):
        if target.coord.x < self.available_x:
            return True
        return False

    def _target_in_safe_zone_x(self, target):
        if target.coord.x < SAFE_ZONE_FOR_COLLECTING:
            return True
        return False

    def _get_available_x(self, drone):
        if not drone.danger_from_enemy_mothership(SivkovDrone.diagonal_enemy_base) \
                and not drone.danger_from_enemy_mothership(SivkovDrone.second_enemy_base):
            self.available_x = theme.FIELD_WIDTH
        elif not drone.danger_from_enemy_mothership(SivkovDrone.second_enemy_base):
            self.available_x = AVAILABLE_SECTOR__ONE_NEAREST_TEAM_DISABLED * theme.FIELD_WIDTH
        else:
            self.available_x = AVAILABLE_SECTOR__TWO_TEAM__START * theme.FIELD_WIDTH \
                if SivkovDrone.number_of_teams == 2 else AVAILABLE_SECTOR__TWO_NEAREST_TEAM_ACTIVE * theme.FIELD_WIDTH

    def _get_x(self, position):
        if position == 1:
            return self.mothership.coord.x + POSITION_ONE
        elif position == 2:
            return self.mothership.coord.x + POSITION_TWO
        elif position == 3 and SivkovDrone.attack_direction == 'up/down':
            return self.mothership.coord.x + POSITION_THREE__UR_DOWN
        elif position == 3 and SivkovDrone.attack_direction == 'left/right':
            return self.mothership.coord.x + POSITION_THREE__LEFT_RIGHT
        elif position == 4:
            return self.mothership.coord.x + POSITION_FOUR
        elif position == 5:
            return self.mothership.coord.x - POSITION_FIVE

    def _get_position_attack_front_x(self, serial_number):
        return (serial_number - 1) * DISTANCE_BETWEEN_DRONES + DISTANCE_FOR_FIRST_DRONE

    def _get_position_attack_flank_x(self, serial_number, y):
        x = SivkovDrone.one_enemy.coord.x - round(
            sqrt(self.shot_distance ** 2 - (y - SivkovDrone.one_enemy.coord.y) ** 2), 0) + 2
        if x < MINIMAL_COORDINATE_NEAR_MOTHERSHIP:
            x = MINIMAL_COORDINATE_NEAR_MOTHERSHIP
            if serial_number in [1, 5]:
                x += CORRECTION_TO_THE_POSITION_OF_THE_OUTERMOST_SHIPS
        return Point(x, y)

    def _enemy_in_attack_sector_x(self, enemy):
        if SECTOR_TO_SELECT_THE_ENEMY[0] <= enemy.coord.x <= SECTOR_TO_SELECT_THE_ENEMY[1]:
            return True
        return False


class PositionRight(Position):

    """Позиция правый край"""

    @property
    def correction_x(self):
        return - self.correction

    def _checking_target_x(self, target):
        if target.coord.x > self.available_x:
            return True
        return False

    def _target_in_safe_zone_x(self, target):
        if target.coord.x > theme.FIELD_WIDTH - SAFE_ZONE_FOR_COLLECTING:
            return True
        return False

    def _get_available_x(self, drone):
        if not drone.danger_from_enemy_mothership(SivkovDrone.diagonal_enemy_base) \
                and not drone.danger_from_enemy_mothership(SivkovDrone.second_enemy_base):
            self.available_x = 0
        elif not drone.danger_from_enemy_mothership(SivkovDrone.second_enemy_base):
            self.available_x = theme.FIELD_WIDTH - AVAILABLE_SECTOR__ONE_NEAREST_TEAM_DISABLED * theme.FIELD_WIDTH
        else:
            self.available_x = theme.FIELD_WIDTH - AVAILABLE_SECTOR__TWO_TEAM__START * theme.FIELD_WIDTH \
                if SivkovDrone.number_of_teams == 2 \
                else theme.FIELD_WIDTH - AVAILABLE_SECTOR__TWO_NEAREST_TEAM_ACTIVE * theme.FIELD_WIDTH

    def _get_x(self, position):
        if position == 1:
            return self.mothership.coord.x - POSITION_ONE
        elif position == 2:
            return self.mothership.coord.x - POSITION_TWO
        elif position == 3 and SivkovDrone.attack_direction == 'up/down':
            return self.mothership.coord.x - POSITION_THREE__UR_DOWN
        elif position == 3 and SivkovDrone.attack_direction == 'left/right':
            return self.mothership.coord.x - POSITION_THREE__LEFT_RIGHT
        elif position == 4:
            return self.mothership.coord.x - POSITION_FOUR
        elif position == 5:
            return self.mothership.coord.x + POSITION_FIVE

    def _get_position_attack_front_x(self, serial_number):
        return theme.FIELD_WIDTH - ((serial_number - 1) * DISTANCE_BETWEEN_DRONES + DISTANCE_FOR_FIRST_DRONE)

    def _get_position_attack_flank_x(self, serial_number, y):
        x = SivkovDrone.one_enemy.coord.x + round(
            sqrt(self.shot_distance ** 2 - (y - SivkovDrone.one_enemy.coord.y) ** 2), 0) - 2
        if x > theme.FIELD_WIDTH - MINIMAL_COORDINATE_NEAR_MOTHERSHIP:
            x = theme.FIELD_WIDTH - MINIMAL_COORDINATE_NEAR_MOTHERSHIP
            if serial_number in [1, 5]:
                x -= CORRECTION_TO_THE_POSITION_OF_THE_OUTERMOST_SHIPS
        return Point(x, y)

    def _enemy_in_attack_sector_x(self, enemy):
        if theme.FIELD_WIDTH - SECTOR_TO_SELECT_THE_ENEMY[1] <= enemy.coord.x \
                <= theme.FIELD_WIDTH - SECTOR_TO_SELECT_THE_ENEMY[0]:
            return True
        return False


class PositionUp(Position):

    """Позиция верх"""

    @property
    def correction_y(self):
        return self.correction

    def _checking_target_y(self, target):
        if target.coord.y > self.available_y:
            return True
        return False

    def _target_in_safe_zone_y(self, target):
        if target.coord.y > theme.FIELD_HEIGHT - SAFE_ZONE_FOR_COLLECTING:
            return True
        return False

    def _get_available_y(self, drone):
        if not drone.danger_from_enemy_mothership(SivkovDrone.diagonal_enemy_base) \
                and not drone.danger_from_enemy_mothership(SivkovDrone.first_enemy_base):
            self.available_y = 0
        elif not drone.danger_from_enemy_mothership(SivkovDrone.first_enemy_base):
            self.available_y = 0 if theme.FIELD_WIDTH - theme.FIELD_HEIGHT >= 500 \
                else theme.FIELD_HEIGHT - AVAILABLE_SECTOR__ONE_NEAREST_TEAM_DISABLED * theme.FIELD_HEIGHT
        else:
            self.available_y = theme.FIELD_HEIGHT - AVAILABLE_SECTOR__TWO_NEAREST_TEAM_ACTIVE * theme.FIELD_HEIGHT

    def _get_y(self, position):
        if position == 1:
            return self.mothership.coord.y - POSITION_TWO
        elif position == 2:
            return self.mothership.coord.y - POSITION_ONE
        elif position == 3 and SivkovDrone.attack_direction == 'up/down':
            return self.mothership.coord.y - POSITION_THREE__LEFT_RIGHT
        elif position == 3 and SivkovDrone.attack_direction == 'left/right':
            return self.mothership.coord.y - POSITION_THREE__UR_DOWN
        elif position == 4:
            return self.mothership.coord.y + POSITION_FIVE
        elif position == 5:
            return self.mothership.coord.y - POSITION_FOUR

    def _get_position_attack_front_y(self, serial_number, x):
        y = SivkovDrone.one_enemy.coord.y + round(
            sqrt(self.shot_distance ** 2 - (x - SivkovDrone.one_enemy.coord.x) ** 2), 0) - 2
        if y > theme.FIELD_HEIGHT - MINIMAL_COORDINATE_NEAR_MOTHERSHIP:
            y = theme.FIELD_HEIGHT - MINIMAL_COORDINATE_NEAR_MOTHERSHIP
            if serial_number in [1, 5]:
                y -= CORRECTION_TO_THE_POSITION_OF_THE_OUTERMOST_SHIPS
        return Point(x, y)

    def _get_position_attack_flank_y(self, serial_number):
        return theme.FIELD_HEIGHT - ((serial_number - 1) * DISTANCE_BETWEEN_DRONES + DISTANCE_FOR_FIRST_DRONE)

    def _enemy_in_attack_sector_y(self, enemy):
        if enemy.coord.y > MINIMAL_COORDINATE_NEAR_MOTHERSHIP:
            return True
        return False


class PositionDown(Position):

    """Позиция низ"""

    @property
    def correction_y(self):
        return - self.correction

    def _checking_target_y(self, target):
        if target.coord.y < self.available_y:
            return True
        return False

    def _checking_target_for_two_teams_y(self, target):
        if SHELLING_SECTOR__TWO_TEAM < target.coord.y < self.available_y:
            return True
        return False

    def _target_in_safe_zone_y(self, target):
        if target.coord.y < SAFE_ZONE_FOR_COLLECTING:
            return True
        return False

    def _get_available_y(self, drone):
        if not drone.danger_from_enemy_mothership(SivkovDrone.diagonal_enemy_base) \
                and not drone.danger_from_enemy_mothership(SivkovDrone.first_enemy_base):
            self.available_y = theme.FIELD_HEIGHT
        elif not drone.danger_from_enemy_mothership(SivkovDrone.first_enemy_base):
            self.available_y = theme.FIELD_HEIGHT if theme.FIELD_WIDTH - theme.FIELD_HEIGHT >= 500 \
                else AVAILABLE_SECTOR__ONE_NEAREST_TEAM_DISABLED * theme.FIELD_HEIGHT
        else:
            self.available_y = AVAILABLE_SECTOR__TWO_NEAREST_TEAM_ACTIVE * theme.FIELD_HEIGHT

    def _get_y(self, position):
        if position == 1:
            return self.mothership.coord.y + POSITION_TWO
        elif position == 2:
            return self.mothership.coord.y + POSITION_ONE
        elif position == 3 and SivkovDrone.attack_direction == 'up/down':
            return self.mothership.coord.y + POSITION_THREE__LEFT_RIGHT
        elif position == 3 and SivkovDrone.attack_direction == 'left/right':
            return self.mothership.coord.y + POSITION_THREE__UR_DOWN
        elif position == 4:
            return self.mothership.coord.y - POSITION_FIVE
        elif position == 5:
            return self.mothership.coord.y + POSITION_FOUR

    def _get_position_attack_front_y(self, serial_number, x):
        y = SivkovDrone.one_enemy.coord.y - round(
            sqrt(self.shot_distance ** 2 - (x - SivkovDrone.one_enemy.coord.x) ** 2), 0) + 2
        if y < MINIMAL_COORDINATE_NEAR_MOTHERSHIP:
            y = MINIMAL_COORDINATE_NEAR_MOTHERSHIP
            if serial_number in [1, 5]:
                y += CORRECTION_TO_THE_POSITION_OF_THE_OUTERMOST_SHIPS
        return Point(x, y)

    def _get_position_attack_flank_y(self, serial_number):
        return (serial_number - 1) * DISTANCE_BETWEEN_DRONES + DISTANCE_FOR_FIRST_DRONE

    def _enemy_in_attack_sector_y(self, enemy):
        if enemy.coord.y < theme.FIELD_HEIGHT - MINIMAL_COORDINATE_NEAR_MOTHERSHIP:
            return True
        return False


class PositionLeftDown(PositionLeft, PositionDown):
    """Обработчик позиций для положения 1: левый нижний угол"""


class PositionRightDown(PositionRight, PositionDown):
    """Обработчик позиций для положения 2: правый нижний угол"""


class PositionLeftUp(PositionLeft, PositionUp):
    """Обработчик позиций для положения 3: левый верхний угол"""


class PositionRightUp(PositionRight, PositionUp):
    """Обработчик позиций для положения 4: правый верхний угол"""


drone_class = SivkovDrone
