import json
import os

from playhouse.db_url import connect
import datetime
import logging
import argparse

from models import Player, Battle, db_proxy

PROJECT_PATH = os.path.dirname(__file__)
ELO_COEFFICIENTS = ((1000, 10), (700, 20), )


class RatingUpdater:

    def __init__(self, db_url, out_file):
        self.database = connect(db_url)
        db_proxy.initialize(self.database)
        self.database.create_tables([Player, Battle])
        self.out_file = out_file

    def get_players(self, battle_results):
        players = {}
        names = battle_results['collected'].keys()
        for name in names:
            path = battle_results['players_modules'][name]
            player, _ = Player.get_or_create(name=name, path=path)
            players[name] = player
        return players

    def parse_results(self, results):
        player_scores = results['collected']
        players = self.get_players(battle_results=results)
        for name, player_elerium in player_scores.items():
            user = players[name]
            koef_elo = 40
            for rating_bond, coeff in ELO_COEFFICIENTS:
                if user.rating >= rating_bond:
                    koef_elo = coeff
                    break
            for opponent_name, opponent_elerium in player_scores.items():
                if opponent_name == name:
                    continue
                opponent = players[opponent_name]
                logging.info(f'Рассчет Ело: {name}/{user.rating} vs {opponent_name}/{opponent.rating}')
                logging.info(f'\tЭлериум: {name}: {player_elerium}, {opponent_name}: {opponent_elerium}')
                expectation = 1 / (1 + 10 ** ((opponent.rating - user.rating) / 400))
                logging.info(f'\texpectation {expectation}')
                avg = (player_elerium + opponent_elerium) / 2
                delta = abs(player_elerium - opponent_elerium) / avg
                if delta < .05:
                    battle_result = 0.5
                elif player_elerium > opponent_elerium:
                    battle_result = 1
                else:
                    battle_result = 0
                rating_change = int(koef_elo * (battle_result - expectation))
                logging.info(f'\tdelta elerium {delta} battle_result {battle_result} rating_change {rating_change}')
                user.rating += rating_change
            user.save()
        return players

        # parsed_results[user_name] = {}
        # parsed_results[user_name]['rating'] = players_rating[user_name]
        # if parsed_results[user_name]['rating'] >= 2400:
        #     koef_elo = 10
        # elif parsed_results[user_name]['rating'] >= 2300:
        #     koef_elo = 20
        # else:
        #     koef_elo = 40
        # for opponent_name, elerium in user_score.items():
        #     expectation = 1 / (1 + 10 ** ((players_rating[opponent_name] - players_rating[user_name]) / 400))
        #     if (elerium * 0.95) <= user_score[user_name] <= (elerium * 1.05):
        #         parsed_results[user_name][opponent_name] = 0.5
        #     elif user_score[user_name] < elerium:
        #         parsed_results[user_name][opponent_name] = 0
        #     elif user_score[user_name] > elerium:
        #         parsed_results[user_name][opponent_name] = 1
        #     parsed_results[user_name]['rating'] += int(
        #         koef_elo * (parsed_results[user_name][opponent_name] - expectation))

    def write_results_in_file(self):
        with open(self.out_file, 'w') as table:
            table.write(f"##### Рейтинг по состоянию на {datetime.date.today().strftime('%d.%m.%Y')}\n\n")
            table.write(f"Позиция|Имя команды|Рейтинг\n")
            table.write(f"---|---|---:\n")
            players = Player.select().order_by(Player.rating.desc())
            for index, player in enumerate(players):
                if index > 41:
                    break
                table.write(f"{index + 1}|{player.name}|{player.rating}\n")

    def update_rating(self, battle_results):
        if 'uuid' not in battle_results:
            raise ValueError('Battle results must contain uuid!')
        battle_uuid = battle_results['uuid']
        if Battle.get_or_none(Battle.uuid == battle_uuid):
            logging.warning(f'Battle {battle_uuid} has been processed before. Skipped.')
            return
        self.parse_results(battle_results)
        Battle.create(uuid=battle_uuid, happened_at=battle_results.get('happened_at'), result=battle_results)

    def renew_from_files(self, path, files):
        for file in files:
            full_file_name = os.path.join(path, file)
            with open(full_file_name, 'r') as ff:
                battle_result = json.load(ff)
            try:
                self.update_rating(battle_result)
            except Exception:
                logging.exception(f'Some error happened while process file {file}. Skipped.')

    def renew_from_directory(self, path):
        for dirpath, dirnames, filenames in os.walk(path):
            self.renew_from_files(dirpath, filenames)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Перерасчитывает таблицу рейтинга по формуле Elo. '
                    'Предыдущая таблица берется из базы sqllite, '
                    'новые результаты битв можно передать как список json-файлов или указать директорию с ними')
    parser.add_argument('-r', '--battle-result', type=str, nargs=argparse.ONE_OR_MORE,
                        help='путь до файла(ов) с результатами игры')
    parser.add_argument('-d', '--battle-result-directory', type=str,
                        help='путь до папки с файлами результатов битв')
    parser.add_argument('-o', '--out-file', type=str, default=f'{PROJECT_PATH}/LOCAL_RATING.md',
                        help='куда сохранять таблицу рейтинга')
    parser.add_argument('-b', '--database', type=str, default=f'{PROJECT_PATH}/astro.sqlite',
                        help='путь до файла sqlite базы данных с рейтингом')
    parser.add_argument('-v', '--verbose', default=False, action='store_true',
                        help='подробности рассчета рейтинга')
    args = parser.parse_args()
    if not args.battle_result and not args.battle_result_directory:
        raise ValueError('Нужно указать или файл с результатом битвы или директорию с такими файлами')
    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    astro_rating = RatingUpdater(db_url=f'sqlite:///{args.database}', out_file=args.out_file)
    if args.battle_result:
        astro_rating.renew_from_files(*args.battle_result)
    if args.battle_result_directory:
        astro_rating.renew_from_directory(args.battle_result_directory)
    astro_rating.write_results_in_file()
