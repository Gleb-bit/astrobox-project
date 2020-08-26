from math import ceil

from astrobox.core import Drone, Asteroid
from robogame_engine.geometry import Point, Vector, normalise_angle

SUFFICIENT_PAYLOAD = 90
FIGHTER = 'fighter'
HARVESTER = 'harvester'


class RoleError(Exception):
    pass


class PestovDrone(Drone):
    my_team = []
    fighters = []
    harvesters = []
    unavailable_asteroids = []
    attack_plan = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.role = None
        self.waiting = False
        self.offensive = False
        self.attacking = False
        self.previous_target = Point(self.x, self.y)
        self.next_target = None

    def on_born(self):
        """Действие при активации дрона"""
        self.__class__.my_team.append(self)
        self.change_role(FIGHTER)
        self.register_drone()
        self.attack_plan.set_mothership(self.my_mothership)

    def register_drone(self):
        if self.__class__.attack_plan is None:
            self.__class__.attack_plan = AttackPlan()
        self.attack_plan = self.__class__.attack_plan

    def change_role(self, role):
        if role == 'fighter':
            self.role = Fighter(self)
            self.offensive = True
            self.waiting = False
            if self in self.__class__.harvesters:
                self.__class__.harvesters.remove(self)
            self.__class__.fighters.append(self)
        elif role == 'harvester':
            self.role = Harvester(self)
            self.offensive = False
            self.waiting = True
            if self in self.__class__.fighters:
                self.__class__.fighters.remove(self)
            self.__class__.harvesters.append(self)

    def on_stop_at_asteroid(self, asteroid):
        """Действие при встрече с астероидом"""
        if isinstance(self.role, Harvester):
            self.role.on_stop_at_asteroid(asteroid)
        else:
            pass

    def on_load_complete(self):
        """Действие при завершении загрузки элериума"""
        if isinstance(self.role, Harvester):
            self.role.on_load_complete()
        else:
            raise RoleError('on_load_complete: Только сборщик может собирать ресурсы')

    def make_route(self, max_payload):
        if isinstance(self.role, Harvester):
            self.role.make_route(max_payload)
        else:
            raise RoleError('make_route: Только сборщик может собирать ресурсы')

    def on_stop_at_mothership(self, mothership):
        """Действие при возвращении на базу"""
        self.turn_to(self.previous_target)  # да, бессмысленно, но главное, что развернется на ~180 градусов
        self.previous_target = Point(self.x, self.y)
        if isinstance(self.role, Harvester):
            if not self.is_empty:
                self.unload_to(mothership)
            else:
                self.try_to_depart()
        elif isinstance(self.role, Fighter):
            if self.enemies_alive():
                self.offensive = True
            else:
                self.change_role(HARVESTER)

    def on_unload_complete(self):
        """Действие при завершении разгрузки дрона"""
        if isinstance(self.role, Harvester):
            self.try_to_depart()
        else:
            raise RoleError('on_unload_complete: Только сборщик может собирать ресурсы')

    def try_to_depart(self):
        """Отправление с базы"""
        if isinstance(self.role, Harvester):
            self.role.try_to_depart()
        else:
            raise RoleError('try_to_depart: Только сборщик может собирать ресурсы')

    def on_wake_up(self):  # совершенно не понимаю, в какой момент вызывается этот метод, но он явно важен
        if isinstance(self.role, Harvester):
            self.try_to_depart()
        elif isinstance(self.role, Fighter):
            self.offensive = True
            if not self.is_moving:
                self.attack_plan.go_to_attack_position(self)

    def move_to_mothership(self):
        """Двигаться на базу"""
        self.target = self.my_mothership
        self.next_target = None
        self.move_at(self.target)

    def move_to_the_closest_asteroid(self):
        """Двигаться к ближайшему астероиду"""
        if isinstance(self.role, Harvester):
            self.role.move_to_the_closest_asteroid()
        else:
            raise RoleError('move_to_the_closest_asteroid: Только сборщик может собирать ресурсы')

    def intercept_asteroid(self):
        """
        Попытка перехватить цель у другого дрона,
        если этот дрон находится ближе к цели.
        """
        if isinstance(self.role, Harvester):
            self.role.intercept_asteroid()
        else:
            raise RoleError('intercept_asteroid: Только сборщик может собирать ресурсы')

    def get_the_closest_asteroid(self):
        """
        Выбор ближайшего к дрону астероида.
        В первую очередь выбираются богатые элериумом астероиды.
        """
        if isinstance(self.role, Harvester):
            return self.role.get_the_closest_asteroid()
        else:
            raise RoleError('get_the_closest_asteroid: Только сборщик может собирать ресурсы')

    def get_next_asteroid(self):
        """Выбрать ближайший к текущей цели астероид"""
        if isinstance(self.role, Harvester):
            return self.role.get_next_asteroid()
        else:
            raise RoleError('get_next_asteroid: Только сборщик может собирать ресурсы')

    def game_step(self):
        super().game_step()

        if not self.is_alive:
            if self in self.__class__.harvesters:
                self.__class__.harvesters.remove(self)
            elif self in self.__class__.fighters:
                self.__class__.fighters.remove(self)

        for asteroid in self.asteroids:  # проверка, не опустели ли астероиды
            if asteroid not in self.__class__.unavailable_asteroids and asteroid.is_empty:
                self.__class__.unavailable_asteroids.append(asteroid)

        if self.health <= 40:
            self.retreat()

        if isinstance(self.role, Harvester):

            if self.waiting:  # возможные действия, при ожидании на базе
                if len(self.asteroids) > len(self.__class__.unavailable_asteroids):
                    self.waiting = False
                    self.try_to_depart()  # отправка на добычу, при наличии свободных астероидов

            for mothership in self.scene.motherships:  # разграбление вражеской базы
                if mothership != self.my_mothership and self.near(mothership):
                    self.offensive = False
                    self.load_from(mothership)

        elif isinstance(self.role, Fighter):
            if self.offensive:
                if not self.attack_plan.target_mothership:
                    for mothership in self.scene.motherships:
                        if mothership != self.my_mothership:
                            self.attack_plan.start_attack(mothership)
                elif self.target not in self.attack_plan.attack_positions or not self.near(self.target):
                    self.attack_plan.go_to_attack_position(self)  # иногда дрон не выполняет эту команду
                elif any([self.near(point) for point in self.attack_plan.attack_positions]) and (self.check_for_enemy_drones() or self.check_target_base()):
                    self.attacking = True

                for drone in self.__class__.fighters:
                    if self.target:
                        if drone.attacking or not self.near(self.target):
                            break
                    else:
                        break
                else:
                    self.attack_plan.advance_to_next_position()
            else:
                if self.health == 100:
                    self.offensive = True
                elif not self.is_moving and self.health >= 80:
                    self.offensive = True
                else:
                    self.move_to_mothership()

            if not self.attack_plan.target_mothership and all([drone.health >= 80 for drone in self.__class__.fighters]):
                for mothership in self.scene.motherships:
                    if mothership != self.my_mothership:
                        self.attack_plan.start_attack(mothership)
            elif self.attack_plan.target_mothership:
                counter = 0
                for drone in self.__class__.fighters:
                    if drone.offensive:
                        counter += 1
                if counter < ceil(float(len(self.__class__.fighters)) / 2):
                    self.attack_plan.abort_attack(self.__class__.fighters)

            if self.attacking:
                self.attack_mode()

            if not self.is_moving and self.target:
                if self.near(self.target) and self.offensive:
                    pass
                elif self.near(self.target):
                    self.offensive = True
                elif self.near(self.my_mothership) or self.health >= 80:
                    self.offensive = True
                    self.attack_plan.go_to_attack_position(self)
                else:
                    self.move_to_mothership()

            if not self.enemies_alive():
                self.change_role('harvester')

    def enemies_alive(self):
        for drone in self.scene.drones:
            if drone not in self.__class__.my_team and drone.is_alive:
                return True
        else:
            for mothership in self.scene.motherships:
                if mothership != self.my_mothership and mothership.is_alive:
                    return True
            else:
                return False

    def attack_mode(self):
        """атака вражеских дронов или базы в радиусе поражения"""
        if isinstance(self.role, Fighter):
            self.role.attack_mode()
        else:
            raise RoleError('attack_mode: Только истребитель может участвовать в бою')

    def check_for_enemy_drones(self):
        """проверка на вражеских дронов в радиусе поражения"""
        if isinstance(self.role, Fighter):
            return self.role.check_for_enemy_drones()
        else:
            raise RoleError('check_for_enemy_drones: Только истребитель может участвовать в бою')

    def check_target_base(self):
        if isinstance(self.role, Fighter):
            return self.role.check_target_base()
        else:
            raise RoleError('check_target_base: Только истребитель может участвовать в бою')

    def retreat(self):
        """бегство из боя"""
        self.previous_target = Point(self.x, self.y)
        self.offensive = False
        self.attacking = False
        if isinstance(self.target, Asteroid) and self.target in self.__class__.unavailable_asteroids:
            self.__class__.unavailable_asteroids.remove(self.target)
        self.move_to_mothership()


class AttackPlan:

    def __init__(self):
        self.my_mothership = None
        self.target_mothership = None
        self.attack_stage = 0
        self.attack_positions = []
        self.advance_distance = None

    def set_mothership(self, mothership):
        if not self.my_mothership:
            self.my_mothership = mothership

    def start_attack(self, target_mothership):
        self.target_mothership = target_mothership
        self.calculate_attack_stages()
        self.create_attack_positions()

    def go_to_attack_position(self, soldier):
        if self.attack_positions:
            index = soldier.__class__.fighters.index(soldier)
            soldier.target = self.attack_positions[index]
            soldier.move_at(soldier.target)

    def calculate_attack_stages(self):
        """расчет количества этапов наступления"""
        distance = self.my_mothership.distance_to(self.target_mothership)
        stages = int(ceil(distance / 400))
        x = (self.target_mothership.x - self.my_mothership.x) / stages
        y = (self.target_mothership.y - self.my_mothership.y) / stages
        self.advance_distance = Vector(x, y)

    def create_attack_positions(self):
        """создание позиций для атаки"""
        self.attack_positions = []
        main_vector = self.advance_distance * (self.attack_stage + 1)
        central_position = Point(self.my_mothership.x + main_vector.x, self.my_mothership.y + main_vector.y)
        self.attack_positions.append(central_position)

        for angle in [-90, 90]:
            wing_angle = normalise_angle(main_vector.direction + angle)
            wing_vector = Vector.from_direction(wing_angle, 100)
            point1 = Point(central_position.x + wing_vector.x, central_position.y + wing_vector.y)
            if point1.x <= 0 or point1.y <= 0:
                point1 = self.rebase_drone_in_formation(point1, wing_vector)
            self.attack_positions.append(point1)
            point2 = Point(central_position.x + (wing_vector * 2).x, central_position.y + (wing_vector * 2).y)
            if point2.x <= 0 or point2.y <= 0:
                point2 = self.rebase_drone_in_formation(point2, wing_vector)
            self.attack_positions.append(point2)

    @staticmethod
    def rebase_drone_in_formation(point, vector):
        return Point(point.x - vector.x * 5, point.y - vector.y * 5)

    def advance_to_next_position(self):
        """продолжение наступления"""
        self.attack_stage += 1
        self.create_attack_positions()

    def abort_attack(self, fighters):
        self.target_mothership = None
        self.attack_stage = 0
        self.attack_positions = []
        self.advance_distance = None
        for drone in fighters:
            if drone.offensive:
                drone.retreat()


class CantInterceptException(Exception):
    pass


class Role:
    def __init__(self, drone):
        self.unit = drone


class Fighter(Role):
    def __init__(self, drone):
        super().__init__(drone)

    def attack_mode(self):
        """атака вражеских дронов или базы в радиусе поражения"""
        enemy = self.unit.check_for_enemy_drones()
        if enemy:
            self.unit.turn_to(enemy)
            self.unit.gun.shot(enemy)
        elif self.unit.check_target_base():
            self.unit.turn_to(self.unit.attack_plan.target_mothership)
            self.unit.gun.shot(self.unit.attack_plan.target_mothership)
        else:
            self.unit.attacking = False

    def check_for_enemy_drones(self):
        """проверка на вражеских дронов в радиусе поражения"""
        for drone in self.unit.scene.drones:
            if drone not in self.unit.__class__.my_team and self.unit.distance_to(drone) <= 600 and drone.is_alive:
                return drone

    def check_target_base(self):
        if self.unit.attack_plan.target_mothership:
            if self.unit.attack_plan.target_mothership.is_alive:
                return self.unit.distance_to(self.unit.attack_plan.target_mothership) <= 600
            else:
                self.unit.attack_plan.abort_attack(self.unit.__class__.fighters)
                return False
        else:
            return False


class Harvester(Role):
    def __init__(self, drone):
        super().__init__(drone)

    def on_stop_at_asteroid(self, asteroid):
        """Действие при встрече с астероидом"""
        self.unit.previous_target = Point(self.unit.x, self.unit.y)
        if self.unit.next_target:
            self.unit.turn_to(self.unit.next_target)
        elif self.unit.payload + asteroid.payload >= SUFFICIENT_PAYLOAD:
            self.unit.turn_to(self.unit.my_mothership)
        self.unit.load_from(asteroid)

    def on_load_complete(self):
        """Действие при завершении загрузки элериума"""
        if isinstance(self.unit.target, Asteroid) and self.unit.target in self.unit.__class__.unavailable_asteroids:
            if self.unit.target.payload != 0:
                self.unit.__class__.unavailable_asteroids.remove(self.unit.target)
        if self.unit.payload >= SUFFICIENT_PAYLOAD:
            self.unit.move_to_mothership()
        elif self.unit.next_target:
            self.unit.target = self.unit.next_target
            max_payload = SUFFICIENT_PAYLOAD - self.unit.payload
            self.unit.make_route(max_payload)
            self.unit.move_at(self.unit.target)
        else:
            try:
                self.unit.intercept_asteroid()
            except CantInterceptException:
                self.unit.move_to_the_closest_asteroid()

    def make_route(self, max_payload):
        if self.unit.target.payload < max_payload:
            self.unit.next_target = self.unit.get_next_asteroid()
            if self.unit.next_target:
                self.unit.__class__.unavailable_asteroids.append(self.unit.next_target)
        else:
            self.unit.next_target = None

    def try_to_depart(self):
        """Отправление с базы"""
        self.unit.move_to_the_closest_asteroid()
        if self.unit.target == self.unit.my_mothership:
            self.unit.waiting = True

    def move_to_the_closest_asteroid(self):
        """Двигаться к ближайшему астероиду"""
        self.unit.target = self.unit.get_the_closest_asteroid()
        if self.unit.target:
            self.unit.__class__.unavailable_asteroids.append(self.unit.target)
            self.unit.make_route(SUFFICIENT_PAYLOAD)
            self.unit.move_at(self.unit.target)
        else:
            self.unit.target = self.unit.my_mothership
            if self.unit.near(self.unit.my_mothership):
                self.unit.waiting = True
            else:
                self.unit.move_at(self.unit.target)

    def intercept_asteroid(self):
        """
        Попытка перехватить цель у другого дрона,
        если этот дрон находится ближе к цели.
        """
        distances = {}
        for asteroid in self.unit.__class__.unavailable_asteroids:
            distance = self.unit.distance_to(asteroid)
            for drone in self.unit.teammates:
                if drone.target == asteroid and drone.distance_to(asteroid) > distance:
                    distances[asteroid] = [drone, distance]
        for asteroid, drone_distance_pair in distances.items():
            closest_drone = min(distances.values(), key=lambda x: x[1])
            if drone_distance_pair == closest_drone:
                self.unit.previous_target = Point(self.unit.x, self.unit.y)
                self.unit.__class__.unavailable_asteroids.remove(asteroid)
                self.unit.move_to_the_closest_asteroid()
                coords = Point(drone_distance_pair[0].x, drone_distance_pair[0].y)
                drone_distance_pair[0].previous_target = coords
                drone_distance_pair[0].move_to_the_closest_asteroid()
                break
        else:
            raise CantInterceptException

    def get_the_closest_asteroid(self):
        """
        Выбор ближайшего к дрону астероида.
        В первую очередь выбираются богатые элериумом астероиды.
        """

        distances = self.get_distances()

        for drone in self.unit.scene.drones:
            if self.unit.target and drone.target:
                distance_to_target = self.unit.target.distance_to(drone.target)
                self.remove_asteroid_occupied_by_enemy(drone, distance_to_target, distances)

        distances_to_rich = [
            asteroid_distance_pair for asteroid_distance_pair in distances
            if asteroid_distance_pair[0].payload >= SUFFICIENT_PAYLOAD]

        if distances_to_rich:
            return (min(distances_to_rich, key=lambda x: x[1]))[0]
        elif distances:
            return (min(distances, key=lambda x: x[1]))[0]

    def get_next_asteroid(self):
        """Выбрать ближайший к текущей цели астероид"""
        distances = self.get_distances()

        for drone in self.unit.scene.drones:
            if self.unit.target and drone.target:
                distance_to_target = self.unit.distance_to(self.unit.target) + self.unit.target.distance_to(
                    drone.target)
                self.remove_asteroid_occupied_by_enemy(drone, distance_to_target, distances)

        if distances:
            return (min(distances, key=lambda x: x[1]))[0]

    def get_distances(self):
        distances_to_asteroids = [(asteroid, self.unit.distance_to(asteroid)) for asteroid in self.unit.asteroids
                                  if asteroid not in self.unit.__class__.unavailable_asteroids]

        distances_to_dead_enemies = [(drone, self.unit.distance_to(drone)) for drone in self.unit.scene.drones
                                     if
                                     drone not in self.unit.__class__.my_team and not drone.is_alive and not drone.is_empty]

        distances_to_motherships = [(base, self.unit.distance_to(base)) for base in self.unit.scene.motherships
                                    if base != self.unit.my_mothership and not base.is_alive and not base.is_empty]

        return distances_to_asteroids + distances_to_dead_enemies + distances_to_motherships

    def remove_asteroid_occupied_by_enemy(self, drone, distance_to_target, distances):
        if drone not in self.unit.__class__.my_team and drone.distance_to(drone.target) < distance_to_target:
            for asteroid_distance_pair in distances:
                if asteroid_distance_pair[0] == drone.target:
                    distances.remove(asteroid_distance_pair)
                    break


drone_class = PestovDrone
