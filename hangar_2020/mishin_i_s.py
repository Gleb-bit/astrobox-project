from astrobox.core import Drone
from robogame_engine.geometry import Point
from math import degrees, atan, cos, radians, sin, fabs


START_COORDS = [[Point(80, 280), Point(150, 270), Point(225, 225), Point(270, 150), Point(280, 80)],
                [Point(1120, 280), Point(1050, 270), Point(975, 225), Point(930, 150), Point(920, 80)],
                [Point(80, 920), Point(150, 930), Point(225, 975), Point(270, 1050), Point(280, 1120)],
                [Point(1120, 920), Point(1050, 930), Point(975, 975), Point(930, 1050), Point(920, 1120)]]

MOTHERSHIP_ATTACK_COORDS = [[[Point(820, 370), Point(740, 290), Point(660, 210), Point(580, 130), Point(600, 50)],
                             [Point(50, 600), Point(130, 580), Point(210, 660), Point(290, 740), Point(370, 820)],
                             [Point(800, 1020), Point(830, 940), Point(860, 860), Point(940, 830), Point(1020, 800)]],
                            [[Point(380, 370), Point(460, 290), Point(540, 210), Point(620, 130), Point(600, 50)],
                             [Point(400, 1020), Point(370, 940), Point(340, 860), Point(260, 830), Point(180, 800)],
                             [Point(1150, 600), Point(1070, 580), Point(990, 660), Point(910, 740), Point(830, 820)]],
                            [[Point(50, 600), Point(130, 620), Point(210, 540), Point(290, 460), Point(370, 380)],
                             [Point(800, 180), Point(830, 260), Point(860, 340), Point(940, 370), Point(1020, 400)],
                             [Point(820, 830), Point(740, 910), Point(660, 990), Point(580, 1070), Point(600, 1150)]],
                            [[Point(400, 180), Point(370, 260), Point(340, 340), Point(260, 370), Point(180, 400)],
                             [Point(1150, 600), Point(1070, 620), Point(990, 540), Point(910, 460), Point(830, 380)],
                             [Point(380, 830), Point(460, 910), Point(540, 990), Point(620, 1070), Point(600, 1150)]]]


class MishinDrone(Drone):
    """
    Автор логики дронов: Мишин Иван

    Краткое описание логики дронов:
      Первый этап - построение дронов в дугу вокруг базы так, чтоюы друг друга не перекрывать, но быть в зоне хила базы
      Второй этап - отстрел подлетающих к дрону на дистанцию выстрела противников и баз, которые находятся в зоне
    досягаемости снаряда
      Третий этап - 'охота' за противниками и базами, которые находятся вне досягаемости снаряда
      Четвёртый этап - сбор всего Элериума с астероидов
      Пятый этап - сбор Элериума с уничтоженных баз
      Шестой этап - вывод статистики полётов дронов
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.number = self.id - 5 * (self.team_number - 1) - 1
        self.statistics = {'number': self.number+1, 'full': 0, 'half-full': 0, 'empty': 0}
        self.drone_count = None
        self.sorted_asteroids = None
        self.asteroids_count = None
        self.team_quantity = None
        self.role = 'battle'
        self.shots_count = 0
        self.near_asteroids = None
        self.harvested = False

    # - - - - - Переопределение родительских методов - - - - - #

    def move_at(self, target, speed=None):
        """
        Метод переопределён для упрощения заполнения self.statistics
        """
        self.statistics[target[0]] += round(self.distance_to(target[1]))
        super().move_at(target[1])

    # - - - - - Вспомогательные функции - - - - - #

    def _move_by_direction(self, x, y, target_x, target_y, distance):
        """
        Передвижение в определённую точку по заданным координатам направления
        :param x: текущая абсцисса дрона
        :param y: текущая ордината дрона
        :param target_x: абсцисса цели
        :param target_y: ордината цели
        :param distance: расстояние, на которое нужно передвинуться
        """
        angle = degrees(atan((target_y - y) / (target_x - x)))
        if target_x < x:
            new_x = x - distance * cos(radians(angle))
        else:
            new_x = x + distance * cos(radians(angle))
        if target_y > y and angle < 0 or target_y < y and angle > 0:
            new_y = y - distance * sin(radians(angle))
        else:
            new_y = y + distance * sin(radians(angle))
        self.move_at(['empty', Point(new_x, new_y)])

    # - - - - - - - - - - События - - - - - - - - - - #

    def on_born(self):
        self.drone_count = len(self.teammates) + 1
        self.team_quantity = max([drone.team_number for drone in self.scene.drones])
        if self.number == 2:
            self.near_asteroids = [asteroid for asteroid in self.asteroids if self.distance_to(asteroid) < 200]
            if self.near_asteroids:
                self.near_asteroids.sort(key=lambda x: self.distance_to(x))
                self.role = 'harvest near'
                self.move_at(['empty', self.near_asteroids[0]])
            else:
                self._arrangement_for_battle()
        else:
            self._arrangement_for_battle()

    def on_load_complete(self):
        if self.role == 'harvest near':
            if not self.near_asteroids[0].payload:
                self.near_asteroids.pop(0)
            if not self.is_full and self.near_asteroids:
                self.move_at(['half-full', self.near_asteroids[0]])
            elif not self.is_full:
                self.move_at(['half-full', self.my_mothership])
            else:
                self.move_at(['full', self.my_mothership])
            return
        if self.health < 50 or self.is_full:
            self.move_at(['full', self.my_mothership])
        else:
            self.move_at(['half-full', self._choose_next_asteroid()])

    def on_unload_complete(self):
        if self.role == 'harvest near':
            if self.near_asteroids:
                self.move_at(['empty', self.near_asteroids[0]])
            else:
                self.role = 'battle'
                self._arrangement_for_battle()
        else:
            target = self._check_available_asteroids()
            if target:
                self.move_at(['empty', target])
            else:
                print(self.statistics)

    def on_stop_at_point(self, target):
        if self.role == 'battle' or self.role == 'attack mothership':
            self._battle()

    def on_stop_at_mothership(self, mothership):
        if mothership == self.my_mothership:
            self.on_stop_at_my_mothership(mothership)
        else:
            self.load_from(mothership)

    def on_stop_at_my_mothership(self, mothership):
        if self.role == 'battle':
            self._arrangement_for_battle()
            return
        if self.role == 'attack mothership':
            self._battle()
            return
        if self.role == 'switch to harvest near':
            self._switch_to_harvest_near()
            return
        self.unload_to(mothership)
        if self.role == 'harvest':
            next_target = self._check_available_asteroids()
            if next_target:
                self.turn_to(next_target)
            else:
                print(self.statistics)

    def on_stop_at_asteroid(self, asteroid):
        if self.role == 'battle' or self.role == 'attack mothership':
            self._battle()
            return
        self.load_from(asteroid)
        if asteroid.payload >= 100 or self.role == 'harvest near':
            self.turn_to(self.my_mothership)
        else:
            self.turn_to(self._choose_next_asteroid())

    # - - - - - - - - - - Сражение - - - - - - - - - - #

    def _arrangement_for_battle(self):
        """
        Расстановка дронов перед сражением
        """
        self.move_at(['empty', START_COORDS[self.team_number - 1][self.number]])

    def _arrangement_to_attack_mothership(self, mothership):
        """
        Расстановка дронов для растрела чужих баз
        """
        if self.team_number < mothership.team_number:
            self.move_at(['empty',
                          MOTHERSHIP_ATTACK_COORDS[self.team_number - 1][mothership.team_number - 2][self.number]])
        else:
            self.move_at(['empty',
                          MOTHERSHIP_ATTACK_COORDS[self.team_number - 1][mothership.team_number - 1][self.number]])

    def _battle(self):
        """
        Логика дрона во время битвы
        """
        if self.health < 50:
            self.move_at(['empty', self.my_mothership])
            return
        target, any_targets = self._check_nearest_enemy()
        if self.number == 2:
            for teammate in self.teammates:
                is_teammate_at_base = fabs(teammate.x - START_COORDS[self.team_number - 1][teammate.number].x) > 50 or\
                                      fabs(teammate.y - START_COORDS[self.team_number - 1][teammate.number].y) > 50
                if is_teammate_at_base and not self.harvested:
                    self.role = 'switch to harvest near'
                    self.move_at(['empty', self.my_mothership])
                    return
        if any_targets:
            self._shot(target)
        else:
            self.role = 'harvest'
            self.move_at(['empty', self._choose_first_asteroid()])

    def _check_nearest_enemy(self):
        """
        Проверка на ближайщего противника или базу
        """
        enemies = [drone for drone in self.scene.drones if
                   self.team != drone.team and drone.is_alive]
        enemies.extend([mothership for mothership in self.scene.motherships
                        if mothership.is_alive and mothership != self.my_mothership])
        enemies.sort(key=lambda x: self.distance_to(x))
        if enemies:
            if 6 > len(enemies) >= 2 and enemies[0] in self.scene.drones and enemies[1] in self.scene.motherships:
                return enemies[1], True
            elif len(enemies) >= 2 and enemies[1] in self.scene.drones and not enemies[1].my_mothership.is_alive:
                return enemies[1], True
            else:
                return enemies[0], True
        else:
            return None, False

    def _shot(self, target):
        """
        Выстрел по цели и передвижение чуть вперёд
        :param target: цель, по которой нужно выстрелить
        """
        self.gun.shot(target)
        self.shots_count += 1
        if target in self.scene.motherships and self.distance_to(target) > self.gun.projectile.max_distance and\
                self.shots_count > 800:
            self._arrangement_to_attack_mothership(target)
        elif self.distance_to(target) > self.gun.projectile.max_distance and self.shots_count > 800:
            self._move_by_direction(self.coord.x, self.coord.y, target.x, target.y, 10)
        else:
            self._move_by_direction(self.coord.x, self.coord.y, target.x, target.y, 0.0001)

    # - - - - - - - - - - Сбор Элериума - - - - - - - - - - #

    def _switch_to_harvest_near(self):
        """
        Переход на сбор элериума вместо сражения для дрона с self.number == 2
        """
        self.near_asteroids = [asteroid for asteroid in self.asteroids if self.distance_to(asteroid) < 500 and
                               asteroid.payload]
        if self.near_asteroids:
            self.near_asteroids.sort(key=lambda x: self.distance_to(x))
            self.harvested = True
            self.role = 'harvest near'
            self.move_at(['empty', self.near_asteroids[0]])

    def _choose_first_asteroid(self):
        """
        Выбор самого первого астероида для полёта; вызывается после окончания сражения
        """
        self.sorted_asteroids = sorted(self.asteroids, key=lambda x: self.distance_to(x))
        self.asteroids_count = len(self.sorted_asteroids)
        target = self.sorted_asteroids[self.asteroids_count // 2 - self.drone_count // 2 + self.number - 2]
        return target

    def _choose_next_asteroid(self):
        """
        Выбор следующего астероида, если сейчас в кузове меньше 100 Элериума
        """
        distances = [[asteroid, self.distance_to(asteroid)] for asteroid in self.asteroids if asteroid.payload]
        distances.sort(key=lambda x: x[1])
        if len(distances):
            return distances[0][0]
        else:
            return self.my_mothership

    def _check_available_asteroids(self):
        """
        Проверка астероидов на наличие в них элериума
        """
        for asteroid in self.sorted_asteroids:
            if asteroid.payload:
                return asteroid
        else:
            return self._check_enemy_motherships_fullness()

    def _check_enemy_motherships_fullness(self):
        """
        Проверка чужих баз на наличие в них Элериума
        """
        for mothership in self.scene.motherships:
            if mothership.payload and mothership != self.my_mothership:
                return mothership


drone_class = MishinDrone
