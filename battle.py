# -*- coding: utf-8 -*-
import logging
import os
from astrobox.space_field import SpaceField
import importlib
import argparse

PROJECT_PATH = os.path.dirname(__file__)


def players_choose():
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
    if players_to_add:
        for number in range(1, number_of_players + 1):
            for index, path in enumerate(players_to_add):
                print('\t', index, path)
            index_for_pop = int(input(f"Выберите игрока №{number} >>> "))
            name = players_to_add.pop(index_for_pop)[:-3]
            added_players.append(os.path.join(hangar_path + '.' + name))
    else:
        print('Ангар пуст.')
        return None
    return added_players


def run_battle(players, speed=150, asteroids_count=50):
    scene = SpaceField(
        speed=speed,
        field=(1200, 600),
        asteroids_count=asteroids_count,
        # headless=True,
    )
    drones_teams = {}
    NUMBER_OF_DRONES = 5
    names = []

    for index, path_to_drone in enumerate(players):
        name = path_to_drone.split('.')[1]
        names.append(name)
        drone = importlib.import_module(path_to_drone).drone_class
        drones_teams[name] = [drone() for _ in range(NUMBER_OF_DRONES)]
    return scene.go()


def print_battle_result(result):
    print('\t', result)


if __name__ == '__main__':
    #  тут добавить argparse что бы можно было указать:
    #  названия модулей студентов для битвы (в формате hangar/stud_cod, если указаны - то не спрашивать)
    #  скорость, астероиды, показывать ли поле - для запуска
    #  файл для сохранения результаттов игры - что бы потом считать рейтинг
    parser = argparse.ArgumentParser(description='drones, space_field, results')
    parser.add_argument('game_speed', type=int, default=5, help='game speed')
    parser.add_argument('asteroids_count', type=int, default=10, help='asteroids count')
    parser.add_argument('out_file', type=str, help='path to file with results')
    parser.add_argument('players', type=str, nargs=argparse.REMAINDER, help='list of players')
    args = parser.parse_args('5 10 RATING_2019.md hangar_2019.kharitonov hangar_2019.vinogradov'.split())
    drones = args.players if args.players else players_choose()
    try:
        result = run_battle(players=drones, speed=args.game_speed, asteroids_count=args.asteroids_count)
        if result:
            print_battle_result(result=result)
    except Exception as exc:
        logging.exception('Game failed :( ')
