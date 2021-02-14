import math
import random
from collections import defaultdict
from copy import deepcopy

from astrobox.core import Drone, MotherShip, Asteroid
from astrobox.themes.default import MOTHERSHIP_HEALING_DISTANCE
from robogame_engine import GameObject
from robogame_engine.geometry import Point, Vector
from robogame_engine.theme import theme


class BasicDrone(Drone):
    soldiers = []
    attack_range = None
    nearest_asteroids = []
    item_number = 0
    in_general_structure = False
    save_distance = 50
    angles = [0, 60, -60, 30, -30, 45, -45, 15, -15]
    position_for_shooting_back = defaultdict(int)
    first_drone = None
    mothership_healing_distance = 190
    all_shooting_back = False
    mothership_full_health = None
    min_percents_mothership_health = 50
    min_percents_drone_health = 50
    distance_enemy_object_near = 100
    angle_fire_line = 15

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.being_treated = False
        self.target = None
        self.target_copy = None
        self.firing_position = None
        self.attack_place = None
        self.role = None
        self.in_general_structure = False
        self.attack_range = self.gun.shot_distance
        self.angle = None
        self.dead_target = None
        self.cant_shoot = False
        self.target_changed = False
        self.began_to_fire = False
        self.shooting_back = False

    def move_and_make_target_copy(self, target):
        self.move_at(target)
        self.target_copy = target

    def assign_and_count_distance_and_move_at_dead_target(self, target):
        self.dead_target = target
        self.target = target
        self.move_at(target)

    def assign_target_firing_position_and_attack_place(self, target, firing_position=None):
        if firing_position:
            self.firing_position = firing_position
        self.target = target
        self.attack_place = deepcopy(self.target.coord)

    def get_and_move_to_firing_position(self, object):
        firing_position = self.get_place_for_attack(self, object)
        if firing_position:
            self.move_at(firing_position)
            self.assign_target_firing_position_and_attack_place(object, firing_position)
            self.in_general_structure = True
            return firing_position

    def get_tuple_nearest_asteroids(self):
        nearest_asteroids = sorted(
            [list((round(self.distance_to(asteroid), 2), asteroid, asteroid.payload)) for asteroid in self.asteroids if
             not asteroid.is_empty],
            key=lambda el: el[0])
        return nearest_asteroids

    def get_tuple_most_filled_asteroids(self, nearest_asteroids, index_distance_to_asteroid=0, index_asteroid=1,
                                        index_payload_asteroid=2):
        nearest_asteroids = sorted(
            [list((asteroid[index_distance_to_asteroid], asteroid[index_asteroid], asteroid[index_payload_asteroid]))
             for asteroid in nearest_asteroids if asteroid[index_payload_asteroid] > 0],
            key=lambda el: el[2], reverse=True)
        return nearest_asteroids

    def get_alive_our_drones(self):
        drones = [drone for drone in self.scene.drones if drone.team == self.team and drone.is_alive]
        return drones

    def get_enemy_bases(self, soldier):
        bases = [base for base in soldier.scene.motherships if
                 base.team != soldier.team]
        return bases

    def get_enemy_alive_drones(self):
        enemies = [drone for drone in self.scene.drones if drone.team != self.team and drone.is_alive]
        return enemies

    def get_enemy_alive_drones_with_distance(self):
        enemies = [(drone, self.distance_to(drone)) for drone in self.scene.drones if
                   drone.team != self.team and drone.is_alive]
        enemies.sort(key=lambda x: x[1])
        return enemies

    def get_dead_drones_load(self):
        dead_drones = [drone for drone in self.scene.drones if not drone.is_alive and not drone.is_empty]
        return dead_drones

    def get_enemy_dead_load_bases(self):
        return [base for base in self.scene.motherships if
                base.team is not self.team and not base.is_alive and base.payload > 0]

    def get_bases_alive(self):
        return [base for base in self.scene.motherships if base.is_alive]

    def get_enemy_bases_alive(self):
        return [base for base in self.scene.motherships if base.team is not self.team and base.is_alive]

    def check_for_presence_in_teammates(self, nearest_asteroids, nearest_asteroid, number_asteroid,
                                        nearest_asteroid_index, enemies_near_asteroid=True,
                                        index_payload=2, index_asteroid=1, safe_len_enemies=3):
        payload_of_nearest_asteroid = nearest_asteroids[nearest_asteroid_index][index_payload]
        enemies_near_asteroid = [enemy for enemy in self.get_enemy_alive_drones() if enemy.distance_to(
            nearest_asteroid) <= enemy.gun.shot_distance and enemy.gun.cooldown > 0] if enemies_near_asteroid else False
        while (nearest_asteroid in [teammate.target for teammate in
                                    self.teammates] and payload_of_nearest_asteroid == 0) or nearest_asteroid.is_empty or enemies_near_asteroid and len(
            enemies_near_asteroid) >= safe_len_enemies:
            if not nearest_asteroids or number_asteroid + 1 == len(nearest_asteroids):
                return None
            else:
                number_asteroid += 1
                nearest_asteroid = nearest_asteroids[number_asteroid][index_asteroid]
                enemies_near_asteroid = [enemy for enemy in self.get_enemy_alive_drones() if enemy.distance_to(
                    nearest_asteroid) <= enemy.gun.shot_distance and enemy.gun.cooldown > 0] if enemies_near_asteroid else False
        return nearest_asteroids[number_asteroid]

    def check_target(self, nearest_asteroids, remaining_amount_elerium=50,
                     free_space_of_transporter=20, enemies_near_target=True, number_asteroid=0, index_asteroid=1,
                     index_payload=2):
        nearest_asteroid = nearest_asteroids[number_asteroid][index_asteroid]
        nearest_asteroid_index = nearest_asteroids.index(nearest_asteroids[number_asteroid])
        if self.role == 'transporter' and self.free_space >= free_space_of_transporter:
            nearest_asteroids = self.get_tuple_most_filled_asteroids(nearest_asteroids)
            if nearest_asteroids and nearest_asteroids[number_asteroid][
                index_payload] - self.free_space >= remaining_amount_elerium:
                nearest_asteroid = nearest_asteroids[number_asteroid][index_asteroid]
                nearest_asteroid_index = nearest_asteroids.index(nearest_asteroids[number_asteroid])
        return self.check_for_presence_in_teammates(nearest_asteroids, nearest_asteroid, number_asteroid,
                                                    nearest_asteroid_index,
                                                    enemies_near_target)

    def get_nearest_asteroid(self, enemies_near_target=True, index_payload=2, index_asteroid=1):
        if all(drone.target for drone in YurchenkoDrone.soldiers):
            for drone in YurchenkoDrone.soldiers:
                if isinstance(drone.target, Asteroid):
                    drone.target = None
        if not YurchenkoDrone.nearest_asteroids:
            YurchenkoDrone.nearest_asteroids = self.get_tuple_nearest_asteroids()
            if not YurchenkoDrone.nearest_asteroids:
                return None
        target = self.check_target(YurchenkoDrone.nearest_asteroids, enemies_near_target=enemies_near_target)
        if not target:
            return None
        payload_of_nearest_asteroid = target[index_payload]
        target_index = YurchenkoDrone.nearest_asteroids.index(
            target)
        if self.free_space >= payload_of_nearest_asteroid:
            YurchenkoDrone.nearest_asteroids.remove(target)
        else:
            YurchenkoDrone.nearest_asteroids[target_index][index_payload] -= self.free_space
        return target[index_asteroid]

    def go_to_nearest_not_empty_asteroid(self, enemies_near_target=True):
        target = self.get_nearest_asteroid(enemies_near_target)
        if target and not target.is_empty:
            self.move_and_make_target_copy(target)
            return target

    def go_to_asteroid_or_mothership(self, enemies_near_asteroid=True):
        nearest_not_empty_asteroid = self.go_to_nearest_not_empty_asteroid(enemies_near_asteroid)
        if not nearest_not_empty_asteroid or self.cargo.is_full or self.target == nearest_not_empty_asteroid:
            if not self.is_empty:
                self.move_at(self.my_mothership)
            else:
                self.become_shooting_back_and_move()

    def become_shooting_back_and_move(self):
        self.shooting_back = True
        self.role = 'warrior'
        self.move_at(YurchenkoDrone.position_for_shooting_back[self.id])

    def get_place_and_angle(self, soldier, purpose, target, ang):
        place = self.get_place_near(purpose, target, ang)
        teammates_firing_positions_near = [teammate for teammate in self.teammates if
                                           teammate.firing_position and teammate.firing_position.distance_to(
                                               place) <= YurchenkoDrone.save_distance]
        bases_near = [base for base in self.get_bases_alive() if
                      base.distance_to(place) <= YurchenkoDrone.distance_enemy_object_near]
        enemies_near = [enemy for enemy in self.get_enemy_alive_drones() if
                        enemy.distance_to(place) <= YurchenkoDrone.distance_enemy_object_near]
        if place and soldier.valide_place(
                place) and not bases_near and not enemies_near and not teammates_firing_positions_near:
            return place

    def get_enemy_drones_and_bases(self):
        alive_enemy_drones = self.get_enemy_alive_drones_with_distance()
        alive_enemy_bases = self.get_enemy_bases_alive()
        load_enemy_drones = self.get_dead_drones_load()
        enemy_dead_load_bases = self.get_enemy_dead_load_bases()
        return {'alive_enemy_drones': alive_enemy_drones, 'alive_enemy_bases': alive_enemy_bases,
                'load_enemy_drones': load_enemy_drones, 'enemy_dead_load_bases': enemy_dead_load_bases}

    def get_target_turn_and_shoot(self, targets_list, target_number=0):
        target = self.get_target(targets_list, index_target=target_number)
        while self.distance_to(target) > self.gun.shot_distance or target.distance_to(
                target.mothership) <= MOTHERSHIP_HEALING_DISTANCE and target.mothership.is_alive:
            if target_number == len(targets_list):
                return
            target = self.get_target(targets_list, index_target=target_number)
            target_number += 1
        self.assign_turn_and_shoot_object(target)

    def move_at_enemy_base(self, all_enemies, target_number=0):
        target = all_enemies['enemy_dead_load_bases'][target_number]
        while sum([teammate.free_space for teammate in self.teammates if
                   teammate.target == target]) >= target.payload or self.is_full:
            if target_number == len(all_enemies['enemy_dead_load_bases']):
                return
            target = all_enemies['enemy_dead_load_bases'][target_number]
            target_number += 1
        self.assign_and_count_distance_and_move_at_dead_target(target)
        return target

    def move_at_load_enemy_drone(self, all_enemies, target_number=0, enemies_near_target=True):
        target = all_enemies['load_enemy_drones'][target_number]
        enemies_near_target = [enemy for enemy in self.get_enemy_alive_drones() if enemy.distance_to(
            target) <= enemy.gun.shot_distance and (
                                       not enemy.is_moving or enemy.gun.cooldown > 0)] if enemies_near_target else False
        while (target in [teammate.target for teammate in
                          self.teammates]) or enemies_near_target and len(enemies_near_target) >= 2:
            if target_number == len(all_enemies['load_enemy_drones']):
                self.go_to_asteroid_or_mothership()
                return
            target = all_enemies['load_enemy_drones'][target_number]
            target_number += 1
            enemies_near_target = [enemy for enemy in self.get_enemy_alive_drones() if enemy.distance_to(
                target) <= enemy.gun.shot_distance and (
                                           not enemy.is_moving or enemy.gun.cooldown > 0)] if enemies_near_target else False
        self.assign_and_count_distance_and_move_at_dead_target(target)
        return target

    def get_roles(self, main_role, dop_role, amount_main_role):
        alive_our_drones = self.get_alive_our_drones()
        for soldier in alive_our_drones:
            if len([soldier for soldier in alive_our_drones if soldier.role == main_role]) < amount_main_role:
                soldier.role = main_role
            else:
                soldier.role = dop_role

    def check_object_on_fire_line_to_target(self, soldier, target, object):
        on_trajectory = soldier.distance_to(target) >= object.distance_to(target) and self.get_angle(object,
                                                                                                     target) < YurchenkoDrone.angle_fire_line and soldier.distance_to(
            object) < soldier.distance_to(target)
        return on_trajectory

    def get_target(self, targets_list, index_target=0, index_return=None):
        if targets_list:
            target = targets_list[index_target]
            if index_return is not None:
                return target[index_return]
            return target

    def get_place_near(self, point, target, angle):
        """
        Расчет места рядом с point с отклонением angle от цели target

        :param point:
        :param target:
        :param angle:
        :return: new place point
        """

        vec = Vector(point.x - target.x, point.y - target.y)
        vec.rotate(angle)
        return Point(target.x + vec.x, target.y + vec.y)

    def valide_place(self, point: Point):
        """
        Подходит ли это место для атаки. Слишком рядом не должно быть партнеров и на линии огня тоже не должно быть
        партнеров.

        :param point: анализируемое место
        :param target: цель
        :return: True or False
        """
        is_valide = 0 < point.x < theme.FIELD_WIDTH and 0 < point.y < theme.FIELD_HEIGHT
        for partner in self.teammates:
            if not partner.is_alive:
                continue

            is_valide = is_valide and (partner.distance_to(point) >= YurchenkoDrone.save_distance)

        return is_valide

    def get_place_for_attack(self, soldier, target):
        """
        Выбор места для атаки цели, если цель не в радиусе атаки

        :param soldier: атакующий
        :param target: цель/объект атаки
        :return: Point  - место атаки или None - если не выбрано место атаки
        """
        if isinstance(target, GameObject):
            vec = Vector.from_points(target.coord, soldier.coord)
        elif isinstance(target, Point):
            vec = Vector.from_points(target, soldier.coord)
        else:
            raise Exception("target must be GameObject or Point!".format(target, ))

        dist = vec.module
        _koef = 1 / dist
        norm_vec = Vector(vec.x * _koef, vec.y * _koef)
        vec_gunshot = norm_vec * min(int(soldier.attack_range), int(dist))
        purpose = Point(target.coord.x + vec_gunshot.x, target.coord.y + vec_gunshot.y)
        if self.angle is not None and self.being_treated:
            place = self.get_place_and_angle(soldier, purpose, target, self.angle)
            if place:
                return place
        for ang in YurchenkoDrone.angles:
            place = self.get_place_and_angle(soldier, purpose, target, ang)
            if place:
                return place
        return None

    def scalar(self, vec1, vec2):
        return vec1.x * vec2.x + vec1.y * vec2.y

    def get_angle(self, partner: GameObject, target: GameObject):
        """
        Получает угол между векторами self-target и partner-target
        """

        v12 = Vector(self.coord.x - target.coord.x, self.coord.y - target.coord.y)
        v32 = Vector(partner.coord.x - target.coord.x, partner.coord.y - target.coord.y)
        _cos = self.scalar(v12, v32) / (v12.module * v32.module + 1.e-8)
        return math.degrees(math.acos(_cos))

    def move_at_dead_enemy(self):
        if not self.is_full:
            all_enemies = self.get_enemy_drones_and_bases()
            if all_enemies['load_enemy_drones']:
                load_enemy_drone = self.move_at_load_enemy_drone(all_enemies)
                if load_enemy_drone:
                    return
            elif all_enemies['enemy_dead_load_bases']:
                enemy_base = self.move_at_enemy_base(all_enemies)
                if enemy_base:
                    return
        self.get_roles(main_role='transporter', dop_role='transporter', amount_main_role=4)

    def assign_turn_and_shoot_object(self, object):
        self.assign_target_firing_position_and_attack_place(object, self.coord)
        self.turn_to(object)
        self.gun.shot(object)

    def get_destination(self, enemies_near_target=True):
        self.role = 'collector'
        all_enemies = self.get_enemy_drones_and_bases()
        if all_enemies['enemy_dead_load_bases']:
            target = self.move_at_enemy_base(all_enemies)
            if not target:
                if all_enemies['load_enemy_drones']:
                    self.move_at_load_enemy_drone(all_enemies, enemies_near_target=enemies_near_target)
                else:
                    self.go_to_asteroid_or_mothership(enemies_near_target)
        elif all_enemies['load_enemy_drones']:
            self.move_at_load_enemy_drone(all_enemies, enemies_near_target=enemies_near_target)
        else:
            self.go_to_asteroid_or_mothership(enemies_near_target)

    def get_positions_for_shooting_back(self, index_x=0, index_y=1, index_place=0):
        if self.my_mothership.x == self.my_mothership.y == 90:
            places = [(YurchenkoDrone.mothership_healing_distance, -40),
                      (YurchenkoDrone.mothership_healing_distance, 50),
                      (150, 130),
                      (60, YurchenkoDrone.mothership_healing_distance),
                      (-30, YurchenkoDrone.mothership_healing_distance)]
        elif self.my_mothership.x == 90 and self.my_mothership.y == theme.FIELD_HEIGHT - 90:
            places = [(YurchenkoDrone.mothership_healing_distance, 40),
                      (YurchenkoDrone.mothership_healing_distance, -50),
                      (150, -130),
                      (60, -YurchenkoDrone.mothership_healing_distance),
                      (-30, -YurchenkoDrone.mothership_healing_distance)]
        elif self.my_mothership.x == theme.FIELD_WIDTH - 90 and self.my_mothership.y == theme.FIELD_HEIGHT - 90:
            places = [(-YurchenkoDrone.mothership_healing_distance, 40),
                      (-YurchenkoDrone.mothership_healing_distance, -50),
                      (-150, -130),
                      (-60, -YurchenkoDrone.mothership_healing_distance),
                      (30, -YurchenkoDrone.mothership_healing_distance)]
        else:
            places = [(-YurchenkoDrone.mothership_healing_distance, -40),
                      (-YurchenkoDrone.mothership_healing_distance, 50),
                      (-150, 130),
                      (-60, YurchenkoDrone.mothership_healing_distance),
                      (30, YurchenkoDrone.mothership_healing_distance)]
        for drone in YurchenkoDrone.soldiers:
            YurchenkoDrone.position_for_shooting_back[drone.id] = Point(
                self.my_mothership.x + places[index_place][index_x],
                self.my_mothership.y + places[index_place][index_y])
            index_place += 1

    def become_collector_or_shoot_enemy(self, shooting_target_teammates_near_base, target, index_target=0):
        if all(shooting_target_teammates_near_base):
            for drone in self.get_alive_our_drones():
                drone.role = 'collector'
        else:
            enemy_alive_drones = self.get_enemy_alive_drones()
            while target.distance_to(
                    target.mothership) <= MOTHERSHIP_HEALING_DISTANCE and target.mothership.is_alive:
                target = self.get_target(enemy_alive_drones, index_target)
                index_target += 1
                if index_target == len(enemy_alive_drones):
                    return
        self.get_destination()

    def get_action_if_teammate_on_fire_line(self, target, teammate):
        if self.distance_to(target) > teammate.distance_to(target) \
                and self.get_angle(teammate, target) < YurchenkoDrone.angle_fire_line \
                and self.distance_to(teammate) < self.distance_to(target):
            return self.get_firing_position(target)

    def get_firing_position(self, target):
        if not self.in_general_structure:
            firing_position = self.get_and_move_to_firing_position(target)
            return firing_position

    def get_action_if_target_changed_coord_or_enough_far(self, target):
        x_target, y_target = target.coord.x, target.coord.y
        x_attack_place, y_attack_place = self.attack_place.x, self.attack_place.y
        target_changed_coord = x_target != x_attack_place or y_target != y_attack_place
        if target_changed_coord and not isinstance(target, MotherShip) and self.distance_to(
                target) > self.gun.shot_distance or \
                self.distance_to(target) > self.gun.shot_distance and not target.is_moving:
            firing_position = self.get_firing_position(target)
            if firing_position:
                return

    def get_action_for_shooting_back(self, low_mothership_health, target_number):
        if self.being_treated or low_mothership_health:
            self.move_at(YurchenkoDrone.position_for_shooting_back[self.id])
        else:
            enemy_alive_drones_on_mothership = [enemy.distance_to(
                enemy.mothership) <= MOTHERSHIP_HEALING_DISTANCE and enemy.mothership.is_alive and not enemy.is_moving
                                                for enemy in self.get_enemy_alive_drones()]
            enemy_alive_drones = self.get_enemy_alive_drones()
            enemies_far = [self.distance_to(enemy) > self.gun.shot_distance for enemy in enemy_alive_drones if
                           enemy.distance_to(enemy.mothership) > MOTHERSHIP_HEALING_DISTANCE]
            if (all(enemy_alive_drones_on_mothership) or all(
                    enemies_far)) and self.target or not enemy_alive_drones:
                self.shoot_base_or_enemy_or_leave_position(enemy_alive_drones, target_number)
            else:
                self.get_target_turn_and_shoot(enemy_alive_drones)

    def shoot_base_or_enemy_or_leave_position(self, enemy_alive_drones, target_number):
        enemy_bases_in_shot_distance = [base for base in self.get_enemy_bases_alive() if
                                        self.distance_to(base) <= self.gun.shot_distance and not any(
                                            enemy for enemy in self.get_enemy_alive_drones() if
                                            enemy.team == base.team and self.check_object_on_fire_line_to_target(
                                                self, base, enemy))]
        if enemy_bases_in_shot_distance:
            self.target = enemy_bases_in_shot_distance[target_number]
            self.assign_turn_and_shoot_object(self.target)
        elif not enemy_alive_drones:
            self.shooting_back = False
        else:
            self.get_target_turn_and_shoot(enemy_alive_drones)


class YurchenkoDrone(BasicDrone):

    def get_and_shoot_target(self, targets_list, item_number=None, target_number=0):
        target = self.get_target(targets_list, target_number, item_number)
        if isinstance(target, Drone):
            while target.near(target.mothership) and not self.began_to_fire:
                if not targets_list or target_number + 1 == len(targets_list):
                    break
                target_number += 1
                target = self.get_target(targets_list, target_number, item_number)
        self.shoot(target)
        alive_our_drones = self.get_alive_our_drones()
        for drone in alive_our_drones:
            if isinstance(drone.target, Asteroid) and not drone.target.is_empty:
                continue
            drone.target = target

    def change_role_to_warrior_or_get_destination(self):
        if not self.get_enemy_dead_load_bases():
            enemy_bases_alive_without_shooting_drones = [enemy_base for enemy_base in self.get_enemy_bases_alive()
                                                         if not (
                    enemy for enemy in self.get_enemy_alive_drones() if
                    enemy.team == enemy_base.team and enemy_base.distance_to(
                        enemy) <= MOTHERSHIP_HEALING_DISTANCE)]
            if enemy_bases_alive_without_shooting_drones:
                self.role = 'warrior'
                self.get_and_shoot_target(enemy_bases_alive_without_shooting_drones)
                return
        self.shooting_back = True
        self.get_destination(enemies_near_target=False)

    def shoot(self, target):
        if isinstance(target, Drone):
            shooting_target_teammates_near_base = [
                teammate.distance_to(teammate.mothership) <= MOTHERSHIP_HEALING_DISTANCE and teammate.gun.cooldown > 0
                for teammate in target.teammates]
            if target.gun.cooldown > 0 and target.distance_to(
                    target.mothership) <= MOTHERSHIP_HEALING_DISTANCE and target.mothership.is_alive:
                self.become_collector_or_shoot_enemy(shooting_target_teammates_near_base, target)
                return

        if self.distance_to(self.my_mothership) < YurchenkoDrone.distance_enemy_object_near and self.began_to_fire:
            self.get_and_move_to_firing_position(target)
            return

        for teammate in self.teammates:
            if not teammate.is_alive:
                continue

            action = self.get_action_if_teammate_on_fire_line(target, teammate)
            if action:
                return

        if not self.valide_place(self.coord):
            firing_position = self.get_firing_position(target)
            if firing_position:
                return

        if self.attack_place:
            action = self.get_action_if_target_changed_coord_or_enough_far(target)
            if action:
                return

        self.assign_turn_and_shoot_object(target)

    def shoot_or_change_target(self, min_percents_mothership_health=50, target_number=0):
        low_mothership_health = self.my_mothership.health / YurchenkoDrone.mothership_full_health * 100 <= min_percents_mothership_health
        if self.shooting_back or low_mothership_health:
            self.get_action_for_shooting_back(low_mothership_health, target_number)
        elif self.target is not None and self.target.is_alive:
            self.shoot(self.target)
        else:
            all_enemies = self.get_enemy_drones_and_bases()
            if all_enemies['alive_enemy_drones']:
                self.get_and_shoot_target(all_enemies['alive_enemy_drones'], item_number=0)
            elif all_enemies['alive_enemy_bases']:
                self.get_and_shoot_target(all_enemies['alive_enemy_bases'])
            elif all_enemies['load_enemy_drones']:
                target = self.move_at_load_enemy_drone(all_enemies)
                if not target and all_enemies['enemy_dead_load_bases']:
                    self.move_at_enemy_base(all_enemies)
            elif all_enemies['enemy_dead_load_bases']:
                self.move_at_enemy_base(all_enemies)
        self.role = 'warrior'

    def on_wake_up(self):
        if self.health <= YurchenkoDrone.min_percents_drone_health:
            self.move_at(self.my_mothership)
            self.in_general_structure = False
            self.being_treated = True
        elif self.dead_target and not self.dead_target.is_empty:
            self.load_from(self.dead_target)
        elif (self.my_mothership.payload <= max(
                [enemy_base.payload for enemy_base in
                 self.get_enemy_bases(
                     self)])) and not any(
            enemy.distance_to(YurchenkoDrone.position_for_shooting_back[self.id]) <= self.gun.shot_distance for enemy in
            self.get_enemy_alive_drones() if enemy.gun.cooldown > 0):
            self.get_destination()
        else:
            self.shoot_or_change_target()

    def on_born(self):
        if YurchenkoDrone.first_drone is None:
            YurchenkoDrone.first_drone = self.id
            YurchenkoDrone.mothership_full_health = self.my_mothership.health
            YurchenkoDrone.soldiers = self, *self.teammates
            self.get_roles(main_role='collector', dop_role='transporter', amount_main_role=4)
            self.get_positions_for_shooting_back()
        if self.role == 'warrior':
            if not self.shooting_back:
                alive_enemy_drones = self.get_enemy_alive_drones_with_distance()
                middle_target_number = len(alive_enemy_drones) // 2
                self.get_and_shoot_target(alive_enemy_drones, item_number=0, target_number=middle_target_number)
            else:
                self.move_at(YurchenkoDrone.position_for_shooting_back[self.id])
            self.began_to_fire = True
        else:
            self.target = self.get_nearest_asteroid(enemies_near_target=False)
            self.move_at(self.target)
        self.target_copy = self.target

    def on_stop_at_asteroid(self, asteroid):
        if self.role == 'warrior':
            self.shoot_or_change_target()
        else:
            if isinstance(self.target_copy, Asteroid) and self.target_copy.payload >= self.free_space:
                self.turn_to(self.my_mothership)
                self.target_copy = None
            self.load_from(asteroid)

    def on_load_complete(self):
        if self.role == 'warrior':
            self.move_at_dead_enemy()
        elif self.health <= YurchenkoDrone.min_percents_drone_health:
            self.move_at(self.my_mothership)
        self.go_to_asteroid_or_mothership(enemies_near_asteroid=True)

    def on_stop_at_mothership(self, mothership):
        if self.role == 'warrior' and not self.dead_target:
            self.shoot_or_change_target()
            self.being_treated = False
            self.in_general_structure = True
            return
        if self.target:
            self.turn_to(self.target)
        else:
            self.turn_to(random.choice(self.asteroids))
        self.unload_to(mothership)

    def on_unload_complete(self):
        self.target = None
        if any(enemy.distance_to(YurchenkoDrone.position_for_shooting_back[self.id]) <= enemy.gun.shot_distance for
               enemy in self.get_enemy_alive_drones() if enemy.gun.cooldown > 0) or self.my_mothership.payload > max(
            [enemy_base.payload for enemy_base in self.get_enemy_bases(self)]):
            self.become_shooting_back_and_move()
        else:
            self.change_role_to_warrior_or_get_destination()


drone_class = YurchenkoDrone
