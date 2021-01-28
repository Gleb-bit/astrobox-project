from astrobox.core import Drone
from robogame_engine.geometry import Point, Vector
from hangar_2021.shirokov_a_s_add.brain_center import BrainCenterShirokovDrones
from hangar_2021.shirokov_a_s_add.statistic import StatisticShirokovDrones


class ShirokovDrone(Drone):
    """
    Основной класс для дронов
    """

    my_brain_center = BrainCenterShirokovDrones()  # класс для командного центра
    statistic = StatisticShirokovDrones() if my_brain_center.print_statistic is True else None  # вывод статистики
    commands = {'found_dead_drones_with_ell': (2, my_brain_center.scavenger),
                'found_dead_bases_with_ell': (3, my_brain_center.scavenger),
                'found_enemy_bases_without_drones': (4, my_brain_center.siege_master),
                'mothership_has_little_health': (5, my_brain_center.defender_base),
                'perimeter_alarm': (1, my_brain_center.defender_base)}  # команды дронам о ситуации на поле боя
    HEALTH_LIMIT_PERCENT = 0.60  # здоровье дрона в процентах, при котором дрон летит на родную базу лечиться
    ACCURACY_SHOT_AIMING = 5  # значение в градусах, при котором допустим выстрел по цели
    ACCURACY_CANCEL_SHOT_FRIENDLY_FIRE = 30  # значение в градусах, при котором не допустим выстрел из-за френдли файра

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.role = None  # текущая роль дрона
        self.current_path_target = None  # точка или объект, куда дрон летит в данный момент, либо где находится сейчас

    def on_born(self):
        """
        Базовый метод для рождения дронов, дополнен
        загрузкой параметров игры в self.my_brain_center,
        выдачей стартовой роли и поиском первой цели
        """

        if self.my_brain_center.ret_object_identify_status is False:
            self.my_brain_center.identify_objects(self.asteroids, self.scene.drones,
                                                  self.scene.motherships, self.my_mothership, self.gun.shot_distance)
        self.role = self.my_brain_center.define_start_role(self.id)
        self.find_and_turn_move_target(fly=True)

    def find_and_turn_move_target(self, fly: bool):
        """
        Поиск цели (точки или объекта) и действие (поворот или полет), совершаемое по отношению к цели

        :param fly: приказ, отданный из предущего метода
        :type fly: bool
        :notes: Если fly == True, то дрон летит к найденной цели, если fly == False - поворачивается к ней
        """

        next_target = self.get_path_target(fly)
        if fly is True:
            self.add_move_at(next_target)
        else:
            self.turn_to(next_target)

    def get_path_target(self, fly: bool):
        """
        Поиск цели (точка или объект) для полета

        :param fly: приказ, отданный из предущего метода
        :type fly: bool
        :return: возвращает цель (объект или точку) для дрона (чтобы он к ней либо повернулся, либо полетел)
        :rtype: Point or Object
        :notes: Если цель не найдена, то переключает роль дрона и ищет заново
        (переключение ролей этим методом ограничено очередностью ролей, поэтому в цикл не упадет)
        """

        target = self.role.get_target_for_fly(self.id, fly)
        if target is None:
            self.role = self.my_brain_center.change_default_role(drone_id=self.id)
            return self.get_path_target(fly)
        else:
            return target

    def add_move_at(self, target: object):
        """
        Расширенный вариант базового метода self.move_at(target) с записью текущей цели дрона и выставлением статуса

        :param target: Точка или объект, к которому полетит дрон
        :type target: Point или Object
        """

        if isinstance(target, Point):
            self.current_path_target = target
        else:
            self.current_path_target = target.id
        self.move_at(target)

    def find_and_destroy_combat_target(self):
        """
        Поиск цели и действие (поворот или выстрел), совершаемое по отношению к цели

        :notes: Так как нет смысла поворачиваться к цели, в которую можно выстрелить, то по дефолту всегда стреляем, а
        если не получается выстрелить, то просто поворачиваемся
        :notes: Если цель не получена, то дрон ничего не делает (он может сменить позицию, но это регулируется отдельно)
        """

        next_target_to_destroy = self.get_combat_target()
        if next_target_to_destroy is not None:
            if self.check_not_friendly_fire(next_target_to_destroy) is True:
                self.add_shot(next_target_to_destroy)
            else:
                self.turn_to(next_target_to_destroy)

    def get_combat_target(self):
        """
        Поиск и возврат цели для выстрела

        :return: возвращает Объект, по которому нужно выстрелить
        :rtype: Object
        """

        return self.role.get_target_for_destroy(self.id)

    def add_shot(self, target: object):
        """
        Расширенный вариант базового метода self.gun.shot(target) с проверкой на точность выстрела

        :param target: Объект, по которому дрону отдан приказ стрелять
        :type target: Object
        """

        vector_to_target = Vector.from_points(self.coord, target.coord)  # строим вектор от себя до цели
        self.turn_to(target)
        if vector_to_target.direction - self.ACCURACY_SHOT_AIMING <= \
                self.direction <= \
                vector_to_target.direction + self.ACCURACY_SHOT_AIMING:  # если враг в зоне поражения, то стреляем
            if self.statistic is not None:
                self.statistic.write_shots()
            self.gun.shot(target)
        else:  # если нет, то поворачиваемся к нему
            self.turn_to(target)

    def check_not_friendly_fire(self, potential_target: object):
        """
        Проверка выстрела на friendly fair (циклом просматривает всех сокомандников и,
        если хотя бы один не проходит все проверки то возвращает False)

        :param potential_target: Цель, по которой дрону отдан приказ стрелять
        :type potential_target: Object
        :return: возвращает True, если выстрелить можно, и возвращает False, если стрелять нельзя
        :rtype: bool
        """

        vector_to_target = Vector.from_points(self.coord, potential_target.coord)  # ветор от дрона до цели
        for my_team_drone in self.my_brain_center.ret_drones_by_status(filter_alive=True, filter_our=True):
            if my_team_drone != self:  # в себя никак не попадешь, поэтому себя проверять на friendly fair не нужно
                if self.distance_to(potential_target) > self.distance_to(
                        my_team_drone):  # если дистанция от дрона до цели больше, чем до сокомандника, то теоретически сокомандник может быть прямо между вами и целью - требуется дальнейшая проверка
                    if my_team_drone.near(
                            potential_target) is False:  # если цель и сокомандник находятся слишком близко друг к другу, то игра засчитает урон дрону или базе из другой команды
                        vector_to_teammate = Vector.from_points(self.coord, my_team_drone.coord)
                        if vector_to_target.direction - self.ACCURACY_CANCEL_SHOT_FRIENDLY_FIRE <= \
                                vector_to_teammate.direction <= \
                                vector_to_target.direction + self.ACCURACY_CANCEL_SHOT_FRIENDLY_FIRE:  # проверка на зону поражения - если сокомандник находится в зоне поражения, то при выстреле с высокой вероятностью будет поражен
                            return False  # возвращаем False - нельзя стрелять
        return True  # возвращаем True, если все дроны прошли все проверки в цикле

    # для небоевых классов, боевым классам астероиды без надобности
    def on_stop_at_asteroid(self, asteroid: object):
        """
        Базовый метод, чтобы распознать цель как астероид и остановиться на нем

        :param asteroid: астероид, выданный как цель для полета
        :type asteroid: Asteroid
        """

        if self.role.combat_class is False:
            if asteroid.is_empty is False:
                if asteroid.payload >= self.free_space:
                    self.turn_to(
                        self.my_mothership)  # если после загрузки эллириума у дрона будет забит трюм до максимума, то сразу поворачиваемся к материнскому кораблю
                else:
                    self.find_and_turn_move_target(
                        fly=False)  # если после загрузки эллириума у дрона будет свободное место в трюме, то сразу поворачиваемся к следующей цели
                self.load_from(asteroid)
            else:
                self.find_and_turn_move_target(fly=True)

    # для небоевых классов, боевые классы эллириум не загружают
    def on_load_complete(self):
        """
        Базовый метод распознавания завершения загрузки эллириума
        """

        if self.is_full:
            self.add_move_at(self.my_mothership)
        else:
            self.find_and_turn_move_target(fly=True)

    # для боевых и небоевых классов (боевые останавливаются только на своем материнском корабле, небоевые - на любых
    def on_stop_at_mothership(self, mothership: object):
        """
        Базовый метод, чтобы распознать цель как материнский корабль и остановиться на нем

        :param mothership: материнский корабль, выданный как цель для полета
        :type mothership: Mothership
        """

        if mothership == self.my_mothership:
            if self.is_empty is False:
                self.find_and_turn_move_target(fly=False)
                self.unload_to(mothership)  # на своем материнском корабле разгружаем эллириум (если он есть в трюме)
            else:
                self.find_and_turn_move_target(fly=True)  # если нет эллириума на борту, сразу летим к новой цели
        else:
            if self.role.combat_class is False:  # на чужой материнский корабль могут прилетать только небоевые классы
                self.load_from(mothership)
                self.find_and_turn_move_target(fly=False)
            else:
                self.find_and_turn_move_target(
                    fly=True)  # если все же дрон боевого класса залетел на чужой материнский корабль, то он ищет новую цель

    # для боевых и небоевых классов
    # дроны выгружаются только на собственной базе
    def on_unload_complete(self):
        """
        Базовый метод распознавания завершения разгрузки эллириума
        """

        self.find_and_turn_move_target(fly=True)

    def on_stop_at_target(self, target: object):
        """
        Расширенный вариант базового метода on_stop_at_target с распознаванием дронов (интересуют только мертвые
        дроны, у которых есть эллириум, остальных - пропускаем) (помимо астероидов и материнских кораблей)

        :param target: Точка или объект, к которому полетит дрон
        :type target: Point или Object
        """

        for drone in self.scene.drones:
            if drone.is_alive is False and drone.is_empty is False:
                if drone.near(target) is True:
                    self.other_on_stop_at_drone(drone)
                    return
        super(ShirokovDrone, self).on_stop_at_target(target)

    # только для боевых классов, небоевые не должны останавливаться на точках без объектов
    def on_stop_at_point(self, target: object):
        """
        Базовый метод, чтобы распознать цель как точку

        :param target: точка на карте, выданная как цель для полета
        :type target: object (Point)
        """

        if self.role.combat_class is True:
            self.find_and_destroy_combat_target()

    # только для класс Scavenger (в целях соблюдения общей архитектуры метод в общих классах дронов)
    def other_on_stop_at_drone(self, drone: object):
        """
        Метод, имитирующий архитектуру базовых методов дрона, в котором как цель для полета распознается дрон

        :param drone: дрон, выданный как цель для полета
        :type drone: object
        """

        if self.role.combat_class is False:
            if drone.is_empty is False:
                self.find_and_turn_move_target(fly=False)
                self.load_from(drone)
            else:
                self.find_and_turn_move_target(fly=True)

    def on_wake_up(self):
        """
        Базовый метод для выдачи команды дронам, которые находятся в бездействии
        """
        if self.role.combat_class is False:
            self.find_and_turn_move_target(fly=True)
        else:
            if self.near(self.my_mothership) is True:
                self.find_and_turn_move_target(fly=True)
            else:
                self.find_and_destroy_combat_target()

    def on_heartbeat(self):
        """
        Базовый метод для проверок от имени дрона в реальном времени
        """

        print([(base, base.payload) for base in self.my_brain_center.ret_enemy_bases_by_status(filter_alive=True)])
        print(self.my_mothership.payload)

        if self.statistic is not None:  # блок про статистику, если не выводим, то не обращаем внимания
            if self.my_brain_center.ret_dead_or_alive_my_drones_main_status is False:  # если все дроны мертвы
                if self.statistic.statistics_have_been_displayed is False:  # и мы еще не выводили статистику
                    self.statistic.count_before_output_statistic += 1  # заводим обратный отсчет, чтобы все обработки завершились
                    if self.statistic.count_before_output_statistic > 10:  # по достижении фиксированного значения выводим статистику
                        print(self.statistic.output_statistic())
                        self.statistic.statistics_have_been_displayed = True  # мы вывели статистику, переключаем показатель

        if self.checks_in_heartbeat_for_this_drone() is True:  # делаем проверки для конкретного дрона
            if self.role.checks_in_heartbeat_for_drone_with_role(self.current_path_target) is False:  # делаем проверки для роли конкретного дрона
                self.find_and_turn_move_target(fly=True)  # если проверка на роль не прошла, то общая команда для всех - искать новую цель для полета

            check_field_from_brain_center = self.my_brain_center.checks_in_heartbeat_for_brain_center()  # запрос о состоянии поля
            for key_situation, value_situation_code in check_field_from_brain_center.items():  # обработка запроса о состоянии поля
                if value_situation_code is True and self.role.highest_priority is False:
                    if self.role != self.commands[key_situation][1]:
                        new_role = self.my_brain_center.change_situation_role(drone_id=self.id,
                                                                              situation_code=self.commands[
                                                                                  key_situation][0])
                        if new_role is not None:  # новая роль может не выдаться, а если выдалась, то меняем текущую на новую
                            self.role = new_role

    def checks_in_heartbeat_for_this_drone(self):
        """
        Метод, включающий все проверки для конкретного дрона

        :return: Если все проверки пройдены успешно, то возвращает True, иначе - False
        :rtype: bool
        """

        if self.check_alive_or_dead() is True:
            if self.check_less_limit() is True:
                return True
        return False

    def check_alive_or_dead(self):
        """
        Метод, проверяющий жив дрон или мертв (если мертв, то дается несколько команд)

        :return: Если жив, то возвращается - True, если дрон мертв - False
        :rtype: bool
        """

        if self.is_alive is False:
            if self.statistic is not None:  # блок про статистику, если не выводим, то не обращаем внимания
                if self.id not in self.statistic.destroyed_my_drones:
                    self.statistic.write_dead_drone(self.id)
            return False
        else:
            if self.statistic is not None:  # блок про статистику, если не выводим, то не обращаем внимания
                self.statistic.write_data(combat_class=self.role.combat_class, fullness=self.fullness)
            return True

    def check_less_limit(self):
        """
        Метод, проверяющий здоровье дрона и если оно падает до установленного порога, то дрону отдается команда
        лететь на базу

        :return: Если дрон в порядке, то возвращается - True, если дрону нужно вылечиться, то False
        :rtype: bool
        """

        if self.health <= self.HEALTH_LIMIT_PERCENT * self.my_brain_center.MAX_DRONE_HEALTH:
            self.add_move_at(self.my_mothership)
            return False
        return True


drone_class = ShirokovDrone
