from astrobox.themes.default import MOTHERSHIP_HEALING_DISTANCE

from hangar_2020.kachanov_v_a_package.drone import DeusDrone


class Behavior:

    def __init__(self, unit: DeusDrone):
        self.unit = unit

    def change_role(self, role=None):
        soldier = self.unit
        if not role:
            soldier.role = soldier.role.next()
        else:
            soldier.role = role(soldier)

    def next(self):
        return Collector(self.unit)


class Collector(Behavior):
    def next_purpose(self):
        if self.unit.is_full:
            return self.unit.basa

        headquarters = self.unit.headquarters

        forbidden_asteroids = list(headquarters.asteroids_in_work)
        if isinstance(self, Transport):
            asteroids = [asteroid for asteroid in self.unit.scene.asteroids if asteroid not in forbidden_asteroids]
            free_elerium = sum([asteroid.payload for asteroid in asteroids])
            if free_elerium < 2000:
                headquarters.asteroids_for_basa = []
                self.unit.basa = self.unit.my_mothership
                return None
            else:
                forbidden_asteroids += headquarters.asteroids_for_basa

        if not hasattr(self.unit.scene, "asteroids"):
            return None

        asteroids = [asteroid for asteroid in self.unit.scene.asteroids if asteroid not in forbidden_asteroids]
        asteroids.extend([mothership for mothership in self.unit.scene.motherships
                          if not mothership.is_alive and not mothership.is_empty])
        asteroids.extend([drone for drone in self.unit.scene.drones
                          if not drone.is_alive and not drone.is_empty])

        enemies = headquarters.get_enemies(self.unit)
        purposes = [(asteroid.distance_to(self.unit.my_mothership), asteroid) for asteroid in asteroids if
                    asteroid.payload > 0]

        purposes.sort(key=lambda x: x[0])

        if purposes:
            second_purpose = min(purposes, key=lambda x: x[0])
            return second_purpose[1]
        elif not enemies:
            return self.unit.basa
        return None

    def find_nearest_purpose(self, asteroids, threshold=1):
        soldier = self.unit
        purposes = [(asteroid.distance_to(soldier.basa), asteroid) for asteroid in asteroids
                    if asteroid.distance_to(soldier.basa) <= MOTHERSHIP_HEALING_DISTANCE * 4
                    and asteroid.payload >= threshold]

        if purposes:
            if isinstance(self, Transport):
                purpose = max(purposes, key=lambda x: x[0])[1]
            else:
                purpose = min(purposes, key=lambda x: x[0])[1]
        else:
            purpose = None

        if purpose == soldier.old_asteroid:
            purpose = None

        return purpose

    def next_step(self, purpose):
        soldier = self.unit
        soldier.actions.append(['move_to', purpose, 1, 1])
        if purpose == soldier.basa:
            if not soldier.is_empty:
                soldier.actions.append(['unload_to', purpose, None, 1])

        elif not soldier.is_full:
            soldier.headquarters.asteroids_in_work.append(purpose)
            soldier.actions.append(['load_from', purpose, None, 1])
        else:
            soldier.actions.append(['unload_to', soldier.my_mothership, None, 1])
        soldier.actions.append(['asteroid_is_free', purpose, None, 1])

    def next(self):
        if self.unit.have_gun:
            if self.unit.headquarters.get_enemies(self.unit):
                return Turel(self.unit)
            return Spy(self.unit)
        return Demob(self.unit)


class Transport(Collector):
    def next(self):
        if self.unit.have_gun and self.unit.my_mothership.payload > 1000:
            return Spy(self.unit)
        return Collector(self.unit)


class Demob(Behavior):
    def next_purpose(self):
        return self.unit.my_mothership

    def next_step(self):
        soldier = self.unit
        if soldier.distance_to(soldier.my_mothership) > 10:
            soldier.actions = [['move_to', soldier.my_mothership, 1, 1]]

        if not soldier.is_empty:
            soldier.actions.append(['unload_to', self.unit.my_mothership, None, 1])

    def next(self):
        return self


class Defender(Behavior):
    def __init__(self, unit: DeusDrone):
        super().__init__(unit)
        self.victim = None
        self.unit.actions = []

    def next_purpose(self):
        soldier = self.unit

        """Атака"""
        if len(soldier.headquarters.get_enemies(soldier)) != 0:
            if not any([soldier.distance_to(base) < MOTHERSHIP_HEALING_DISTANCE for base in soldier.scene.motherships]) \
                    and soldier.meter_2 == 1.0 and not soldier.is_full:
                return self.victim
        return None

    def next_step(self, purpose):
        soldier = self.unit
        self.victim = purpose
        if soldier.distance_to(purpose) > soldier.attack_range:
            point_attack = soldier.headquarters.get_place_for_attack(soldier, purpose)
            if point_attack:
                soldier.actions.append(['move_to', point_attack, 1, 1])

        soldier.add_attack(purpose)

    def next(self):
        return Collector(self.unit)


class CombatBot(Defender):

    def next_purpose(self):
        self.victim = super().next_purpose()
        if self.victim and self.victim.distance_to(self.victim.my_mothership) > MOTHERSHIP_HEALING_DISTANCE:
            return self.victim

        soldier = self.unit
        enemies = soldier.headquarters.get_enemies(soldier)
        if enemies:
            self.victim = enemies[0][0]
            return self.victim

        self.victim = None
        return None

    def next(self):
        return Spy(self.unit)


class Spy(Defender):

    def next_purpose(self):
        if self.victim and self.victim.is_alive:
            return self.victim

        soldier = self.unit
        bases = soldier.headquarters.get_bases(soldier)
        if bases:
            self.victim = bases[0][0]
            return self.victim

        self.victim = None
        return None

    def next_step(self, target):
        soldier = self.unit
        self.victim = target

        if soldier.distance_to(target) > soldier.attack_range:
            point_attack = soldier.headquarters.get_place_for_attack(soldier, target)
            if point_attack:
                soldier.actions.append(['move_to', point_attack, 1, 1])

        soldier.add_attack(target)

    def next(self):
        soldier = self.unit
        enemies = soldier.headquarters.get_enemies(soldier)
        if enemies:
            return CombatBot(self.unit)
        return Collector(self.unit)


class BaseGuard(Defender):

    def next_purpose(self):
        if self.victim and self.victim.is_alive \
                and self.victim.distance_to(self.victim.my_mothership) > MOTHERSHIP_HEALING_DISTANCE:
            return self.victim
        return None

    def next_step(self, target):
        soldier = self.unit
        self.victim = target

        if target:
            soldier.add_attack(target)
        elif soldier.distance_to(soldier.my_mothership) > MOTHERSHIP_HEALING_DISTANCE * 0.95:
            point_attack = soldier.headquarters.get_vec_near_mothership(soldier)
            soldier.actions.append(['move_to', point_attack, 1, 1])

    def next(self):
        soldier = self.unit
        enemies = soldier.headquarters.get_enemies(soldier)
        if len(enemies) == 0:
            return Collector(self.unit)
        return Spy(self.unit)


class Turel(Defender):

    def next_purpose(self):
        soldier = self.unit

        enemies = soldier.headquarters.get_enemies(soldier)
        if enemies:
            return enemies[0][0]
        return None

    def next_step(self, target):
        soldier = self.unit
        if target:
            soldier.add_attack(target)
        elif soldier.distance_to(soldier.my_mothership) > MOTHERSHIP_HEALING_DISTANCE * 0.95:
            point_attack = soldier.headquarters.get_vec_near_mothership(soldier)
            soldier.actions.append(['move_to', point_attack, 1, 1])

    def next(self):
        return Collector(self.unit)


class Distractor(Defender):

    def next_purpose(self):
        soldier = self.unit
        if self.victim and self.victim.is_alive:
            return self.victim

        enemies = soldier.headquarters.get_enemies(soldier)
        if enemies:
            return enemies[0][0]
        return None

    def next_step(self, target):
        soldier = self.unit
        if target:
            soldier.add_attack(target)
        elif soldier.distance_to(soldier.my_mothership) > MOTHERSHIP_HEALING_DISTANCE * 0.95:
            point_attack = soldier.headquarters.get_vec_near_mothership(soldier)
            soldier.actions.append(['move_to', point_attack, 1, 1])

    def next(self):
        return Collector(self.unit)
