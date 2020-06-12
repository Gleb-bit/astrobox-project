# -*- coding: utf-8 -*-

from astrobox.core import Drone
from astrobox.themes.default import MOTHERSHIP_HEALING_DISTANCE
from robogame_engine.geometry import Point, Vector
from robogame_engine.theme import theme


class Headquarters:
    """
    Штаб
    """
    roles = {}
    moves_empty = 0
    moves_semi_empty = 0
    moves_full = 0

    def __init__(self):
        self.drones = []
        self.elirium_stors_in_work = []
        self.elirium_stors_in_work_free_elirium = []

    def new_drone(self, drone):
        """
        Регистрация нового дрона
        :param drone:
        :return:
        """
        number_drones = len(self.drones)
        self._get_roles(number_drones + 1, drone.have_gun)
        self._add_drone(drone)
        for idx, drone in enumerate(self.drones):
            self._give_role(drone, idx)

    def _give_role(self, drone, index):
        """
        Раздача ролей
        :param drone:
        :param index:
        :return:
        """
        all_roles = [Collector for _ in range(Headquarters.roles["collector"])]
        all_roles.extend(Warrior for _ in range(Headquarters.roles["warrior"]))
        this_role = all_roles[index]
        drone.role = this_role(unit=drone)

    def _get_roles(self, number_drones, have_gun):
        """
        Получение количественного списка всех ролей
        :param number_drones:
        :param have_gun:
        :return:
        """
        if have_gun:
            collectors = number_drones // 3
            warrior = max(0, number_drones - collectors)
            Headquarters.roles["collector"] = collectors
            Headquarters.roles["warrior"] = warrior

        else:
            collectors = number_drones
            Headquarters.roles["collector"] = collectors
            Headquarters.roles["warrior"] = 0

    def _add_drone(self, drone):
        drone.headquarters = self
        drone.actions = []
        self.drones.append(drone)

    def get_actions(self, drone):
        """
        Получение дроном нового действия, действия добавляются в список и выполняются по очереди
        :param drone:
        :return:
        """

        full_elirium_stors = self.get_full_elirium_stors(drone)
        enemies = self.get_enemies(drone)
        enemies_bases = self.get_bases(drone)

        if not full_elirium_stors and drone.stop_at_basa:
            if drone.have_gun:
                if not enemies and not enemies_bases:
                    drone.actions = []
                    drone.actions.append(['stop', 'stop'])
            else:
                drone.actions = []
                drone.actions.append(['stop', 'stop'])
            return

        if drone.meter_2 <= drone.limit_health and drone.distance_to(drone.mothership) > MOTHERSHIP_HEALING_DISTANCE:
            self.elirium_stors_in_work = []
            self.elirium_stors_in_work_free_elirium = []
            if hasattr(drone.role, 'remove_occupied_point_attack'):
                drone.role.remove_occupied_point_attack(drone)
            drone.actions.append(['move', drone.my_mothership])
            if drone.payload > 0:
                drone.actions.append(['unload', drone.my_mothership])
            return

        purpose = drone.role.next_purpose()

        if purpose:
            drone.role.next_step(purpose)
        else:
            drone.action = []
            drone.role.change_role()
            purpose = drone.role.next_purpose()
            if purpose:
                drone.role.next_step(purpose)
            else:
                drone.actions.append(['move', drone.my_mothership])
                drone._next_action()

    def get_enemies(self, drone):
        """
        Получение списка врагов, отсортированного по возрастанию удаленности от дрона
        :param drone:
        :return:
        """
        enemies = [(enemy, drone.distance_to(enemy)) for enemy in drone.scene.drones if
                   drone.team != enemy.team and enemy.is_alive]
        enemies.sort(key=lambda x: x[1])
        return enemies

    def get_bases(self, drone):
        """
        Получение списка вражеских баз, отсортированного по возрастанию удаленности от дрона
        :param drone:
        :return:
        """
        bases = [(base, drone.distance_to(base)) for base in drone.scene.motherships if
                 base.team != drone.team and base.is_alive]
        bases.sort(key=lambda x: x[1])
        return bases

    def get_full_elirium_stors(self, drone):
        """
        Получение списка всех объектов, из которых, можно добывать элириум
        :param drone:
        :return:
        """
        full_elirium_stors = set(aster for aster in drone.asteroids if aster.payload)
        if drone.have_gun:
            full_elirium_stors.update(set(mothership for mothership in drone.scene.motherships
                                          if not mothership.is_alive and not mothership.is_empty))
            full_elirium_stors.update(set(enemy for enemy in drone.scene.drones
                                          if not enemy.is_alive and not enemy.is_empty))

        return full_elirium_stors

    def get_elirium_stors_as_target(self, drone):
        """
        Получение объектов для добычи элириума, которые уже заняты
        :param drone:
        :return:
        """
        elirium_stors_as_targets = set()
        for idx, elirium_stor_free_space in enumerate(self.elirium_stors_in_work_free_elirium):
            if elirium_stor_free_space > 0:
                elirium_stor_free_space -= drone.free_space
            else:
                elirium_stor = self.elirium_stors_in_work[idx]
                elirium_stors_as_targets.add(elirium_stor)

        return elirium_stors_as_targets

    def get_elirium_stor_as_target(self, drone, available_elirium_stors):
        """
        Получение цели из которой добывать элириум
        :param drone:
        :param available_elirium_stors:
        :return:
        """
        if drone.have_gun:
            elirium_stor_as_target = self.get_nearest_elirium_stor(drone, available_elirium_stors)
        else:
            list_efficiency = []
            elirium_stor_as_target = None

            for elirium_stor_free_to_load in available_elirium_stors:

                distance = drone.distance_to(elirium_stor_free_to_load)
                can_load = min(drone.free_space, elirium_stor_free_to_load.payload)
                efficiency = (can_load / distance if distance else 0)
                list_efficiency.append(efficiency)
                if efficiency == max(list_efficiency):
                    elirium_stor_as_target = elirium_stor_free_to_load

        return elirium_stor_as_target

    def get_nearest_elirium_stor(self, drone, available_elirium_stors):
        elirium_stor_distances = [(elirium_stor, drone.distance_to(elirium_stor)) for elirium_stor in
                                  available_elirium_stors]
        elirium_stor = min(elirium_stor_distances, key=lambda x: x[1])[0] if elirium_stor_distances else None
        return elirium_stor

    def remove_item_elirium_stors_in_work(self, elirium_stor):
        """
        Удаление обекта для добычи элириума из списка занятых
        :param elirium_stor:
        :return:
        """
        if elirium_stor in self.elirium_stors_in_work:
            idx = self.elirium_stors_in_work.index(elirium_stor)
            self.elirium_stors_in_work.pop(idx)
            self.elirium_stors_in_work_free_elirium.pop(idx)

    def save_statistic_move(self, drone, purpose):
        """
        Сохрание статистки движения команды с разной загрузкой трюма
        :param drone:
        :param purpose:
        :return:
        """
        length = drone.distance_to(purpose)
        if drone.is_empty:
            Headquarters.moves_empty += length
        elif drone.free_space > 0:
            Headquarters.moves_semi_empty += length
        elif drone.is_full:
            Headquarters.moves_full += length

    def print_statistic(self, class_name):
        """
        Печать статистки движения команды с разной загрузкой трюма
        :return:
        """
        print("\nСтатистика:")
        print(
            f'Команда {class_name.__name__} '
            f'с пустым трюмом прошла {round(Headquarters.moves_empty)} pix')
        print(
            f'Команда {class_name.__name__} '
            f'с полным трюмом прошла {round(Headquarters.moves_full)} pix')
        print(
            f'Команда {class_name.__name__} '
            f'с неполностью заполненым трюмом {round(Headquarters.moves_semi_empty)} pix')


class DroneRole:
    victim = None
    occupied_points_attack = []

    def __init__(self, unit):
        self.unit = unit
        # self.prev_point_attack = None

    def change_role(self, role=None):
        drone = self.unit
        if not role:
            drone.role = drone.role._next_role()
        else:
            drone.role = role(drone)

    def _next_role(self):
        pass

    def next_purpose(self):
        pass

    def next_step(self, purpose):
        pass


class Collector(DroneRole):
    """
    Роль сборщика элириума
    """

    def next_purpose(self):
        drone = self.unit
        headquarters = drone.headquarters
        enemies = headquarters.get_enemies(drone)
        enemies_bases = headquarters.get_bases(drone)
        if (len(enemies) == 1 and
                all(basa[0].payload < drone.mothership.payload for basa in enemies_bases) and
                drone.have_gun):
            return None

        if (any([drone.mothership.payload - basa[0].payload > 600 for basa in headquarters.get_bases(drone)]) or
            len([drone for drone in drone.headquarters.drones if drone.is_alive])) < 4:
            return None

        if drone.is_full:
            return drone.my_mothership

        full_elirium_stors = headquarters.get_full_elirium_stors(drone)
        elirium_stors_as_targets = headquarters.get_elirium_stors_as_target(drone)

        free_elirium_stors = full_elirium_stors - elirium_stors_as_targets
        elirium_stor_as_target = headquarters.get_elirium_stor_as_target(drone, free_elirium_stors)

        if any([basa[0].payload - drone.mothership.payload > 400 for basa in headquarters.get_bases(drone)]):
            elirium_stor_as_target = max([basa[0] for basa in headquarters.get_bases(drone)], key=lambda x: x.payload)

        if elirium_stor_as_target:
            return elirium_stor_as_target
        else:
            if (enemies or enemies_bases) and drone.have_gun:
                return None
            else:
                return drone.my_mothership

    def next_step(self, purpose):
        drone = self.unit
        drone.actions.append(['move', purpose])

        if self._next_step_by_dasa(purpose):
            return

        if purpose not in drone.headquarters.elirium_stors_in_work:
            purpose_free_to_load = purpose.payload - drone.free_space
            drone.headquarters.elirium_stors_in_work.append(purpose)
            drone.headquarters.elirium_stors_in_work_free_elirium.append(purpose_free_to_load)
        else:
            idx = drone.headquarters.elirium_stors_in_work.index(purpose)
            drone.headquarters.elirium_stors_in_work_free_elirium[idx] -= drone.free_space

        drone.actions.append(['load', purpose])
        drone.actions.append(['it is free', purpose])

    def _next_step_by_dasa(self, purpose):
        drone = self.unit
        headquarters = drone.headquarters
        full_elirium_stors = headquarters.get_full_elirium_stors(drone)

        if purpose == drone.my_mothership:
            if not drone.is_empty:
                drone.actions.append(['unload', purpose])
                return True
            elif full_elirium_stors:
                drone._next_action()
            else:
                drone.stop_at_basa = True
                all_stop = all([drone.stop_at_basa for drone in headquarters.drones if drone.is_alive])
                full_elirium_stors = headquarters.get_full_elirium_stors(drone)
                if not full_elirium_stors and all_stop:
                    drone.headquarters.print_statistic(drone.__class__)
                return True
        return False

    def _next_role(self):
        if self.unit.have_gun:
            return Warrior(self.unit)
        return Collector(self.unit)


class Warrior(DroneRole):
    """
    Роль воина
    """

    def next_purpose(self):
        drone = self.unit
        headquarters = drone.headquarters
        enemies = headquarters.get_enemies(drone)
        enemies_bases = headquarters.get_bases(drone)
        enemies_in_space = [enemy for enemy in enemies if
                            enemy[0].distance_to(enemy[0].mothership) > MOTHERSHIP_HEALING_DISTANCE and
                            enemy[0].distance_to(drone.mothership) > drone.mothership.radius]
        Warrior.victim = (enemies_in_space[0][0] if enemies_in_space else None)

        if self.victim and self.victim.is_alive and drone.distance_to(self.victim) < drone.attack_range:
            pass
        elif enemies_in_space:
            self.victim = enemies_in_space[0][0]
        elif enemies:
            self.victim = enemies[0][0]
        elif enemies_bases:
            self.victim = enemies_bases[0][0]
        else:
            self.victim = None
        return self.victim

    def next_step(self, purpose):
        drone = self.unit
        headquarters = drone.headquarters
        enemies_bases = headquarters.get_bases(drone)

        if drone.distance_to(purpose) > drone.attack_range:
            point_attack = self.get_place_for_attack(drone, purpose)
            if point_attack:
                self.remove_occupied_point_attack(drone)
                drone.actions.append(['move', point_attack])
                return

        collector_is_alive = any((team_mate.is_alive and isinstance(team_mate.role, Collector)) for
                                 team_mate in headquarters.drones)

        if not collector_is_alive and any([drone.mothership.payload - basa[0].payload < 200 for basa in enemies_bases]):
            full_elirium_stors = headquarters.get_full_elirium_stors(drone)
            for elirium_stor in full_elirium_stors:
                if drone.distance_to(elirium_stor) < drone.radius * 4:
                    drone.actions.append(['move', elirium_stor])
                    drone.actions.append(['load', elirium_stor])
                    drone.actions.append(['it is free', elirium_stor])

        if (Warrior.victim and self.valid_bullet_trajectory(drone.coord, Warrior.victim) and
                drone.distance_to(Warrior.victim) < drone.attack_range):
            purpose = Warrior.victim

        if (hasattr(purpose, 'mothership') and purpose.meter_2 < 0.7 and
                drone.distance_to(purpose) < drone.attack_range * 0.6):
            vec = Vector.from_points(purpose.coord, purpose.mothership.coord, module=1)
            vec *= drone.radius * 4
            possible_purpose_coord = Point(purpose.coord.x + vec.x, purpose.coord.y + vec.y)
            drone.actions.append(['turn', possible_purpose_coord])
        else:
            drone.actions.append(['turn', purpose])

        if self.valid_place(drone.coord) and self.valid_bullet_trajectory(drone.coord, purpose):
            safe_mothership_radius = round(drone.mothership.radius * 1.6)
            if drone.mothership.distance_to(drone.coord) < safe_mothership_radius:
                safe_mothership_vec = Vector.from_points(drone.mothership.coord, purpose.coord, module=1)
                safe_mothership_vec = safe_mothership_vec * safe_mothership_radius
                point_attack = Point(drone.coord.x + safe_mothership_vec.x, drone.coord.y + safe_mothership_vec.y)
                drone.actions.append(['move', point_attack])
                return
            drone.actions.append(['shoot', purpose])
        else:
            point_attack = self.get_place_for_attack(drone, purpose)
            if point_attack:
                self.remove_occupied_point_attack(drone)
                drone.actions.append(['move', point_attack])

    def remove_occupied_point_attack(self, drone):
        for point in self.occupied_points_attack:
            if drone.distance_to(point) <= round(drone.radius * 1.5):
                self.occupied_points_attack.remove(point)

    def get_place_for_attack(self, drone, target):
        vec = Vector.from_points(target.coord, drone.coord, module=1)

        dist = drone.distance_to(target)
        vec_gunshot = vec * min(int(drone.attack_range), int(dist))
        purpose = Point(target.coord.x + vec_gunshot.x, target.coord.y + vec_gunshot.y)

        angles = [ang for ang in range(-50, 51, 10)]
        possible_points_attack = []
        for ang in angles:
            vec = Vector(purpose.x - target.x, purpose.y - target.y)
            vec.rotate(ang)
            possible_point_attack = Point(target.x + vec.x, target.y + vec.y)
            possible_points_attack.append(possible_point_attack)

        possible_points_attack.sort(key=lambda x: drone.distance_to(x))
        for point_attack in possible_points_attack:
            place_free = True
            for occupied_point in self.occupied_points_attack:
                place_free = place_free and point_attack.distance_to(occupied_point) >= round(drone.radius * 1.6)

            if (point_attack and self.valid_place(point_attack) and
                    self.valid_bullet_trajectory(point_attack, target) and place_free):
                self.occupied_points_attack.append(point_attack)
                return point_attack

        return None

    def valid_place(self, point):
        drone = self.unit
        save_distance = round(drone.radius * 1.5)
        is_valid = 0 < point.x < theme.FIELD_WIDTH and 0 < point.y < theme.FIELD_HEIGHT

        for team_mate in drone.headquarters.drones:
            if not team_mate.is_alive or team_mate is drone or team_mate.is_moving:
                continue
            is_valid = is_valid and (team_mate.distance_to(point) >= save_distance)

        return is_valid

    def valid_bullet_trajectory(self, point, target):
        drone = self.unit
        save_distance = round(drone.radius * 1.2)
        is_valid = 0 < point.x < theme.FIELD_WIDTH and 0 < point.y < theme.FIELD_HEIGHT

        for length in range(1, round(point.distance_to(target.coord)), round(save_distance / 2)):
            attack_vec = Vector.from_points(point, target.coord, module=1)
            vec_gunshot = attack_vec * length
            point_on_trajectory = Point(point.x + vec_gunshot.x, point.y + vec_gunshot.y)
            for team_mate in drone.headquarters.drones:
                if not team_mate.is_alive or team_mate is drone:
                    continue
                is_valid = is_valid and (team_mate.distance_to(point_on_trajectory) >= save_distance)

        return is_valid

    def _next_role(self):
        return Collector(self.unit)


class OkhotnikovFNDrone(Drone):
    actions = []
    headquarters = None
    attack_range = 0
    limit_health = 0.65

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stop_at_basa = False
        self.role = None

    def _next_action(self):

        if not self.actions:
            self.headquarters.get_actions(self)

        action, target = self.actions[0]
        if action == "move":
            if isinstance(target, Point):
                vec = Vector.from_points(self.coord, target, module=1)
            else:
                vec = Vector.from_points(self.coord, target.coord, module=1)
            self.vector = vec
            self._move_to(target)
            self.actions.pop(0)

        elif action == "unload":
            self.actions.pop(0)
            self.unload_to(target)

        elif action == "load":
            self.actions.pop(0)
            self.load_from(target)

        elif action == "it is free":
            self.actions.pop(0)
            self.elirium_stor_is_free(target)
            self._next_action()

        elif action == "turn":
            if isinstance(target, Point):
                vec = Vector.from_points(self.coord, target, module=1)
            else:
                vec = Vector.from_points(self.coord, target.coord, module=1)
            self.vector = vec
            self.actions.pop(0)
            self.turn_to(target)

        elif action == "shoot":
            self.actions.pop(0)
            self.gun.shot(target)
            self._next_action()

        elif action == "stop":
            return

        else:
            self.actions.pop(0)
            self._next_action()

    def _move_to(self, target):
        self.headquarters.save_statistic_move(self, target)
        super().move_at(target)

    def elirium_stor_is_free(self, elirium_stor):
        self.headquarters.remove_item_elirium_stors_in_work(elirium_stor)

    def _first_step(self):

        full_elirium_stors = self.headquarters.get_full_elirium_stors(self)
        elirium_stors_as_targets = set(elirium_stor for elirium_stor in self.headquarters.elirium_stors_in_work)
        free_elirium_stors = full_elirium_stors - elirium_stors_as_targets

        if not free_elirium_stors:
            elirium_stor = self.headquarters.get_nearest_elirium_stor(self, full_elirium_stors)
            self.prev_elirium_stor = elirium_stor
            return elirium_stor

        elirium_stor = self.headquarters.get_nearest_elirium_stor(self, free_elirium_stors)
        self.headquarters.elirium_stors_in_work.append(elirium_stor)
        self.headquarters.elirium_stors_in_work_free_elirium.append(elirium_stor.payload)
        self.prev_elirium_stor = elirium_stor

        return elirium_stor

    def on_born(self):

        if OkhotnikovFNDrone.headquarters is None:
            OkhotnikovFNDrone.headquarters = Headquarters()
        OkhotnikovFNDrone.headquarters.new_drone(self)

        if self.have_gun:
            self.attack_range = self.gun.shot_distance

        target = self._first_step()
        self.actions.append(['move', target])
        self.actions.append(['load', target])
        self.actions.append(['it is free', target])
        self._next_action()

    def game_step(self):
        super().game_step()
        if self.meter_2 <= self.limit_health and self.distance_to(self.mothership) > MOTHERSHIP_HEALING_DISTANCE:
            self.actions = []
            self._next_action()

    def on_stop_at_asteroid(self, asteroid):
        self._next_action()

    def on_load_complete(self):
        self._next_action()

    def on_stop_at_mothership(self, mothership):
        self._next_action()

    def on_unload_complete(self):
        self._next_action()

    def on_stop_at_point(self, target):
        self._next_action()

    def on_stop(self):
        self._next_action()

    def on_wake_up(self):
        self._next_action()


drone_class = OkhotnikovFNDrone
