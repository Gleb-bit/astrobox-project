# -*- coding: utf-8 -*-

from astrobox.core import Drone
from robogame_engine import GameObject
from robogame_engine.geometry import Point


class DeusDrone(Drone):
    actions = []
    headquarters = None
    attack_range = 0
    limit_health = 0.5
    cost_forpost = 0
    role = None

    def registration(self):
        pass

    def born_soldier(self):
        pass

    def next_action(self):
        pass

    def move_to(self, object):
        pass

    def move_to_step(self, object):
        pass

    def shoot(self, object):
        pass

    def add_attack(self, purpose):
        pass

    def validate_place(self, point: Point):
        pass

    def save_distance(self):
        pass

    def get_angle(self, partner: GameObject, target: GameObject):
        pass

    def add_basa(self, basa):
        pass

    def asteroid_is_free(self, asteroid):
        pass

    def asteroids_for_basa(self):
        pass
