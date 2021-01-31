# -*- coding: utf-8 -*-
import json
import logging
import os
import random
import sys
from collections import OrderedDict
from pprint import pprint

import settings
from astrobox.space_field import SpaceField
import importlib
import argparse

from models import Player, init_db


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
    hangars = [x for x in os.listdir(settings.PROJECT_PATH) if 'hangar' in x]
    if not hangars:
        raise ValueError(f'No hangars in {settings.PROJECT_PATH}')
    for index, path in enumerate(hangars):
        print(f'\t {index} - {path}')
    choice = get_user_answer('Номер директории для подгрузки кода', range(len(hangars)))
    number_of_players = get_user_answer('Количество игроков', range(1, 5))
    hangar_path = hangars[choice] if os.path.exists(os.path.join(settings.PROJECT_PATH, hangars[choice])) else None
    players_to_add = [x for x in os.listdir(os.path.join(settings.PROJECT_PATH, hangar_path)) if '__' not in x]
    added_players = []
    if players_to_add:
        for number in range(1, number_of_players + 1):
            for index, path in enumerate(players_to_add):
                print(f'\t {index} - {path}')
            player_number = get_user_answer(f"Выберите игрока №{number}", range(len(players_to_add)))
            name = players_to_add.pop(player_number)
            added_players.append(os.path.join(hangar_path, name))
    else:
        print('Ангар пуст.')
        return None
    return added_players


def run_battle(player_modules, speed=150, asteroids_count=50, drones_count=5, show_screen=False):
    scene = SpaceField(
        speed=speed,
        field=(1200, 1200),
        asteroids_count=asteroids_count,
        can_fight=True,
        headless=not show_screen,
    )
    scene._Scene__teams = OrderedDict()
    drones_teams = {}
    drones_paths = {}
    for i, team_module in enumerate(player_modules):
        module_to_import = team_module.replace('.py', '').replace('/', '.').replace('\\', '.')
        drone_module = importlib.import_module(module_to_import)
        if not hasattr(drone_module, 'drone_class'):
            raise ValueError(f'In module {team_module} no variable drone_class: cant import drones!!!')
        drone = drone_module.drone_class
        drones_paths[drone.__name__] = team_module
        drones_teams[i] = [drone() for _ in range(drones_count)]
    battle_result = scene.go()
    battle_result['players_modules'] = drones_paths
    return battle_result


def print_battle_result(result):
    print('')
    print(f'Battle result:')
    pprint(result)


def save_battle_result(result, path):
    with open(path, 'w') as ff:
        ff.write(json.dumps(result, indent=1))
    print('')
    print(f'Battle result saved to {path}')


def get_tournament_players(player_module):
    if '.py' not in player_module:
        raise ValueError("Param player_module must be kind of 'hangar_XXXX/student_module.py'")
    player = Player.get_or_none(path=player_module)
    if not player:
        raise ValueError(f"No player with path {player_module} in database! Try renew_rating")
    candidates = [player, ]
    top_players = Player.select().filter(
        Player.rating > player.rating * 1.1
    ).order_by(Player.rating.asc()).limit(4)
    bottom_players = Player.select().filter(
        Player.rating < player.rating * 0.9
    ).order_by(Player.rating.desc()).limit(4)
    similar_players = Player.select().filter(
        (Player.rating <= player.rating * 1.1) &
        (Player.rating >= player.rating * 0.9) &
        (Player.id != player.id)
    )

    similar_players = list(similar_players) if similar_players else []
    top_players = list(top_players) if top_players else []
    bottom_players = list(bottom_players) if bottom_players else []
    top_players.sort(key=lambda x: x.rating)

    number_top_players = min(len(top_players), 1)
    number_similar_players = min(2 - number_top_players, len(similar_players))
    number_bottom_players = min(3 - number_top_players - number_similar_players, len(bottom_players))
    number_other_players = 3 - (number_top_players + number_similar_players + number_bottom_players)

    player_lists = []
    for candidat in [top_players[number_top_players - 1:1],
                     similar_players[:number_similar_players],
                     bottom_players[:number_bottom_players]
                     ]:
        if candidat:
            player_lists.append(candidat)

    other_players = [*top_players[number_top_players:],
                     *similar_players[number_similar_players:],
                     *bottom_players[number_bottom_players:]]

    random.shuffle(other_players)
    player_lists.append(other_players[:number_other_players])

    while len(candidates) <= 4:
        random.shuffle(similar_players)
        for _players in player_lists:
            candidate = _players.pop() if _players else None
            if candidate:
                candidates.append(candidate)
        if not any(player_lists):
            break
    return [candidate.path for candidate in candidates]


def _modules_exists(modules):
    for module in modules:
        full_path = os.path.join(settings.PROJECT_PATH, module)
        if not os.path.exists(full_path):
            return False
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Запускает битву нескольких команд дронов. '
                    'Модули с дронами можно указать как относительные пути к python-модулям. '
                    'Например: "python -m battle -p hangar_2019/.module_1.py hangar_2020/module_2.py" ". '
                    'Если модули не указаны, скрипт выяснит их интерактивно '
    )
    parser.add_argument('-p', '--player-module', type=str, nargs=argparse.ONE_OR_MORE,
                        help='Список модулей команд игроков в формате hangar_XXXX/module_name.py')
    parser.add_argument('-s', '--game-speed', type=int, default=10, help='Скорость битвы')
    parser.add_argument('-a', '--asteroids-count', type=int, default=10, help='Количество астероидов')
    parser.add_argument('-d', '--drones-count', type=int, default=5, help='Количество дронов в команде')
    parser.add_argument('-o', '--out-file', type=str, help='Путь для сохранения json-результатов битвы')
    parser.add_argument('-od', '--out-dir', type=str,
                        help='Папка для сохранения json-результатов битвы, имя файла автоматическое')
    parser.add_argument('-c', '--show-screen', action='store_true', help='показать экран битвы')
    parser.add_argument('-b', '--database', type=str, default=settings.DB_URL,
                        help=f'URL соединения с БД (если не указано то {settings.DB_URL})')
    parser.add_argument('-t', '--tournament', type=str,
                        help='Режим турнира для указанного игрока (путь до модуля), '
                             'остальные 3 игрока выбираются автоматически по рейтингу: '
                             'больший/меньший на 10 процентов и примерно равный (плюс/минус 5 процентов)')

    args = parser.parse_args()
    init_db(db_url=args.database)
    if args.tournament:
        if not _modules_exists([args.tournament, ]):
            logging.error(f'No module {args.tournament}')
            sys.exit(1)
        players = get_tournament_players(args.tournament)
    elif args.player_module:
        if not _modules_exists(args.player_module):
            logging.error(f'No one of modules: {args.player_module}')
            sys.exit(1)
        players = args.player_module
    else:
        players = players_choose()
    try:
        result = run_battle(player_modules=players, speed=args.game_speed,
                            asteroids_count=args.asteroids_count, drones_count=args.drones_count,
                            show_screen=True)
        if result:
            if args.out_file:
                save_battle_result(result=result, path=args.out_file)
            elif args.out_dir:
                os.makedirs(args.out_dir, exist_ok=True)
                path = os.path.join(args.out_dir, f"{result['uuid']}.json")
                save_battle_result(result=result, path=path)
            else:
                print_battle_result(result=result)
    except Exception as exc:
        logging.exception(f'Что-то пошло не так с параметрами {args}')
