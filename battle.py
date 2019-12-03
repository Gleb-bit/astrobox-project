# -*- coding: utf-8 -*-
import json
import logging
import os
from pprint import pprint
from astrobox.space_field import SpaceField
import importlib
import argparse

PROJECT_PATH = os.path.dirname(__file__)


def get_user_answer(prompt, valid_values=None):
    while True:
        answer = input(f'{prompt} >>> ')
        try:
            answer = int(answer)
        except ValueError:
            print('Необходимо ввести номер')
            continue
        if valid_values and answer not in valid_values:
            print(f'Выберите один вариант из {list(valid_values)}')
            continue
        return answer


def players_choose():
    hangars = [x for x in os.listdir(PROJECT_PATH) if 'hangar' in x]
    if not hangars:
        raise ValueError(f'No hangars in {PROJECT_PATH}')
    for index, path in enumerate(hangars):
        print(f'\t {index} - {path}')
    choice = get_user_answer('Номер директории для подгрузки кода', range(len(hangars)))
    number_of_players = get_user_answer('Количество игроков', range(1, 5))
    hangar_path = hangars[choice] if os.path.exists(os.path.join(PROJECT_PATH, hangars[choice])) else None
    players_to_add = [x for x in os.listdir(os.path.join(PROJECT_PATH, hangar_path)) if '__' not in x]
    added_players = []
    if players_to_add:
        for number in range(1, number_of_players + 1):
            for index, path in enumerate(players_to_add):
                print(f'\t {index} - {path}')
            index_for_pop = get_user_answer(f"Выберите игрока №{number}", range(len(players_to_add)))
            name = players_to_add.pop(index_for_pop)[:-3]
            added_players.append(os.path.join(hangar_path + '.' + name))
    else:
        print('Ангар пуст.')
        return None
    return added_players


def run_battle(players, speed=150, asteroids_count=50, drones_count=5, show_screen=False):
    scene = SpaceField(
        speed=speed,
        field=(1200, 600),
        asteroids_count=asteroids_count,
        can_fight=True,
        headless=not show_screen,
    )
    drones_teams = {}
    for i, team_module in enumerate(players):
        if '.py' in team_module:
            team_module = team_module.replace(PROJECT_PATH, '').replace('.py', '').replace('/', '.')
        drone = importlib.import_module(team_module).drone_class
        drones_teams[i] = [drone() for _ in range(drones_count)]
    return scene.go()


def print_battle_result(result):
    print('')
    print(f'Battle result:')
    pprint(result)


def save_battle_result(result, path):
    with open(path, 'w') as ff:
        ff.write(json.dumps(result, indent=1))
    print('')
    print(f'Battle result saved to {path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Запускает битву нескольких команд дронов. '
                    'Модули с дронами можно указать как python-модули, так и пути к ним. '
                    'Например: "python -m battle -p hangar_2019.module_1 hangar_2019.module_2" '
                    'или "python -m battle -p hangar_2019/.module_1.py hangar_2019/.module_2.py" ". '
                    'Если модули не указаны, скрипт выяснит их интерактивно '
    )
    parser.add_argument('-p', '--player-module', type=str, nargs=argparse.ONE_OR_MORE,
                        help='Список модулей команд игроков в формате hangar_XXXX.module_name')
    parser.add_argument('-s', '--game-speed', type=int, default=5, help='Скорость битвы')
    parser.add_argument('-a', '--asteroids-count', type=int, default=10, help='Количество астероидов')
    parser.add_argument('-d', '--drones-count', type=int, default=5, help='Количество дронов в команде')
    parser.add_argument('-o', '--out-file', type=str, help='Путь для сохранения json-результатов битвы')
    parser.add_argument('-c', '--show-screen', action='store_true', help='показать экран битвы')
    # TODO запиши себе параметры в запуск в пайчарме
    # args = parser.parse_args(''
    #                          '-p hangar_2019.kharitonov hangar_2019.vinogradov'
    #                          ' -s 5 -a 10 '
    #                          # '--show-screen'
    #                          # ' -o /tmp/battle_1.json'
    #                          ''.split())
    args = parser.parse_args()
    players = args.player_module if args.player_module else players_choose()
    try:
        result = run_battle(players=players, speed=args.game_speed,
                            asteroids_count=args.asteroids_count, drones_count=args.drones_count,
                            show_screen=args.show_screen)
        if result:
            if args.out_file:
                save_battle_result(result=result, path=args.out_file)
            else:
                print_battle_result(result=result)
    except Exception as exc:
        logging.exception('Что-то пошло не так...')

