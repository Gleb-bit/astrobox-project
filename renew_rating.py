import json
import os

from playhouse.db_url import connect
import datetime
import logging
import argparse

from peewee import (
    BooleanField, CharField, DatabaseProxy, DateTimeField, DeferredForeignKey, ForeignKeyField,
    IntegerField, Model, SmallIntegerField, SQL, TextField,
)

PROJECT_PATH = os.path.dirname(__file__)

db_proxy = DatabaseProxy()


class BaseModel(Model):
    created_at = DateTimeField(default=datetime.datetime.now, null=True)
    updated_at = DateTimeField(default=datetime.datetime.now, null=True)

    class Meta:
        database = db_proxy  # см https://clck.ru/Jy4BB

    def save(self, force_insert=False, only=None):
        self.updated_at = datetime.datetime.now()
        super().save(force_insert=force_insert, only=only)


class AstroboxRating(BaseModel):
    user_name = CharField(max_length=255)
    rating = IntegerField(default=0)


class ProceededBattles(BaseModel):
    """ для хранения данных об обработанных результатах битв """
    battle_id = CharField(max_length=255)
    # тут можно еще сами результаты сохранять... вдруг перерасчет нужен будет


class RatingUpdater:

    def __init__(self, db_url, out_file):
        self.database = connect(db_url)
        db_proxy.initialize(self.database)
        self.database.create_tables([AstroboxRating, ProceededBattles])
        self.out_file = out_file

    def get_players(self, names):
        players = {}
        for name in names:
            player, created = AstroboxRating.get_or_create(user_name=name)
            players[name] = player
        return players

    def parse_results(self, results):
        user_score = results['collected']
        players = self.get_players(names=user_score.keys())
        for user_name, user_elerium in user_score.items():
            user = players[user_name]
            if user.rating >= 2400:
                koef_elo = 10
            elif user.rating >= 2300:
                koef_elo = 20
            else:
                koef_elo = 40
            for opponent_name, opponent_elerium in user_score.items():
                if opponent_name == user_name:
                    continue
                opponent = players[opponent_name]
                expectation = 1 / (1 + 10 ** ((opponent.rating - user.rating) / 400))
                if user_elerium < opponent_elerium * 0.95:
                    battle_result = 0
                elif user_elerium > opponent_elerium * 0.95:
                    battle_result = 1
                else:
                    battle_result = 0.5
                user.rating += int(koef_elo * (battle_result - expectation))
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
            table.write(f"Рейтинг по состоянию на {datetime.date.today().strftime('%d.%m.%Y')}\n\n")
            players = AstroboxRating.select().order_by('-rating')
            for index, player in enumerate(players):
                table.write(f"{index + 1}. {player.user_name} - {player.rating}\n")

    def update_rating(self, results_from_battle):
        if 'uuid' not in results_from_battle:
            raise ValueError('Battle results must contain uuid!')
        battle_id = results_from_battle['uuid']
        if ProceededBattles.get_or_none(ProceededBattles.battle_id == battle_id):
            logging.warning(f'Battle {battle_id} has been processed before. Skipped.')
            return
        self.parse_results(results_from_battle)
        ProceededBattles.create(battle_id=battle_id)

    def renew_from_files(self, *files):
        for file in files:
            with open(file, 'r') as ff:
                battle_result = json.load(ff)
            try:
                self.update_rating(battle_result)
            except Exception:
                logging.exception(f'Some error happened while process file {file}. Skipped.')

    def renew_from_directory(self, path):
        for dirpath, dirnames, filenames in os.walk(path):
            self.renew_from_files(filenames)


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
    args = parser.parse_args()
    if not args.battle_result and not args.battle_result_directory:
        raise ValueError('Нужно указать или файл с результатом битвы или директорию с такими файлами')

    astro_rating = RatingUpdater(db_url=f'sqlite:///{args.database}', out_file=args.out_file)
    if args.battle_result:
        astro_rating.renew_from_files(*args.battle_result)
    if args.battle_result_directory:
        astro_rating.renew_from_directory(args.battle_result_directory)
    astro_rating.write_results_in_file()
