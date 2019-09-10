from astrobox.core import Drone


ASTEROIDS_DRONES = {}


class VinogradovDrone(Drone):

    def on_born(self):
        if len(ASTEROIDS_DRONES) == 0:
            self._fill_holder()
        asteroid = self.choose_asteroid()
        self.move_at(asteroid)

    def on_stop_at_asteroid(self, asteroid):
        if not self.mothership.is_full:
            self.load_from(asteroid)

    def on_load_complete(self):
        asteroid = self.choose_asteroid()
        if not self.is_full and asteroid is not None:
            self.move_at(asteroid)
        else:
            self.move_at(self.my_mothership)

    def on_stop_at_mothership(self, mothership):
        self.unload_to(mothership)

    def on_unload_complete(self):
        asteroid = self.choose_asteroid()
        if asteroid is not None:
            self.move_at(asteroid)

    def _fill_holder(self):
        for asteroid in self.asteroids:
            if asteroid.payload > 0:
                if asteroid not in ASTEROIDS_DRONES:
                    ASTEROIDS_DRONES[asteroid] = []

    def choose_asteroid(self):
        for aster, drone in ASTEROIDS_DRONES.items():
            if drone is self:
                if aster.is_empty:
                    ASTEROIDS_DRONES.pop(aster)
        asteroids_params = [asteroid for asteroid in self.asteroids if not asteroid.is_empty]
        asteroids_params.sort(key=lambda ast: self.distance_to(ast)/ast.payload)
        if len(asteroids_params) > 0:
            for sorted_asteroid in asteroids_params:
                asteroid_drones = ASTEROIDS_DRONES[sorted_asteroid]
                free_space = [drone.free_space for drone in asteroid_drones if drone != self]
                free_space.append(self.free_space)
                free_space_sum = sum(free_space)
                if sorted_asteroid.payload >= free_space_sum*.8:
                    ASTEROIDS_DRONES[sorted_asteroid].append(self)
                    return sorted_asteroid
            return asteroids_params[0]
drone_class = VinogradovDrone
