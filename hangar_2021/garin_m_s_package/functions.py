# -*- coding: utf-8 -*-

import garin_m_s_package.geom as g
from astrobox.guns import PlasmaProjectile
from astrobox.core import Drone, MotherShip
from robogame_engine.geometry import Point


DRONE_RADIUS = Drone.radius
DRONE_SAFE_RADIUS = DRONE_RADIUS + PlasmaProjectile.radius + 1
DRONE_ATTACK_DISTANCE = DRONE_RADIUS + PlasmaProjectile.max_distance

MOTHERSHIP_RADIUS = MotherShip.radius
MOTHERSHIP_SAFE_RADIUS = MOTHERSHIP_RADIUS + PlasmaProjectile.radius + 1
MOTHERSHIP_ATTACK_DISTANCE = MOTHERSHIP_RADIUS + PlasmaProjectile.max_distance

SAFE_DISTANCE = DRONE_RADIUS + PlasmaProjectile.max_distance + PlasmaProjectile.radius


def scene_center(obj):
    return Point(x=obj.scene.field[0] / 2, y=obj.scene.field[1] / 2)


def point(coord):
    return Point(*coord)


def get_drones(obj):
    return tuple(drone for drone in obj.scene.drones if drone.is_alive and drone != obj)


def get_team_drones(obj):
    return tuple(drone for drone in obj.scene.drones if drone.is_alive and drone.team == obj.team and drone != obj)


def get_enemy_drones(obj):
    return tuple(drone for drone in obj.scene.drones if drone.is_alive and drone.team != obj.team)


def get_enemy_bases(obj):
    return tuple(base for base in obj.scene.motherships if base.is_alive and base.team != obj.team)


def get_shots(obj):
    return tuple(shot for shot in obj.scene.objects if shot.__class__ is PlasmaProjectile and shot.state.target_point)


def get_elirium_source(obj):
    for_return = list()
    for_return.extend(target for target in obj.asteroids if target.payload)
    for_return.extend(target for target in obj.scene.drones if target.payload and not target.is_alive)
    for_return.extend(target for target in obj.scene.motherships if target.payload and not target.is_alive)
    return tuple(for_return)


def get_elirium_sources_info(obj, elirium_sources):
    for_return = dict()
    for elirium_source in elirium_sources:
        for_return[elirium_source] = [elirium_source.payload, obj.mothership.distance_to(elirium_source),
                                      obj.distance_to(elirium_source), 0]
    return for_return


def get_elirium_sources_future_info(obj, sources):
    drones = get_drones(obj=obj)
    for drone in drones:
        targets = (target for target in sources
                   if drone.state.target_point and target.near(drone.state.target_point)
                   or drone.target and target.near(drone.target))

        for target in targets:
            if drone.team is obj.team:
                payload = sources[target][0] - drone.free_space
                sources[target][0] = payload
            else:
                if obj.distance_to(target) > drone.distance_to(target):
                    payload = sources[target][0] - drone.free_space
                    sources[target][0] = payload

    return [[gain] + value for gain, value in sources.items() if value[0] > 0]


def get_points_info(obj, points):
    for_return = list()
    for point in points:
        for_return.append([point, obj.distance_to(point), obj.mothership.distance_to(point)])
    return for_return


def points_on_feald(objects, near_base=None):
    for_return = list()
    for obj in objects:
        if obj.is_moving:
            point = obj.state.target_point
        else:
            point = obj.coord
        if position_on_feald(objects=obj, point=point, near_base=near_base):
            for_return.append(point)

    return for_return


def position_on_feald(objects, point, near_base):
    if near_base is True and objects.mothership.is_alive and objects.mothership.distance_to(point) <= 200:
        return True
    elif near_base is False and objects.mothership.distance_to(point) > 200:
        return True
    elif near_base is False and not objects.mothership.is_alive:
        return True
    elif near_base is None:
        return True
    else:
        return False


def available_points_for_attack(obj, obj_type, points, dist_change=0):
    for_return = list()
    distance = {'drone': DRONE_ATTACK_DISTANCE, 'base': MOTHERSHIP_ATTACK_DISTANCE}
    drone_coord = get_coord(obj=obj.my_position)
    for point in points:
        point_coord = get_coord(obj=point)
        if distance[obj_type] + dist_change > g.distance_between_points(point_1=drone_coord, point_2=point_coord):
            if team_on_shot_line(obj=obj, target=point) is False:
                for_return.append(point)
    return for_return


def positions_around_base(obj, center, point_count, dist=199.9):
    points = g.points_on_ring(scene=obj.scene.field, radius=dist,
                              point_base=(obj.scene.field[0] / 2, obj.scene.field[1] / 2),
                              center=get_coord(center), count=point_count, edge=DRONE_RADIUS)

    return tuple(Point(*point) for point in points)


def positions_for_attack(obj, targets, dis, point_count=11):
    for_return = list()
    for target in targets:
        target_coord = get_coord(obj=target)
        points_coord = g.points_on_ring(scene=(obj.scene.field[0], obj.scene.field[1]),
                                        radius=dis,
                                        point_base=(obj.mothership.coord.x, obj.mothership.coord.y),
                                        center=target_coord,
                                        count=point_count,
                                        edge=50)
        for point_coord in points_coord:
            point = Point(*point_coord)
            for targett in targets:
                if obj.mothership.distance_to(point) >= obj.mothership.distance_to(targett):
                    break
            else:
                if obj.mothership.distance_to(point) > 100:
                    for_return.append(point)

    return for_return


def positions_near(obj, positions, distance):
    for_return = list()
    team = get_team_drones(obj=obj)
    for point in positions:
        point_coord = get_coord(obj=point)
        for drone in team:
            drone_coord = get_coord(obj=drone.my_position)
            if g.distance_between_points(point_1=point_coord, point_2=drone_coord) < distance:
                break
        else:
            for_return.append(point)
    return for_return


def get_coord(obj):
    if obj.__class__ is Point:
        return obj.x, obj.y
    else:
        return obj.coord.x, obj.coord.y


def in_front_of_no_one(positions, targets, check_points, check_type='drone'):
    for_return = list()
    for position in positions:
        for target in targets:
            for check in check_points:
                if point_on_shot_line(point_start=position, point_end=target, point_find=check, obj_type=check_type):
                    break
            else:
                continue
            break
        else:
            for_return.append(position)
    return for_return


def no_team_behind(obj, positions, targets, target_type):
    for_return = list()
    distance = {'drone': DRONE_ATTACK_DISTANCE, 'base': MOTHERSHIP_ATTACK_DISTANCE}
    team = [drone.my_position for drone in get_team_drones(obj=obj)]
    for position in positions:
        for target in targets:
            for drone in team:
                check_dist = g.distance_between_points(point_1=get_coord(obj=drone), point_2=get_coord(obj=target))
                if check_dist < distance[target_type]:
                    if point_on_shot_line(point_start=drone, point_end=target, point_find=position, obj_type='drone'):
                        break
            else:
                continue
            break
        else:
            for_return.append(position)

    return for_return


def point_on_shot_line(point_start, point_end, point_find, obj_type='drone'):
    distance = {'drone': DRONE_SAFE_RADIUS, 'base': MOTHERSHIP_RADIUS, 'space': 100}
    point_start = get_coord(obj=point_start)
    point_end = get_coord(obj=point_end)
    point_find = get_coord(obj=point_find)
    intersection = g.intersection(point_start=point_start, point_end=point_end, point_find=point_find)
    if g.point_between_points(point_start=point_start, point_end=point_end, point_find=intersection) is True:
        distance_to_line = g.distance_between_points(point_1=point_find, point_2=intersection)
        if distance_to_line < distance[obj_type]:
            return True
        else:
            return False
    else:
        return False


def team_on_shot_line(obj, target):
    team = [obj.mothership]
    team.extend(get_team_drones(obj=obj))
    for drone in team:
        if point_on_shot_line(point_start=obj.coord, point_end=target, point_find=drone.coord):
            return True
    else:
        return False


def get_danger_info(obj, point, count=2):
    shots = get_shots(obj=obj)
    shots_count = 0
    for shot in shots:
        enemy = shot._owner.coord
        target = shot.state.target_point
        point_end = g.point_between_on_distance(distance=DRONE_ATTACK_DISTANCE,
                                                point_start=(enemy.x, enemy.y),
                                                point_end=(target.x, target.y))
        if point_on_shot_line(point_start=enemy, point_end=Point(*point_end), point_find=point):
            count += 1

    if shots_count >= count:
        return True
    else:
        return False


def safe_positions(obj, positions, danger, lvl=0, dis=0):
    for_return = list()
    for position in positions:
        pos_coord = get_coord(obj=position)
        level = 0
        for enemy in danger:
            enemy_coord = get_coord(obj=enemy)
            if g.distance_between_points(point_1=pos_coord, point_2=enemy_coord) < SAFE_DISTANCE:
                if level >= lvl:
                    break
                else:
                    if g.distance_between_points(point_1=pos_coord, point_2=enemy_coord) >= dis:
                        for enemy_2 in danger:
                            if enemy_2 != enemy:
                                if point_on_shot_line(point_start=position, point_end=enemy, point_find=enemy_2):
                                    break
                        else:
                            level += 1
                    else:
                        break
            else:
                if get_danger_info(obj=obj, point=position, count=1):
                    break
        else:
            for_return.append(position)
    return for_return


def points_generation(data, key, reverse, importance=1):
    """
    Определяет значение привлекательности параметра.
    :param key: Принимает ключ для сортировки
    :param reverse: Сортировка списка. Принимает True (по убыванию) или False (по возрастанию).
    :param importance: Принимает важность ключа.
    """
    keys = {'elirium_in_asteroid': 1,
            'distance': 1,
            'distance_from_team_mothership': 2,
            'count': 2,
            'distance_from_team_drone': 3}

    for_return = list()
    data.sort(key=lambda row: row[keys[key]], reverse=reverse)

    for number, value in enumerate(data):
        value[-1] += (0.1 * (number + 0.1) * importance)
        for_return.append(value)
    return for_return