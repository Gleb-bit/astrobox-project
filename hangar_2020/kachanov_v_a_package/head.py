import importlib
import inspect
import logging
import math
import random

from astrobox.themes.default import MOTHERSHIP_HEALING_DISTANCE
from robogame_engine import GameObject, scene
from robogame_engine.geometry import Point, get_arctan
from robogame_engine.geometry import Vector

from hangar_2020.kachanov_v_a_package.roles import Turel, BaseGuard, Spy, CombatBot, Collector, Distractor, Defender, \
    Transport

logging.basicConfig(filename="head.log", filemode="w", level=logging.INFO)


class Headquarters:
    """
    Штаб-кватриа.

    Раздаёт роли солдатам:
    collector - забирает элериум с ближайших астеройов и тащит его на баз;
    transport - собирает элериум с дальних астеройдов и подтаскивает его на астеройды, ближайшие к базе,
        откуда потом его забирает collector;
    combat - солдат с боевым оружием;
    spy - шпион-подрывник, атакует базы;
    base guard - ополчение, все ополченцы атакуют одного противника;
    turel - обороняет базу, под прикрытием базы ведет непрерывный огонь в сторону противника.

    Команды солдатам:
    move - двигаться к объекту;
    load - собрать элериум с объекта;
    unload - разгрузиться в объект;
    it is free - астеройд свободен для других дронов.
    Команды помещаются в очередь и выполняются последовательно.
    """

    roles = {}
    asteroids_for_basa = []
    moves_empty = 0
    moves_semi_empty = 0
    moves_full = 0
    start_position = {}

    angles_turel = [0, 30]
    angles_distractor = []
    angles_turel_2 = []
    nearest_asteroid = None
    buffer_zone = []
    points_attack = []
    enemy = None
    angles_collector = [-30, 55, -55]
    start_angles = []

    map_field = scene.theme.FIELD_WIDTH, scene.theme.FIELD_HEIGHT
    center_map = Point(x=round(int(map_field[0] // 2)), y=round(int(map_field[1] // 2)))

    def __init__(self):
        self.soldiers = []
        self.asteroids_in_work = []

        self.transport = 0
        self.collector = 3
        self.combatbot = 0
        self.spy = 0
        self.turel = 2
        self.baseguard = None
        self.distractor = 0
        self.enemy = None
        self.near_temmates = []
        self.move_to_base = False

    def new_soldier(self, soldier):
        number_drones = len(self.soldiers)
        self.get_roles(number_drones + 1, soldier.have_gun)
        self.add_soldier(soldier)
        for idx, soldier in enumerate(self.soldiers):
            self.give_role(soldier, idx)

    def give_role(self, soldier, index):
        classes = [class_item for class_item in
                   inspect.getmembers(importlib.import_module("hangar_2020.kachanov_v_a_package.roles"),
                                      inspect.isclass)]
        all_roles = [class_item[0] for class_item in classes if hasattr(self, class_item[0].lower())]
        all_roles = [globals()[class_item] for class_item in all_roles for _ in range(self.roles[class_item.lower()])]
        all_roles.reverse()
        this_role = all_roles[index]
        soldier.role = this_role(unit=soldier)

    def get_roles(self, numb_drones, have_gun):
        if have_gun:
            self.baseguard = max(0, numb_drones - self.collector - self.spy - self.turel - self.transport -
                                 self.combatbot - self.distractor)
        else:
            self.transport, self.combatbot, self.spy, self.turel, self.baseguard, self.distractor = 0 * 5
            self.collector = numb_drones
            Headquarters.roles["collector"] = self.collector

        classes = [class_item for class_item in
                   inspect.getmembers(importlib.import_module("hangar_2020.kachanov_v_a_package.roles"),
                                      inspect.isclass)]
        all_roles = [class_item[0].lower() for class_item in classes if hasattr(self, class_item[0].lower())]
        for role in all_roles:
            Headquarters.roles[role] = self.__getattribute__(role)

    def add_soldier(self, soldier):
        soldier.headquarters = self
        soldier.actions = []
        soldier.basa = None
        soldier.old_asteroid = None
        self.soldiers.append(soldier)

    def get_actions(self, soldier):
        soldier.buffer_zone.clear()

        purpose = soldier.role.next_purpose()

        """HIT DETECTION FOR FRIENDLY FIRE PREVENT"""
        if isinstance(soldier.role, Turel):
            if purpose:
                vec_to_purpose = Vector.from_points(soldier.coord, purpose.coord)
                for mate in soldier.teammates:
                    if soldier.distance_to(mate) <= 20:
                        soldier.buffer_zone.append(0)
                        break
                    vec_to_mate = Vector.from_points(soldier.coord, mate.coord)
                    vec_multiply = vec_to_purpose.x * vec_to_mate.x + vec_to_purpose.y * vec_to_mate.y
                    vec_multiply_modules = int(vec_to_purpose.module * vec_to_mate.module)
                    if vec_multiply_modules == 0:
                        soldier.buffer_zone.append(0)
                        break
                    else:
                        angle = math.degrees(math.acos(int(vec_multiply) / vec_multiply_modules))
                        if angle < 30:
                            soldier.buffer_zone.append(angle)
                            break

        full_teams = [base[0] for base in self.get_bases(soldier)
                      if 0 < len(self.get_drones_by_base(soldier, base[0])) < 2]

        empty_teams = [base[0] for base in self.get_bases(soldier)
                       if len(self.get_drones_by_base(soldier, base[0])) == 0]

        week_teams = []
        if len(soldier.scene.teams) - len(full_teams) <= len(soldier.scene.teams) / 2 and len(soldier.scene.teams) != 4:
            week_teams = full_teams
        elif len(soldier.scene.teams) - len(empty_teams) <= len(soldier.scene.teams) / 2:
            week_teams = empty_teams
        elif 0 < len(full_teams) < 2 and len(empty_teams) > 0:
            week_teams.append(full_teams[0])
            week_teams.append(empty_teams[0])

        if len(soldier.teammates) > 2 and len(week_teams) > 0:
            """CONDITION FOR ENTER OF COUNT OF WEEKS TEAMS"""

            if len(self.angles_turel_2) == 0 or self.enemy and not self.enemy.is_alive:
                self.angles_turel_2 = [-50, -37, -25, -13, 0, 13, 25, 37, 50]
            if soldier.distance_to(soldier.basa) <= MOTHERSHIP_HEALING_DISTANCE:
                soldier.enemy_target = None
            if soldier.enemy_target is None or not soldier.enemy_target.is_alive:
                basa = week_teams[0]
                if basa.payload >= 0:
                    if not isinstance(soldier.role, Turel):
                        soldier.role.change_role(Turel)
                    points = []
                    if len(self.get_drones_by_base(soldier, basa)) == 0 and not len(full_teams) > 0:
                        soldier.enemy_target = basa
                        soldier.role.change_role(Spy)
                        soldier.role.next_step(basa)
                        return
                    elif len(self.get_drones_by_base(soldier, basa)) > 0:
                        soldier.enemy_target = self.get_drones_by_base(soldier, basa)[0][0]
                    self.enemy = soldier.enemy_target
                    vec = self.get_vec_near_mothership(soldier, basa)
                    for angle in self.angles_turel_2:
                        koef = 0.5
                        if soldier.scene.field <= (900, 900):
                            koef = 0.7
                        vec_position = self.get_position_near_mothership(vec, koef)
                        vec_position.rotate(angle)
                        point_attack = Point(basa.coord.x + vec_position.x, basa.coord.y + vec_position.y)
                        points.append((angle, point_attack))
                    nearest_point = [(soldier.enemy_target.distance_to(point[1]), point) for point in points]
                    nearest_point.sort(key=lambda x: x[0])
                    self.angles_turel_2.remove(nearest_point[0][1][0])
                    soldier.actions.append(['move_at', nearest_point[0][1][1], 1, 1])
                    return

        if purpose:
            soldier.role.next_step(purpose)

        elif isinstance(soldier.role, Collector) and self.get_enemies(soldier):
            soldier.role.change_role(Turel)
            soldier.actions.append(['move_to', soldier.start_point, 1, 1])
        else:
            soldier.role.change_role()

    def get_enemies_by_base(self, base, nearest=True):
        enemies = self.get_enemies(base)
        result = []
        for enemy in enemies:
            if enemy[1] < MOTHERSHIP_HEALING_DISTANCE * 2 or not nearest:
                result.append(enemy[0])
        return result

    def get_enemies(self, soldier):
        enemies = [(drone, soldier.distance_to(drone)) for drone in soldier.scene.drones if
                   soldier.team != drone.team and drone.is_alive]
        enemies.sort(key=lambda x: x[1])
        return enemies

    def get_bases(self, soldier):
        bases = [(base, soldier.distance_to(base)) for base in soldier.scene.motherships if
                 base.team != soldier.team and base.is_alive]
        bases.sort(key=lambda x: x[1])
        return bases

    def remove_item_asteroids_in_work(self, item):
        if item in self.asteroids_in_work:
            idx = self.asteroids_in_work.index(item)
            self.asteroids_in_work.pop(idx)

    def get_place_for_attack(self, soldier, target):
        """
        Выбор места для атаки цели, если цель не в радиусе атаки

        :param soldier: атакующий
        :param target: цель/объект атаки
        :return: Point  - место атаки или None - если не выбрано место атаки
        """
        if isinstance(target, GameObject):
            vec = Vector.from_points(target.coord, soldier.coord)
        elif isinstance(target, Point):
            vec = Vector.from_points(target, soldier.coord)
        else:
            raise Exception("target must be GameObject or Point!".format(target, ))

        dist = vec.module
        _koef = 1 / dist
        norm_vec = Vector(vec.x * _koef, vec.y * _koef)
        vec_gunshot = norm_vec * min(int(soldier.attack_range), int(dist))
        purpose = Point(target.coord.x + vec_gunshot.x, target.coord.y + vec_gunshot.y)
        angles = [0, 60, -60, 30, -30]
        random.shuffle(angles)
        for ang in angles:
            place = self.get_place_near(purpose, target, ang)
            if place and soldier.validate_place(place):
                return place
        return None

    def get_place_near(self, point, target, angle):
        """
        Расчет места рядом с point с отклонением angle от цели target
        :param point:
        :param target:
        :param angle:
        :return: new place point
        """
        vec = Vector(point.x - target.x, point.y - target.y)
        vec.rotate(angle)
        return Point(target.x + vec.x, target.y + vec.y)

    def get_vec_near_mothership(self, soldier, base):
        center_field = Point(soldier.scene.field[0] // 2, soldier.scene.field[1] // 2)
        angle = get_arctan(center_field.y, center_field.x)
        angle_deviation = 45 - angle

        vec = Vector.from_points(base.coord, center_field)
        if base.coord.x == 90 and base.coord.y == 90 or \
                base.coord.x == soldier.scene.field[0] - 90 and base.coord.y == soldier.scene.field[1] - 90:
            vec.rotate(angle_deviation)
        else:
            vec.rotate(-angle_deviation)
        return vec

    def get_place_near_mothership(self, soldier, vec, koef=0.99):
        dist = vec.module
        _koef = 1 / dist
        norm_vec = Vector(vec.x * _koef, vec.y * _koef)
        vec_position = norm_vec * int(MOTHERSHIP_HEALING_DISTANCE * koef)
        return Point(soldier.coord.x + vec_position.x, soldier.coord.y + vec_position.y)

    def get_position_near_mothership(self, vec, koef=0.99):
        dist = vec.module
        _koef = 1 / dist
        norm_vec = Vector(vec.x * _koef, vec.y * _koef)
        vec_position = norm_vec * int(koef * dist)
        return vec_position

    def get_drones_by_base(self, soldier, base):
        return [enemy for enemy in self.get_enemies(soldier) if enemy[0].team == base.team]

    def get_start_position(self, soldier, vec_position, angle):
        vec_position.rotate(angle)
        point_attack = Point(soldier.coord.x + vec_position.x, soldier.coord.y + vec_position.y)
        return point_attack

    def generator_coord(self):
        for x in range(0, scene.theme.FIELD_WIDTH, 20):
            for y in range(0, scene.theme.FIELD_HEIGHT, 20):
                yield Point(x, y)

    def save_static_move(self, soldier, purpose):
        length = soldier.distance_to(purpose)
        if soldier.is_empty:
            self.moves_empty += length
        elif soldier.free_space > 0:
            self.moves_semi_empty += length
        elif soldier.is_full:
            self.moves_full += length
