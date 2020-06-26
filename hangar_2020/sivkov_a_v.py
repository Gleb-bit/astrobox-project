# -*- coding: utf-8 -*-avsivkov
"""Модуль содержит класс дрона 'AvsivkovDrone', управляющий его поведением"""

from astrobox.core import Drone
from robogame_engine.geometry import Point, Vector
from astrobox.themes.default import MOTHERSHIP_HEALING_DISTANCE
from robogame_engine.theme import theme


class AvsivkovDrone(Drone):
    """Дрон-добытчик"""
    identifier = {}
    ore_reserves = []
    total_drones = 0
    total_reports = []
    collection_is_over = False
    number_of_participants = 0
    tactic = None
    enemy = None
    target = None
    shots_at_enemy = 0
    enemy_bases = {}
    front_position = 150
    wait = 0
    number_of_teams = None
    base_position = None
    driller_role_available = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        AvsivkovDrone.total_drones += 1
        self.serial_number = AvsivkovDrone.total_drones
        self.asteroids_index = []
        self.keys_to_asteroids = []
        self.ore_of_asteroids = []
        self.report = False
        self.role = None
        self.position = None

    def on_born(self):
        """Начало деятельности дрона"""
        if self.serial_number == 1:
            self._dispatcher(first_start=True)
            if AvsivkovDrone.number_of_teams == 2:
                AvsivkovDrone.collection_is_over = True
                self._get_tactic()
        else:
            self._get_my_asteroid()
        if AvsivkovDrone.number_of_teams != 2:
            self.move_at(self.asteroids[self.asteroids_index[-1]])

    def _dispatcher(self, first_start=False):
        """Анализирует ситуацию и выдаёт цель"""
        self.ore_of_asteroids = []
        self.keys_to_asteroids = []
        asteroids = []
        for k, asteroid in enumerate(self.asteroids):
            asteroids.append((self.distance_to(asteroid), k, asteroid.payload, asteroid.state.obj.id))
        if first_start:
            self._data_collection(asteroids)
        if AvsivkovDrone.number_of_teams == 2 and self.distance_to(self.my_mothership) < 20 \
                and theme.FIELD_WIDTH < theme.FIELD_HEIGHT:
            asteroids.sort(reverse=True)
        else:
            asteroids.sort()
        for _, k, payload, asteroid_id in asteroids:
            self.keys_to_asteroids.append(asteroid_id)
            self.ore_of_asteroids.append(payload)
        self._data_synchronization()
        self._create_route_sheet()

    def _create_route_sheet(self):
        """Выдаёт дрону астеройд"""
        for i, ore_quantity in enumerate(self.ore_of_asteroids):
            index = AvsivkovDrone.identifier[self.keys_to_asteroids[i]]
            if sum(AvsivkovDrone.ore_reserves) == 0:
                break
            elif ore_quantity == 0:
                continue
            elif theme.FIELD_WIDTH > theme.FIELD_HEIGHT and self.asteroids[index].coord.y < theme.FIELD_HEIGHT / 2 \
                    and AvsivkovDrone.total_drones > 1 and AvsivkovDrone.number_of_teams < 3 \
                    and AvsivkovDrone.tactic == 'defense':
                continue
            else:
                if ore_quantity > self.free_space:
                    AvsivkovDrone.ore_reserves[index] -= self.free_space
                else:
                    AvsivkovDrone.ore_reserves[index] = 0
                self.asteroids_index.append(index)
                break

    def _data_collection(self, asteroids):
        """Собирает необходимые данные для координации дронов"""
        AvsivkovDrone.ore_reserves = [asteroid[2] for asteroid in asteroids]
        if AvsivkovDrone.number_of_teams == 2:
            asteroids.sort(reverse=True)
        else:
            asteroids.sort()
        for j, asteroid_data in enumerate(asteroids):
            AvsivkovDrone.identifier[asteroid_data[3]] = asteroid_data[1]
        for base in self.scene.motherships:
            if base.team != self.team:
                AvsivkovDrone.enemy_bases[base.team] = base.coord
        AvsivkovDrone.number_of_teams = len(self.scene.drones) // AvsivkovDrone.total_drones
        if self.my_mothership.coord.x == 90 and self.my_mothership.coord.y == 90:
            AvsivkovDrone.base_position = ('left', 'down')
        elif self.my_mothership.coord.y == 90 and self.my_mothership.coord.x != 90:
            AvsivkovDrone.base_position = ('right', 'down')
        elif self.my_mothership.coord.x == 90 and self.my_mothership.coord.y != 90:
            AvsivkovDrone.base_position = ('left', 'up')
        else:
            AvsivkovDrone.base_position = ('right', 'up')

    def _data_synchronization(self):
        """Актуализирует данные для координации дронов"""
        for i, ore in enumerate(self.ore_of_asteroids):
            index = AvsivkovDrone.identifier[self.keys_to_asteroids[i]]
            if ore < AvsivkovDrone.ore_reserves[index]:
                AvsivkovDrone.ore_reserves[index] = ore
            if ore > AvsivkovDrone.ore_reserves[index]:
                self.ore_of_asteroids[i] = AvsivkovDrone.ore_reserves[index]

    def _get_my_asteroid(self):
        """Выдаёт дрону астеройд и собирает отчёт о завершении работы"""
        if sum(AvsivkovDrone.ore_reserves):
            self._dispatcher()
            if not self.asteroids_index:
                self._return_to_base()
        else:
            self._completion_of_work()

    def _return_to_base(self):
        """Возвращает дрона на базу"""
        if self.distance_to(self.my_mothership) == 0:
            self._completion_of_work()
        else:
            self.move_at(self.my_mothership)

    def _completion_of_work(self):
        """Дрон заканчивает работу"""
        if not self.report:
            self._create_report()
        if len([drone for drone in self.scene.drones if drone.team == self.team and drone.is_alive]) \
                == len(AvsivkovDrone.total_reports):
            AvsivkovDrone.collection_is_over = True

    def _create_report(self):
        """Дрон сообщает, что он закончил работу"""
        AvsivkovDrone.total_reports.append(True)
        self.report = True

    def on_stop_at_asteroid(self, asteroid):
        """Дрон приземлился на астеройд"""
        if not AvsivkovDrone.collection_is_over or self.role == 'driller':
            self.load_from(asteroid)

    def on_load_complete(self):
        """Загрузка руды завершена"""
        if not AvsivkovDrone.collection_is_over or self.role == 'driller':
            self.asteroids_index.pop(-1)
            if self.free_space and sum(AvsivkovDrone.ore_reserves) and theme.FIELD_WIDTH < theme.FIELD_HEIGHT:
                self._get_my_asteroid()
                if self.asteroids_index:
                    self.move_at(self.asteroids[self.asteroids_index[-1]])
            else:
                self.move_at(self.my_mothership)

    def on_stop_at_mothership(self, mothership):
        """Дрон приземлился на главный корабль"""
        if self.payload:
            self.unload_to(mothership)
        else:
            if not AvsivkovDrone.collection_is_over:
                self._completion_of_work()

    def on_unload_complete(self):
        """Выгрузка руды завершена"""
        if (3 >= AvsivkovDrone.total_drones <= len([drone for drone in self.scene.drones if drone.is_alive]) -
            AvsivkovDrone.total_drones * 3 and AvsivkovDrone.number_of_teams != 2) \
                or (AvsivkovDrone.number_of_teams == 2 and self.my_mothership.payload >= 100
                    and AvsivkovDrone.total_drones < 3) \
                or (AvsivkovDrone.number_of_teams == 3 and
                    (AvsivkovDrone.total_drones > len([drone for drone in self.scene.drones
                                                       if drone.team == self.team and drone.is_alive])
                     or AvsivkovDrone.total_drones < 4 and self.my_mothership.payload >= 300)):
            AvsivkovDrone.collection_is_over = True
            if self.role == 'driller':
                self.role = 'defender'
                self.get_position(position=2)
                self.move_at(self.position)
        elif not AvsivkovDrone.collection_is_over or AvsivkovDrone.number_of_teams == 2:
            self._get_my_asteroid()
            if self.asteroids_index:
                self.move_at(self.asteroids[self.asteroids_index[-1]])

    def on_wake_up(self):
        """Дрон бездействует"""
        if not AvsivkovDrone.collection_is_over or self.role == 'driller':
            if self.asteroids_index:
                self.move_at(self.asteroids[-1])
            elif self.free_space and sum(AvsivkovDrone.ore_reserves):
                self._get_my_asteroid()
            elif self.distance_to(self.my_mothership) > 10:
                self.move_at(self.my_mothership)
            elif not self.report:
                self._completion_of_work()
            elif self.role == 'driller':
                self.role = None
        else:
            if AvsivkovDrone.tactic == 'defense':
                self._tactic__defense()
            elif AvsivkovDrone.tactic == 'attack':
                self._tactic__attack()
            elif AvsivkovDrone.tactic == 'robbery':
                self._tactic__robbery()
            elif AvsivkovDrone.tactic == 'the_end':
                pass
            else:
                self._get_tactic()

    def _get_tactic(self):
        """Определяет тактику действий для дронов"""
        AvsivkovDrone.total_drones = len([drone for drone in self.scene.drones if drone.team == self.team
                                          and drone.is_alive])
        AvsivkovDrone.number_of_participants = 0
        AvsivkovDrone.enemy = None
        if AvsivkovDrone.total_drones < 3 or AvsivkovDrone.number_of_teams == 2:
            if theme.FIELD_WIDTH > theme.FIELD_HEIGHT and AvsivkovDrone.tactic != 'attack' \
                    and AvsivkovDrone.number_of_teams == 2 and AvsivkovDrone.total_drones > 3:
                AvsivkovDrone.tactic = 'attack'
            else:
                AvsivkovDrone.tactic = 'defense'
        elif self.distance_to(self.my_mothership) < 20 or AvsivkovDrone.wait >= 30:
            self._get_enemy()
            if not AvsivkovDrone.enemy:
                self._get_enemy()
                if not AvsivkovDrone.enemy:
                    AvsivkovDrone.tactic = 'robbery'
            elif self._where_is_enemy() and AvsivkovDrone.tactic != 'attack' and AvsivkovDrone.number_of_teams == 4:
                AvsivkovDrone.tactic = 'attack'
            else:
                AvsivkovDrone.tactic = 'defense'

    def _tactic__defense(self):
        """Тактика обороны и грабежа"""
        if self.role not in ['defender', 'collector', 'saboteur', 'driller', 'awaiting']:
            AvsivkovDrone.number_of_participants += 1
            if AvsivkovDrone.number_of_participants == 1 and AvsivkovDrone.total_drones > 1:
                if AvsivkovDrone.total_drones < 3 or AvsivkovDrone.number_of_teams == 2:
                    self.get_position(position=3)
                else:
                    self.get_position(position=1)
                self.role = 'defender'
            elif AvsivkovDrone.number_of_participants == 2 and AvsivkovDrone.total_drones > 2:
                self.get_position(position=2)
                self.role = 'defender'
            else:
                self.position = self.my_mothership
                if AvsivkovDrone.number_of_teams == 2:
                    self._launch_driller()
                else:
                    self.role = 'collector'
                self.move_at(self.position)
        elif self.role == 'defender':
            if self.distance_to(self.position) > 5:
                self.move_at(self.position)
            elif AvsivkovDrone.enemy:
                self.turn_to(AvsivkovDrone.enemy)
                self._shoot()
            else:
                self._get_enemy()
                if not AvsivkovDrone.enemy:
                    self._get_tactic()
        elif self.role == 'collector':
            self._tactic__robbery()

    def _launch_driller(self):
        """Запуск дрона бурильщика на сбор рессурсов"""
        self.role = 'driller'
        self._dispatcher()
        self.position = self.asteroids[self.asteroids_index[-1]]

    def _tactic__attack(self):
        """Тактика стремительного нападения"""
        if AvsivkovDrone.tactic != 'attack' or self.health < 60:
            self.move_at(self.my_mothership)
        elif not self.role:
            AvsivkovDrone.number_of_participants += 1
            if AvsivkovDrone.number_of_participants == 1 and AvsivkovDrone.number_of_teams > 2:
                self.role = 'collector'
                self.get_position()
            else:
                if AvsivkovDrone.number_of_participants == 1:
                    self.get_position()
                self.role = 'soldier'
            if theme.FIELD_WIDTH <= theme.FIELD_HEIGHT and AvsivkovDrone.number_of_teams > 2:
                self.position = Point((theme.FIELD_WIDTH - 120 * AvsivkovDrone.total_drones) // 2 + 120 *
                                      AvsivkovDrone.number_of_participants, AvsivkovDrone.front_position)
            else:
                self.position = Point(AvsivkovDrone.front_position,
                                      (theme.FIELD_HEIGHT - 110 * AvsivkovDrone.total_drones) // 2 + 110 *
                                      AvsivkovDrone.number_of_participants)
        elif AvsivkovDrone.wait >= 30:
            self._get_tactic()
        elif self.role == 'collector':
            self._tactic__robbery()
        elif self.distance_to(self.my_mothership) < 50:
            self.move_at(self.position)
        elif not AvsivkovDrone.enemy:
            self._get_enemy()
            AvsivkovDrone.wait += 1
        elif (len([drone for drone in self.scene.drones if drone.team != self.team and drone.is_alive]) == 3) \
                and AvsivkovDrone.driller_role_available:
            AvsivkovDrone.driller_role_available = False
            self._launch_driller()
        elif (theme.FIELD_WIDTH <= theme.FIELD_HEIGHT and AvsivkovDrone.base_position[1] == 'down'
              and AvsivkovDrone.enemy.coord.y < AvsivkovDrone.front_position + 100) \
                or (theme.FIELD_WIDTH <= theme.FIELD_HEIGHT and AvsivkovDrone.base_position[1] == 'up'
                    and AvsivkovDrone.enemy.coord.y > AvsivkovDrone.front_position - 100) \
                or (AvsivkovDrone.total_drones > len([drone for drone in self.scene.drones
                                                      if drone.team == self.team and drone.is_alive])) \
                or (theme.FIELD_WIDTH > theme.FIELD_HEIGHT and AvsivkovDrone.base_position[1] == 'left'
                    and AvsivkovDrone.enemy.coord.x > AvsivkovDrone.front_position + 100) \
                or (theme.FIELD_WIDTH > theme.FIELD_HEIGHT and AvsivkovDrone.base_position[1] == 'right'
                    and AvsivkovDrone.enemy.coord.x > AvsivkovDrone.front_position - 100)\
                or (len([drone for drone in self.scene.drones if drone.team != self.team and drone.is_alive]) == 1) \
                or (theme.FIELD_HEIGHT >= theme.FIELD_WIDTH and AvsivkovDrone.base_position[1] == 'up'
                    and self.front_position < theme.FIELD_HEIGHT / 2) \
                or (theme.FIELD_HEIGHT >= theme.FIELD_WIDTH and AvsivkovDrone.base_position[1] == 'down'
                    and self.front_position > theme.FIELD_HEIGHT / 2) \
                or (theme.FIELD_HEIGHT < theme.FIELD_WIDTH and AvsivkovDrone.base_position[1] == 'left'
                    and self.front_position > theme.FIELD_WIDTH / 2) \
                or (theme.FIELD_HEIGHT < theme.FIELD_WIDTH and AvsivkovDrone.base_position[1] == 'right'
                    and self.front_position < theme.FIELD_WIDTH / 2):
            AvsivkovDrone.wait = 100
            self._get_tactic()
        elif theme.FIELD_WIDTH <= theme.FIELD_HEIGHT and self.coord.y != AvsivkovDrone.front_position:
            self.position = Point(self.coord.x, AvsivkovDrone.front_position)
            self.move_at(self.position)
        elif theme.FIELD_WIDTH > theme.FIELD_HEIGHT and self.coord.x != AvsivkovDrone.front_position:
            self.position = Point(AvsivkovDrone.front_position, self.coord.y)
            self.move_at(self.position)
        elif self.distance_to(AvsivkovDrone.enemy) > self.gun.shot_distance:
            self._get_enemy()
            if self.distance_to(AvsivkovDrone.enemy) > self.gun.shot_distance:
                AvsivkovDrone.wait += 1
                if AvsivkovDrone.wait >= 10:
                    if theme.FIELD_HEIGHT >= theme.FIELD_WIDTH and AvsivkovDrone.base_position[1] == 'down':
                        AvsivkovDrone.front_position += 30
                    elif theme.FIELD_HEIGHT < theme.FIELD_WIDTH and AvsivkovDrone.base_position[0] == 'left':
                        AvsivkovDrone.front_position += 30
                    else:
                        AvsivkovDrone.front_position -= 30
        else:
            self.turn_to(AvsivkovDrone.enemy)
            AvsivkovDrone.wait = 0
            self._shoot()

    def _tactic__robbery(self):
        """Сбор рессурсов (грабёж)"""
        if AvsivkovDrone.tactic == 'robbery':
            self._get_enemy()
            if AvsivkovDrone.enemy:
                AvsivkovDrone.tactic = None
        if self.role != 'collector':
            self.role = None
        if not AvsivkovDrone.target:
            self._get_target()
            if not AvsivkovDrone.target:
                if AvsivkovDrone.total_drones == 1:
                    self.get_position(position=3)
                    self.role = 'defender'
                AvsivkovDrone.number_of_participants = 0
                AvsivkovDrone.tactic = 'defense'
        elif self.distance_to(self.my_mothership) < 20:
            if AvsivkovDrone.target.payload and AvsivkovDrone.target.is_alive:
                self.move_at(AvsivkovDrone.target)
            else:
                AvsivkovDrone.target = None
        elif self.payload == 100 or not AvsivkovDrone.target.payload:
            self.move_at(self.my_mothership)
        elif self.distance_to(AvsivkovDrone.target) < 20 and self.free_space:
            self.load_from(AvsivkovDrone.target)
        else:
            self.move_at(self.my_mothership)

    def _where_is_enemy(self):
        """Определяет насколько враги близко к нашей базе"""
        enemy_coordinate = []
        if AvsivkovDrone.base_position[1] == 'down':
            enemies = [drone for drone in self.scene.drones if drone.team != self.team and drone.is_alive
                       and drone.coord.y < theme.FIELD_HEIGHT - AvsivkovDrone.total_drones * 140]
        else:
            enemies = [drone for drone in self.scene.drones if drone.team != self.team and drone.is_alive
                       and drone.coord.y > 0 + AvsivkovDrone.total_drones * 140]
        for enemy in enemies:
            vector = Vector.from_points(enemy.coord, AvsivkovDrone.enemy_bases[enemy.team])
            if vector.module > 30:
                enemy_coordinate.append(enemy.coord.y)
        if enemy_coordinate or theme.FIELD_WIDTH - theme.FIELD_HEIGHT > 200:
            return False
        else:
            return True

    def _get_enemy(self):
        """Определяет дрону врага"""
        AvsivkovDrone.shots_at_enemy = 0
        enemies = [(self.distance_to(drone), drone) for drone in self.scene.drones if drone.team != self.team
                   and drone.is_alive]
        enemy_base = [base for base in self.scene.motherships if base.team != self.team and base.is_alive]
        if enemies:
            enemies.sort(key=lambda x: x[0])
        if len(enemies) <= 2 and AvsivkovDrone.number_of_teams == 2 and enemy_base \
                and self.distance_to(enemy_base[-1]) < self.gun.shot_distance:
            AvsivkovDrone.enemy = enemy_base[-1]
        else:
            for enemy in enemies:
                vector = Vector.from_points(enemy[1].coord, AvsivkovDrone.enemy_bases[enemy[1].team])
                if vector.module > MOTHERSHIP_HEALING_DISTANCE or AvsivkovDrone.number_of_teams == 2:
                    AvsivkovDrone.enemy = enemy[1]
                    break

    def _get_target(self):
        """Определяет цель для сбора рессурса"""
        enemy_bases = [(base.payload, base) for base in self.scene.motherships if base.team != self.team
                       and base.payload and base.is_alive]
        if enemy_bases:
            if AvsivkovDrone.tactic == 'attack':
                safe_way = []
                for base in enemy_bases:
                    if base[1].coord.x == self.my_mothership.coord.x or base[1].coord.y == self.my_mothership.coord.y:
                        safe_way.append(base[1])
                if safe_way:
                    AvsivkovDrone.target = safe_way[0]
            if not AvsivkovDrone.target:
                enemy_bases.sort(reverse=True, key=lambda x: x[0])
                AvsivkovDrone.target = enemy_bases[0][1]
        else:
            if AvsivkovDrone.tactic == 'robbery':
                enemy_bases = [base for base in self.scene.motherships if base.team != self.team and base.payload]
                if enemy_bases:
                    AvsivkovDrone.target = enemy_bases[0]
                else:
                    AvsivkovDrone.tactic = 'the_end'

    def get_position(self, position=None):
        """Определяет координатную позицию дрону в зависимости от расположения базы"""
        if AvsivkovDrone.tactic == 'attack':
            if theme.FIELD_WIDTH > theme.FIELD_HEIGHT:
                if AvsivkovDrone.base_position[0] == 'right':
                    AvsivkovDrone.front_position = theme.FIELD_WIDTH - 150
            elif AvsivkovDrone.base_position[1] == 'up':
                AvsivkovDrone.front_position = theme.FIELD_HEIGHT - 150
        elif AvsivkovDrone.tactic == 'defense':
            if position == 1:
                if AvsivkovDrone.base_position[1] == 'down':
                    self.position = Point(self.my_mothership.coord.x, self.my_mothership.coord.y + 190)
                if AvsivkovDrone.base_position[1] == 'up':
                    self.position = Point(self.my_mothership.coord.x, self.my_mothership.coord.y - 190)
            elif position == 2:
                if AvsivkovDrone.base_position[0] == 'left':
                    self.position = Point(self.my_mothership.coord.x + 190, self.my_mothership.coord.y)
                if AvsivkovDrone.base_position[0] == 'right':
                    self.position = Point(self.my_mothership.coord.x - 190, self.my_mothership.coord.y)
            else:
                if AvsivkovDrone.base_position[0] == 'left' and AvsivkovDrone.base_position[1] == 'down':
                    self.position = Point(self.my_mothership.coord.x + 140, self.my_mothership.coord.y + 140)
                if AvsivkovDrone.base_position[0] == 'right' and AvsivkovDrone.base_position[1] == 'down':
                    self.position = Point(self.my_mothership.coord.x - 140, self.my_mothership.coord.y + 140)
                if AvsivkovDrone.base_position[0] == 'left' and AvsivkovDrone.base_position[1] == 'up':
                    self.position = Point(self.my_mothership.coord.x + 140, self.my_mothership.coord.y - 140)
                if AvsivkovDrone.base_position[0] == 'right' and AvsivkovDrone.base_position[1] == 'up':
                    self.position = Point(self.my_mothership.coord.x - 140, self.my_mothership.coord.y - 140)

    def _shoot(self):
        """Дрон делает выстрел"""
        if AvsivkovDrone.enemy and AvsivkovDrone.enemy.is_alive and AvsivkovDrone.shots_at_enemy < 8:
            AvsivkovDrone.shots_at_enemy += 1
            self.gun.shot(AvsivkovDrone.enemy)
        else:
            AvsivkovDrone.enemy = None
            self._get_enemy()

drone_class = AvsivkovDrone
