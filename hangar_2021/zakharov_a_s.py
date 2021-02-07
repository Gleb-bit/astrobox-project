# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
import math
from abc import abstractmethod, ABC
from random import randint

from astrobox.core import Drone, Asteroid
from robogame_engine import GameObject
from robogame_engine.geometry import Point, Vector
from astrobox.themes.default import MOTHERSHIP_HEALING_DISTANCE, CARGO_TRANSITION_DISTANCE
from astrobox.theme import theme


class Strategy(ABC):

    @abstractmethod
    def do_step(self, drone):
        pass


class ZakharovContext:
    my_team = []

    def __init__(self, strategy, my_mothership):
        self.strategies = {
            'Loader': StrategyLoader(),
            'Defender': StrategyDefender(my_mothership.coord),
            'Marauder': StrategyMarauder(),
            'FastLoader': StrategyFastLoader()
        }
        self._strategy = self.strategies[strategy]

    @property
    def strategy(self) -> Strategy:
        return self._strategy

    @strategy.setter
    def strategy(self, strategy):
        if self._strategy and type(self._strategy) == type(self.strategies[strategy]):
            return
        self._strategy = self.strategies[strategy]
        for d in self.my_team:
            d.personal_strategy = None
            d.actions = []
            d.angle = -1

    def valid_place_gun(self, drone, target):
        for partner in self.my_team:
            if (
                    not partner.is_alive or (partner.coord.x == drone.coord.x and partner.coord.y == drone.coord.y)
                    or partner.distance_to(drone) > drone.gun.shot_distance
            ):
                continue
            vec_my_drone = Vector(partner.coord.x - drone.coord.x, partner.coord.y - drone.coord.y)
            vec_target = Vector(target.coord.x - drone.coord.x, target.coord.y - drone.coord.y)
            if vec_my_drone.module < 20:
                return False
            if vec_my_drone.module <= vec_target.module:
                if math.atan(25 / vec_my_drone.module) * (180 / math.pi) > \
                        abs(vec_target.direction - vec_my_drone.direction):
                    return False
        return True

    def near_enemy(self, drone):
        for t in self.my_scene['enemy_teams']:
            for enemy_drone in self.my_scene['enemy_drones'][t]:
                if (drone.distance_to(enemy_drone) < CARGO_TRANSITION_DISTANCE
                        and not enemy_drone.cargo.is_empty
                        and not enemy_drone.is_moving
                ):
                    return enemy_drone
        return None

    def get_enemy_at_gun(self, drone):
        for d in drone.scene.drones:
            if d.team != drone.team and drone.distance_to(d) <= drone.gun.shot_distance and d.is_alive:
                vec1 = Vector(d.coord.x - drone.coord.x, d.coord.y - drone.coord.y)
                if abs(drone.direction - vec1.direction) < 15:
                    return d

    def estimation_scene(self, scene):
        self.my_scene = {
            'sum_payload': sum([asteroid.cargo.payload for asteroid in scene.asteroids]),
            'enemy_motherships': dict([(m.team, m) for m in scene.motherships if m.team != self.my_team[0].team]),
            'enemy_teams': [t for t in scene.teams if t != self.my_team[0].team],
            'count_dead_my_team': len([d for d in self.my_team if not d.is_alive]),
        }

        self.my_scene['enemy_drones'] = dict([(t, [d for d in scene.drones if t == d.team and d.is_alive])
                                              for t in self.my_scene['enemy_teams']])
        safe_length = self.my_team[0].gun.shot_distance
        if len(scene.teams) <= 2 or self.my_scene['sum_payload'] == 0:
            safe_length += MOTHERSHIP_HEALING_DISTANCE
        self.my_scene['enemy_drones_my_mothership'] = \
            dict([(team, [d for d in self.my_scene['enemy_drones'][team]
                          if d.is_empty and not d.is_moving and
                          self.my_team[0].my_mothership.distance_to(d) < safe_length
                          ]
                   ) for team in self.my_scene['enemy_teams']])
        self.my_scene['count_enemy_drones_mothership'] = \
            dict([(t, len([d for d in self.my_scene['enemy_drones'][t]
                           if d.distance_to(self.my_scene['enemy_motherships'][t]) < 10
                           ])
                   ) for t in self.my_scene['enemy_teams']])
        self.my_scene['enemy_drones_defender'] = \
            dict([(t, [d for d in self.my_scene['enemy_drones'][t]
                       if not d.is_moving and
                       (50 < d.distance_to(self.my_scene['enemy_motherships'][t]) <= MOTHERSHIP_HEALING_DISTANCE)])
                  for t in self.my_scene['enemy_teams']])

    def get_step(self, drone):
        if drone.meter_2 < drone.limit_health:
            drone.actions = []
            drone.actions.append(['move', drone.my_mothership])
            if not drone.is_empty:
                drone.actions.append(['unload', drone.my_mothership])
            return
        self.estimation_scene(drone.scene)
        # если возле нашей базы больше 2-х пустых (или 1 ого), не двигающихся дронов (охотников)
        if (
                sum(map(lambda t: len(self.my_scene['enemy_drones_my_mothership'][t]),
                        self.my_scene['enemy_teams'])) > len(drone.scene.teams) // 2
        ):
            self.strategy = 'Defender'
            if self.my_scene['sum_payload'] > 0:
                if len([d for d in self.my_team if d.personal_strategy and isinstance(d.personal_strategy,
                                                                                 StrategyFastLoader)]) < 1:
                    drone.personal_strategy = 'FastLoader'
            # if (
            #         ((len([m for m in drone.scene.motherships if not m.is_alive and not m.cargo.is_empty]) > 0
            #          or any(map(lambda t: len([d for d in self.my_scene['enemy_drones'][t] if d.is_alive]) == 0,
            #                  self.my_scene['enemy_teams'])))
            #          and all(map(lambda t: len(self.my_scene['enemy_drone_defenders'][t])>2,
            #                self.my_scene['enemy_teams']))
            # ):
            #     if len([d for d in self.my_team if d.personal_strategy and isinstance(d.personal_strategy,
            #                                                                      StrategyMarauder)]) < 1:
            #         drone.personal_strategy = 'Marauder'
        # если погибла чужая база или все дроны и нет охотников
        elif ((len([m for m in drone.scene.motherships if not m.is_alive and not m.cargo.is_empty]) > 0 or
               any(map(lambda t: len([d for d in self.my_scene['enemy_drones'][t] if d.is_alive]) == 0,
                       self.my_scene['enemy_teams'])))
              and sum(map(lambda t: len(self.my_scene['enemy_drones_my_mothership'][t]),
                          self.my_scene['enemy_teams'])) < 2
        ):
            self.strategy = 'Marauder'
            # если у любой чужой команды больше 1 дрона
            if any(map(lambda t: len(self.my_scene['enemy_drones'][t]) > 1, self.my_scene['enemy_drones'])):
                # выделяем 3-х защитников
                if len([d for d in self.my_team if d.personal_strategy and
                                               isinstance(d.personal_strategy, StrategyDefender)]) < 3:
                    drone.personal_strategy = 'Defender'
            else:
                for d in self.my_team:
                    d.personal_strategy = None
                    d.actions = []
                    d.angle = -1

        # если мы потеряли дрона и у нас больше элериума чем у любой другой команды
        # и у любой чужой команды больше чем 1 дрон
        elif (
                self.my_scene['count_dead_my_team'] > 0 and
                all(map(lambda t: self.my_team[0].my_mothership.cargo.payload >
                                  self.my_scene['enemy_motherships'][t].cargo.payload, self.my_scene['enemy_teams']))
                and any(map(lambda t: len(self.my_scene['enemy_drones'][t]) > 1, self.my_scene['enemy_drones']))
        ):

            self.strategy = 'Defender'
            # если остался элериум отправляем 1-го грузчика
            if self.my_scene['sum_payload'] > 0 and len([d for d in self.my_team if d.personal_strategy and
                                                            isinstance(d.personal_strategy, StrategyFastLoader)]) < 1:
                drone.personal_strategy = 'FastLoader'
        # если у всех чужих команд  остался 1 дрон и остался элериум
        elif (
                all(map(lambda t: len(self.my_scene['enemy_drones'][t]) == 1,
                        self.my_scene['enemy_drones'])) and
                isinstance(self.strategy, StrategyDefender) and
                self.my_scene['sum_payload'] > 0
        ):
            self.strategy = 'Loader'
        # если у любой  чужой команды  остался 1 дрон и остался элериум
        elif (
                any(map(lambda t: len(self.my_scene['enemy_drones'][t]) == 1,
                        self.my_scene['enemy_drones'])) and
                isinstance(self.strategy, StrategyDefender) and
                self.my_scene['sum_payload'] > 0
        ):
            self.strategy = 'Loader'
            if self.my_scene['count_dead_my_team'] > 0:
                if len([d for d in self.my_team if isinstance(d.personal_strategy, StrategyDefender)]) <= 2:
                    drone.personal_strategy = 'Defender'
        # если мы потеряли больше 1 дрона
        elif self.my_scene['count_dead_my_team'] > 1:
            self.strategy = 'FastLoader'
            if len([d for d in self.my_team if isinstance(d.personal_strategy, StrategyDefender)]) < 2:
                drone.personal_strategy = 'Defender'
        # если нападают на базу
        elif drone.my_mothership.meter_2 < 0.9:
            if drone.my_mothership.cargo.payload > 1400 or drone.my_mothership.meter_2 < 0.5:
                if len([d for d in self.my_team if isinstance(d.personal_strategy, StrategyDefender)]) < 3:
                    drone.personal_strategy = 'Defender'
        # если кончился элериум на астероидах
        elif self.my_scene['sum_payload'] == 0:
            if not isinstance(self.strategy, StrategyDefender):
                self.strategy = 'Defender'
        else:

            if len(drone.scene.teams) > 2:
                self.strategy = 'FastLoader'
            else:
                self.strategy = 'Loader'
                # if self.my_scene['sum_payload'] > 0 and len([d for d in self.my_team if d.personal_strategy and
                #                                             isinstance(d.personal_strategy,StrategyFastLoader)]) < 1:
                #     drone.personal_strategy = 'FastLoader'

        if type(drone.personal_strategy) == type(self._strategy):
            drone.personal_strategy = None

        if drone.personal_strategy:
            drone.personal_strategy.do_step(drone)
        else:
            self._strategy.do_step(drone)

    def new_drone(self, drone):
        self.my_team.append(drone)
        self.get_step(drone)


class StrategyLoader(Strategy):

    def get_asteroid_surplus(self, asteroid, my_drone):
        return asteroid.cargo.payload - sum(
            [drone.free_space for drone in my_drone.context.my_team if drone.target == asteroid])

    def _get_my_asteroid(self, drone):
        """
        Функция возвращает цель астероид для загрузки elerium

        Составляет список целей из еще не выбрвнных другими дронами астероидов у которых  есть elerium
        вначале проверяет, первую цель по списку для полной загрузки, если таких нет,
        то  выбирает ближайшую к дрону цель из составленного списка
        :return: asteroid
        """

        targets = [a for a in drone.asteroids if (self.get_asteroid_surplus(a, drone) > 0 and
                                                  drone.distance_to(a) > 1)]
        targets.extend([d for d in drone.scene.drones if not d.is_empty and not d.is_alive])
        for team in drone.context.my_scene['enemy_teams']:
            if len(drone.context.my_scene['enemy_drones_defender'][team]) > 1:
                for target in targets:
                    if (
                            drone.context.my_scene['enemy_motherships'][team].distance_to(target) <=
                            MOTHERSHIP_HEALING_DISTANCE + drone.gun.shot_distance or
                            len([d for d in drone.scene.drones
                                 if d.is_empty and d.is_alive
                                    and d.distance_to(target) <= drone.gun.shot_distance
                                    and d.team != drone.team]) > 1
                    ):
                        targets.remove(target)

        targets.sort(key=lambda x: drone.distance_to(x), reverse=False)
        if targets and any(map(lambda t: len(drone.context.my_scene['enemy_drones_defender'][t]) > 1,
                               drone.context.my_scene['enemy_teams'])):
            return targets[0]
        for asteroid in targets:
            if self.get_asteroid_surplus(asteroid, drone) >= drone.free_space:
                return asteroid

        target = None

        return target

    def get_target(self, drone):
        if drone.free_space == 0:
            drone.target = drone.my_mothership
        else:
            sum_payload = sum([asteroid.cargo.payload for asteroid in drone.asteroids])
            sum_free_space = sum([d.free_space for d in drone.context.my_team
                                  if d.target in drone.asteroids])
            # если свободное место в дронах, у которых есть цель меньше суммы груза всех астероидов,
            # то выбираем цель иначе остаемся на базе
            if sum_payload > sum_free_space:
                drone.target = self._get_my_asteroid(drone)
            else:
                if not drone.is_empty:
                    drone.target = drone.my_mothership
                else:
                    drone.target = None
        return drone.target

    def do_step(self, drone):
        drone.limit_health = 0.9
        drone.heartbeat_do = False
        drone.turn_do = False
        if drone.actions:
            return
        target = self.get_target(drone)

        if not target:
            if drone.distance_to(drone.my_mothership) > MOTHERSHIP_HEALING_DISTANCE:
                target = drone.my_mothership
            else:
                return

        if target == drone.my_mothership:
            drone.actions.append(['move', target])
            if not drone.is_empty:
                drone.actions.append(['unload', target])
            next_target = self._get_my_asteroid(drone)
            if next_target and next_target != drone.my_mothership:
                drone.actions.append(['turn', next_target])
        else:
            if drone.distance_to(target) > 350:
                drone.actions.append(['move_step', target.coord])
                return
            else:
                if drone.distance_to(target) > 1:
                    drone.actions.append(['move', target])

            if drone.free_space >= target.cargo.payload:
                next_target = self._get_my_asteroid(drone)
                if next_target is None:
                    next_target = drone.my_mothership
            else:
                next_target = drone.my_mothership
            if not drone.is_full:
                drone.actions.append(['load', target])
                drone.actions.append(['turn', next_target])


class StrategyFastLoader(StrategyLoader):

    def _get_my_asteroid(self, drone):
        """
        Функция возвращает цель астероид для загрузки elerium

        Составляет список целей из еще не выбрвнных другими дронами астероидов у которых  есть elerium
        вначале проверяет, первую цель по списку для полной загрузки, если таких нет,
        то  выбирает ближайшую к дрону цель из составленного списка
        :return: asteroid
        """

        targets = [a for a in drone.asteroids if (self.get_asteroid_surplus(a, drone) > 0 and drone.distance_to(a) > 1)]
        targets.extend([d for d in drone.scene.drones if not d.is_empty and not d.is_alive])
        targets.sort(key=lambda x: drone.distance_to(x), reverse=False)

        for asteroid in targets:
            if self.get_asteroid_surplus(asteroid, drone) >= drone.free_space and not drone.alarm_near_target(asteroid):
                return asteroid

        for target in targets:
            if not drone.alarm_near_target(target):
                return target
        return None

    def devide_step_path(self, drone, target):
        if drone.distance_to(target) > 150:
            for angle_delta in range(12):
                vec = Vector.from_points(drone.coord, target.coord)
                vec = Vector.from_direction(vec.direction + randint(angle_delta * 5, angle_delta * 5),
                                            150)
                flag = True
                for d in drone.scene.drones:
                    if d.team != drone.team and drone.distance_to(d) < drone.gun.shot_distance:
                        vec2 = Vector.from_points(d.coord, target.coord)
                        if (
                                (abs(180 - abs(d.direction - vec.direction)) < 5 or
                                 (abs(d.direction - vec.direction) < 5 and abs(vec2.direction - vec.direction) < 5))
                        ):
                            flag = False
                if flag:
                    break
            else:
                vec = Vector.from_points(drone.coord, target.coord)
                vec = Vector.from_direction(vec.direction, 150)
                new_coord = Point(x=drone.coord.x + vec.x, y=drone.coord.y + vec.y)
                drone.actions.append(['move_step', new_coord])
                return
            new_coord = Point(x=drone.coord.x + vec.x, y=drone.coord.y + vec.y)
            drone.actions.append(['move_step', new_coord])
        else:
            if drone.distance_to(target) > 1:
                drone.actions.append(['move', target])



    def do_step(self, drone):
        drone.heartbeat_do = True
        drone.limit_health = 0.9
        if drone.prev_action == 'load':
            if not drone.flag_on_load_complete or drone._transition:
                return
            elif drone.loader_thief > 2:
                if drone.distance_to(drone.prev_target) < 10 or not drone.prev_target.is_alive:
                    drone.actions.append(['shot', drone.prev_target])
                    return
                else:
                    drone.loader_thief = 0
        elif drone.prev_action == 'unload':
            if not drone.flag_on_unload_complete:
                return
        elif drone.prev_action == 'move':
            if drone.prev_target and drone.distance_to(drone.prev_target) > CARGO_TRANSITION_DISTANCE:
                return
        if drone.actions:
            return

        if drone.distance_to(drone.my_mothership) < CARGO_TRANSITION_DISTANCE:
            if not drone.is_empty:
                drone.actions.append(['unload', drone.my_mothership])
                drone.flag_on_unload_complete = False
                next_target = self._get_my_asteroid(drone)
                if next_target and next_target != drone.my_mothership:
                    drone.actions.append(['turn', next_target])
            else:
                target = self.get_target(drone)
                if target:
                    drone.actions.append(['move', target])
            return


        elif drone.prev_target and drone.distance_to(drone.prev_target) < CARGO_TRANSITION_DISTANCE:
            if not drone.is_full:
                enemy_loader = drone.context.near_enemy(drone)
                if enemy_loader:
                    # if isinstance(drone.prev_target, Asteroid):
                    drone.actions.append(['load', enemy_loader])
                    drone.flag_on_load_complete = False
                    drone.loader_thief += 1
                    return
                if not drone.prev_target.cargo.is_empty:
                    drone.actions.append(['load', drone.prev_target])
                    drone.flag_on_load_complete = False
                    drone.loader_thief = 0
                    next_target = self._get_my_asteroid(drone)
                    if next_target and next_target != drone.my_mothership:
                        drone.actions.append(['turn', next_target])
                    return
                else:
                    target = self.get_target(drone)
                    if target:
                        drone.actions.append(['move', target])
                    else:
                        drone.actions.append(['move', drone.my_mothership])
            else:
                drone.actions.append(['move', drone.my_mothership])
        else:
            if not drone.is_full:
                target = self.get_target(drone)
                if target:
                    drone.actions.append(['move', target])
                else:
                    drone.actions.append(['move', drone.my_mothership])
            else:
                drone.actions.append(['move', drone.my_mothership])




    # def do_step1(self, drone):
    #
    #     if drone.heartbeat_do:
    #         if drone.prev_action == 'load':
    #             enemy_loader = drone.context.near_enemy(drone)
    #             if enemy_loader:
    #                 if isinstance(drone.prev_target, Asteroid):
    #                     drone.actions = []
    #                     drone.actions.append(['load', enemy_loader])
    #                 drone.loader_thief += 1
    #
    #
    #             if not drone.is_full and not drone.prev_target.cargo.is_empty and not drone.is_moving:
    #                 if drone.flag_on_load_complete:
    #                     if drone.loader_thief > 5:
    #                         drone.actions = []
    #                         drone.actions.append(['shot', enemy_loader])
    #                         drone.loader_thief = 0
    #                     else:
    #                         drone.actions = []
    #                         drone.actions.append(['load', drone.prev_target])
    #                     # return
    #                 # if drone._transition.is_finished:
    #                 #     if drone.loader_thief > 5:
    #                 #         drone.actions = []
    #                 #         drone.actions.append(['shot', enemy_loader])
    #                 #         drone.loader_thief = 0
    #                 #     else:
    #                 #         drone.actions = []
    #                 #         drone.actions.append(['load', drone.prev_target])
    #                 # return
    #         elif drone.distance_to(drone.my_mothership) < 15 and drone.prev_action == 'unload':
    #             if not drone.cargo.is_empty and drone.meter_2 < 1:
    #                 return
    #         # elif drone.prev_action == 'move' and drone.distance_to(drone.target) > 1:
    #         #     return


        # drone.heartbeat_do = True
        # drone.limit_health = 0.9
        # if drone.actions:
        #     return
        # target = self.get_target(drone)
        #
        # if not target:
        #     if drone.distance_to(drone.my_mothership) > 1:
        #         target = drone.my_mothership
        #     else:
        #         return
        #
        # if target == drone.my_mothership:
        #     drone.actions.append(['move', target])
        #     next_target = self._get_my_asteroid(drone)
        #     # if next_target and next_target != drone.my_mothership:
        #     #     drone.actions.append(['turn', next_target])
        #
        #     if not drone.is_empty:
        #         drone.actions.append(['unload', target])
        #         #drone.heartbeat_do = False
        #     next_target = self._get_my_asteroid(drone)
        #     if next_target and next_target != drone.my_mothership:
        #         drone.actions.append(['turn', next_target])
        #         drone.turn_do = False
        # else:
        #
        #     drone.heartbeat_do = True
        #     drone.actions.append(['move', target])
        #     if not drone.is_full:
        #         drone.actions.append(['load', target])
        #         drone.loader_thief = 0
        #     if drone.free_space >= target.cargo.payload:
        #         next_target = self._get_my_asteroid(drone)
        #         if next_target is None:
        #             next_target = drone.my_mothership
        #     else:
        #         next_target = drone.my_mothership
        #     drone.actions.append(['turn', next_target])
        #     drone.turn_do = False


class StrategyMarauder(StrategyFastLoader):

    def get_target(self, drone):
        """
        меняем  цель  на уничтоженные базы
        :return: asteroid
        """
        if drone.free_space == 0:
            drone.target = drone.my_mothership
        else:
            enemy_motherships = [mothership for mothership in drone.scene.motherships if not mothership.is_alive
                                 and not mothership.is_empty]
            for mothership in enemy_motherships:
                count_alive_drone = len([d for d in drone.scene.drones if mothership.team == d.team and d.is_alive])
                if count_alive_drone <= 1:
                    drone.target = mothership
                    return drone.target
            drone.target = None
        return drone.target


class StrategyDefender(Strategy):
    def __init__(self, mothership_point):
        index_mothership_x = int(mothership_point.x // (theme.FIELD_WIDTH / 2))
        index_mothership_y = int(mothership_point.y // (theme.FIELD_HEIGHT / 2))
        global_angles = [[[0, 90, 30, 60], [0, 270, 300, 330]], [[180, 90, 120, 150], [180, 270, 210, 240]]]
        self.angles = global_angles[index_mothership_x][index_mothership_y]

    def get_place_near_mothership(self, drone, exclude_angle=-1):
        def get_position_of_angle():
            position = Point(drone.my_mothership.coord.x + MOTHERSHIP_HEALING_DISTANCE - 1,
                             drone.my_mothership.coord.y)
            vec = Vector.from_points(drone.my_mothership.coord, position)
            if drone.angle >= 0:
                vec.rotate(drone.angle)
            position = Point(drone.my_mothership.coord.x + vec.x, drone.my_mothership.coord.y + vec.y)
            return position

        if (
                drone.angle >= 0 and
                50 < drone.distance_to(drone.my_mothership) <= MOTHERSHIP_HEALING_DISTANCE
                and exclude_angle == -1
        ):
            if drone.angle == -1 and drone.distance_to(drone.my_mothership) > 1:
                return drone.my_mothership.coord
            position = get_position_of_angle()
            if drone.distance_to(position) > 1:
                return position
            else:
                return None

        for angle in self.angles:
            is_valide = True
            for partner in drone.context.my_team:
                if not partner.is_alive or partner is drone:
                    continue
                is_valide = is_valide and (partner.angle != angle) and (angle != exclude_angle)
            if is_valide:
                drone.angle = angle
                return get_position_of_angle()
        return None

    def get_enemy_target(self, my_drone):
        enemies = [(drone, my_drone.distance_to(drone)) for drone in my_drone.scene.drones if
                   (my_drone.team != drone.team and
                    drone is not my_drone.my_mothership and drone.is_alive and not drone.is_moving)]

        enemies.sort(key=lambda x: x[1])
        for enemy_target in enemies:
            if enemy_target[1] <= my_drone.gun.shot_distance + 100 and my_drone.valide_place(enemy_target[0].coord):
                return enemy_target[0]
        else:
            return None

    def do_step(self, drone):
        drone.limit_health = 0.5
        drone.heartbeat_do = False
        drone.turn_do = False
        if drone.actions:
            return
        if not drone.is_empty:
            drone.actions.append(['move', drone.my_mothership])
            drone.actions.append(['unload', drone.my_mothership])
            return
        point_attack = self.get_place_near_mothership(drone)
        if point_attack:
            drone.actions.append(['move', point_attack])
        else:
            if drone.distance_to(drone.my_mothership) > MOTHERSHIP_HEALING_DISTANCE:
                drone.actions.append(['move', drone.my_mothership])
        drone.target = self.get_enemy_target(drone)
        if drone.target:
            drone.actions.append(['turn', drone.target])
            drone.actions.append(['shot', drone.target])
        else:
            if drone.context.my_scene['count_dead_my_team'] > 1:
                point_attack = self.get_place_near_mothership(drone, drone.angle)
                if point_attack:
                    drone.actions.append(['move', point_attack])


class ZakharovDrone(Drone):
    context = None
    total_distance_full = 0
    total_distance_empty = 0
    total_distance = 0
    limit_health = 0.5
    angle = -1

    @property
    def personal_strategy(self) -> Strategy:
        return self._personal_strategy

    @personal_strategy.setter
    def personal_strategy(self, strategy):
        if not strategy:
            self._personal_strategy = None
            return
        if self.personal_strategy and type(self.personal_strategy) == type(self.context.strategies[strategy]):
            return
        self._personal_strategy = self.context.strategies[strategy]
        self.actions = []
        self.angle = -1

    def registry_context(self):
        if ZakharovDrone.context is None:
            ZakharovDrone.context = ZakharovContext('FastLoader', self.my_mothership)
        ZakharovDrone.context.new_drone(drone=self)

    def on_born(self):
        self._personal_strategy = None
        self.actions = []
        self.heartbeat_do = False
        self.turn_do = False
        self.flag_on_load_complete = False
        self.prev_action = ''
        self.prev_target = None
        self.registry_context()
        ZakharovDrone.context.get_step(self)
        # self.do_action()

    def do_action(self):
        if (self.meter_2 < self.limit_health and self.distance_to(self.my_mothership) > MOTHERSHIP_HEALING_DISTANCE
                and self.check_count_drone_attack() > 1):
            if not self.actions or self.actions[0] != 'unload':
                self.actions = []
                self.prev_action = ''
                self.prev_target = None
                #self.heartbeat_do = False
                self.turn_do = False
                self.actions.append(['move', self.my_mothership])
                if not self.is_empty:
                    self.actions.append(['unload', self.my_mothership])

        i = 0
        while not self.actions:
            ZakharovDrone.context.get_step(self)
            i += 1
            if i > 1:
                return

        action, target = self.actions[0]

        if action == 'move':
            self.move_at(target)
            self.actions.pop(0)
            self.prev_action = 'move'
            self.prev_target = target

        elif action == 'move_step':
            if self.heartbeat_do:
                if self.prev_action == 'unload':
                    if self.is_empty and self.meter_2 == 1:
                        self.move_to_step(target)
                        self.actions.pop(0)
                        self.prev_action = 'move'
                elif self.prev_action == 'load':
                    if self.flag_on_load_complete:
                        self.move_to_step(target)
                        self.actions.pop(0)
                        self.prev_action = 'move'
                else:
                    self.move_to_step(target)
                    self.actions.pop(0)
                    self.prev_action = 'move'
            else:
                self.move_to_step(target)
                self.actions.pop(0)
                self.prev_action = 'move'

        elif action == 'load':

            self.load_from(target)
            self.prev_action = 'load'
            self.prev_target = target
            self.actions.pop(0)

        elif action == 'unload':

            self.unload_to(target)
            self.actions.pop(0)
            self.prev_action = 'unload'
            self.do_action()

        elif action == 'turn':

            if not self.is_moving:
                self.turn_to(target)
                self.actions.pop(0)
                # self.prev_action = 'turn'
        elif action == "shot":
            # if not self.heartbeat_do:
            self.shot(target)
            self.actions.pop(0)
        else:
            self.actions.pop(0)
            self.do_action()

    def move_at(self, target, speed=None):
        distance = self.distance_to(target)
        if not isinstance(target, Point):
            vec = Vector.from_points(self.coord, target.coord, distance - CARGO_TRANSITION_DISTANCE +1)
            new_coord = Point(x=self.coord.x + vec.x, y=self.coord.y + vec.y)
        else:
            new_coord = target
        ZakharovDrone.total_distance += distance
        if self.is_empty:
            ZakharovDrone.total_distance_empty += distance
        if self.is_full:
            ZakharovDrone.total_distance_full += distance
        super().move_at(new_coord, speed)

    def move_to_step(self, coord):
        distance = min(350, self.distance_to(coord))
        vec = Vector.from_points(self.coord, coord, distance)
        new_coord = Point(x=self.coord.x + vec.x, y=self.coord.y + vec.y)
        self.move_at(new_coord)

    def check_count_drone_attack(self):
        result = 0
        for d in self.scene.drones:
            if d.team != self.team and d.is_alive and self.distance_to(d) < self.gun.shot_distance + 50:
                vec2 = Vector.from_points(d.coord, self.coord)
                if abs(d.direction - vec2.direction) < 5:
                    result += 1
        return result

    def alarm_near_target(self, target):

        # для всех чужих команд проверяем число защитников
        for team in self.context.my_scene['enemy_teams']:
            count_enemy_defender = len(self.context.my_scene['enemy_drones_defender'][team])
            if count_enemy_defender > 1:
                if len(self.scene.teams) > 2:
                    safe_length = self.gun.shot_distance / 2
                else:
                    safe_length = self.gun.shot_distance

                if self.context.my_scene['enemy_motherships'][team].distance_to(target) <= safe_length:
                    return True

            if count_enemy_defender > 3:
                if (self.context.my_scene['enemy_motherships'][team].distance_to(target) <=
                        self.gun.shot_distance + MOTHERSHIP_HEALING_DISTANCE + 10):
                    return True

        if sum(map(lambda t: len(self.context.my_scene['enemy_drones_my_mothership'][t]),
                   self.context.my_scene['enemy_teams'])) > 1:
            if any([[d.distance_to(target) <= self.gun.shot_distance for d in
                     self.context.my_scene['enemy_drones'][t] if
                     d.is_alive and d.is_empty and not d.is_moving]
                    for t in self.context.my_scene['enemy_teams']]):
                return True
        return False

    def verify_angle(self, partner: GameObject, target: Point):
        """
        возвращает истину, если partner перекрывает цель
        """
        v_from_self_to_target = Vector(target.x - self.coord.x, target.y - self.coord.y)
        v_from_self_to_partner = Vector(partner.coord.x - self.coord.x, partner.coord.y - self.coord.y)
        if v_from_self_to_target.module > v_from_self_to_partner.module and v_from_self_to_partner.module > 0:
            angle_partner = math.atan(70 / v_from_self_to_partner.module) * (180 / math.pi)
            return abs(v_from_self_to_target.direction - v_from_self_to_partner.direction) < angle_partner
        else:
            return False

    def valide_place(self, target: Point):
        for partner in self.context.my_team:
            if not partner.is_alive or partner is self:
                continue
            if (partner.distance_to(target) < 26) or (self.verify_angle(partner, target)):
                return False
        return True

    def shot(self, target):

        if not self.have_gun:
            return
        if self.valide_place(self.target.coord):
            self.gun.shot(target)

    def on_stop_at_asteroid(self, asteroid):
        self.flag_on_stop_asteroid = True
        self.do_action()

    def on_load_complete(self):
        self.flag_on_load_complete = True
        self.do_action()

    def on_stop_at_mothership(self, mothership):
        self.do_action()

    def on_unload_complete(self):
        self.flag_on_unload_complete = True
        self.do_action()

    def on_wake_up(self):
        self.do_action()

    def on_collide_with(self, obj_status):
        self.do_action()

    def on_heartbeat(self):
        if self.heartbeat_do:
            self.do_action()


drone_class = ZakharovDrone

