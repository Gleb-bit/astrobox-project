from random import choice, randint, shuffle
from astrobox.core import Drone
from robogame_engine.geometry import Vector, Point
from robogame_engine import scene
from robogame_engine.theme import theme

# python -m battle -p hangar_2019/khizhov_d_s.py hangar_2019/kharitonov.py -c -s 2 -od "result_battle"
# python -m battle -p hangar_2019/khizhov_d_s.py hangar_2019/ishmukhamedov.py -c -s 2 -od "result_battle"
# python -m battle -p hangar_2019/khizhov_d_s.py hangar_2019/surkova_e_n.py -c -s 2 -od "result_battle"
# python -m battle -p hangar_2019/khizhov_d_s.py hangar_2019/vinogradov.py -c -s 2 -od "result_battle"
# python -m battle -p hangar_2019/khizhov_d_s.py hangar_2019/khizhov.py -c -s 2 -od "result_battle"


class KhizhovDrone(Drone):
    map_field = scene.theme.FIELD_WIDTH, scene.theme.FIELD_HEIGHT
    center_map = Point(x=round(int(map_field[0] // 2)), y=round(int(map_field[1] // 2)))
    my_team = []
    asteroids_in_work = []
    path_is_fully_loaded = 0
    path_half_loaded = 0
    path_is_empty = 0
    attack_range = 0
    task = ()
    last_task = []
    limit_health = 0.5
    optimal_start_coord = []
    step = 0
    first_coord = None
    optimal_coord = None
    enemy_target = None
    all_object = set()
    near_aster = []
    target_move_to = None
    shot_count = 0

    def next_action(self):
        """Выполняем таск с аргумнтами или без, инфа для дебага"""
        if len(self.last_task) > 4:
            self.last_task.clear()
        i = 0
        while not self.task:
            self.task_manage()
            i += 1
            if i > 1:
                return
        if self._selected:
            print(f'{self.id}    задача    {self.task}')
        payload = self.task[1].payload if hasattr(self.task[1], 'payload') else 'None'
        distance = self.distance_to(self.task[1]) if self.task[1] else 'None'
        self.last_task.append(f'Я - {self}, {self._sleep_countdown} ,Задача - {self.task[0].__name__},'
                              f' к {self.task[1]}, тип аргумента {self.task[1].__class__.__name__}'
                              f' свободного места {self.free_space},  в таргете  {payload} '
                              f'элериума, до таргета {distance} м ------')
        if not self.task:
            self.task = (self.go_home, False)
        elif self.task[1]:
            args = self.task[1]
            self.task[0](args)
            self.task = ()
        else:
            self.task[0]()
            self.task = ()

    def task_manage(self):
        """Получаем таск если его не было на момент окончания прошлого действия"""
        self.update_all_data()
        other_enemy_target = [drone for drone in self.scene.drones if self.team != drone.team and drone.is_alive]
        if self.enemy_target and self.have_gun:
            self.task = (self.shoot, self.enemy_target)
        elif self.asteroids_in_work and self._sleep_countdown > 9:
            self.task = (self.collect, False)
        elif not self.asteroids_in_work and other_enemy_target and self.have_gun:
            self.task = (self.shoot, other_enemy_target[0])
        elif self.get_enemy_bases_alive() and self.have_gun:
            self.task = (self.shoot, self.get_enemy_bases_alive()[0])
        else:
            self.task = (self.go_home, False)

    def move_to_optimal_position(self):
        coord = self.first_coord if self.my_team.index(self) == 0 else self.optimal_coord[self.my_team.index(self) - 1]
        self.task = (self.move_to, coord)
        self.next_action()

    def on_born(self):
        self.my_team.append(self)
        self.update_all_data()
        max_id = len(self.scene.drones) // self.scene.teams_count
        near_aster = sorted(self.asteroids, key=lambda asteroid: self.distance_to(asteroid))
        near_aster = near_aster[:7]
        self.vector = Vector.from_points(self.coord, self.center_map, module=1)
        vec = Vector.from_direction(self.direction, 250)
        self.first_coord = Point(x=int(self.x + vec.x), y=int(self.y + vec.y))
        coord_1 = [[-100, -100], [100, 100], [-250, -250], [250, 250], [-400, -400], [400, 400]]
        coord_2 = [[100, -100], [-100, 100], [250, -250], [-250, 250], [400, -400], [-400, 400]]
        if 1 < self.team_number < 4:
            self.optimal_coord = [Point(x=int(self.first_coord.x + coord[0]), y=int(self.first_coord.y + coord[1]))
                                  for coord in coord_1]
        else:
            self.optimal_coord = [Point(x=int(self.first_coord.x + coord[0]), y=int(self.first_coord.y + coord[1]))
                                  for coord in coord_2]
        if self.have_gun:
            self.attack_range = self.gun.shot_distance
            self.move_to_optimal_position()
            return
        elif len(near_aster) >= max_id:
            self.task = (self.move_to, near_aster[self.my_team.index(self)])
            return self.next_action()
        else:
            self.task = (self.move_to, choice(near_aster))
            self.next_action()

    def collect_stat(self, target):
        length = self.distance_to(target)
        if self.is_empty:
            self.path_is_empty += length
        elif self.free_space > 0:
            self.path_half_loaded += length
        elif self.is_full:
            self.path_is_fully_loaded += length

    def game_over(self):
        print('Всего было пройдено полностью загруженным :',
              round(sum([getattr(member, 'path_is_fully_loaded') for member in self.my_team])))
        print('Всего было пройдено пустым :',
              round(sum([getattr(member, 'path_is_empty') for member in self.my_team])))
        print('Всего было пройдено частично загруженным :',
              round(sum([getattr(member, 'path_half_loaded') for member in self.my_team])))

    def move_to(self, target):
        self.shot_count = 0
        self.target_move_to = target
        if isinstance(target, Point):
            if self.distance_to(target) > 450 and abs(self.distance_to(target) - self.distance_to(
                    self.my_mothership)) > 11:
                target = choice(self.near_aster)
            if round(target.x) == round(self.x) and round(target.y) == round(self.y):
                target = Point(x=round(int(self.x + randint(-10, 10))),
                               y=round(int(self.y + randint(-10, 10))))
        if not isinstance(target, Point):
            if round(target.x) == round(self.x) and round(target.y) == round(self.y):
                if target in self.near_aster:
                    self.near_aster.remove(target)
                target = choice(self.near_aster)
        vector_target = Vector.from_points(self.coord, target, module=1) if isinstance(target, Point) else \
            Vector.from_points(self.coord, target.coord, module=1)
        self.vector = vector_target
        target_coord = target.coord if hasattr(target, 'coord') else target
        self.collect_stat(target_coord)
        super().move_at(target_coord)

    def change_locate(self, target):
        """Нужен был отдельный таск для дебага"""
        self.task = (self.move_to, target)
        self.next_action()

    def go_home(self):
        self.update_all_data()
        if not self.asteroids_in_work:
            random_point = Point(x=round(int(self.my_mothership.x + randint(-10, 10))),
                                 y=round(int(self.my_mothership.y + randint(-10, 10))))
            if self.coord != random_point:
                self.task = (self.move_to, random_point)
                return self.next_action()
        self.task = (self.move_to, self.my_mothership)
        self.next_action()

    def update_all_data(self):
        dead_drone = [drone for drone in self.scene.drones if not drone.is_alive]
        self.all_object.update(self.asteroids, dead_drone)
        self.near_aster = sorted(self.all_object, key=lambda asteroid: self.distance_to(asteroid))
        self.near_aster = self.near_aster[:3]
        self.asteroids_in_work = [asteroid for asteroid in self.asteroids if asteroid.payload > 0]
        self.asteroids_in_work.extend(self.get_dead_drone_load())
        if self.have_gun:
            self.asteroids_in_work.extend(self.get_enemy_load_bases())

    def get_enemy_alive_drone(self):
        enemies = [(drone, self.distance_to(drone)) for drone in self.scene.drones if
                   self.team != drone.team and drone.is_alive]
        enemies.sort(key=lambda x: x[1])
        return enemies

    def get_dead_drone_load(self):
        dead_drone = [drone for drone in self.scene.drones if not drone.is_alive and drone.payload > 0]
        return dead_drone

    def get_enemy_load_bases(self):
        return [base for base in self.scene.motherships if
                base.team is not self.team and base.is_alive and base.payload > 0]

    def get_enemy_bases_alive(self):
        return [base for base in self.scene.motherships if base.team is not self.team and base.is_alive]

    def sorted_by_near(self):
        self.update_all_data()
        return sorted(self.asteroids_in_work, key=lambda asteroid: self.distance_to(asteroid))

    def sorted_by_rich(self):
        self.update_all_data()
        return sorted(self.asteroids_in_work, key=lambda asteroid: asteroid.payload, reverse=True)

    def sorted_by_rich_near(self):
        self.update_all_data()
        asteroid_rich = sorted(self.asteroids_in_work, key=lambda asteroid: asteroid.payload, reverse=True)
        aster_rich_near = [aster for aster in asteroid_rich if self.distance_to(aster) <= 400]
        return sorted(aster_rich_near, key=lambda asteroid: asteroid.payload, reverse=True)

    def get_asteroid(self, sorted_func, random=False):
        self.update_all_data()
        rich = [aster for aster in self.asteroids_in_work if aster.payload >= 130 and self.distance_to(aster) <= 500]
        sorted_asteroid = sorted_func()
        if random:
            if len(sorted_asteroid) >= 3:
                sorted_asteroid = sorted_asteroid[:3]
                return choice(sorted_asteroid)
        if rich:
            return rich[0]
        for asteroid in sorted_asteroid:
            return asteroid

    @property
    def asteroid_assigned_to_you(self):
        return self.get_asteroid(sorted_func=self.sorted_by_rich_near) if self.step < 2 else \
            self.get_asteroid(sorted_func=self.sorted_by_near)

    def collect(self):
        """Выбираем откуда будем собирать"""
        self.update_all_data()
        for asteroid in self.asteroids_in_work:
            if self.distance_to(asteroid) < 20:
                self.task = (self.load_from, asteroid)
                return self.next_action()
        if self.is_full:
            self.task = (self.go_home, False)
            return self.next_action()
        self.target = self.get_asteroid(sorted_func=self.sorted_by_near, random=True)
        if self.a_suitable_target(check=True):
            return self.next_action()
        self.target = self.get_asteroid(sorted_func=self.sorted_by_rich_near)
        if self.a_suitable_target(check=True):
            return self.next_action()
        self.target = self.get_asteroid(sorted_func=self.sorted_by_near, random=True)
        if self.a_suitable_target(check=False):
            return self.next_action()
        self.task = (self.go_home, False)
        self.next_action()

    def a_suitable_target(self, check=False):
        """Последняя проверка таргета с которого будем собирать"""
        if self.target and self.free_space < 15 and self.distance_to(self.target) > 350:
            self.task = (self.go_home, False)
            return True
        if self.target and check:
            if self.check_who_already_go(self.target):
                self.task = (self.move_to, self.target)
                return True
            return False
        if self.target:
            self.task = (self.move_to, self.target)
            return True
        return False

    def check_who_already_go(self, target):
        """Проверка чтобы к астероиду не ехали лишние дроны"""
        who_in_target = [drone for drone in self.teammates if drone.target == target]
        if len(who_in_target) == 1:
            return True if who_in_target[0].target.payload > who_in_target[0].free_space else False
        elif len(who_in_target) > 1:
            return False
        return True

    def pursue(self, target_coord):
        """Двигаемся немного вперед к цели"""
        vec1 = Vector.from_points(self.coord, target_coord, module=1)
        self.vector = vec1
        vec2 = Vector.from_direction(round(self.direction), 30)
        new_coord = Point(round(int(self.x + vec2.x)), y=round(int(self.y + vec2.y)))
        self.task = (self.move_to, new_coord)
        self.next_action()

    def shoot(self, target):
        vec = Vector.from_points(self.coord, target.coord, module=self.attack_range)
        for base in self.scene.motherships:
            if target is base and self.distance_to(base) < 250:
                self.task = (self.change_locate, self.center_map)
                return self.next_action()
            if hasattr(target, 'distance_to') and target.distance_to(base) < 300 and self.distance_to(base) < 300:
                self.task = (self.change_locate, self.center_map)
                return self.next_action()
            if self.distance_to(base) < 150:
                self.task = (self.pursue, target.coord)
                return self.next_action()
        if not self.check_shoot(target, vec):
            return self.next_action()
        if self.distance_to(target.coord) > self.attack_range:
            self.task = (self.pursue, target.coord)
            return self.next_action()
        if self.gun_cooldown:
            self.task = (self.turn_to, target)
            return self.next_action()
        if target.is_alive:
            self.vector = vec
            self.shot_count += 1
            self.gun.shot(target)
        else:
            self.task = (self.change_locate, self.center_map)
        self.next_action()

    def check_shoot(self, target_coord, vec):
        self.update_all_data()
        the_bullet_will_reach = Point(x=int(self.coord.x + vec.x), y=int(self.coord.y + vec.y))
        for teammate in self.teammates:
            """Генерируем новые координаты где нет союзников"""
            coord_1 = [[60, -60], [-60, 60], [20, -100], [-20, 100], [50, 100], [-50, -100]]
            coord_2 = [[70, -70], [-70, 50], [-70, 100], [50, 100], [-50, 100], [50, -100]]
            new_coord = [Point(x=round(int(teammate.coord.x + coord[0])), y=round(int(teammate.coord.y + coord[1])))
                         for coord in coord_1]
            new_coord.extend([Point(x=round(int(self.coord.x + coord[0])), y=round(int(self.coord.y + coord[1])))
                              for coord in coord_2])
            if self.distance_to(target_coord) <= self.distance_to(the_bullet_will_reach):
                """Расчитываем траекторию пули, и проверяем что на ней нет союзников"""
                step_x = (abs(target_coord.x) - abs(self.coord.x)) / 10
                step_y = (abs(target_coord.y) - abs(self.coord.y)) / 10
                coord_trajectory_bullet = [(self.coord.x + step_x * i, self.coord.y + step_y * i) for i in range(1, 11)]
                check_traject = any([abs(round(teammate.coord.x - x)) <= 50 and abs(round(teammate.coord.y - y)) <= 50
                                     and self.distance_to(teammate) >= 50 for x, y in coord_trajectory_bullet])
                near_check = (self.distance_to(teammate) - self.radius * 2) < - 25 and not teammate.is_moving
                """Смена локации, если стоим близко к союзнику или попадем в союзника пулей"""
                if check_traject or near_check and not self.shot_count:
                    shuffle(new_coord)
                    for coord in new_coord:
                        if all([mate.distance_to(coord) - self.radius * 2 > - 25 for mate in self.teammates]):
                            if 0 < coord.x < self.map_field[0] and 0 < coord.y < self.map_field[1]:
                                self.task = (self.change_locate, coord)
                                return False
                    self.task = (self.change_locate, choice(self.near_aster))
                    return False
        return True

    def check_enemies_in_sight(self):
        """Определяем в кого стрелять, не бьем тех кто стоит в зоне отхила"""
        if self.have_gun:
            living_enemies = self.get_enemy_alive_drone()
            if living_enemies:
                for enemy, dist in living_enemies:
                    if enemy.my_mothership.is_alive:
                        enemy_coord = enemy.distance_to(enemy.my_mothership)
                        if enemy_coord > 200:
                            return enemy
                    else:
                        return enemy

    def on_stop_at_target(self, target):
        self.update_all_data()
        for asteroid in self.all_object:
            if asteroid.near(target):
                if asteroid.payload > 0 and self.free_space > 0:
                    self.task = (self.load_from, asteroid)
                    return self.next_action()
                if self.is_full:
                    self.task = (self.go_home, False)
                    return self.next_action()
                continue
        for ship in self.scene.motherships:
            if ship.near(target):
                if ship == self.my_mothership:
                    self.step += 1
                    if self.payload > 0:
                        self.task = (self.unload_to, ship)
                    return self.next_action()
                else:
                    if ship.payload and self.free_space > 0:
                        self.task = (self.load_from, ship)
                        return self.next_action()
                    elif self.free_space > 0 and self.asteroids_in_work:
                        self.task = (self.collect, False)
                        return self.next_action()
                    else:
                        self.task = (self.move_to, self.center_map)
                        return self.next_action()
        self.on_stop_at_point(target)

    def on_stop_at_point(self, target):
        self.next_action()

    def on_stop(self):
        if self.meter_2 <= self.limit_health:
            self.task = (self.go_home, False)
        self.next_action()

    def on_load_complete(self):
        if self.free_space > 0 and self.asteroids_in_work:
            self.task = (self.collect, False)
        elif self.is_full:
            self.task = (self.go_home, False)
        else:
            self.task = (self.move_to, choice(self.near_aster))
        return self.next_action()

    def on_unload_complete(self):
        self.next_action()

    def on_hearbeat(self):
        # if self.get_enemy_bases_alive():
        #     self.scene._prev_endgame_state['countdown'] = 260
        if self._sleep_countdown < 10:
            self.task = ()
            return self.next_action()
        if self.meter_2 <= self.limit_health:
            self.task = (self.go_home, False)
            return self.next_action()
        self.enemy_target = self.check_enemies_in_sight()
        if self.have_gun and self.enemy_target:
            """Атака"""
            if not isinstance(self.target_move_to, Point):
                if not any([self.distance_to(base) < 200 for base in self.scene.motherships]) \
                        and self.meter_2 == 1.0 and not self.is_full:
                    self.task = (self.shoot, self.enemy_target)
                    return self.next_action()
            """Отходим чтобы выманить противника с базы"""
            if not self.asteroids_in_work and not self.enemy_target and \
                    any([enemy for enemy, dist in self.get_enemy_alive_drone() if enemy.gun_cooldown]):
                self.task = (self.go_home, False)
                self.next_action()
        """Не едем к таргету если в нем закончился элериум"""
        if not isinstance(self.target_move_to, Point) and not self.enemy_target:
            if not self.target_move_to.payload and self.target_move_to is not self.my_mothership:
                return self.next_action()
        """Смена позиции по вертикали, в точку где никого нет."""
        if self.enemy_target or not self.asteroids_in_work:
            if any([mate for mate in self.teammates
                    if 300 < mate.x < self.map_field[0] - 300 and mate.distance_to(
                    self.target_move_to) - self.radius * 2 < - 25 and not mate.is_moving]):
                range_x = round(self.target_move_to.x - 40), round(self.target_move_to.x + 41)
                new_coord = self.generator_coord(range_x)
                shuffle(new_coord)
                for coord in new_coord:
                    if coord and 50 < coord.x < self.map_field[0] - 50 and 50 < coord.y < self.map_field[1] - 50:
                        self.task = (self.move_to, coord)
                        return self.next_action()

    def generator_coord(self, range_x):
        """Генерируем координаты по вертикали"""
        temp = []
        for x in range(range_x[0], range_x[1], 40):
            for y in range(self.map_field[1] - 50, 50, -50):
                point = Point(x=round(int(x)), y=round(int(y)))
                if all([500 > mate.distance_to(point) > 100 for mate in self.teammates]):
                    temp.append(point)
        return temp

    def on_wake_up(self):
        print(f'{self.state}, последние 3 задачи:')
        for task in self.last_task:
            print(task)
        self.task = (self.move_to, choice(self.near_aster))
        self.next_action()


drone_class = KhizhovDrone
