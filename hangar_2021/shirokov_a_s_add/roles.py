from operator import itemgetter
from random import choice
from robogame_engine.geometry import Point, Vector


class RoleAbstract:
    """
    Начальный абстрактный класс для ролей дронов

    :param center: мозговой центр, управляющий поведением дронов
    :type center: object
    """

    my_drones_with_this_role = None  # атрибут для записи id дронов, имеющих роль
    combat_class = None  # атрибут для хранения инфо о том, боевой класс или нет
    highest_priority = None  # атрибут для хранения инфо о том, есть ли у класса приоритет или нет
    distribution = None  # атрибут для хранения инфо о том, нужна ли между дронами система распределения целей
    dict_for_distribution = None  # атрибут для осуществления алгоритма распределения целей
    check_safety_obj = None  # атрибут для хранения инфо о том, нужно ли проверять безопасность объекта полета

    def __init__(self, center):
        self.brain_center = center

    def get_target_for_fly(self, my_drone_id: int, to_move: bool):
        """
        Общий метод для всех ролей, предназначенный для поиска и выбора цели, к которой должен полететь дрон

        :param my_drone_id: id дрона, который запросил поиск цели
        :type my_drone_id: int
        :param to_move: определяет, нужно ли дрону лететь к цели или достаточно к ней повернуться
        :type to_move: bool
        :return: возвращает родной материнский корабль
        :rtype: object
        :notes: в классах-наследниках следует переопределить return
        """

        return self.brain_center.all_objects_on_field['my_base']

    def update_distribution(self):
        """
        Общий метод для обновления информации о распределении целей

        :notes: в классах-наследниках следует переопределить return
        """

        pass

    def checks_in_heartbeat_for_drone_with_role(self, current_path_target_id):
        """
        Общий метод для проверок, нужных только для конкретной роли

        :param current_path_target_id: id объекта, к которому летит дрон (или к которому уже прилетел)
        :type current_path_target_id: int
        :notes: в классах-наследниках следует переопределить return
        """

        return True

    def check_safety_point_or_obj(self, cur_target: int or object, radius_cancel_fly: int):
        """
        Общий метод для проверки безопасности того или иного объекта (нет ли поблизости вражеских дронов)

        :param cur_target: id объекта или точка, к которой летит дрон (или к которой уже прилетел)
        :type cur_target: int или object
        :param radius_cancel_fly: радиус от объекта, если в пределах которого обнаружен враг, то объект считается
        небезопасным
        :type radius_cancel_fly: int
        """

        bc = self.brain_center
        if cur_target == bc.all_objects_on_field['my_base'].id:
            return True
        bc = self.brain_center

        if isinstance(cur_target, int):
            obj = bc.get_object_for_id(cur_target)
            obj_coord = obj.coord
        else:
            obj = cur_target
            obj_coord = obj

        alive_enemy_drones = bc.ret_drones_by_status(filter_alive=True, filter_our=False)
        permissions = []
        for enemy_drone in alive_enemy_drones:
            if permissions.count(False) >= 2:
                return False
            distance = enemy_drone.distance_to(obj)
            if radius_cancel_fly < distance < bc.shot_distance:  # дрон на расстоянии выстрела
                vector_from_enemy_drone = Vector.from_points(enemy_drone.coord, obj_coord)
                if vector_from_enemy_drone.direction - 90 <= enemy_drone.direction <= \
                        vector_from_enemy_drone.direction + 90:  # дрон повернут к цели
                    permissions.append(False)  # дроны на дистанции выстрела и смотрят на цель - отказать
                else:
                    permissions.append(True)  # дроны на дистанции выстрела, но смотрят в другую сторону - разрешить
            elif radius_cancel_fly >= distance:
                permissions.append(False)  # дроны слишком близко к цели - отказать
            else:
                permissions.append(True)  # дроны за дистанцией выстрела - разрешить
        if permissions.count(False) >= 2:
            return False
        else:
            return True


class RoleEarner(RoleAbstract):
    """
    Начальный абстрактный класс для ролей дронов, в качестве назначения имеющих сбор эллириума
    """

    combat_class = False  # переопределяем combat_class
    collecting_resource_from_my_quadrant = None  # атрибут для хранения инфо о том, нужно ли собираеть эллириум с мертвых тел

    def checks_in_heartbeat_for_drone_with_role(self, current_path_target_id: int):
        """
        Проверка для ролей с суперклассом RoleEarner, осуществляющаяся через метод on_heartbeat()

        :param current_path_target_id: id объекта, к которому летит дрон (или к которому уже прилетел)
        :type current_path_target_id: current_path_target_id
        :notes: В данном методе должны быть сосредоточены и распределены по порядку все проверки,
        совершающиеся для небоевых классов
        """

        return self.check_ast_pay_zero(current_path_target_id)

    def check_ast_pay_zero(self, current_path_target_id: int):
        """
        Проверка на определение остатков эллириума у объекта, к которому летит дрон

        :param current_path_target_id: id объекта, к которому летит дрон (или к которому уже прилетел)
        :type current_path_target_id: int
        :return: True, если объект не является родным материнским кораблем и там есть эллириум, False -
        в любом другом случае
        :rtype: bool
        """

        if current_path_target_id != self.brain_center.all_objects_on_field['my_base'].id:
            if self.brain_center.get_object_for_id(current_path_target_id).is_empty is True:
                return False
        return True


class RoleDestroyer(RoleAbstract):
    """
    Начальный абстрактный класс для ролей дронов, в качестве назначения имеющих уничтожение целей
    """

    combat_class = True  # переопределяем combat_class
    shot_distance = None  # дистанция выстрела

    def get_target_for_destroy(self, my_drone_id: int):
        """
        Общий метод для всех ролей с суперклассом RoleDestroyer, предназначенный для поиска и выбора цели
        в качестве мишени

        :param my_drone_id: id дрона, который запросил поиск цели
        :type my_drone_id: int
        :notes: в классах-наследниках следует переопределить return
        """

        return None

    def change_point(self, my_drone_id: int, add_identifier: int = None):
        """
        Общий метод для выбора точки обстрела для всех боевых классов

        :param my_drone_id: id дрона, который запросил выдачу точки
        :type my_drone_id: int
        :param add_identifier: дополнительный идентификатор для поиска точки (по умолчанию None)
        :type add_identifier: int или None
        :notes: в классах-наследниках следует переопределить return
        """

        return None

    def check_right_location(self, current_path_target: int):
        """
        Общий метод для проверки текущей локации для всех боевых классов
        (дрон с такой ролью должен быть либо на базе, либо на точке обстрела)

        :param current_path_target: объект, который нужно проверить (точка)
        :type current_path_target: object
        :return: True, если объект прошел проверки, False -
        если не прошел
        :rtype: bool
        :notes: в классах-наследниках следует переопределить return
        """

        return True


class RoleCollector(RoleEarner):
    """
    Класс Собиратели. Собирает эллириум с астероидов (и, возможно, мертвых дронов)
    в пределах своего квадранта (или, возможно, со всего поля).
    """

    highest_priority = True  # переопределяем highest_priority (у роли-наследника будет высший приоритет)
    collecting_resource_from_the_dead_obj = None  # атрибут для хранения информации о том, нужно ли сборщикам собирать эллириум с мертвых объектов

    def collecting_targets_for_collectors(self, quadrant: bool, dead: bool):
        """
        Метод для сбора потенциальных целей для Сборщиков.

        :param quadrant: значение переменной collecting_resource_from_my_quadrant из дочернего класса
        :type quadrant: bool
        :param dead: значение переменной collecting_resource_from_the_dead_obj из дочернего класса
        :type quadrant: bool
        :return: список потенциальных целей
        :rtype: list
        """

        bc = self.brain_center
        objects_for_fly = []  # собираем список потенциальных целей согласно атрибутам
        if quadrant is True:
            objects_for_fly.extend(bc.all_objects_on_field['asteroids_on_my_quadrant'])
            if dead is True:
                dead_objects = bc.ret_drones_by_status(filter_alive=False, filter_our=None)
                dead_objects = [obj for obj in dead_objects if bc.recognize_quadrant_for_obj(obj) == bc.my_quadrant]
                objects_for_fly.extend(dead_objects)
        else:
            objects_for_fly.extend(bc.all_objects_on_field['all_asteroids'])
            if dead is True:
                dead_objects = bc.ret_drones_by_status(filter_alive=False, filter_our=None)
                objects_for_fly.extend(dead_objects)
        return objects_for_fly


class RoleSeniorCollector(RoleCollector):
    """
    Класс Старшие собиратели.
    Берет в работу только объекты, в которых эллириума больше, чем может вместить его трюм.
    Дроны с данной ролью летают к одному и тому же объекту только по одному.
    """

    my_drones_with_this_role = []  # переопределяем my_drones_with_this_role
    distribution = True  # переопределяем distribution (расределение целей нужно)
    dict_for_distribution = {}  # переопределяем dict_for_distribution для распределения целей
    collecting_resource_from_my_quadrant = False  # переопределяем collecting_resource_from_my_quadrant
    collecting_resource_from_the_dead_obj = True  # переопределяем collecting_resource_from_the_dead_obj

    def __init__(self, center):
        super().__init__(center)
        self.TAKE_INTO_WORK_OBJ_WITH_ELL = center.MAX_DRONE_ELL  # в константу выносим максимальное кол-во эллириума на борту дрона

    def get_target_for_fly(self, my_drone_id: int, to_move: bool):  # переопределили метод из суперкласса
        """
        Метод для выбора цели для старшего сборщика
        (астероиды, у которых эллириума больше максимальной вместимости трюма у дрона)

        :param my_drone_id: id дрона, который запросил поиск цели
        :type my_drone_id: int
        :param to_move: определяет, нужно ли дрону лететь к цели или достаточно к ней повернуться
        :type to_move: bool
        :return: возвращает выбранный для полета объект или None, если объект не найден
        :rtype: object или None
        """

        bc = self.brain_center
        drone = bc.get_object_for_id(my_drone_id)

        if self.distribution is True:
            self.update_distribution()  # обновляем распределение целей

        objects_for_fly = self.collecting_targets_for_collectors(quadrant=self.collecting_resource_from_my_quadrant,
                                                                 dead=self.collecting_resource_from_the_dead_obj)

        info_about_obj = []  # дополняем список потенциальных целей рядом сторонних показателей (только дистанция от дрона до цели)
        for obj in objects_for_fly:
            if obj.payload >= self.TAKE_INTO_WORK_OBJ_WITH_ELL:
                if obj.id not in self.dict_for_distribution.keys() or \
                        self.dict_for_distribution[obj.id] is None:
                    info_about_obj.append([obj, drone.distance_to(obj)])
        try:
            next_obj = min(info_about_obj, key=itemgetter(1))[0]  # выбираем ближайшую цель
        except ValueError:
            return None  # если список пустой, значит цели закончились
        else:
            if to_move is True:
                self.dict_for_distribution[next_obj.id] = my_drone_id  # если дрон собирается лететь к цели, то закидываем инфу о предстоящем полете в атрибут для распределения целей
            return next_obj

    def update_distribution(self):  # переопределили метод из суперкласса
        """
        Метод для обновления объекта, хранящего информацию о распределнии целей между дронами в данной роли
        """

        bc = self.brain_center
        for obj_id, my_drone_id in self.dict_for_distribution.items():
            if my_drone_id is not None:
                if bc.get_object_for_id(obj_id).is_empty is True or \
                        bc.get_object_for_id(my_drone_id).is_alive is False:  # если цель уже исчерпала эллириум или дрон, полетевший к ней, погиб раньше, чем смог долететь, то ставим None (чтобы цель снова участвовала в распределении)
                    self.dict_for_distribution[obj_id] = None


class RoleJuniorCollector(RoleCollector):
    """
    Класс Младшие собиратели.
    Берет в работу все объекты, где есть эллириум в пределах дозволенной области
    Дроны с данной ролью могут летать к одному и тому же объекту одновременно
    """

    my_drones_with_this_role = []  # переопределяем my_drones_with_this_role
    distribution = False  # переопределяем distribution (расределение целей не нужно)
    collecting_resource_from_my_quadrant = True  # переопределяем collecting_resource_from_my_quadrant
    collecting_resource_from_the_dead_obj = False  # переопределяем collecting_resource_from_the_dead_obj

    def __init__(self, center):
        super().__init__(center)
        self.MAX_FREE_SPACE_IN_DRONE = center.MAX_DRONE_ELL  # в константу выносим максимальное кол-во эллириума на борту дрона

    def get_sum_free_space_in_other_drones_on_ast(self, obj_with_ell_id: int):
        """
        Метод суммирует свободное место в трюмах дронов, которые летят к объекту с id = obj_with_ell_id

        :param obj_with_ell_id: id объекта
        :type obj_with_ell_id: object
        :return: суммарное количество свободного места в трюмах
        :rtype: int
        """

        bc = self.brain_center
        list_my_drones = bc.ret_drones_with_current_path_target(obj_with_ell_id)
        sum_free_space = sum([drone.free_space for drone in list_my_drones])
        return sum_free_space

    def get_free_space_in_my_drone(self, my_drone: object):
        """
        Метод для подсчета свободного места в дроне после того, как он обработает свою текущую цель (к которой летит)

        :param my_drone: дрон, который запросил поиск цели
        :type my_drone: object
        :return: возвращает количество свободного места в трюме
        :rtype: int
        """

        bc = self.brain_center
        location_id = my_drone.current_path_target
        if location_id is not None:
            location = bc.get_object_for_id(location_id)
            if location != bc.all_objects_on_field['my_base']:
                return my_drone.free_space - location.payload
        return self.MAX_FREE_SPACE_IN_DRONE

    def get_target_for_fly(self, my_drone_id: int, to_move: bool):
        """
        Метод для выбора цели для младшего сборщика (астероиды или, возможно, мертвые дроны,
        у которых эллириума меньше максимальной вместимости трюма дрона)

        :param my_drone_id: id дрона, который запросил поиск цели
        :type my_drone_id: int
        :param to_move: определяет, нужно ли дрону лететь к цели или достаточно к ней повернуться
        :type to_move: bool
        :return: возвращает выбранный для полета объект или None, если объект не найден
        :rtype: object или None
        """

        bc = self.brain_center
        drone = bc.get_object_for_id(my_drone_id)

        if self.distribution is True:
            self.update_distribution()  # обновляем распределение целей (тут не нужно)

        objects_for_fly = self.collecting_targets_for_collectors(quadrant=self.collecting_resource_from_my_quadrant,
                                                                 dead=self.collecting_resource_from_the_dead_obj)

        info_about_obj = []
        for obj in objects_for_fly:
            if obj.is_empty is False:
                sum_fs = self.get_sum_free_space_in_other_drones_on_ast(obj.id)  # суммируем свободное место в трюмах
                if sum_fs < obj.payload:
                    free_ell_in_ast = obj.payload - sum_fs  # определяем остатки эллириума на объекте после того, как с них соберут ресурс дроны, которые уже к нему летят
                    info_about_obj.append([obj, drone.distance_to(obj), free_ell_in_ast])

        drone_free_space = self.get_free_space_in_my_drone(drone)

        info_about_obj = sorted(info_about_obj, key=lambda dist_to_ast: dist_to_ast[2])
        number_dist = len(info_about_obj)
        for info_about_one_obj in info_about_obj:
            free_ell_in_obj = info_about_one_obj[2]
            factor = free_ell_in_obj / (
                drone_free_space if drone_free_space != 0 else 1)  # считаем соотношение будущих остатков эллириума на объекте к будущему free_space у текущего дрона
            priority = factor + number_dist
            info_about_one_obj.append(priority)
            number_dist -= 1
        try:
            next_asteroid = max(info_about_obj, key=itemgetter(3))[0]
        except ValueError:
            return None
        else:
            return next_asteroid


class RoleScavenger(RoleEarner):
    """
    Класс Падальщики.
    Сидят на базе и вылетают в поле только тогда, когда появляется мертвый объект с эллириумом.
    Дроны с данной ролью могут летать к одному и тому же объекту одновременно, если это чья-то база, если же дрон -
    то только по одному
    """

    my_drones_with_this_role = []  # переопределяем my_drones_with_this_role
    distribution = True  # переопределяем distribution (расределение целей нужно)
    dict_for_distribution = {}  # переопределяем dict_for_distribution для распределения целей
    collecting_resource_from_my_quadrant = False  # переопределяем collecting_resource_from_my_quadrant
    highest_priority = False  # переопределяем highest_priority (здесь - низкий приоритет)
    check_safety_obj = True  # переопределяем check_safety_obj (здесь - True)
    COUNT_OF_STEPS_BEFORE_WORK = 150  # кол-во шагов игры, пока проиграется анимация смерти у дронов
    RADIUS_CANCEL_FLY = 100  # если в радиусе объекта замечены вражеские дроны, то объект не считается безопасным автоматически (без других проверок)

    def get_target_for_fly(self, my_drone_id: int, to_move: bool):
        """
        Метод для выбора цели для Падальщика (ими могут быть только мертвые дроны/базы с эллириумом

        :param my_drone_id: id дрона, который запросил поиск цели
        :type my_drone_id: int
        :param to_move: определяет, нужно ли дрону лететь к цели или достаточно к ней повернуться
        :type to_move: bool
        :return: возвращает выбранный для полета объект или родной материнский корабль, если объект не найден
        :rtype: object
        """

        bc = self.brain_center
        my_drone = bc.get_object_for_id(my_drone_id)
        if my_drone.is_empty is False:
            return bc.all_objects_on_field['my_base']  # если у текущего дрона есть эллириум, то пусть сначала летит на базу для разгрузки

        if self.distribution is True:
            self.update_distribution()  # обновляем распределение целей

        dead_objects_with_ell = []
        for key_obj_id, value_info in bc.dead_obj_with_ell_on_field.items():
            obj = bc.get_object_for_id(key_obj_id)
            if obj.is_empty is False:  # интересуют мертвые объекты, если у них есть эллириум
                if self.check_safety_point_or_obj(key_obj_id, self.RADIUS_CANCEL_FLY) is True:  # если поблизости к объекту нет врагов
                    if obj.payload > bc.MAX_DRONE_ELL:
                            dead_objects_with_ell.append([obj, my_drone.distance_to(obj)])  # если у объекта эллириума больше, чем максимальная вместимость трюма, то лететь можно всем сразу
                    else:
                        if key_obj_id not in self.dict_for_distribution.keys() \
                                or self.dict_for_distribution[key_obj_id] is None:
                            if value_info is None or value_info > self.COUNT_OF_STEPS_BEFORE_WORK:  # летим к дрону, только если у него завершилась анимация смерти
                                dead_objects_with_ell.append([obj, my_drone.distance_to(obj)])
                else:
                    if key_obj_id in self.dict_for_distribution.keys():  # если объект небезопасен, то возвращаем его в алгоритм распределения целей
                        self.dict_for_distribution[key_obj_id] = None
        try:
            next_obj_with_ell = min(dead_objects_with_ell, key=itemgetter(1))[0]
        except ValueError:
            return bc.all_objects_on_field['my_base']
        else:
            if to_move is True:
                self.dict_for_distribution[next_obj_with_ell.id] = my_drone_id
            return next_obj_with_ell

    def update_distribution(self):
        """
        Метод для обновления объекта, хранящего информацию о распределнии целей между дронами в данной роли
        """

        bc = self.brain_center
        for dead_object_id, my_drone_id in self.dict_for_distribution.items():
            if my_drone_id is not None:
                if bc.get_object_for_id(dead_object_id).is_empty is True or \
                        bc.get_object_for_id(my_drone_id).is_alive is False or \
                        bc.get_object_for_id(my_drone_id).near(bc.all_objects_on_field['my_base']) is True:
                    self.dict_for_distribution[dead_object_id] = None

    def checks_in_heartbeat_for_drone_with_role(self, current_path_target_id):  # переопределяем метод одного из суперкласов, добавляя помимо существующих проверок еще одну (на безопасность объекта)
        """
        Проверка для ролей, осуществляющаяся через метод on_heartbeat()

        :param current_path_target_id: id объекта, к которому летит дрон (или к которому уже прилетел)
        :type current_path_target_id: int
        :notes: использует проверки, определенные в суперклассе + кое-что из своего
        """

        if self.check_safety_point_or_obj(current_path_target_id, self.RADIUS_CANCEL_FLY) is True:
            if isinstance(current_path_target_id, int) is True:
                return super(RoleScavenger, self).checks_in_heartbeat_for_drone_with_role(
                    current_path_target_id)
            else:
                return True
        else:
            if current_path_target_id in self.dict_for_distribution.keys():  # если объект небезопасен, то возвращаем его в алгоритм распределения целей
                self.dict_for_distribution[current_path_target_id] = None
        return False


class RoleDefenderBase(RoleDestroyer):
    """
    Класс Защитник Базы.
    Выстраиваются вокруг базы в построение (точки для построения берут из мозгового центра) и отстреливают дронов,
    которые нарушили периметр базы
    """

    my_drones_with_this_role = []  # переопределяем my_drones_with_this_role
    distribution = True  # переопределяем distribution (расределение целей нужно)
    dict_for_distribution = {}  # переопределяем dict_for_distribution для распределения целей
    highest_priority = True  # переопределяем highest_priority (здесь - высший)

    def get_target_for_fly(self, my_drone_id: int, to_move: bool):  # переопределяем метод одного из суперклассов
        """
        Метод для выбора цели для Защитника (либо на базу, либо на точку защиты)

        :param my_drone_id: id дрона, который запросил поиск цели
        :type my_drone_id: int
        :param to_move: определяет, нужно ли дрону лететь к цели или достаточно к ней повернуться (здесь не используется)
        :type to_move: bool
        :return: возвращает либо одну из точек зашиты, либо родной материнский корабль
        :rtype: object
        """

        drone = self.brain_center.get_object_for_id(my_drone_id)
        if self.distribution is True:
            self.update_distribution()
        if my_drone_id in self.dict_for_distribution.keys():
            if self.dict_for_distribution[my_drone_id] is not None:
                return self.dict_for_distribution[my_drone_id]
        if drone.is_empty is True:
            return self.change_point(my_drone_id)  # если дрон пустой, то пусть встает на защиту
        else:
            return self.brain_center.all_objects_on_field['my_base']  # если дрон не пустой, то пусть летит на базу

    def get_target_for_destroy(self, my_drone_id: int):  # переопределяем метод одного из суперклассов
        """
        Метод для выбора цели для Защитника (выбирает цель именно для атаки)

        :param my_drone_id: id дрона, который запросил поиск мишени
        :type my_drone_id: int
        :return: возвращает либо объект, по которому нужно выстрелить, либо None, если объект не найден
        :rtype: object или None
        """

        bc = self.brain_center
        potential_targets = []
        for enemy_drone_id in bc.enemy_drones_around_base:
            enemy_drone = bc.get_object_for_id(enemy_drone_id)
            if enemy_drone.is_alive is True:
                if enemy_drone.distance_to(enemy_drone.my_mothership) > bc.MOTHERSHIP_HEALING_DISTANCE:  # если вражеский дрон находится в зоне жизни своей базы, то по нему бесполезно стрелять
                    potential_targets.append([enemy_drone, bc.all_objects_on_field['my_base'].distance_to(enemy_drone)])
        try:
            next_combat_target = min(potential_targets, key=itemgetter(1))[0]
        except ValueError:
            return None
        else:
            return next_combat_target

    def update_distribution(self):  # переопределили метод одного из суперкласса
        """
        Метод для обновления объекта, хранящего информацию о распределнии точек защиты между дронами
        (дроны не должны толпиться на одной точке, иначе будут стрелять друг по другу)
        """

        bc = self.brain_center
        for def_point, my_drone_id in self.dict_for_distribution.items():
            if my_drone_id is not None:
                my_drone = bc.get_object_for_id(my_drone_id)
                if def_point not in bc.ret_current_path_targets_in_my_drones or \
                        my_drone.is_alive is False:
                    self.dict_for_distribution[def_point] = None

    def change_point(self, my_drone_id: int, add_identifier: int = None):  # переопределили метод в одном из суперклассов
        """
        Метод для выбора точки защиты

        :param my_drone_id: id дрона, который запросил поиск точки защиты
        :type my_drone_id: int
        :param add_identifier: дополнительный идентификатор (здесь не нужен, поэтому None)
        :type add_identifier: None
        :return: возвращает случайную точку защиты
        :rtype: object
        """

        bc = self.brain_center
        potential_points = []
        for defend_point in bc.defend_points:
            if defend_point not in self.dict_for_distribution.keys() or \
                    self.dict_for_distribution[defend_point] is None:
                potential_points.append(defend_point)
        chosen_def_point = choice(potential_points)
        self.dict_for_distribution[chosen_def_point] = my_drone_id
        return chosen_def_point

    def checks_in_heartbeat_for_drone_with_role(self, current_path_target: int or object):
        """
        Проверка для ролей, осуществляющаяся через метод on_heartbeat()

        :param current_path_target: id объекта, к которому летит дрон (или к которому уже прилетел)
        :type current_path_target: int or object
        :notes: использует проверки, определенные в суперклассе + кое-что из своего
        """

        if self.check_right_location(current_path_target) is True:
            return super(RoleDefenderBase, self).checks_in_heartbeat_for_drone_with_role(current_path_target)
        return False

    def check_right_location(self, current_path_target: int or object):  # переопределили метод в одном из суперклассов
        """
        Проверка для ролей, осуществляющаяся через метод on_heartbeat()

        :param current_path_target: id объекта или точка, к которой летит дрон (или к которой уже прилетел)
        :type current_path_target:
        :notes: использует проверки, определенные в суперклассе + кое-что из своего
        """

        bc = self.brain_center
        if current_path_target not in bc.defend_points:
            return False
        else:
            return True


class RoleSiegeMaster(RoleDestroyer):
    """
    Класс Осадный мастер.
    Летит к незащищенной вражеской базе и обстреливает ее, занимая одну из ранее сформированных точек
    """

    my_drones_with_this_role = []  # переопределяем my_drones_with_this_role
    distribution = True  # переопределяем distribution (расределение целей нужно)
    dict_for_distribution = {}  # переопределяем dict_for_distribution для распределения целей
    highest_priority = False  # переопределяем highest_priority (здесь - низший)
    RADIUS_CANCEL_FLY = 100  # если в радиусе объекта замечены вражеские дроны, то объект не считается безопасным автоматически (без других проверок)

    def get_target_for_fly(self, my_drone_id: int, to_move: bool):  # переопределили метод в одном из суперклассов
        """
        Метод для выбора цели для Защитника (либо на базу, либо на точку атаки)

        :param my_drone_id: id дрона, который запросил поиск цели
        :type my_drone_id: int
        :param to_move: определяет, нужно ли дрону лететь к цели или достаточно к ней повернуться (здесь не используется)
        :type to_move: bool
        :return: возвращает либо одну из точек атаки, либо родной материнский корабль
        :rtype: object
        """

        bc = self.brain_center
        my_drone = self.brain_center.get_object_for_id(my_drone_id)
        if my_drone.is_empty is False:
            return bc.all_objects_on_field['my_base']

        if self.distribution is True:
            self.update_distribution()

        base_without_drones = []
        for base_id in bc.enemy_bases_without_drones:
            enemy_base = bc.get_object_for_id(base_id)
            if enemy_base.is_alive is True:
                base_without_drones.append([enemy_base, my_drone.distance_to(enemy_base)])
        try:
            next_base_without_drones = min(base_without_drones, key=itemgetter(1))[0]
        except ValueError:
            return bc.all_objects_on_field['my_base']
        else:
            return self.change_point(my_drone_id, next_base_without_drones.id)

    def update_distribution(self):  # переопределили метод в одном из суперклассов
        """
        Метод для обновления объекта, хранящего информацию о распределении точек атаки между дронами
        (дроны не должны толпиться на одной точке, иначе будут стрелять друг по другу)
        """

        for att_point, my_drone_id in self.dict_for_distribution.items():
            if my_drone_id is not None:
                if att_point not in self.brain_center.ret_current_path_targets_in_my_drones:
                    self.dict_for_distribution[att_point] = None

    def get_target_for_destroy(self, my_drone_id: int):  # переопределили метод в одном из суперклассов
        """
        Метод для выбора цели для Защитника (выбирает цель именно для атаки)

        :param my_drone_id: id дрона, который запросил поиск мишени
        :type my_drone_id: int
        :return: возвращает либо объект, по которому нужно выстрелить, либо None, если объект не найден
        :rtype: object или None
        """

        bc = self.brain_center
        my_drone = bc.get_object_for_id(my_drone_id)
        potential_targets = []
        for enemy_base in bc.ret_enemy_bases_by_status(filter_alive=True):
            potential_targets.append([enemy_base, my_drone.distance_to(enemy_base)])
        try:
            next_combat_target = min(potential_targets, key=itemgetter(1))[0]
        except ValueError:
            return None
        else:
            return next_combat_target

    def change_point(self, my_drone_id: int, add_identifier: int = None):  # переопределили метод в одном из суперклассов
        """
        Метод для выбора точки атаки

        :param my_drone_id: id дрона, который запросил поиск точки защиты
        :type my_drone_id: int
        :param add_identifier: дополнительный идентификатор (здесь нужен - id вражеской базы)
        :type add_identifier: int
        :return: возвращает случайную точку атаки или родную базу
        :rtype: object
        """

        bc = self.brain_center
        base_id = add_identifier
        potential_attack_points = []
        for att_point in bc.attack_points[base_id]:
            if att_point not in self.dict_for_distribution.keys() or \
                    self.dict_for_distribution[att_point] is None:
                if self.check_safety_point_or_obj(att_point, self.RADIUS_CANCEL_FLY) is True:
                    potential_attack_points.append(att_point)
        try:
            chosen_point = choice(potential_attack_points)
        except IndexError:
            return bc.all_objects_on_field['my_base']
        else:
            self.dict_for_distribution[chosen_point] = my_drone_id
            return chosen_point

    def checks_in_heartbeat_for_drone_with_role(self, current_path_target: int or object):  # переопределили метод в одном из суперклассов
        """
        Проверка для ролей, осуществляющаяся через метод on_heartbeat()

        :param current_path_target: id объекта, к которому летит дрон (или к которому уже прилетел)
        :type current_path_target: int or object
        :notes: использует проверки, определенные в суперклассе + кое-что из своего
        """

        if self.check_right_location(current_path_target) is True:
            if self.check_safety_point_or_obj(current_path_target, self.RADIUS_CANCEL_FLY) is True:
                return super(RoleSiegeMaster, self).checks_in_heartbeat_for_drone_with_role(current_path_target)
            else:
                if current_path_target in self.dict_for_distribution.keys():  # если объект небезопасен, то возвращаем его в алгоритм распределения целей
                    self.dict_for_distribution[current_path_target] = None
        return False

    def check_right_location(self, current_path_target: Point or int):
        """
        Метод для проверки текущей локации (дрон должен быть либо на базе, либо на точке обстрела)

        :param current_path_target: объект, который нужно проверить (точка)
        :type current_path_target: object or int
        :return: True, если объект прошел проверки, False - если не прошел
        :rtype: bool
        """

        bc = self.brain_center
        if any([current_path_target in att_point for att_point in bc.attack_points.values()]) is False and \
                current_path_target != bc.all_objects_on_field['my_base'].id:
            return False
        else:
            return True

