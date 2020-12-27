from astrobox.core import Drone
from astrobox.guns import PlasmaGun
from robogame_engine.geometry import Point, Vector
from robogame_engine.scene import theme

MIN_ENEMIES = 2


class DemintsevDrone(Drone):
    COLLECTOR = 'collector'
    FORWARD = 'forward'
    GUARD = 'guard'
    collect_elerium = True
    enemies_drones_alive = True
    elerium_restriction = 0

    my_team = []
    mothership_guards = []
    positions_for_attack = []

    guards_positions_enable = False
    guards_positions = {
        1: None,
        2: None,
    }

    def __init__(self):
        self.role = DemintsevDrone.COLLECTOR
        self.attack_target = [None, None]
        self.X_CENTRE = theme.FIELD_WIDTH // 2
        self.Y_CENTRE = theme.FIELD_HEIGHT // 2
        super().__init__()

    # Общие методы
    def get_elerium_restriction(self):
        for asteroid in self.asteroids:
            DemintsevDrone.elerium_restriction += asteroid.payload
        DemintsevDrone.elerium_restriction = DemintsevDrone.elerium_restriction // 3

    def change_strategy(self):
        if DemintsevDrone.enemies_drones_alive:
            if not len([1 for drone in DemintsevDrone.my_team if drone.is_alive]) > 2:
                DemintsevDrone.collect_elerium = False

    def on_heartbeat(self):
        self.change_strategy()
        if self.health < 40:
            self.move(self.my_mothership)
            if self.role == DemintsevDrone.FORWARD or self.role == DemintsevDrone.GUARD:
                self.attack_target[1] = 1
        super().on_heartbeat()

    def turn(self, _object):
        if isinstance(_object, Point):
            self.vector = Vector.from_points(point1=self.coord, point2=_object)
        else:
            self.vector = Vector.from_points(point1=self.coord, point2=_object.coord)

    def move(self, _object):
        self.turn(_object)
        super().move_at(_object)

    # Методы для сбора реусрсов
    def select_nearest_asteroid(self):
        """
            Выбирает ближайший к дрону астеройд с ресурсами. Если все ресурсы собраны - летит на базу.

            :return: возвращает подходящий астеройд или базу.
        """
        min_distance = 0.0
        _target = None

        if self.my_mothership.payload < DemintsevDrone.elerium_restriction:
            asteroids_with_elerium = set(aster for aster in self.asteroids if aster.payload)
            asteroids_as_targets = set(drone.target for drone in self.my_team)
            free_asteroids = asteroids_with_elerium - asteroids_as_targets
            if free_asteroids:
                for asteroid in free_asteroids:
                    distance_to_asteroid = self.distance_to(asteroid)
                    if not min_distance:
                        min_distance = distance_to_asteroid
                        _target = asteroid
                    elif min_distance > distance_to_asteroid:
                        min_distance = distance_to_asteroid
                        _target = asteroid
            if _target is None:
                if not any(asteroids_with_elerium):
                    DemintsevDrone.collect_elerium = False
                return self.my_mothership
            else:
                return _target
        else:
            DemintsevDrone.collect_elerium = False
            return self.my_mothership

    def check_asteroids(self):
        """
            Проверяет есть ли ресурсы на астеройдах, которые выбраны в качестве целей для своих дронов.
            Если ресурсов нет - вызывает метод select_nearest_asteroid()
        """
        asteroids_in_work = set(drone.target for drone in self.my_team)
        for aster in asteroids_in_work:
            for drone in self.my_team:
                if aster == drone.target and aster.payload == 0:
                    drone.select_nearest_asteroid()

    def on_stop_at_asteroid(self, asteroid):
        self.load_from(asteroid)

    def on_load_complete(self):
        if self.role == DemintsevDrone.COLLECTOR:
            if self.is_full:
                self.move(self.my_mothership)
            else:
                self.move(self.select_nearest_asteroid())

    def on_stop_at_mothership(self, mothership):
        if DemintsevDrone.collect_elerium:
            self.check_asteroids()
        self.unload_to(mothership)

    def on_unload_complete(self):
        self.select_nearest_asteroid()

    # Методы для боя
    def get_guards_positions(self):
        """
            Создает позиции для дронов-охранников базы
        """
        DemintsevDrone.guards_positions_enable = True
        x = self.my_mothership.coord.x
        y = self.my_mothership.coord.y

        if len([1 for drone in DemintsevDrone.my_team if drone.is_alive]) == 1:
            if x > self.X_CENTRE and y > self.Y_CENTRE:
                new_x = x - 115.0
                new_y = y - 115.0
                DemintsevDrone.guards_positions[1] = Point(new_x, new_y)
            elif x > self.X_CENTRE and y < self.Y_CENTRE:
                new_x = x - 115.0
                new_y = y + 115.0
                DemintsevDrone.guards_positions[1] = Point(new_x, new_y)
            elif x < self.X_CENTRE and y > self.Y_CENTRE:
                new_x = x + 115.0
                new_y = y - 115.0
                DemintsevDrone.guards_positions[1] = Point(new_x, new_y)
            elif x < self.X_CENTRE and y < self.Y_CENTRE:
                new_x = x + 115.0
                new_y = y + 115.0
                DemintsevDrone.guards_positions[1] = Point(new_x, new_y)
        else:
            if x > self.X_CENTRE and y > self.Y_CENTRE:
                new_x = x - 130.0
                new_y = y - 30
                DemintsevDrone.guards_positions[1] = Point(new_x, new_y)
                new_y = y - 130
                DemintsevDrone.guards_positions[2] = Point(x, new_y)
            elif x > self.X_CENTRE and y < self.Y_CENTRE:
                new_x = x - 130.0
                new_y = y + 30
                DemintsevDrone.guards_positions[1] = Point(new_x, new_y)
                new_y = y + 130
                DemintsevDrone.guards_positions[2] = Point(x, new_y)
            elif x < self.X_CENTRE and y > self.Y_CENTRE:
                new_x = x + 130.0
                new_y = y - 30
                DemintsevDrone.guards_positions[1] = Point(new_x, new_y)
                new_y = y - 130
                DemintsevDrone.guards_positions[2] = Point(x, new_y)
            elif x < self.X_CENTRE and y < self.Y_CENTRE:
                new_x = x + 130.0
                new_y = y + 30
                DemintsevDrone.guards_positions[1] = Point(new_x, new_y)
                new_y = y + 130
                DemintsevDrone.guards_positions[2] = Point(x, new_y)

    def change_role(self, role):
        self.role = role

    def get_gun(self):
        self._gun = PlasmaGun(self)

    def shoot(self, enemy):
        if not self.near(self.my_mothership):
            self.turn(enemy)
            self.gun.shot(enemy)

    def count_alive_enemy_drones(self, base=False):
        alive_drones = 0
        for drone in self.scene.drones:
            if drone not in DemintsevDrone.my_team and drone.health > 0:
                alive_drones += 1
        if base:
            for mothership in self.scene.motherships:
                if mothership != self.my_mothership and mothership.health:
                    alive_drones += 1
        if not alive_drones:
            DemintsevDrone.enemies_drones_alive = False
        return alive_drones

    def get_coordinate_for_step(self):
        """
            Создает точки для трех дронов, на которые они перемещаются, когда self.role == FORWARD
        """
        x = self.coord.x
        y = self.coord.y

        if x <= (theme.FIELD_WIDTH - 580):
            new_x1 = x + 40
            new_x2 = new_x1 + 120
            new_x3 = new_x2 + 120
        else:
            new_x1 = theme.FIELD_WIDTH - 570
            new_x2 = theme.FIELD_WIDTH - 640
            new_x3 = theme.FIELD_WIDTH - 710

        if y <= (theme.FIELD_HEIGHT - 580):
            new_y1 = y + 190
            new_y2 = new_y1 + 50
            new_y3 = new_y2 + 50
        else:
            new_y1 = theme.FIELD_HEIGHT - 570
            new_y2 = new_y1 - 640
            new_y3 = new_y2 - 710

        point_1 = Point(new_x1, new_y1)
        point_2 = Point(new_x2, new_y2)
        point_3 = Point(new_x3, new_y3)
        DemintsevDrone.positions_for_attack = [point_1, point_2, point_3]

    def get_position_for_attack(self):
        if not any(DemintsevDrone.positions_for_attack):
            self.get_coordinate_for_step()
        position = DemintsevDrone.positions_for_attack.pop(0)
        self.attack_target = [position, 1]
        self.target = position

    def get_nearest_victim(self):
        """
            Создает список вражеских дронов/баз до которых долетит выстрел.
            :return: Возвращает ближайший дрон/базу или False.
        """
        _enemies = [(drone, self.distance_to(drone)) for drone in self.scene.drones if
                    drone not in DemintsevDrone.my_team
                    and drone.health > 0
                    and self.distance_to(drone) < 580.1
                    ]
        _enemies.sort(key=lambda x: x[1])
        if _enemies:
            return _enemies.pop(0)
        else:
            _enemies_base = [(base, self.distance_to(base)) for base in self.scene.motherships if
                             base != self.my_mothership
                             and base.health > 0
                             and self.distance_to(base) < 580.1
                             ]
            if _enemies_base:
                return _enemies_base.pop(0)
            else:
                return False

    def get_protection_mothership(self):
        """
            Делает дрона охранником базы.
        """
        for drone in DemintsevDrone.my_team:
            if drone.is_alive and self.role != DemintsevDrone.GUARD:
                DemintsevDrone.mothership_guards.append(self)
                self.change_role(DemintsevDrone.GUARD)
                guard_number = None
                for index, guard in enumerate(DemintsevDrone.mothership_guards):
                    if self == guard:
                        guard_number = index + 1
                position = DemintsevDrone.guards_positions[guard_number]
                self.attack_target = [position, 1]
                self.target = position
                return

    def protect_position(self):
        target = self.get_nearest_victim()
        if target:
            self.shoot(target[0])
        else:
            if self.role == DemintsevDrone.FORWARD:
                self.get_position_for_attack()

    def attack(self):
        coordinate, movement = self.attack_target
        if movement:
            self.move(coordinate)
            self.target = coordinate
            self.attack_target[1] = 0
        else:
            self.target = None
            self.protect_position()

    # Игровой процесс
    def on_born(self):
        self.get_gun()
        if not DemintsevDrone.elerium_restriction:
            self.get_elerium_restriction()
        self.target = self.get_action()
        self.move(self.target)
        self.my_team.append(self)

    def on_wake_up(self):
        if self.is_full:
            self.move(self.my_mothership)
        else:
            self.target = self.get_action()
            if self.target:
                self.move(self.target)

    def get_action(self):
        if DemintsevDrone.collect_elerium:
            return self.select_nearest_asteroid()

        elif not self.count_alive_enemy_drones(base=True):
            self.change_role(DemintsevDrone.COLLECTOR)
            DemintsevDrone.collect_elerium = True
            DemintsevDrone.elerium_restriction = 10000

        else:
            # Если количество своих дорнов больше двух
            if not DemintsevDrone.guards_positions_enable:
                self.get_guards_positions()
            if len([1 for drone in DemintsevDrone.my_team if drone.is_alive]) > 2:
                if len(DemintsevDrone.mothership_guards) < 2:
                    self.get_protection_mothership()

                if self.role == DemintsevDrone.GUARD:
                    self.attack()
                elif self.role == DemintsevDrone.COLLECTOR:
                    self.change_role(DemintsevDrone.FORWARD)
                    self.get_position_for_attack()

                if self.count_alive_enemy_drones() < MIN_ENEMIES:
                    if self.role == DemintsevDrone.FORWARD:
                        self.attack()
            else:
                if not DemintsevDrone.guards_positions_enable:
                    self.get_guards_positions()
                if len(DemintsevDrone.mothership_guards) < 2:
                    self.get_protection_mothership()
                self.attack()


drone_class = DemintsevDrone
