# -*- coding: utf-8 -*-
import json
import logging
import os
from pprint import pprint

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


def run_battle(players, speed=150, asteroids_count=50, show_screen=False):
    scene = SpaceField(
        speed=speed,
        field=(1200, 600),
        asteroids_count=asteroids_count,
        can_fight=True,
        headless=not show_screen,
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
    pprint(result)


def save_battle_result(result, path):
    with open(path, 'w') as ff:
        ff.write(json.dumps(result))
    print(f'Battle result save to {path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Запускает битву нескольких игроков.')
    parser.add_argument('-p', '--players', type=str, nargs=argparse.ONE_OR_MORE,
                        help='Список модулей команд игроков в формате hangar_XXXX.module_name')
    parser.add_argument('-s', '--game-speed', type=int, default=5, help='Скорость игры')
    parser.add_argument('-a', '--asteroids-count', type=int, default=10, help='Количество астероидов')
    parser.add_argument('-o', '--out-file', type=str, help='Путь для сохранения json-результатов игры')
    parser.add_argument('-c', '--show-screen', action='store_true', help='показать экран игры')
    # TODO запиши себе параметры в запуск в пайчарме
    # args = parser.parse_args(''
    #                          '-p hangar_2019.kharitonov hangar_2019.vinogradov'
    #                          ' -s 5 -a 10 '
    #                          # '--show-screen'
    #                          # ' -o /tmp/battle_1.json'
    #                          ''.split())
    args = parser.parse_args()
    players = args.players if args.players else players_choose()
    try:
        result = run_battle(players=players, speed=args.game_speed,
                            asteroids_count=args.asteroids_count, show_screen=args.show_screen)
        if result:
            if args.out_file:
                save_battle_result(result=result, path=args.out_file)
            else:
                print_battle_result(result=result)
    except Exception as exc:
        logging.exception('Что-то пошло не так...')
