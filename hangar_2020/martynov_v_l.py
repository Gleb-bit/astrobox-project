import logging
import math

from astrobox.core import Drone
from astrobox.themes.default import MOTHERSHIP_HEALING_DISTANCE
from robogame_engine.geometry import Point, Vector
from robogame_engine.theme import theme

delay = 0

log = logging.getLogger('martynov_log')
log.setLevel(level=logging.INFO)

log_path = 'martynov_log.log'

file_handler = logging.FileHandler(log_path, encoding='utf8')
file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
file_handler.setLevel(level=logging.ERROR)
log.addHandler(file_handler)



class MartynovDrone(Drone):
    distance_loaded = 0
    distance_unloaded = 0
    distance_partly_loaded = 0
    end_game = 0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        log.info('Лог создан 2')
        self.target_to_collect = list()
        self.target_to_shoot = list()
        self.act_mode = 'collect'
        self.gun_activated = False
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
            'collector':0

        }

    def _sum_distance(self, target):
        """
        считаем пройденную дистанцию Дроном в одном из состояний загрузки
        """
        if self.is_full:
            self.distance_loaded += self.distance_to(target)
        elif self.is_empty:
            self.distance_unloaded += self.distance_to(target)
        else:
            self.distance_partly_loaded += self.distance_to(target)


    def move_at(self, target, speed=None):
        """
        добавляем к методу move_at() основного класса подсчёт дистанции
        """
        super().move_at(target, speed=speed)
        self._sum_distance(target)

    def on_born(self):
        self.debug(f'on_born 1 => action_analytics')
        self.action_analytics()
        self.debug(f'on_born 2 => collect_or_attack')
        self.collect_or_attack()
        self.logger.addHandler(file_handler)
        self.debug(f"I'm borning {self.id}")

    def collect_or_attack(self):
        """
        Думаем, что делать и делаем
        Защищаем, если противников больше, чем живых союзников
        """

        all_on_mothership, alive_enemy, collect_from = self._prepare_analityc()


        if self.near(self.mothership):
            if not self.is_empty:
                self.unload_to(self.mothership)

        if self.distance_to(self.mothership) < 150 and self.act_mode == 'attack':
            self.act_mode = 'defender'
        elif self.dict_analytic['alive_drones'] > self.dict_analytic['alive_teammates']:
            self._deffend_or_collect(all_on_mothership=all_on_mothership)

        elif alive_enemy \
                and all_on_mothership:
            self._if_all_enemy_on_motherships(collect_from)
        elif alive_enemy != 0:
            self.act_mode = 'attack'
        elif collect_from:
            self.debug(f'collect_or_attack 5 => self.act_mode: collect')
            self.act_mode = 'collect'
        elif alive_enemy == 0 and collect_from == 0:
            self.debug(f'collect_or_attack 1 => self.act_mode: back')
            self.act_mode = 'back'

    def _deffend_or_collect(self, all_on_mothership):
        if self.target_to_shoot and self.target_to_collect and \
                self.distance_to_mother(self.target_to_shoot[0]) * 0.7 > self.distance_to_mother(
            self.target_to_collect[0]) and all_on_mothership:
            self.act_mode = 'collect'

        self.act_mode = 'defender'
        self.debug(f'collect_or_attack 1 => self.act_mode: defender')

    def _if_all_enemy_on_motherships(self, collect_from):
        if collect_from:
            self.act_mode = 'collect'
        elif not self.is_empty:
            self.act_mode = 'back'
        elif self.dict_analytic['alive_motherships']:
            self.act_mode = 'attack'
        else:
            self.act_mode = 'defender'

    def distance_to_mother(self, other):
        """
            The distance to other points
        """
        return math.sqrt((self.mothership.coord.x - other.x) ** 2 + (self.mothership.coord.y - other.y) ** 2)

    def _prepare_analityc(self):
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

    def print_my_statistic(self):
        print('-' * 35)
        print(f'Статистика по полётам всех MartynovDrone:\n'
              f'Летали загруженными полностью: {self.distance_loaded},\n'
              f'Летали загруженными НЕполностью: {self.distance_partly_loaded},\n'
              f'Летали пустыми: {self.distance_unloaded}')
        print('-' * 35)

    def on_wake_up(self):
        self.act_mode = 'defender' if self.act_mode is None else self.act_mode

    def wandering_in_space(self):
        """
        Можем ли блуждать по полю?
        :return:
        """

        if self.is_alive is False:
            self.target_to_collect = list()
            self.target_to_shoot = list()
            self.point_to = None
            self.choice_collect = list()
            self.debug(f'wandering_in_space 1 => Дрона нет в живых.')
            return False
        # Возврат на базу, если жизней менее или равно 50%
        elif self.health < 70:
            self.point_to = self.mothership
            self.act_mode = 'back'
            self.debug(f'wandering_in_space 2 => self.act_mode = back')
            return True

        else:
            # Если можем, то блуждаем
            self.debug(f'wandering_in_space 3 => Жив и действует')
            return True

    def next_action(self):
        self.debug(f'Привет, я дрон {self}')
        if self.is_alive:
            self.debug(f'on_heartbeat 1 => action_analytics')
            self.action_analytics()
            self.collect_or_attack()
        # Действуем, только если живы
        if self.wandering_in_space():

            if self.act_mode == 'collect':
                self.debug(f'on_heartbeat 2 => space_collect_from')
                self.space_collect_from()
            # Если закончились ресурсы на астероидах, то аттачим
            elif self.act_mode == 'attack':
                self.debug(f'on_heartbeat 3 => space_enemy_attack')
                self.space_enemy_attack()

            elif self.act_mode == 'mother_attack':
                self.debug(f'on_heartbeat 3 => space_enemy_attack')
                self.space_enemy_mother_attack()

            elif self.act_mode == 'defender':
                self.debug(f'on_heartbeat 3 => space_enemy_attack')
                self.defend_my_base()

            elif self.act_mode == 'back':
                self.debug(f'on_heartbeat 5 => return_to_base')
                self.return_to_base()

            self.check_game_over()

    def on_heartbeat(self):
        self.next_action()

    def space_enemy_attack(self):

        if self.point_to is None:
            self.debug(f'space_enemy_attack 1 => _get_near_point + _get_places_near_enemy')
            self.point_to = self._get_near_point(self, self._get_places_near_enemy())

        self._attack_move_or_turn()

        vec = Vector.from_points(self.coord, self.target_to_shoot[0].coord)
        if abs(vec.direction - self.direction) < 10:
            if self.teammates_on_attack_line():
                self.debug(f'space_enemy_attack 5 => gun.shot')
                self.gun.shot(self.target_to_shoot[0])
            else:
                self.debug(f'space_enemy_attack 6 => _get_near_point + _get_places_near_enemy')
                self.move_at(self.point_to)

    def _attack_move_or_turn(self):
        if not self.near(self.point_to):
            self.debug(f'space_enemy_attack 2 => move_at')
            self.move_at(self.point_to)
        elif self.distance_to(self.target_to_shoot[0]) >= self.gun.shot_distance:
            self.debug(f'space_enemy_attack 3 => _get_near_point + _get_places_near_enemy')
            self.point_to = self._get_near_point(self, self._get_places_near_enemy())
            self.move_at(self.point_to)
        else:
            self.debug(f'space_enemy_attack 4 => turn_to')
            self.turn_to(self.target_to_shoot[0])

    def defend_my_base(self):
        """
        Выбор точки для атаки
        Защищаем, если рядом с матерью
        :return:
        """

        if not self.point_to or self.distance_to(self.mothership) < MOTHERSHIP_HEALING_DISTANCE * 0.9:
            self.point_to = self._get_near_point(self, self._get_places_near_mothership())

        if self.point_to and not self.near(self.point_to):
            self.move_at(self.point_to)
        elif self.near(self.point_to):
            self.choice_action()

    def choice_action(self):
        if self.target_to_shoot:
            vec = Vector.from_points(self.coord, self.target_to_shoot[0].coord)
            if abs(vec.direction - self.direction) >= 7:
                self.turn_to(self.target_to_shoot[0])

            # if self.distance_to(self.target_to_shoot[0]) <= self.gun.shot_distance:
            if self.teammates_on_attack_line():
                self.gun.shot(self.target_to_shoot[0])

    def teammates_on_attack_line(self):
        """
        Отвеч на вопрос "есть ли союзники на линии атаки?"
        Допилить чем ближе к союзнику, тем больше угол до союзника
        Возможно как-то с помощью прямоугольного треугольника...
        :return:
        """

        can_attack = [
            (abs(self.direction - Vector.from_points(self.coord, drone.coord).direction) > 25
             or self.distance_to(self.target_to_shoot[0]) < self.distance_to(drone))
            and not self.near(self.mothership)
            for drone in self.teammates
        ]

        return all(can_attack)

    def _get_places_near_enemy(self):

        point_list = list()
        directions_list = list()
        start_vector = Vector(x=self.target_to_shoot[0].x, y=self.target_to_shoot[0].y)

        distance_to_target = self.distance_to(self.target_to_shoot[0])
        shot_dist_with_koef = self.gun.shot_distance * 0.7

        distance_to_shot = distance_to_target \
            if shot_dist_with_koef > distance_to_target \
            else shot_dist_with_koef

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

        self.debug(f'_get_places_near_enemy нашли токчи рядом с дроном противником')
        return point_list

    def _get_near_point(self, team_object, all_point_list):
        """
        Ближайшаа точка из списка точек
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
        self.debug(f'_get_near_point 1 => выбрал {choice_point[0]} из точек {choice_point}.')

        return choice_point[0] if choice_point else False

    def point_near_point(self, first, second):
        points_dist = math.sqrt((first.x - second[0]) ** 2 + (first.x - second[1]) ** 2)

        return points_dist <= self.radius / 10

    def _get_places_near_mothership(self):
        """
        Все точки рядо с матерью
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

        self.debug(f'_get_places_near_mothership нашли токчи рядом с матерью')
        return point_list

    def check_game_over(self):
        whats_going_on = sum([value for key, value in self.dict_analytic.items()])
        if whats_going_on and self.near(self.mothership):
            MartynovDrone.end_game += 1

        if self.end_game == len(self.teammates) + 1:
            self.print_my_statistic()

    def return_to_base(self):
        """
        Возвращаемся на базу и ничего не делаем. Конец игры.
        :return:
        """

        if self.near(self.mothership):
            self.debug(f'return_to_base 1 => return')
            if not self.is_empty:
                self.unload_to(self.mothership)

        else:
            self.debug(f'return_to_base 2 => move_at {self.mothership}')
            self.move_at(self.mothership)

    def space_collect_from(self):

        if not self.target_to_collect:
            return

        # Если на астероиде
        if self.near(self.target_to_collect[0]):
            # Не пустой - собираем
            if not self.target_to_collect[0].is_empty:

                self.debug(f'on_stop_at_asteroid => load_from {self.target_to_collect[0]}')
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
        if not self.choice_collect:
            self.debug('on_load_complete, choice_collect is None')
            self.point_to = self.mothership
            self.move_at(self.point_to)
        else:
            self.target_to_collect = [self.mothership, 0, 0, 'self.mothership'] \
                if self.is_full else self.choice_collect[0]

            self.debug('on_load_complete', self.target_to_collect)
            self.point_to = self.target_to_collect[0]
            self.move_at(self.point_to)

    def _collect_if_transition(self):
        if self._transition:
            # Выбор, на астероид или на базу
            next_target = self._elerium_gathering()
            self.debug(f'space_collect_from 1 => turn_to {next_target[0]}')
            self.turn_to(next_target[0])
        else:
            # Если полный трюм, меняем маршрут в полёте и летим разгружаться
            if self.is_full:
                self.point_to = self.mothership
                self.debug(f'space_collect_from_asteroid 2 => move_at {self.point_to}')
                self.move_at(self.point_to)
            else:
                if self.target_to_collect[2] > 0:
                    self.point_to = self.target_to_collect[0]
                    self.debug(f'space_collect_from_asteroid 3 => move_at {self.point_to}')
                    self.move_at(self.point_to)
                    # Если есть ресурс в трюме, НО задача атаковать, то сбрасываем отвозим.
                else:
                    # Если у нашей цели закончился элириум
                    self.debug(f'space_collect_from_asteroid 4 => move_to_new_asteroid')
                    self.move_to_new_asteroid()

    def _collect_if_at_mothership(self):
        self.debug(f'on_stop_at_mothership')
        # Дрон не пустой - отдаём матери
        if not self.is_empty:
            self.unload_to(self.mothership)
            if self._transition and self.target_to_collect:
                self.turn_to(self.target_to_collect[0])
        else:
            # Если дрон пустой, летим к следующей цели
            if not self.choice_collect:
                self.debug('on_unload_complete, choice_collect is None')
            else:
                self.target_to_collect = self.choice_collect[0]
                self.debug('on_unload_complete', self.target_to_collect)
                self.point_to = self.target_to_collect[0]
                self.move_at(self.point_to)

    def near(self, obj):
        """
        Is it near to the object?
        :param obj:
        :return:
        """

        return self.distance_to(obj) <= self.radius / 10

    def _enemy_mother_analytics(self):
        self.debug('Выбираем мать для атаки!')

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
            if mothership != self.mothership
               and mothership.is_alive is True
               and mothership.team not in mothers_defend
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
                self.debug(f'_enemy_drone_analytics 1 => near_enemy {choice_motherships}')
                self.near_enemy(choice_motherships)
            else:
                self.debug(f'_enemy_drone_analytics 2 => near_enemy не поменялась {self.target_to_shoot}')
        else:
            self.target_to_shoot = None
            self.debug(f'_enemy_drone_analytics 3 => Нет Матерей для атаки!')

    def _enemy_drone_analytics(self):
        """
        Выбор ближайшего дрона противника
        Мониторинг живых противников.
        """
        choice_drones = [
            [
                drone,
                self.distance_to(drone),
                drone.team,
                'drone',
                drone.distance_to(drone.mothership)
            ] for drone in self.scene.drones
            if drone not in self.teammates
               and drone != self
               and drone.is_alive is True
        ]
        self.dict_analytic['alive_drones'] = len(choice_drones)
        enemy_drones_on_mothership = [drone for drone in choice_drones if drone[4] <= 250]
        self.dict_analytic['enemy_drones_on_mothership'] = len(enemy_drones_on_mothership)
        # Ближайший противник

        # !!! Выбираем ближайшую цель только если цели нет
        # или дистанция до цели у защитников более 30%
        # у остальных более 70%
        if self.act_mode == 'defender':
            shot_dist_koef = 0.3
        else:
            shot_dist_koef = 0.7

        if self.dict_analytic['alive_drones']:
            if (
                    not self.target_to_shoot
                    or not self.target_to_shoot[0].is_alive
                    or self.distance_to(self.target_to_shoot[0]) > self.gun.shot_distance * shot_dist_koef
            ):
                self.debug(f'_enemy_drone_analytics 1 => near_enemy {choice_drones}')
                self.near_enemy(choice_drones)
            else:
                self.debug(f'_enemy_drone_analytics 2 => near_enemy не поменялась {self.target_to_shoot}')
        else:
            self.target_to_shoot = None
            self.debug(f'_enemy_drone_analytics 3 => Нет дронов для атаки!')

    def near_enemy(self, object_list):
        """
        Выбор ближайшего врага.
        :param object_list:
        :return:
        """

        if not object_list:
            self.debug('Враг не найден.')
            self.target_to_shoot.clear()
            self.debug(f'near_enemy 1 => Объект не найден. Очищаю список объектов для атаки.')
        else:
            object_list.sort(key=lambda x: x[1])
            new_target_to_shoot = object_list[0]
            # Если новая цель, то выбираем точку для атаки.
            if new_target_to_shoot != self.target_to_shoot:
                self.target_to_shoot = new_target_to_shoot
            self.debug(f'near_enemy 2 => Враг найден {self.target_to_shoot}, точка для атаки {self.point_to}')

    def near_collect(self, object_list):
        """
        Выбор ближайшего объекта для сбора.
        :param object_list:
        :return:
        """

        if not object_list:
            self.debug('Объект не найден.')
            self.target_to_collect.clear()
            self.debug(f'near_collect 1 => Объект не найден. Очищаю список объектов для сбора.')
        else:
            object_list.sort(key=lambda x: x[1])
            self.target_to_collect = object_list[0]
            self.debug(f'near_collect 2 => Объект найден.')

    def action_analytics(self):
        self.debug(f'action_analytics 1 => _enemy_drone_analytics.')
        self._enemy_drone_analytics()

        if not self.target_to_shoot \
                or self.dict_analytic['enemy_drones_on_mothership'] == self.dict_analytic['alive_drones']:
            self.debug(f'action_analytics 2 => _enemy_mother_analytics.')
            self._enemy_mother_analytics()


        self.debug(f'action_analytics 3 => _collect_analytics.')
        self._collect_analytics()
        self.debug(f'action_analytics 3 => collect_or_attack.')

    def _collect_analytics(self):
        # Анализируем, с кого можно фармануть
        # первы делом отдаём уже зарезервированные объекты.

        asteroid_target = self._asteroid_target_team()
        # Отбираем астероиды с payload > 0

        self.choice_collect = [
            [
                asteroid,
                self.distance_to(asteroid),
                asteroid.payload,
                'asteroid',
            ] for asteroid in self.asteroids
            if asteroid.payload > 0
               and asteroid not in asteroid_target
        ]

        self.dict_analytic['asteroid'] = len(self.choice_collect)
        self.debug(f'_collect_analytics 1 => '
                     f'добавлено астероидов для сбора: {self.dict_analytic["asteroid"]}')

        # if len(self.choice_collect) == 0:
        # Отбираем мёртвые базы с fullness > 0
        another_mothership = [
            [
                mothership,
                self.distance_to(mothership),
                mothership.payload,
                'mothership',
            ] for mothership in self.scene.motherships
            if mothership != self.mothership
               and mothership.is_alive is False
               and mothership.payload > 0
        ]

        self.dict_analytic['dead_full_motherships'] = len(another_mothership)

        self.choice_collect.extend(another_mothership)
        self.debug(f'_collect_analytics 1 => '
                     f'добавлено матерей для сбора: {self.dict_analytic["dead_full_motherships"]}')
        # Сортируем исходя из дистанции
        self.choice_collect = sorted(self.choice_collect, key=lambda x: x[1])

        # if len(self.choice_collect) == 0:
        # Отбираем мёртвых дронов с fullness > 0
        another_drones = [
            [
                drone,
                self.distance_to(drone),
                drone.payload,
                'drone',
            ] for drone in self.scene.drones
            if drone != self
               and drone.is_alive is False
               and drone.payload > 0
        ]

        self.dict_analytic['dead_full_drones'] = len(another_drones)
        self.debug(
            f'_collect_analytics 1 => добавлено дронов для сбора: {self.dict_analytic["dead_full_drones"]}')
        self.choice_collect.extend(another_drones)
        self.debug(f'_collect_analytics 1 => '
                     f'всего объектов для сбора: {len(self.choice_collect)}')
        self.near_collect(self.choice_collect)

    def _elerium_gathering(self):
        """
        Если количество Элириума способно заполнить трюм, разворачиваемся к базе
        :return:
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
        self.debug(f'_elerium_gathering 1 => next_target: {next_target}')
        return next_target

    def _get_my_asteroid(self):
        sorted_asteroid = self._choice_near_object()
        # Если есть, то астероид, если нет, то база
        if sorted_asteroid == self.mothership:
            return [self.mothership, 0]
        elif sorted_asteroid is not None:
            return [sorted_asteroid, sorted_asteroid.payload]
        else:
            # Флажок, есть ли в наличии астероиды с ресурсами
            self.attack_mode = 'attack' if sorted_asteroid is None else 'collect'
            self.debug(f'_get_my_asteroid 1 => нет астероидов переключил self.attack_mode: {self.attack_mode}')

    def _choice_near_object(self):
        # Ближайшие к self
        if len(self.choice_collect) > 0:
            first_target = self.choice_collect[0]
            self.debug(f'_choice_near_object 1 => Ближайший объект для сбора: {first_target[0]}')
            return first_target[0]
        else:
            self.debug(f'_choice_near_object 2 => Ближайший объект для сбора: {None}')
            return None

    def move_to_new_asteroid(self):
        # Выбор ближайшего, незанятого астероида
        self.target_to_collect = list() if not self.choice_collect else self.choice_collect[0]
        if self.target_to_collect:
            self.point_to = self.target_to_collect[0]
            self.debug(f'move_to_new_asteroid 1 => move_at: {self.point_to}')
            self.move_at(self.point_to)

    def _asteroid_target_team(self):
        # занятые астероиды
        asteroid_target = [
            team_ship.target_to_collect[0]
            for team_ship in self.teammates
            if team_ship.target_to_collect
               and team_ship.is_alive
        ]
        self.debug(f'_asteroid_target_team 1 => астероиды у союзников: {asteroid_target}')
        return asteroid_target
