# -*- coding: utf-8 -*-
import logging
import os
from astrobox.space_field import SpaceField
import importlib

PROJECT_PATH = os.path.dirname(__file__)


def drones_choose():
    hangars = [x for x in os.listdir(PROJECT_PATH) if 'hangar' in x]
    if not hangars:
        raise ValueError(f'No hangars in {PROJECT_PATH}')
    for index, path in enumerate(hangars):
        print('\t', index, path)
    choice = int(input('Название директории для подгрузки кода >>> '))
    number_of_players = int(input('Количество игроков >>> '))
    hangar_path = hangars[choice] if os.path.exists(os.path.join(PROJECT_PATH, hangars[choice])) else None
    players_to_add = [x for x in os.listdir(os.path.join(PROJECT_PATH, hangar_path)) if '__' not in x]
    added_players = []
    drones = {}
    if players_to_add:
        for number in range(1, number_of_players + 1):
            for index, path in enumerate(players_to_add):
                print('\t', index, path)
            index_for_pop = int(input(f"Выберите игрока №{number} >>> "))
            added_players.append(players_to_add.pop(index_for_pop))
    else:
        print('Ангар пуст.')
        return None
    for drone in added_players:
        path_to_drone = os.path.join(hangar_path + '.' + drone[:-3])
        drones[str(drone[:-3])] = importlib.import_module(path_to_drone).drone_class

    return drones


def run_battle(drones, speed=150, asteroids_count=50):
    scene = SpaceField(
        speed=speed,
        field=(1200, 600),
        asteroids_count=asteroids_count,
        # headless=True,
    )
    drones_teams = {}
    NUMBER_OF_DRONES = 5
    names = []
    for index, (name, drone) in enumerate(drones.items()):
        names.append(name)
        drones_teams[name] = [drone() for _ in range(NUMBER_OF_DRONES)]
    return scene.go()


def print_battle_result(result):
    print('\t', result)


if __name__ == '__main__':
    # TODO тут добавить argparse что бы можно было указать:
    #  названия модулей студентов для битвы (в формате hangar/stud_cod, если указаны - то не спрашивать)
    #  скорость, астероиды, показывать ли поле - для запуска
    #  файл для сохранения результаттов игры - что бы потом считать рейтинг
    drones = drones_choose()
    try:
        result = run_battle(drones=drones, speed=5, asteroids_count=10)
        if result:
            print_battle_result(result=result)
    except Exception as exc:
        logging.exception('Game failed :( ')
