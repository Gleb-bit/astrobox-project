import random
from robogame_engine.geometry import Point
from astrobox.core import Drone

DEAD_BASES = []


class SurkovaDrone(Drone):
    status = "born"

    def sorting_asteroids(self):
        self.aiming_asteroids = self.asteroids
        for asteroid in self.aiming_asteroids:
            if asteroid.payload > 0 and self.distance_to(asteroid) != 0:
                self.distances.append(self.distance_to(asteroid))

    def check_asteroids(self):
        for asteroid in self.aiming_asteroids:
            if self.distance_to(asteroid) == self.target_distance:
                self.target = asteroid

    def check_teammates(self):
        self.distances = []
        target = self.find_the_nearest()
        if not target:
            return False
        else:
            return target

    def find_the_nearest(self):
        if self.status == "born" or self.status == "change":
            self.check_standers()
            if self.standers <= self.soldiers_count // 2:
                self.check_defenders()
                if self.defenders > 0:
                    self.target_coord_x = (self.coord.x + 150)
                    target_point = Point(x=self.target_coord_x, y=self.coord.y)
                    return target_point
                else:
                    self.target_coord_y = (self.coord.y + 150) * self.standers
                    target_point = Point(x=self.coord.x, y=self.target_coord_y)
                    return target_point
            else:
                self.status = "stay_near_base"
        elif self.status == "go":
            self.sorting_asteroids()
            if not self.distances:
                return False
            else:
                self.target_distance = random.choice(self.distances)
                self.check_asteroids()
                return self.target
        else:
            return False

    def check_standers(self):
        self.standers = 0
        for teamer in self.teammates:
            if teamer.status == "stand_further":
                self.standers += 1

    def check_defenders(self):
        for teamer in self.teammates:
            try:
                if teamer.defenders > 0:
                    break
            except:
                pass
        else:
            self.defenders += 1

    def on_born(self):
        self.target_coord_y = 0
        self.target_coord_x = 0
        self.defenders = 0
        self.soldiers_count = len(self.teammates) + 1
        self.enemies = list(self.scene.get_objects_by_type(cls_name="DevastatorDrone"))
        target = self.check_teammates()
        if not target:
            self.stop()
        else:
            self.status = "stand_further"
            self.move_at(target)

    def on_stop_at_asteroid(self, asteroid):
        if self.status == "stay_near_base" or self.status == "stand_further" or self.status == "change":
            self.stop()
        else:
            self.status = "go"
            self.load_from(asteroid)

    def on_load_complete(self):
        target = self.check_teammates()
        if self.is_full or not target:
            self.move_at(self.mothership)
        else:
            self.move_at(target)

    def shooting(self):
        self.gun.shot(self.enemy)

    def on_stop_at_mothership(self, mothership):
        if self.status == "stand_further":
            self.stop()
        else:
            if mothership != self.mothership:
                self.load_from(mothership)
            if self.payload == 0:
                self.on_unload_complete()
            self.unload_to(mothership)

    def on_unload_complete(self):
        self.status = "go"
        target = self.check_teammates()
        if target:
            self.move_at(target)
        else:
            if self.near(self.mothership):
                base = self.check_motherships()
                if base:
                    self.move_at(base)
                else:
                    self.stop()
            else:
                self.move_at(self.mothership)

    def check_motherships(self):
        for base in self.scene.motherships:
            if base.payload <= 0 or base == self.mothership:
                DEAD_BASES.append(base)
            elif not base:
                return False
            else:
                return base

    def check_teamers_near_base(self):
        near_bases = 0
        for teamer in self.teammates:
            if teamer.status == "stand_further":
                near_bases += 1
            elif teamer.status == "change":
                return False
        if near_bases <= self.soldiers_count // 2 and len(self.enemies) >= 1:
            return True

    def buttle(self):
        battle = Battle(unit=self)
        self.enemy = battle.find_nearest_enemy()
        if self.enemy:
            if self.status == "go":
                target = self.check_teammates()
                self.move_at(target)
            else:
                self.turn_to(self.enemy)
                self.shooting()
        else:
            self.status = "go"

    def on_wake_up(self):
        if self.status == "go":
            self.move_at(self.mothership)
        elif self.status == "stay_near_base":
            deads = self.check_teamers_near_base()
            if deads:
                self.status = "change"
                target = self.check_teammates()
                self.move_at(target)
            else:
                self.stop()
        elif self.status == "change":
            self.buttle()
        elif self.status == "stand_further" and not self.near(self.mothership):
            self.buttle()


class Battle:

    def __init__(self, unit: SurkovaDrone):
        self.unit = unit

    def find_death(self):
        for enemy in self.unit.enemies:
            if not enemy.is_alive:
                self.unit.enemies.remove(enemy)

    def find_nearest_distance_enemy(self):
        self.find_death()
        self.enemy_distances = []
        for enemy in self.unit.enemies:
            for teamer in self.unit.teammates:
                if self.unit.distance_to(enemy) != self.unit.distance_to(teamer) and self.unit.distance_to(enemy) > 50:
                    self.enemy_distances.append(self.unit.distance_to(enemy))
                    self.enemy_distances.sort()

    def find_nearest_enemy(self):
        self.find_nearest_distance_enemy()
        for enemy in self.unit.enemies:
            if self.unit.distance_to(enemy) == self.enemy_distances[0]:
                return enemy


drone_class = SurkovaDrone
