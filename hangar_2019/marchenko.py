# -*- coding: utf-8 -*-
import random
from astrobox.core import Drone


class MarchenkoDron(Drone):

    def __init__(self):
        super().__init__()

        self.fully_loaded = 0
        self.completely_empty = 0
        self.almost_fully_loaded = 0

        self.old_x = 90.0
        self.old_y = 90.0

        self.all_way = 0

    def statistic(self):
        print(f'{self.__class__.__name__} {self.id}:\n'
              f'\tfully_loaded - {self.fully_loaded}\n'
              f'\tcompletely_empty - {self.completely_empty}\n'
              f'\talmost_fully_loaded - {self.almost_fully_loaded}\n'
              f'\tall_way - {self.all_way}', flush=True)

    def calculation_of_way(self):
        if self.x != self.old_x:
            x = max(self.x, self.old_x) - min(self.x, self.old_x)
            if self.y != self.old_y:
                y = max(self.y, self.old_y) - min(self.y, self.old_y)
                result = (x ** 2 + y ** 2) ** 0.5
            else:
                result = self.x
        else:
            result = self.x

        return result

    def add_to_desired(self, way):
        if self.is_full:
            self.fully_loaded += way
        elif self.is_empty:
            self.completely_empty += way
        else:
            self.almost_fully_loaded += way

        self.all_way += way

    def on_born(self):
        self.passive_asteroids = []
        self.active_asteroids = self.asteroids
        self.move_at(random.choice(self.active_asteroids))

    def on_stop_at_asteroid(self, asteroid):
        way = self.calculation_of_way()
        self.add_to_desired(way=way)
        self.asteroid = asteroid
        self.load_from(asteroid)

    def on_load_complete(self):
        if self.payload < 90:
            self.passive_asteroids.append(self.asteroid)
            self.active_asteroids.remove(self.asteroid)
            if len(self.active_asteroids) < 1:
                self.move_at(self.my_mothership)
            else:
                self.move_at(random.choice(self.active_asteroids))
        else:
            self.move_at(self.my_mothership)

    def on_stop_at_mothership(self, mothership):
        way = self.calculation_of_way()
        self.add_to_desired(way=way)
        self.unload_to(mothership)

    def on_stop_at_point(self, target):
        way = self.calculation_of_way()
        self.add_to_desired(way=way)
        self.move_at(target)

    def on_unload_complete(self):
        way = self.calculation_of_way()
        self.add_to_desired(way=way)
        if len(self.active_asteroids) < 1:
            self.stop()
        else:
            self.move_at(self.asteroid)


drone_class = MarchenkoDron
