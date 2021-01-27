from math import sin, radians, cos, degrees, acos

from astrobox.core import Drone
from robogame_engine.geometry import Point, Vector




class Pilot:

    def __init__(self, drone):
        self.drone = drone

    def on_born(self):
        pass

    def on_stop_at_mothership(self):
        pass

    def move_to_target(self, target, distance):
        """Движемся к определенной точке, учитывая номер дрона"""
        field_width, field_height = self.drone.scene.field
        if target.y > field_height / 2 and target.x < field_width / 2:
            # top left
            angle = -90 / (len(self.drone.teammates) + 1) * self.drone.number
        elif target.y > field_height / 2 and target.x > field_width / 2:
            # top right
            angle = -180 + 90 / (len(self.drone.teammates) + 1) * self.drone.number
        elif target.y < field_height / 2 and target.x > field_width / 2:
            # bottom right
            angle = 180 - 90 / (len(self.drone.teammates) + 1) * self.drone.number
        else:
            # bottom left
            angle = 90 / (len(self.drone.teammates) + 1) * self.drone.number
        attack_x = target.x + distance * cos(radians(angle))
        attack_y = target.y + distance * sin(radians(angle))
        self.drone.move_at(Point(abs(attack_x), abs(attack_y)))

    def move_at_enemy_base_point(self):
        self.move_to_target(self.drone.enemy.mothership, 300)

    def move_at_enemy_attack_point(self):
        self.move_to_target(self.drone.enemy, 300)

    def find_next(self):
        """Находит следующий пункт назначения"""
        targets = [drone.next_asteroid for drone in self.drone.teammates if drone.next_asteroid is not None]
        asteroids = [asteroid for asteroid in self.drone.asteroids if asteroid not in targets and not asteroid.is_empty]
        if asteroids:
            asteroids = sorted(asteroids, key=lambda x: x.distance_to(self.drone))
            if not self.drone.is_full:
                self.drone.next_asteroid = asteroids[0]
                return
        self.drone.next_asteroid = self.drone.mothership
        self.find_enemy()

    def find_enemy(self):
        """Ищем следующего дрона для атаки"""
        enemy_drones = [drone for drone in self.drone.scene.drones
                        if drone not in self.drone.teammates and drone != self.drone]
        enemy_drones = [drone for drone in enemy_drones if drone.is_alive and drone != self.drone.mothership]
        if enemy_drones:
            enemy_with_gun = [drone for drone in enemy_drones if drone.have_gun]
            if enemy_with_gun:
                enemy_drones = enemy_with_gun
            enemy_drones = sorted(enemy_drones, key=lambda x: x.distance_to(self.drone))
            self.drone.enemy = enemy_drones[0]

    @property
    def is_not_empty_asteroids(self):
        """Проверяем есть ли еще не пустые астероиды"""
        asteroids = [asteroid for asteroid in self.drone.asteroids if not asteroid.is_empty]
        if asteroids:
            return True
        self.drone.next_asteroid = None

    def normalize_vector(self, vector):
        """Нормализировать вектор"""
        len_vector = vector.module
        return Vector(vector.x / len_vector, vector.y / len_vector)

    def scalar_vector_multiplication(self, vector1, vector2):
        """Скалярное произведение вектора"""
        result = vector1.x * vector2.x + vector1.y * vector2.y
        return result

    @property
    def teammate_on_fireline(self):
        """Проверям находится ли кто-то из команды на линии огня"""
        vector_to_enemy = Vector(self.drone.enemy.x - self.drone.x, self.drone.enemy.y - self.drone.y)
        vector_to_enemy = self.normalize_vector(vector_to_enemy)
        for drone in self.drone.teammates:
            if drone.distance_to(self.drone) <= drone.radius * 1.5:
                return True
            teammate_vector_to_enemy = Vector(self.drone.enemy.x - drone.x, self.drone.enemy.y - drone.y)
            teammate_vector_to_enemy = self.normalize_vector(teammate_vector_to_enemy)
            scalar = self.scalar_vector_multiplication(vector_to_enemy, teammate_vector_to_enemy)
            try:
                angle = degrees(acos(scalar))
            except Exception:
                return True
            if angle < 10 \
                    and (drone.distance_to(self.drone.enemy) < self.drone.distance_to(self.drone.enemy)):
                return True
        else:
            return False

    def find_death_motherships(self):
        """Проверяем, есть ли базы, на которые уже никто не вернется"""
        death_motherships = [mothership for mothership in self.drone.scene.motherships
                             if mothership != self.drone.mothership and not mothership.is_alive
                             and not mothership.is_empty]
        if death_motherships:
            return death_motherships[0]

    def live_enemy_drones(self):
        return [drone for drone in self.drone.scene.drones
                if drone not in self.drone.teammates and drone != self.drone and drone.is_alive
                and drone not in self.drone.scene.motherships]


class DefenderPilot(Pilot):

    def on_born(self):
        self.move_to_target(self.drone.mothership, 350)

    def on_wake_up(self):
        if self.need_to_be_killer():
            self.drone.pilot = KillerPilot(self.drone)
            return
        enemy_drones = self.live_enemy_drones()
        if self.is_not_empty_asteroids:
            self.drone.pilot = ReaperPilot(self.drone)
            return
        if not enemy_drones:
            if self.is_not_empty_asteroids:
                self.drone.pilot = ReaperPilot(self.drone)
            else:
                self.drone.move_at(self.drone.mothership)
            return
        if self.find_death_motherships():
            if self.drone.number <= len(self.drone.teammates) // 2:
                self.drone.pilot = MothershipReaperPilot(self.drone)
                return
        self.move_to_target(self.drone.mothership, 350)
        self.find_enemy()
        if len(enemy_drones) <= 4:
            self.move_at_enemy_attack_point()
        if self.drone.distance_to(self.drone.mothership) > 50:
            if self.teammate_on_fireline:
                self.find_enemy()
            self.drone.turn_to(self.drone.enemy)
            self.drone.gun.shot(self.drone.enemy.mothership)

    def need_to_be_killer(self):
        enemy_drones = self.live_enemy_drones()
        if len(enemy_drones) <= 4:
            return True


class ReaperPilot(Pilot):

    def on_born(self):
        self.find_next()
        self.drone.move_at(self.drone.next_asteroid)

    def on_stop_at_mothership(self):
        self.drone.turn_to(45)
        self.drone.unload_to(self.drone.mothership)

    def on_wake_up(self):
        if not len(self.drone.teammates):
            self.move_to_target(self.drone.mothership, 350)
            self.drone.pilot = DefenderPilot(self.drone)
            return
        if not self.is_not_empty_asteroids:
            self.drone.pilot = DefenderPilot(self.drone)
            return
        self.find_next()
        self.drone.move_at(self.drone.next_asteroid)


class MothershipReaperPilot(Pilot):

    def on_wake_up(self):
        death_mothership = self.find_death_motherships()
        if death_mothership:
            self.drone.death_mothership = death_mothership
            self.drone.move_at(death_mothership)
            return
        self.drone.pilot = DefenderPilot(self.drone)


class KillerPilot(Pilot):

    def on_wake_up(self):
        live_enemies = self.live_enemy_drones()
        if self.is_not_empty_asteroids:
            self.drone.pilot = ReaperPilot(self.drone)
            return
        if not live_enemies:
            self.drone.pilot = ReaperPilot(self.drone)
            return
        self.find_enemy()
        self.move_at_enemy_attack_point()
        if self.drone.distance_to(self.drone.mothership) > 100:
            if self.teammate_on_fireline:
                self.find_enemy()
            self.drone.turn_to(self.drone.enemy)
            if not self.teammate_on_fireline:
                self.drone.gun.shot(self.drone.enemy.mothership)


class BysevDrone(Drone):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.enemy = None
        self.next_asteroid = None
        self.death_mothership = None
        teammates = [dr for dr in self.scene.drones if isinstance(dr, BysevDrone)]
        self.number = teammates.index(self)
        self.pilot = DefenderPilot(self)

    def on_born(self):
        self.pilot.on_born()

    def on_load_complete(self):
        self.pilot.find_next()
        self.move_at(self.next_asteroid)

    def on_stop_at_asteroid(self, asteroid):
        if isinstance(self.pilot, ReaperPilot):
            if not asteroid.is_empty:
                self.turn_to(self.mothership)
                self.load_from(asteroid)

    def on_stop_at_mothership(self, mothership):
        if mothership != self.mothership and not mothership.is_empty:
            self.load_from(mothership)
            return
        if not self.is_empty:
            self.unload_to(mothership)
        self.pilot.on_stop_at_mothership()

    def on_wake_up(self):
        self.pilot.on_wake_up()

    def on_heartbeat(self):
        if self.health <= 50:
            self.move_at(self.mothership)
            self.gun.shot(self.have_gun)


drone_class = BysevDrone