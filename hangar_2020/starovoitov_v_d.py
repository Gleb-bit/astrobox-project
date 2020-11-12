import logging
import math
from collections import defaultdict

from astrobox.core import Drone
from astrobox.core import MotherShip
from robogame_engine.geometry import Vector, Point
from robogame_engine.theme import theme

logging.basicConfig(filename="my_dist_drone.log", filemode="w", level=logging.INFO)


class DroneAction(Drone):
    _my_team = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.enemy = None
        self.point = None
        self.guard_coord = None

        self.strategy = None
        self.print_stats = False
        self.prev_enemy_target = None

        self.limit_health = 50
        self.distance_without_cargo = 0
        self.distance_with_not_full_cargo = 0
        self.distance_full_cargo = 0
        self.x_distance = 0.5
        self.target_payload_at_first = 0

    def load_from(self, source):
        logging.info('load')
        super().load_from(source)
        self.strategy.load_from(source)

    def unload_to(self, target):
        logging.info('unload')
        super().unload_to(target)
        self.strategy.unload_to(target)

    def move_at(self, target, speed=None):
        if self.print_stats:
            if self.is_empty:
                self.distance_without_cargo += self.distance_to(target)
            else:
                if self.is_full:
                    self.distance_full_cargo += self.distance_to(target)
                else:
                    self.distance_with_not_full_cargo += self.distance_to(target)
        super().move_at(target, speed)

    def move_at_with_stop(self, target):
        logging.info('move with stop')
        if self.distance_to(target) > 100:
            new_target = self.get_near_point(point=target.coord, x_distance=0.1)
            self.move_at(new_target)
        self.move_at(target)

    @property
    def get_new_asteroid(self):
        return self.strategy.get_new_asteroid

    @property
    def my_team(self):
        return [drone for drone in self._my_team if drone.is_alive]

    @property
    def enemies(self):
        return [(drone, drone.distance_to(drone.mothership)) for drone in self.scene.drones
                if drone.is_alive and drone.team is not self.team]  # sorted by far from mother ship

    @property
    def enemies_ships(self):
        return [ship for ship in self.scene.motherships if ship is not self.my_mothership and ship.is_alive]

    def on_stop_at_asteroid(self, asteroid):
        logging.info('stop at asteroid')
        self.strategy.on_stop_at_asteroid(asteroid)

    def on_load_complete(self):
        logging.info('load complete')
        self.strategy.on_load_complete()

    def on_stop_at_mothership(self, mothership):
        logging.info('stop at mothership')
        self.strategy.on_stop_at_mothership(mothership)

    def on_stop_at_point(self, target):
        logging.info('stop at point')
        self.strategy.on_stop_at_point(target)

    def on_stop(self):
        self.strategy.on_stop()

    def on_wake_up(self):
        self.strategy.on_wake_up()

    def on_unload_complete(self):
        logging.info('unload complete')
        self.strategy.on_unload_complete()

    def fast_turning_to(self, point):
        vector_to_shot = Vector.from_points(self.coord, point)
        point_from_shooting = self.get_near_point(point=point, x_distance=10 ** -10)
        self.move_at(point_from_shooting)
        if math.fabs(self.vector.direction - vector_to_shot.direction) < 10:
            return True

    @staticmethod
    def out_boundaries(point):
        if point.x < 0 or point.y < 0 or point.x > theme.FIELD_WIDTH or point.y > theme.FIELD_HEIGHT:
            return True
        else:
            return False

    def get_near_point(self, point, distance=80, delta_angle=60, x_distance=0.0, start_point=None):
        if start_point is None:
            start_point = self.coord
        vector_between_points = Vector.from_points(start_point, point)
        angle_to_point = vector_between_points.direction
        if x_distance != 0:
            distance = vector_between_points.module * x_distance
            delta_angle = 0
        new_angle_grad = angle_to_point + delta_angle
        new_angle = Vector.to_radian(int(new_angle_grad))
        new_x = start_point.x + distance * math.cos(new_angle)
        new_y = start_point.y + distance * math.sin(new_angle)
        new_point = Point(new_x, new_y)
        return new_point

    @staticmethod
    def check_on_points_errors(first_coord, second_coord):
        if hasattr(first_coord, 'coord'):
            first_coord = first_coord.coord
        if hasattr(second_coord, 'coord'):
            second_coord = second_coord.coord
        return first_coord, second_coord

    @classmethod
    def get_distance_from_points(cls, first_point, second_point):
        first_point, second_point = cls.check_on_points_errors(first_point, second_point)
        enemy_vector = Vector.from_points(first_point, second_point)
        enemy_distance_to_target = Vector.calc_module(enemy_vector.x, enemy_vector.y)
        return enemy_distance_to_target

    def get_base_guard_coord(self, distance=180, attack_cord=None, delta_angle=-45):
        if attack_cord is None:
            base_coord = self.mothership.coord
            delta_angle = 27
        else:
            base_coord = attack_cord
        if base_coord.x < 300 and base_coord.y < 300:
            angle = 315
        elif base_coord.x < 300 and 300 < base_coord.y:
            angle = 225
        elif base_coord.x > 300 and 300 > base_coord.y:
            angle = 45
        else:
            angle = 135
        angle = angle if attack_cord is None else angle + 2 * delta_angle
        for index_drone, drone in enumerate(self.my_team):
            if drone == self:
                if index_drone == 0:
                    new_angle = angle
                elif index_drone == 1:
                    new_angle = angle + delta_angle
                elif index_drone == 2:
                    new_angle = angle - delta_angle
                elif index_drone == 3:
                    new_angle = angle + 2 * delta_angle
                elif index_drone == 4:
                    new_angle = angle - 2 * delta_angle
                elif index_drone == 5:
                    new_angle = angle + 3 * delta_angle
                elif attack_cord is None and index_drone > 5:
                    distance = 0.001
                    new_angle = angle
                else:
                    new_angle = angle + index_drone * delta_angle
                guard_coord = self.get_near_point(start_point=base_coord, point=base_coord,
                                                  distance=distance, delta_angle=new_angle)
                return guard_coord

    def healing_limits(self):
        if self.distance_to(self.mothership) > 200 and self.limit_health != 80:
            logging.info(f"Changing healing_limit to 80, {self}")
            self.limit_health = 80
        elif self.distance_to(self.mothership) < 200 and self.limit_health != 50:
            logging.info(f"Changing healing_limit to 50, {self}")
            self.limit_health = 50

    def damage_taken(self, damage=0):
        self.healing_limits()
        if self.coord != self.guard_coord or not self.near(self.mothership):
            if self.health - damage < self.limit_health:
                if self.distance_to(self.mothership) > 200:
                    self.move_at_position_near_base()
                else:
                    for drone in self.teammates:
                        if self.near(drone):
                            self.move_at(self.mothership)
                            break
        super().damage_taken(damage)

    def move_at_position_near_base(self):
        if self.is_empty:
            self.guard_coord = self.get_base_guard_coord()
            self.point = self.guard_coord
        else:
            self.point = self.mothership
        self.move_at(self.point)

    def print_stat(self):
        res = f'|{"-" * 28} Drones {"-" * 28}|\n' \
              f'|{"Distance":^64}|\n' \
              f'|{"Drone Full cargo":^20}|{"Drone Not full cargo":^22}|{"Drone Full empty":^20}|\n' \
              f'|{self.distance_full_cargo:^20.2f}|{self.distance_with_not_full_cargo :^22.2f}' \
              f'|{self.distance_without_cargo:^20.2f}|\n'
        print(res)


class Scenario:
    def __init__(self, drone):
        self.drone = drone

    def start(self):
        self.drone.guard_coord = self.drone.get_base_guard_coord()

    def on_stop(self):
        pass


class Hunter(Scenario):
    def __init__(self, drone):
        super().__init__(drone)
        self.counter = 0

    def start(self):
        logging.info(f"Hunter, {self.drone}")
        super().start()

    def get_new_asteroid(self):
        pass

    def load_from(self, source):
        self.shoot_avoid_damage()

    def unload_to(self, target):
        middle_point = Point(x=600, y=300)
        self.drone.turn_to(middle_point)

    def on_load_complete(self):
        if self.drone.is_full:
            self.drone.move_at_position_near_base()
        else:
            self.shoot_avoid_damage()

    def on_unload_complete(self):
        self.drone.move_at_position_near_base()
        self.shoot_avoid_damage()

    def on_stop_at_point(self, target):
        self.shoot_avoid_damage()

    def on_stop_at_mothership(self, mothership):
        if mothership == self.drone.mothership and not self.drone.is_empty:
            self.drone.unload_to(mothership)
        else:
            self.drone.load_from(mothership)

    def on_stop_at_asteroid(self, asteroid):
        if not asteroid.is_empty:
            self.drone.load_from(asteroid)
        self.shoot_avoid_damage()

    def on_wake_up(self):
        self.shoot_avoid_damage()

    def choose_enemy_or_ship(self):
        logging.info(f"Choosing enemy, {self.drone}")
        all_enemies = self.drone.enemies
        if all_enemies:
            drones_list = sorted(all_enemies, key=lambda items: items[1], reverse=True)
            return self.choose_enemy_drone(drones_list)
        elif self.drone.enemies_ships:
            return self.drone.enemies_ships[0]
        self.drone.point = self.drone.get_base_guard_coord()
        self.drone.strategy = CleanerCollector(self.drone)
        self.drone.strategy.start()

    def choose_enemy_drone(self, drones_list):
        for e_drone, distance_to_e_drone in drones_list:
            if self.drone.get_distance_from_points(self.drone.mothership.coord, e_drone.coord) < 800 \
                    or not e_drone.mothership.is_alive:
                return e_drone
            elif distance_to_e_drone > 200:
                return e_drone
            elif distance_to_e_drone > 90:
                return e_drone
        else:
            return drones_list[0][0]

    def shoot_avoid_damage(self):
        enemy = self.try_to_resolve_healing_problem()
        if not enemy:
            return
        if enemy is not None and enemy.is_alive:
            if enemy is False or enemy is None:
                print("saDas")
            point_to_shoot = self.coord_to_shoot(enemy)
            if self.ready_and_in_position(enemy, point_to_shoot) and self.drone.fast_turning_to(point_to_shoot):
                logging.info(f"Hunter shooting, {self.drone}")
                self.drone.gun.shot(point_to_shoot)
        else:
            self.drone.enemy = self.choose_enemy_or_ship()

    def try_to_resolve_healing_problem(self):
        enemy = self.choose_enemy_or_ship()
        self.drone.point = self.drone.coord
        self.drone.enemy = enemy
        if isinstance(enemy, Drone) and enemy.mothership.is_alive and enemy.is_alive:
            if self.winner():
                self.drone.strategy = WinnerStrategy(self.drone)
                self.drone.strategy.start()
                return False
            elif self.drone.health < self.drone.limit_health:
                self.drone.move_at_position_near_base()
                return False
            elif self.far_from_enemies_object:
                self.drone.strategy = SafeCollector(self.drone)
                self.drone.strategy.start()
                return False
            elif self.need_defend():
                self.drone.strategy = SafeWaiter(self.drone)
                self.drone.strategy.start()
                return False
            elif self.ships_without_drones and self.neighborhood and enemy.distance_to(self.drone) > 650:
                self.drone.strategy = SafeBaseDestroyer(self.drone)
                self.drone.strategy.start()
                return False
            elif self.attack_weak_enemy_base(enemy) and len(self.drone.enemies) < 7:
                if 90 < enemy.distance_to(enemy.mothership) < 200:
                    return self.attack_week_base(enemy)
                else:
                    return enemy
            elif enemy.distance_to(self.drone.mothership) < 800:
                return self.try_to_be_not_honest(enemy)
            elif self.time_to_waite():
                self.drone.strategy = SafeWaiter(self.drone)
                self.drone.strategy.start()
                return False
        return enemy

    def attack_week_base(self, enemy):
        vector_to_shoot = Vector.from_points(self.drone.coord, enemy.mothership.coord)
        if self.calculation_if_can_damage(enemy.coord, vector_to_shoot, 200, angle_coefficient=10 * 580):
            point = self.calculate_point_to_damage_base(enemy)
            if point:
                self.drone.point = point
            else:
                self.drone.move_at_position_near_base()
            if self.drone.near(self.drone.point):
                return enemy.mothership
            else:
                self.drone.move_at(self.drone.point)
                return False
        else:
            return enemy.mothership

    def need_defend(self, counter=0):
        if self.drone.enemies:
            for drone in self.drone.enemies:
                if drone[0] is None:
                    print('dronecyka')
                if drone[0].distance_to(self.drone.mothership) < 750:
                    counter += 1
            if counter >= 4:
                return True
        return False

    def attack_weak_enemy_base(self, enemy):
        enemy_team = [drone for drone in self.drone.enemies if drone[0].team == enemy.team]
        if len(enemy_team) * 3 <= len(self.drone.my_team) and \
                self.drone.distance_to(enemy.mothership) < theme.FIELD_WIDTH and enemy.mothership.is_alive:
            return True
        else:
            return False

    def winner(self):
        sum_asteroids_payload = sum([asteroid.payload for asteroid in self.drone.scene.asteroids])
        sum_enemy_payload = sum([mothership.payload for mothership in self.drone.enemies_ships])
        sum_drone_payload = sum([drone.payload for drone in self.drone.scene.drones
                                 if drone.team is not self.drone.team])
        if sum_drone_payload + sum_enemy_payload + sum_asteroids_payload < self.drone.mothership.payload:
            return True
        else:
            return False

    def time_to_waite(self):
        sum_asteroids_payload = sum([asteroid.payload for asteroid in self.drone.scene.asteroids])
        time_to_waite = True
        ships = []
        for ship in self.drone.enemies_ships:
            if sum_asteroids_payload + ship.payload > self.drone.mothership.payload:
                time_to_waite = False
                ships.append(ship)
        if not time_to_waite:
            for ship in ships:
                ship_drones = [drone for drone in self.drone.enemies if drone[0].team == ship.team]
                len_near_base = len([drone for drone in ship_drones if drone[1] < 200])
                ratio = len(ship_drones) / max(len_near_base, 1)
                if ship.payload < self.drone.mothership.payload and ratio < 2:
                    time_to_waite = True
        return time_to_waite

    def try_to_be_not_honest(self, enemy):
        vector_to_enemy = Vector.from_points(self.drone.coord, enemy.coord)
        delta_angle = math.fabs(180 - vector_to_enemy.direction - enemy.direction)
        if self.drone.near(self.drone.guard_coord) or delta_angle < 10:
            return enemy
        else:
            self.drone.strategy = SafeWaiter(self.drone)
            self.drone.strategy.start()
            return False

    @property
    def far_from_enemies_object(self):
        far_from_enemies_object = SafeCollector(self.drone).get_new_asteroid
        if not far_from_enemies_object or self.drone.distance_to(far_from_enemies_object) > 1000:
            return False
        else:
            return True

    @property
    def neighborhood(self):
        e_coord = self.ships_without_drones[0].coord
        m_coord = self.drone.mothership.coord
        if e_coord.x == m_coord.x or e_coord.y == m_coord.y:
            return True

    @property
    def ships_without_drones(self):
        ships_without_drones = []
        for ship in self.drone.enemies_ships:
            len_enemy_team = len([drone for drone, distance_to_mothership in self.drone.enemies
                                  if drone.team == ship.team and distance_to_mothership > 90])
            if len_enemy_team == 0 and ship.payload > 20 and ship.is_alive:
                ships_without_drones.append(ship)
        return ships_without_drones

    def calculate_point_to_damage_base(self, enemy, distance_limit=680):
        points = defaultdict(int)
        for angle in range(0, 360, 5):
            base_point = (self.drone.get_base_guard_coord(attack_cord=enemy.mothership.coord,
                                                          distance=distance_limit, delta_angle=angle))
            distance_from_enemy_to_point = self.drone.get_distance_from_points(base_point, enemy.coord)
            if not self.drone.out_boundaries(base_point):
                points[base_point] = distance_from_enemy_to_point
        points = sorted(points.items(), key=lambda item: item[1], reverse=True)
        for point in points.copy():
            if self.removing_not_fitting_points(enemy, point[0]):
                points.remove(point)
        if points:
            for new_point in points:
                if self.drone.get_distance_from_points(new_point[0], self.drone.mothership) < 200:
                    return new_point[0]
            else:
                min_dist_to_base = 2000
                min_point = None
                for point in points:
                    dist_to_base = self.drone.get_distance_from_points(self.drone.mothership.coord, point[0])
                    if dist_to_base < min_dist_to_base:
                        min_dist_to_base = dist_to_base
                        min_point = point[0]
                return min_point
        return False

    def removing_not_fitting_points(self, enemy, point):
        for motherhip in self.drone.scene.motherships:
            if self.drone.get_distance_from_points(point, motherhip.coord) < 100 and motherhip.is_alive:
                return True
        for drone in self.drone.teammates:
            if self.drone.get_distance_from_points(point, drone.point) < 90:
                return True
        vector_to_shoot = Vector.from_points(point, enemy.mothership.coord)
        if self.calculation_if_can_damage(enemy.coord, vector_to_shoot, 20, angle_coefficient=10 * 580):
            return True

    def check_distance(self, point_to_shoot, enemy):
        shot_distance = 690 if isinstance(enemy, MotherShip) else 620
        if self.drone.distance_to(point_to_shoot) > shot_distance:
            self.drone.point = self.drone.get_near_point(point=enemy.coord, x_distance=0.1)
            return False
        else:
            return True

    def ready_and_in_position(self, enemy, point_to_shoot):
        if not self.check_distance(point_to_shoot, enemy) or \
                self.can_damage_team_or_base(point_to_shoot, check_list=self.drone.teammates) or \
                self.can_damage_team_or_base(point_to_shoot, check_list=[self.drone.mothership]):
            self.drone.move_at(self.drone.point)
            return False
        elif self.drone.gun.can_shot:
            logging.info(f"Hunter in position and ready, {self.drone}")
            return True
        else:
            self.drone.fast_turning_to(point_to_shoot)

    def can_damage_team_or_base(self, point_to_shoot, check_list, dist_rec=80, angle_rec=60):
        point_changed = False
        self_coord = self.drone.point
        self_coord, mate_coord = self.drone.check_on_points_errors(self_coord, point_to_shoot)
        vector_to_shot = Vector.from_points(self_coord, point_to_shoot)
        for mate in check_list:
            close_distance = 80 if isinstance(mate, Drone) else 120
            if mate.is_moving:
                mate_coord = mate.coord
            else:
                mate_coord = mate.point if hasattr(mate, 'point') else mate.coord
            can_damage_true = self.calculation_if_can_damage(mate_coord, vector_to_shot, close_distance)
            if can_damage_true:
                point_changed = True
                while can_damage_true:
                    self.drone.point = self.avoid_damage(point_to_shoot, mate, distance=dist_rec, delta_angle=angle_rec)
                    can_damage_true = self.calculation_if_can_damage(mate_coord, vector_to_shot, close_distance)
                    dist_rec += 50
                    if dist_rec > 350 or self.drone.out_boundaries(self.drone.point):
                        angle_rec += 10
                        dist_rec = 80
                else:
                    check_list.remove(mate)
                    self.can_damage_team_or_base(point_to_shoot, check_list, dist_rec, angle_rec)
        return True if point_changed else False

    def calculation_if_can_damage(self, mate_coord, vector_to_shot, close_distance, angle_coefficient=15 * 580):
        self_coord = self.drone.point
        self_coord, mate_coord = self.drone.check_on_points_errors(self_coord, mate_coord)
        if self_coord is None or mate_coord is None:
            return False
        vector_to_drone = Vector.from_points(self_coord, mate_coord)
        dist_to_drone = vector_to_drone.module if vector_to_drone.module > 0 else 1
        delta_angle = math.fabs(vector_to_drone.direction - vector_to_shot.direction)
        delta_angle = delta_angle if delta_angle < 180 else 360 - delta_angle
        delta_dist = vector_to_shot.module - dist_to_drone
        correct_angle = angle_coefficient / dist_to_drone
        vector_condition = correct_angle > delta_angle and delta_dist > 10
        dist_condition = self.drone.get_distance_from_points(self_coord, mate_coord) < close_distance
        return dist_condition or vector_condition

    def avoid_damage(self, point_to_shoot, mate, distance=100, delta_angle=60):
        new_point_max = self.drone.get_near_point(point_to_shoot, distance=distance, delta_angle=delta_angle)
        new_point_min = self.drone.get_near_point(point_to_shoot, distance=distance, delta_angle=-delta_angle)
        if hasattr(mate, 'point') and mate.point is not None:
            mate_point_to_point_max = self.drone.get_distance_from_points(mate.point, new_point_max)
            self_point_to_point_max = self.drone.get_distance_from_points(self.drone.point, new_point_max)
            condition = mate_point_to_point_max > self_point_to_point_max
        else:
            mate_coord_to_point_max = mate.distance_to(new_point_max)
            self_coord_to_point_max = self.drone.distance_to(new_point_max)
            condition = mate_coord_to_point_max > self_coord_to_point_max
        point = new_point_max if condition else new_point_min
        if self.drone.out_boundaries(point):
            point = self.drone.guard_coord
        return point

    def determine_point_to_shoot_from_vector(self, e_coord, e_vector, speed_drone=1, speed_shoot=2):
        time_to_e = self.drone.get_distance_from_points(self.drone.point, e_coord) / speed_shoot
        e_dist_while_shooting = time_to_e * speed_drone
        e_angle = Vector.to_radian(e_vector.direction)
        meeting_point_x = e_dist_while_shooting * math.cos(e_angle)
        meeting_point_y = e_dist_while_shooting * math.sin(e_angle)
        meeting_point = Point(e_coord.x + meeting_point_x, e_coord.y + meeting_point_y)
        return meeting_point

    def coord_to_shoot(self, enemy):
        if enemy.is_moving:

            if enemy.target is None or not hasattr(enemy.target, 'coord'):
                point_to_shoot = self.determine_point_to_shoot_from_vector(e_coord=enemy.coord, e_vector=enemy.vector)
            else:
                if self.drone.prev_enemy_target == enemy.target:
                    point_to_shoot = self.try_to_predict_target(enemy)
                else:
                    self.drone.prev_enemy_target = enemy.target
                    point_to_shoot = self.coord_to_shoot(enemy)
        else:
            point_to_shoot = enemy.coord
        return point_to_shoot

    def try_to_predict_target(self, enemy, drone_speed=1, shot_speed=2):
        enemy_distance_to_target = self.drone.get_distance_from_points(enemy.coord, enemy.target.coord)
        distance_me_to_target = self.drone.get_distance_from_points(self.drone.point, enemy.target.coord)
        delta_time_drone = enemy_distance_to_target / drone_speed
        delta_time_shot = distance_me_to_target / shot_speed
        if delta_time_shot < delta_time_drone or enemy.target.payload == 0:
            point_to_shoot = self.determine_point_to_shoot_from_vector(enemy.coord, enemy.vector)
        else:
            point_to_shoot = enemy.target.coord
        return point_to_shoot


class SafeWaiter(Hunter):
    def start(self):
        logging.info(f"SafeWaiter start, {self.drone}")
        super().start()

    def shoot_avoid_damage(self):
        logging.info(f"SafeWaiter shooting, {self.drone}")
        enemy = self.choose_enemy_or_ship()
        self.drone.enemy = enemy
        if not self.drone.near(self.drone.guard_coord):
            self.drone.move_at_position_near_base()
            return
        point_to_shoot = self.coord_to_shoot(enemy)
        if len(self.drone.enemies) != 0 and enemy.mothership.payload < self.drone.mothership.payload \
                and self.try_to_resolve_healing_problem():
            if self.can_damage_team_or_base(point_to_shoot, self.drone.teammates) \
                    or self.can_damage_team_or_base(point_to_shoot, [self.drone.mothership]):
                self.drone.point = self.drone.get_base_guard_coord()
                return
            if self.drone.gun.can_shot and self.drone.fast_turning_to(point_to_shoot):
                self.drone.gun.shot(point_to_shoot)
            else:
                self.drone.fast_turning_to(point_to_shoot)
        else:
            self.drone.strategy = Hunter(self.drone)
            self.drone.strategy.start()

    def can_damage_team_or_base(self, point_to_shoot, check_list, dist_rec=80, angle_rec=60):
        self_coord = self.drone.point
        self_coord, mate_coord = self.drone.check_on_points_errors(self_coord, point_to_shoot)
        vector_to_shot = Vector.from_points(self_coord, point_to_shoot)
        for mate in check_list:
            close_distance = 80 if isinstance(mate, Drone) else 120
            mate_coord = mate.coord
            can_damage_true = self.calculation_if_can_damage(mate_coord, vector_to_shot, close_distance,
                                                             angle_coefficient=5 * 580)
            if can_damage_true:
                return can_damage_true

    def choose_enemy_drone(self, drones_list):
        for e_drone, distance_to_e_drone in drones_list:
            if self.drone.get_distance_from_points(self.drone.mothership.coord, e_drone.coord) < 800:
                return e_drone
        else:
            return drones_list[0][0]

    def try_to_resolve_healing_problem(self):
        enemy = self.drone.enemy
        if len(self.drone.my_team) == 1:
            return True
        if isinstance(enemy, Drone) and enemy.mothership.is_alive:
            far_from_enemies_object = SafeCollector(self.drone).get_new_asteroid
            if far_from_enemies_object or self.attack_weak_enemy_base(enemy):
                return False
            elif self.ships_without_drones and self.neighborhood:
                return False
            else:
                return True
        return False


class WinnerStrategy(SafeWaiter):
    def shoot_avoid_damage(self):
        logging.info(f"Winner shooting, {self.drone}")
        enemy = self.choose_enemy_or_ship()
        if not self.drone.near(self.drone.guard_coord):
            self.drone.move_at_position_near_base()
            return
        if enemy is not None:
            point_to_shoot = self.coord_to_shoot(enemy)
            if self.can_damage_team_or_base(point_to_shoot, self.drone.teammates) \
                    or self.can_damage_team_or_base(point_to_shoot, [self.drone.mothership]):
                self.drone.point = self.drone.get_base_guard_coord()
                return
            if self.drone.gun.can_shot and self.drone.fast_turning_to(point_to_shoot):
                self.drone.gun.shot(point_to_shoot)
        else:
            self.drone.strategy = Hunter(self.drone)
            self.drone.strategy.start()

    def choose_enemy_or_ship(self):
        logging.info(f"Choosing enemy, {self.drone}")
        all_enemies = self.drone.enemies
        if all_enemies:
            enemy = all_enemies[0][0]
            for drone, _ in all_enemies:
                if drone.distance_to(self.drone) < enemy.distance_to(self.drone):
                    enemy = drone
            return enemy
        else:
            self.drone.point = self.drone.get_base_guard_coord()
            self.drone.strategy = CleanerCollector(self.drone)
            self.drone.strategy.start()


class SafeBaseDestroyer(Hunter):
    def on_wake_up(self):
        self.drone.strategy = Hunter(self.drone)
        self.drone.strategy.start()

    def start(self):
        logging.info(f"SafeBaseDestroyer start, {self.drone}")
        super().start()
        self.drone.move_at_position_near_base()

    def choose_enemy_drone(self, drones_list):
        distance_to_me = defaultdict(int)
        for e_drone, distance_to_e_drone in drones_list:
            distance_to_me[e_drone] = self.drone.distance_to(e_drone)
        distance_to_me = sorted(distance_to_me.items(), key=lambda v: v[1])
        return distance_to_me[0][0]

    def shoot_avoid_damage(self):
        enemy = self.choose_enemy_or_ship()
        if isinstance(enemy, Drone) and enemy.distance_to(self.drone) > 630 and self.ships_without_drones:
            ship = self.ships_without_drones[0]
            if self.drone.distance_to(ship) > 680:
                point = self.calculate_point_to_damage_base(ship)
                if not point:
                    if self.drone.near(self.drone.guard_coord):
                        self.drone.fast_turning_to(enemy)
                        self.drone.gun.shot(ship)
                else:
                    self.drone.point = point
                    self.drone.move_at(self.drone.point)
                    logging.info(f"SafeBaseDestroyer moving, {self.drone}")
            elif self.can_damage_team_or_base(ship.coord, self.drone.teammates):
                self.drone.move_at(self.drone.point)
            else:
                logging.info(f"SafeBaseDestroyer shooting, {self.drone}")
                self.drone.fast_turning_to(ship.coord)
                self.drone.gun.shot(ship)
        else:
            logging.info(f"SafeBaseDestroyer to Hunter, {self.drone}")
            self.drone.strategy = Hunter(self.drone)
            self.drone.strategy.start()

    def calculate_point_to_damage_base(self, enemy, distance_limit=680):
        points = []
        for angle in range(0, 360, 5):
            base_point = (self.drone.get_base_guard_coord(attack_cord=enemy.coord, distance=300, delta_angle=angle))
            points.append(base_point)
        for point in points.copy():
            for drone in self.drone.enemies:
                if drone[0] is not None and point in points and drone[0].distance_to(point) < 630:
                    points.remove(point)
        if points:
            for point in points.copy():
                vector_to_shoot = Vector.from_points(point, enemy.coord)
                for drone in self.drone.teammates:
                    if self.calculation_if_can_damage(drone.point, vector_to_shoot, 20, angle_coefficient=5 * 580) \
                            and point in points:
                        points.remove(point)
        if points:
            point = points[0]
        else:
            point = False
        return point

    def calculation_if_can_damage(self, mate_coord, vector_to_shot, close_distance, angle_coefficient=5 * 580):
        self_coord = self.drone.point
        self_coord, mate_coord = self.drone.check_on_points_errors(self_coord, mate_coord)
        vector_to_drone = Vector.from_points(self_coord, mate_coord)
        dist_to_drone = vector_to_drone.module if vector_to_drone.module > 0 else 1
        delta_angle = math.fabs(vector_to_drone.direction - vector_to_shot.direction)
        delta_angle = delta_angle if delta_angle < 180 else 360 - delta_angle
        delta_dist = vector_to_shot.module - dist_to_drone
        correct_angle = angle_coefficient / dist_to_drone
        vector_condition = correct_angle > delta_angle and delta_dist > 10
        dist_condition = self.drone.get_distance_from_points(self_coord, mate_coord) < close_distance
        return dist_condition or vector_condition


class Collector(Scenario):
    def start(self):
        self.drone.target = self.drone.strategy.get_new_asteroid
        self.drone.move_at_with_stop(self.drone.target)

    @property
    def get_new_asteroid(self):
        return self.drone.strategy.get_new_asteroid

    def load_from(self, source):
        pass

    def unload_to(self, target):
        middle_point = Point(x=600, y=300)
        self.drone.turn_to(middle_point)

    def on_stop_at_asteroid(self, asteroid):
        if asteroid.coord is not self.drone.target.coord:
            self.drone.move_at(self.drone.target)
        else:
            self.drone.load_from(asteroid)

    def on_load_complete(self):
        if self.drone.free_space:
            self.drone.target = self.drone.get_new_asteroid or self.drone.my_mothership
        else:
            self.drone.target = self.drone.my_mothership
        self.drone.move_at(self.drone.target)

    def on_stop_at_mothership(self, mothership):
        self.drone.unload_to(mothership)

    def on_stop_at_point(self, target):
        if 0 < self.drone.target.payload < self.drone.target_payload_at_first:
            self.drone.target = self.change_asteroid()
        self.drone.move_at_with_stop(self.drone.target)

    def on_wake_up(self):
        if self.drone.target is None:
            self.drone.stop()

    def on_unload_complete(self):
        self.drone.target = self.drone.get_new_asteroid
        self.drone.move_at_with_stop(self.drone.target) if self.drone.target is not None else self.drone.stop()

    def change_asteroid(self):
        target = self.get_new_asteroid
        if target is not None:
            if target.payload > self.drone.target.payload:
                return target
            else:
                return self.drone.target
        else:
            return self.drone.my_mothership

    def if_self_close_to_target(self, payload, asteroid, list_of_tuples):
        for drone in self.drone.my_team:
            if drone.target == asteroid and drone is not self.drone:
                if payload <= self.drone.free_space:
                    if self.drone.distance_to(asteroid) <= drone.distance_to(asteroid):
                        if len(list_of_tuples) < 3:
                            drone.target = drone.mothership
                        else:
                            drone.target = drone.get_new_asteroid or drone.my_mothership
                        drone.move_at(drone.target)
                        return asteroid, True
                else:
                    payload -= drone.free_space
        return payload, False

    def give_next_asteroid_from_list(self, list_of_tuples):
        payload = 0
        for asteroid, distance in list_of_tuples:
            payload = asteroid.payload
            result, bool_res = self.if_self_close_to_target(payload, asteroid, list_of_tuples)
            if bool_res:
                return result
            elif not bool_res:
                payload = result
            if payload > self.drone.free_space:
                self.drone.target_payload_at_first = payload
                return asteroid
        if len(list_of_tuples) > 0:
            self.drone.target_payload_at_first = payload
            return list_of_tuples[0][0]

    def get_list_of_asteroid(self, reverse=True):
        asteroids_distances = defaultdict(str)
        for asteroid in self.drone.asteroids:
            if asteroid.payload > 0:
                asteroids_distances[asteroid] = self.drone.distance_to(asteroid)
        asteroids_distances = [(k, v) for k, v in sorted(asteroids_distances.items(),
                                                         key=lambda item: item[1], reverse=reverse)]
        return asteroids_distances


class MiddleCollector(Collector):
    def start(self):
        logging.info(f'MiddleCollector start {self.drone}')
        super().start()

    @property
    def get_new_asteroid(self):
        distance_to_asteroids = self.get_list_of_asteroid()
        distance_to_asteroids_from_middle = distance_to_asteroids[len(distance_to_asteroids) // 3:]
        asteroid = self.give_next_asteroid_from_list(list_of_tuples=distance_to_asteroids_from_middle)
        return asteroid or self.drone.mothership


class NearCollector(Collector):
    def start(self):
        logging.info(f'NearCollector start {self.drone}')
        super().start()

    @property
    def get_new_asteroid(self):
        distance_to_asteroids = self.get_list_of_asteroid(reverse=False)
        asteroid = self.give_next_asteroid_from_list(list_of_tuples=distance_to_asteroids)
        return asteroid or self.drone.mothership


class CleanerCollector(Collector):
    def start(self):
        logging.info(f'CleanerCollector start {self.drone}')
        super().start()

    def get_list_of_asteroid(self, reverse=True):
        to_obj_distances = defaultdict(str)
        dead_motherships_list = [mothership for mothership in self.drone.scene.motherships
                                 if not mothership.is_alive and mothership is not self.drone.mothership
                                 and mothership.payload > 0]
        dead_drones_list = [drone for drone in self.drone.scene.drones
                            if not drone.is_alive and drone.payload > 0]
        asteroid_list = [asteroid for asteroid in self.drone.asteroids if asteroid.payload > 0]
        all_obj = dead_motherships_list + dead_drones_list + asteroid_list
        for current_obj in all_obj:
            to_obj_distances[current_obj] = self.drone.distance_to(current_obj)
        to_obj_distances = [(k, v) for k, v in sorted(to_obj_distances.items(),
                                                      key=lambda item: item[1], reverse=reverse)]
        return to_obj_distances

    def give_next_asteroid_from_list(self, list_of_tuples):
        for asteroid, distance in list_of_tuples:
            payload = asteroid.payload
            for drone in self.drone.teammates:
                if drone.target == asteroid:
                    payload -= drone.free_space
            if payload > 0:
                return asteroid

    @property
    def get_new_asteroid(self):
        distance_to_objects = self.get_list_of_asteroid(reverse=False)
        current_object = self.give_next_asteroid_from_list(list_of_tuples=distance_to_objects)
        return current_object or self.drone.mothership

    def on_stop_at_point(self, target):
        if self.drone.target is None:
            self.drone.target = self.drone.get_new_asteroid
        if self.drone.distance_to(self.drone.target) < 25:
            self.drone.load_from(self.drone.target)
        else:
            self.drone.move_at(self.drone.target)

    def on_stop_at_mothership(self, mothership):
        if mothership is self.drone.mothership:
            self.drone.unload_to(mothership)
        else:
            self.drone.load_from(mothership)

    def on_stop_at_asteroid(self, asteroid):
        if isinstance(self.drone.target, Drone):
            self.drone.load_from(self.drone.target)
        else:
            self.drone.load_from(asteroid)


class SafeCollector(CleanerCollector):
    def start(self):
        super().start()

    def give_next_asteroid_from_list(self, list_of_tuples):
        for asteroid, distance in list_of_tuples:
            payload = asteroid.payload
            for drone in self.drone.teammates:
                if drone.target == asteroid:
                    payload -= drone.free_space
            if payload > 20:
                return asteroid

    @property
    def get_new_asteroid(self):
        safe_distance = 635 - 15 * len(self.drone.my_team)
        distance_to_objects = self.get_list_of_asteroid(reverse=False)
        for enemy, distance_to_enemy_base in self.drone.enemies:
            for __object in distance_to_objects.copy():
                if __object in distance_to_objects and enemy.distance_to(__object[0]) < safe_distance:
                    distance_to_objects.remove(__object)
        if distance_to_objects:
            current_object = self.give_next_asteroid_from_list(list_of_tuples=distance_to_objects)
            if current_object:
                return current_object
        self.drone.strategy = Hunter(self.drone)
        self.drone.strategy.start()

    def on_load_complete(self):
        if self.drone.payload > 50:
            self.drone.move_at_position_near_base()
        else:
            super().on_load_complete()

    def load_from(self, source):
        self.drone.turn_to(self.drone.mothership)
        super().load_from(source)


class StarovoitovDrone(DroneAction):
    def on_born(self):
        self._my_team.append(self)
        if self.have_gun:
            self.fighters()
        else:
            self.collectors()
        self.strategy.start()

    def fighters(self):
        self.strategy = Hunter(self)

    def collectors(self):
        if len(self.my_team) % 2 == 0:
            self.strategy = NearCollector(self)
        else:
            self.strategy = MiddleCollector(self)


drone_class = StarovoitovDrone
