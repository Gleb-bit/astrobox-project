import itertools
import random
from math import cos, sin, radians

from astrobox.core import Drone, MotherShip
from robogame_engine import scene
from robogame_engine.geometry import Point, Vector
from robogame_engine.theme import theme


class ZaikinDrone(Drone):
    field = scene.theme.FIELD_WIDTH, scene.theme.FIELD_HEIGHT
    center_map = Point(x=round(int(field[0] // 2)),
                       y=round(int(field[1] // 2)))
    drones = list()
    quantity_elerium = 0
    enemies = list()
    count_drone_in_team = 0
    vector = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_target = None
        self.range_not_loader = 0
        self.range_half_fullness = 0
        self.range_fullness = 0
        self.enemy = None
        self.is_gun = False

    # astrobox
    def on_born(self):
        pass
        # Добавляем дрона в список дронов
        ZaikinDrone.drones.append(self)
        self.count_drone_in_team = len(
            self.scene.drones) // self.scene.teams_count
        # Добавляем количество элериума
        if not ZaikinDrone.quantity_elerium:
            ZaikinDrone.quantity_elerium = sum(
                [asteroid.payload for asteroid in self.asteroids])
        # Если есть оружие у дронов
        if self.have_gun:
            # Дрон является атакующим
            # Сделать шаг вперёд
            self.step_forward()
        else:
            self.current_target = self.next_asteroid_for_loader()
            self.move_to(target=self.current_target)

    # astrobox
    def on_stop_at_asteroid(self, asteroid):
        if self.is_gun:
            self.find_nearest_target()
        elif not self.is_full and not asteroid.is_empty:
            self.load_from(source=asteroid)
        else:
            self.move_to(self.my_mothership)

    # astrobox
    def on_load_complete(self):
        # Если не полный и есть астеройды с элериумом, то выключаем
        # пушки и летим собирать.
        if not self.is_full and \
                any([not asteroid.is_empty for asteroid in self.asteroids]):
            self.is_gun = False
            self.current_target = self.next_asteroid_for_loader()
            self.move_to(self.current_target)
        # Если не полный и есть оружие
        elif not self.is_full and self.have_gun:
            self.is_gun = True
            self.current_target = self.next_asteroid_for_loader()
            self.move_to(self.current_target)
        elif self.is_full:
            self.is_gun = False
            self.move_to(self.my_mothership)

    def on_stop_at_point(self, target):
        if self.is_gun:
            self.find_nearest_target()

    def move_to(self, target):
        if isinstance(target, Point):
            coord = target
        else:
            coord = target.coord
        self.vector = Vector.from_points(self.coord, coord, module=0.1)
        self.move_at(target)

    # astrobox
    def on_stop(self):
        if self.is_gun is False:
            self.current_target = self.next_asteroid_for_loader()
            self.move_to(target=self.current_target)
            return
        if not self.validate_direction():
            self.move_to(self.current_target)
            return
        self.gun.shot(self.enemy)
        if self.checking_enemy_mothership():
            self.move_to(self.current_target)
            return
        if self.check_health():
            self.move_to(self.current_target)
            return
        if self.distance_to(self.my_mothership) < 100:
            self.current_target = self.pursue()
            self.move_to(self.current_target)
            return
        self.find_nearest_target()

    # astrobox
    def on_stop_at_mothership(self, mothership):
        self.unload_to(target=mothership)
        if mothership != self.mothership and not mothership.is_alive:
            self.load_from(mothership)
            self.current_target = mothership
            return
        if self.is_gun:
            self.find_nearest_target()
            return

    # astrobox
    def on_unload_complete(self):
        if isinstance(self.current_target, MotherShip) and \
                self.my_mothership != self.current_target and \
                not self.current_target.is_empty:
            self.move_to(target=self.current_target)
            return

        if any([not asteroid.is_empty for asteroid in self.asteroids]):
            self.current_target = self.next_asteroid_for_loader()
            self.move_to(target=self.current_target)
            return

        if isinstance(self.current_target, MotherShip) and \
                self.current_target.is_empty:
            self.find_nearest_target()
            return

        self.step_forward()

    def next_asteroid_for_loader(self):
        next_asteroid = self.min_vector_to_asteroid()
        return next_asteroid

    def min_vector_to_asteroid(self):
        asters = self.asteroids
        dead_drone = [drone for drone in self.scene.drones if
                      not drone.is_alive and drone.payload > 0]
        asters.extend(dead_drone)
        sorted_asteroids = sorted(self.asteroids,
                                  key=lambda asteroid: self.distance_to(
                                      asteroid))
        direction_drones = [drone.current_target for drone in self.drones]
        asteroids = [asteroid for asteroid in sorted_asteroids if
                     not asteroid.is_empty]

        not_busy_asteroids = [asteroid for asteroid in asteroids if
                              asteroid not in direction_drones]

        if not_busy_asteroids:
            return not_busy_asteroids[0]
        if asteroids:
            return asteroids[0]
        else:
            return self.my_mothership

    def add_enemies_drones(self):
        if not ZaikinDrone.enemies:
            for drone in self.scene.drones:
                if drone not in self.drones:
                    ZaikinDrone.enemies.append(drone)

    # Поиск --------------------------------------
    def find_nearest_target(self):
        self.add_enemies_drones()
        # Живые враги вне базы
        alive_drones_outside_mothership = self.find_enemy_drones(outside=True)
        # Ближайщий враг, пока None
        nearest_enemy = None
        # Если есть живые враги вне базы

        if alive_drones_outside_mothership:
            # Сортируем дроны по дистанции
            alive_drones_outside_mothership.sort(key=lambda x: x[0])
            # Выбираем ближайщего дрона для атаки.
            nearest_enemy = alive_drones_outside_mothership[0][1]
        else:
            # Ищем живых ВСЕХ живых дронов
            alive_drones = self.find_enemy_drones()
            # Если есть хоть один живой дрон
            if alive_drones:
                # Сортируем дроны по дистанции
                alive_drones.sort(key=lambda x: x[0])
                # Выбираем ближайщего дрона для атаки.
                nearest_enemy = alive_drones[0][1]

        # Если есть враг, то атакуем
        if not nearest_enemy:
            if (all([not enemy.is_alive for enemy in self.enemies]) and
                    any([not aster.is_empty for aster in self.asteroids])):
                my_drones = [dr for dr in self.drones if dr.is_alive]
                for dr in my_drones[:2]:
                    dr.is_gun = False

            motherships = [(moth, moth.payload)
                           for moth in self.scene.motherships
                           if moth != self.my_mothership and moth.is_alive]
            if motherships:
                motherships.sort(key=lambda x: x[1])
                nearest_enemy = motherships[0][0]
            else:
                nearest_enemy = self.my_mothership
                self.is_gun = False
        self.enemy = nearest_enemy
        self.vector = Vector.from_points(self.coord, self.enemy.coord,
                                         module=0.1)
        self.turn_to(self.enemy)

    def get_objects_with_elerium(self) -> list:
        """
        Получить все объекты с элериумом, кроме баз
        :return:
        """
        asteroids = [aster for aster in self.scene.asteroids if aster.payload > 0]
        asteroids.extend([drone for drone in self.scene.drones if drone.payload > 0])

        return asteroids

    def find_enemy_drones(self, outside=False) -> list:
        """
        Если outside==True, то происходит поиск живых дронов, которые
        находятся вне своей базы.
        Иначе поиск живых дронов
        :return: Список кортежов. Пример [(Дистанция до дрона, Дрон)]
        """
        enemy_drones = [drone for drone in self.scene.drones if
                        drone not in self.drones]
        if outside:
            drones = [(self.distance_to(drone), drone)
                      for drone in enemy_drones
                      if drone.is_alive and
                      not drone.near(drone.my_mothership) and
                      drone.my_mothership.is_alive and
                      drone.distance_to(drone.my_mothership) > 200]
        else:
            drones = [(self.distance_to(drone), drone)
                      for drone in enemy_drones
                      if drone.is_alive ]

        return drones

    def find_point_for_shot(self) -> Point:
        self_x, self_y = self.coord.x, self.coord.y
        enemy_x, enemy_y = self.enemy.coord.x, self.enemy.coord.y
        difference_x = abs(self_x - enemy_x)
        difference_y = abs(self_y - enemy_y)
        new_x = min([self_x, enemy_x]) + difference_x / 3
        new_y = min([self_y, enemy_y]) + difference_y / 3
        point_for_shot = self.new_point(x=new_x, y=new_y)
        return point_for_shot

    # Проверки --------------------------------------
    def checking_enemy_mothership(self):
        if self.find_enemy_drones(outside=True):
            return False
        for mothership in self.scene.motherships:
            if mothership.is_alive or mothership == self.my_mothership:
                continue
            enemy_drones_for_mothership = [enemy for enemy in self.enemies if
                                           enemy.my_mothership == mothership]
            if not mothership.is_empty:
                if all([not drone.is_alive for drone in
                        enemy_drones_for_mothership]):
                    self.current_target = mothership
                    return True
        return False

    def checking_die_enemy_with_elerium(self):
        for drone in self.scene.drones:
            if not drone.is_empty and not drone.is_alive:
                if any([my_drone.current_target == Point(drone.coord.x,
                                                         drone.coord.y) for
                        my_drone in self.drones]):
                    return False
                else:
                    self.enemy = drone
                    self.current_target = Point(drone.coord.x, drone.coord.y)
                    self.move_to(self.current_target)
                return True
        return False

    def check_health(self):
        if self.meter_2 < 0.5:
            self.current_target = self.my_mothership
            return True
        return False

    def create_point_for_my_drone(self):
        radius = 300
        if self.enemy is not None:
            enemy_mothership = self.enemy.my_mothership
        else:
            return False
        if self.enemy.near(enemy_mothership):
            if enemy_mothership.coord.y == self.my_mothership.coord.y:
                index_drone = self.drones.index(self) + 1
                angel = 90 // len(self.drones) * index_drone
                coord_x = enemy_mothership.coord.x - radius * cos(
                    radians(angel))
                coord_y = radius * sin(
                    radians(angel)) + enemy_mothership.coord.y
                if self.is_alive:
                    self.current_target = Point(coord_x, coord_y)
                return True
        return False

    def step_forward(self):
        """
        Каждый дрон вначале делает шаг вперед на расстояние 150.
        :return:
        """
        self.is_gun = True

        self.vector = Vector.from_points(self.coord, self.center_map,
                                         module=0.1)

        radius = 220 + self.drones.index(self) * 30
        # # Получить углы для шага
        angels = self.get_angels(self.my_mothership)
        a, b = self.my_mothership.coord.x, self.my_mothership.coord.y,

        self.current_target = self.get_point_for_move(angels, a, b, radius)
        self.move_to(self.current_target)

    def get_point_for_move(self, angels, a, b, radius):
        x = self.get_value_from_formula(angels=angels,
                                        radius=radius,
                                        coord=a,
                                        x=True)
        y = self.get_value_from_formula(angels=angels,
                                        radius=radius,
                                        coord=b,
                                        x=False)
        return Point(x=x, y=y)

    def new_point(self, x, y) -> Point:
        angels = self.get_angels(self.enemy)
        radius = 100
        if not self.validate_near_drone(radius, x, y):
            x += random.choice([-radius, radius])
            y += random.choice([-radius * 2, radius * 2])
        if self.validate_point(x, y):
            point = Point(
                round(int(x + Vector.to_radian(angels[self.drones.index(self)]))),
                round(int(y + Vector.to_radian(angels[self.drones.index(self)]))),
            )
        else:
            point = self.pursue()
        return point

    def get_angels(self, target) -> list:
        """
        Получить углы по которым нужно построиться в полукруг
        :param target: Drone, MotherShip
        :return: Список углов
        """
        half_width = theme.FIELD_WIDTH / 2
        half_height = theme.FIELD_HEIGHT / 2
        if target.coord.x <= half_width and target.coord.y <= half_height:
            angels = [angel for angel in
                      range(0, 91, 90 // self.count_drone_in_team)]
        elif target.coord.x <= half_width and target.coord.y >= half_height:
            angels = [angel for angel in
                      range(270, 361, 90 // self.count_drone_in_team)]
        elif target.coord.x >= half_width and target.coord.y >= half_height:
            angels = [angel for angel in
                      range(180, 271, 90 // self.count_drone_in_team)]
        else:
            angels = [angel for angel in
                      range(90, 181, 90 // self.count_drone_in_team)]

        return angels

    def get_value_from_formula(self, angels: list, radius: int, coord, x=True):
        self_index = ZaikinDrone.drones.index(self)
        if x and (0 in angels or 360 in angels):
            return radius * cos(radians(angels[self_index])) + coord
        elif x and 180 in angels:
            return coord - abs(radius * cos(radians(angels[self_index])))

        if not x and 90 in angels:
            return radius * sin(radians(angels[self_index])) + coord
        elif not x and 270 in angels:
            return coord - abs(radius * sin(radians(angels[self_index])))

    def pursue(self):
        """Двигаемся немного вперед к цели"""
        vec2 = Vector.from_direction(round(self.direction), 30)
        new_coord = Point(
            x=round(int(self.x + vec2.x)),
            y=round(int(self.y + vec2.y))
        )
        return new_coord

    # Валидация ----------------------------------
    def validate_direction(self):
        if self.enemy is None:
            return True
        if self.distance_to(self.enemy) > self.gun.shot_distance - 50:
            self.current_target = self.pursue()
            return False

        if any([self.near(moth) for moth in self.scene.motherships]):
            self.current_target = self.find_point_for_shot()
            return False

        if self.enemy.near(self):
            return True

        if not isinstance(self.enemy, MotherShip) and \
                self.enemy.distance_to(self.enemy.my_mothership) < 200:
            self.current_target = self.find_point_for_shot()
            return False

        vec = Vector.from_points(self.coord, self.enemy.coord, module=self.gun.shot_distance)
        the_bullet_will_reach = Point(x=int(self.coord.x + vec.x),
                                      y=int(self.coord.y + vec.y))
        for teammate in self.teammates:
            coord_1 = [[60, -60], [-60, 60], [20, -100], [-20, 100], [50, 100],
                       [-50, -100]]
            coord_2 = [[70, -70], [-70, 50], [-70, 100], [50, 100], [-50, 100],
                       [50, -100]]
            new_coord = [Point(x=round(int(teammate.coord.x + coord[0])),
                               y=round(int(teammate.coord.y + coord[1])))
                         for coord in coord_1]
            new_coord.extend([Point(x=round(int(self.coord.x + coord[0])),
                                    y=round(int(self.coord.y + coord[1])))
                              for coord in coord_2])
            if self.distance_to(self.enemy) < self.distance_to(
                    the_bullet_will_reach):
                step_x = (abs(self.enemy.x) - abs(self.coord.x)) / 10
                step_y = (abs(self.enemy.y) - abs(self.coord.y)) / 10
                coord_trajectory_bullet = [
                    (self.coord.x + step_x * i, self.coord.y + step_y * i) for
                    i in range(1, 11)]
                check_traject = any([abs(
                    round(teammate.coord.x - x)) <= 50 and abs(
                    round(teammate.coord.y - y)) <= 50
                                     and self.distance_to(teammate) >= 50 for
                                     x, y in coord_trajectory_bullet])
                near_check = (self.distance_to(
                    teammate) - self.radius * 2) < - 25 and not teammate.is_moving
                if check_traject or near_check:
                    random.shuffle(new_coord)
                    for coord in new_coord:
                        if all([mate.distance_to(
                                coord) - self.radius * 2 > - 25 for mate in
                                self.teammates]):
                            if 0 < coord.x < self.field[
                                0] and 0 < coord.y < self.field[1]:
                                self.current_target = self.find_point_for_shot()
                                return False
                    self.current_target = self.find_point_for_shot()

                    return False
        return True

    def validate_point(self, x, y):
        if not 0 < x < theme.FIELD_WIDTH and 0 < y < theme.FIELD_HEIGHT:
            return False
        if any([moth.near(Point(x, y)) for moth in self.scene.motherships]):
            return False
        return True

    def validate_near_drone(self, radius, x, y):
        for drone in self.drones:
            if drone == self or not drone.is_alive:
                continue
            cent_r_x, cent_r_y = drone.current_target.x, drone.current_target.y
            circle = (x - cent_r_x) ** 2 + (y - cent_r_y) ** 2
            if circle <= (radius + 10) ** 2:
                return False

        return True


drone_class = ZaikinDrone
