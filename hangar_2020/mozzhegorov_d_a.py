from __future__ import annotations

import math
from abc import ABC, abstractmethod
from math import sin, cos, radians

from astrobox.core import Drone
from robogame_engine.geometry import Point
import collections
from robogame_engine.theme import theme

DEFENCE_CONFIG = {
    'defender': 4,
    'collector': 1,
}
DESTROY_CONFIG = {
    'defender': 2,
    'destroyer': 1,
}
ELLERIUM_FOR_COST = 10000
MAX_HEALTH = 100
DIST_TO_WALLS = 185
ATTACKER_PARAMS = [(0, 0),  # (dist, angle)
                   (73, -75),
                   (73, 75),
                   (146, -85),
                   (146, 85), ]
ATTACKER_PARAMS_NEW = [(0, 0),  # (dist, angle)
                       (90, 90),
                       (90, -90),
                       (180, 90),
                       (180, -90), ]
MD_PARAMS = [(0, 0),  # (dist, angle)
             (80, 90),
             (80, -90),
             (80, 90),
             (0, 0), ]
ATTACKER_PARAMS_WIDE = [(0, 0),  # (dist, angle)
                        (90.6, 86),
                        (90.6, -86),
                        (180.9, 82),
                        (180.9, -82), ]
DEFENDER_PARAMS = [(0, 0),  # (dist, angle)
                   (95.1, -103.75),
                   (95.1, 103.75),
                   (184.7, -117.5),
                   (184.7, 117.5), ]
POINTER_FOR_DEFENDERS = Point(710, 710)
COLLECTORS_WITHOUT_ENEMIES = 1
STALKERS = 1
FF_DIST = 57
HEALTH_LIMIT = 0.8
DISTATION_FOR_NEW_HEAD_DRONE_PLACE = 562
SAFE_DISTATION_FOR_DEFEND = 290
MODULE_FOR_STRAIGHT_MOVE = 2
DEFENCE = 0
ATTACK = 1
MOTHERSHIPDESTROY = 2
CLEANER = 3


class MozzhegorovDrone(Drone):
    my_team_roles = collections.defaultdict(int)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.quarter_of_my_mothership = 0
        self._strategy = None
        self.actions = []
        self.angle_to_defence = None
        self.center_field = Point(theme.FIELD_WIDTH // 2, theme.FIELD_HEIGHT // 2)
        self.offset = 0
        self.place = None

    @property
    def strategy(self):
        return self._strategy

    @strategy.setter
    def strategy(self, strategy) -> None:
        self._strategy = strategy(self)

    def get_new_action(self) -> None:
        self._strategy.next_action()

    def get_first_role(self):
        strategies = {
            'defender': Defender,
            'collector': Collector,
            'attacker': Attacker,
        }
        for name, strategy_class in strategies.items():
            if MozzhegorovDrone.my_team_roles[name] < DEFENCE_CONFIG[name] and self.have_gun:
                self.strategy = strategy_class
                MozzhegorovDrone.my_team_roles[name] += 1
                break
            else:
                self.strategy = strategies['collector']

    def operating(self):
        if self.health < MAX_HEALTH * HEALTH_LIMIT and not self.near(self.my_mothership):
            self.moving(self.my_mothership)
            return
        if not bool(self.actions):
            self._strategy.next_action()
        if bool(self.actions):
            action, parametr = self.actions[0]
            handler = getattr(self, action)
            handler(parametr)
            self.actions.pop(0)
        self._strategy.change_strategy()

    # actions
    def moving(self, target):
        if target is not None:
            self.target = target
            super().move_at(target, speed=None)

    def shooting(self, target):
        self.turn_to(target)
        self.gun.shot(target)

    def turning(self, obj):
        self.turn_to(obj)

    def loading(self, _):
        if self.free_space < self.target.payload:
            target_to_turn = self.my_mothership
        else:
            target_to_turn = self._strategy.get_new_target(self._strategy.is_ast_free)
        if target_to_turn:
            self.turning(obj=target_to_turn)
        self.load_from(self.target)

    def unloading(self, obj):
        if obj:
            self.turning(obj=obj)
        self.unload_to(self.my_mothership)

    def moving_straight(self, _):
        angle = radians(self.vector.direction)
        x = self.coord.x + MODULE_FOR_STRAIGHT_MOVE * cos(angle)
        y = self.coord.y + MODULE_FOR_STRAIGHT_MOVE * sin(angle)
        super().move_at(Point(x, y), speed=None)

    # callbacks
    def on_born(self):
        self.get_first_role()
        angle_center_to_my_ms = self.vector.from_points(self.center_field, self.my_mothership.coord).direction
        self.quarter_of_my_mothership = int(angle_center_to_my_ms // 90)

    def on_stop_at_asteroid(self, asteroid):
        self.operating()

    def on_load_complete(self):
        self.operating()

    def on_stop_at_mothership(self, mothership):
        self.operating()

    def on_unload_complete(self):
        self.operating()

    def on_wake_up(self):
        self.operating()


class Strategy(ABC):
    head_drone = {
        'coord': Point(0, 0),
        'target': None,
        'pointer': None,
        'enemy_near_base_cnt': 0,
        'crew_tactic': DEFENCE,
    }

    def __init__(self, drone):
        self.drone = drone

    @abstractmethod
    def next_action(self):
        pass

    def change_strategy(self):
        team = self.drone.teammates
        team.append(self.drone)
        teammates = self.drone.teammates
        defenders = [teammate for teammate in team if isinstance(teammate.strategy, Defender)]
        destroyers = [teammate for teammate in team if isinstance(teammate.strategy, MothershipsDestroyer)]
        collectors = [teammate for teammate in team if isinstance(teammate.strategy, Collector)]
        enemies = self.enemies_sorted_dist_to_my_ms()
        ast_to_loot = self.get_new_target(self.is_ast_free)
        if not bool(enemies):
            Strategy.head_drone['crew_tactic'] = CLEANER

        if self.drone.scene._step > 16000 and \
                not isinstance(self.drone.strategy, Collector)\
                and len(defenders) > 1:
            self.drone.strategy = Collector
            return

        if Strategy.head_drone['crew_tactic'] is DEFENCE:

            if self.get_new_target(self.is_ast_needed_drone) is None and \
                    not isinstance(self.drone.strategy, Defender) and \
                    (self.drone.is_empty and self.drone.near(self.drone.my_mothership)):
                self.drone.strategy = Defender

        if not bool(enemies) and (len(collectors) < COLLECTORS_WITHOUT_ENEMIES or
                                  not bool(self.motherships_alive_with_ellerium())):
            self.drone.strategy = Collector
            return

        if Strategy.head_drone['crew_tactic'] in (ATTACK, DEFENCE):
            if (len(enemies) < 15 or not bool(enemies)) and not isinstance(self.drone.strategy, Attacker):
                Strategy.head_drone['crew_tactic'] = ATTACK
                self.drone.strategy = Attacker
                self.drone.actions.append(('moving', self.drone.my_mothership))
                return

        if Strategy.head_drone['crew_tactic'] is MOTHERSHIPDESTROY:
            offsets_in_crew = [teammate.offset for teammate in teammates if not isinstance(teammate.strategy, Defender)]
            ms_alive_with_ellerium = self.motherships_alive_with_ellerium()
            ms_dead_with_ellerium = self.motherships_dead_with_ellerium()

            # To Collector
            can_change_strategy_to_collector = (len(defenders) >= DESTROY_CONFIG['defender'] and
                                                len(destroyers) >= DESTROY_CONFIG['destroyer'] and
                                                not isinstance(self.drone.strategy, Defender) and
                                                not isinstance(self.drone.strategy, Collector))

            if (bool(ms_dead_with_ellerium) or bool(ast_to_loot)) and can_change_strategy_to_collector:
                self.drone.strategy = Collector

            # To Destroyer
            can_destroy_ms = ((not bool(ms_dead_with_ellerium) or len(enemies) > 1) and
                              bool(ms_alive_with_ellerium) and
                              bool(self.enemies_sorted_dist_to_my_ms()))

            can_change_strategy_to_destroyer = (not isinstance(self.drone.strategy, MothershipsDestroyer) and
                                                not isinstance(self.drone.strategy, Defender) and
                                                self.drone.is_empty and
                                                len(defenders) >= DESTROY_CONFIG['defender'])

            if can_destroy_ms and can_change_strategy_to_destroyer:
                self.drone.strategy = MothershipsDestroyer

            # To Defender
            can_change_strategy_to_defender = ((bool(offsets_in_crew) and self.drone.offset < min(offsets_in_crew)) and
                                               not isinstance(self.drone.strategy, Defender) and
                                               len(defenders) < DESTROY_CONFIG['defender'])

            if bool(enemies) and can_change_strategy_to_defender:
                self.drone.strategy = Defender
                self.drone.actions.append(('moving', self.drone.my_mothership))

        if Strategy.head_drone['crew_tactic'] is CLEANER:
            if not bool(collectors) \
                    and not isinstance(self.drone.strategy, Collector):
                self.drone.strategy = Collector
                return

            if bool(collectors) \
                    and not isinstance(self.drone.strategy, Attacker) \
                    and not isinstance(self.drone.strategy, Collector):
                self.drone.strategy = Attacker
                return

    # general
    def enemies_sorted_dist_to_my_ms(self):
        enemies = [(drone, drone.distance_to(self.drone.my_mothership)) for drone in self.drone.scene.drones
                   if self.drone.team != drone.team and drone.is_alive]
        enemies.sort(key=lambda x: x[1])
        enemies = dict(enemies)
        return list(enemies.keys())

    def motherships_alive_with_ellerium(self):
        return [ms for ms in
                self.get_other_sorted_motherships_with_filtr()
                if ms.is_alive
                and not self.mothership_has_alive_drones(ms)
                and not ms.is_empty
                and self.drone.my_mothership != ms]

    def motherships_dead_with_ellerium(self):
        return [ms for ms in
                self.get_other_sorted_motherships_with_filtr()
                if not ms.is_alive
                and not self.mothership_has_alive_drones(ms)
                and not ms.is_empty
                and self.drone.my_mothership != ms]

    # Collector
    def is_ast_free(self, ast):
        return not any([ast == teammate.target for teammate in self.drone.teammates])

    def is_ast_needed_drone(self, asteroid):
        sum_free_space = 0
        for teammate in self.drone.teammates:
            if teammate.target == asteroid:
                sum_free_space += teammate.free_space
        if sum_free_space > asteroid.payload:
            return False
        return True

    def get_sorted_list_of_asteroids(self):
        ast_with_distance = {}
        for ast in self.drone.asteroids:
            distance = self.drone.distance_to(ast)
            if distance > 1:
                ast_with_distance[distance] = ast
        sorted_by_dist = sorted(ast_with_distance)
        sorted_list = [ast_with_distance[k] for k in sorted_by_dist]
        return sorted_list

    def is_needed_target(self):
        target = None
        all_ellerium = sum([ast.payload for ast in self.drone.asteroids])
        if self.teammates_busy_freespace() < all_ellerium:
            target = self.get_new_target(self.is_ast_needed_drone)
        return target

    def teammates_busy_freespace(self):
        return sum([teammate.free_space
                    for teammate in self.drone.teammates
                    if teammate.target and teammate.target != self.drone.my_mothership])

    def teammates_empty(self):
        return all([teammate.is_empty for teammate in self.drone.teammates])

    def get_new_target(self, ast_filter_type):

        motherships_dead_with_ellerium = [mothership for mothership in self.drone.scene.motherships
                                          if not mothership.is_alive
                                          and not mothership.is_empty
                                          and self.drone.my_mothership != mothership]
        if bool(motherships_dead_with_ellerium):
            for ms in motherships_dead_with_ellerium:
                if ast_filter_type(ms):
                    return ms

        enemies = self.enemies_sorted_dist_to_my_ms()
        for ast in self.get_sorted_list_of_asteroids():
            ast_in_safe_dist = min([enemy.distance_to(ast) for enemy in self.enemies_sorted_dist_to_my_ms()]) > 650 \
                               or self.drone.my_mothership.distance_to(ast) < 250
            if ast.payload \
                    and ast_filter_type(ast) \
                    and (not bool(enemies) or ast_in_safe_dist):
                return ast

        dead_drone = self.get_dead_drone_with_ellerium(self.is_ast_needed_drone)
        if bool(dead_drone):
            return dead_drone

    def get_dead_drone_with_ellerium(self, ast_filter_type):
        enemies = self.enemies_sorted_dist_to_my_ms()
        dead_with_ellerium = [drone for drone in self.drone.scene.drones
                              if drone.payload
                              and not drone.is_alive
                              and (not bool(enemies) or min([enemy.distance_to(drone) for enemy in enemies]) > 650)]
        for drone in dead_with_ellerium:
            if ast_filter_type(drone):
                return drone

    # Attacker + Defender
    def is_friendly_fire(self, aim):
        angle_to_aim = self.drone.vector.from_points(self.drone.coord, aim).direction
        for teammate in self.drone.teammates:
            angle_to_teammate = teammate.vector.from_points(self.drone.coord, teammate.coord).direction
            delta_angle = math.fabs(angle_to_aim - angle_to_teammate)
            dist_to_teammate = teammate.distance_to(self.drone) * sin(math.radians(delta_angle))
            if teammate.is_alive \
                    and delta_angle < 90 \
                    and math.fabs(dist_to_teammate) < FF_DIST:
                return True
        return False

    def enemy_near_base(self, _team):
        enemies = self.enemies_sorted_dist_to_my_ms()
        mothership_for_id = [ms for ms in self.get_other_sorted_motherships_with_filtr()
                             if ms.team == _team][0]
        for enemy in enemies:
            if enemy.team == _team and not enemy.distance_to(mothership_for_id) < 250 and enemy.is_alive:
                return False
        return True

    def get_other_sorted_motherships_with_filtr(self, extra_filtr=None):
        motherships = [(ms, self.drone.distance_to(ms)) for ms in
                       self.drone.scene.motherships
                       if self.drone.my_mothership != ms
                       and (extra_filtr is None or extra_filtr(ms))
                       and ms is not None]
        if bool(motherships):
            motherships.sort(key=lambda x: x[1])
            motherships = dict(motherships)
            return list(motherships.keys())
        else:
            return None

    def get_other_sorted_payload_motherships_with_filtr(self):
        motherships = [(ms, ms.payload) for ms in
                       self.drone.scene.motherships
                       if self.drone.my_mothership != ms
                       and ms.is_alive
                       and not self.mothership_has_alive_drones(ms)
                       and ms is not None]
        if bool(motherships):
            motherships.sort(key=lambda x: x[1], reverse=True)
            motherships = dict(motherships)
            return list(motherships.keys())
        else:
            return None

    def mothership_has_alive_drones(self, mothership):
        for enemy in self.enemies_sorted_dist_to_my_ms():
            if mothership.team == enemy.team and enemy.is_alive:
                return True
        return False

    @staticmethod
    def check_coord_near_walls(coord, scope, dist_to_walls):
        if coord < dist_to_walls:
            return dist_to_walls
        elif coord > (scope - dist_to_walls):
            return scope - dist_to_walls
        else:
            return coord

    def get_place_for_attack(self, target, params_for_crew=None, dist_to_target=500, dist_to_walls=None):
        if params_for_crew is None:
            params_for_crew = ATTACKER_PARAMS

        for offset in range(5):
            if offset not in [teammate.offset for teammate in self.drone.teammates
                              if teammate.offset is not None and teammate.is_alive]:
                self.drone.offset = offset
                break
        angle_my_mothership_target = self.drone.vector.from_points(self.drone.my_mothership.coord, target).direction
        dist_in_crew, angle_in_crew = params_for_crew[self.drone.offset]
        head_drone_x, head_drone_y = Strategy.head_drone['coord'].x, Strategy.head_drone['coord'].y
        if ((head_drone_x, head_drone_y) == (0, 0)
                or self.drone.distance_to(target) > DISTATION_FOR_NEW_HEAD_DRONE_PLACE):
            angle = radians(angle_my_mothership_target)
            x = self.drone.my_mothership.coord.x + \
                (self.drone.my_mothership.distance_to(target) - dist_to_target) * cos(angle)
            y = self.drone.my_mothership.coord.y + \
                (self.drone.my_mothership.distance_to(target) - dist_to_target) * sin(angle)

            Strategy.head_drone['coord'] = Point(self.check_coord_near_walls(x, theme.FIELD_WIDTH, dist_to_walls),
                                                 self.check_coord_near_walls(y, theme.FIELD_HEIGHT, dist_to_walls))
        else:
            x = 0
            y = 0

        if angle_in_crew != 0:
            angle_offset = radians(angle_my_mothership_target + angle_in_crew)
            x = Strategy.head_drone['coord'].x + dist_in_crew * cos(angle_offset)
            y = Strategy.head_drone['coord'].y + dist_in_crew * sin(angle_offset)

        if self.drone.offset == 0:
            return Strategy.head_drone['coord']
        else:
            return Point(x, y)

    def get_target_for_shot(self, team=None):
        list_of_targets = self.enemies_sorted_dist_to_my_ms()
        list_of_motherships = [ms for ms in self.get_other_sorted_motherships_with_filtr() if ms.is_alive]
        if bool(list_of_motherships):
            list_of_targets.extend(list_of_motherships)

        for enemy in list_of_targets:
            if (self.is_friendly_fire(enemy.coord) or self.drone.distance_to(enemy) > 650
                    or (team is not None and enemy.team != team)):
                if self.drone.offset == 0 and isinstance(self.drone.strategy, Attacker):
                    continue
            else:
                return enemy


class Collector(Strategy):

    def next_action(self):
        all_ellerium = sum([ast.payload for ast in self.drone.asteroids]) + \
                       sum([drone.payload for drone in self.drone.scene.drones if
                            drone.payload and not drone.is_alive]) + \
                       sum([mothership.payload for mothership in self.get_other_sorted_motherships_with_filtr()])
        if all_ellerium == 0:
            self.drone.actions.append(('moving', self.drone.my_mothership))
            return

        if self.drone.near(self.drone.my_mothership):
            if not self.drone.is_empty:
                place = self.get_new_target(self.is_ast_needed_drone)
                self.drone.actions.append(('unloading', place))
            else:
                place = self.get_new_target(self.is_ast_free)
                self.drone.actions.append(('moving', place))
        else:
            if isinstance(self.drone.target, Point):
                place = self.get_new_target(self.is_ast_free)
                self.drone.actions.append(('moving', place))
                return
            if not self.drone.is_full and not self.drone.target.is_empty:
                self.drone.actions.append(('loading', self.drone.target))
            elif self.drone.target.is_empty and Strategy.head_drone['enemy_near_base_cnt'] < 50:
                place = self.get_new_target(self.is_ast_needed_drone)
                if place is None:
                    self.drone.actions.append(('moving', self.drone.my_mothership))
                self.drone.actions.append(('moving', place))
            else:
                self.drone.actions.append(('moving', self.drone.my_mothership))


class Attacker(Strategy):

    def __init__(self, drone):
        super().__init__(drone)
        self.opposite_enemy = False
        self.straight_steps = 0
        self.attack_mothership_id = 0

    def is_crew_in_friendly_fire(self, target):
        for teammate in self.drone.teammates:
            if isinstance(teammate.strategy, Attacker) and self.is_friendly_fire(target):
                return False
        return True

    def next_action(self):
        enemies = self.enemies_sorted_dist_to_my_ms()

        if (len(enemies) > 1 and Strategy.head_drone['enemy_near_base_cnt'] > 150) or \
                Strategy.head_drone['enemy_near_base_cnt'] > 250:
            Strategy.head_drone['crew_tactic'] = MOTHERSHIPDESTROY
            Strategy.head_drone['coord'] = Point(0, 0)
            return

        pointer = self.get_other_sorted_motherships_with_filtr(self.mothership_has_alive_drones)
        if pointer is None and bool(self.motherships_alive_with_ellerium()):
            pointer = self.motherships_alive_with_ellerium()[0]
        elif bool(pointer):
            pointer = pointer[0]
        elif bool(enemies):
            pointer = enemies[0]
        else:
            self.drone.actions.append(('moving', self.drone.my_mothership))
            return

        angle_center_to_enemy_ms = self.drone.vector.from_points(self.drone.center_field, pointer.coord).direction
        quarter_to_mothership_enemy = int(angle_center_to_enemy_ms // 90)
        self.opposite_enemy = math.fabs(self.drone.quarter_of_my_mothership - quarter_to_mothership_enemy) > 1

        if bool(enemies) and self.enemy_near_base(pointer.team):
            Strategy.head_drone['enemy_near_base_cnt'] += 1
        else:
            Strategy.head_drone['enemy_near_base_cnt'] = 0

        if not bool(enemies):
            self.drone.place = self.get_place_for_attack(pointer.coord, ATTACKER_PARAMS_NEW, 400, dist_to_walls=250)
        elif self.opposite_enemy:
            pointer = enemies[0]
            self.drone.place = self.get_place_for_attack(pointer.coord, ATTACKER_PARAMS_WIDE, 642, dist_to_walls=225)
        else:
            pointer = enemies[0]
            self.drone.place = self.get_place_for_attack(pointer.coord, ATTACKER_PARAMS, 642, dist_to_walls=185)

        if self.drone.near(self.drone.my_mothership):
            self.drone.actions.append(('moving', self.drone.place))
            return

        Strategy.head_drone['target'] = self.get_target_for_shot(pointer.team)

        if Strategy.head_drone['target'] is not None and \
                not self.is_friendly_fire(Strategy.head_drone['target'].coord) and \
                not self.drone.distance_to(Strategy.head_drone['target']) > 637:
            self.drone.actions.append(('shooting', Strategy.head_drone['target']))
        else:
            self.drone.actions.append(('turning', pointer))
            self.drone.actions.append(('moving_straight', None))
            self.straight_steps += 1

        if self.straight_steps > 25:
            self.straight_steps = 0
            self.drone.actions.append(('moving', self.drone.my_mothership))


class Defender(Strategy):

    def get_place_for_defend(self):
        defend_coord = [
            (theme.FIELD_WIDTH - SAFE_DISTATION_FOR_DEFEND, theme.FIELD_HEIGHT - SAFE_DISTATION_FOR_DEFEND),
            (SAFE_DISTATION_FOR_DEFEND, theme.FIELD_HEIGHT - SAFE_DISTATION_FOR_DEFEND),
            (SAFE_DISTATION_FOR_DEFEND, SAFE_DISTATION_FOR_DEFEND),
            (theme.FIELD_WIDTH - SAFE_DISTATION_FOR_DEFEND, SAFE_DISTATION_FOR_DEFEND),
        ]
        return Point(*defend_coord[self.drone.quarter_of_my_mothership])

    def next_action(self):
        pointer = self.get_place_for_defend()
        place = self.get_place_for_attack(pointer, DEFENDER_PARAMS, 83, dist_to_walls=185)
        target = self.get_target_for_shot()

        if self.drone.near(place):
            if bool(target):
                self.drone.actions.append(('shooting', target))
        else:
            self.drone.actions.append(('moving', place))


class MothershipsDestroyer(Strategy):

    def get_place_for_destroyer(self, target, params_for_crew, dist_to_target, dist_to_walls):
        angle_my_mothership_target = self.drone.vector.from_points(self.drone.my_mothership.coord, target).direction
        dist_in_crew, angle_in_crew = params_for_crew[self.drone.offset]
        angle = radians(angle_my_mothership_target)
        angle_offset = radians(angle_my_mothership_target + angle_in_crew)
        x = self.drone.my_mothership.coord.x + \
            (self.drone.my_mothership.distance_to(target) - dist_to_target) * cos(angle)
        y = self.drone.my_mothership.coord.y + \
            (self.drone.my_mothership.distance_to(target) - dist_to_target) * sin(angle)

        x = self.check_coord_near_walls(x, theme.FIELD_WIDTH, dist_to_walls) + dist_in_crew * cos(angle_offset)
        y = self.check_coord_near_walls(y, theme.FIELD_HEIGHT, dist_to_walls) + dist_in_crew * sin(angle_offset)

        return Point(x, y)

    def next_action(self):
        if bool(self.get_other_sorted_payload_motherships_with_filtr()):
            pointer = self.get_other_sorted_payload_motherships_with_filtr()[0]
        else:
            self.drone.actions.append(('moving', self.drone.my_mothership))
            return

        for distation in range(601, 300, -50):
            self.drone.place = self.get_place_for_destroyer(pointer.coord, MD_PARAMS, distation, 120)
            if min([enemy.distance_to(self.drone.place) for enemy in self.enemies_sorted_dist_to_my_ms()]) > 640:
                break

        if self.drone.near(self.drone.place):
            if bool(pointer):
                self.drone.actions.append(('shooting', pointer))
        else:
            self.drone.actions.append(('moving', self.drone.place))


drone_class = MozzhegorovDrone
