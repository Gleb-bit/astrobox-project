# -*- coding: utf-8 -*-
import logging
from astrobox.core import Drone
from astrobox.space_field import SpaceField
from robogame_engine.geometry import Point, Vector


class SimonScene(SpaceField):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.my_team = []
        self.mothership_for_attack = None
        self.points_to_attack = None
        self.points_to_attack_mothership = None

    def get_coords_for_attak_mothership(self, drones_in_my_team, mothership_name):
        mothership = self.get_mothership(mothership_name)
        drones = list(d for d in self.drones if d.team == mothership.team)
        quantity = drones_in_my_team
        if mothership.x > self.field[0] / 2 and mothership.y > self.field[1] / 2:
            p = Point(mothership.x, mothership.y - 500)
            v = Vector.from_points(mothership.coord, p)
        elif mothership.x > self.field[0] / 2 and mothership.y < self.field[1] / 2:
            p = Point(mothership.x - 500, mothership.y)
            v = Vector.from_points(mothership.coord, p)
        elif mothership.x < self.field[0] / 2 and mothership.y > self.field[1] / 2:
            p = Point(mothership.x + 500, mothership.y)
            v = Vector.from_points(mothership.coord, p)
        elif mothership.x < self.field[0] / 2 and mothership.y < self.field[1] / 2:
            p = Point(mothership.x, mothership.y + 500)
            v = Vector.from_points(mothership.coord, p)
        points_to_stop = [p]
        angle = 90 / (quantity - 1)
        difference = angle
        while len(points_to_stop) < quantity:
            next_v = Vector.from_direction(v.direction - angle, v.module)
            next_p = Point(mothership.x + next_v.x, mothership.y + next_v.y)
            points_to_stop.append(next_p)
            angle += difference
        self.points_to_attack_mothership = points_to_stop


class SimonDrone(Drone):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logging.basicConfig(filename="my_dist_drone.log", filemode="w", level=logging.INFO)
        self.action = None

        self.command_for_attack = None
        self.point_to_attack_mothership = None
        self.target_for_attack = None
        self.obj_for_on_load = None
        self.nearby_drone_is_alive = None

    def on_born(self):
        logging.info(f'Drone {self.id} on_born')
        self.scene.my_team.append(self)
        self.action = 'Start_atack'

    def on_heartbeat(self):
        if self.health < 30:
            self.action = 'move_to_mathership'
        for d in self.scene.drones:
            if d.gun.cooldown != 0 and d.team != self.team and d.team != self.command_for_attack and d.mothership.is_alive:
                self.point_to_attack_mothership = None
                self.scene.mothership_for_attack = d.team
                self.command_for_attack = self.scene.mothership_for_attack
                self.action = 'get_plase_for_attack_mothership'
        if self.action == 'move_to_mathership' and self.health > 99:
            self.action = 'move_to_plase_for_attack'
        if self.action == 'move_to_plase_for_attack':
            self.move_at(self.point_to_attack_mothership)
        if self.action == 'move_to_mathership':
            self.vector = Vector.from_points(self.coord, self.mothership.coord)
            self.move_at(self.my_mothership)
        if self.action == 'search_obj_with_elerium':
            self.search_obj_with_elerium()
        if self.action == 'load_from':
            self.load_from(self.obj_for_on_load)
        if self.action == 'unload_to':
            self.unload_to(self.mothership)
        if self.action == 'Start_atack':
            self.get_mothership_for_attack()
        if self.action == 'get_plase_for_attack_mothership':
            self.get_plase_for_attack_mothership(self.scene.mothership_for_attack)
        if self.action == 'get_drone_for_attack':
            self.get_drone_for_attack(self.scene.mothership_for_attack)
        if self.action == 'shottt':
            self.shottt(self.gun, self.target_for_attack)

    def search_obj_with_elerium(self):
        motherships_with_elerium = list(obj for obj in self.scene.motherships if obj.payload and obj.team != self.team)
        nearby_motherships_with_elerium = sorted(motherships_with_elerium,
                                                 key=lambda obj: self.distance_to(obj),
                                                 reverse=True)
        if nearby_motherships_with_elerium:
            self.obj_for_on_load = nearby_motherships_with_elerium.pop()
            self.action = 'onload'
            self.move_at(self.obj_for_on_load)
        else:
            drones_with_elerium = list(
                obj for obj in self.scene.drones if obj.payload and obj.team != self.team)
            nearby_drones_with_elerium = sorted(drones_with_elerium,
                                                key=lambda obj: self.distance_to(obj),
                                                reverse=True)
            if nearby_drones_with_elerium:
                self.obj_for_on_load = nearby_drones_with_elerium.pop()
                self.action = 'onload'
                self.move_at(self.obj_for_on_load)

    def on_stop_at_mothership(self, mothership):
        if mothership == self.obj_for_on_load:
            self.action = 'load_from'
        if mothership == self.mothership:
            self.action = 'unload_to'

    def on_load_complete(self):
        self.move_at(self.mothership)

    def on_unload_complete(self):
        self.action = 'search_obj_with_elerium'

    def search_drones_is_alive(self):
        drones_is_alive = list(d for d in self.scene.drones if d.team != self.team and d.is_alive)
        nearby_drones_is_alive = sorted(drones_is_alive, key=lambda d: self.distance_to(d), reverse=True)
        if nearby_drones_is_alive:
            self.nearby_drone_is_alive = nearby_drones_is_alive.pop()

    def shottt(self, gun, target):
        if target.health <= 0:
            self.action = 'get_drone_for_attack'
        self.vector = Vector.from_points(self.coord, target.coord)
        if self.not_shot_on_my_drones():
            self.gun.shot(target)

    def get_mothership_for_attack(self):
        motherships_for_attack = sorted(list(m for m in self.scene.motherships if m.is_alive and m.team != self.team),
                                        key=lambda m: self.mothership.distance_to(m))
        if not motherships_for_attack:
            self.action = 'search_obj_with_elerium'
        else:
            self.scene.mothership_for_attack = motherships_for_attack.pop().team
            self.command_for_attack = self.scene.mothership_for_attack
            self.action = 'get_plase_for_attack_mothership'

    def get_plase_for_attack_mothership(self, mothership):
        if not self.scene.points_to_attack_mothership:
            drones_in_my_team = len(list(d for d in self.scene.drones if d.team == self.team and d.is_alive))
            self.scene.get_coords_for_attak_mothership(drones_in_my_team, mothership)
        if not self.point_to_attack_mothership:
            self.point_to_attack_mothership = self.scene.points_to_attack_mothership.pop()
            self.move_at(self.point_to_attack_mothership)
        self.action = 'move_to_plase_for_attack'

    def on_stop_at_point(self, target):
        if target == self.point_to_attack_mothership:
            if not self.target_for_attack or not self.target_for_attack.is_alive:
                self.get_drone_for_attack(self.scene.mothership_for_attack)
            self.action = 'shottt'

    def on_stop_at_asteroid(self, asteroid):
        if asteroid.near(self.point_to_attack_mothership):
            if not self.target_for_attack or not self.target_for_attack.is_alive:
                self.get_drone_for_attack(self.scene.mothership_for_attack)
            self.action = 'shottt'

    def get_drone_for_attack(self, name_mothership):
        mothership_for_attack = self.scene.get_mothership(name_mothership)
        if not mothership_for_attack.is_alive:
            self.action = 'Start_atack'
        drones_for_attack = list(d for d in self.scene.drones if d.team == mothership_for_attack.team and d.is_alive)
        if drones_for_attack == []:
            if mothership_for_attack.is_alive:
                self.target_for_attack = mothership_for_attack
                self.action = 'shottt'
            else:
                self.point_to_attack_mothership = None
                self.action == 'Start_atack'
        if drones_for_attack:
            drones_in_radius_attack = set(d for d in drones_for_attack if self.distance_to(
                d) <= self.gun.shot_distance and d.is_alive)
            reserved_drones_for_attack = set(d.target_for_attack for d in self.scene.drones if d.team == self.team)
            free = drones_in_radius_attack - reserved_drones_for_attack
            if free:
                sort_to_distance = sorted(free,
                                          key=lambda drone: self.distance_to(drone),
                                          reverse=True)
                self.target_for_attack = sort_to_distance[-1]
                self.action = 'shottt'
            elif drones_in_radius_attack:
                sort_to_distance = sorted(drones_in_radius_attack,
                                          key=lambda drone: self.distance_to(drone),
                                          reverse=True)
                self.target_for_attack = sort_to_distance[-1]
                self.action = 'shottt'

    def not_shot_on_my_drones(self):
        for drone in self.scene.my_team:
            if drone != self and drone.is_alive and self.distance_to(drone) < self.distance_to(
                    self.target_for_attack):
                # точки начала и конца отрезка
                x1, y1 = float(self.x), float(self.y)
                x2, y2 = float(self.target_for_attack.x), float(self.target_for_attack.y)
                # точка центра окружности
                p1, p2 = drone.x, drone.y
                # коэфициенты уравнения прямой
                a = y1 - y2
                b = x2 - x1
                c = (x1 * y2) - (x2 * y1)
                # перпендикуляр от центра окружности к прямой
                d = abs((a * p1) + (b * p2) + c) / pow(a ** 2 + b ** 2, 0.5)
                # если d < радиуса окружности - прямая пересекает окружжность, если равен - косается
                if drone.radius >= d >= 0:
                    self.action = 'get_drone_for_attack'
                    return False
        return True


drone_class = SimonDrone()
