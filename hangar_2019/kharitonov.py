# -*- coding: utf-8 -*-

from astrobox.core import Drone


log_dict = {
    'Distance_empty': 0,
    'Distance_not_full': 0,
    'Distance_full': 0
}

_targets = {}


class KharitonovDrone(Drone):
    my_team = []

    def on_born(self):
        self.target = self.get_nearest_unit()
        _targets[self.id] = self.target

        log_dict['Distance_empty'] += self.distance_to(self.target)
        self.move_at(self.target)
        self.my_team.append(self)

    def get_nearest_unit(self):
        func = lambda u: not u.is_empty
        units = [a for a in self.asteroids if func(a)]
        units.sort(key=lambda u: u.distance_to(self))

        for u in units:
            if u in _targets.values():
                continue
            return u
        return self.mothership

    def on_stop_at_asteroid(self, asteroid):
        if asteroid.cargo.payload > self.cargo.payload:
            self.turn_to(self.mothership)
        else:
            nearest_object = self.get_nearest_unit()
            self.turn_to(nearest_object)
        self.load_from(asteroid)

    def on_load_complete(self):
        if self.is_full:
            self.move_at(self.my_mothership)
            _targets[self.id] = None
            log_dict['Distance_full'] += self.distance_to(self.target)
        else:

            self.target = self.get_nearest_unit()
            _targets[self.id] = self.target
            log_dict['Distance_not_full'] += self.distance_to(self.target)

            self.move_at(self.target)

    def on_stop_at_mothership(self, mothership):
        nearest_object = self.get_nearest_unit()
        self.turn_to(nearest_object)
        self.unload_to(mothership)

    def collected_all_resources(self):
        for item in self.teammates:
            if item.is_moving:
                return False
        return True

    @staticmethod
    def print_statistic():
        print('Дистанция, пройденная пустым дроном', log_dict['Distance_empty'])
        print('Дистанция, пройденная не пустым дроном:', log_dict['Distance_not_full'])
        print('Дистанция, пройденная полным дроном:', log_dict['Distance_full'])

    def on_unload_complete(self):
        self.target = self.get_nearest_unit()
        if self.target is not self.mothership:
            log_dict['Distance_empty'] += self.distance_to(self.target)
            self.move_at(self.target)
            _targets[self.id] = self.target
        elif self.collected_all_resources():
            self.print_statistic()

    def on_wake_up(self):
        self.target = self.get_nearest_unit()
        if self.target:
            self.move_at(self.target)
            _targets[self.id] = self.target


drone_class = KharitonovDrone
