# -*- coding: utf-8 -*-
from astrobox.core import Drone
from robogame_engine.geometry import Point, Vector
from robogame_engine.theme import theme
from astrobox.themes.default import MOTHERSHIP_HEALING_DISTANCE
import random

FRSP_TO_RETURN = 30
DOUBLE_PAYLOAD = 150
NUMB_OF_FIGHTERS_ON_START = 0


class HeadQuarter:
    """
    Класс штаб-квартиры
    """

    def __init__(self):
        self.TURRET_POINTS = []
        self.courses_k = [-30, 30, 15, 0, -15]
        self.fighters_squadron = []
        self.harvesters_squadron = []
        self.enemy_bases = []
        self.enemies = []
        self.enemy_turrets = []
        self.cargo_objects = []
        self.center_field = Point(theme.FIELD_WIDTH // 2, theme.FIELD_HEIGHT // 2)


class CheslavlevDrone(Drone):
    my_team = []
    my_hq = HeadQuarter()

    # поля статистики дистанции команды
    team_total_distance = 0.0
    team_distance_full_load = 0.0
    team_distance_part_load = 0.0
    team_distance_empty = 0.0

    def __init__(self, stat_f=False, **kwargs):
        """
        :param stat_f: bool, флаг "выводить статистику дистанции или нет", по умолчанию False
        :param kwargs:

        """
        super().__init__(**kwargs)
        # поля статистики дистанции дрона
        self.inner_team_id = None
        self.role = None
        self.friends_list = []
        self.distance = 0.0
        self.distance_full_load = 0.0
        self.distance_part_load = 0.0
        self.distance_empty = 0.0
        self.position = None
        self.aim = None
        self.finish_work_f = False
        self.stat_f = stat_f
        self.on_position_f = False
        # поле определяет показатель payload астероида, при котором (и более) на него будет направлено 2 дрона
        self.double_payload = DOUBLE_PAYLOAD
        # поле определяет максимальный free_space дрона, с которым допустимо возвращение на базу без поиска новой цели
        self.max_free_space_to_return = FRSP_TO_RETURN
        self.hq = CheslavlevDrone.my_hq

    def sort_enemies(self):
        """
        Метод сортирует вражеские объекты, распределяя их по полям объекта Headquarters:
        базы,
        дроны,

        :return: None

        """
        for mothership in self.scene.motherships:
            if mothership is self.mothership:
                continue
            self.hq.enemy_bases.append(mothership)
        for drone in self.scene.drones:
            if isinstance(drone, CheslavlevDrone):
                continue
            else:
                self.hq.enemies.append(drone)

    def check_team(self):
        """
        Метод проверяет статус команды и после каждой проверки пересоздает список в поле self.friends_list (союзники дрона)

        :return: None

        """
        self.friends_list.clear()
        for drone in CheslavlevDrone.my_team:
            if drone == self:
                continue
            if drone.health <= 0:
                CheslavlevDrone.my_team.remove(drone)
            else:
                self.friends_list.append(drone)

    def get_turret_points(self):
        """
        Метод создает стартовые точки расстановки дронов

        :return: None

        """
        vec = Vector.from_points(self.my_mothership.coord, self.hq.center_field)
        dir = vec.direction
        angles_set = [dir - 70, dir + 40, dir + 10, dir - 10, dir - 40]

        for angle in angles_set:
            vec_turret = Vector.from_direction(direction=angle, module=MOTHERSHIP_HEALING_DISTANCE * 0.9)
            point_turret = Point(self.my_mothership.coord.x + vec_turret.x, self.my_mothership.coord.y + vec_turret.y)
            self.hq.TURRET_POINTS.append(Point(x=point_turret.x, y=point_turret.y))

    def set_start_role(self):
        """
        Метод задает стартовую роль  и позицию дрона

        :return: None

        """
        if len(self.hq.fighters_squadron) < NUMB_OF_FIGHTERS_ON_START:
            self.role = Fighter(drone=self)
            self.hq.fighters_squadron.append(self)
            self.position = self.hq.TURRET_POINTS[self.inner_team_id - 1]
            self.role.on_born()
        else:
            self.role = Harvester(drone=self)
            self.hq.harvesters_squadron.append(self)
            self.role.on_born()

    def play_role(self):
        """
        Метод играет или меняет боевую роль или позицию дрона если имеются условия.
        Если условий нет вызывается on_wake_up()  c текущей ролью и позицией

        :return: None

        """
        if len(self.hq.enemies) < len(CheslavlevDrone.my_team) and \
                isinstance(self.role, Fighter) and self.role.turret:
            self.role.fighter = True
            self.role.turret = False
            self.role.fighter_mode()
        elif isinstance(self.role, Harvester) and self.role.get_total_payload() == 0 and self.hq.enemy_bases:
            self.role = Fighter(drone=self)
            self.hq.harvesters_squadron.remove(self)
            self.hq.fighters_squadron.append(self)
            self.position = self.hq.TURRET_POINTS[self.inner_team_id - 1]
            self.move_at(self.position)
        elif not self.hq.enemies and not self.hq.enemy_bases and isinstance(self.role, Fighter):
            self.role = Harvester(drone=self)
            self.hq.fighters_squadron.remove(self)
            self.hq.harvesters_squadron.append(self)
            self.role.on_born()
        else:
            self.role.on_wake_up()

    def on_born(self):
        """
        При вызове метода у первого созданного дрона вызываются методы get_turret_points(), sort_enemies()  и создается
        список hq.cargo_objects (объектов в которых есть лут)

        :return: None

        """
        CheslavlevDrone.my_team.append(self)
        self.inner_team_id = len(CheslavlevDrone.my_team)
        if len(CheslavlevDrone.my_team) == 1:
            self.get_turret_points()
            self.sort_enemies()
            self.hq.cargo_objects += self.asteroids + self.hq.enemy_bases
        self.set_start_role()
        self.role.on_born()

    def on_stop_at_asteroid(self, asteroid):
        self.check_team()
        self.role.on_stop_at_asteroid(asteroid)

    def on_load_complete(self):
        self.check_team()
        self.role.on_load_complete()

    def on_stop_at_mothership(self, mothership):
        self.check_team()
        self.role.on_stop_at_mothership(mothership)

    def on_unload_complete(self):
        self.check_team()
        self.role.on_unload_complete()

    def on_stop_at_point(self, target):
        self.check_team()
        self.role.on_stop_at_point(target)

    def on_wake_up(self):
        self.check_team()
        if self.health < 60:
            self.move_at(self.my_mothership)
        else:
            self.play_role()


class Harvester:
    """
    Класс роли дрона - сборщик ресурсов
    """

    def __init__(self, drone):
        self.drone = drone

    def __get_cargo_object_priority(self, cargo_object):
        """
        Метод определят "приоритет объекта", т.е. отношение коэффициента груза на нем к дистанции до него.
        Чем больше груза и меньше дистанция - тем он приоритетнее.
        distance_k = коэффциент дистанции до объекта.
        enemy_interest_k = коэффциент заинтересованности врага в объекте (показывает сколько еще врагов летит на этот
        объект)

        :param cargo_object: Asteroid-class, Drone-class or Mothership-class instance
        :return: priority, float, коэффициент приоритета объекта

        """
        distance = self.drone.distance_to(cargo_object)
        distance_k = distance if distance > 0 else 0.1
        enemy_interest_k = 1
        for enemy in self.drone.hq.enemies:
            if enemy.target == cargo_object:
                enemy_interest_k += 1
        priority = (cargo_object.cargo.payload / distance_k) / enemy_interest_k
        return priority

    def _get_team_targets(self):
        """
        Метод возвращает список целей других дронов команды

        :rtype: list
        :return:team_targets_list - список целей дронов команды (кроме цели дрона, вызывающего метод)

        """
        team_targets_list = []
        for drone in CheslavlevDrone.my_team:
            if drone == self.drone:
                continue
            team_targets_list.append(drone.target)
        return team_targets_list

    def _handle_distance_stat(self, target):
        """
        Метод вычисляет потенциальное "пустое", "полупустое", или "полное" расстояние, которое предстоит пройти дрону
        распределяет полученные данные по соответствующим полям объекта Drone.

        :param target: Asteroid-class instance или MotherShip-class instance: цель полета

        """
        target_distance = self.drone.distance_to(target)
        self.drone.distance += target_distance
        if self.drone.is_empty:
            self.drone.distance_empty += target_distance
        elif self.drone.is_full:
            self.drone.distance_full_load += target_distance
        elif 0 < self.drone.free_space < 100:
            self.drone.distance_part_load += target_distance

    def _show_finish_stat(self):
        """
        Метод собирает и выводит в консоль статистику по команде.

        """
        print(f'Distance stat:\nTotal distance with full load: {CheslavlevDrone.team_distance_full_load}, '
              f'{round(CheslavlevDrone.team_distance_full_load / CheslavlevDrone.team_total_distance * 100, 1)}%'
              f'\nTotal distance with part load: {CheslavlevDrone.team_distance_part_load},'
              f'{round(CheslavlevDrone.team_distance_part_load / CheslavlevDrone.team_total_distance * 100, 1)}%'
              f'\nTotal distance with empty cargo hold: {CheslavlevDrone.team_distance_empty},',
              f'{round(CheslavlevDrone.team_distance_empty / CheslavlevDrone.team_total_distance * 100, 1)}%')

    def get_total_payload(self):
        """
        Метод возвращает совокупный payload всех объектов на поле. Если вражеские базы не уничтожены считается только
        payload астероидов. Если уничтожены - то совокупный (в т.ч. и разрушенных вражеских баз)

        :rtype: int
        :return: total_cargo_objects_payload

        """

        if self.drone.hq.enemy_bases:
            source = self.drone.asteroids
        else:
            source = self.drone.hq.cargo_objects
        total_cargo_objects_payload = 0
        for cargo_object in source:
            total_cargo_objects_payload += cargo_object.cargo.payload
        return total_cargo_objects_payload

    def get_active_drones_free_space(self):
        """
        Метод возвращает совокупный free_space  всех дронов, у которых есть target  (т.е. тех, которые "в пути").

        :rtype: int
        :return: total_free_space

        """
        total_free_space = 0
        for drone in CheslavlevDrone.my_team:
            if drone.target:
                total_free_space += drone.free_space
        return total_free_space

    def _get_my_cargo_target(self):
        """
        Метод возвращает приоритетную цель для полета.
        Сначала получаем список целей других дронов команды (_get_team_targets()) чтобы они всем "роем"
        не летели на 1 цель, а распределялись, затем сортируем полученный полученный списков по ключу,
        который вовзращает метод __get_cargo_object_priority() (по приоритету).
        Далее в цикле по сортированному списку целей определяем цель, при этом определенном payload на цель
        может быть направлено 2 дрона.

        :rtype: Object-class instance
        :return: target

        """
        if self.drone.hq.enemy_bases:
            source = self.drone.asteroids
        else:
            source = self.drone.hq.cargo_objects

        team_targets = self._get_team_targets()
        sorted_cargo_objects_list = sorted(source, key=self.__get_cargo_object_priority,
                                           reverse=True)
        target = False
        for obj in sorted_cargo_objects_list:
            if obj.cargo.payload > self.drone.double_payload and team_targets.count(obj) < 2:
                target = obj if self.__get_cargo_object_priority(obj) > 0 else False
                break
            elif obj.cargo.payload <= self.drone.double_payload and obj not in team_targets:
                target = obj if self.__get_cargo_object_priority(obj) > 0 else False
                break
        return target

    def on_finish_work(self):
        """
        Метод обрабатывает ситуацию, когда нужно остановить работу дрона-сборщика и оставить его на базе. Поднимает флаг
        finish_work_f, отправляет статистику по дистанции в поля класса, проверяет закончили ли другие дроны работу и при
        успешной проверке вызывает _show_finish_stat()

        """
        self.drone.finish_work_f = True
        CheslavlevDrone.team_total_distance += round(self.drone.distance, 0)
        CheslavlevDrone.team_distance_full_load += round(self.drone.distance_full_load, 0)
        CheslavlevDrone.team_distance_part_load += round(self.drone.distance_part_load, 0)
        CheslavlevDrone.team_distance_empty += round(self.drone.distance_empty, 0)
        if all(drone.finish_work_f for drone in CheslavlevDrone.my_team) and self.drone.stat_f:
            self._show_finish_stat()

    def on_born(self):
        self.drone.target = self._get_my_cargo_target()
        self.drone.move_at(self.drone.target)

    def on_stop_at_asteroid(self, asteroid):
        self.drone.load_from(asteroid)

    def on_stop_at_point(self, target):
        if hasattr(target, 'cargo'):
            self.drone.load_from(target)

    def on_load_complete(self):
        if 0 <= self.drone.free_space <= self.drone.max_free_space_to_return:
            self.drone.target = False
            self._handle_distance_stat(self.drone.my_mothership)
            self.drone.move_at(self.drone.my_mothership)
        else:
            self.drone.target = self._get_my_cargo_target()
            if self.drone.target:
                self._handle_distance_stat(self.drone.target)
                self.drone.move_at(self.drone.target)
            else:
                self._handle_distance_stat(self.drone.my_mothership)
                self.drone.move_at(self.drone.my_mothership)

    def on_stop_at_mothership(self, mothership):
        if mothership != self.drone.my_mothership:
            self.drone.load_from(mothership)
        else:
            if self.drone.is_empty:
                self.on_finish_work()
            else:
                self.drone.unload_to(mothership)
                self.drone.target = False

    def on_unload_complete(self):
        self.drone.max_free_space_to_return -= 5
        cargo_check = self.get_active_drones_free_space() < self.get_total_payload()
        if cargo_check:
            self.drone.target = self._get_my_cargo_target()
            if self.drone.target:
                self._handle_distance_stat(self.drone.target)
                self.drone.move_at(self.drone.target)
            else:
                self.on_finish_work()
        else:
            self.on_finish_work()

    def on_wake_up(self):
        pass


class Fighter:
    """
    Класс роли дрона - истребитель.
    """

    def __init__(self, drone):
        self.drone = drone
        self.turret = True
        self.fighter = False

    def get_point_near_target(self):
        """
        Метод рассчитывает начальную точку атаки рядом с целью.

        :return: Point-class instance

        """
        vec = Vector.from_points(self.drone.coord, self.drone.aim.coord)
        dist = (self.drone.distance_to(self.drone.aim) - self.drone.gun.shot_distance) * 1.05
        direction = vec.direction
        vec_attack = Vector.from_direction(direction=direction + self.drone.hq.courses_k[self.drone.inner_team_id - 1],
                                           module=dist)
        point = Point(self.drone.coord.x + vec_attack.x, self.drone.coord.y + vec_attack.y)
        return point

    def change_position(self, position):
        """
        Метод выводит дрон-истребитель на позицию для стрельбы.

        :param position, Point
        :return: None

        """
        self.drone.position = position
        self.drone.move_at(self.drone.position)

    def turret_mode(self):
        """
        Метод отрабатывает режим работы дрона-турели. Дрон проверяет списки целей, убирает уничтоженные, затем вызывает
        метод get_priority_aim для получения приоритетной цели из списка вооруженных дронов,
        после чего стреляет методом shooting если цель в пределах досягаемости. Если цель вне досягаемости выстрел не
        происходит, чтобы лишней плотностью огня не убить своих сборщиков

        :return: None

        """
        self.check_enemy_teams()

        if self.drone.hq.enemies:
            self.drone.aim = self.get_priority_aim(self.drone.hq.enemies)
            angle_valid = all(list(map(lambda x: self.get_angle_delta(x) > 20, self.drone.friends_list)))
            if self.drone.aim and self.drone.distance_to(
                    self.drone.aim) <= self.drone.gun.shot_distance and angle_valid:
                self.shooting(self.drone.aim)

    def fighter_mode(self):
        """
         Метод отрабатывает режим работы дрона-истребителя. Дрон проверяет списки целей, убирает уничтоженные, затем вызывает
         open_fire()

         :return: None

         """

        self.check_enemy_teams()

        if self.drone.hq.enemies and set(self.drone.hq.enemies) == set(self.drone.hq.enemy_turrets):
            self.open_fire(self.drone.hq.enemy_turrets)

        elif self.drone.hq.enemies:
            self.open_fire(self.drone.hq.enemies)

        elif self.drone.hq.enemy_bases:
            self.open_fire(self.drone.hq.enemy_bases)

    def open_fire(self, enemy_list):
        """
        Метод отрабатывает работу истребителя:
        получение цели - get_priority_aim(),
        сближение с целью (если необходимо)
        и вызывает метод стельбы shooting()

        :param enemy_list: list
        :return: None

        """
        self.drone.aim = self.get_priority_aim(enemy_list)
        if self.drone.aim:
            if self.drone.distance_to(self.drone.aim) <= self.drone.gun.shot_distance:
                self.shooting(self.drone.aim)
            else:
                self.change_position(position=self.get_point_near_target())

    def shooting(self, aim):
        """
        Метод отрабатывает 1 выстрел последовательным вызовом методов класса Drone

        :param aim: цель выстрела. Drone-class или Mothership-class instance
        :return: None

        """
        if self.drone.distance_to(self.drone.mothership) > self.drone.mothership.radius:
            self.drone.turn_to(aim)
            self.drone.gun.shot(aim)

    def check_enemy_teams(self):
        """
        Метод проверяет списки целей и удаляет из них убитые цели
        :return: None

        """
        self.check_enemy_turret()
        for enemy_list in [self.drone.hq.enemies, self.drone.hq.enemy_turrets, self.drone.hq.enemy_bases]:
            if len(enemy_list) > 0:
                for enemy in enemy_list:
                    if enemy.health <= 0:
                        enemy_list.remove(enemy)

    def get_priority_aim(self, enemy_list):
        """
        Метод возвращает приоритетную цель, если ее удалось рассчитать и валидировать.
        Если на вход методу пришел список дронов-турелей, то в качестве цели возвращается база дрона (т.к. выбить сам дрон
        из режима турели сложно).

        :param enemy_list: список целей
        :return: цель, Drone-class или Mothership-class instance или False

        """
        self.drone.enemies = sorted(enemy_list, key=lambda x: self.drone.distance_to(x))
        aim_iterator = iter(self.drone.enemies)
        aim = next(aim_iterator)

        if enemy_list == self.drone.hq.enemy_turrets:
            while aim.mothership.health < 0:
                try:
                    aim = next(aim_iterator)
                except StopIteration:
                    aim = False
            return aim.mothership
        else:
            while not self.valide_shot(aim) and aim in self.drone.hq.enemy_turrets:
                try:
                    aim = next(aim_iterator)
                except StopIteration:
                    aim = False
            return aim

    def check_enemy_turret(self):
        """
        Метод проверяет, встали ли вражеские дроны в режим турелей.
        Переписывает список вражеских турелей.
        True

        :return: bool

        """
        self.drone.hq.enemy_turrets.clear()
        for drone in self.drone.hq.enemies:
            if (self.drone.distance_to(drone.mothership) - self.drone.distance_to(drone)) \
                    <= MOTHERSHIP_HEALING_DISTANCE and drone.mothership.health > 0:
                self.drone.hq.enemy_turrets.append(drone)

    def get_angle_delta(self, friend_drone):
        """
        Метод возвращает дельту углов между углом дрона к цели и углом дрона к союзнику.
        Используется для дальнейшей проверки не находится ли союзник на линии огня.

        :param friend_drone: Drone-class instance
        :return: float

        """
        my_aim_vec = Vector.from_points(self.drone.coord, self.drone.aim.coord)
        my_aim_direction = my_aim_vec.direction

        friend_drone_vec = Vector.from_points(self.drone.coord, friend_drone.coord)
        friend_drone_direction = friend_drone_vec.direction
        result = abs(friend_drone_direction - my_aim_direction)
        return result

    def valide_shot(self, aim):
        """
        Метод проверяет нет ли в рядом с целью выстрела союзника, чтобы избежать дружественного огня. Если все союзники
        находятся на расстоянии более 50 от цели, возвращается True иначе False

        :param aim: цель, Drone-class или Mothership-class
        :return: bool

        """
        aim_point = Point(aim.coord.x, aim.coord.y)
        if all(list(map(lambda x: x.distance_to(aim_point) > 50, self.drone.friends_list))):
            return True
        else:
            return False

    def valide_position(self, position):
        """
        Метод проверяет
        - не находится ли слишком близко от позиции истребителя союзник (point_valid)
        - не находится ли союзник на линии огня в этой позиции истребителя (angle_valid)
        чтобы избежать дружественного огня.

        :param position:
        :return: bool

        """
        angle_valid = all(list(map(lambda x: self.get_angle_delta(x) > 20, self.drone.friends_list)))
        point_valid = all(list(map(lambda x: x.distance_to(position) > 50, self.drone.friends_list)))
        if point_valid and angle_valid:
            return True
        else:
            return False

    def avoid_friendly_fire(self):
        """
        Метод меняет позицию дрона-истребителя на случайно генерируемую в пределах 150 от изначальной.
        Вызывается если в других методах valide_position() вернул False.

        :return: None

        """
        vec = Vector(self.drone.position.x, self.drone.position.y)
        point = vec.from_direction(direction=random.choice([90, 180, 270, 360]), module=random.choice([100, 150, 200]))
        self.change_position(
            position=Point(x=self.drone.coord.x + point.x, y=self.drone.coord.y + point.y))

    def on_stop_action(self):
        if self.fighter and not self.valide_position(self.drone.position):
            self.avoid_friendly_fire()
        else:
            if self.turret:
                self.turret_mode()
            elif self.fighter:
                self.fighter_mode()

    def on_born(self):
        self.drone.move_at(self.drone.position)

    def on_wake_up(self):
        if not self.drone.hq.enemies and self.drone.health < 100:
            self.avoid_friendly_fire()
        else:
            if self.turret:
                self.turret_mode()
            elif self.fighter:
                self.fighter_mode()

    def on_stop_at_point(self, target):
        self.on_stop_action()

    def on_stop_at_asteroid(self, asteroid):
        self.on_stop_action()

    def on_stop_at_mothership(self, mothership):
        if self.turret:
            self.turret_mode()
        elif self.fighter:
            self.change_position(position=self.drone.hq.TURRET_POINTS[self.drone.inner_team_id - 1])
            self.fighter_mode()

    def on_unload_complete(self):
        pass


drone_class = CheslavlevDrone
