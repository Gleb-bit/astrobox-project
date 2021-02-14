# -*- coding: utf-8 -*-
from astrobox.core import *
from abc import ABC, abstractmethod
from astrobox.themes.default import MOTHERSHIP_HEALING_DISTANCE
from robogame_engine.geometry import Point, Vector


class Strategy(ABC):

    center_field = Point(theme.FIELD_WIDTH // 2, theme.FIELD_HEIGHT // 2)

    def __init__(self, drone_ref):
        self.drone_ref = drone_ref

        self.prepare_position = None

        self.actions_mapping = {
            "on_born": self.on_born,
            "on_stop_at_asteroid": self.on_stop_at_asteroid,
            "on_load_complete": self.on_load_complete,
            "on_stop_at_mothership": self.on_stop_at_mothership,
            "on_unload_complete": self.on_unload_complete,
            "on_stop_at_point": self.on_stop_at_point,
            "on_hearbeat": self.on_hearbeat,
            "on_stop": self.on_stop,
            "on_wake_up": self.on_wake_up
        }

    def implement_strategy(self, message, **kwargs):
        self.actions_mapping[message](**kwargs)

    @abstractmethod
    def on_born(self, **kwargs):
        pass

    @abstractmethod
    def on_stop_at_asteroid(self, **kwargs):
        pass

    @abstractmethod
    def on_load_complete(self, **kwargs):
        pass

    @abstractmethod
    def on_stop_at_mothership(self, **kwargs):
        pass

    @abstractmethod
    def on_unload_complete(self, **kwargs):
        pass

    @abstractmethod
    def on_stop_at_point(self, **kwargs):
        pass

    @abstractmethod
    def on_hearbeat(self, **kwargs):
        pass

    @abstractmethod
    def on_stop(self, **kwargs):
        pass

    @abstractmethod
    def on_wake_up(self, **kwargs):
        pass

    def switch_strategy(self):
        # живые союзники
        alive_teammates = [drone for drone in self.drone_ref.my_team if drone.is_alive]

        # если вылетели с материнской базы больше, чем константа COUNT_SAFE_FLY, то переключаемся в режим защиты
        if self.drone_ref.count_fly >= VorobyevDrone.COUNT_SAFE_FLY:
            self.drone_ref.strategy = self.drone_ref.defend_strategy

        # если есть враги вблизи нашей базы (и их больше двух), и вылетали >= чем константа COUNT_SAFE_FLY
        if self.drone_ref.get_enemy_in_base_range() and self.drone_ref.count_fly >= VorobyevDrone.COUNT_SAFE_FLY:
            self.drone_ref.strategy = self.drone_ref.defend_strategy
        # или если есть 1 враг в пределах своей базы, и живых союзников >= 3, переходим в режим уничтожения базы врага
        elif self.drone_ref.is_few_drones_near_enemy_bases() \
                and self.drone_ref.count_fly >= VorobyevDrone.COUNT_SAFE_FLY and len(alive_teammates) >= 3:
            self.drone_ref.strategy = self.drone_ref.mship_killer_strategy
        # или если есть источник ресурсов (дрон, астероид, база), то собираем его
        elif self.drone_ref.get_safe_asteroid() and self.drone_ref.count_fly >= VorobyevDrone.COUNT_SAFE_FLY:
            self.drone_ref.strategy = self.drone_ref.collect_strategy

        # если после первых вылетов не осталось астероидов для сбора, то всем устанавливаем граничное количество вылетов
        if isinstance(self.drone_ref.strategy, Collector) and not self.drone_ref.get_next_asteroid() \
                and self.drone_ref.count_fly < VorobyevDrone.COUNT_SAFE_FLY:
            self.drone_ref.count_fly = VorobyevDrone.COUNT_SAFE_FLY
            self.drone_ref.strategy = self.drone_ref.defend_strategy

        self.drone_ref.strategy.act()


class Collector(Strategy):

    def act(self):
        if self.drone_ref.payload == 100 or (
                not self.drone_ref.get_safe_asteroid() and self.drone_ref.count_fly >= VorobyevDrone.COUNT_SAFE_FLY):
            self.drone_ref.move_at(self.drone_ref.my_mothership)
            return

        if self.drone_ref.count_fly < VorobyevDrone.COUNT_SAFE_FLY:
            if self.drone_ref.target is None or self.drone_ref.target.payload == 0:
                self.drone_ref.target = self.drone_ref.get_next_asteroid()

        else:
            self.drone_ref.target = self.drone_ref.get_safe_asteroid()
        if self.drone_ref.target:
            if self.drone_ref.distance_to(self.drone_ref.target) < 10 and self.drone_ref.free_space > 0:
                self.drone_ref.number_asteroid_for_loading = 0
                self.drone_ref.load_from(self.drone_ref.target)
                self.drone_ref.turn_to(self.drone_ref.mothership)
                return

        if self.drone_ref.target:
            self.drone_ref.move_at(self.drone_ref.target)

    def on_born(self, **kwargs):
        self.act()

    def on_stop_at_asteroid(self, **kwargs):
        self.drone_ref.load_from(self.drone_ref.target)
        self.drone_ref.turn_to(self.drone_ref.my_mothership)

    def on_load_complete(self, **kwargs):
        self.act()

    def on_stop_at_mothership(self, **kwargs):
        self.drone_ref.count_fly += 1
        if self.drone_ref.team == self.drone_ref.my_mothership.team:
            if self.drone_ref.payload:
                self.drone_ref.unload_to(self.drone_ref.my_mothership)
                self.drone_ref.is_unloading_to_mothership = True
                self.drone_ref.turn_to(Strategy.center_field)

    def on_unload_complete(self, **kwargs):
        self.drone_ref.is_unloading_to_mothership = False

    def on_stop_at_point(self, **kwargs):
        pass

    def on_stop(self, **kwargs):
        self.act()

    def on_hearbeat(self, **kwargs):
        pass

    def on_wake_up(self, **kwargs):
        super(Collector, self).switch_strategy()


class Defender(Strategy):
    def act(self):
        if self.drone_ref.payload > 0:
            self.drone_ref.move_at(self.drone_ref.mothership)
            return
        if self.drone_ref.x == self.drone_ref.get_start_point().x and self.drone_ref.y == self.drone_ref.get_start_point().y:
            self.enemy = self.drone_ref.get_available_enemy_in_shot_range()
            if self.enemy:
                if hasattr(self.enemy, 'mothership'):
                    if self.enemy.distance_to(
                            self.enemy.mothership) <= MOTHERSHIP_HEALING_DISTANCE + self.enemy.radius + self.enemy.mothership.radius \
                            and self.drone_ref.distance_to(
                        self.enemy.mothership) - self.enemy.mothership.radius <= self.drone_ref.attack_range \
                            and self.enemy.mothership.is_alive:
                        self.enemy = self.enemy.mothership

                self.drone_ref.target = self.enemy
                self.drone_ref.shot()
        else:
            self.drone_ref.move_at(self.drone_ref.get_start_point())

    def on_born(self, **kwargs):
        self.act()

    def on_stop_at_asteroid(self, **kwargs):
        pass

    def on_load_complete(self, **kwargs):
        self.act()

    def on_stop_at_mothership(self, **kwargs):
        pass

    def on_unload_complete(self, **kwargs):
        pass

    def on_stop_at_point(self, **kwargs):
        pass

    def on_stop(self, **kwargs):
        self.act()

    def on_hearbeat(self, **kwargs):
        pass

    def on_wake_up(self, **kwargs):
        super(Defender, self).switch_strategy()


class MothershipKiller(Strategy):
    enemy = None

    def act(self):
        if not self.enemy or not self.enemy.is_alive:
            self.enemy = self.get_enemy()
            if self.enemy:
                self.prepare_position = self.get_prepare_position(self.enemy)
                if not self.drone_ref.is_safe_way_to_target(self.prepare_position):
                    self.drone_ref.move_at(self.drone_ref.mothership)
        if self.enemy:
            if not self.drone_ref.near(self.prepare_position):
                self.drone_ref.move_at(self.prepare_position)
                return

            if self.drone_ref.health < self.drone_ref.limit_health:
                self.drone_ref.move_at(self.drone_ref.my_mothership)
            else:
                self.drone_ref.target = self.enemy
                self.drone_ref.shot()

        if self.drone_ref.count_enemies_in_shot_range() > 1:
            self.drone_ref.move_at(self.drone_ref.mothership)
            return

    def get_prepare_position(self, enemy):
        if self.drone_ref.distance_to(enemy) <= self.drone_ref.attack_range:
            return self.drone_ref.coord
        circle_radius = self.drone_ref.attack_range + self.drone_ref.radius
        angle_step = 2.3 * math.degrees(math.asin(self.drone_ref.radius / circle_radius))
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
                    (possible_attack_point, possible_attack_point.distance_to(self.drone_ref.mothership)))

            current_angle += angle_step

        if len(possible_positions) >= self.drone_ref.serial_number:
            possible_positions.sort(key=lambda x: x[1])
            return possible_positions[self.drone_ref.serial_number - 1][0]  # выбираем позицию, которая ближе к своей базе
        return self.drone_ref.get_start_point()

    def get_enemy(self):
        enemy_bases = [(base, self.drone_ref.mothership.distance_to(base)) for base in self.drone_ref.scene.motherships
                       if base.team != self.drone_ref.team]
        enemy_bases.sort(key=lambda x: x[1])
        enemy_bases = [base for base, distance in enemy_bases]
        stop_index = 1 if len(enemy_bases) == 1 else len(enemy_bases) - 1
        for i in range(stop_index):
            enemy_base = enemy_bases[i]
            drones_enemy_base = [drone for drone in self.drone_ref.scene.drones if drone.team == enemy_base.team
                                 and drone.is_alive]
            if len(drones_enemy_base) <= 1:
                if enemy_base.is_alive:
                    return enemy_base
                elif len(drones_enemy_base) == 1:
                    return drones_enemy_base[0]

    def is_collision_with_field_size(self, point):
        """ метод проверяет не вылетит ли дрон на границу экрана если полетит в point"""
        field_size_x = theme.FIELD_WIDTH
        field_size_y = theme.FIELD_HEIGHT
        if field_size_x < (point.x + self.drone_ref.radius) or field_size_y < (point.y + self.drone_ref.radius) \
                or point.x < self.drone_ref.radius or point.y < self.drone_ref.radius:
            return True
        else:
            return False

    def is_collision_with_my_mother_ship(self, point):
        if point.distance_to(
                self.drone_ref.my_mothership) - self.drone_ref.mothership.radius - self.drone_ref.radius < 0:
            return True
        else:
            return False

    def on_born(self, **kwargs):
        self.act()

    def on_stop_at_asteroid(self, **kwargs):
        pass

    def on_load_complete(self, **kwargs):
        self.act()

    def on_stop_at_mothership(self, **kwargs):
        pass

    def on_unload_complete(self, **kwargs):
        pass

    def on_stop_at_point(self, **kwargs):
        self.act()

    def on_stop(self, **kwargs):
        self.act()

    def on_hearbeat(self, **kwargs):
        pass

    def on_wake_up(self, **kwargs):
        super(MothershipKiller, self).switch_strategy()


class VorobyevDrone(Drone):
    my_team = []
    serial_number = 1
    drone_states = {}
    limit_health = 0.7
    COUNT_SAFE_FLY = 3

    def __init__(self, **kwargs):
        super(VorobyevDrone, self).__init__(**kwargs)
        self._strategy = None

        self.serial_number = VorobyevDrone.serial_number
        VorobyevDrone.serial_number += 1

        self.my_team.append(self)

        self.collect_strategy = Collector(drone_ref=self)
        self.defend_strategy = Defender(drone_ref=self)
        self.mship_killer_strategy = MothershipKiller(drone_ref=self)

        self.number_asteroid_for_loading = 0
        self.attack_range = self.gun.shot_distance
        self.count_fly = 0
        self.is_unloading_to_mothership = False

    @property
    def strategy(self):
        return self._strategy

    @strategy.setter
    def strategy(self, strategy) -> None:
        self._strategy = strategy

    def move_at(self, target, speed=None, **kwargs):
        super(VorobyevDrone, self).move_at(target, speed=speed)

    def on_born(self, **kwargs):
        self.strategy = self.collect_strategy
        self._strategy.implement_strategy(message="on_born", **kwargs)

    def on_stop_at_asteroid(self, asteroid, **kwargs):
        self._strategy.implement_strategy(message="on_stop_at_asteroid", **kwargs)

    def on_load_complete(self, **kwargs):
        self._strategy.implement_strategy(message="on_load_complete", **kwargs)

    def on_stop_at_mothership(self, mothership, **kwargs):
        self._strategy.implement_strategy(message="on_stop_at_mothership", **kwargs)

    def on_unload_complete(self, **kwargs):
        self._strategy.implement_strategy(message="on_unload_complete", **kwargs)

    def on_stop_at_point(self, target, **kwargs):
        self._strategy.implement_strategy(message="on_stop_at_point", **kwargs)

    def on_stop(self, **kwargs):
        self._strategy.implement_strategy(message="on_stop", **kwargs)

    def on_wake_up(self, **kwargs):
        self._strategy.implement_strategy(message="on_wake_up", **kwargs)

    def is_near_base(self):
        if self.distance_to(self.mothership) > MOTHERSHIP_HEALING_DISTANCE:
            return False
        else:
            return True

    def on_heartbeat(self, **kwargs):
        if isinstance(self.strategy, Collector) and not self.is_near_base() and self.meter_2 < self.limit_health:
            self.move_at(self.mothership)
        if self.health < 100 and not self.is_near_base() and isinstance(self.strategy, Collector):
            self.number_asteroid_for_loading += 1
            self.move_at(self.mothership)
        if isinstance(self.strategy, Collector) and not self.is_near_base() \
                and self.count_enemies_in_shot_range() > 1 and self.count_fly >= self.COUNT_SAFE_FLY:
            self.move_at(self.mothership)
        if isinstance(self.strategy, MothershipKiller) and self.meter_2 < self.limit_health:
            self.move_at(self.mothership)

        self._strategy.implement_strategy(message="on_hearbeat", **kwargs)

    def count_enemies_in_shot_range(self):
        enemies_in_shot_range = [drone for drone in self.scene.drones if
                                 self.team != drone.team and drone.is_alive and self.distance_to(
                                     drone) <= self.attack_range + self.radius]
        return len(enemies_in_shot_range)

    def get_enemy_in_base_range(self, number_enemy=0):
        enemies = [(drone, self.distance_to(drone)) for drone in self.scene.drones if
                   self.team != drone.team and drone.is_alive and self.mothership.distance_to(
                       drone) <= self.attack_range + MOTHERSHIP_HEALING_DISTANCE]

        if enemies:
            enemies.sort(key=lambda x: x[1])
            if len(enemies) >= 2:
                return enemies[number_enemy][0]
            else:
                return None
        else:
            return None

    def is_few_drones_near_enemy_bases(self):
        enemy_bases = [(base, self.mothership.distance_to(base)) for base in self.scene.motherships
                       if base.team != self.team]
        enemy_bases.sort(key=lambda x: x[1])
        enemy_bases = [base for base, distance in enemy_bases]

        stop_index = 1 if len(enemy_bases) == 1 else len(enemy_bases) - 1

        for i in range(stop_index):
            enemy_base = enemy_bases[i]
            drones_enemy_base = [drone for drone in self.scene.drones if drone.team == enemy_base.team
                                 and drone.is_alive]

            if len(drones_enemy_base) <= 1:
                if enemy_base.is_alive or len(drones_enemy_base) == 1:
                    return True

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

    def get_asteroid_future_payload(self, asteroid):
        """Функция для расчёта будущего количества элериума на астероиде.
            Из текущего количества элериума вычитается свободное место всех дронов(кроме текущего) для которых астероид является целью"""
        asteroid_future_payload = asteroid.payload
        for drone in self.my_team:  # учтём всех дронов что уже летят на этот астероид для сбора ресурсов
            if drone == self:  # кроме себя самого
                continue
            if drone.target == asteroid and not drone.is_unloading_to_mothership and drone.is_alive:  # без учёта дронов на разгрузке
                asteroid_future_payload -= drone.free_space
        return asteroid_future_payload

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
        drones_with_same_target = [drone for drone in self.my_team if
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

    def shot(self):
        vector_to_target = Vector.from_points(self.coord, self.target.coord)
        self.turn_to(self.target)
        if vector_to_target.direction - 2 <= self.direction <= vector_to_target.direction + 2:
            self.gun.shot(self.target)
        else:
            self.turn_to(self.target)

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
        for drone in self.my_team:
            if drone is self or not drone.is_alive:
                continue
            for i in range(15, steps_count + 1):
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

    def distance_to(self, obj):
        if obj is None:
            return 10000
        else:
            return super(VorobyevDrone, self).distance_to(obj)

    def get_start_point(self):
        step_angle = 15  # начальный угол отклонения для начального разлёта
        game_field_half_x_size = theme.FIELD_WIDTH * 0.5
        game_field_half_y_size = theme.FIELD_HEIGHT * 0.5
        # в зависисости от положения базы, выбираем угол от которого будем разлетаться в полукруг вокруг базы
        start_angle, start_x, start_y = 0, 0, 0

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
        current_angle_radians = math.radians(self.serial_number * step_angle + start_angle)
        x = start_x + math.cos(current_angle_radians) * start_radius
        y = start_y + math.sin(current_angle_radians) * start_radius
        return Point(x, y)

drone_class = VorobyevDrone