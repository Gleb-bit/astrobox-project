# -*- coding: utf-8 -*-

from astrobox.core import Drone
from astrobox.themes.default import MOTHERSHIP_HEALING_DISTANCE, PROJECTILE_SPEED, DRONE_SPEED
from astrobox.themes.default import MIN_ASTEROID_ELERIUM, MAX_ASTEROID_ELERIUM
from robogame_engine.geometry import Point, Vector
from robogame_engine.theme import theme


class Headquarters:
    """
    Класс - штаб-квартира дронов.
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
        Регистрация нового дрона в штаб-квартире
        :param drone: экземпляр класса OkhotnikovFNDrone
        """
        self._add_drone(drone)
        number_drones = len(self.drones)
        self._get_roles(number_drones, drone.have_gun)
        for idx, drone in enumerate(self.drones):
            self._give_role(drone, idx)

    def _give_role(self, drone, index):
        """
        Раздача дронам ролей
        :param drone: экземпляр класса OkhotnikovFNDrone
        """
        all_roles = [Collector for _ in range(Headquarters.roles["collector"])]
        all_roles.extend(Warrior for _ in range(Headquarters.roles["warrior"]))
        this_role = all_roles[index]
        drone.role = this_role(unit=drone)

    def _get_roles(self, number_drones, have_gun):
        """
        Получение количественного списка всех ролей
        :param number_drones: определяет колличество дронов
        :param have_gun: определяет наличие у дронов оружия
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
        """
        Добавление дрона в список дронов штаб-квартиры
        :param drone: экземпляр класса OkhotnikovFNDrone
        """
        drone.actions = []
        self.drones.append(drone)

    def get_actions(self, drone):
        """
        Получение дроном нового действия, действия добавляются в список и выполняются по очереди
        :param drone: экземпляр класса OkhotnikovFNDrone
        """

        full_elirium_stors = self.get_full_elirium_stors(drone)
        enemies = self.get_enemies(drone)
        enemies_bases = self.get_bases(drone)

        if not full_elirium_stors and drone.stop_at_basa:
            self._stop_action(drone, enemies, enemies_bases)
            return

        if drone.meter_2 <= drone.limit_health and drone.distance_to(drone.mothership) > MOTHERSHIP_HEALING_DISTANCE:
            self._low_health_action(drone)
            return

        purpose = drone.role.next_purpose()

        if purpose:
            drone.role.next_step(purpose)
        else:
            self._emty_pupose_action(drone)

    def _emty_pupose_action(self, drone):
        """
        Действия дрона при отсутствии цели
        :param drone: экземпляр класса OkhotnikovFNDrone
        """
        drone.actions = []
        drone.role.change_role()
        purpose = drone.role.next_purpose()
        if purpose:
            drone.role.next_step(purpose)
        else:
            drone.actions.append(['move', drone.my_mothership])
            drone._next_action()

    def _low_health_action(self, drone):
        """
        Действия дрона при низком здоровье
        :param drone: экземпляр класса OkhotnikovFNDrone
        """
        self.elirium_stors_in_work = []
        self.elirium_stors_in_work_free_elirium = []
        if hasattr(drone.role, 'remove_occupied_point_attack'):
            drone.role.remove_occupied_point_attack(drone)
        drone.actions.append(['move', drone.my_mothership])
        if drone.payload > 0:
            drone.actions.append(['unload', drone.my_mothership])

    def _stop_action(self, drone, enemies, enemies_bases):
        """
        Действия дрона, когда необходимо закончить игру
        :param drone: экземпляр класса OkhotnikovFNDrone
        :param enemies: список живых вражеских дронов
        :param enemies_bases: список живых вражеских баз
        """
        if drone.have_gun:
            if not enemies and not enemies_bases:
                drone.actions = []
                drone.actions.append(['stop', 'stop'])
        else:
            drone.actions = []
            drone.actions.append(['stop', 'stop'])

    def get_enemies(self, drone):
        """
        Получение списка вражеских дронов, отсортированного по возрастанию удаленности от дрона
        :param drone: class OkhotnikovFNDrone
        :return: список кортежей (вражеских дрон, расстояние до вражеского дрона) живых вражеских дронов
        """
        enemies = [(enemy, drone.distance_to(enemy)) for enemy in drone.scene.drones if
                   drone.team != enemy.team and enemy.is_alive]
        enemies.sort(key=lambda x: x[1])
        return enemies

    def get_bases(self, drone):
        """
        Получение списка живых вражеских баз, отсортированного по возрастанию удаленности от дрона
        :param drone: экземпляр класса OkhotnikovFNDrone
        :return: список кортежей (вражеская база, расстояние до вражеской базы) живых вражеских баз
        """
        bases = [(base, drone.distance_to(base)) for base in drone.scene.motherships if
                 base.team != drone.team and base.is_alive]
        bases.sort(key=lambda x: x[1])
        return bases

    def get_full_elirium_stors(self, drone):
        """
        Получение множества всех объектов, из которых, можно добывать элириум
        :param drone: экземпляр класса OkhotnikovFNDrone
        :return: множество астероидов, мертвых вражевких баз, мертвых вражеских дронов, в которых есть ресурсы
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
        :param drone: экземпляр класса OkhotnikovFNDrone
        :return: множество объектов для добычи элириума, которые уже заняты
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
        :param drone: экземпляр класса OkhotnikovFNDrone
        :param available_elirium_stors: доступные для загрузки ресурсов объекты
        :return: обект, из которого добывать ресурсы
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
        """
        Получение ближайшей цели, из которой можно добывать элириум
        :param drone: экземпляр класса OkhotnikovFNDrone
        :param available_elirium_stors: доступные для загрузки ресурсов объекты
        :return: ближайший обект, из которого добывать ресурсы
        """
        elirium_stor_distances = [(elirium_stor, drone.distance_to(elirium_stor)) for elirium_stor in
                                  available_elirium_stors]
        elirium_stor = min(elirium_stor_distances, key=lambda x: x[1])[0] if elirium_stor_distances else None
        return elirium_stor

    def remove_item_elirium_stors_in_work(self, elirium_stor):
        """
        Удаление обекта для добычи элириума из списка занятых
        :param elirium_stor: объект, который надо удалить из списка
        """
        if elirium_stor in self.elirium_stors_in_work:
            idx = self.elirium_stors_in_work.index(elirium_stor)
            self.elirium_stors_in_work.pop(idx)
            self.elirium_stors_in_work_free_elirium.pop(idx)

    def save_statistic_move(self, drone, purpose):
        """
        Сохрание статистки движения команды с разной загрузкой трюма
        :param drone: экземпляр класса OkhotnikovFNDrone
        :param purpose: обект, расстояние до которого нужно посчитать
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
        :class_name: класс OkhotnikovFNDrone
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
    """
    Базовый класс роли дрона
    """
    victim = None
    occupied_points_attack = []

    def __init__(self, unit):
        self.unit = unit
        self.victim = None

    def change_role(self, role=None):
        """
        Меняет роль дрона
        :param role: роль дрона
        """
        drone = self.unit
        if not role:
            drone.role = self._next_role()
        else:
            drone.role = role(drone)

    def _next_role(self):
        """
        Определяет следующую роль
        """
        pass

    def next_purpose(self):
        """
        Определяет следующую цель
        """
        pass

    def next_step(self, purpose):
        """
        Следующие шаги, которые добавляются в обший список команд
        :param purpose: обект, колученный в методе next_purpose
        """
        pass


class Collector(DroneRole):
    """
    Роль сборщика элириума
    """

    def next_purpose(self):
        """
        Определяет следующую цель
        :return: цель из которой добывать элириум, если None, то будет смена роли дрона
        """
        drone = self.unit

        headquarters = drone.headquarters
        enemies = headquarters.get_enemies(drone)
        enemies_bases = headquarters.get_bases(drone)

        if self._check_role(drone, enemies, enemies_bases, headquarters):
            return None

        if drone.is_full:
            return drone.my_mothership

        elirium_stor_as_target = self._get_elirium_stor_as_target(drone, headquarters)

        if elirium_stor_as_target:
            return elirium_stor_as_target
        else:
            if (enemies or enemies_bases) and drone.have_gun:
                return None
            else:
                return drone.my_mothership

    def _check_role(self, drone, enemies, enemies_bases, headquarters):
        """
        Метод определяет нужно ли поменять роль втечение боя
        :param drone: экземпляр класса OkhotnikovFNDrone
        :param enemies: список живых вражеских дронов
        :param enemies_bases: список живых вражеских баз
        :param headquarters: экземпляр класса Headquarters
        :return: булевое значение необходимости поменять роль
        """
        team_count = len(drone.scene.motherships)
        count_asteroids = len(set(aster for aster in drone.asteroids))
        average_elirium_in_asteroid = (MAX_ASTEROID_ELERIUM + MIN_ASTEROID_ELERIUM) / 2
        difference_payload = average_elirium_in_asteroid * count_asteroids / team_count * 0.4
        alive_enemies = 1
        alive_teammates = 4

        if (len(enemies) == alive_enemies and
                all(basa[0].payload < drone.mothership.payload for basa in enemies_bases) and
                drone.have_gun):
            return True

        if (all([drone.mothership.payload - basa[0].payload > difference_payload for basa in enemies_bases]) and
                enemies_bases):
            return True

        if len([drone for drone in drone.headquarters.drones if drone.is_alive]) < alive_teammates:
            return True

        return False

    def _get_elirium_stor_as_target(self, drone, headquarters):
        """
        Получение цели из которой добывать элириум
        :param drone: экземпляр класса OkhotnikovFNDrone
        :param headquarters: экземпляр класса Headquarters
        :return: объект, из которого добывать элириум
        """
        full_elirium_stors = headquarters.get_full_elirium_stors(drone)
        elirium_stors_as_targets = headquarters.get_elirium_stors_as_target(drone)
        free_elirium_stors = full_elirium_stors - elirium_stors_as_targets
        elirium_stor_as_target = headquarters.get_elirium_stor_as_target(drone, free_elirium_stors)

        return elirium_stor_as_target

    def next_step(self, purpose):
        """
        Определяет следующие шаги, которые добавляются в обший список команд
        :param purpose: обект, колученный в методе next_purpose
        """
        drone = self.unit
        drone.actions.append(['move', purpose])

        if self._next_step_by_dasa(purpose, drone):
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

    def _next_step_by_dasa(self, purpose, drone):
        """
        Определяет действия дрона, если целью, является своя база
        :param purpose: обект, колученный в методе next_purpose
        :param drone: экземпляр класса OkhotnikovFNDrone
        :return: возвращает булевое значение, нужно ли продолжать расчет в методе next_step
        """
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
        """
        Определяет следующую роль
        """
        if self.unit.have_gun:
            return Warrior(self.unit)
        return Collector(self.unit)


class Warrior(DroneRole):
    """
    Роль воина
    """

    def next_purpose(self):
        """
        Определяет следующую цель
        :return: цель в которую стрелять
        """
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
        """
        Определяет следующие шаги, которые добавляются в обший список команд
        :param purpose: обект, колученный в методе next_purpose
        """
        drone = self.unit

        if drone.distance_to(purpose) > drone.attack_range:
            point_attack = self.get_place_for_attack(drone, purpose)
            if point_attack:
                self.remove_occupied_point_attack(drone)
                drone.actions.append(['move', point_attack])
                return

        self._load_elirium_if_not_collector(drone)

        if (Warrior.victim and self.valid_bullet_trajectory(drone.coord, Warrior.victim) and
                drone.distance_to(Warrior.victim) < drone.attack_range):
            purpose = Warrior.victim

        self._turn_to_purpose(drone, purpose)
        self._shoot_or_move(drone, purpose)

    def _shoot_or_move(self, drone, purpose):
        """
        Происходит выбор делать выстрел или сменить позицию
        :param drone: экземпляр класса OkhotnikovFNDrone
        :param purpose: обект, колученный в методе next_purpose
        """
        safe_mothership_radius = round(drone.mothership.radius * 1.6)

        if self.valid_place(drone.coord) and self.valid_bullet_trajectory(drone.coord, purpose):
            if drone.mothership.distance_to(drone.coord) < safe_mothership_radius:
                safe_mothership_vec = Vector.from_points(drone.mothership.coord, purpose.coord, module=1)
                dist_to_move = round(safe_mothership_radius - drone.distance_to(drone.mothership) + 2)
                safe_mothership_vec = safe_mothership_vec * dist_to_move
                point_attack = Point(drone.coord.x + safe_mothership_vec.x, drone.coord.y + safe_mothership_vec.y)
                drone.actions.append(['move', point_attack])
                return
            drone.actions.append(['shoot', purpose])
        else:
            point_attack = self.get_place_for_attack(drone, purpose)
            if point_attack:
                self.remove_occupied_point_attack(drone)
                drone.actions.append(['move', point_attack])

    def _turn_to_purpose(self, drone, purpose):
        """
        Поворот к цели
        :param drone: экземпляр класса OkhotnikovFNDrone
        :param purpose: обект, колученный в методе next_purpose
        """
        if hasattr(purpose, 'is_moving') and purpose.is_moving:
            purpose_vec = Vector.from_direction(direction=purpose.direction, module=1)
            drone_purpose_vec = Vector.from_points(purpose.coord, drone.coord)

            length = drone_purpose_vec.module if drone_purpose_vec.module > 0 else 1
            _cos = ((purpose_vec.x * drone_purpose_vec.x + purpose_vec.y * drone_purpose_vec.y) /
                    (length * purpose_vec.module))
            coef_b = (PROJECTILE_SPEED ** 2 - DRONE_SPEED ** 2)
            coef_d = (2 * DRONE_SPEED * length * _cos) ** 2 + 4 * coef_b * (length ** 2)
            coef = round((-2 * DRONE_SPEED * length + coef_d ** 0.5) / (2 * coef_b) * DRONE_SPEED)
            purpose_vec = purpose_vec * coef
            possible_purpose = Point(purpose.coord.x + purpose_vec.x, purpose.coord.y + purpose_vec.y)

            drone.actions.append(['turn', possible_purpose])
        else:
            drone.actions.append(['turn', purpose])

    def _load_elirium_if_not_collector(self, drone):
        """
        Загрузка элириума, если нету живого сборщика в команде
        :param drone: экземпляр класса OkhotnikovFNDrone
        :param headquarters: экземпляр класса Headquarters
        """
        difference_payload = 200
        load_elirium_radius = drone.radius * 4

        headquarters = drone.headquarters
        enemies_bases = headquarters.get_bases(drone)
        collector_is_alive = any((team_mate.is_alive and isinstance(team_mate.role, Collector)) for
                                 team_mate in headquarters.drones)

        if (not collector_is_alive and
                any([drone.mothership.payload - basa[0].payload < difference_payload for basa in enemies_bases]) and
                drone.meter_1 < 1):
            full_elirium_stors = headquarters.get_full_elirium_stors(drone)
            for elirium_stor in full_elirium_stors:
                if drone.distance_to(elirium_stor) < load_elirium_radius:
                    drone.actions.append(['move', elirium_stor])
                    drone.actions.append(['load', elirium_stor])
                    drone.actions.append(['it is free', elirium_stor])

    def remove_occupied_point_attack(self, drone):
        """
        Очистка занятой точки для атаки
        :param drone: экземпляр класса OkhotnikovFNDrone
        """
        for point in self.occupied_points_attack:
            if drone.distance_to(point) <= round(drone.radius * 1.5):
                self.occupied_points_attack.remove(point)

    def get_place_for_attack(self, drone, purpose):
        """
        Получение места для атаки
        :param drone: экземпляр класса OkhotnikovFNDrone
        :param purpose: обект, колученный в методе next_purpose
        :return: точка на карте, из которой будет вестись огонь по цели
        """
        safe_distance = round(drone.radius * 1.6)

        vec = Vector.from_points(purpose.coord, drone.coord, module=1)
        dist = drone.distance_to(purpose)
        vec_gunshot = vec * min(int(drone.attack_range), int(dist))
        target = Point(purpose.coord.x + vec_gunshot.x, purpose.coord.y + vec_gunshot.y)

        possible_points_attack = self._get_possible_points_attack(target, purpose, drone)
        # print(possible_points_attack)
        for point_attack in possible_points_attack:
            place_free = True
            for occupied_point in self.occupied_points_attack:
                place_free = place_free and point_attack.distance_to(occupied_point) >= safe_distance

            if (point_attack and self.valid_place(point_attack) and
                    self.valid_bullet_trajectory(point_attack, purpose) and place_free):
                self.occupied_points_attack.append(point_attack)
                return point_attack

        return None

    def _get_possible_points_attack(self, target, purpose, drone):
        """
        Получение возможных точек для атаки в порядке удаления от текущего положения дрона
        :param target: точка на карте, расположенная на растоянии выстрела от purpose
        :param purpose: обект, колученный в методе next_purpose
        :param drone: экземпляр класса OkhotnikovFNDrone
        :return: список точек на карте из которых возможно вести стрельбу по цели purpose
        """
        angles = [ang for ang in range(-50, 51, 10)]
        possible_points_attack = []
        for ang in angles:
            vec = Vector(target.x - purpose.x, target.y - purpose.y)
            vec.rotate(ang)
            possible_point_attack = Point(purpose.x + vec.x, purpose.y + vec.y)
            possible_points_attack.append(possible_point_attack)
        possible_points_attack.sort(key=lambda x: drone.distance_to(x))
        return possible_points_attack

    def valid_place(self, point):
        """
        Проверка валидности места для атаки
        :param point: одна из точек на карте из списка полученного в _get_possible_points_attack
        :return: булевое значение, валидна или нет
        """
        drone = self.unit
        safe_distance = round(drone.radius * 1.5)
        is_valid = 0 < point.x < theme.FIELD_WIDTH and 0 < point.y < theme.FIELD_HEIGHT

        for team_mate in drone.headquarters.drones:
            if not team_mate.is_alive or team_mate is drone or team_mate.is_moving:
                continue
            is_valid = is_valid and (team_mate.distance_to(point) >= safe_distance)

        return is_valid

    def valid_bullet_trajectory(self, point, purpose):
        """
        Проверка, нету ли дронов из своей команды на траектории выстрела из точки point
        :param point: одна из точек на карте из списка полученного в _get_possible_points_attack
        :param purpose: обект, колученный в методе next_purpose
        :return: булевое значение, валидна или нет
        """
        drone = self.unit
        safe_distance = round(drone.radius * 1.2)
        is_valid = 0 < point.x < theme.FIELD_WIDTH and 0 < point.y < theme.FIELD_HEIGHT
        mothership = drone.mothership
        is_valid = is_valid and (mothership.distance_to(purpose) > mothership.radius)

        for length in range(1, round(point.distance_to(purpose.coord)), round(safe_distance / 2)):
            attack_vec = Vector.from_points(point, purpose.coord, module=1)
            vec_gunshot = attack_vec * length
            point_on_trajectory = Point(point.x + vec_gunshot.x, point.y + vec_gunshot.y)
            for team_mate in drone.headquarters.drones:
                if not team_mate.is_alive or team_mate is drone:
                    continue
                is_valid = is_valid and (team_mate.distance_to(point_on_trajectory) >= safe_distance)

        return is_valid

    def _next_role(self):
        return Collector(self.unit)


class OkhotnikovFNDrone(Drone):
    headquarters = None
    attack_range = 0
    limit_health = 0.65

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stop_at_basa = False
        self.role = None
        self.actions = []

    def _next_action(self):
        """
        Выполение команды из списка, если команды нету, то получает новую команду
        """

        if not self.actions:
            self.headquarters.get_actions(self)

        action, target = self.actions[0]
        if action == "move":
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
        """
        Модификация базавого метода move, для расчета движения дронов с разной загрузкой
        :param target: цель полученная из списка выполняемых команд
        """
        self.headquarters.save_statistic_move(self, target)
        super().move_at(target)

    def elirium_stor_is_free(self, elirium_stor):
        """
        Освобождение источника элириума из занятых
        :param elirium_stor: цель полученная из списка выполняемых команд
        """
        self.headquarters.remove_item_elirium_stors_in_work(elirium_stor)

    def _first_step(self):
        """
        Первая команда для всех дронов
        :return: возвращает объект, из которого можно добывать элириум
        """

        full_elirium_stors = self.headquarters.get_full_elirium_stors(self)
        elirium_stors_as_targets = set(elirium_stor for elirium_stor in self.headquarters.elirium_stors_in_work)
        free_elirium_stors = full_elirium_stors - elirium_stors_as_targets

        if not free_elirium_stors:
            elirium_stor = self.headquarters.get_nearest_elirium_stor(self, full_elirium_stors)
            return elirium_stor

        elirium_stor = self.headquarters.get_nearest_elirium_stor(self, free_elirium_stors)
        self.headquarters.elirium_stors_in_work.append(elirium_stor)
        self.headquarters.elirium_stors_in_work_free_elirium.append(elirium_stor.payload)

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
