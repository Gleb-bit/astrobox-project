# -*- coding: utf-8 -*-
import logging
import math

from astrobox.core import Asteroid
from robogame_engine import GameObject
from robogame_engine.geometry import Point, Vector
from robogame_engine.theme import theme

from hangar_2020.kachanov_v_a_package.drone import DeusDrone
from hangar_2020.kachanov_v_a_package.head import Headquarters
from hangar_2020.kachanov_v_a_package.roles import Transport, Collector, Turel, Distractor

logging.basicConfig(filename="kachanov_soldiers.log", filemode="w", level=logging.INFO)


class KachanovDrone(DeusDrone):
    actions = []
    headquarters = None
    attack_range = 0
    limit_health = 0.7
    cost_forpost = 0
    role = None
    start_dist_attack = None
    enemy_basa = None
    start_point = None
    start_angle = None
    angle = None
    point_attack = None
    target_move_to = None
    enemy_target = None
    buffer_zone = []

    def registration(self):
        if KachanovDrone.headquarters is None:
            KachanovDrone.headquarters = Headquarters()
        KachanovDrone.headquarters.new_soldier(self)

    def born_soldier(self):
        self.registration()

        if self.have_gun:
            self.attack_range = self.gun.shot_distance

        if isinstance(self.role, Transport):
            candidats_asteroids_for_basa = min([(asteroid.distance_to(self.my_mothership), asteroid)
                                                for asteroid in self.asteroids if
                                                asteroid not in self.asteroids_for_basa])

            candidat_basa = candidats_asteroids_for_basa[1]
            self.add_basa(candidat_basa)
            self.basa = candidat_basa
        else:
            self.basa = self.my_mothership

    def next_action(self):
        while not self.actions:
            self.headquarters.get_actions(self)

        action, object, is_performed, is_next = self.actions[0]
        if hasattr(self, action):
            if is_performed:
                if is_performed == 1:
                    self.actions[0][2] = 2
                    getattr(self, action)(object)
                else:
                    self.actions.pop(0)
                    self.next_action()
            else:
                self.actions.pop(0)
                getattr(self, action)(object)
                if is_next:
                    self.next_action()

        elif action == "pass":
            self.actions.pop(0)
            self.move_to_step(self.coord)

        else:
            # Пропускаем неизвестную команду
            self.actions.pop(0)
            self.next_action()

        if isinstance(object, Asteroid):
            self.old_asteroid = object

    def move_to(self, object):
        self.cost_forpost = 0
        self.target_move_to = object
        self.headquarters.save_static_move(self, object)
        vector_target = Vector.from_points(self.coord, object, module=1) if isinstance(object, Point) else \
            Vector.from_points(self.coord, object.coord, module=1)
        self.vector = vector_target
        super().move_at(object)

    def move_to_step(self, object):
        distance = min(250, max(100, self.distance_to(object) - 50))
        vec = Vector.from_direction(self.direction, distance)
        new_coord = Point(x=self.coord.x + vec.x, y=self.coord.y + vec.y)
        self.move_to(new_coord)

    def shoot(self, object):

        if not self.have_gun:
            self.role.change_role(Collector)
            return

        vec = Vector.from_points(self.coord, object.coord, module=self.attack_range)

        for partner in self.headquarters.soldiers:
            if not partner.is_alive or partner is self:
                continue

        if len(self.buffer_zone) > 0:
            return

        self.cost_forpost += 1
        self.vector = vec
        self.gun.shot(object)

    def add_attack(self, purpose):

        self.actions.append(['shoot', purpose, 1, 1])

    def go_home(self):
        self.actions.append(['move_to', self.basa, 1, 1])

    def validate_place(self, point: Point):
        """
        Подходит ли это место для атаки. Слишком рядом не должно быть партнеров и на линии огня тоже не должно быть
        партнеров.
        :param point: анализируемое место
        :return: True or False
        """

        is_valide = 0 < point.x < theme.FIELD_WIDTH and 0 < point.y < theme.FIELD_HEIGHT

        for partner in self.headquarters.soldiers:
            if not partner.is_alive or partner is self:
                continue

            is_valide = is_valide and (partner.distance_to(point) >= self.save_distance)

        return is_valide

    @property
    def save_distance(self):
        return 50  # abs(2 * self.gun.shot_distance * math.sin(10))

    def get_angle(self, partner: GameObject, target: GameObject):
        """
        Получает угол между векторами self-target и partner-target
        """

        def scalar(vec1, vec2):
            return vec1.x * vec2.x + vec1.y * vec2.y

        v12 = Vector(self.coord.x - target.coord.x, self.coord.y - target.coord.y)
        v32 = Vector(partner.coord.x - target.coord.x, partner.coord.y - target.coord.y)
        _cos = scalar(v12, v32) / (v12.module * v32.module + 1.e-8)
        return math.degrees(math.acos(_cos))

    def add_basa(self, basa):
        self.headquarters.asteroids_for_basa.append(basa)

    def asteroid_is_free(self, asteroid):
        self.headquarters.remove_item_asteroids_in_work(asteroid)

    @property
    def asteroids_for_basa(self):
        if hasattr(self.headquarters, "asteroids_for_basa"):
            return self.headquarters.asteroids_for_basa
        else:
            return self.my_mothership

    # callbacks:
    def on_born(self):

        self.born_soldier()
        nearesst_aster = [(self.distance_to(aster), aster) for aster in self.asteroids]
        nearesst_aster.sort(key=lambda x: x[0])
        idx = len(self.headquarters.soldiers) - 1

        if self.have_gun:

            vec = self.headquarters.get_vec_near_mothership(self, self.basa)
            angles = []
            if isinstance(self.role, Turel):
                angles = self.headquarters.angles_turel.copy()
                self.headquarters.angles_turel.remove(angles[0])
            elif isinstance(self.role, Collector):
                angles = self.headquarters.angles_collector.copy()
                self.headquarters.angles_collector.remove(angles[0])

            self.start_angle = angles[0]
            vec.rotate(angles[0])
            point_attack = self.headquarters.get_place_near_mothership(self, vec)
            self.start_point = point_attack
            self.vector = Vector.from_points(self.coord, self.headquarters.center_map, module=1)

            if point_attack:
                self.actions.append(['move_to', point_attack, 1, 1])
        else:
            self.actions.append(["move_to", nearesst_aster[idx][1], 1, 1])

        self.next_action()

    def on_stop_at_mothership(self, mothership):
        if self.payload > 0:
            self.actions.append(['unload_to', mothership, 1, 1])
        self.next_action()

    def on_wake_up(self):
        self.next_action()

    def on_hearbeat(self):

        if not isinstance(self.role, Turel):
            if self.meter_2 <= self.limit_health:
                self.go_home()
                self.next_action()


drone_class = KachanovDrone
