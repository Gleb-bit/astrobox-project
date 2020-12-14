# -*- coding: utf-8 -*-
from astrobox.core import Drone
from robogame_engine.geometry import Point, Vector

DEFER = "defer"
COMANDO = "comandir"
DISTANSE_BETWEEN_POINT_TO_ATTACK = 65
DISTANCE_HIDE_FIRST_ASTEROID = 600
LEFT_DAWN = "1"
RIGHT_DAWN = "2"
LEFT_UP = "3"
RIGHT_UP = "4"


class OlshannikovDron(Drone):
    my_team = []
    my_team_defer = []
    all_distans_flights = 0
    distans_of_fullness = 0
    distans_of_empty = 0
    distans_of_filled = 0
    points_for_attack = []
    our_commander = None
    point_for_defing = None

    def on_born(self):
        """Метод движка игры, вызываемый при создании дрона"""
        self.role = None
        self.get_role()
        self.sum_payload = 0
        self.dron_for_action = None
        self.my_point_attack = None
        self.unloading_dron = None
        self.loading_dron = None
        self.shot_is_fired = 0
        self.my_target_attack = None
        self.my_points_attack = None
        self.my_point_attack_info = None
        self.last_location_enemy = None
        self.place_shot_gun = None
        self.distans_of_fullness_in_persent = 0
        self.distans_of_filled_in_persent = 0
        self.distans_of_empty_in_persent = 0
        self.count_fire_for_change_position = 6
        self.distanse_between_point_to_attack = DISTANSE_BETWEEN_POINT_TO_ATTACK
        self.distance_hide_first_asteroid = DISTANCE_HIDE_FIRST_ASTEROID
        self.hide = None
        self.avaid = None
        self.shot_distance = 681
        self.create_point_defing()
        self.target = self.get_good_first_asteroid()
        self.move_at(self.target)

    def add_to_team(self):
        """Добавление дрона к списку дронов его роли"""
        self.my_team.append(self)
        if self.role == DEFER:
            self.my_team_defer.append(self)
        if self.role == COMANDO:
            OlshannikovDron.our_commander = self

    def delete_in_team(self):
        """Удаление дрона из его команды"""
        self.my_team.remove(self)
        if self.role == DEFER:
            self.my_team_defer.remove(self)
        if self.role == COMANDO:
            OlshannikovDron.our_commander = None

    def get_role(self):
        """Выдача начальных ролей дронам """
        if len(self.my_team) == 3:
            self.role = COMANDO
        else:
            self.role = DEFER
        self.add_to_team()

    def to_death(self):
        """Функция вызывающая при смерти дрона"""
        self.delete_in_team()

    def create_point_defing(self):
        """Создание точки обороны в зависимости от расположения базы"""
        self.determine_position_my_mothership()
        if self.position_my_mothership == LEFT_DAWN:
            point = Point(self.my_mothership.coord.x + 82, self.my_mothership.coord.y + 82)
            OlshannikovDron.point_for_defing = point
        elif self.position_my_mothership == RIGHT_DAWN:
            point = Point(self.my_mothership.coord.x - 82, self.my_mothership.coord.y + 82)
            OlshannikovDron.point_for_defing = point
        elif self.position_my_mothership == LEFT_UP:
            point = Point(self.my_mothership.coord.x + 82, self.my_mothership.coord.y - 82)
            OlshannikovDron.point_for_defing = point
        elif self.position_my_mothership == RIGHT_UP:
            point = Point(self.my_mothership.coord.x - 82, self.my_mothership.coord.y - 82)
            OlshannikovDron.point_for_defing = point

    def get_distance_to_enemy_motherships(self):
        """Определяет дистанцию вражеских баз от союзной"""
        self.distance_to_mothrships = []
        for motheship in self.scene.motherships:
            distance = self.my_mothership.distance_to(motheship)
            self.distance_to_mothrships.append([motheship, distance])
        self.distance_to_mothrships.sort(key=lambda x: x[1], reverse=False)
        self.distance_to_mothrships.pop(0)
        self.distance_to_mothrships.sort(key=lambda x: x[1], reverse=True)
        return self.distance_to_mothrships

    def determine_position_my_mothership(self):
        """Определяет, в каком углу зареспилась база"""
        self.position_my_mothership = None
        sum_x_and_y = int(self.my_mothership.coord.x) + int(self.my_mothership.coord.y)
        if sum_x_and_y == 180:
            self.position_my_mothership = LEFT_DAWN
            return
        elif sum_x_and_y == 2220:
            self.position_my_mothership = RIGHT_UP
            return
        if int(self.my_mothership.coord.x) == 1110:
            self.position_my_mothership = RIGHT_DAWN
            return
        else:
            self.position_my_mothership = LEFT_UP

    def set_distance_to_asteroids(self):
        """Определяет растояния до астеройдов относительно дрона"""
        self.distance_to_asteroids = []
        for asteroid in self.asteroids:
            if asteroid.payload:
                self.distance_to_asteroids.append([asteroid, self.distance_to(asteroid)])
        self.distance_to_asteroids.sort(key=lambda x: x[1])
        if self.distance_to_asteroids:
            self.near_asteroid = self.distance_to_asteroids[0]
        return self.distance_to_asteroids

    def choice_asteroid_with_team(self):
        """Функция выбора астеройда, учитывая выбор своей команды и загруженности астеройда"""
        self.my_team_withot_me = []
        self.my_team_withot_me.extend(self.my_team)
        self.my_team_withot_me.remove(self)
        self.my_asteroid = []
        for asteroid in self.distance_to_asteroids:
            if self.check_asteroid_with_team(asteroid):
                return self.my_asteroid
        if self.distance_to_asteroids:
            self.my_asteroid = self.distance_to_asteroids[0][0]
            return self.my_asteroid
        else:
            self.create_point_behind_comandor()
            self.my_asteroid = self.point_bihind_comandor
            return self.my_asteroid

    def check_asteroid_with_team(self, asteroid, lower_value_payload=-50):
        """Проверка конкретного астеройда"""
        if not self.my_team_withot_me:
            self.expected_payload_asteroid_with_me = asteroid[0].payload - self.free_space
            self.my_asteroid = asteroid[0]
            return self.my_asteroid
        elif len(self.my_team_withot_me) == 1:
            return self.check_alleged_payload_when_one_ally(asteroid, lower_value_payload)
        else:
            return self.check_alleged_payload_with_team(asteroid, lower_value_payload)

    def check_alleged_payload_when_one_ally(self, asteroid, lower_value_payload):
        """Проверка загруженности астеройдов, если дрон 1"""
        if self.my_team_withot_me[0].target == asteroid[0]:
            self.supposed_payload_asteroid = asteroid[0].payload - self.my_team_withot_me[0].free_space
            self.expected_payload_asteroid_with_me = self.supposed_payload_asteroid - self.free_space
            if self.expected_payload_asteroid_with_me > -lower_value_payload:
                self.my_asteroid = asteroid[0]
                return self.my_asteroid
        else:
            self.my_asteroid = asteroid[0]
            return self.my_asteroid

    def check_alleged_payload_with_team(self, asteroid, lower_value_payload):
        """Проверка загруженности астеройдов если есть команда"""
        self.supposed_payload_asteroid = asteroid[0].payload
        for dron in self.my_team_withot_me:
            if dron.target == asteroid[0]:
                self.supposed_payload_asteroid -= dron.free_space
        self.expected_payload_asteroid_with_me = self.supposed_payload_asteroid - self.free_space
        if self.expected_payload_asteroid_with_me > lower_value_payload:
            self.my_asteroid = asteroid[0]
            return self.my_asteroid

    def _get_my_asteroid(self):
        """Возвращает оптимальный астеройд, с которого нужно собирать ресурсы"""
        self.set_distance_to_asteroids()
        self.choice_asteroid_with_team()
        return self.my_asteroid

    def get_good_first_asteroid(self):
        """Выбор астеройда, когда только зареспились"""
        self.set_distance_to_first()
        self.choice_first_asteroid()
        return self.my_asteroid

    def set_distance_to_first(self):
        """Определяется дистанция до астеройдов, для первого полёта"""
        self.distance_to_asteroids = []
        for asteroid in self.asteroids:
            self.distance_to_asteroids.append([asteroid, self.distance_to(asteroid), asteroid.payload])
        self.distance_to_asteroids.sort(key=lambda x: x[2])
        self.distance_to_asteroids.reverse()
        return self.distance_to_asteroids

    def choice_first_asteroid(self):
        """Выбор первого астеройда"""
        self.my_team_withot_me = []
        self.my_team_withot_me.extend(self.my_team)
        self.my_team_withot_me.remove(self)
        self.my_asteroid = []
        asteroid_for_delate = []
        for asteroid in self.distance_to_asteroids:
            if asteroid[1] > self.distance_hide_first_asteroid:
                asteroid_for_delate.append(asteroid)
        if asteroid_for_delate:
            for asteroid in asteroid_for_delate:
                self.distance_to_asteroids.remove(asteroid)
        for asteroid in self.distance_to_asteroids:
            if self.check_asteroid_with_team(asteroid, 0):
                return self.my_asteroid
        self.distance_to_asteroids.sort(key=lambda x: x[1])
        for asteroid in asteroid_for_delate:
            if self.check_asteroid_with_team(asteroid, 0):
                return self.my_asteroid

    def on_stop_at_asteroid(self, asteroid):
        """Действие если дрон остановился около астеройда"""
        if self.expected_payload_asteroid_with_me > -70:
            self.turn_to(self.my_mothership)
        else:
            if len(self.distance_to_asteroids) > 1:
                self.turn_to(self.distance_to_asteroids[1][0])
        self.load_from(asteroid)

    def on_load_complete(self):
        """Метод движка игры, должен вызываться когда загрузка закончена"""
        self.selecting_action()

    def on_stop_at_mothership(self, mothership):
        """Метод движка игры, действие при остановке у базы"""
        self.unload_to(mothership)
        if self.distance_to_asteroids:
            self.turn_to(self.distance_to_asteroids[0][0])

    def on_unload_complete(self):
        """Метод движка игры, должен вызываться когда выгрузка закончена"""
        self.selecting_action()

    def on_wake_up(self):
        """Метод движка игры, должен вызываться когда дрон простаивает"""
        self.selecting_action()

    def move_at(self, target, speed=None):
        """Метод движка игры, отвечающий за команду перемещения дрона, с добавлением функции  логирования
        статистики перелётов"""
        super().move_at(target, speed)
        self.target = target
        self.collection_statistics_of_flights(target=target)
        self.distans_to_persent()
        self.loging_statistics_of_flights()

    def collection_statistics_of_flights(self, target):
        """Функция обновления статистики пройденных расстояний с учётом заполненности"""
        if self.fullness == 1.0:
            self.distans_of_fullness += self.distance_to(target)
        elif self.fullness == 0.0:
            self.distans_of_empty += self.distance_to(target)
        else:
            self.distans_of_filled += self.distance_to(target)

    def distans_to_persent(self):
        """Функция переводящая пройденное расстояние в проценты"""
        self.all_distans_flights = self.distans_of_fullness + self.distans_of_empty + self.distans_of_filled
        self.distans_of_fullness_in_persent = int(self.distans_of_fullness / self.all_distans_flights * 100)
        self.distans_of_filled_in_persent = int(self.distans_of_filled / self.all_distans_flights * 100)
        self.distans_of_empty_in_persent = int(self.distans_of_empty / self.all_distans_flights * 100)

    def loging_statistics_of_flights(self):
        """Функция логирующая проценностное соотношение пройденных расстояний"""
        text_for_write = f'Преодолено расстояная полностью заполненным - {self.distans_of_fullness_in_persent}% \n' \
                         f'Преодалено расстояния с грузом на борту - {self.distans_of_filled_in_persent}% \n' \
                         f'Преоделено расстояния с пустым трюмом {self.distans_of_empty_in_persent}%'
        with open(file="statistics_of_flights.txt", mode="w", encoding="utf-8") as file:
            file.write(text_for_write)

    def selecting_action(self):
        """Выбор действия дрона в зависимости от версии"""
        if self.role == DEFER:
            self.selecting_action_defer()
        if self.role == COMANDO:
            self.selecting_actiom_comando()

    def selecting_action_looter(self):
        """Метод определяющий действие дрона при команде сбора ресурсов"""
        if self.need_loading_in_dron():
            self.interaction_dron()
        elif self.need_unload_to_mothership():
            self.move_at(self.my_mothership)
        elif not self.asteroids:
            self.move_at(self.point_for_defing)
        else:
            self.move_at(self._get_my_asteroid())

    def set_distance_to_my_team(self):
        """Формирует список до союзных не полных дронов, которые не заняты другими дронами исключая себя"""
        self.distance_to_my_team = []
        if len(self.my_team_defer) == 1:
            dron = self.my_team_defer[0]
            if dron.fullness != 1.0:
                if not dron.loading_dron:
                    self.distance_to_my_team.append([dron, self.distance_to(dron)])
        else:
            for dron in self.my_team_defer:
                if dron.fullness != 1.0:
                    if not dron.loading_dron:
                        self.distance_to_my_team.append([dron, self.distance_to(dron)])
        self.distance_to_my_team.sort(key=lambda x: x[1])

    def need_loading_in_dron(self):
        """Функция определяющая, необходимости разгрузки в дрона"""
        if self.fullness == 1.0:
            return False
        if self.distance_to(self.my_mothership) == 0:
            return False
        self.set_distance_to_my_team()
        for dron, distance_to_dron in self.distance_to_my_team:
            if distance_to_dron < 10:
                sum_payload = self.payload + dron.payload
                if 110 < sum_payload < 185:
                    self.dron_for_action = dron
                    return True

    def interaction_dron(self):
        """Функция отвечающая за осуществелния разгрузки/загрузки в союзного дрона"""
        if self.dron_for_action.payload < self.payload:
            self.unloading_dron = self.dron_for_action
            self.loading_dron = self
        else:
            self.unloading_dron = self
            self.loading_dron = self.dron_for_action
        if self.unloading_dron.near(self.loading_dron):
            self.unloading_dron.turn_to(self._get_my_asteroid())
            self.unloading_dron.unload_to(self.loading_dron)
            self.loading_dron.load_from(self.unloading_dron)
            self.loading_dron.turn_to(self.my_mothership)

    def need_unload_to_mothership(self):
        """Нужно ли лететь разгружаться на базу"""
        if self.distance_to(self.my_mothership) == 0.0:
            return False
        if self.fullness > 0.9:
            return True
        self.set_distance_to_asteroids()
        if not self.distance_to_asteroids:
            return True
        self._get_my_asteroid()
        self.proportion_need_for_unloading = (self.distance_to(self.my_asteroid) /
                                              self.distance_to(self.my_mothership)) * \
                                             self.fullness
        return self.proportion_need_for_unloading >= 0.4

    def selecting_actiom_comando(self):
        """Выбор действия командира"""
        self.check_ally()
        if len(self.my_team_withot_me) < 4:
            self.go_to_defing_my_mothership()
        elif not self.distance_to_asteroids:
            self.go_to_defing_my_mothership()
        elif self.my_mothership.health < 50:
            self.go_to_defing_my_mothership()
        else:
            self.selecting_action_looter()

    def check_ally(self):
        """Проверка живы ли союзники"""
        if self.health == 0:
            return
        if len(self.my_team) == 1:
            return
        self.my_team_withot_me = []
        for ally in self.my_team:
            if ally.health > 0:
                self.my_team_withot_me.append(ally)
        self.my_team_withot_me.remove(self)

    def go_to_defing_my_mothership(self):
        """Лететь к точке защиты, команда союзникам спрятаться или раскрыться"""
        if self.near(self.point_for_defing):
            self.hide_away_all_off()
            self.defing_my_mothership()
        else:
            self.hide_away_all_on()
            self.move_at(self.point_for_defing)

    def defing_my_mothership(self):
        """Метод определяющий защиты базы"""
        if self.my_target_attack:
            if self.shot_is_fired == self.count_fire_for_change_position:
                self.shot_is_fired = 0
                self.get_my_victim()
                if not self.my_target_attack:
                    return
                self.give_victim_my_team()
                if self.my_target_attack:
                    self.create_points_to_attack()
                    self.give_points_to_attack_to_defer()
                    self.attact_enemy()
            else:
                self.attact_enemy()
        else:
            self.get_my_victim()
            if not self.my_target_attack:
                return
            self.give_victim_my_team()
            self.create_points_to_attack()
            self.give_points_to_attack_to_defer()
            self.attact_enemy()

    def hide_away_all_on(self):
        """Спрятать всю команду"""
        for ally in self.my_team:
            ally.hide = True

    def hide_away_all_off(self):
        """Вся команда перестаёт быть спрятаной"""
        for ally in self.my_team:
            ally.hide = None

    def get_my_victim(self):
        """Метод выбора врага"""
        self.get_distance_to_enemy(self)
        self.target = self.get_my_target_enemy()

    def create_points_to_attack(self):
        """Создать точки для атаки"""
        enemy = self.my_target_attack
        vec = Vector.from_points(self.coord, enemy.coord)
        vec.rotate(180)
        self.points_for_attack = []
        for angle in range(0, 360, 2):
            vec.rotate(angle)
            point_to_attack = Point(enemy.coord.x + vec.x, enemy.coord.y + vec.y)
            if point_to_attack.x > 0 and point_to_attack.y > 0:
                self.points_for_attack.append(point_to_attack)
        self.corected_point_to_attack_for_mothership()
        self.delete_point_near_for_me()
        while self.delate_nearest_points(self.distanse_between_point_to_attack):
            pass
        return self.points_for_attack

    def delete_point_near_for_me(self):
        """Удалить точки вокруг командира"""
        point_for_delate = []
        for point in self.points_for_attack:
            if self.distance_to(point) < self.distanse_between_point_to_attack:
                point_for_delate.append(point)
        for point in point_for_delate:
            self.points_for_attack.remove(point)

    def delate_nearest_points(self, radius=50):
        """Удаление точек атаки, лежащих друг другу ближе радиуса"""
        point_for_delate_uncorect = []
        for point_analiz in self.points_for_attack:
            for point in self.points_for_attack:
                distance = point_analiz.distance_to(point)
                if distance == 0:
                    continue
                if distance < radius:
                    point_for_delate_uncorect.append(point)
            if point_for_delate_uncorect:
                break
        if point_for_delate_uncorect:
            for point in point_for_delate_uncorect:
                self.points_for_attack.remove(point)
                return True

    def corected_point_to_attack_for_mothership(self):
        """Удаление точек слишком близких к базе и создание хороших точек"""
        bad_point = []
        for point_analiz in self.points_for_attack:
            distance = point_analiz.distance_to(self.my_mothership)
            if distance < 120:
                bad_point.append(point_analiz)
        for point in bad_point:
            self.points_for_attack.remove(point)
        good_point = []
        for point in bad_point:
            point_is_good = False
            koef = 1
            while not point_is_good:
                vec = Vector.from_points(self.my_mothership.coord, point)
                new_point = Point(self.my_mothership.coord.x + vec.x / 10 * koef,
                                  self.my_mothership.coord.y + vec.y / 10 * koef)
                koef += 1
                if new_point.distance_to(self.my_mothership) > 120:
                    good_point.append(new_point)
                    point_is_good = True
        for point in good_point:
            self.points_for_attack.append(point)

    def give_points_to_attack_to_defer(self):
        """Передача точек для атаки деферам"""
        number_defer = 0
        for defer in self.my_team_defer:
            defer.my_points_attack = self.points_for_attack
            number_defer += 1
            self.my_points_attack = self.points_for_attack

    def get_distance_to_enemy(self, obj):
        """Определение дистанции до врагов"""
        self.my_enemy = []
        self.my_enemy.extend(self.scene.drones)
        for ally in self.my_team:
            self.my_enemy.remove(ally)
        self.distance_to_my_enemy = []
        for enemy in self.my_enemy:
            if enemy.health > 0:
                self.distance_to_my_enemy.append([enemy, obj.distance_to(enemy)])
        self.distance_to_my_enemy.sort(key=lambda x: x[1])
        return self.distance_to_my_enemy

    def get_my_target_enemy(self):
        """Выбор врага для атаки"""
        for enemy, distance_to_enemy in self.distance_to_my_enemy:
            if distance_to_enemy < self.shot_distance and enemy.distance_to(enemy.my_mothership) > 150:
                self.my_target_attack = enemy
                return enemy
        for enemy, distance_to_enemy in self.distance_to_my_enemy:
            if distance_to_enemy < self.shot_distance:
                self.my_target_attack = enemy
                return enemy

    def give_victim_my_team(self):
        """Передача таргета для атаки деферам"""
        if self.distance_to(self.my_target_attack) < 100:
            return
        if len(self.my_team_defer) == 1:
            self.my_team_defer[0].my_target_attack = self.my_target_attack
        else:
            for ally in self.my_team_defer:
                ally.my_target_attack = self.my_target_attack

    def selecting_action_defer(self):
        """Определения действия дефера"""
        if self.health == 0:
            self.to_death()
            return
        self.check_ally()
        if self.our_commander.health == 0:
            OlshannikovDron.our_commander = self
            self.role = COMANDO
            return
        if self.health < 80 and self.distance_to(self.my_mothership) > 190 and self.points_for_attack:
            self.create_point_avaid()
            if self.avaid:
                self.avaid = None
                self.move_at(self.my_mothership)
                return
            else:
                self.move_at(self.points_for_avaid)
                self.avaid = True
                return
        if self.health < 30:
            self.move_at(self.my_mothership)
        if self.hide:
            if self.near(self.my_mothership):
                return
            else:
                self.move_at(self.my_mothership)
                return
        if self.my_target_attack:
            if self.payload > 20:
                self.move_at(self.my_mothership)
                return
            self.get_my_point_attack()
            if self.shot_is_fired == 0:
                self.shot_is_fired += 1
                if self.near(self.my_point_attack):
                    self.attact_enemy()
                else:
                    self.move_at(self.my_point_attack)
            elif self.shot_is_fired > self.count_fire_for_change_position * 3:
                self.shot_is_fired = 0
            else:
                self.attact_enemy()
        elif len(self.my_team_withot_me) < 3:
            self.create_point_behind_comandor()
            if self.near(self.point_bihind_comandor):
                return
            else:
                self.move_at(self.point_bihind_comandor)
        else:
            self.selecting_action_looter()

    def get_my_point_attack(self):
        """Выбор точки атаки из списка"""
        defer_with_point_to_attack = []
        for defer in self.my_team:
            if defer.my_point_attack:
                defer_with_point_to_attack.append(defer)
        if self.my_point_attack:
            defer_with_point_to_attack.remove(self)
        self.distance_to_points_to_attack = []
        for point in self.my_points_attack:
            sum_x_and_y = int(point.x) + int(point.y)
            self.distance_to_points_to_attack.append([point, self.distance_to(point), sum_x_and_y])
        for defer in defer_with_point_to_attack:
            for point in self.distance_to_points_to_attack:
                if defer.my_point_attack_info[2] == point[2]:
                    self.distance_to_points_to_attack.remove(point)
        self.distance_to_points_to_attack.sort(key=lambda x: x[1])
        self.delete_point_near_enemy()
        if self.priority_points_near_mothership():
            return
        if self.distance_to_points_to_attack:
            self.my_point_attack_info = self.distance_to_points_to_attack[0]
            self.my_point_attack = self.distance_to_points_to_attack[0][0]
            return self.my_point_attack
        self.move_at(self.my_mothership)

    def delete_point_near_enemy(self):
        """Удаление точек слишком близко к врагам"""
        index_bad_point = []
        index = 0
        for point, distance, sum_x_and_y in self.distance_to_points_to_attack:
            distance_point_to_enemys = self.get_distance_to_enemy(point)
            if distance_point_to_enemys[0][1] < 50:
                index_bad_point.append(index)
            index += 1
        if index_bad_point:
            index_bad_point.reverse()
            for index in index_bad_point:
                self.distance_to_points_to_attack.pop(index)

    def priority_points_near_mothership(self):
        """Если есть свободная точка рядом с базой, то нужно выбрать её"""
        for point, distance, sum_x_and_y in self.distance_to_points_to_attack:
            if point.distance_to(self.my_mothership) < 200:
                self.my_point_attack = point
                self.my_point_attack_info = [point, distance, sum_x_and_y]
                return True

    def get_my_team_defer_with_me(self):
        """Создание списка команды дефером без вызывающего"""
        my_team_defer_with_me = []
        my_team_defer_with_me.extend(self.my_team_defer)
        my_team_defer_with_me.remove(self)
        return my_team_defer_with_me

    def create_point_behind_comandor(self):
        """Создание точки между командиром и базой"""
        vec = Vector.from_points(OlshannikovDron.our_commander.coord, self.my_mothership.coord)
        vec.rotate(180)
        self.point_bihind_comandor = Point(self.my_mothership.coord.x + vec.x / 3,
                                           self.my_mothership.coord.y + vec.y / 3)

    def attact_enemy(self):
        """выбор определения метода атаки по врагу"""
        self.locating_shot_gun()
        if self.my_target_attack.health > 0 and self.distance_to(self.my_target_attack) < self.shot_distance:
            if self.gun.cooldown:
                self.turn_to(self.place_shot_gun)
            else:
                if self.ally_line_shot_gun():
                    self.shot_is_fired += 1
                    ally = self.ally_line_shot_gun()
                    ally.points_for_attack = self.points_for_attack
                else:
                    self.turn_to(self.place_shot_gun)
                    self.gun.shot(self.place_shot_gun)
                    self.turn_to(self.place_shot_gun)
                    self.shot_is_fired += 1
        else:
            self.shot_is_fired = 0
            self.delete_data_dead_enemy()

    def ally_line_shot_gun(self):
        """Есть ли союзник на линии огня"""
        self.check_ally()
        vec = Vector.from_points(self.coord, self.my_target_attack.coord)
        points_on_fire = []
        koef = 1
        count_point = 30
        for _ in range(0, count_point, 1):
            point_on_fire = Point(self.coord.x + vec.x / count_point * koef,
                                  self.coord.y + vec.y / count_point * koef)
            koef += 1
            points_on_fire.append(point_on_fire)
        if len(self.my_team) == 1:
            return False
        if len(self.my_team) == 2:
            for point in points_on_fire:
                if point.distance_to(self.my_team_withot_me[0]) < 35:
                    return self.my_team_withot_me[0]
        else:
            for point in points_on_fire:
                for ally in self.my_team_withot_me:
                    if point.distance_to(ally) < 35:
                        ally.points_for_attack = self.points_for_attack
                        return ally

    def create_point_avaid(self):
        """Создание точки рядом с вызывающим"""
        point = self.get_point_from_self(self.my_target_attack, 40, 90)
        self.points_for_avaid = point

    def locating_shot_gun(self):
        """Метод определяющий место выстрела, что бы стрелять на опережение"""
        new_location_enemy = Point(self.my_target_attack.x, self.my_target_attack.y)
        if self.last_location_enemy:
            vec = Vector.from_points(self.last_location_enemy, new_location_enemy)
            koef = 0.5
            self.place_shot_gun = Point(self.my_target_attack.x + vec.x * koef,
                                        self.my_target_attack.y + vec.y * koef)
            self.last_location_enemy = new_location_enemy
        else:
            self.last_location_enemy = new_location_enemy
            self.place_shot_gun = self.last_location_enemy

    def get_point_from_self(self, target_to, distance, rotate=0):
        """Создание точки рядом с собой, относительно врага, с определенной дистанции и поворотом"""
        vec = Vector.from_points(self.coord, target_to.coord)
        koef_reduced = self.distance_to(target_to) / distance / 8
        vec.rotate(rotate)
        point = Point(self.coord.x + vec.x / koef_reduced, self.coord.y + vec.y / koef_reduced)
        while self.distance_to(point) < distance:
            point = Point(point.x + vec.x / koef_reduced, point.y + vec.y / koef_reduced)
        return point

    def delete_data_dead_enemy(self):
        """Удаление информации о мёртвом враге"""
        self.my_target_attack = None
        self.points_for_attack = None
        self.my_point_attack = None


drone_class = OlshannikovDron
