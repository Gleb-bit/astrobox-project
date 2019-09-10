from astrobox.core import Drone


class KrasnogorovDrone(Drone):

    def __init__(self, my_number):
        super().__init__()
        self.drone_number = my_number
        self.my_asteroid = None
        self.empty_asteroids = []

    def on_born(self):
        self.play = True
        self.distance_not_fully_loaded = 0
        self.distance_loaded = 0

        if self.drone_number != 1:
            self.my_first_asteroid = self.find_middle_asteroid()
        else:
            self.my_first_asteroid = self.find_closest_asteroid()

        self.my_asteroid = self.my_first_asteroid
        self.move_at(self.my_first_asteroid)
        self.current_asteroid = 0
        self.my_asteroid = self.my_first_asteroid

    def on_stop_at_asteroid(self, asteroid):
        if self.free_space <= asteroid.payload:
            self.turn_to(self.my_mothership)
        else:
            self.turn_to(self.find_closest_asteroid())
        self.load_from(asteroid)

    def on_load_complete(self):
        self.check_all_asteroids()
        if len(self.empty_asteroids) == len(self.asteroids):
            self.move_at(self.my_mothership)
        elif not self.is_full:
            self.my_asteroid = self.find_closest_asteroid()
            self.move(self.my_asteroid)
        else:
            self.move(self.my_mothership)

    def on_stop_at_mothership(self, mothership):
        if self.payload != 0:
            self.unload_to(mothership)
            self.turn_to(self.find_closest_asteroid())
        else:
            self.on_unload_complete()

    def on_unload_complete(self):
        self.check_all_asteroids()
        self.my_asteroid = self.find_closest_asteroid()
        if self.my_asteroid == self.my_mothership:
            self.play = False
            self.statistic()
            self.stop()
        else:
            self.move(self.my_asteroid)

    def find_closest_asteroid(self):
        "ищем полностью свободные астероиды, второй цикл - ищем кому можно помочь, если нету свободных астероидов"
        distance_and_number_drone = []
        for asteroid in self.asteroids:
            if self.check_asteroid(asteroid, only_free_asteroid=True):
                distance_and_number_drone.append((asteroid, self.distance_to(asteroid)))
        if not distance_and_number_drone:
            for asteroid in self.asteroids:
                if self.check_asteroid(asteroid, only_free_asteroid=False):
                    distance_and_number_drone.append((asteroid, self.distance_to(asteroid)))
        if not distance_and_number_drone:
            return self.my_mothership
        information_about_drone = min(distance_and_number_drone, key=lambda i: i[1])
        return information_about_drone[0]

    def check_asteroid(self, asteroid, only_free_asteroid=False):
        if asteroid in self.empty_asteroids:
            return False
        if only_free_asteroid == False:
            payload = asteroid.payload
            for drone in self.teammates:
                if drone.my_asteroid == asteroid:
                    payload -= drone.free_space
            if payload <= 0:
                if asteroid not in self.empty_asteroids:
                    self.empty_asteroids.append(asteroid)
                return False
            else:
                return True
        else:
            for drone in self.teammates:
                if drone.my_asteroid == asteroid:
                    if asteroid not in self.empty_asteroids:
                        self.empty_asteroids.append(asteroid)
                    return False
            return True

    def move(self, target):
        self.move_at(target)
        if self.is_empty:
            self.distance_not_fully_loaded += self.distance_to(target)
        else:
            self.distance_loaded += self.distance_to(target)

    def find_middle_asteroid(self):
        distance_and_number_drone = []
        for asteroid in self.asteroids:
            if self.check_asteroid(asteroid, only_free_asteroid=True):
                distance_and_number_drone.append((asteroid, self.distance_to(asteroid)))
        distance_and_number_drone.sort(key=lambda i: i[1])
        n = len(distance_and_number_drone)
        return distance_and_number_drone[n * 4 // 10][0]

    def check_all_asteroids(self):
        for asteroid in self.asteroids:
            if asteroid.payload <= 0 and asteroid not in self.empty_asteroids:
                self.empty_asteroids.append(asteroid)

    def statistic(self):

        sum_without_resources = 0
        sum_with_resources = 0

        for drone in self.teammates:
            if drone.play == False:
                sum_without_resources += drone.distance_not_fully_loaded
                sum_with_resources += drone.distance_loaded
            else:
                return
        print("Пролетели расстояние загруженными = ", round(sum_with_resources, 2))
        print("Пролетели расстояние не загруженными", round(sum_without_resources, 2))
        print(len(self.empty_asteroids))


drone_class = KrasnogorovDrone
