import math

from astrobox.core import Drone
from astrobox.themes.default import MOTHERSHIP_HEALING_DISTANCE
from robogame_engine.geometry import Point, Vector
from robogame_engine.theme import theme


class MartynovDrone(Drone):
    """
        Класс MartynovDrone - дрон для сбора элериума и защиты.
        Attributes
        ----------
        target_to_collect - цель для сбора элериума.
        my_near_enemy - ближайший враг.
        target_to_shoot - цель для выстрела.
        act_mode - мод дрона (defender, attack, collect, back).
        point_to - точка для полёта.
        choice_collect - список доступных целей для сбора элериума.
        dict_analytic - подробная аналитика поля боя.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.target_to_collect = list()
        self.my_near_enemy = None
        self.target_to_shoot = list()
        self.act_mode = 'defender'
        self.point_to = None
        self.choice_collect = list()
        self.dict_analytic = {
            'asteroid': 0,
            'dead_full_motherships': 0,
            'dead_full_drones': 0,
            'alive_drones': 0,
            'alive_motherships': 0,
            'enemy_drones_on_mothership': 0,
            'alive_teammates': 0,
            'collector': 0,
            'greed_count': 0

        }

    def move_at(self, target, speed=None):
        """
            Добавляем к методу move_at() основного класса подсчёт дистанции
        """
        super().move_at(target, speed=speed)

    def on_born(self):
        """
            При роздении, защищаем базу,
            собираем аналитику поля боя и принимаем решение, собирать ресурсы или атаковать врагов.
        """
        self.act_mode = 'defender'
        self.action_analytics()
        self.choice_action()

    def choice_action(self):
        """
            Сложная логика выбора действий дрона "act_mode":
            - защищать мать,
            - атаковать врагов,
            - собирать ресурсы,
            - вернуться на базу.
        """

        all_on_mothership, alive_enemy, collect_from = self._prepare_analytic()

        if self.near(self.mothership):
            if not self.is_empty:
                self.unload_to(self.mothership)
                if self.target_to_shoot:
                    self.turn_to(self.target_to_shoot[0])
                elif self.target_to_collect:
                    self.turn_to(self.target_to_collect[0])

        if self.is_full:
            self.act_mode = 'back'
            self.move_at(self.mothership)

        if self.act_mode == 'defender':
            self._if_defender(all_on_mothership)

        elif self.act_mode == 'attack':
            if self.dict_analytic['alive_drones'] >= self.dict_analytic['alive_teammates']:
                self._defend_or_collect()
            else:
                if (not alive_enemy or all_on_mothership) and self.target_to_collect:
                    self.act_mode = 'collect'
                elif alive_enemy and self.target_to_shoot:
                    self.act_mode = 'attack'
                else:
                    self.act_mode = 'back'
        elif self.act_mode == 'back':
            if self.is_empty:
                self.act_mode = 'defender'

        elif self.act_mode == 'collect':
            self._if_collect(collect_from, all_on_mothership)

        if alive_enemy == 0 and collect_from == 0:
            self.act_mode = 'defender'

    def _if_defender(self, all_on_mothership):
        """
            Часть сложной логики выбора действий дрона "act_mode".
            Если зашитник, то...
            :param all_on_mothership: Все ли противники на своих матерях?
            :type all_on_mothership: Bool.
        """
        if not self.is_empty:
            self.act_mode = 'back'
            return

        if self.target_to_collect:
            # Собираем, первым делом, если цель для сбора рядом с матерью.
            if (self.distance_object_to_object(self.mothership, self.target_to_collect[0]) < self.gun.shot_distance
                    and len(self.teammates) > 3):
                self.act_mode = 'collect'
                return
            elif self.dict_analytic['alive_drones'] == 0:
                self.act_mode = 'collect'
                return

        if self.target_to_shoot:
            if self.dict_analytic['alive_drones'] <= self.dict_analytic['alive_teammates'] and self.target_to_shoot:
                self.act_mode = 'attack'
            elif self.dict_analytic['alive_drones'] > self.dict_analytic['alive_teammates'] and not all_on_mothership:
                self._defend_or_collect()
            elif all_on_mothership and self.target_to_shoot[3] == 'mothership':
                self.act_mode = 'attack'
            else:
                self.act_mode = 'defender'
            return

    def _defend_or_collect(self):
        """
            Часть сложной логики выбора действий дрона "act_mode".
            Защищать или собирать элериум.
        """

        # Проверяет дистанцию от ближайшего врага до ближайшего астероида.
        if self.my_near_enemy and self.target_to_collect:

            another_distance = abs(self.distance_object_to_object(self.my_near_enemy[0], self.target_to_collect[0]))
            can_i_take = (

                    another_distance > self.gun.shot_distance
            )
        else:
            can_i_take = True

        # Собираем, если есть астероиды.
        if self.my_near_enemy \
                and self.target_to_collect \
                and can_i_take:
            self.act_mode = 'collect'
        else:
            self.act_mode = 'defender'

    def _if_collect(self, collect_from, all_on_mothership):
        """
            Часть сложной логики выбора действий дрона "act_mode".
            Если сборщик, то...
            :param collect_from: Цель для сбора
            :type collect_from: Объект - астероид или дрон или чужая база.
            :param all_on_mothership: Все ли противники на своих матерях?
            :type all_on_mothership: Bool.
        """
        if self.target_to_collect:
            object_distance = self.distance_object_to_object(self.mothership, self.target_to_collect[0]) \
                              > self.gun.shot_distance
        else:
            object_distance = None

        if object_distance and not all_on_mothership:
            if not self.is_empty:
                self.act_mode = 'back'
            else:
                self.act_mode = 'defender'
        elif collect_from and all_on_mothership:
            self.act_mode = 'collect'
        elif collect_from:
            self.act_mode = 'collect'
        elif not self.is_empty:
            self.act_mode = 'back'
        elif self.dict_analytic['alive_motherships'] != 0 and self.target_to_shoot:
            self.act_mode = 'attack'
        else:
            self.act_mode = 'defender'

    # noinspection PyMethodMayBeStatic
    def distance_object_to_object(self, first, second):
        """
            Дистанция от одного объекта до другого.
            :param first: первый объект
            :type first: объект с координатами "x" и "y".
            :param second: второй объект
            :type second: объект с координатами "x" и "y".
        """
        return math.sqrt((first.coord.x - second.x) ** 2 + (first.coord.y - second.y) ** 2)

    def _prepare_analytic(self):
        """
            Промежуточная аналитика для сложной логики выбора действий дрона "act_mode".
            return:
            all_on_mothership - все враги возле своих баз (поле свободно для сбора =) )
            alive_enemy - количество живых врагов. Есть кого атаковать?
            collect_from - количество объектов с элериумом. Есть с кого собирать?
        """
        self.dict_analytic['alive_teammates'] = len([drone for drone in self.teammates if drone.is_alive])
        alive_enemy = self.dict_analytic['alive_drones'] + self.dict_analytic['alive_motherships']
        collect_from = (
                self.dict_analytic['dead_full_drones']
                + self.dict_analytic['dead_full_motherships']
                + self.dict_analytic['asteroid']
        )

        self.dict_analytic['collector'] = len([
            drone for drone in self.teammates
            if drone.is_alive and drone.act_mode == 'collect'])
        self.dict_analytic['collector'] += 1 if self.act_mode == 'collect' else 0

        all_on_mothership = self.dict_analytic['enemy_drones_on_mothership'] == self.dict_analytic['alive_drones']

        return all_on_mothership, alive_enemy, collect_from

    def on_stop_at_asteroid(self, asteroid):
        self.next_action()

    def on_load_complete(self):
        self.next_action()

    def on_stop_at_mothership(self, mothership):
        self.next_action()

    def on_unload_complete(self):
        self.next_action()

    def on_wake_up(self):
        self.act_mode = 'defender' if self.act_mode is None else self.act_mode

    def wandering_in_space(self):
        """
            Можем ли блуждать по полю?
            Если показатель health меньше допустимой нормы, блуждаем на базу.
            :return:
        """

        if self.is_alive is False:
            self.target_to_collect = list()
            self.target_to_shoot = list()
            self.point_to = None
            self.choice_collect = list()
            return False
        # Возврат на базу, если жизней менее или равно 50%
        elif self.health < 70:
            self.point_to = self.mothership
            self.act_mode = 'back'
            return True

        else:
            # Если можем, то блуждаем
            return True

    def next_action(self):
        """
            - Аналиника,
            - выбор "act_mode",
            - запуск логики работы дрона исходя из "act_mode".
        """
        if self.is_alive:
            self.action_analytics()
            self.choice_action()

        # Действуем, только если живы
        if self.wandering_in_space():

            if self.act_mode == 'collect':
                self.space_collect_from()
            # Если закончились ресурсы на астероидах, то аттачим
            elif self.act_mode == 'attack':
                self.space_enemy_attack()

            elif self.act_mode == 'defender':
                self.defend_my_base()

            elif self.act_mode == 'back':
                self.return_to_base()

    def on_hearbeat(self):
        self.next_action()

    def space_enemy_attack(self):
        """
            Логика работы война. "act_mod" = "attack".
        """
        if self.point_to is None:
            self.point_to = self._get_near_point(self, self._get_places_near_enemy())

        self._attack_move_or_turn()

        vec = Vector.from_points(self.coord, self.target_to_shoot[0].coord)
        if abs(vec.direction - self.direction) < 10:
            if self.teammates_on_attack_line():
                self.gun.shot(self.target_to_shoot[0])
            else:
                self.move_at(self.point_to)

    def _attack_move_or_turn(self):
        """
            Часть логики работы война. "act_mod" = "attack".
            Двигаемся или поворачиваемся?
        """
        if not self.near(self.point_to):
            self.move_at(self.point_to)
        elif self.distance_to(self.target_to_shoot[0]) >= self.gun.shot_distance:
            self.point_to = self._get_near_point(self, self._get_places_near_enemy())
            self.move_at(self.point_to)
        else:
            self.turn_to(self.target_to_shoot[0])

    def defend_my_base(self):
        """
            Логика работы защитника. "act_mod" = "defender".
        """

        self.point_to = self._get_near_point(self, self._get_places_near_mothership())

        if self.point_to and not self.near(self.point_to):
            self.move_at(self.point_to)
        elif self.near(self.point_to):
            self.defender_shot_or_turn()

    def defender_shot_or_turn(self):
        """
            Часть логики работы защитника. "act_mod" = "defender".
            Атакуем или поворачиваемся?
        """
        if self.target_to_shoot:
            vec = Vector.from_points(self.coord, self.target_to_shoot[0].coord)
            if abs(vec.direction - self.direction) >= 7:
                self.turn_to(self.target_to_shoot[0])

            if self.teammates_on_attack_line():
                self.gun.shot(self.target_to_shoot[0])

    def teammates_on_attack_line(self):
        """
            Проверяет "есть ли союзники на линии атаки?"
            :return: True or False
        """
        can_attack = [
            (abs(self.direction - Vector.from_points(self.coord, drone.coord).direction) > 25
             or self.distance_to(self.target_to_shoot[0]) < self.distance_to(drone))
            and not self.near(self.mothership)
            for drone in self.teammates
        ]

        return all(can_attack)

    def _get_places_near_enemy(self):
        """
            Выбор точки возле противника для атаки.
            :return: список доступных точек для атаки.
        """
        point_list = list()
        directions_list = list()
        start_vector = Vector(x=self.target_to_shoot[0].x, y=self.target_to_shoot[0].y)

        distance_to_target = self.distance_to(self.target_to_shoot[0])
        shot_dist_with_rate = self.gun.shot_distance * 0.7

        distance_to_shot = distance_to_target \
            if shot_dist_with_rate > distance_to_target \
            else shot_dist_with_rate

        for direction in range(0, 361, 5):
            point_dir = start_vector.from_direction(direction=direction, module=int(distance_to_shot))

            point_x = point_dir.x + start_vector.x
            point_y = point_dir.y + start_vector.y

            if (theme.FIELD_WIDTH - self.radius >= point_x >= self.radius) \
                    and (theme.FIELD_HEIGHT - self.radius >= point_y >= self.radius):
                directions_list.append(direction)

        start = 0
        stop = len(directions_list)
        step = len(directions_list) // 10 if len(directions_list) // 10 > self.dict_analytic['alive_teammates'] else 5
        angle_list = list()

        for angle in range(start, stop, step):
            angle_list.append(directions_list[angle])
            new_point = start_vector.from_direction(direction=directions_list[angle],
                                                    module=int(distance_to_shot))
            point_x = new_point.x + start_vector.x
            point_y = new_point.y + start_vector.y

            point_list.append(Point(point_x, point_y))

        return point_list

    def _get_near_point(self, team_object, all_point_list):
        """
            Выбор ближайшей точки для team_object из all_point_list.
            :return: Одну точку или False, в случае, если точек нет.

            :param team_object: текущий дрон или союзник.
            :type team_object: дрон.

            :param all_point_list: Список доступных точек.
            :type all_point_list: Point list.
        """
        teammates_point = [
            (drone.x, drone.y) for drone in self.teammates
        ]

        teammates_point.extend(
            [
                (drone.point_to.x, drone.point_to.y) for drone in self.teammates if drone.point_to is not None
            ]
        )

        teammates_point.extend((self.mothership.coord.x, self.mothership.coord.y))

        choice_point = [point for point in all_point_list
                        if (point.x, point.y) not in teammates_point
                        ]

        choice_point.sort(key=lambda x_point: team_object.distance_to(x_point))

        return choice_point[0] if choice_point else False

    def _get_places_near_mothership(self):
        """
            Выбор точки возле матери для защиты.
            :return: список доступных точек для защиты вокруг матери.
        """

        point_list = list()
        directions_list = list()
        start_vector = Vector(x=self.mothership.x, y=self.mothership.y)
        for direction in range(0, 361, 5):
            point_dir = start_vector.from_direction(direction=direction, module=int(MOTHERSHIP_HEALING_DISTANCE * 0.9))

            point_x = point_dir.x + start_vector.x
            point_y = point_dir.y + start_vector.y

            if (theme.FIELD_WIDTH - self.radius >= point_x >= self.radius) \
                    and (theme.FIELD_HEIGHT - self.radius >= point_y >= self.radius):
                directions_list.append(direction)

        start = 0
        stop = len(directions_list)
        step = len(directions_list) // (len(self.teammates) + 1)
        angle_list = list()

        for angle in range(start, stop, step):
            angle_list.append(directions_list[angle])
            new_point = start_vector.from_direction(direction=directions_list[angle],
                                                    module=int(MOTHERSHIP_HEALING_DISTANCE * 0.9))
            point_x = new_point.x + start_vector.x
            point_y = new_point.y + start_vector.y

            point_list.append(Point(point_x, point_y))

        return point_list

    def return_to_base(self):
        """
            Возвращаемся на базу и ничего не делаем. Конец игры.
        """

        if self.near(self.mothership):
            if not self.is_empty:
                self.unload_to(self.mothership)

        else:
            self.move_at(self.mothership)

    def space_collect_from(self):
        """
            Логика работы сборщика. "act_mod" = "collect".
        """
        if not self.target_to_collect:
            return

        # Если на астероиде
        if self.near(self.target_to_collect[0]):
            # Не пустой - собираем
            if not self.target_to_collect[0].is_empty:

                self.load_from(self.target_to_collect[0])

                self._collect_if_transition()
            else:
                # пустой - ищем, куда бы податься
                self._collect_if_is_empty()

        # Если на матери
        elif self.near(self.mothership.coord):
            self._collect_if_at_mothership()
        else:
            if not self.is_full and self.target_to_collect:
                self.move_at(self.target_to_collect[0])
            else:
                self.move_at(self.mothership)

    def _collect_if_is_empty(self):
        """
            Часть логика работы сборщика. "act_mod" = "collect".
            Если в поле, пустой и нечего собирать, думаем куда лететь.
        """
        if not self.choice_collect:
            self.point_to = self.mothership
            self.move_at(self.point_to)
        else:
            self.target_to_collect = [self.mothership, 0, 0, 'self.mothership'] \
                if self.is_full else self.choice_collect[0]

            self.point_to = self.target_to_collect[0]
            self.move_at(self.point_to)

    def _collect_if_transition(self):
        """
            Часть логика работы сборщика. "act_mod" = "collect".
            Пока разгружаемся, думаем куда лететь.
        """
        if self._transition:
            # Выбор, на астероид или на базу
            next_target = self._elerium_gathering()
            self.turn_to(next_target[0])
        else:
            # Если полный трюм, меняем маршрут в полёте и летим разгружаться
            if self.is_full:
                self.point_to = self.mothership
                self.move_at(self.point_to)
            else:
                if self.target_to_collect[2] > 0:
                    self.point_to = self.target_to_collect[0]
                    self.move_at(self.point_to)
                    # Если есть ресурс в трюме, НО задача атаковать, то сбрасываем отвозим.
                else:
                    # Если у нашей цели закончился элириум
                    self.move_to_new_asteroid()

    def _collect_if_at_mothership(self):
        """
            Часть логика работы сборщика. "act_mod" = "collect".
            Если на метери, думаем куда лететь.
        """
        # Дрон не пустой - отдаём матери
        if not self.is_empty:
            self.unload_to(self.mothership)
            if self._transition and self.target_to_collect:
                self.turn_to(self.target_to_collect[0])
        else:
            # Если дрон пустой, летим к следующей цели
            if self.choice_collect:
                self.target_to_collect = self.choice_collect[0]
                self.point_to = self.target_to_collect[0]
                self.move_at(self.point_to)

    def near(self, obj):
        """
        Is it near to the object?
        :param obj:
        :return: Bool.
        """

        return self.distance_to(obj) <= self.radius / 10

    def _enemy_mother_analytics(self):
        """
            Ищем беззащитную база для атаки
        """
        # Матеря с защитой
        mothers_defend = {}

        for drones in self.scene.drones:
            if drones.is_alive and drones.team != self.team:
                if drones.team in mothers_defend:
                    mothers_defend[drones.team] += 1
                else:
                    mothers_defend[drones.team] = 1

        choice_motherships = [
            [
                mothership,
                self.mothership.distance_to(mothership),
                mothership.team,
                'mothership',
            ] for mothership in self.scene.motherships
            if mothership != self.mothership and mothership.is_alive is True and mothership.team not in mothers_defend
        ]

        self.dict_analytic['alive_motherships'] = len(choice_motherships)

        # Принципы выбора матери:
        # 1. Самая близкая и беззащитная к своей базе
        if self.dict_analytic['alive_motherships']:
            if (
                    not self.target_to_shoot
                    or not self.target_to_shoot[0].is_alive
                    or self.distance_to(self.target_to_shoot[0]) > self.gun.shot_distance * 0.7
            ):
                self.near_enemy(choice_motherships)
        else:
            self.target_to_shoot = None

    def _enemy_drone_analytics(self):
        """
            Выбор ближайшего дрона противника для атаки.
            Мониторинг живых противников.
            !!! Выбираем ближайшую цель только если цели нет, или дистанция до цели:
            - у защитников более 30%,
            - у остальных более 70%.
        """
        choice_drones = [
            [
                drone,
                self.distance_to(drone),
                drone.team,
                'drone',
                drone.distance_to(drone.mothership)
            ] for drone in self.scene.drones
            if drone not in self.teammates and drone != self and drone.is_alive is True
        ]
        self.dict_analytic['alive_drones'] = len(choice_drones)
        enemy_drones_on_mothership = [drone for drone in choice_drones if drone[4] <= 350]
        self.dict_analytic['enemy_drones_on_mothership'] = len(enemy_drones_on_mothership)
        # Ближайший противник
        if self.act_mode == 'defender':
            shot_dist_rate = 0.3
        else:
            shot_dist_rate = 0.7

        if self.dict_analytic['alive_drones']:
            if (
                    not self.target_to_shoot
                    or not self.target_to_shoot[0].is_alive
                    or self.distance_to(self.target_to_shoot[0]) > self.gun.shot_distance * shot_dist_rate
            ):
                self.near_enemy(choice_drones)
        else:
            self.target_to_shoot = None

    def near_enemy(self, object_list):
        """
            Выбор ближайшего врага.
            :param object_list: Список врагов.
            :type object_list: drone list.
        """

        if not object_list:
            self.target_to_shoot.clear()
        else:
            object_list.sort(key=lambda x: x[1])
            self.my_near_enemy = object_list[0]
            # Если новая цель, то выбираем точку для атаки.
            if self.my_near_enemy != self.target_to_shoot:
                self.target_to_shoot = self.my_near_enemy

    def near_collect(self, object_list):

        """
            Выбор ближайшего объекта для сбора.
            :param object_list:
            :type object_list: list of object.
        """

        if not object_list:
            self.target_to_collect.clear()
        else:
            object_list.sort(key=lambda x: x[1])
            self.target_to_collect = object_list[0]

    def action_analytics(self):
        """
            Полная аналитика для решения, что делать дрону:
            - Проверка наличия врагов,
            - Проверка наличия свободных матерей,
            - Проверка наличия объектов для сбора ресурсов.
        """
        self._enemy_drone_analytics()

        if not self.target_to_shoot \
                or self.dict_analytic['enemy_drones_on_mothership'] == self.dict_analytic['alive_drones']:
            self._enemy_mother_analytics()

        self._collect_analytics()

    def _collect_analytics(self):
        """
            Анализируем, с кого можно собрать ресурсы.
            Первым делом отдаём уже зарезервированные объекты.
        """

        asteroid_target = self._asteroid_target_team()

        # Отбираем астероиды с payload > 0
        self.choice_collect = [
            [
                asteroid,
                self.distance_to(asteroid),
                asteroid.payload,
                'asteroid',
            ] for asteroid in self.asteroids
            if asteroid.payload > 0 and asteroid not in asteroid_target
        ]

        self.dict_analytic['asteroid'] = len(self.choice_collect)

        # Отбираем мёртвые базы с fullness > 0
        another_mothership = [
            [
                mothership,
                self.distance_to(mothership),
                mothership.payload,
                'mothership',
            ] for mothership in self.scene.motherships
            if mothership != self.mothership and mothership.is_alive is False and mothership.payload > 0
        ]

        self.dict_analytic['dead_full_motherships'] = len(another_mothership)

        self.choice_collect.extend(another_mothership)

        # Сортируем исходя из дистанции
        self.choice_collect = sorted(self.choice_collect, key=lambda x: x[1])

        # Отбираем мёртвых дронов с fullness > 0
        another_drones = [
            [
                drone,
                self.distance_to(drone),
                drone.payload,
                'drone',
            ] for drone in self.scene.drones
            if drone != self and drone.is_alive is False and drone.payload > 0
        ]

        self.dict_analytic['dead_full_drones'] = len(another_drones)

        self.choice_collect.extend(another_drones)

        self.near_collect(self.choice_collect)

    def _elerium_gathering(self):
        """
            Если количество Элириума способно заполнить трюм, разворачиваемся к базе.
            :return: следующий объект для сбора элириума | мать.
        """

        if (self.fullness + (self.target_to_collect[1] / 100)) >= 1:
            next_target = [self.mothership, 0]

        else:
            # Если нет, то к следующему астероиду
            next_target = self._get_my_asteroid()
            if next_target[1] < 0:
                next_target = self._get_my_asteroid()
            else:
                next_target = [self.mothership, 0]
        return next_target

    def _get_my_asteroid(self):
        """
            Выбор следующего объекта для сбора элериума
            :return: следующий объект для сбора элириума | мать.
        """
        sorted_asteroid = self._choice_near_object()
        # Если есть, то астероид, если нет, то база
        if sorted_asteroid == self.mothership:
            return [self.mothership, 0]
        elif sorted_asteroid is not None:
            return [sorted_asteroid, sorted_asteroid.payload]
        else:
            # Флажок, есть ли в наличии астероиды с ресурсами
            self.attack_mode = 'attack' if sorted_asteroid is None else 'collect'

    def _choice_near_object(self):
        """
            Выбор следующего объекта для сбора элериума
            :return: объект | None.
        """
        if len(self.choice_collect) > 0:
            first_target = self.choice_collect[0]
            return first_target[0]
        else:
            return None

    def move_to_new_asteroid(self):
        """
            Двигаемся к ближайшему объекту для сбора элериума.
        """
        self.target_to_collect = list() if not self.choice_collect else self.choice_collect[0]
        if self.target_to_collect:
            self.point_to = self.target_to_collect[0]
            self.move_at(self.point_to)

    def _asteroid_target_team(self):
        """
            Объекты для сбора элериума, занятые союзниками.
            :return: список объектов.
        """
        asteroid_target = [
            team_ship.target_to_collect[0]
            for team_ship in self.teammates
            if team_ship.target_to_collect and team_ship.is_alive
        ]
        return asteroid_target


drone_class = MartynovDrone
