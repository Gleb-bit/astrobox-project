from random import shuffle
from astrobox.core import Drone
from astrobox.themes.default import MOTHERSHIP_HEALING_DISTANCE
from robogame_engine import GameObject
from robogame_engine.geometry import Point, Vector
from robogame_engine.theme import theme


class LepilinDron(Drone):

    """
    Базовый класс дрона. Наследуется от "Drone".
    В зависимости от контекста на поле боя выбирает состояние.
    """

    occupied_asteroids = []
    queue_occupied_asteroids = []
    my_team = []
    my_alive_teammates = []
    dead_loot = []
    dead_mothership = False
    seeker_on_space = []
    collector_on_space = []
    asteroids_with_payload = []

    def __init__(self):
        super(LepilinDron, self).__init__()
        self.style = None
        self.mode = None
        self.my_asteroid = None
        self.enemy_list = list()
        self.enemy_dead_list = list()
        self.my_team.append(self)

    def set_state(self, status):
        """
        Поменять состояние (style). Атрибут называется style, потому что state уже есть
        в родительском классе.
        self.mode отображает в базовом классе текущее состояние.
        """
        self.style = status
        self.mode = self.style

    def character_act(self):
        """характерное действие в каждом состояние"""
        self.style = self.mode.character_act()

    def seeker_act(self):
        """Стиль "seeker" """
        self.set_state(Seeker(me=self))
        self.character_act()

    def hunter_act(self):
        """Стиль "hunter" """
        self.set_state(Hunter(me=self))
        self.character_act()

    def collector_act(self):
        """Стиль "collector" """
        self.set_state(Collector(me=self))
        self.character_act()

    def destroyer_act(self):
        """Стиль "destroyer" """
        self.set_state(Destroyer(me=self))
        self.character_act()

    def protector_act(self):
        """Стиль "protector" """
        self.set_state(Protector(me=self))
        self.character_act()

    def on_hearbeat(self):
        """пульс игры"""

        if self.health < 40 or self.payload > 50:
            self.move_at(self.my_mothership)
        self.asteroids_with_payload = [asteroid for asteroid in self.asteroids if asteroid.payload > 0]
        self.my_alive_teammates = [team for team in self.my_team if team.is_alive]
        self.count_dead_enemyes()

    def on_born(self):
        """Рождение"""
        self.count()
        self.strategy()

    def on_stop_at_asteroid(self, asteroid):
        """Сел на астероид"""
        self.load_from(asteroid)

    def on_load_complete(self):
        """Загрузка элериума завершена"""
        self.strategy()

    def on_stop_at_mothership(self, mothership):
        """Сел на базу"""
        self.unload_to(mothership)

    def on_unload_complete(self):
        """Разгрузка завершена"""
        self.strategy()

    def on_stop_at_point(self, target):
        """
        При посадке на точку проверяет её. Если точка - объект, то загрузить элериум.
        Если собственная база - разгрузить.
        """
        if isinstance(target, GameObject) and target is not self.my_mothership:
            self.load_from(target)
        elif target is self.my_mothership:
            self.unload_to(target)

    def on_stop(self):
        """Остановка дрона"""
        self.strategy()

    def on_wake_up(self):
        self.strategy()

    def strategy(self):
        """
        Единственная функция выбора состояния дрона и, соответственно, стратегии.
        """
        if self.payload > 50 or self.health < 40: #на всякий случай
            self.move_at(self.my_mothership)
            return

        if len(self.enemy_list) > 10:
            self._four_teams_strategy()
        else:
            self._two_teams_strategy()

    def _four_teams_strategy(self):
        """
        Стратегия: 4 команды
        """
        self._list_zero_out()
        if len(self.my_alive_teammates) < 2 and self.my_mothership.payload > 1:  #protector
            self.protector_act()
            return
        if len(self.my_alive_teammates) > 4 and len(self.asteroids_with_payload) > 2:
            self.seeker_act()
            return
        if self.enemy_dead_list and len(self.collector_on_space) < len(self.my_alive_teammates) - 1 and not self.dead_loot\
                or self.enemy_dead_list and self in self.collector_on_space and not self.dead_loot:  #collector
            self.collector_act()
            return
        elif not self.seeker_on_space or len(self.seeker_on_space) < 2 \
                and len(self.my_alive_teammates) > 2: #seeker
            self.seeker_act()
            return
        elif self in self.seeker_on_space and len(self.my_alive_teammates) > 2 \
                and len(self.seeker_on_space) < 2: #seeker
            self.seeker_act()
            return
        if len(self.my_alive_teammates) < 3 and len(self.enemy_list) < 3:  #seeker
            self.seeker_act()
        elif not self.enemy_list and not self.dead_loot:  #collector
            self.collector_act()
        elif self.dead_loot:  #seeker
            self.seeker_act()
        elif len(self.enemy_list) < 3 and not self.dead_mothership:  #destroyer
            self.destroyer_act()
        elif self.enemy_list:  #hunter
            self.hunter_act()

    def _two_teams_strategy(self):
        """
        Стратегия: 2 команды
        """

        self._list_zero_out()

        if len(self.my_alive_teammates) < 2 and self.my_mothership.payload > 1:  #protector
            self.protector_act()
            return
        if not self.seeker_on_space or len(self.seeker_on_space) < 2 \
                and len(self.my_alive_teammates) > 2: #seeker
            self.seeker_act()
            return
        elif self in self.seeker_on_space and len(self.my_alive_teammates) > 2 \
                and len(self.seeker_on_space) < 2: #seeker
            self.seeker_act()
            return
        if len(self.my_alive_teammates) <= 3 and len(self.enemy_list) < 4 \
                and len(self.asteroids_with_payload) > 1:  #seeker
            print('тут')
            self.seeker_act()
        elif not self.enemy_list and not self.dead_loot:  #collector
            self.collector_act()
        elif self.dead_loot:  #seeker
            self.seeker_act()
        elif len(self.enemy_list) < 3 and not self.dead_mothership:  #destroyer
            self.destroyer_act()
        elif self.enemy_list:  #hunter
            self.hunter_act()

    def _list_zero_out(self):
        """
        Обновляет списки с Сикерами и Коллекторами
        """
        for dron in self.seeker_on_space: # если действующий Seeker убит - убрать его из списка
            if not dron.is_alive:
                self.seeker_on_space.pop(self.seeker_on_space.index(dron))

        for dron in self.collector_on_space: # если действующий Collector убит - убрать его из списка
            if not dron.is_alive:
                self.collector_on_space.pop(self.collector_on_space.index(dron))

    def count(self):
        """
        Посчитать всех вражеских дронов на карте. Эта функция используется при рождении
        для того, чтобы можно было выбрать состояние "Hunter" из базового класса.
        """

        teammates = set(self.my_team)
        all_drones = set(dron for dron in self.scene.drones)
        all_motherships = set(mothership for mothership in self.scene.motherships
                           if mothership is not self.my_mothership)
        enemy_drones = all_drones - teammates
        enemy_drones.update(all_motherships)
        self.enemy_list = list(enemy_drones)

    def count_dead_enemyes(self):
        """
        Проверяет на наличие мёртвых вражеских баз
        """
        all_motherships = [mothership for mothership in self.scene.motherships
                           if mothership is not self.my_mothership and not mothership.is_alive]
        dead_objects = [[self.distance_to(obj), obj, obj.payload] for obj in all_motherships if obj.payload > 0]
        dead_objects = sorted(dead_objects, key=lambda x: x[0])
        self.enemy_dead_list = dead_objects
        return self.enemy_dead_list


class Seeker:

    """
    Состояние "Seeker".
    Задача: собирать элериум с астероидов.
    """

    def __init__(self, me: LepilinDron):
        self.me = me
        self.me.seeker_on_space.append(self.me)

    def __str__(self):
        return 'Seeker style'

    def character_act(self):
        """
        Главное действие этого класса. Найти ближайший или ближайший не занятый астероид
        с элериумом и отправиться к нему.
        """
        if self.me.payload == 100:
            self.me.move_at(self.me.my_mothership)
            return
        if self.me.my_asteroid is None or self.me.my_asteroid.payload == 0:
            next_asteroid = self.take_different_asteroids()
        else:
            next_asteroid = self.take_nearest_asteroid()
        self.me.my_asteroid = next_asteroid
        self.me.move_at(next_asteroid)

    def take_different_asteroids(self):
        """
        Выдаёт каждому следующему дрону
        ближайший не занятый астероид.
        """
        if self.me.payload == 100:
            return self.me.my_mothership
        distance_list = self.count_asteroids()
        self.me.occupied_asteroids = [teammate.my_asteroid for teammate in self.me.my_team]
        for asteroid_pack in distance_list:
            asteroid = asteroid_pack[1]
            if asteroid in self.me.occupied_asteroids:
                continue
            else:
                return asteroid
        return distance_list[-1][1]

    def take_nearest_asteroid(self):
        """
        Выдаёт ближайший к дрону астероид
        """
        distance_list = self.count_asteroids()
        next_asteroid = distance_list[0][1]
        if len(self.me.queue_occupied_asteroids) > 1:
            next_asteroid = self.me.queue_occupied_asteroids.pop(-1)
        return next_asteroid

    def count_asteroids(self):
        """
        Считает все астероиды с элериумом на карте и сортирует их в список
        от ближайшего к самому далёкому
        """

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

    """
    Состояние "Collector". Задача: собирать элериум с мёртвых объектов.
    Наследуется от "Seeker".
    """

    def __init__(self, me: LepilinDron):
        super(Collector, self).__init__(me)
        self.me = me
        self.me.collector_on_space.append(self.me)

    def __str__(self):
        return 'Collector style'

    def character_act(self):
        """
        Главное дествие этого класса. Найти следующий мёртвый объект с элириумом и двигаться к нему.
        По прибытию загрузить элериум.
        """
        next_obj = self.take_nearest_asteroid()
        if self.me.on_stop_at_point(next_obj):
            self.me.load_from(next_obj)
            return
        return self.me.move_at(next_obj)

    def count_asteroids(self):
        """
        Считает все мёртвые объекты на карте, формирует их в список и возвращает его.
        Если таких объектов нет - возвращает базу
        """
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

    """
    Боевое состояние "Hunter". Задача: стрелять в живые вражеские объекты.
    """

    enemyes_list = None
    point_list = []
    enemy_motherships = []

    def __init__(self, me: LepilinDron):
        self.me = me

    def __str__(self):
        return 'Hunter style'

    def character_act(self):
        """
        Главная функция этого класса. Встать на точку для атаки и стрелять
        """
        if not [obj for obj in self.count_enemyes() if obj.is_alive]:
            return
        my_target = self.detect_enemy()
        if my_target and self.me.distance_to(my_target) > self.me.gun.shot_distance:
            point = self.get_place_for_attack(my_target)
            if point:
                return self.me.move_at(point)
            else:
                return
        if my_target and my_target.is_alive:
            self.shot(target=my_target)

    def get_place_for_attack(self, target):
        """
        Выбор места для атаки цели, если цель не в радиусе атаки
        """
        if isinstance(target, GameObject):
            vec = Vector.from_points(target.coord, self.me.coord)
        elif isinstance(target, Point):
            vec = Vector.from_points(target, self.me.coord)
        else:
            raise Exception("target must be GameObject or Point!".format(target, ))
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
        """
        Расчет места рядом с point с отклонением angle от цели target
        """
        vec = Vector(point.x - target.x, point.y - target.y)
        vec.rotate(angle)
        return Point(target.x + vec.x, target.y + vec.y)

    def valide_place(self, point: Point):
        """
        Подходит ли это место для атаки. Слишком рядом не должно быть партнеров
        и на линии огня тоже не должно быть партнеров.
        """
        is_valide = 0 < point.x < theme.FIELD_WIDTH and 0 < point.y < theme.FIELD_HEIGHT
        for partner in self.me.my_team:
            if not partner.is_alive or partner is self:
                continue
        return is_valide

    def shot(self, target):
        """
        Проверить позицию, повернуться к вражескому объекту и выстрелить.
        """
        for dron in self.me.my_team:
            if not dron.is_alive or dron is self.me:
                continue
            if dron.near(self.me) and self.me is not dron:
                next_point = self.get_place_for_attack(target)
                self.me.move_at(next_point)
                return
        if not self.valide_place(self.me.coord):
            next_point = self.get_place_for_attack(target)
            self.me.move_at(next_point)
            return
        if self.me.distance_to(target) > self.me.gun.shot_distance\
                or self.me.distance_to(self.me.my_mothership) < 130:
            next_point = self.get_place_for_attack(target)
            self.me.move_at(next_point)
            return
        self.me.turn_to(target)
        self.me.gun.shot(target)

    def detect_enemy(self):
        """
        Выдаёт ближайшего живого вражеского дрона
        """
        target_list = []
        for target in self.count_enemyes():
            if target.is_alive:
                target_list.append((self.me.distance_to(target), target))
        target_distance_list = sorted(target_list, key=lambda x: x[0])
        next_target = target_distance_list[0][1]
        return next_target

    def count_enemyes(self):
        """
        Посчитать всех вражеских дронов на карте.
        Посчитать все вражеские базы на карте.
        Добавить всё это в единый список, в базовый класс.
        """
        teammates = set(self.me.my_team)
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

    """
    Состояние "Destroyer". Задача: стрелять в базу врага до её уничтожения.
    Наследуется от "Hunter".
    """

    def __str__(self):
        return 'Destroyer style'

    __repr__ = __str__

    def character_act(self):
        """
        Главная функция этого класса.
        Ищет живую базу и стреляет в неё. Если база мертва - возвращает атрибут
        базового класса "Мёртвая база" в значение True
        """
        for target in self.enemy_motherships:
            if target.is_alive:
                return self.shot(target)
            else:
                self.me.dead_mothership = True


class Protector(Hunter):

    """
    Состояние "Защитник". Задача: стоять возле базы на расстоянии действия эффекта
    лечения базы и отстреливаться. Наследуется от "Hunter".
    """

    def __str__(self):
        return 'Protector style'

    def character_act(self):
        """
        Главная функция этого класса. Найти ближайшего противника, встать напротив него и стрелять.
        """
        my_target = self.detect_enemy()
        new_position = self.check_base_near(my_target)
        if self.me.coord.x == new_position.x and self.me.coord.y == new_position.y:
            self.shot(my_target)
            return
        else:
            self.me.move_at(new_position)
            return

    def check_base_near(self, target):
        """
        Найти новую точку рядом с базой.
        """
        base = self.me.my_mothership
        new_vec = Vector.from_points(base.coord, target.coord)
        other_vec = new_vec.module
        _koef = 1 / other_vec
        norm_vec = Vector(new_vec.x * _koef, new_vec.y * _koef)
        vec_position = Vector(norm_vec.x * MOTHERSHIP_HEALING_DISTANCE * 0.9,
                              norm_vec.y * MOTHERSHIP_HEALING_DISTANCE * 0.9)
        new_position = Point(base.coord.x + vec_position.x, base.coord.y + vec_position.y)
        return new_position


drone_class = LepilinDron
