import math
from collections import defaultdict
from functools import reduce
from typing import List
from abc import ABCMeta, ABC
from abc import abstractmethod

from robogame_engine.geometry import Vector, Point
from astrobox.core import theme, Asteroid, Drone, MotherShip, Unit
from astrobox.guns import PlasmaProjectile

MIN_SOLDER_DEFENDER = 3
MIN_ENEMY_ON_BASE_TO_ATTACK = 1
MIN_DRONE_FOR_ATTACK = 3
MIN_SOLIDER = 3
CNT_DANGER_TO_SOLIDER = 2
MAX_NOT_FIGHT = 1
MIN_COUNT_ENEMY_DRONE_IN_HOME_ZONE = 1

CAN_LOAD = 'CAN_LOAD'
CAN_UNLOAD = 'CAN_UNLOAD'
DANGER = 'DANGER'
NONE = 'NONE'
SUCCESS = 'SUCCESS'
UNSUCCESSFUL = 'UNSUCCESSFUL'
NEXT_TARGET = "NEXT_TARGET"
IMPOSSIBLE = "IMPOSSIBLE"
MOVE_TO_LOAD = "MOVE_TO_LOAD"
LOAD_FROM_TARGET = "LOAD_FROM_TARGET"
MOVE_TO_UNLOAD = "MOVE_TO_UNLOAD"
CAN_FIGHT = 'CAN_FIGHT'
MOVE_TO_PLACE_FIGHT = 'MOVE_TO_PLACE_FIGHT'
FIND_LOAD = 'FIND_LOAD'
MOVE_TO_DEFEND_PLACE = "MOVE_TO_DEFEND_PLACE"
DEFENDER = "DEFENDER"
UNLOAD_FROM_TARGET = 'UNLOAD_FROM_TARGET'

SCENARIOS = {
    "CollectorRole":
        {
            "DEFAULT": "NULL",
            "NULL": {
                "handler": "available_do",
                "result_state": {"CAN_LOAD": "FIND_LOAD",
                                 "CAN_UNLOAD": "MOVE_TO_UNLOAD",
                                 "DANGER": "MOVE_TO_REPAIR",
                                 "NONE": "IMPOSSIBLE"}

            },
            "FIND_LOAD": {
                "handler": "find_load_target",
                "result_state": {"SUCCESS": "MOVE_TO_LOAD",
                                 "DANGER": "MOVE_TO_REPAIR",
                                 "UNSUCCESSFUL": "NULL"}
            },
            "MOVE_TO_LOAD": {
                "handler": "move_to_load",
                "result_state": {"DANGER": "MOVE_TO_REPAIR",
                                 "SUCCESS": "LOAD_FROM_TARGET",
                                 "NEXT_TARGET": "FIND_LOAD",
                                 "UNSUCCESSFUL": "NULL"}
            },
            "MOVE_TO_UNLOAD": {
                "handler": "move_to_unload",
                "result_state": {"DANGER": "MOVE_TO_REPAIR",
                                 "SUCCESS": "UNLOAD_FROM_TARGET",
                                 "UNSUCCESSFUL": "NULL"}
            },
            "LOAD_FROM_TARGET": {
                "handler": "load_from_target",
                "result_state": {"DANGER": "MOVE_TO_REPAIR",
                                 "SUCCESS": "MOVE_TO_UNLOAD",
                                 "NEXT_TARGET": "FIND_LOAD",
                                 "UNSUCCESSFUL": "NULL"}
            },
            "UNLOAD_FROM_TARGET": {
                "handler": "unload_from_target",
                "result_state": {"DANGER": "MOVE_TO_REPAIR",
                                 "SUCCESS": "NULL",
                                 "UNSUCCESSFUL": "NULL"
                                 }
            },
            "MOVE_TO_REPAIR": {
                "handler": "move_to_repair",
                "result_state": {
                    "MOVE_TO_UNLOAD": "MOVE_TO_UNLOAD",
                    "SUCCESS": "REPAIR"}
            },
            "REPAIR": {
                "handler": "repair",
                "result_state": {"CAN_UNLOAD": "UNLOAD_FROM_TARGET",
                                 "SUCCESS": "NULL"}
            },
            "IMPOSSIBLE": {
                "handler": None,
                "result_state": {}
            }
        },
    "SoliderRole": {
        "DEFAULT": "NULL",
        "NULL": {
            "handler": "available_do",
            "result_state": {
                "CAN_FIGHT": "FIND_TARGET",
                "DANGER": "MOVE_TO_DEFEND_PLACE",
                "DEFENDER": "MOVE_TO_DEFEND_PLACE",
                "NONE": "IMPOSSIBLE"
            }
        },
        "MOVE_TO_DEFEND_PLACE":
            {
                "handler": "move_to_defend_place",
                "result_state": {
                    "SUCCESS": "FIND_TARGET",
                }
            },
        "FIND_TARGET": {
            "handler": "find_target",
            "result_state": {
                "SUCCESS": "MOVE_TO_PLACE_FIGHT",
                "UNSUCCESSFUL": "NULL",
                "DANGER": "MOVE_TO_DEFEND_PLACE"
            }
        },
        "MOVE_TO_PLACE_FIGHT": {
            "handler": "move_to_place",
            "result_state": {
                "SUCCESS": "FIGHT",
                "UNSUCCESSFUL": "NULL",
                "DANGER": "MOVE_TO_DEFEND_PLACE"
            }
        },
        "FIGHT": {
            "handler": "fight_to_target",
            "result_state": {
                "UNSUCCESSFUL": "NULL",
                "SUCCESS": "FIND_TARGET",
                "DANGER": "MOVE_TO_DEFEND_PLACE"
            }
        },
        "IMPOSSIBLE": {
            "handler": None,
            "result_state": {}
        }},
}


def _counter(func):
    """Декоратор для next_action, для избегания рекурсий"""

    def run_scenario(self, *args, **kwargs):
        if self.count_scenario < 5:
            self.count_scenario += 1
            func(self, *args, **kwargs)

    return run_scenario


def is_circles_intersection(in_circle_1: Point, in_radius1: float, in_circle_2: Point, in_radius2: float, ):
    x1, y1, r1 = in_circle_1.x, in_circle_1.y, in_radius1
    x2, y2, r2 = in_circle_2.x, in_circle_2.y, in_radius2

    dx, dy = x2 - x1, y2 - y1
    d = math.sqrt(dx * dx + dy * dy)
    if d > r1 + r2:
        return False
    else:
        return True


def circle_line_segment_intersection(circle_center, circle_radius, pt1, pt2, full_line=True, tangent_tol=1e-9):
    """Find the points at which a circle intersects a line-segment.  This can happen at 0, 1, or 2 points.
    Источник https://stackoverflow.com/questions/30844482/what-is-most-efficient-way-to-find-the-intersection-of-a-line
    -and-a-circle-in-py

    :param circle_center: The (x, y) location of the circle center
    :param circle_radius: The radius of the circle
    :param pt1: The (x, y) location of the first point of the segment
    :param pt2: The (x, y) location of the second point of the segment
    :param full_line: True to find intersections along full line - not just in the segment.  False will just return inte
    rsections within the segment.
    :param tangent_tol: Numerical tolerance at which we decide the intersections are close enough to consider it a tang
    ent

    :return Sequence[Tuple[float, float]]: A list of length 0, 1, or 2, where each element is a point at which the circl
    e intercepts a line segment.

    Note: We follow: http://mathworld.wolfram.com/Circle-LineIntersection.html
    """

    (p1x, p1y), (p2x, p2y), (cx, cy) = pt1, pt2, circle_center
    (x1, y1), (x2, y2) = (p1x - cx, p1y - cy), (p2x - cx, p2y - cy)
    dx, dy = (x2 - x1), (y2 - y1)
    dr = (dx ** 2 + dy ** 2) ** .5
    big_d = x1 * y2 - x2 * y1
    discriminant = circle_radius ** 2 * dr ** 2 - big_d ** 2

    if discriminant < 0:  # No intersection between circle and line
        return []
    else:  # There may be 0, 1, or 2 intersections with the segment
        intersections = [
            (cx + (big_d * dy + sign * (-1 if dy < 0 else 1) * dx * discriminant ** .5) / dr ** 2,
             cy + (-big_d * dx + sign * abs(dy) * discriminant ** .5) / dr ** 2)
            for sign in ((1, -1) if dy < 0 else (-1, 1))]  # This makes sure the order along the segment is correct
        # If only considering the segment, filter out intersections that do not fall within the segment
        if not full_line:
            fraction_along_segment = [(xi - p1x) / dx if abs(dx) > abs(dy) else (yi - p1y) / dy for xi, yi in
                                      intersections]
            intersections = [pt for pt, frac in zip(intersections, fraction_along_segment) if 0 <= frac <= 1]
        # If line is tangent to circle, return just one point (as both intersections have same location)
        if len(intersections) == 2 and abs(discriminant) <= tangent_tol:
            return [intersections[0]]
        else:
            return intersections


def is_line_intersection_circle(in_circle_point: Point, radius: float, in_line_point1: Point,
                                in_line_point2: Point) -> bool:
    """
    Проверка пересечения линии окружности

    :param in_circle_point: Point Центр круга
    :param radius: float Радиус круга
    :param in_line_point1: point точка начало/конца линии
    :param in_line_point2: point точка начало/конца линии

    :return: Возврат True если линия пересекает круг иначе False
    """

    if is_circles_intersection(in_circle_point, radius, in_line_point1, 15):
        return True

    points = circle_line_segment_intersection((in_circle_point.x, in_circle_point.y), radius,
                                              (in_line_point1.x, in_line_point1.y),
                                              (in_line_point2.x, in_line_point2.y),
                                              full_line=False)
    return bool(points)


def all_positions(in_distance: float, in_radius_drone: float) -> List[Point]:
    """
     Выдать точки круга в расстоянии друг от друга, без пересечения радиуса int_radius_drone

    :param in_distance: расстояние до центральной точки
    :param in_radius_drone: используемы радиус между точками, т.е. круг от точки в радиусе in_radius_drone не должен пер
    есекаться

    :return: возвратит  List[Point]
    """

    r = in_distance

    points = []
    a = r
    b = r
    c = in_radius_drone + 1

    turn_angle = math.degrees(math.acos((a ** 2 + b ** 2 - c ** 2) / (2 * a * b))) * 2
    pos_count = round(360 / turn_angle)
    avg_agree = (360 - turn_angle * pos_count) / pos_count

    if avg_agree < 0 and pos_count > 1:
        avg_agree = (360 - turn_angle * (pos_count - 1)) / (pos_count - 1)

    turn_angle = round(turn_angle + avg_agree)
    angle = -10

    while angle < 360:
        v_pos = Vector.from_direction(angle, r)
        angle += turn_angle
        points.append(Point(round(v_pos.x), round(v_pos.y)))

    return points


class AbstractVoychenkoDrone:
    __metaclass__ = ABCMeta

    @property
    @abstractmethod
    def target(self) -> Unit:
        pass

    @target.setter
    @abstractmethod
    def target(self, value: Unit):
        pass

    @property
    @abstractmethod
    def pos_point(self) -> Point:
        pass

    @pos_point.setter
    @abstractmethod
    def pos_point(self, value: Point):
        pass

    @property
    @abstractmethod
    def role(self) -> 'Role':
        pass

    @role.setter
    @abstractmethod
    def role(self, value: 'Role'):
        pass

    @property
    @abstractmethod
    def strategy(self) -> 'Strategy':
        pass

    @strategy.setter
    @abstractmethod
    def strategy(self, value: 'Strategy'):
        pass

    @property
    @abstractmethod
    def shot_distance(self) -> float:
        pass

    @shot_distance.setter
    @abstractmethod
    def shot_distance(self, value: float):
        pass

    @abstractmethod
    def distance_to(self, obj) -> int:
        pass

    @property
    @abstractmethod
    def coord(self) -> Point:
        pass

    @property
    @abstractmethod
    def radius(self) -> int:
        pass

    @property
    @abstractmethod
    def mothership(self) -> MotherShip:
        pass

    @property
    @abstractmethod
    def enemy_mothership(self) -> List[Drone]:
        pass

    @property
    @abstractmethod
    def teammates(self) -> List['AbstractVoychenkoDrone']:
        pass

    @abstractmethod
    def team_enemy(self, team_number: [int, None] = None) -> List[Drone]:
        pass

    @property
    @abstractmethod
    def asteroids(self) -> List[Asteroid]:
        pass

    @property
    @abstractmethod
    def health(self) -> int:
        pass

    @abstractmethod
    def team_role(self, in_type_role: type) -> List['AbstractVoychenkoDrone']:
        pass

    @property
    @abstractmethod
    def health2(self) -> int:
        pass

    @abstractmethod
    def direction(self):
        pass

    @abstractmethod
    def drone_focus_on_obj(self, in_obj: [Unit, Drone], distance: [int, None] = None) -> List[Drone]:
        pass

    @abstractmethod
    def move_at(self, target, speed=None) -> None:
        pass

    @abstractmethod
    def game_step(self):
        pass

    @abstractmethod
    def on_born(self):
        pass

    @abstractmethod
    def on_heartbeat(self):
        pass

    @abstractmethod
    def on_stop_at_asteroid(self, asteroid):
        pass

    @abstractmethod
    def on_load_complete(self):
        pass

    @abstractmethod
    def on_stop_at_mothership(self, mothership):
        pass

    @abstractmethod
    def on_unload_complete(self):
        pass

    @abstractmethod
    def on_stop_at_point(self, target):
        pass

    @abstractmethod
    def on_stop(self):
        pass

    @abstractmethod
    def on_wake_up(self):
        pass


class Position:
    def __init__(self, drone: AbstractVoychenkoDrone):
        self.drone: AbstractVoychenkoDrone = drone

    def get_point_attack_to_drone(self, in_distance: float, in_target_check: Unit):
        if self.drone.distance_to(in_target_check) <= in_distance and self.check_point(self.drone.coord,
                                                                                       in_target_check, False, True):
            return self.drone.coord
        points = self.get_point(in_distance, in_target_check)
        points = sorted(points, key=lambda val: self.drone.distance_to(val))
        return points[0] if points else None

    def get_point_attack_to_base(self, in_distance: float, in_target_check: Unit):
        if self.drone.distance_to(in_target_check) <= in_distance and self.check_point(self.drone.coord,
                                                                                       in_target_check, True, False):
            return self.drone.coord
        points = self.get_point(in_distance, in_target_check, in_check_intersection_enemy=True)
        points = sorted(points, key=lambda val: self.drone.mothership.distance_to(val))
        return points[0] if points else None

    def get_point_defend_base(self, in_distance: float, in_target_check: Unit):
        points = self.get_point(in_distance, in_target_check, in_check_intersection_myteam=False)
        points = sorted(points, key=lambda val: self.drone.distance_to(val))
        return points[0] if points else None

    def get_point(self, in_distance, in_target_check: Unit, in_check_intersection_enemy=False,
                  in_check_intersection_myteam=True) -> List[Point]:
        """Получить позиции для атаки in_target_check

        :param in_distance дистанция на которой выбрать позицию, если для нее позиция не найдена она будет
          уменьшаться
        :param in_target_check цель против которой выберается позиция
        :param in_check_intersection_enemy True - проверять пересечения с вражескими дронами
        :param in_check_intersection_myteam True проверять пересечения со своими дронами"""

        distance = in_distance  # if in_distance > self.drone.radius * 2 else self.drone.shot_distance
        points: List[Point] = []

        while not points:
            points = self._get_points_around_target(in_target_check.coord, distance)
            points = [point for point in points if self.check_point(point, in_target_check, in_check_intersection_enemy,
                                                                    in_check_intersection_myteam)]
            distance -= self.drone.radius
            if distance < self.drone.radius:
                break

        if not points:
            return []

        return points

    def check_point(self, in_point: Point, in_target_check: Unit, in_check_intersection_enemy_drone: bool,
                    in_check_intersection_myteam: bool) -> bool:
        """Проверить точку на валидность позиции

            :param in_point проверяемая позиция
            :param in_target_check цель против которой выберается позиция
            :param in_check_intersection_enemy_drone True - проверять пересечения с вражескими дронами
            :param in_check_intersection_myteam True - проверять пересечения c сво дронами"""

        if in_target_check != self.drone.mothership:
            for mothership in self.drone.enemy_mothership:
                if mothership == in_target_check:
                    continue
                if mothership.distance_to(in_point) < self.drone.shot_distance + theme.MOTHERSHIP_HEALING_DISTANCE:
                    return False

        if self.drone.mothership.distance_to(in_point) <= self.drone.mothership.radius + PlasmaProjectile.radius:
            return False

        for drone in self.drone.teammates:
            if drone.pos_point is None:
                continue
            else:
                pos_point = drone.pos_point

            if is_line_intersection_circle(pos_point, self.drone.radius + PlasmaProjectile.radius, in_point,
                                           in_target_check.coord):
                return False

            if drone.target is None:
                continue

            if in_check_intersection_myteam and is_line_intersection_circle(in_point, self.drone.radius,
                                                                            pos_point,
                                                                            drone.target.coord):
                return False

        if not in_check_intersection_enemy_drone:
            return True

        for drone in self.drone.team_enemy():
            if is_line_intersection_circle(drone.coord, drone.radius + PlasmaProjectile.radius, in_point,
                                           in_target_check.coord):
                return False
        else:
            return True

    def _get_points_around_target(self, in_point: Point, in_distance: float) -> List[Point]:
        """Получить точки позиции вокруг in_point в дистанции in_distance """

        points = all_positions(in_distance, self.drone.radius)
        points = [Point(point.x + in_point.x, point.y + in_point.y) for point in points]
        points = [point for point in points if
                  (point.y > self.drone.radius + 15) and (point.y < theme.FIELD_HEIGHT - self.drone.radius - 15)
                  and (point.x > self.drone.radius + 15) and (
                          point.x < theme.FIELD_WIDTH - self.drone.radius - 15)]
        return points


class Role:
    def __init__(self, drone):
        self.drone = drone
        self.state: str = SCENARIOS[type(self).__name__]['DEFAULT']
        self.home_distance = self.drone.shot_distance + theme.MOTHERSHIP_HEALING_DISTANCE

    def is_attack_base(self):
        enemy_drone_near_base = [drone for drone in self.drone.team_enemy() if
                                 self.drone.mothership.distance_to(drone) < self.home_distance]
        asteroids_max_to_miss_danger = self.drone.count_asteroids * 0.7
        can_miss_danger = (self.drone.count_fullness_asteroid <= asteroids_max_to_miss_danger)
        return len(enemy_drone_near_base) > MIN_COUNT_ENEMY_DRONE_IN_HOME_ZONE and can_miss_danger

    def available_do(self):
        pass


class CollectorRole(Role):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def available_do(self) -> str:
        """Что дрон может сделать"""

        if self.drone.cargo.payload > 0:
            return CAN_UNLOAD

        if self.get_load_target() is not None:
            return CAN_LOAD
        elif self.drone.cargo.payload > 0:
            return UNLOAD_FROM_TARGET
        else:
            return NONE

    def busy_asteroids(self) -> defaultdict:
        """Астероиды занятые своими дронами key - астероид, value эллериум который будет собран"""

        asteroids = defaultdict(int)
        for drone in self.drone.team_role(CollectorRole):
            if drone == self.drone:
                continue

            if isinstance(drone.target, Asteroid):
                asteroid: Unit = drone.target
                asteroids[asteroid] += drone.cargo.free_space

        return asteroids

    def get_available_motherships(self):
        if self.drone.cargo.free_space <= 20:
            return []
        all_motherships: List[Unit] = []
        for mothership in self.drone.enemy_mothership:
            if mothership.cargo.payload == 0 or mothership.is_alive:
                continue
        return all_motherships

    def get_available_drone_no_asteroid(self):
        all_drones: List[Unit] = []
        for drone in self.drone.team_enemy():
            if not isinstance(drone, Drone) or drone.cargo.payload == 0:
                continue
            if drone.distance_to(drone.mothership) <= theme.MOTHERSHIP_HEALING_DISTANCE:
                continue
            if self.drone.distance_to(drone) > theme.CARGO_TRANSITION_DISTANCE*3:
                continue
            all_drones.append(drone)
        if all_drones:
            all_drones = sorted(all_drones, key=lambda val: val.distance_to(self.drone))[-1:]
        return all_drones

    def get_available_drone(self):
        all_drones: List[Unit] = []
        for drone in self.drone.team_enemy():
            if not isinstance(drone, Drone):
                continue
            if self.drone.distance_to(drone) > theme.CARGO_TRANSITION_DISTANCE:
                continue
            if isinstance(drone.target, Asteroid):
                all_drones.append(drone)
        if all_drones:
            all_drones = sorted(all_drones, key=lambda val: val.distance_to(self.drone))[-1:]
        return all_drones

    def get_available_asteroids(self) -> List[Unit]:
        busy_asteroids = self.busy_asteroids()

        asteroids: List[Unit] = [asteroid for asteroid in self.drone.asteroids if asteroid not in busy_asteroids.keys()]
        return asteroids

    def get_available_obj(self) -> List[Unit]:
        """Выдаёт список доступных для сборки объектов"""

        all_asteroid = []
        if all_asteroid.extend(self.get_available_drone()):
            return all_asteroid
        all_asteroid.extend(self.get_available_motherships())
        all_asteroid.extend(self.get_available_asteroids())
        all_asteroid.extend(self.get_available_drone_no_asteroid())
        return all_asteroid

    def get_load_target(self) -> [Unit, None]:
        """Найти цель для сборки"""

        asteroids: List[Unit] = self.get_available_obj()
        if not asteroids:
            return None

        asteroids.sort(key=lambda value: self.drone.distance_to(value))

        return asteroids[0]

    def find_load_target(self) -> str:
        if self.drone.free_space > 0:
            self.drone.target = self.get_load_target()
        else:
            self.drone.target = None

        if self.drone.target is None:
            if self.drone.cargo.payload > 0:
                self.state = MOVE_TO_UNLOAD
            else:
                self.drone.move_at(self.drone.mothership)

        return SUCCESS if self.drone.target is not None else UNSUCCESSFUL

    def move_to_load(self) -> str:
        if self.drone.target is None or self.drone.target not in self.get_available_obj():
            return UNSUCCESSFUL

        if self.is_can_load():
            return ''

        if isinstance(self.drone.target, Drone) and self.drone.target.is_alive:
            self.find_load_target()
            if self.drone.target is None:
                return UNSUCCESSFUL

        if isinstance(self.drone.target, Asteroid) and self.drone.target.cargo.payload == 0 \
                and self.is_near_target(self.drone.target):
            alernative = self.drone.enemy_near_obj(self.drone.target, theme.CARGO_TRANSITION_DISTANCE)
            alernative = sorted([drone for drone in alernative if drone.cargo.payload > 0],
                                key=lambda val: self.drone.distance_to(val))
            if alernative:
                self.drone.target = alernative[0]
            else:
                return NEXT_TARGET

        if self.drone.distance_to(self.drone.target) <= theme.CARGO_TRANSITION_DISTANCE:
            return SUCCESS
        else:
            self.drone.move_at(self.drone.target)

    def is_near_target(self, target):
        return self.drone.distance_to(target) <= theme.CARGO_TRANSITION_DISTANCE

    def is_can_load(self):
        if self.get_available_drone() and self.drone.free_space > 0:
            self.drone.target = self.get_available_drone()[0]
            self.state = LOAD_FROM_TARGET
            return True

    def move_to_unload(self) -> str:
        self.drone.target = self.drone.mothership
        if self.is_can_load():
            return ''
        if self.drone.distance_to(self.drone.target) < theme.CARGO_TRANSITION_DISTANCE:
            return SUCCESS
        else:
            self.drone.move_at(self.drone.target)

    def load_from_target(self) -> str:
        """ Загрузить эллериум с цели"""

        if self.drone.target is None:
            return UNSUCCESSFUL

        self.is_can_load()

        if self.drone.free_space > 0 and self.drone.target.payload > 0:
            if self.drone.distance_to(self.drone.target) >= theme.CARGO_TRANSITION_DISTANCE:
                return NEXT_TARGET
            self.drone.load_from(self.drone.target)
        else:
            if self.drone.cargo.free_space > 20:
                return NEXT_TARGET
            else:
                return SUCCESS

    def unload_from_target(self) -> str:
        """ Выгрузить эллериум в MotherShip"""

        if self.drone.target is None:
            return UNSUCCESSFUL

        if self.drone.payload > 0 and self.drone.target.cargo.free_space > 0:
            self.drone.turn_to(self.drone.center)
            self.drone.unload_to(self.drone.target)
        else:
            return SUCCESS

    def move_to_repair(self) -> [str, None]:
        # Едем на ремонт если можем разгрузиться - разгружаемся
        if self.is_can_load():
            return ''

        if self.drone.cargo.payload > 0:
            self.drone.target = self.drone.mothership
            return MOVE_TO_UNLOAD

        if self.drone.distance_to(
                self.drone.mothership) < theme.MOTHERSHIP_HEALING_DISTANCE - self.drone.radius * 1.5:
            return SUCCESS

        self.drone.target = self.drone.mothership

        if self.drone.near(self.drone.target):
            return SUCCESS
        else:
            self.drone.move_at(self.drone.target)

    def repair(self) -> [str, None]:
        if self.is_can_load():
            return ''
        if self.drone.health == theme.DRONE_MAX_SHIELD:
            return SUCCESS


class SoliderRole(Role):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.count_not_fight = 0
        self.position = Position(self.drone)

    def available_do(self) -> str:
        """Возможные действия SoliderDrone"""

        if self.drone.gun is None:
            return NONE

        if not self.drone.team_enemy() and not self.drone.enemy_mothership:
            return NONE

        if self.is_attack_base():
            return DEFENDER

        return CAN_FIGHT

    def get_target_obj(self) -> [Drone, None]:
        """Найти цель среди дронов"""

        if not self.enemy_available:
            return None
        enemy_near_team = [self.drone.enemy_near_obj(drone, drone.shot_distance) for drone in self.drone.teammates]
        if enemy_near_team:
            enemy_near_team = set(reduce(lambda x, y: x + y, enemy_near_team))
            enemy_near_team = list(set(self.enemy_available) & enemy_near_team)

        if enemy_near_team:
            enemy_near_team = sorted(enemy_near_team, key=lambda val: self.drone.distance_to(val))
        else:
            enemy_near_team = sorted(self.enemy_available, key=lambda val: self.drone.distance_to(val))

        targets_can_shot = list(
            filter(lambda val: self.drone.is_can_shot(val) and self.drone.distance_to(val) < self.drone.shot_distance,
                   enemy_near_team))

        if targets_can_shot:
            return targets_can_shot[0]
        else:
            return enemy_near_team[0]

    def get_common_target(self) -> [None, Unit]:
        """найти общую цель"""

        team_targets: List[Unit] = []

        for drone in self.drone.team_role(SoliderRole):
            if drone == self.drone or self.drone.target is None or self.drone.target not in self.enemy_available:
                continue

            if self.drone.target is not None and self.drone.target not in team_targets:
                team_targets.append(self.drone.target)

        if not team_targets:
            return None

        team_targets = sorted(team_targets, key=lambda key: self.drone.distance_to(key))
        return team_targets[0]

    def find_target(self):
        """найти цель среди дронов, баз, общей цели"""
        target = self.get_common_target()
        if target is None or target is not None and not self.drone.is_can_shot(target):
            target = self.get_target_obj()

        if isinstance(target, Drone) and target.mothership in self.enemy_mothership_available:
            have_drones = len(self.drone.team_role(SoliderRole)) >= MIN_DRONE_FOR_ATTACK
            enemy_mothership_can_shot = self.drone.distance_to(target.mothership) <= self.drone.shot_distance
            self_in_health_zone = self.drone.distance_to(self.drone.mothership) <= theme.MOTHERSHIP_HEALING_DISTANCE
            can_attack_base = have_drones or (enemy_mothership_can_shot and self_in_health_zone)
            enemy_dist_to_base = target.distance_to(target.mothership)
            is_drone_in_health_zone = enemy_dist_to_base <= theme.MOTHERSHIP_HEALING_DISTANCE + self.drone.radius

            if can_attack_base and is_drone_in_health_zone:
                target = target.mothership

        self.drone.target = target
        if self.drone.target is None:
            return DANGER

        self.count_not_fight = 0
        return SUCCESS

    def move_to_defend_place(self):
        """Двигаться к базе в зону востановления занять позицию к обороне"""
        if self.drone.pos_point is None or self.drone.distance_to(
                self.drone.pos_point) > theme.MOTHERSHIP_HEALING_DISTANCE:
            distance = theme.MOTHERSHIP_HEALING_DISTANCE - self.drone.radius
            self.drone.pos_point = self.position.get_point_defend_base(distance, self.drone.mothership)

        if self.drone.pos_point is None:
            self.drone.move_at(self.drone.mothership.coord)
            return

        if self.drone.distance_to(self.drone.pos_point) < 5:
            self.drone.turn_to(self.drone.center)
            return SUCCESS
        else:
            self.drone.move_at(self.drone.pos_point)

    def move_to_place(self):
        """Двигаться к найденному месту для атаки"""
        if self.drone.target not in self.enemy_available or self.drone.target is None:
            self.drone.target = None
            return UNSUCCESSFUL

        if isinstance(self.drone.target, MotherShip) \
                and self.drone.enemy_near_obj(self.drone.target, theme.MOTHERSHIP_HEALING_DISTANCE) == 1 \
                and self.drone.distance_to(self.drone.target) <= self.drone.shot_distance / 2:
            for drone in self.drone.team_role(SoliderRole):
                if drone.pos_point == self.drone.mothership.coord:
                    break
            else:
                self.drone.pos_point = self.drone.target.coord

        if self.drone.pos_point is not None:
            is_far_away_from_target = self.drone.target.distance_to(self.drone.pos_point) > self.drone.shot_distance
            is_can_damage_self_base = self.drone.distance_to(self.drone.mothership) < self.drone.mothership.radius
        else:
            is_far_away_from_target, is_can_damage_self_base = False, False

        distance = self.drone.distance_to(self.drone.target)
        if distance > self.drone.shot_distance:
            distance = self.drone.shot_distance
        if distance < self.drone.radius * 2:
            distance = self.drone.radius * 2

        if not self.is_attack_base() and (
                self.drone.pos_point is None or is_far_away_from_target or is_can_damage_self_base):
            if isinstance(self.drone.target, MotherShip):
                self.drone.pos_point = self.position.get_point_attack_to_base(distance,
                                                                              self.drone.target)
            else:
                self.drone.pos_point = self.position.get_point_attack_to_drone(distance,
                                                                               self.drone.target)
        if self.drone.pos_point is None:
            return UNSUCCESSFUL

        if self.drone.distance_to(self.drone.pos_point) < 5:
            return SUCCESS
        else:
            self.drone.move_at(self.drone.pos_point)

    def fight_to_target(self):
        """Стрелять в цель"""
        if self.drone.target is None or not self.drone.target.is_alive:
            return UNSUCCESSFUL
        if self.drone.shot_distance + PlasmaProjectile.radius < self.drone.distance_to(
                self.drone.target):
            return UNSUCCESSFUL
        if self.drone.target not in self.enemy_available:
            return UNSUCCESSFUL

        if self.count_not_fight > MAX_NOT_FIGHT:
            self.count_not_fight = 0
            self.drone.target = None
            return UNSUCCESSFUL

        end_vector_direct = Vector.from_direction(self.drone.direction, self.drone.shot_distance)
        end_point = Point(self.drone.coord.x + end_vector_direct.x, self.drone.coord.y + end_vector_direct.y)
        radius_target = self.drone.radius + PlasmaProjectile.radius
        if not is_line_intersection_circle(self.drone.target.coord, radius_target, self.drone.coord, end_point):
            self.drone.turn_to(self.drone.target)
        else:
            if self.drone.is_can_shot():
                self.count_not_fight = 0
                if is_line_intersection_circle(self.drone.target.coord, radius_target, self.drone.coord, end_point):
                    self.drone.turn_to(self.drone.target)
                    self.drone.gun.shot(self.drone.target)
            else:
                self.count_not_fight += 1

    @property
    def enemy_available(self) -> List[Unit]:
        all_enemy: List[Unit] = []
        all_enemy.extend(self.enemy_drone_available)
        all_enemy.extend(self.enemy_mothership_available)
        return all_enemy

    @property
    def enemy_drone_available(self) -> List[Drone]:
        """Дроны в зоне лечения пропускаются"""

        return [drone for drone in self.drone.team_enemy()
                if self.drone.mothership.distance_to(drone) < self.home_distance or
                drone not in self.drone.enemy_near_obj(drone.mothership, theme.MOTHERSHIP_HEALING_DISTANCE)
                or not drone.mothership.is_alive]

    @property
    def enemy_mothership_available(self) -> List[MotherShip]:
        motherships: List[MotherShip] = []
        count_mothership = len([mothership for mothership in self.drone.enemy_mothership if mothership.is_alive])
        max_length_to_mathership = max(
            [self.drone.mothership.distance_to(mothership) for mothership in self.drone.enemy_mothership])
        for mothership in self.drone.enemy_mothership:
            if count_mothership == 3 and self.drone.mothership.distance_to(mothership) == max_length_to_mathership:
                continue
            is_min_drone_enemy = len(self.drone.team_enemy(mothership.team_number)) <= MIN_ENEMY_ON_BASE_TO_ATTACK
            is_have_drone_to_attack = len(self.drone.team_role(SoliderRole)) >= MIN_DRONE_FOR_ATTACK
            cnt_near_base = self.drone.enemy_near_obj(mothership, theme.MOTHERSHIP_HEALING_DISTANCE)
            is_all_in_health_zone = cnt_near_base == self.drone.team_enemy(mothership.team_number)
            is_base_near = self.drone.mothership.distance_to(mothership) <= self.drone.shot_distance
            is_self_in_health_zone = self.drone.distance_to(self.drone.mothership) <= theme.MOTHERSHIP_HEALING_DISTANCE
            if (is_have_drone_to_attack and is_min_drone_enemy) or (
                    is_all_in_health_zone and is_base_near and is_self_in_health_zone):
                motherships.append(mothership)
        return motherships


class Strategy:
    all_ellerium = 0

    def __init__(self, drone: AbstractVoychenkoDrone):
        self.drone = drone
        self.count_scenario = 0
        self.drone.role = CollectorRole(self.drone)
        self.danger_count = 0
        self.all_ellerium = 0
        self.team_attack = False

    def sum_ellerium(self):
        self.all_ellerium = sum([asteroid.cargo.payload for asteroid in self.drone.asteroids])

    def rest_counter(self):
        self.count_scenario = 0

    def is_danger(self) -> bool:
        """ "Трусость" дронов, если опасно - Бежать!"""

        if self.drone.role.state in [MOVE_TO_UNLOAD, UNLOAD_FROM_TARGET] and self.drone.target == self.drone.mothership:
            return False
        if isinstance(self.drone.role, SoliderRole) and self.drone.distance_to(
                self.drone.mothership) < theme.MOTHERSHIP_HEALING_DISTANCE:
            return False

        if self.drone.health == theme.DRONE_MAX_SHIELD:
            return False

        drone_focus_on_me = self.drone.drone_focus_on_obj(self.drone)

        if not drone_focus_on_me:
            return False

        if isinstance(self.drone.role, SoliderRole) and self.drone.target is not None and isinstance(self.drone.target,
                                                                                                     MotherShip):
            can_death = theme.PROJECTILE_DAMAGE
            health = self.drone.health if not drone_focus_on_me else self.drone.health - theme.PROJECTILE_DAMAGE
        else:
            can_death = len(drone_focus_on_me) * theme.PROJECTILE_DAMAGE
            health = self.drone.health2

        if health - can_death < theme.PROJECTILE_DAMAGE:
            return True

        return False

    def change_role(self):
        if isinstance(self.drone.role, CollectorRole):
            self.drone.role = SoliderRole(self.drone)
        elif isinstance(self.drone.role, SoliderRole):
            self.drone.role = CollectorRole(self.drone)

        if self.drone.role.available_do() == IMPOSSIBLE:
            self.drone.move_at(self.drone.mothership)
        else:
            self.next_action()

    @_counter
    def next_action(self) -> None:
        if self.drone.role is None:
            return

        handler_str = ''

        if self.count_scenario > 5:
            return

        self.analyze_roles()

        self.count_scenario += 1
        role_str = type(self.drone.role).__name__
        try:
            if DANGER in SCENARIOS[role_str][self.drone.role.state]['result_state'].keys() and self.is_danger():
                answer = DANGER
                if len(self.drone.team_role(SoliderRole)) < MIN_SOLIDER:
                    self.change_role()
                    self.next_action()
                    return
                self.drone.pos_point = None
                self.danger_count += 1
            else:
                handler_str = SCENARIOS[role_str][self.drone.role.state]['handler']
                if handler_str is None:
                    return
                handler = getattr(self.drone.role, handler_str)
                answer = handler()

            if answer is None or answer not in SCENARIOS[role_str][self.drone.role.state]['result_state']:
                return

            state = SCENARIOS[role_str][self.drone.role.state]['result_state'][answer]
            self.drone.role.state = state

            if isinstance(self.drone.role, CollectorRole) and state in [UNLOAD_FROM_TARGET, LOAD_FROM_TARGET]:
                self.danger_count = 0

            if self.drone.role.state == IMPOSSIBLE:
                self.change_role()
            else:
                self.next_action()

        except Exception as exc:
            print(type(self.drone.role), handler_str, exc)


    def analyze_roles(self):
        if self.all_ellerium == 0:
            self.sum_ellerium()
        if isinstance(self.drone.role, CollectorRole) and self.drone.team_enemy():
            if self.danger_count >= CNT_DANGER_TO_SOLIDER and self.drone.mothership.cargo.payload < (
                    self.all_ellerium * 0.5):
                self.change_role()

        if isinstance(self.drone.role, SoliderRole) \
                and not self.is_danger() \
                and self.drone.health == theme.DRONE_MAX_SHIELD \
                and (self.drone.mothership.cargo.payload < (self.all_ellerium * 0.5) or not self.drone.team_enemy()) \
                and not self.drone.team_role(CollectorRole) \
                and (len(self.drone.team_role(SoliderRole)) > MIN_SOLDER_DEFENDER or not self.drone.team_enemy()):
            temp = CollectorRole(self.drone)
            if temp.available_do() != NONE:
                self.change_role()


class VoychenkoDrones(Drone, AbstractVoychenkoDrone, ABC):

    def __init__(self, **kwargs):
        Drone.__init__(self, **kwargs)
        self.role = None
        self.shot_distance = self.gun.shot_distance + PlasmaProjectile.radius + 5 if self.gun is not None else 0
        self.strategy: Strategy = Strategy(self)
        self.pos_point = None
        self.center: Point = Point(round(theme.FIELD_WIDTH / 2), round(theme.FIELD_WIDTH / 2))
        self.last_point_to_move: Point = self.coord

    @property
    def target(self) -> Unit:
        return self._target

    @target.setter
    def target(self, value: Unit):
        self._target = value

    @property
    def pos_point(self) -> Point:
        return self._pos_point

    @pos_point.setter
    def pos_point(self, value: Point):
        self._pos_point = value

    @property
    def role(self) -> 'Role':
        return self._role

    @role.setter
    def role(self, value: 'Role'):
        self._role = value

    @property
    def strategy(self) -> Strategy:
        return self._strategy

    @strategy.setter
    def strategy(self, value: Strategy):
        self._strategy = value

    @property
    def shot_distance(self) -> float:
        return self._shot_distance

    @shot_distance.setter
    def shot_distance(self, value: float):
        self._shot_distance = value

    def move_at(self, target, speed=None):
        """
          Двигаться к цели - target, Движется до точки в короткими интервалами:
            theme.DRONE_SPEED * theme.HEARTBEAT_INTERVAL
          Для анализа происходящего во время передвижения
        """
        if self.distance_to(target) < theme.DRONE_SPEED:
            return None

        if isinstance(target, Point):
            point_to_move = target
        else:
            point_to_move = target.coord

        vector_to_target = Vector.from_points(self.coord, point_to_move)

        if vector_to_target.module >= theme.DRONE_SPEED * theme.HEARTBEAT_INTERVAL:
            vector_direct = Vector.from_direction(vector_to_target.direction,
                                                  theme.DRONE_SPEED * theme.HEARTBEAT_INTERVAL)
            point_to_move = Point(self.coord.x + vector_direct.x, self.coord.y + vector_direct.y)

        if (point_to_move.x, point_to_move.x) == (self.last_point_to_move.x, self.last_point_to_move.y):
            return
        self.last_point_to_move = point_to_move

        if isinstance(target, (Asteroid, Drone, MotherShip)):
            super().move_at(target)
        else:
            super().move_at(point_to_move)

    def game_step(self):
        if self.role is not None:
            self.strategy.rest_counter()
        super().game_step()

    def on_born(self):
        self.strategy.next_action()

    def on_heartbeat(self):
        if not self.is_alive:
            return
        self.strategy.next_action()

    def on_stop_at_asteroid(self, asteroid):
        self.strategy.next_action()

    def on_load_complete(self):
        self.strategy.next_action()

    def on_stop_at_mothership(self, mothership):
        self.strategy.next_action()

    def on_unload_complete(self):
        self.strategy.next_action()

    def on_stop_at_point(self, target):
        self.strategy.next_action()

    def on_stop(self):
        self.strategy.next_action()

    def on_wake_up(self):
        if not self.is_alive:
            return
        self.strategy.next_action()

    def team_role(self, in_type_role: type) -> List[AbstractVoychenkoDrone]:
        return [drone for drone in self.scene.drones if
                isinstance(drone, VoychenkoDrones) and isinstance(drone.role, in_type_role) and drone.is_alive]

    def team_enemy(self, team_number: [int, None] = None) -> List[Drone]:
        if team_number is None:
            return [drone for drone in self.scene.drones if not isinstance(drone, VoychenkoDrones) and drone.is_alive]
        else:
            return [drone for drone in self.scene.drones if drone.team_number == team_number and drone.is_alive]

    @property
    def asteroids(self) -> List[Unit]:
        """ Астероиды, дроны, базы в которых находится эллериум"""

        asteroids: List[Unit] = [asteroid for asteroid in super().asteroids if not asteroid.cargo.is_empty]

        for obj in self.scene.objects:
            if not isinstance(obj, (Drone, MotherShip)):
                continue
            if obj.is_alive or obj in asteroids:
                continue

            if len(self.enemy_near_obj(obj, self.shot_distance)) > 2:
                continue

            if obj.cargo.payload > 0:
                asteroids.append(obj)

        asteroids = sorted(asteroids, key=lambda val: self.distance_to(val))
        return asteroids

    def drone_focus_on_obj(self, in_obj: Unit, distance: [int, None] = None) -> List[Drone]:

        """
        Выдает список дронов нацеленных на obj, и находящихся на расстоянии distance

        :param in_obj: Объект на который нацелены дроны:
        :param distance: расстояние в котором дроны могут быть находится, по умолчанию расстояние выстрела + 100

        :return: список дронов нацеленных на Obj
        """

        drone_focus_on_obj: List[Drone] = []

        if self.gun is None:
            return drone_focus_on_obj

        if distance is None:
            distance = self.shot_distance

        for drone in self.team_enemy():
            vector = Vector.from_direction(drone.direction, distance)
            end_point = Point(drone.coord.x + vector.x, drone.coord.y + vector.y)

            if is_line_intersection_circle(
                    in_obj.coord, in_obj.radius + PlasmaProjectile.radius,
                    drone.coord,
                    end_point):
                drone_focus_on_obj.append(drone)

        return drone_focus_on_obj

    @property
    def health2(self) -> int:
        """Health, учитывая возможные повреждения"""

        health = self.health

        for plasma in [obj for obj in self.scene.objects if isinstance(obj, PlasmaProjectile)]:
            len_to_me = self.distance_to(plasma.owner)

            if len_to_me > self.shot_distance:
                continue

            v1 = Vector.from_direction(plasma.owner.direction, len_to_me)
            end_point = Point(plasma.owner.coord.x + v1.x, plasma.owner.coord.y + v1.y)

            if is_line_intersection_circle(self.coord, self.radius + PlasmaProjectile.radius, plasma.owner.coord,
                                           end_point):
                health -= theme.PROJECTILE_DAMAGE

        return health

    def is_can_shot(self, in_target: Unit = None) -> bool:
        """Опредлелить можно ли сделать выстрел, не попав в своего"""
        if in_target is None and self.target is None:
            return False
        if in_target is None:
            in_target = self.target
        for drone in self.teammates:
            distance_to_drone = self.distance_to(drone)
            if drone.distance_to(in_target) < self.radius:
                continue
            if distance_to_drone > self.distance_to(in_target.coord):
                continue

            if is_line_intersection_circle(drone.coord, drone.radius + PlasmaProjectile.radius, self.coord,
                                           in_target.coord):
                return False
        else:
            return True

    @property
    def enemy_mothership(self) -> List[MotherShip]:
        """Живые базы врага"""

        return [mothership for mothership in self.scene.motherships if
                mothership != self.mothership and mothership.is_alive]

    @property
    def count_asteroids(self):
        return len(super().asteroids)

    @property
    def count_fullness_asteroid(self):
        return len([asteroid for asteroid in self.asteroids if asteroid.cargo.free_space == 0])

    def enemy_near_obj(self, in_obj: [Unit, Point], in_distance: float) -> List[Unit]:
        """Враги вокруг in_drone в дистанции in_distance"""

        v_enemy_near_obj: List[Unit] = []
        enemy: List[Unit] = self.team_enemy()
        enemy.extend(self.enemy_mothership)
        for enemy_drone in enemy:
            if in_obj.distance_to(enemy_drone) < in_distance:
                v_enemy_near_obj.append(enemy_drone)

        return v_enemy_near_obj


drone_class = VoychenkoDrones