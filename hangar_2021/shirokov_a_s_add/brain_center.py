from math import sin, cos, pi
from typing import Dict, Final
from astrobox.themes.default import MOTHERSHIP_HEALING_DISTANCE, MAX_DRONE_ELERIUM, DRONE_MAX_SHIELD, \
    MOTHERSHIP_MAX_SHIELD
from robogame_engine import scene
from robogame_engine.geometry import Point
from hangar_2021.shirokov_a_s_add.roles import RoleDefenderBase, RoleScavenger, RoleSiegeMaster, RoleSeniorCollector, \
    RoleJuniorCollector
from statistics import median


class BrainCenterShirokovDrones:
    """
    Класс для мозгового центра, где анализируется ситуация на поле в целом и обрабатываются запросы дронов,
    связанные с их координацией между собой
    """

    all_objects_on_field: Dict[str, tuple or None] = {'all_asteroids': None,
                                                      'asteroids_on_my_quadrant': None,
                                                      'all_drones': None,
                                                      'my_drones': None,
                                                      'enemy_drones': None,
                                                      'all_bases': None,
                                                      'my_base': None,
                                                      'enemy_bases': None}  # разбивка объектов на поле по видам и принадлежности (свой/чужой)
    print_statistic = False  # указывает, нужен ли вывод финальной статистики
    shot_distance = None  # дистанция выстрела
    defend_points = None  # тьюпл с точками защиты, которые занимают дроны класса Defender
    attack_points = None  # словарь с тьюплами точек атаки вокруг каждой вражеской базы (для дронов класса SiegeMaster)
    my_quadrant = None  # четверть поля, где зареспаунился наш материнский корабль
    commands_count = None  # количество команд на поле
    MIN_MOTHERSHIP_HEALTH = 0.40  # минимальное здоровье материнского корабля в процентах, ниже которого бьется общая тревога
    MAX_MOTHERSHIP_HEALTH: Final = MOTHERSHIP_MAX_SHIELD  # максимальное здоровье материнского корабля
    MOTHERSHIP_HEALING_DISTANCE: Final = MOTHERSHIP_HEALING_DISTANCE  # расстояние вокруг материнского корабля, где у дронов восстанавливается здоровье
    MAX_DRONE_ELL: Final = MAX_DRONE_ELERIUM  # максимально возможное количество эллириума в трюме дрона
    MAX_DRONE_HEALTH: Final = DRONE_MAX_SHIELD  # максимально возможное здоровье дрона
    SCHEMA_FOR_DEFEND: Final = {'count_points': 3,
                                'delta_between_first_and_last_point': 110,
                                'distance_coefficient_for': {'first_and_last_point': 1, 'middle_point': 0.6,
                                                             'other_point': 0.75}}
    SCHEMA_FOR_ATTACK: Final = {'count_points': 5,
                                'delta_between_first_and_last_point': 90,
                                'distance_coefficient_for': {'first_and_last_point': 0.4, 'middle_point': 0.4,
                                                             'other_point': 0.4}}
    DEGREES_DEVIATION: Final = {1: 90, 2: 270, 3: 0, 4: 180}  # отклонение в градусах, зависящее от квадранта базы, рассчитываемое для точек
    enemy_drones_around_base = []  # список вражеских дронов, подлетевших к материнскому кораблю на опасное расстояние
    dead_obj_with_ell_on_field = {}  # словарь с мертвыми вражескими дронами и материнскими кораблями, на борту которых есть эллириум
    enemy_bases_without_drones = []  # вражеские базы, оставшиеся без дронов (дроны либо мертвы, либо далеко от базы)

    def __init__(self):
        self.senior_collector = RoleSeniorCollector(self)
        self.junior_collector = RoleJuniorCollector(self)
        self.defender_base = RoleDefenderBase(self)
        self.scavenger = RoleScavenger(self)
        self.siege_master = RoleSiegeMaster(self)
        self.roles = (self.senior_collector, self.junior_collector, self.defender_base,
                      self.scavenger, self.siege_master)
        self.starting_lineup = {2: {self.senior_collector: 2, self.defender_base: 3},
                                3: {self.senior_collector: 3, self.defender_base: 2},
                                4: {self.senior_collector: 5}}

    def identify_objects(self, asteroids: list, drones: list, motherships: list, my_mothership,
                         shot_distance: int):
        """
        Метод, определяющий объекты игры и их принадлежность к родной или неродной команде,
        а также определяющий вспомогательные точки и некоторые константы

        :param asteroids: список всех астероидов на поле
        :type asteroids: list
        :param drones: список всех дронов на поле
        :type drones: list
        :param motherships: список всех материнских кораблей на поле
        :type motherships: list
        :param my_mothership: родной для команды материнский корабль
        :type my_mothership: Object
        :param shot_distance: дистанция выстрела для дрона
        :type shot_distance: int
        :notes: Вызывается один раз в самом начале игры
        """

        self.my_quadrant = self.recognize_quadrant_for_obj(my_mothership)
        self.all_objects_on_field['all_asteroids'] = tuple(asteroids)
        self.all_objects_on_field['all_drones'] = tuple(drones)
        self.all_objects_on_field['my_drones'] = tuple([drone for drone in drones
                                                        if drone.my_mothership == my_mothership])
        self.all_objects_on_field['enemy_drones'] = tuple([drone for drone in drones
                                                           if drone.mothership != my_mothership])
        self.all_objects_on_field['all_bases'] = tuple(motherships)
        self.all_objects_on_field['my_base'] = my_mothership
        self.all_objects_on_field['enemy_bases'] = tuple([base for base in motherships if base != my_mothership])
        self.shot_distance = shot_distance
        self.commands_count = len(self.all_objects_on_field['enemy_bases']) + 1
        for role in self.roles:
            if role.combat_class is True:
                role.shot_distance = shot_distance
        self.all_objects_on_field['asteroids_on_my_quadrant'] = tuple([asteroid for asteroid in asteroids
                                                                       if
                                                                       self.my_quadrant == self.recognize_quadrant_for_obj(
                                                                           asteroid)])
        self.defend_points = self.update_defend_points()
        self.attack_points = self.update_attack_points()

    @staticmethod
    def recognize_quadrant_for_obj(obj: object):
        """
        Метод, определяющий четверть, в пределах которого находится объект

        :param obj: Объект, для которой нужно определить четверть
        :type obj: Object
        :return: Номер четверти базы
        :rtype: int
        """

        len_half_axis_x = scene.theme.FIELD_WIDTH / 2
        len_half_axis_y = scene.theme.FIELD_HEIGHT / 2
        obj_coord_x = obj.coord.x
        obj_coord_y = obj.coord.y
        if obj_coord_x < len_half_axis_x and obj_coord_y < len_half_axis_y:
            return 3
        elif obj_coord_x < len_half_axis_x and obj_coord_y > len_half_axis_y:
            return 2
        elif obj_coord_x > len_half_axis_x and obj_coord_y < len_half_axis_y:
            return 1
        elif obj_coord_x > len_half_axis_x and obj_coord_y > len_half_axis_y:
            return 4

    def update_defend_points(self):
        """
        Метод для обновления точек защиты, готовит входные данные для отправки в self.recognize_points_around_base,
        затем результаты работы этого метода возвращает

        :return: результат метода self.recognize_points_around_base
        :rtype: tuple
        """

        my_base = self.all_objects_on_field['my_base']

        count_alive_my_drones = len(self.ret_drones_by_status(filter_alive=True,
                                                              filter_our=True))  # определяем количество живых дронов из моей команды
        count_points = self.SCHEMA_FOR_DEFEND['count_points'] if \
            count_alive_my_drones >= self.SCHEMA_FOR_DEFEND['count_points'] else count_alive_my_drones

        schema = self.SCHEMA_FOR_DEFEND
        default_distance = int(self.MOTHERSHIP_HEALING_DISTANCE * 0.99)
        return self.recognize_points_around_base(base_obj=my_base, schema=schema, default_distance=default_distance,
                                                 count_points=count_points)

    def update_attack_points(self):
        """
        Метод для обновления точек атаки, готовит входные данные для отправки в self.recognize_points_around_base,
        затем результаты работы этого метода возвращает

        :return: словарь, где ключом является id базы врага, а значением - тьюпл с точками атаки
        :rtype: dict
        :notes: в текущем билде обновляет точки атаки один раз, в начале игры
        """

        enemy_bases = self.all_objects_on_field['enemy_bases']
        schema = self.SCHEMA_FOR_ATTACK
        default_distance = int(self.shot_distance)
        attack_points = {}
        for enemy_base in enemy_bases:
            points_tuple = self.recognize_points_around_base(base_obj=enemy_base, schema=schema,
                                                             default_distance=default_distance)
            attack_points[enemy_base.id] = points_tuple
        return attack_points

    def recognize_points_around_base(self, *, base_obj: object, schema: dict, default_distance: int, count_points=None):
        """
        Метод, позволяющий рассчитать точки вокруг базы для атаки или защиты по входным данным

        :param base_obj: база, для которой нужен расчет
        :type base_obj: object
        :param schema: схема построения точек вокруг объекта
        :type schema: dict
        :param default_distance: базовое расстояние от базы до точки
        :type default_distance: int
        :param count_points: количество точек, которое нужно рассчитать (по умолчанию None, так как есть в schema)
        :type count_points: int or None
        """

        base_coord_x = base_obj.coord.x
        base_coord_y = base_obj.coord.y
        delta_first_and_last = schema['delta_between_first_and_last_point']
        angle = 0 - (delta_first_and_last - 90) / 2  # определяем отклонение от начальной точки и конечной
        angle += self.DEGREES_DEVIATION[
            self.recognize_quadrant_for_obj(base_obj)]  # определяем отклонение от стартовой точки
        count_points = schema['count_points'] if count_points is None else count_points
        try:
            step_angle = delta_first_and_last / (count_points - 1)  # определяем отклонение между соседними точками
        except ZeroDivisionError:
            step_angle = 0
            angle += delta_first_and_last / 2
        default_distance_from_base = default_distance  # радиус, в котором будет выстроена оборона
        list_of_points = []
        count = 1
        while count <= count_points:
            if count == 1 or count == count_points:
                distance_from_base = default_distance_from_base * schema['distance_coefficient_for'][
                    'first_and_last_point']
            elif count_points % 2 == 1 and count == median(range(1, count_points + 1)):
                distance_from_base = default_distance_from_base * schema['distance_coefficient_for']['middle_point']
            else:
                distance_from_base = default_distance_from_base * schema['distance_coefficient_for']['other_point']
            point = Point(base_coord_x + (distance_from_base * cos(angle * pi / 180)),
                          base_coord_y + (distance_from_base * sin(angle * pi / 180)))
            list_of_points.append(point)
            angle += step_angle
            count += 1
        return tuple(list_of_points)

    def define_start_role(self, drone_id: int):
        """
        Метод для выдачи стартовых ролей для дронов

        :param drone_id: id дрона, который запросил стартовую роль
        :type drone_id: int
        :return: роль для дрона
        :rtype: object
        """
        for key_count_comands, value_lineup in self.starting_lineup.items():
            if key_count_comands == self.commands_count:
                for key_role, value_count in value_lineup.items():
                    if self.ret_my_drones_roles.count(key_role) == value_count:
                        continue
                    else:
                        self.update_role(drone_id, key_role, start_role=True)
                        return key_role

    def change_default_role(self, drone_id: int):
        """
        Метод для выдачи ролей по очереди (базовый алгоритм)

        :param drone_id: id дрона, который запросил роль
        :type drone_id: int
        :return: роль для дрона
        :rtype: object
        """

        drone = self.get_object_for_id(drone_id)
        role_for_return = None
        if drone.role == self.senior_collector:
            role_for_return = self.junior_collector
        elif drone.role == self.junior_collector:
            if self.ret_my_drones_roles.count(self.defender_base) >= self.SCHEMA_FOR_DEFEND['count_points']:
                if self.ret_my_drones_roles.count(self.scavenger) >= 1:
                    role_for_return = self.siege_master
                else:
                    role_for_return = self.scavenger
            else:
                role_for_return = self.defender_base
        self.update_role(drone_id, role_for_return)
        return role_for_return

    def change_situation_role(self, drone_id: int, situation_code: int):
        """
        Метод для выдачи ролей по ситуации (ситуативные роли, зависят от ситуации на поле)

        :param drone_id: id дрона, который запросил роль
        :type drone_id: int
        :param situation_code: код ситуации, возникшей на поле
        :type situation_code: int
        :return: роль для дрона
        :rtype: object
        """

        role_for_return = None
        if situation_code == 1:
            if self.ret_my_drones_roles.count(self.defender_base) < self.SCHEMA_FOR_DEFEND['count_points']:
                role_for_return = self.defender_base
        elif situation_code == 2:
            if self.ret_my_drones_roles.count(self.scavenger) < 1:
                role_for_return = self.scavenger
        elif situation_code == 3:
            if self.ret_my_drones_roles.count(self.scavenger) < 2:
                role_for_return = self.scavenger
        elif situation_code == 4:
            if self.ret_my_drones_roles.count(self.siege_master) < 2:
                role_for_return = self.siege_master
        elif situation_code == 5:
            if self.ret_my_drones_roles.count(self.defender_base) < self.SCHEMA_FOR_DEFEND['count_points']:
                role_for_return = self.defender_base
        if role_for_return is not None:
            self.update_role(drone_id, role_for_return)
        return role_for_return

    def update_role(self, drone_id: int, new_role: object, *, start_role=False):
        """
        Метод для регистрации id дрона в списке держателей конкретной роли

        :param drone_id: id дрона, который запросил роль
        :type drone_id: int
        :param new_role: полученная дроном роль
        :type new_role: object
        :param start_role: параметр, указывающий на то, стартовая роль выдана или нет
        :type start_role: bool
        """

        drone = self.get_object_for_id(drone_id)
        if start_role is False:
            drone.role.my_drones_with_this_role.remove(drone_id)
        new_role.my_drones_with_this_role.append(drone_id)

    def get_object_for_id(self, number_id: int):
        """
        Идентификация объекта по его id

        :param number_id: id
        :type number_id: int
        :return: object
        :rtype: object
        """

        for ast in self.all_objects_on_field['all_asteroids']:
            if ast.id == number_id:
                return ast
        for drone in self.all_objects_on_field['all_drones']:
            if drone.id == number_id:
                return drone
        for base in self.all_objects_on_field['all_bases']:
            if base.id == number_id:
                return base

    def checks_in_heartbeat_for_brain_center(self):
        """
        Метод для проверки ситуации на поле через on_heartbeat

        :return: словарь с результатами проверки (ключ - описание проверки, значение - булево, где True,
        если проверка пройдена, и False, если проверка не пройдена
        :rtype: dict
        :notes: перед или после сбора проверок, требующих ответа дрону, проводится ряд других проверок
        """

        self.check_count_defenders()
        response_after_checks = {'found_dead_drones_with_ell': self.check_dead_drones_with_ell(),
                                 'found_dead_bases_with_ell': self.check_dead_enemy_bases_with_ell(),
                                 'found_enemy_bases_without_drones': self.check_enemy_bases_without_drones(),
                                 'perimeter_alarm': self.check_safety_radius_base(),
                                 'mothership_has_little_health': self.check_mothership_health()}
        return response_after_checks

    def check_count_defenders(self):
        """
        Метод для перепроверки количества дронов на поле и пересчета точек защиты в случае, если дронов осталось меньше,
        чем базовое количество защитников
        """

        if len(self.ret_drones_by_status(filter_alive=True, filter_our=True)) < len(self.defend_points):
            self.defend_points = self.update_defend_points()

    def check_safety_radius_base(self):
        """
        Метод для вычисления вражеских дронов, подлетевших к родной базе на опасное расстояние.
        Найденные дроны закидываются в self.enemy_drones_around_base

        :return: True, если в периметре обнаружены враги, и False, если враги не обнаружены
        :rtype: bool
        """

        for enemy_drone_id in self.enemy_drones_around_base:
            enemy_drone = self.get_object_for_id(enemy_drone_id)
            if enemy_drone.is_alive is False:
                self.enemy_drones_around_base.remove(enemy_drone_id)
        for enemy_drone in self.ret_drones_by_status(filter_alive=True, filter_our=False):
            my_base = self.all_objects_on_field['my_base']
            if my_base.distance_to(enemy_drone) <= self.shot_distance + self.MOTHERSHIP_HEALING_DISTANCE * 0.99:
                if enemy_drone.id not in self.enemy_drones_around_base:
                    self.enemy_drones_around_base.append(enemy_drone.id)
            else:
                if enemy_drone.id in self.enemy_drones_around_base:
                    self.enemy_drones_around_base.remove(enemy_drone.id)
        if len(self.enemy_drones_around_base) > 0:
            return True
        else:
            return False

    def check_dead_drones_with_ell(self):
        """
        Метод для вычисления на поле мертвых дронов с эллириумом в трюме.
        id найденных дронов закидываются в self.dead_obj_with_ell_on_field

        :return: True, если на поле обнаружены дроны, и False, если дроны не обнаружены
        :rtype: bool
        """

        dead_drones = self.ret_drones_by_status(filter_alive=False, filter_our=None)
        found_dead_drones = False
        for drone in dead_drones:
            if drone.is_empty is False:
                found_dead_drones = True
                if drone.id not in self.dead_obj_with_ell_on_field.keys():
                    self.dead_obj_with_ell_on_field[drone.id] = 1
                else:
                    self.dead_obj_with_ell_on_field[drone.id] += 1
        return found_dead_drones

    def check_dead_enemy_bases_with_ell(self):
        """
        Метод для вычисления на поле мертвых баз с эллириумом в трюме.
        id найденных баз закидываются в self.dead_obj_with_ell_on_field

        :return: True, если на поле обнаружены базы, и False, если базы не обнаружены
        :rtype: bool
        """

        dead_bases = self.ret_enemy_bases_by_status(filter_alive=False)
        found_dead_bases = False
        for base in dead_bases:
            if base.is_empty is False:
                found_dead_bases = True
                self.dead_obj_with_ell_on_field[base.id] = None
        return found_dead_bases

    def check_enemy_bases_without_drones(self):
        """
        Метод для вычисления на поле баз, находящихся слишком далеко от живых дронов (любой команды)
        id найденных баз закидываются в self.enemy_bases_without_drones

        :return: True, если на поле обнаружены базы вне дистанции выстрела, и False, если базы не обнаружены
        :rtype: bool
        """

        for enemy_bases_id in self.enemy_bases_without_drones:
            enemy_base = self.get_object_for_id(enemy_bases_id)
            if enemy_base.is_alive is False:
                self.enemy_bases_without_drones.remove(enemy_bases_id)
                del self.attack_points[enemy_bases_id]
        alive_bases = self.ret_enemy_bases_by_status(filter_alive=True)
        for base in alive_bases:
            if base.is_empty is False:
                drones_and_base = all([base.distance_to(drone) > self.shot_distance * 0.90 for drone in
                                       self.ret_drones_by_status(filter_alive=True, filter_our=False)])
                if drones_and_base is True:
                    if base.id not in self.enemy_bases_without_drones:
                        self.enemy_bases_without_drones.append(base.id)
                else:
                    if base.id in self.enemy_bases_without_drones:
                        self.enemy_bases_without_drones.remove(base.id)
        if len(self.enemy_bases_without_drones) > 0:
            return True
        else:
            return False

    def check_mothership_health(self):
        """
        Метод для проверки здоровья родного материнского корабля

        :return: True, если материнский корабль при смерти, и False, если все в порядке
        :rtype: bool
        """

        if self.all_objects_on_field['my_base'].health < self.MAX_MOTHERSHIP_HEALTH * self.MIN_MOTHERSHIP_HEALTH:
            return True
        return False

    @property
    def ret_dead_or_alive_my_drones_main_status(self):
        """
        Метод для проверки факта гибели всей команды

        :return: True, если хотя бы один дрон жив, и False, если все мертвы
        :rtype: bool
        """

        dead_or_alive_my_drones = [drone.is_alive for drone in self.all_objects_on_field['my_drones']]
        return any(dead_or_alive_my_drones)

    @property
    def ret_object_identify_status(self):
        """
        Метод для проверки заполнения атрибутов с объектами на поле

        :return: True, если все атрибуты заполнены, и False, если хотя бы один не заполнен
        :rtype: bool
        """

        return all([None not in self.all_objects_on_field.values(), self.defend_points,
                    self.attack_points, self.my_quadrant, self.shot_distance])

    @property
    def ret_my_drones_roles(self):
        """
        Метод для получения текущих ролей у дронов из моей команды

        :return: список ролей, принадлежащих моим дронам
        :rtype: list
        """

        return [drone.role for drone in self.all_objects_on_field['my_drones']
                if drone.role is not None and drone.is_alive is True]

    def ret_drones_with_current_path_target(self, filter_target):
        """
        Метод для получения текущих ролей у дронов из моей команды

        :param filter_target: id объекта или точка, к которой летит дрон (или на которой уже находится)
        :type filter_target: id or Point
        :return: список дронов, летящих к точке или объекту из filter_target
        :rtype: list
        """

        return [drone for drone in self.all_objects_on_field['my_drones'] if drone.current_path_target == filter_target]

    def ret_drones_by_status(self, *, filter_alive: bool, filter_our: bool or None):
        """
        Метод для получения списка дронов по разным параметрам

        :param filter_alive: настройка, определяющая живых или мертвых дронов нужно вернуть
        (True, если живых, False, если мертвых)
        :type filter_alive: bool
        :param filter_our: настройка, определяющая принадлежность дрона к команде (по системе свой/чужой) - True,
        если нужно вернуть дронов из своей команды, и False, если нужно вернуть дронов из чужих команд и None, если
        данный параметр не важен
        :type filter_our: bool or None
        :return: список дронов
        :rtype: list
        """

        if filter_alive is True:
            if filter_our is True:
                return [drone for drone in self.all_objects_on_field['my_drones'] if drone.is_alive is True]
            elif filter_our is False:
                return [drone for drone in self.all_objects_on_field['enemy_drones'] if drone.is_alive is True]
            elif filter_our is None:
                return [drone for drone in self.all_objects_on_field['all_drones'] if drone.is_alive is True]
        elif filter_alive is False:
            if filter_our is True:
                return [drone for drone in self.all_objects_on_field['my_drones'] if drone.is_alive is False]
            elif filter_our is False:
                return [drone for drone in self.all_objects_on_field['enemy_drones'] if drone.is_alive is False]
            elif filter_our is None:
                return [drone for drone in self.all_objects_on_field['all_drones'] if drone.is_alive is False]

    def ret_enemy_bases_by_status(self, *, filter_alive: bool):
        """
        Метод для получения списка баз по параметру

        :param filter_alive: настройка, определяющая живые или мертвые базы нужно вернуть
        (True, если живых, False, если мертвых)
        :type filter_alive: bool
        :return: список баз
        :rtype: list
        """

        if filter_alive is True:
            return [base for base in self.all_objects_on_field['enemy_bases'] if base.is_alive is True]
        elif filter_alive is False:
            return [base for base in self.all_objects_on_field['enemy_bases'] if base.is_alive is False]

    @property
    def ret_current_path_targets_in_my_drones(self):
        """
        Метод для получения текущих целей полета у дронов из моей команды

        :return: список текущих целей дронов (к которым они летят или к которым уже прилетели)
        :rtype: list
        """

        return [drone.current_path_target for drone in self.all_objects_on_field['my_drones']
                if drone.current_path_target is not None and drone.is_alive is True]
