# -*- coding: utf-8 -*-
import os
from astrobox.space_field import SpaceField
import importlib


def drones_choose():
    scene = SpaceField(
        speed=150,
        field=(1200, 600),
        asteroids_count=50,
        headless=True)
    hangars = list(filter(lambda x: x[:6] == 'hangar', os.listdir()))
    for index, path in enumerate(hangars):
        print(index, path)
    choice = int(input('Название директории для подгрузки кода'))
    number_of_players = int(input('Количество игроков'))
    hangar_path = hangars[choice] if os.path.exists(hangars[choice]) else None
    players_to_add = os.listdir(hangar_path)
    added_players = []
    drones = {}
    if players_to_add:
        for number in range(1, number_of_players + 1):
            for index, path in enumerate(players_to_add):
                print(index, path)
            index_for_pop = int(input(f"Выберите игрока №{number}"))
            added_players.append(players_to_add.pop(index_for_pop))
    else:
        print('Ангар пуст.')
        return None
    for drone in added_players:
        path_to_drone = os.path.join(hangar_path + '.' + drone[:-3])
        drones[str(drone[:-3])] = importlib.import_module(path_to_drone).drone_class

    drones_teams = {}
    NUMBER_OF_DRONES = 5
    names = []
    for index, (name, drone) in enumerate(drones.items()):
        names.append(name)
        drones_teams[name] = [drone() for _ in range(NUMBER_OF_DRONES)]

    res = scene.go()
    return res

