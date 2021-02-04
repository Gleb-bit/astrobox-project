# -*- coding: utf-8 -*-

from garin_m_s.statistics import StatisticsMixin
import garin_m_s.drone_states as st
from astrobox.core import Drone


class GarinDrone(Drone, StatisticsMixin):
    my_team = []

    _states = {
        'collector': st.Collector(),
        'guard_base': st.GuardBase(),
        'aiming': st.Aiming(),
        'shooting': st.Shooting(),
        'infantry': st.Infantry(),
        'destruction': st.Destruction(),
        'sabotage': st.Sabotage(),
        'base_attack': st.BaseAttack(),
        'besiegement': st.Besiegement()
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        StatisticsMixin.__init__(self)
        self._local_state = st.Born()
        self.my_role = None

    def change_state(self, state: st.DroneState):
        self._local_state = state

    def on_born(self):
        self.look_around_myself()
        self.my_team.append(self)
        self.get_my_target()
        self.act()

    def act(self):
        self._execute(operation='act')

    def look_first(self):
        self._execute(operation='look_first')

    def look_around_myself(self):
        self._execute(operation='look_around_myself')

    def look_around_team(self):
        self._execute(operation='look_around_team')

    def get_my_target(self):
        self._execute(operation='get_my_target')

    def on_stop_at_point(self, target):
        if self.my_role == 'collector':
            killed = [gain for gain in self.scene.drones if self.near(gain) and gain.payload]
            self.turn_to(self.mothership)
            self.load_from(killed[0])
        self.look_around_myself()
        self.get_my_target()
        self.act()

    def on_stop_at_asteroid(self, asteroid):
        if self.my_role == 'collector':
            self.turn_to(self.mothership)
            self.load_from(asteroid)
        self.look_around_myself()
        self.get_my_target()
        self.act()

    def on_load_complete(self):
        self.look_around_myself()
        self.get_my_target()
        self.act()

    def on_stop_at_mothership(self, mothership):
        if mothership.team == self.team:
            if not self.is_empty:
                self.unload_to(mothership)
            else:
                self.look_around_myself()
                self.get_my_target()
                self.act()
        else:
            if self.my_role == 'collector':
                self.turn_to(self.mothership)
                self.load_from(mothership)

    def on_unload_complete(self):
        self.look_around_myself()
        self.get_my_target()
        self.act()

    def on_wake_up(self):
        self.look_around_myself()
        self.get_my_target()
        self.act()

    def distance(self):
        if self.is_empty:
            return 'empty', self.distance_to(self.target)
        elif self.is_full:
            return 'full', self.distance_to(self.target)
        else:
            return 'part_full', self.distance_to(self.target)

    def stat_print(self):
        self.team_distance()
        if all(dron.near(self.mothership) and dron.is_empty and dron.target is False for dron in self.my_team):
            self.stat_distance_out(self.team_stat_distance)

    def _execute(self, operation: str):
        try:
            func = getattr(self._local_state, operation)
            func(self)
        except AttributeError:
            print(f'{self} в состоянии {self._local_state.__class__} не умеет {operation}.')


drone_class = GarinDrone
