# -*- coding: utf-8 -*-

from astrobox.core import Drone


# Атрибуты дрона / Астероида

# coord - координаты собственного местоположения
# direction - курс корабля
# my_mathership - космобаза приписки
# asteroids - список всех астероидов на поле
# payload - кол-во элериума в трюме
# free_space - свободного места в трюме
# fullness - процент загрузки
# is_empty - трюм пустой
# is_full - трюм полностью забит элериумом


# Методы дрона
# turn_to(obj) - повернуться к объекту/точке
# move_at(obj) - двигаться к объекту/точке
# stop() – остановиться
# load_from(obj) - загрузить элериум от объекта в трюм
# unload_to(obj) - разгрузить элериум из трюма в объект
# distance_to(obj) - рассчет расстояния до объекта/точки
# near(obj) - дрон находится рядом с объектом/точкой


class IshmukhamedovDrone(Drone):
    targets = []
    full_travel = 0
    empty_travel = 0
    underload_travel = 0

    def on_born(self):
        if self._find_the_target():
            self._calculate_statistics(self.target[0])
            self.move_at(self.target[0])

    def _init_targets(self):
        for asteroid in self.asteroids:
            if not asteroid.is_empty:
                self.targets.append([asteroid, True])

    def _check_asteroids(self):
        if self.targets:
            for asteroid in self.targets:
                if asteroid[0].is_empty:
                    self.targets.remove(asteroid)
        else:
            self._init_targets()

    def _calculate_statistics(self, destination):
        if self.is_empty:
            IshmukhamedovDrone.empty_travel += self.distance_to(destination)
        elif self.is_full:
            IshmukhamedovDrone.full_travel += self.distance_to(destination)
        else:
            IshmukhamedovDrone.underload_travel += self.distance_to(destination)

    def get_statistics(self):
        stat = [self.empty_travel, self.full_travel, self.underload_travel]
        return stat

    def _find_the_target(self):
        self._check_asteroids()

        if self.targets:
            for target in self.targets:
                if target[1]:
                    self.target = target
                    break
        else:
            return False

        for asteroid in self.targets:
            if len(self.targets) > 5 and not asteroid[1]:
                continue

            if self.distance_to(self.target[0]) > self.distance_to(asteroid[0]) and asteroid[1]:
                self.target = asteroid

        self.target[1] = False

        return True

    def on_stop_at_asteroid(self, asteroid):

        if asteroid.payload >= self.free_space:
            self.turn_to(self.my_mothership)
        else:
            if self._find_the_target():
                self.turn_to(self.target[0])
            else:
                self.turn_to(self.mothership)

        self.load_from(asteroid)

    def on_load_complete(self):
        if self.target:
            self.target[1] = True

        if self.is_full:
            self._calculate_statistics(self.my_mothership)
            self.move_at(self.my_mothership)
        else:
            if self.target:
                self._calculate_statistics(self.target[0])
                self.move_at(self.target[0])
            else:
                self._calculate_statistics(self.my_mothership)
                self.move_at(self.my_mothership)

    def on_stop_at_mothership(self, mothership):
        if self._find_the_target():
            self.turn_to(self.target[0])
        else:
            self.target = []

        self.unload_to(mothership)

    def on_unload_complete(self):
        if self.target:
            self._calculate_statistics(self.target[0])
            self.move_at(self.target[0])
        else:
            self.stop()

    def on_wake_up(self):
        if self._find_the_target():
            self._calculate_statistics(self.target[0])
            self.move_at(self.target[0])
        else:
            if self.distance_to(self.my_mothership) == 0:
                self.stop()
            else:
                self._calculate_statistics(self.my_mothership)
                self.move_at(self.my_mothership)


drone_class = IshmukhamedovDrone
