import math
from math import cos, sin


from astrobox.core import Drone
import logging
from robogame_engine.geometry import Point
from robogame_engine.theme import theme

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG, filename="xvatov.log", filemode="w")



class Brain:


    def __init__(self):
        self.army = []
        self.army_quantity = 0
        self.workers = []
        self.asteroids_not_empty = []
        self.all_team = []
        self.where_all_team = []

        self.position_defense = []
        self.position_center = []
        self.win_position = []

        self.save_distance = 50

        self.my_money = 0
        self.all_money = 0
        self.start_game_flag = None
        self.start_game_flag_2 = False

        self.army_live={}
    def start_game(self):
        if self.start_game_flag is None:
            self.start_game_flag = True
            for aster in self.asteroids_not_empty:
                self.all_money += int(aster[2])
    def update_army_quantity(self):
        self.army_live={}
        self.army_quantity = 0
        for i, partner in enumerate(self.army):
            if partner.is_alive:
                self.army_live[partner.number_drone] = self.army_quantity
                self.army_quantity += 1
        if self.army_quantity == 5:
            self.start_game_flag_2 = True

    def big_losses(self, person):
        if self.start_game_flag_2:
            if self.army_quantity<=3:
                person.fight = True


    def add_person(self, person):
        self.army_quantity += 1
        self.where_all_team.append(person.my_mothership)
        if not (self.army_quantity <= 5):
            self.army.append(person)
            person.fight = True
        else:
            self.army.append(person)
            person.fight = False

    def updatet_asteroids(self, asteroids):
        ''' Заполняем матрицу данных self.ASTEROIDS =
                 [номер self.asteroids, расстояние от базы, кол-во эл]'''
        self.asteroids_not_empty = []
        for i, asteroid in enumerate(asteroids):
            if asteroid.payload != 0:
                xi, yi = asteroid.coord.x, asteroid.coord.y
                li = (xi ** 2 + yi ** 2) ** (0.5)
                if asteroid.payload != 0:
                    self.asteroids_not_empty.append([i, li, asteroid.payload])
        self.start_game()
        if self.asteroids_not_empty:
            self.asteroids_not_empty.sort(key=lambda x: x[1])
            return self.asteroids_not_empty
        else:
            return []

    def get_asteroids_watch(self, person):
        self.updatet_asteroids(asteroids=person.asteroids)
        if person.number_drone < len(self.asteroids_not_empty):
            return self.asteroids_not_empty[person.number_drone]
        else:
            return self.asteroids_not_empty[0]


    def get_asretoid_after_born(self, person):
        self.updatet_asteroids(asteroids=person.asteroids)
        for i in range(len(self.asteroids_not_empty) - 1):
            if self.asteroids_not_empty[i][2] <= 0:
                self.asteroids_not_empty.pop(i)
        if self.asteroids_not_empty == []:
            return person.my_mothership
        if person.number_drone < len(self.asteroids_not_empty):
            asteroid = self.asteroids_not_empty[person.number_drone]
        else:
            asteroid = self.asteroids_not_empty[0]
        number_first_asteroid = asteroid[0]
        if asteroid[2] >= 0:
            asteroid[2] -= person.free_space
            if asteroid[2] <= 0:
                if person.number_drone < len(self.asteroids_not_empty):
                    self.asteroids_not_empty.pop(person.number_drone)
                else:
                    self.asteroids_not_empty.pop(0)
            self.where_all_team[person.number_drone] = person.asteroids[number_first_asteroid]
            return person.asteroids[number_first_asteroid]
        else:
            self.where_all_team[person.number_drone] = person.my_mothership
            return person.my_mothership

    def after_asteroid_worker(self, person):
        for i in range(len(self.asteroids_not_empty) - 1):
            if self.asteroids_not_empty[i][2] <= 0:
                self.asteroids_not_empty.pop(i)
        if len(self.asteroids_not_empty) == 0:
            person.move_info()
            self.where_all_team[person.number_drone] = person.my_mothership
            person.move_at(person.my_mothership)
        else:
            if person.payload != 100:
                person.move_info()
                nearest_asteroid = self.calculation_min_len(person)
                self.where_all_team[person.number_drone] = nearest_asteroid
                person.move_at(nearest_asteroid)
            else:
                person.move_info()
                self.where_all_team[person.number_drone] = person.my_mothership
                person.move_at(person.my_mothership)

    def burn_worker(self, person):
        next_asteroid = self.get_asretoid_after_born
        #person.move_info()
        person.move_at(next_asteroid(person))

    def get_place_near_mothership(self, person):
        self.update_army_quantity()
        y = [280, 0]
        x = [50, 300]
        dy = int(abs(y[0] - y[-1]) // self.army_quantity)
        dx = int(abs(x[0] - x[-1]) // self.army_quantity)
        if person.my_mothership.coord.x <= theme.FIELD_WIDTH // 2 and person.my_mothership.coord.y <= theme.FIELD_HEIGHT // 2:
            y = list(range(y[0], y[-1], -dy))
            x = list(range(x[0], x[-1], dx))
            if self.army_quantity==1:
                x= [person.my_mothership.coord.x+75]
                y = [person.my_mothership.coord.y+75]
        elif person.my_mothership.coord.x >= theme.FIELD_WIDTH // 2 and person.my_mothership.coord.y <= theme.FIELD_HEIGHT // 2:
            x = [theme.FIELD_WIDTH - t for t in x]
            y = list(range(y[0], y[-1], -dy))
            x = list(range(x[0], x[-1], -dx))
            if self.army_quantity==1:
                x = [person.my_mothership.coord.x-75]
                y = [person.my_mothership.coord.y+75]
        elif person.my_mothership.coord.x >= theme.FIELD_WIDTH // 2 and person.my_mothership.coord.y >= theme.FIELD_HEIGHT // 2:
            x = [theme.FIELD_WIDTH - t for t in x]
            y = [theme.FIELD_HEIGHT - t for t in y]
            y = list(range(y[0], y[-1], dy))
            x = list(range(x[0], x[-1], -dx))
            if self.army_quantity == 1:
                x = [person.my_mothership.coord.x - 75]
                y = [person.my_mothership.coord.y - 75]
        elif person.my_mothership.coord.x <= theme.FIELD_WIDTH // 2 and person.my_mothership.coord.y >= theme.FIELD_HEIGHT // 2:
            y = [theme.FIELD_HEIGHT - t for t in y]
            y = list(range(y[0], y[-1], dy))
            x = list(range(x[0], x[-1], dx))
            if self.army_quantity == 1:
                x = [person.my_mothership.coord.x + 75]
                y = [person.my_mothership.coord.y - 75]
        x = x[:self.army_quantity]
        y = y[:self.army_quantity]
        position_defense = []
        for i in range(self.army_quantity):
            position_defense.append(Point(x[i], y[i]))
            self.where_all_team[person.number_drone] = Point(x=x[i], y=y[i])
        self.position_defense = position_defense


    def get_win_position(self, person, point):
        self.update_army_quantity()
        if self.army_quantity <5:
            quantity=5
        else:
            quantity=self.army_quantity
        center_field = Point(theme.FIELD_WIDTH // 2, theme.FIELD_HEIGHT // 2)
        Radius = ((point.x - center_field.x) ** 2 + (point.y - center_field.y) ** 2) ** 0.5
        radius = Radius * 0.8
        pfi = [(10 + 20 * i) * 3.14 / 180 for i in range(quantity)]
        win_position = []
        if (person.distance_to(point) > radius and person.distance_to(point) < 1.5*radius) or self.win_position == [] or\
                (person.distance_to(point) < radius and person.distance_to(point) > 0.3*radius):
            for fi in pfi:
                x_circle = radius * cos(fi)
                y_circle = radius * sin(fi)
                if point.x <= theme.FIELD_WIDTH // 2 and point.y <= theme.FIELD_HEIGHT // 2:
                    win_position.append(Point(x=point.x + x_circle, y=point.y + y_circle))
                elif point.x >= theme.FIELD_WIDTH // 2 and point.y <= theme.FIELD_HEIGHT // 2:
                    win_position.append(Point(x=point.x - x_circle, y=point.y + y_circle))
                elif point.x >= theme.FIELD_WIDTH // 2 and point.y >= theme.FIELD_HEIGHT // 2:
                    win_position.append(Point(x=point.x - x_circle, y=point.y - y_circle))
                elif point.x <= theme.FIELD_WIDTH // 2 and point.y >= theme.FIELD_HEIGHT // 2:
                    win_position.append(Point(x=point.x + x_circle, y=point.y - y_circle))
            self.win_position = win_position

    def game_over(self, person):
        if len(self.get_bases(person)) == 0 and len(self.get_enemies(person)) == 0 and len(
                self.asteroids_not_empty) == 0:
            for dron in self.all_team:
                if dron.free_space == 100:
                    flag_empty_drons = True
                else:
                    flag_empty_drons = False
                    break
            if flag_empty_drons:
                for dron in self.all_team:
                    dron.print_info()

    def next_action(self, person):
        self.game_over(person)
        self.update_army_quantity()
        self.big_losses(person)
        if person.health < 65:
            person.move_at(person.my_mothership)
            if person.near(person.my_mothership.coord):
                person.stop()
            else:
                person.move_at(person.my_mothership)
        else:
            if not person.fight:
                self.updatet_asteroids(person.asteroids)
                if self.asteroids_not_empty==[] or self.my_money*2+1>self.all_money:


                    if person.near(person.my_mothership.coord):
                        if self.my_money * 2 + 1 > self.all_money or person.payload == 0 or self.army_quantity<=3:
                            person.fight = True
                        else:
                            person.unload_to(person.mothership)
                    else:
                        person.move_at(person.mothership)

                else:
                    if int(person.payload) == 0 and person.near(person.my_mothership.coord):
                        self.burn_worker(person)
                        #person.turn_to(Point(300,300))
                    elif int(person.payload) != 100:
                        if not person.near(person.my_mothership.coord) and self.where_all_team[person.number_drone].payload > 0:
                            person.load_from(self.where_all_team[person.number_drone])
                            #person.turn_to(person.my_mothership.coord)
                        else:
                            if self.asteroids_not_empty:
                                self.after_asteroid_worker(person)

                    elif int(person.payload) == 100 or self.asteroids_not_empty == []:
                        if person.near(person.my_mothership.coord):
                            # print("Время выгружать")
                            person.unload_to(person.my_mothership)
                            person.turn_to(self.get_asteroids_watch(person))
                            self.my_money +=person.payload

                        else:
                            # print("бак полный, на базу!")
                            self.after_asteroid_worker(person)


            else:
                if int(person.payload) != 0:
                    if person.near(person.my_mothership.coord):
                        person.move_at(person.mothership)
                    else:
                        person.unload_to(person.mothership)


                if len(self.get_bases(person)) == 0 and len(self.get_enemies(person)) == 0:
                    person.fight = False
                    if not person.near(person.mothership):
                        person.move_at(person.mothership)
                    self.army = []
                else:
                    if person.health < 50:
                        person.move_at(person.my_mothership)
                    else:
                        if len(self.get_enemies(person)) == 0:
                            target = self.get_bases(person)[0][0]
                            self.get_win_position(person=person, point=Point(target.coord.x, target.coord.y))
                            my_position_win = self.win_position[person.number_drone]
                            if not person.near(my_position_win):
                                person.move_at(my_position_win)
                            else:

                                person.turn_to(target)
                                person.shoot(target)
                        elif len(self.get_enemies(person)) == 1 and self.army_quantity==5:
                            target = self.get_enemies(person)[0][0]
                            self.get_win_position(person=person, point=Point(target.coord.x, target.coord.y))
                            my_position_win = self.win_position[person.number_drone]
                            if not person.near(my_position_win):
                                person.move_at(my_position_win)
                            else:

                                person.turn_to(target)
                                person.shoot(target)
                        else:
                            self.get_place_near_mothership(person)
                            number_live = self.army_live[person.number_drone]
                            if number_live>=self.army_quantity:
                                self.update_army_quantity()
                            my_position_defense = self.position_defense[number_live]
                            if not person.near(my_position_defense):
                                person.move_at(my_position_defense)
                            else:
                                if len(self.get_enemies(person)) >= 1:
                                    targets = self.get_enemies(person)
                                    target = targets[0][0]
                                    person.turn_to(target)
                                    if self.probe(person=person, point=Point(x=target.coord.x, y=target.coord.y)):
                                        person.shoot(target)
                                    else:
                                        person.stop()

    def valide_place(self, person, point: Point):
        """
        Подходит ли это место для атаки. Слишком рядом не должно быть партнеров и на линии огня тоже не должно быть
        партнеров.
        :param point: анализируемое место
        :return: True or False
        """
        # TODO - на линии огня не проанализирвать, т.к. не ясно где цель

        is_valide = 0 < point.x < theme.FIELD_WIDTH and 0 < point.y < theme.FIELD_HEIGHT
        for partner in self.army:
            if not partner.is_alive or partner is person:
                continue
            is_valide = is_valide and (partner.distance_to(point) >= self.save_distance)
        return is_valide

    def probe(self, person, point: Point):
        N=15
        x0 = point.x
        x1 = person.coord.x
        y0 = point.y
        y1 = person.coord.y
        k = (y0-y1)/(x0-x1)
        b = y1-k*x1
        x_min = min(x0, x1)
        x_max = max(x0,x1)
        y_min=min(y1,y1)
        y_max=max(y0, y1)
        dx = int((x_max - x_min) // N)

        if dx == 0:
            dy= int((y_max - y_min)//N)
            if dy==0:
                return True
            y = list(range(int(y_min), int(y_max) + dy, dy))[:N + 1]
            for i in range(N+1):
                for partner in self.army:
                    if not partner.is_alive or partner is person:
                        continue
                    elif partner.distance_to(Point(x=x0, y=y[i])) < 60:
                        return False
            return True
        else:
            x = list(range(int(x_min), int(x_max)+dx, dx))[:N+1]
            for i in range(N+1):
                y = k*x[i] + b
                for partner in self.army:
                    if not partner.is_alive or partner is person:
                        continue
                    elif partner.distance_to(Point(x=x[i], y=y)) < 60:
                        return False
            return True


    def calculation_min_len(self, person):
        '''Находим ближайший астеройд'''
        if self.asteroids_not_empty:
            min_len = 10 ** 4
            k = 0
            for i, asteroid in enumerate(person.asteroids):
                li = person.distance_to(asteroid)
                if min_len > li and asteroid.payload != 0:
                    min_len = li
                    k = i

            for i, line in enumerate(self.asteroids_not_empty):
                if self.asteroids_not_empty[i][0] == k:
                    self.asteroids_not_empty[i][2] -= person.free_space
            return person.asteroids[k]
        else:
            return person.my_mothership

    def get_enemies(self, person):
        enemies = [(drone, person.distance_to(drone)) for drone in person.scene.drones if
                   person.team != drone.team and drone.is_alive]
        enemies.sort(key=lambda x: x[1])
        return enemies

    def get_bases(self, soldier):
        bases = [(base, soldier.distance_to(base)) for base in soldier.scene.motherships if
                 base.team != soldier.team and base.is_alive]
        bases.sort(key=lambda x: x[1])
        return bases


class XvatovDrone(Drone):
    brain = None
    info = []
    start_index = 0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tub = 100
        self.fight = None
        self.number_drone = None
        self.info.append([0, 0, 0])
        self.ASTEROIDS = None

    def registration(self):
        XvatovDrone.brain.add_person(self)
        self.number_drone = len(XvatovDrone.brain.all_team)
        XvatovDrone.brain.all_team.append(self)

    def shoot(self, object):
        self.gun.shot(object)

    def get_min_len(self):
        min_len = 10 ** 4
        for i, asteroid in enumerate(self.asteroids):
            li = self.distance_to(asteroid)
            if min_len > li and asteroid.payload != 0:
                min_len = li
        return min_len

    def print_info(self):
        print("Дрон с номером", self.number_drone, f"пролетел не загруженный l={self.info[self.number_drone][0]}")
        print("Дрон с номером", self.number_drone,
              f"пролетел загруженный не полностью l={self.info[self.number_drone][1]}")
        print("Дрон с номером", self.number_drone,
              f"пролетел загруженный полностью l={self.info[self.number_drone][2]}")

    def next_action(self):
        XvatovDrone.brain.next_action(self)

    def on_born(self):
        self.start_game()
        self.registration()
        if not self.fight:
            self.next_action()
        else:
            self.stop()

    def start_game(self):
        if XvatovDrone.brain is None:
            XvatovDrone.brain = Brain()
        self.update_space()

    def update_space(self):
        self.ASTEROIDS = XvatovDrone.brain.updatet_asteroids(asteroids=self.asteroids)

    def on_stop_at_asteroid(self, asteroid):
        self.next_action()

    def on_load_complete(self):
        self.next_action()

    def move_info(self):

        if self.payload == 0:
            if self.ASTEROIDS:
                self.info[self.number_drone][0] += self.ASTEROIDS[0][1]

        if self.payload != 0 and self.payload != 100:
            self.info[self.number_drone][1] += self.get_min_len()
        elif self.payload == 100 or self.ASTEROIDS == []:
            if self.is_full:
                self.info[self.number_drone][2] += self.distance_to(self.my_mothership)
            else:
                self.info[self.number_drone][1] += self.distance_to(self.my_mothership)

    def on_stop_at_mothership(self, mothership):
        self.next_action()

    def on_unload_complete(self):
        self.next_action()

    def on_wake_up(self):
        self.next_action()





drone_class = XvatovDrone