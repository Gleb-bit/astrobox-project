# -*- coding: utf-8 -*-

from astrobox.core import Drone
from robogame_engine.geometry import Point
from robogame_engine.theme import theme

INDENT = 100
MIN_INDENT = 80
MIN_HEALTH = 70

HORIZONTAL_INDENT = theme.FIELD_WIDTH // 4


class SmirnovDrone(Drone):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # self.x_coord = HORIZONTAL_INDENT + random.randint(-INDENT, INDENT)
        self.x_coord = HORIZONTAL_INDENT
        self.y_coord = MIN_INDENT * (self._get_self_index() + 2) - 50
        self.point = Point(self.x_coord, self.y_coord)
        self.position = []

    # Главный метод
    def on_hearbeat(self):
        enemies = self.get_enemies()

        if self.position and self.position[0] == 'move_at':
            pass
        else:
            if self._check_health():
                if len(enemies) > 0:
                    if self.position and (self.position[0] == 'on_stop' or self.position[0] == 'on_wake_up'):
                        if len(enemies) < 3 and self.x < theme.FIELD_WIDTH // 2:
                            self.point = Point(x=theme.FIELD_WIDTH // 2, y=self.coord.y)
                            self._change_position_center()
                        elif len(enemies) == 1 and self.x > theme.FIELD_WIDTH // 2:
                            self._check_shoot_enemy(enemies[0])
                        else:
                            self._check_shoot_enemy(enemies[0])
                else:
                    self.position = ['move_at', Point(self.x, self.y)]

            else:
                self.move_at(self.mothership)

    # Вспомогательные методы
    def _check_health(self):
        return self.health > MIN_HEALTH

    def _change_position_center(self):
        self.point = Point(x=theme.FIELD_WIDTH // 2, y=self.coord.y)
        self.move_at(self.point)

    def _check_shoot_enemy(self, target):
        if self._check_health():
            self.turn_to(target)
            self.gun.shot(target)
        else:
            self.move_at(self.mothership)

    def _get_enemy_count(self):
        return len(self.get_enemies())

    def _check_enemy_count(self):
        return len(self.get_enemies()) > 1

    def _get_self_index(self):
        return self.scene.drones.index(self)

    def _is_near(self, target):
        return self.distance_to(target) < theme.FIELD_WIDTH // 2

    def _move_at_closest_asteroid(self, closest_asteroid):
        if closest_asteroid:
            self.move_at(closest_asteroid)
        else:
            self.move_at(self.mothership)

    # Основные методы

    def on_born(self):
        enemies = self.get_enemies()
        closest_asteroid = self.get_closest_asteroid()

        if enemies:
            self.move_at(self.point)
        elif closest_asteroid:
            self._move_at_closest_asteroid(closest_asteroid)
        else:
            self.stop()

    def on_stop(self):
        enemies = self.get_enemies()
        if self._get_self_index() != 0:
            self.position = ['on_stop', Point(self.x, self.y)]
            if enemies:
                if len(enemies) > 0:
                    self._check_shoot_enemy(enemies[0])
                else:
                    closest_asteroid = self.get_closest_asteroid()
                    self._move_at_closest_asteroid(closest_asteroid)
            else:
                closest_asteroid = self.get_closest_asteroid()
                self._move_at_closest_asteroid(closest_asteroid)
        else:
            self.position = ['move_at', Point(self.x, self.y)]
            closest_asteroid = self.get_closest_asteroid()
            self._move_at_closest_asteroid(closest_asteroid)

    def on_wake_up(self):
        self.position = ['on_wake_up', Point(self.x, self.y)]

    def get_closest_asteroid(self):
        empty_asteroids = [asteroid for asteroid in self.asteroids if asteroid.cargo.payload > 0]
        empty_asteroids.sort(key=lambda u: u.distance_to(self))
        index = self.scene.drones.index(self)
        if not empty_asteroids:
            return False
        if index > len(empty_asteroids) - 1:
            index = 0
        return empty_asteroids[index]

    def get_enemies(self):
        enemies = [drone for drone in self.scene.drones if self.team != drone.team and drone.is_alive]
        enemies.sort(key=lambda x: x.distance_to(self))
        return enemies

    def on_stop_at_asteroid(self, asteroid):
        if self._get_self_index() != 0:
            enemies = self.get_enemies()
            if len(enemies) == 0:
                self.position = ['on_stop_at_asteroid', Point(self.x, self.y)]
                self.load_from(asteroid)
                closest_asteroid = self.get_closest_asteroid()
                if closest_asteroid and self._check_health():
                    self.turn_to(closest_asteroid)
                    self.move_at(closest_asteroid)
                else:
                    self.turn_to(self.mothership)
                    self.move_at(self.mothership)
            else:
                self.point = Point(self.x - 50, self.y)
                self.move_at(self.point)
        else:
            self.load_from(asteroid)

    def on_load_complete(self):
        if not self.is_full and self._check_health():
            closest_asteroid = self.get_closest_asteroid()
            self._move_at_closest_asteroid(closest_asteroid)
        else:
            self.move_at(self.my_mothership)

    def on_stop_at_mothership(self, mother_ship):
        if not self.is_empty:
            self.unload_to(mother_ship)
        else:
            self.on_born()

    def on_unload_complete(self):
        if self._get_self_index() != 0:
            self.on_born()
        else:
            closest_asteroid = self.get_closest_asteroid()
            self._move_at_closest_asteroid(closest_asteroid)


drone_class = SmirnovDrone 
