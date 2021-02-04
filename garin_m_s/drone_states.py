# -*- coding: utf-8 -*-

import functions as f
from abc import ABCMeta, abstractmethod


class DroneState(metaclass=ABCMeta):

    guard_positions = None
    targets = []

    @abstractmethod
    def act(self, obj):
        pass

    @abstractmethod
    def get_my_target(self, obj):
        pass

    @abstractmethod
    def look_around_myself(self, obj):
        pass


class Born(DroneState):
    """
    Состояние рождения.
    """

    def act(self, obj):
        obj.change_state(obj._states[obj.my_role])

    def get_my_target(self, obj):
        obj.my_position = obj.coord

    def look_around_myself(self, obj):
        obj.my_role = 'collector'

        if obj.my_team:
            pass
        else:
            DroneState.guard_positions = f.positions_around_base(obj=obj, center=obj.mothership, point_count=7)
            obj.__class__.elirium_on_map = self._elirium_on_map(obj=obj)
            obj.__class__.elirium_for_win = obj.elirium_on_map // 2 + 1

    def _elirium_on_map(self, obj):
        count = 0
        for asteroid in obj.scene.asteroids:
            count += asteroid.payload
        return count


class Aiming(DroneState):
    """
    Состояние наведения.
    """

    def act(self, obj):
        if obj.target:
            obj.turn_to(obj.target)
            obj.change_state(obj._states['shooting'])
        elif not obj.near(obj.my_position):
            obj.move_at(obj.my_position)
            obj.change_state(obj._states[obj.my_role])
        else:
            obj.change_state(obj._states[obj.my_role])

    def get_my_target(self, obj):
        if obj.targets:
            if obj.my_role == 'guard_base':
                obj.targets.sort(key=lambda row: row[-1], reverse=False)
            else:
                obj.targets.sort(key=lambda row: row[-1], reverse=False)
            obj.target = obj.targets[0][0]
            obj.targets.clear()

    def look_around_myself(self, obj):
        obj.targets = list()
        enemies = f.get_enemy_drones(obj=obj)
        bases = f.get_enemy_bases(obj=obj)
        if self.danger_info(obj=obj):
            obj.my_role = 'guard_base'
        elif obj.my_role == 'guard_base':
            targets = f.points_on_feald(objects=enemies, near_base=False)
            targets = f.available_points_for_attack(obj=obj, obj_type='drone', points=targets)
            if targets:
                obj.targets = f.get_points_info(obj=obj, points=targets)
            else:
                obj.my_role = 'infantry'
        elif obj.my_role == 'infantry':
            targets = f.points_on_feald(objects=enemies, near_base=False)
            targets = f.available_points_for_attack(obj=obj, obj_type='drone', points=targets)
            if targets:
                obj.targets = f.get_points_info(obj=obj, points=targets)
        elif obj.my_role == 'besiegement':
            targets = f.points_on_feald(objects=enemies)
            targets = f.available_points_for_attack(obj=obj, obj_type='drone', points=targets, dist_change=1)
            if targets:
                obj.targets = f.get_points_info(obj=obj, points=targets)
        else:
            targets = f.available_points_for_attack(obj=obj, obj_type='base', points=bases, dist_change=1)
            if targets:
                obj.targets = f.get_points_info(obj=obj, points=targets)

    def danger_info(self, obj):
        if obj.my_role == 'guard_base':
            if obj.health < 50 and f.get_danger_info(obj=obj, point=obj.coord, count=2):
                return True
        elif obj.my_role == 'infantry':
            if obj.health < 85 or f.get_danger_info(obj=obj, point=obj.coord, count=2):
                return True
        elif obj.my_role == 'besiegement':
            if obj.health < 99 or f.get_danger_info(obj=obj, point=obj.coord, count=2):
                return True
        elif obj.my_role == 'sabotage':
            if obj.health < 25 or f.get_danger_info(obj=obj, point=obj.coord, count=1):
                return True
        elif obj.my_role == 'destruction' or obj.my_role == 'base_attack':
            if obj.health < 99 or f.get_danger_info(obj=obj, point=obj.coord, count=1):
                return True
        else:
            return False


class Shooting(DroneState):
    """
    Состояние выстрела.
    """

    def act(self, obj):
        if obj.target:
            obj.gun.shot(obj.target)
            obj.target = None
        obj.change_state(obj._states['aiming'])

    def get_my_target(self, obj, **kwargs):
        pass

    def look_around_myself(self, obj, **kwargs):
        if f.team_on_shot_line(obj=obj, target=obj.target):
            obj.target = None


class GuardBase(DroneState):
    """
    Состояние защитника базы.
    """

    def act(self, obj):
        if obj.near(obj.my_position):
            if obj.my_role == 'guard_base':
                if not obj.near(obj.mothership):
                    obj.change_state(obj._states['aiming'])
            else:
                obj.change_state(obj._states[obj.my_role])
        else:
            obj.move_at(obj.my_position)

    def get_my_target(self, obj, **kwargs):
        if obj.points:
            obj.points.sort(key=lambda row: row[1], reverse=False)
            obj.my_position = obj.points[0][0]
            obj.points.clear()
        elif obj.distance_to(obj.mothership) > 200:
            obj.my_position = obj.mothership.coord

    def look_around_myself(self, obj):
        obj.points = list()
        if any(obj.my_position is position for position in self.guard_positions):
            pass
        elif obj.is_empty:
            team = f.get_team_drones(obj=obj)
            for position in self.guard_positions:
                if not any(drone.my_position is position for drone in team):
                    obj.points = f.get_points_info(obj=obj, points=[position])
            if not obj.points and not obj.near(obj.mothership):
                obj.points = f.get_points_info(obj=obj, points=[obj.mothership.coord])
        else:
            obj.points = f.get_points_info(obj=obj, points=[obj.mothership.coord])


class Infantry(DroneState):

    def act(self, obj, role='infantry'):
        if obj.near(obj.my_position):
            if obj.my_role == role:
                obj.change_state(obj._states['aiming'])
            else:
                obj.change_state(obj._states[obj.my_role])
        else:
            obj.move_at(obj.my_position)
            obj.change_state(obj._states[obj.my_role])

    def get_my_target(self, obj, index=1):

        if obj.points:
            obj.points.sort(key=lambda row: row[index], reverse=False)
            obj.my_position = obj.points[0][0]

    def look_around_myself(self, obj, **kwargs):
        obj.points = list()
        enemy_drones = f.get_enemy_drones(obj=obj)
        enemy_positions_on_field = f.points_on_feald(objects=enemy_drones, near_base=False)
        if f.available_points_for_attack(obj=obj, obj_type='drone', points=enemy_positions_on_field):
            pass
        elif self.check_safe_alirium(obj=obj):
            obj.my_role = 'collector'
        elif enemy_positions_on_field:
            team_drones = f.get_team_drones(obj=obj)
            team_positions = [drone.my_position for drone in team_drones]
            enemy_positions_on_base = f.points_on_feald(objects=enemy_drones, near_base=True)

            positions = f.positions_for_attack(obj=obj, targets=enemy_positions_on_field,
                                               dis=f.DRONE_ATTACK_DISTANCE - 50, point_count=21)
            positions = f.safe_positions(obj=obj, positions=positions, danger=enemy_positions_on_base)
            positions = f.positions_near(obj=obj, positions=positions, distance=f.DRONE_RADIUS * 2)
            positions = f.no_team_behind(obj=obj, positions=positions,
                                         targets=enemy_positions_on_field, target_type='drone')
            positions = f.in_front_of_no_one(positions=positions, targets=enemy_positions_on_field,
                                             check_points=team_positions, check_type='drone')
            if positions:
                obj.points = f.get_points_info(obj=obj, points=positions)
            else:
                obj.my_role = 'destruction'
        else:
            obj.my_role = 'destruction'

    def check_safe_alirium(self, obj):
        enemies = f.get_enemy_drones(obj=obj)
        enemies = f.points_on_feald(objects=enemies)
        gains = f.get_elirium_source(obj=obj)
        gains = f.safe_positions(obj=obj, positions=gains, danger=enemies, lvl=1, dis=500)
        gains = f.positions_near(obj=obj, positions=gains, distance=f.DRONE_RADIUS)
        if gains:
            return True
        else:
            return False


class Destruction(Infantry):

    def act(self, obj, **kwargs):
        Infantry.act(self, obj=obj, role='destruction')

    def look_around_myself(self, obj, **kwargs):
        bases = f.get_enemy_bases(obj=obj)
        if f.available_points_for_attack(obj=obj, obj_type='base', points=bases):
            pass
        elif self.check_safe_alirium(obj=obj):
            obj.my_role = 'collector'
        else:
            positions = list()
            team = [drone.my_position for drone in f.get_team_drones(obj=obj)]
            radiuses = (200, 300, 400, 500, f.MOTHERSHIP_ATTACK_DISTANCE - 50)
            enemies = f.points_on_feald(objects=f.get_enemy_drones(obj=obj))
            for radius in radiuses:
                for base in bases:
                    positions.extend(f.positions_around_base(obj=obj, center=base, point_count=21, dist=radius))
            positions = f.safe_positions(obj=obj, positions=positions, danger=enemies)
            positions = f.positions_near(obj=obj, positions=positions, distance=f.DRONE_RADIUS)
            positions = f.in_front_of_no_one(positions=positions, targets=bases, check_points=team, check_type='drone')
            if positions:
                obj.points = f.get_points_info(obj=obj, points=positions)
            else:
                obj.my_role = 'sabotage'


class Sabotage(Infantry):

    def act(self, obj, **kwargs):
        Infantry.act(self, obj=obj, role='sabotage')

    def look_around_myself(self, obj, **kwargs):
        enemy_bases = f.get_enemy_bases(obj=obj)
        if f.available_points_for_attack(obj=obj, obj_type='base', points=enemy_bases, dist_change=-400):
            pass
        elif self.check_safe_alirium(obj=obj):
            obj.my_role = 'collector'
        else:
            positions = list()
            enemy_drones = f.get_enemy_drones(obj=obj)
            for base in enemy_bases:
                positions_around_base = f.positions_around_base(obj=obj, center=base, point_count=7, dist=100)
                defenders = [drone for drone in enemy_drones if drone.team == base.team]
                defenders = f.points_on_feald(objects=defenders)
                for position in positions_around_base:
                    for defender in defenders:
                        if base.near(defender):
                            break
                        elif f.point_on_shot_line(point_start=position, point_end=defender,
                                                  point_find=base, obj_type='base') is False:
                            break
                        elif f.point_on_shot_line(point_start=obj.my_position, point_end=base,
                                                  point_find=defender, obj_type='space') is True:
                            break
                    else:
                        positions.append(position)
            positions = f.positions_near(obj=obj, positions=positions, distance=f.DRONE_RADIUS * 2)
            if positions:
                obj.points = f.get_points_info(obj=obj, points=positions)
            else:
                obj.my_role = 'base_attack'


class BaseAttack(Infantry):

    def act(self, obj, **kwargs):
        Infantry.act(self, obj=obj, role='base_attack')

    def look_around_myself(self, obj, **kwargs):
        positions = list()
        bases = f.get_enemy_bases(obj=obj)
        if f.available_points_for_attack(obj=obj, obj_type='base', points=bases):
            pass
        elif self.check_safe_alirium(obj=obj):
            obj.my_role = 'collector'
        else:
            team = [drone.my_position for drone in f.get_team_drones(obj=obj)]
            radiuses = (400, 500, f.MOTHERSHIP_ATTACK_DISTANCE - 50)
            enemies = f.points_on_feald(objects=f.get_enemy_drones(obj=obj))
            for radius in radiuses:
                for base in bases:
                    positions.extend(f.positions_around_base(obj=obj, center=base, point_count=21, dist=radius))
            positions = f.safe_positions(obj=obj, positions=positions, danger=enemies, lvl=1, dis=300)
            positions = f.positions_near(obj=obj, positions=positions, distance=f.DRONE_RADIUS)
            positions = f.no_team_behind(obj=obj, positions=positions, targets=bases, target_type='drone')
            positions = f.in_front_of_no_one(positions=positions, targets=bases, check_points=team, check_type='drone')
            positions = f.in_front_of_no_one(positions=positions, targets=bases, check_points=enemies, check_type='drone')
            if positions:
                obj.points = f.get_points_info(obj=obj, points=positions)
            else:
                obj.my_role = 'besiegement'


class Besiegement(Infantry):

    def act(self, obj, **kwargs):
        Infantry.act(self, obj=obj, role='besiegement')

    def look_around_myself(self, obj, **kwargs):
        enemy_drones = f.get_enemy_drones(obj=obj)
        if f.available_points_for_attack(obj=obj, obj_type='drone', points=enemy_drones):
            pass
        elif self.check_safe_alirium(obj=obj):
            obj.my_role = 'collector'
        else:
            bases_info = self.bases_info(obj=obj, enemy_drones=enemy_drones)

            team_drones = f.get_team_drones(obj=obj)
            team_positions = [drone.my_position for drone in team_drones]

            for base in bases_info:
                defenders = base[3]
                defenders.sort(key=lambda row: row[1], reverse=False)
                for defender in defenders:
                    d = f.DRONE_ATTACK_DISTANCE - 50
                    danger = [drone for drone in enemy_drones if drone != defender[0]]
                    danger = f.points_on_feald(objects=danger)
                    positions = f.positions_for_attack(obj=obj, targets=[defender[0]], dis=d, point_count=31)
                    positions.extend(
                        f.positions_for_attack(obj=obj, targets=[defender[0]], dis=d - 100, point_count=31))
                    positions.extend(
                        f.positions_for_attack(obj=obj, targets=[defender[0]], dis=d - 100, point_count=31))
                    positions = f.safe_positions(obj=obj, positions=positions, danger=danger)
                    positions = f.no_team_behind(obj=obj, positions=positions,
                                                 targets=[defender[0].coord], target_type='drone')
                    positions = f.in_front_of_no_one(positions=positions, targets=[defender[0].coord],
                                                     check_points=team_positions, check_type='drone')
                    positions = f.positions_near(obj=obj, positions=positions, distance=f.DRONE_RADIUS * 2)
                    if positions:
                        obj.points = f.get_points_info(obj=obj, points=positions)
                        break
                else:
                    continue
                break

    def bases_info(self, obj, enemy_drones):
        bases_info = list()
        bases = f.get_enemy_bases(obj=obj)
        for base in bases:
            defenders = [[drone, obj.mothership.distance_to(drone)] for drone in enemy_drones
                         if drone.team == base.team]
            bases_info.append([base, obj.mothership.distance_to(base), len(defenders), defenders, 0])
        bases_info = f.points_generation(data=bases_info, key='distance', reverse=False, importance=1)
        bases_info = f.points_generation(data=bases_info, key='count', reverse=False, importance=1)
        bases_info.sort(key=lambda row: row[-1], reverse=False)
        return bases_info


class Collector(DroneState):
    """
    Состояние сборщика.
    """

    def act(self, obj):
        if obj.near(obj.my_position):
            obj.change_state(obj._states[obj.my_role])
        else:
            obj.move_at(obj.my_position)
            if not obj.my_role == 'Collector':
                obj.change_state(obj._states[obj.my_role])

    def get_my_target(self, obj):
        if obj.points:
            obj.points = f.points_generation(data=obj.points, key='distance_from_team_mothership',
                                             reverse=False, importance=1)
            obj.points = f.points_generation(data=obj.points, key='distance_from_team_drone',
                                             reverse=False, importance=1)

            obj.points.sort(key=lambda row: row[-1], reverse=False)
            obj.my_position = obj.points[0][0]
            obj.points.clear()

    def look_around_myself(self, obj):
        obj.points = list()
        if obj.health < 75 or f.get_danger_info(obj=obj, point=obj.coord) or obj.is_full:
            obj.my_role = 'guard_base'
        else:
            enemies = f.get_enemy_drones(obj=obj)
            enemies = f.points_on_feald(objects=enemies)
            gains = f.get_elirium_source(obj=obj)
            if obj.mothership.is_empty:
                gains = f.positions_near(obj=obj, positions=gains, distance=f.DRONE_RADIUS)
            else:
                gains = f.safe_positions(obj=obj, positions=gains, danger=enemies, lvl=1, dis=500)
            gains = f.get_elirium_sources_info(obj=obj, elirium_sources=gains)
            if gains:
                obj.points = f.get_elirium_sources_future_info(obj=obj, sources=gains)
            else:
                obj.my_role = 'guard_base'
