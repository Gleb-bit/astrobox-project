from random import shuffle
from astrobox.core import Drone
from astrobox.themes.default import MOTHERSHIP_HEALING_DISTANCE
from robogame_engine import GameObject
from robogame_engine.geometry import Point, Vector
from robogame_engine.theme import theme

MIN_HEALTH = 40
MAX_CARGO = 50


class SmirnovDrone(Drone):
    teammates = []
    teammates_lives = []
    dead_loot = []
    mother_ship_is_dead = False
    collectors = []
    seekers = []
    asteroids_with_payload = []
    asteroids_busy = []
    asteroids_queue = []

    def __init__(self):
        super(SmirnovDrone, self).__init__()
        self.style = None
        self.mode = None
        self.asteroid_in_action = None
        self.enemy_list = []
        self.enemy_dead_list = []
        self.teammates.append(self)

    def set_state(self, status):
        self.style = status
        self.mode = self.style

    def main_action(self):
        self.style = self.mode.main_action()

    def collect(self):
        self.set_state(Collector(me=self))
        self.main_action()

    def seek(self):
        self.set_state(Seeker(me=self))
        self.main_action()

    def hunting(self):
        self.set_state(Hunter(me=self))
        self.main_action()

    def destroy(self):
        self.set_state(Destroyer(me=self))
        self.main_action()

    def protect(self):
        self.set_state(Protector(me=self))
        self.main_action()

    def on_heartbeat(self):
        if self.health < MIN_HEALTH or self.payload > MAX_CARGO:
            self.move_at(self.my_mothership)
        self.asteroids_with_payload = [asteroid for asteroid in self.asteroids if asteroid.payload > 0]
        self.teammates_lives = [team for team in self.teammates if team.is_alive]
        self._get_dead_enemies()

    def _get_dead_enemies(self):

        motherships = [mothership for mothership in self.scene.motherships
                       if mothership is not self.my_mothership and not mothership.is_alive]
        dead_objects = [[self.distance_to(obj), obj, obj.payload] for obj in motherships if obj.payload > 0]
        dead_objects = sorted(dead_objects, key=lambda x: x[0])
        self.enemy_dead_list = dead_objects
        return self.enemy_dead_list

    def _count(self):

        teammates = set(self.teammates)
        all_drones = set(dron for dron in self.scene.drones)
        motherships = set(mothership for mothership in self.scene.motherships
                          if mothership is not self.my_mothership)
        enemy_drones = all_drones - teammates
        enemy_drones.update(motherships)
        self.enemy_list = list(enemy_drones)

    def _recount(self):

        for dron in self.seekers:
            if not dron.is_alive:
                self.seekers.pop(self.seekers.index(dron))

        for dron in self.collectors:
            if not dron.is_alive:
                self.collectors.pop(self.collectors.index(dron))

    def on_born(self):
        self._count()
        self.strategy()

    def on_stop(self):
        self.strategy()

    def on_stop_at_asteroid(self, asteroid):
        self.load_from(asteroid)

    def on_load_complete(self):
        self.strategy()

    def on_unload_complete(self):
        self.strategy()

    def on_stop_at_point(self, target):
        if isinstance(target, GameObject) and target is not self.my_mothership:
            self.load_from(target)
        elif target is self.my_mothership:
            self.unload_to(target)

    def on_stop_at_mothership(self, mothership):
        self.unload_to(mothership)

    def on_wake_up(self):
        self.strategy()

    def strategy(self):
        self._recount()
        if len(self.teammates_lives) < 2 and self.my_mothership.payload > 1:
            self.protect()
            return
        if len(self.teammates_lives) > 4 and len(self.asteroids_with_payload) > 2:
            self.seek()
            return
        if (self.enemy_dead_list and
                len(self.collectors) < len(self.teammates_lives) - 1 and
                not self.dead_loot
                or self.enemy_dead_list and self in self.collectors and not self.dead_loot):
            self.collect()
            return
        elif (not self.seekers or len(self.seekers) < 2
              and len(self.teammates_lives) > 2):
            self.seek()
            return
        elif (self in self.seekers and len(self.teammates_lives) > 2
              and len(self.seekers) < 2):
            self.seek()
            return
        if len(self.teammates_lives) < 3 and len(self.enemy_list) < 3:
            self.seek()
        elif not self.enemy_list and not self.dead_loot:
            self.collect()
        elif self.dead_loot:
            self.seek()
        elif len(self.enemy_list) < 3 and not self.mother_ship_is_dead:
            self.destroy()
        elif self.enemy_list:
            self.hunting()


class Seeker:

    def __init__(self, me: SmirnovDrone):
        self.me = me
        self.me.seekers.append(self.me)

    def main_action(self):

        if self.me.payload == 100:
            self.me.move_at(self.me.my_mothership)
            return
        if self.me.asteroid_in_action is None or self.me.asteroid_in_action.payload == 0:
            next_asteroid = self.get_asteroids()
        else:
            next_asteroid = self.get_near_asteroid()
        self.me.asteroid_in_action = next_asteroid
        self.me.move_at(next_asteroid)

    def get_asteroids(self):

        if self.me.payload == 100:
            return self.me.my_mothership
        distance_list = self.get_asteroids_count()
        self.me.asteroids_busy = [teammate.asteroid_in_action for teammate in self.me.teammates]
        for asteroid_pack in distance_list:
            asteroid = asteroid_pack[1]
            if asteroid in self.me.asteroids_busy:
                continue
            else:
                return asteroid
        return distance_list[-1][1]

    def get_near_asteroid(self):

        distance_list = self.get_asteroids_count()
        next_asteroid = distance_list[0][1]
        if len(self.me.asteroids_queue) > 1:
            next_asteroid = self.me.asteroids_queue.pop(-1)
        return next_asteroid

    def get_asteroids_count(self):

        distance_list = list()
        asteroid_list = [asteroid for asteroid in self.me.asteroids if asteroid.payload > 0]
        for asteroid in asteroid_list:
            distance_to_point = self.me.distance_to(asteroid)
            asteroid_payload = asteroid.payload
            distance_list.append([distance_to_point, asteroid, asteroid_payload])
        distance_list = sorted(distance_list, key=lambda x: x[0])
        if len(distance_list) == len(self.me.asteroids):
            distance_list = distance_list[:]  # с какого астероида начинать
            return distance_list
        if not distance_list:
            return [("", self.me.my_mothership)]
        return distance_list


class Collector(Seeker):
    def __init__(self, me: SmirnovDrone):
        super(Collector, self).__init__(me)
        self.me = me
        self.me.collectors.append(self.me)

    def main_action(self):

        next_obj = self.get_near_asteroid()
        if self.me.on_stop_at_point(next_obj):
            self.me.load_from(next_obj)
            return
        return self.me.move_at(next_obj)

    def get_asteroids_count(self):

        all_dead = [dron for dron in self.me.scene.drones if not dron.is_alive]
        all_motherships = [dron.my_mothership for dron in self.me.scene.drones
                           if not dron.my_mothership.is_alive]
        all_dead.extend(all_motherships)
        dead_objects = [[self.me.distance_to(obj), obj, obj.payload] for obj in all_dead if obj.payload > 0]
        dead_objects = sorted(dead_objects, key=lambda x: x[0])
        self.me.enemy_dead_list = dead_objects
        if len(dead_objects) == 0:
            if len(self.me.enemy_list) == len(self.me.enemy_dead_list):
                self.me.dead_loot.append(True)
            return [("", self.me.my_mothership)]
        return dead_objects


class Hunter:
    enemies_list = None
    point_list = []
    enemy_motherships = []

    def __init__(self, me: SmirnovDrone):
        self.me = me

    def main_action(self):

        if not [obj for obj in self.get_enemies_count() if obj.is_alive]:
            return
        my_target = self.get_enemy()
        if my_target and self.me.distance_to(my_target) > self.me.gun.shot_distance:
            point = self.attack_place(my_target)
            if point:
                return self.me.move_at(point)
            else:
                return
        if my_target and my_target.is_alive:
            self.shot(target=my_target)

    def attack_place(self, target):

        if isinstance(target, GameObject):
            vec = Vector.from_points(target.coord, self.me.coord)
        elif isinstance(target, Point):
            vec = Vector.from_points(target, self.me.coord)
        else:
            raise Exception("wrong object".format(target, ))
        dist = vec.module
        _koef = 1 / dist
        norm_vec = Vector(vec.x * _koef, vec.y * _koef)
        vec_gunshot = norm_vec * min(int(self.me.gun.shot_distance), int(dist))
        purpose = Point(target.coord.x + vec_gunshot.x, target.coord.y + vec_gunshot.y)
        angles = [0, 10, 20, 30, -20, -10, -30]
        shuffle(angles)
        for ang in angles:
            place = self.get_place_near(purpose, target, ang)
            if place:
                return place
        return None

    @staticmethod
    def get_place_near(point, target, angle):
        vec = Vector(point.x - target.x, point.y - target.y)
        vec.rotate(angle)
        return Point(target.x + vec.x, target.y + vec.y)

    def place_validation(self, point: Point):

        is_valide = 0 < point.x < theme.FIELD_WIDTH and 0 < point.y < theme.FIELD_HEIGHT
        for partner in self.me.teammates:
            if not partner.is_alive or partner is self:
                continue
        return is_valide

    def shot(self, target):

        for dron in self.me.teammates:
            if not dron.is_alive or dron is self.me:
                continue
            if dron.near(self.me) and self.me is not dron:
                next_point = self.attack_place(target)
                self.me.move_at(next_point)
                return
        if not self.place_validation(self.me.coord):
            next_point = self.attack_place(target)
            self.me.move_at(next_point)
            return
        if self.me.distance_to(target) > self.me.gun.shot_distance \
                or self.me.distance_to(self.me.my_mothership) < 130:
            next_point = self.attack_place(target)
            self.me.move_at(next_point)
            return
        self.me.turn_to(target)
        self.me.gun.shot(target)

    def get_enemy(self):

        target_list = []
        for target in self.get_enemies_count():
            if target.is_alive:
                target_list.append((self.me.distance_to(target), target))
        target_distance_list = sorted(target_list, key=lambda x: x[0])
        next_target = target_distance_list[0][1]
        return next_target

    def get_enemies_count(self):

        teammates = set(self.me.teammates)
        all_drones = set(dron for dron in self.me.scene.drones)
        enemy_drones = all_drones - teammates
        enemy_drones = list(enemy_drones)
        for dron in enemy_drones:
            if isinstance(dron, Drone) and dron.my_mothership not in enemy_drones \
                    and dron.my_mothership not in self.enemy_motherships \
                    and dron.my_mothership.is_alive:
                enemy_drones.append(dron.my_mothership)
                self.enemy_motherships.append(dron.my_mothership)
        self.me.enemy_list = enemy_drones
        self.me.enemy_list.extend(self.enemy_motherships)
        self.me.enemy_list = [obj for obj in self.me.enemy_list if obj.is_alive]
        return self.me.enemy_list


class Destroyer(Hunter):

    def main_action(self):

        for target in self.enemy_motherships:
            if target.is_alive:
                return self.shot(target)
            else:
                self.me.mother_ship_is_dead = True


class Protector(Hunter):

    def main_action(self):

        my_target = self.get_enemy()
        new_position = self.get_near_base(my_target)
        if self.me.coord.x == new_position.x and self.me.coord.y == new_position.y:
            self.shot(my_target)
            return
        else:
            self.me.move_at(new_position)
            return

    def get_near_base(self, target):

        base = self.me.my_mothership
        new_vec = Vector.from_points(base.coord, target.coord)
        other_vec = new_vec.module
        _koef = 1 / other_vec
        norm_vec = Vector(new_vec.x * _koef, new_vec.y * _koef)
        vec_position = Vector(norm_vec.x * MOTHERSHIP_HEALING_DISTANCE * 0.9,
                              norm_vec.y * MOTHERSHIP_HEALING_DISTANCE * 0.9)
        new_position = Point(base.coord.x + vec_position.x, base.coord.y + vec_position.y)
        return new_position

drone_class = SmirnovDrone