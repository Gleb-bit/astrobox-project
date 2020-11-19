# -*- coding: utf-8 -*-
import math
from astrobox.core import Drone
from astrobox.themes.default import MOTHERSHIP_HEALING_DISTANCE
from robogame_engine.geometry import Point, Vector
from robogame_engine.theme import theme


class BeskaevDrone(Drone):
    drones_team = []
    limit_health = 0.6
    COUNT_SAFE_FLY = 3

    def __init__(self):
        super(BeskaevDrone, self).__init__()
        self.is_unloading_to_mothership = False
        self.drones_team.append(self)
        self.collection_is_over = False
        self.priority = len(self.drones_team)
        self.count_fly = 0
        self.attack_range = self.gun.shot_distance
        self.target = None
        self.number_asteroid_for_loading = 0
        self.role = Collector(self)

    def get_start_point(self):
        step_angle = 15  # начальный угол отклонения для начального разлёта
        game_field_half_x_size = theme.FIELD_WIDTH * 0.5
        game_field_half_y_size = theme.FIELD_HEIGHT * 0.5
        # в зависисости от положения базы, выбираем угол от которого будем разлетаться в полукруг вокруг базы
        if self.mothership.x < game_field_half_x_size and self.mothership.y < game_field_half_y_size:
            start_angle = 0
            start_x = 0
            start_y = 0
        elif self.mothership.x < game_field_half_x_size and self.mothership.y > game_field_half_y_size:
            start_angle = 270
            start_x = 0
            start_y = theme.FIELD_HEIGHT
        elif self.mothership.x > game_field_half_x_size and self.mothership.y < game_field_half_y_size:
            start_angle = 90
            start_x = theme.FIELD_WIDTH
            start_y = 0
        elif self.mothership.x > game_field_half_x_size and self.mothership.y > game_field_half_y_size:
            start_angle = 180
            start_x = theme.FIELD_WIDTH
            start_y = theme.FIELD_HEIGHT

        start_radius = MOTHERSHIP_HEALING_DISTANCE * 1.4
        current_angle_radians = math.radians(self.priority * step_angle + start_angle)
        x = start_x + math.cos(current_angle_radians) * start_radius
        y = start_y + math.sin(current_angle_radians) * start_radius
        return Point(x, y)

    def on_born(self):
        self.role.role_action()

    def get_asteroid_future_payload(self, asteroid):
        """Функция для расчёта будущего количества элериума на астероиде.
            Из текущего количества элериума вычитается свободное место всех дронов(кроме текущего) для которых астероид является целью"""
        asteroid_future_payload = asteroid.payload
        for drone in self.drones_team:  # учтём всех дронов что уже летят на этот астероид для сбора ресурсов
            if drone == self:  # кроме себя самого
                continue
            if drone.target == asteroid and not drone.is_unloading_to_mothership:  # без учёта дронов на разгрузке
                asteroid_future_payload -= drone.free_space
        return asteroid_future_payload

    def get_next_asteroid(self):
        """ Функция выбора следующего астероида для загрузки элериума"""
        min_distance = 10000
        next_asteroid = None  # если не нашёлся следующий астероид, то летим на базу
        for asteroid in self.asteroids:
            current_distance = self.distance_to(asteroid)
            asteroid_future_payload = self.get_asteroid_future_payload(asteroid)  # будет ли элериум на этом астероиде?
            # выбираем астероид где можно будет загрузится по полной
            if asteroid_future_payload >= self.free_space and current_distance < min_distance:
                next_asteroid = asteroid
                min_distance = current_distance

        if not next_asteroid:  # если не нашли астероид где побольше элериума, то летим на ближайший где будут ресурсы
            next_asteroid = self.get_nearest_asteroid_for_loading()
        return next_asteroid

    def get_nearest_asteroid_for_loading(self):
        """функция для выбора ближайшего астероида"""
        nearest_asteroid = None

        # если есть астероиды с элериумом то полетим на ближайший
        asteroids_with_elerium = [asteroid for asteroid in self.asteroids if asteroid.payload > 0]
        if len(asteroids_with_elerium) > 0:
            ordered_by_dist_asteroids = sorted(asteroids_with_elerium, key=lambda asteroid: self.distance_to(asteroid))

            for asteroid in ordered_by_dist_asteroids:
                asteroid_future_payload = self.get_asteroid_future_payload(
                    asteroid)  # будет ли элериум на этом астероиде?

                # посмотрим на дронов летящих на этот астероид, и если мы ближе самого дальнего и нам останется элериум, то забронируем себе место
                possible_asteroid = self.get_asteroid_if_self_closer(asteroid, asteroid_future_payload)
                if possible_asteroid:
                    return possible_asteroid

                if asteroid_future_payload > 0:  # если на астероиде останется элериум то летим туда, он самый ближний
                    nearest_asteroid = asteroid
                    return nearest_asteroid

        return nearest_asteroid

    def get_asteroid_if_self_closer(self, asteroid, asteroid_future_payload):
        nearest_asteroid = None
        drones_with_same_target = [drone for drone in self.drones_team if
                                   drone.target == asteroid and not drone.is_unloading_to_mothership
                                   and drone.free_space > 0]

        if len(drones_with_same_target) > 0:
            drones_with_same_target = sorted(drones_with_same_target, key=lambda drone: drone.distance_to(asteroid))
            most_distant_droid = drones_with_same_target[-1]
            if self.distance_to(asteroid) < most_distant_droid.distance_to(asteroid):
                asteroid_future_payload += most_distant_droid.free_space
                if asteroid_future_payload > 0:  # если нам останется элериум без учёта самого дальнего дрона
                    nearest_asteroid = asteroid
                    self.wedge_in_front_of_most_distant(most_distant_droid, asteroid_future_payload)

        return nearest_asteroid

    def wedge_in_front_of_most_distant(self, most_distant_droid, asteroid_future_payload):
        asteroid_future_payload -= self.free_space  # хватит ли самому дальнему дрону элериума?
        if asteroid_future_payload < 0:  # если нет, то поищем ему новую цель
            most_distant_droid_next_target = most_distant_droid.get_next_asteroid()
            if most_distant_droid_next_target:
                most_distant_droid.target = most_distant_droid_next_target
                most_distant_droid.move_at(most_distant_droid.target)
            else:  # если нечего собирать, то летим на базу
                most_distant_droid.move_at(most_distant_droid.my_mothership)

    def check_asteroids(self):
        for drone in self.drones_team:
            if drone == self:  # кроме себя самого
                continue

            # если на астероиде куда летит другой дрон уже всё собрали, то выбираем новую цель
            if drone.target.payload == 0 and not drone.is_unloading_to_mothership and drone.free_space > 0:
                next_target = drone.get_next_asteroid()
                if next_target:
                    drone.target = next_target
                    drone.move_at(drone.target)
                else:
                    drone.move_at(drone.my_mothership)

    def on_stop_at_asteroid(self, asteroid):
        self.load_from(asteroid)
        self.turn_to(self.mothership)
        # self.check_asteroids()

    def on_load_complete(self):

        self.role.role_action()

    def on_wake_up(self):
        self.do_action()

    def game_step(self):
        super().game_step()
        if isinstance(self.role, Collector) and not self.is_near_base() and self.meter_2 < self.limit_health:
            self.move_at(self.mothership)
        if self.health < 100 and not self.is_near_base() and isinstance(self.role, Collector):
            self.number_asteroid_for_loading += 1
            self.move_at(self.mothership)
        if isinstance(self.role, Collector) and not self.is_near_base() \
                and self.count_enemies_in_shot_range() > 1 and self.count_fly >= self.COUNT_SAFE_FLY:
            self.move_at(self.mothership)
        if isinstance(self.role, Exterminator) and self.meter_2 < self.limit_health:
            self.move_at(self.mothership)

    def count_enemies_in_shot_range(self):
        enemies_in_shot_range = [drone for drone in self.scene.drones if
                                 self.team != drone.team and drone.is_alive and self.distance_to(
                                     drone) <= self.attack_range + self.radius]
        return len(enemies_in_shot_range)

    def is_near_base(self):
        if self.distance_to(self.mothership) > MOTHERSHIP_HEALING_DISTANCE:
            return False
        else:
            return True

    def do_action(self):
        alive_teammates = [drone for drone in self.drones_team if drone.is_alive]
        if self.count_fly >= self.COUNT_SAFE_FLY:
            self.role = Defender(self)
        if self.get_enemy_in_base_range() and self.count_fly >= self.COUNT_SAFE_FLY:
            self.role = Defender(self)
        elif self.is_few_drones_near_enemy_bases() and self.count_fly >= self.COUNT_SAFE_FLY and len(
                alive_teammates) >= 5:
            self.role = Exterminator(self)
        elif self.get_safe_asteroid() and self.count_fly >= self.COUNT_SAFE_FLY:
            self.role = Collector(self)

        self.role.role_action()

    def shot(self, target):
        vector_to_target = Vector.from_points(self.coord, target.coord)
        self.turn_to(target)
        if vector_to_target.direction - 2 <= self.direction <= vector_to_target.direction + 2:
            self.gun.shot(target)
        else:
            self.turn_to(target)

    def is_few_drones_near_enemy_bases(self):
        enemy_base1 = [base for base in self.scene.motherships if base.team != self.team and base.x == self.mothership.x][0]
        enemy_base2 = [base for base in self.scene.motherships if base.team != self.team and base.y == self.mothership.y][0]
        drones_enemy_base1 = [drone for drone in self.scene.drones if drone.team == enemy_base1.team
                              and drone.is_alive]
        drones_enemy_base2 = [drone for drone in self.scene.drones if drone.team == enemy_base2.team
                              and drone.is_alive]
        if (enemy_base1.is_alive and len(drones_enemy_base1) <= 1) or len(drones_enemy_base1) == 1:
            return True
        elif (enemy_base2.is_alive and len(drones_enemy_base2) <= 1) or len(drones_enemy_base2) == 1:
            return True
        else:
            return False

    def get_safe_asteroid(self):
        asteroid_with_elerium = [asteroid for asteroid in self.asteroids if asteroid.payload > 0]
        dead_drone_drone_with_elerium = [drone for drone in self.scene.drones if
                                         not drone.is_alive and drone.payload > 0]
        asteroid_with_elerium.extend(dead_drone_drone_with_elerium)
        dead_enemy_base_with_elerium = [base for base in self.scene.motherships if base.team != self.team
                                        and not base.is_alive and base.payload > 0]
        asteroid_with_elerium.extend(dead_enemy_base_with_elerium)
        safe_asteroids = []
        for asteroid in asteroid_with_elerium:
            if self.is_safe_way_to_target(asteroid):
                safe_asteroids.append(asteroid)

        if safe_asteroids:
            safe_asteroids = [(asteroid, self.distance_to(asteroid)) for asteroid in safe_asteroids]
            safe_asteroids.sort(key=lambda x: x[1])
            index = self.number_asteroid_for_loading % len(safe_asteroids)
            return safe_asteroids[index][0]
        else:
            return None

    def is_safe_way_to_target(self, target):  # проверяет безопасно ли лететь до цели
        enemies = [drone for drone in self.scene.drones if self.team != drone.team and drone.is_alive]

        vector_to_target = Vector.from_points(self.coord, target.coord if not isinstance(target, Point) else target)
        distance_to_target = vector_to_target.module if vector_to_target.module > 1 else 1
        _koef = 1 / distance_to_target
        normalize_vector = Vector(vector_to_target.x * _koef, vector_to_target.y * _koef)
        start_distance = 100 if self.is_near_base() else 1
        drones_on_way = []
        for i in range(start_distance, int(distance_to_target), self.radius // 2):
            current_vector = normalize_vector * i
            check_point = Point(self.x + current_vector.x, self.y + current_vector.y)
            for drone in enemies:
                if drone.distance_to(
                        check_point) <= self.attack_range + 2 * self.radius:  # если по пути будем под обстрелом, то небезопасно
                    drones_on_way.append(drone.id)

        drones_on_way = set(drones_on_way)
        if len(drones_on_way) <= 1:  # если во время перелёта по дрону будет стретять не больше 1 врага, то можно лететь
            return True
        else:
            return False

    def get_available_enemy_in_shot_range(self):
        enemies_in_shot_range = [(drone, self.distance_to(drone)) for drone in self.scene.drones if
                                 self.team != drone.team and drone.is_alive and self.distance_to(
                                     drone) <= self.attack_range + 1.5 * self.radius]
        if not enemies_in_shot_range:
            return None

        enemies_in_shot_range.sort(key=lambda x: x[1])
        for enemy, distance in enemies_in_shot_range:
            possibility_of_shooting, drone = self.check_possibility_of_shooting(self.coord, enemy)
            if possibility_of_shooting:
                return enemy

        return None

    def get_enemy_in_base_range(self, number_enemy=0):

        enemies = [(drone, self.distance_to(drone)) for drone in self.scene.drones if
                   self.team != drone.team and drone.is_alive and self.mothership.distance_to(
                       drone) <= self.attack_range + MOTHERSHIP_HEALING_DISTANCE]

        if enemies:
            enemies.sort(key=lambda x: x[1])
            return enemies[number_enemy][0]
        else:
            return None

    def check_possibility_of_shooting(self, point, object):
        """ Проверяет можно ли из point выстрелить по цели не задев напарников
        Возвращает True, None - если возможен выстрел
        False, Drone - если выстрел не возможен. Drone, который на пути выстрела"""
        vector_to_target = Vector.from_points(point, object.coord)
        distance_to_target = vector_to_target.module
        _koef = 1 / distance_to_target
        normalize_vector = Vector(vector_to_target.x * _koef, vector_to_target.y * _koef)
        vector_to_check = normalize_vector * 5
        steps_count = int(distance_to_target // 5)
        for drone in self.drones_team:
            if drone is self or not drone.is_alive:
                continue
            for i in range(1, steps_count + 1):
                current_vector = vector_to_check * i
                check_point = Point(point.x + current_vector.x, point.y + current_vector.y)

                is_inside = self.point_is_inside_drone(drone, check_point)
                if is_inside:
                    return False, drone

        return True, None

    def point_is_inside_drone(self, drone, point):
        distance = drone.distance_to(point)
        if distance <= drone.radius * 1.4:
            return True
        else:
            return False

    def on_stop_at_mothership(self, mothership):
        self.count_fly += 1
        if self.team == mothership.team:
            if self.payload:
                self.unload_to(mothership)
                self.turn_to(self.target)
                self.is_unloading_to_mothership = True

    def on_unload_complete(self):
        self.is_unloading_to_mothership = False


class Collector:

    def __init__(self, me: BeskaevDrone):
        self.me = me

    def role_action(self):
        if self.me.payload == 100 or (not self.me.get_safe_asteroid() and self.me.count_fly >= self.me.COUNT_SAFE_FLY):
            self.me.move_at(self.me.my_mothership)
            return

        if self.me.count_fly < self.me.COUNT_SAFE_FLY:
            if self.me.target is None or self.me.target.payload == 0:
                self.me.target = self.me.get_next_asteroid()

        else:
            self.me.target = self.me.get_safe_asteroid()
        if self.me.target:
            if self.me.distance_to(self.me.target) < 10 and self.me.free_space > 0:
                self.me.number_asteroid_for_loading = 0
                self.me.load_from(self.me.target)
                self.me.turn_to(self.me.mothership)
                return

        if self.me.target:
            self.me.move_at(self.me.target)


class Defender:

    def __init__(self, me: BeskaevDrone):
        self.me = me

    def role_action(self):
        if self.me.payload > 0:
            self.me.move_at(self.me.mothership)
            return
        if self.me.x == self.me.get_start_point().x and self.me.y == self.me.get_start_point().y:
            self.enemy = self.me.get_available_enemy_in_shot_range()  # or self.get_enemy_in_range()
            # or self.get_enemy_bases() or self.get_enemy_out_of_range()
            if self.enemy:
                if hasattr(self.enemy, 'mothership'):
                    if self.enemy.distance_to(
                            self.enemy.mothership) <= \
                            MOTHERSHIP_HEALING_DISTANCE + self.enemy.radius + self.enemy.mothership.radius \
                            and self.me.distance_to(
                        self.enemy.mothership) - self.enemy.mothership.radius <= self.me.attack_range \
                            and self.enemy.mothership.is_alive:
                        self.enemy = self.enemy.mothership

                self.me.shot(self.enemy)
        else:
            self.me.move_at(self.me.get_start_point())


class Exterminator:
    enemy = None

    def __init__(self, me):
        self.me = me
        self.prepare_position = None

    def role_action(self):

        if not self.enemy or not self.enemy.is_alive:
            self.enemy = self.get_enemy()
            if self.enemy:
                self.prepare_position = self.get_prepare_position(self.enemy)
                if not self.me.is_safe_way_to_target(self.prepare_position):
                    self.me.move_at(self.me.mothership)
        if self.enemy:
            if not self.me.near(self.prepare_position):
                self.me.move_at(self.prepare_position)
                return
            self.me.shot(self.enemy)
        if self.me.count_enemies_in_shot_range() > 1:
            self.me.move_at(self.me.mothership)
            return

    def get_prepare_position(self, enemy):
        if self.me.distance_to(enemy) <= self.me.attack_range:
            return self.me.coord
        circle_radius = self.me.attack_range + self.me.radius
        angle_step = 2 * math.degrees(math.asin(self.me.radius / circle_radius))
        possible_positions = []  # возможные позиции для атаки по цели
        current_angle = 0
        while current_angle < 360:

            angle_radians = math.radians(current_angle)
            x = math.cos(angle_radians) * circle_radius
            y = math.sin(angle_radians) * circle_radius
            possible_attack_point = Point(enemy.x + x, enemy.y + y)

            if not self.is_collision_with_field_size(possible_attack_point) \
                    and not self.is_collision_with_my_mother_ship(possible_attack_point):
                possible_positions.append(
                    (possible_attack_point, possible_attack_point.distance_to(self.me.mothership)))

            current_angle += angle_step

        if len(possible_positions) >= self.me.priority:
            possible_positions.sort(key=lambda x: x[1])
            return possible_positions[self.me.priority - 1][0]  # выбираем позицию, которая ближе к своей базе
        return self.me.get_start_point()

    def get_enemy(self):
        enemy_base1 = [base for base in self.me.scene.motherships if base.team != self.me.team
                       and base.x == self.me.mothership.x][0]
        enemy_base2 = [base for base in self.me.scene.motherships if base.team != self.me.team
                       and base.y == self.me.mothership.y][0]
        drones_enemy_base1 = [drone for drone in self.me.scene.drones if drone.team == enemy_base1.team
                              and drone.is_alive]
        drones_enemy_base2 = [drone for drone in self.me.scene.drones if drone.team == enemy_base2.team
                              and drone.is_alive]

        if len(drones_enemy_base1) <= 1:
            if enemy_base1.is_alive:
                return enemy_base1
            elif len(drones_enemy_base1) == 1:
                return drones_enemy_base1[0]

        if len(drones_enemy_base2) <= 1:
            if enemy_base2.is_alive:
                return enemy_base2
            elif len(drones_enemy_base2) == 1:
                return drones_enemy_base2[0]

    def is_collision_with_field_size(self, point):
        """ метод проверяет не вылетит ли дрон на границу экрана если полетит в point"""
        field_size_x = theme.FIELD_WIDTH
        field_size_y = theme.FIELD_HEIGHT
        if field_size_x < (point.x + self.me.radius) or field_size_y < (point.y + self.me.radius) \
                or point.x < self.me.radius or point.y < self.me.radius:
            return True
        else:
            return False

    def is_collision_with_my_mother_ship(self, point):
        if point.distance_to(self.me.my_mothership) - self.me.mothership.radius - self.me.radius < 0:
            return True
        else:
            return False


drone_class = BeskaevDrone
