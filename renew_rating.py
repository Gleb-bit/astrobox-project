import os

import battle
from playhouse.db_url import connect
import datetime
import logging
import argparse
from playhouse.shortcuts import model_to_dict

from peewee import (
    BooleanField, CharField, DatabaseProxy, DateTimeField, DeferredForeignKey, ForeignKeyField,
    IntegerField, Model, SmallIntegerField, SQL, TextField,
)

PROJECT_PATH = os.path.dirname(__file__)


db_proxy = DatabaseProxy()


class AstroboxRating(Model):
    user_name = CharField(max_length=255)
    rating = CharField(max_length=255, null=True, default=0)
    created_at = DateTimeField(default=datetime.datetime.now, null=True)
    updated_at = DateTimeField(default=datetime.datetime.now, null=True)

    class Meta:
        database = db_proxy  # см https://clck.ru/Jy4BB

    def save(self, force_insert=False, only=None):
        self.updated_at = datetime.datetime.now()
        super().save(force_insert=force_insert, only=only)


class RatingUpdater:

    def __init__(self, db_url):
        self.database = connect(db_url)
        db_proxy.initialize(self.database)
        self.database.create_tables([AstroboxRating, ])

    @staticmethod
    def add_new_player_in_db(user_name):
        AstroboxRating.get_or_create(user_name=user_name)

    @staticmethod
    def save_results_in_db(parsed_results):
        for user_name, user_results in parsed_results.items():
            result = user_results['rating']
            user, created = AstroboxRating.get_or_create(user_name=user_name, defaults=dict(rating=result))
            if not created:
                user.rating = result
                user.save()

    @staticmethod
    def get_results_from_db():
        ratings = AstroboxRating.select().dicts()
        logging.debug(f'Рейтинговая таблица: {ratings}')
        return list(ratings)

    def get_ratings(self, results):
        players_rating = {}
        for new_user in results:
            self.add_new_player_in_db(new_user)
        for user in results:
            rating, created = AstroboxRating.get_or_create(user_name=user)
            # тут привести к работе с обьектами
            new_rating = int(rating.get().rating)
            if created:
                players_rating[user] = new_rating
            else:
                players_rating[user] = 0
        return players_rating

    def parse_results(self, results):
        parsed_results = {}
        players_rating = self.get_ratings(results)
        for user_name in results:
            parsed_results[user_name] = {}
            parsed_results[user_name]['rating'] = players_rating[user_name]
            if parsed_results[user_name]['rating'] >= 2400:
                koef_elo = 10
            elif parsed_results[user_name]['rating'] >= 2300:
                koef_elo = 20
            else:
                koef_elo = 40
            for opponent_name, elerium in results.items():
                expectation = 1 / (1 + 10 ** ((players_rating[opponent_name] - players_rating[user_name]) / 400))
                if (elerium * 0.95) <= results[user_name] <= (elerium * 1.05):
                    parsed_results[user_name][opponent_name] = 0.5
                elif results[user_name] < elerium:
                    parsed_results[user_name][opponent_name] = 0
                elif results[user_name] > elerium:
                    parsed_results[user_name][opponent_name] = 1
                parsed_results[user_name]['rating'] += int(
                    koef_elo * (parsed_results[user_name][opponent_name] - expectation))
        return parsed_results

    @staticmethod
    def write_results_in_file(ratings, path_to_file):
        rating_table = {}
        for element in ratings:
            rating_table[element['user_name']] = element['rating']
        rating_list = sorted(rating_table.items(), key=lambda x: x[1], reverse=True)
        with open(path_to_file, 'w') as table:
            table.write(f"Рейтинг по состоянию на {datetime.date.today().strftime('%d.%m.%Y')}\n\n")
            for index, (name, rating) in enumerate(rating_list):
                table.write(f"{index + 1}. {name} - {rating}\n")

    def update_table_and_database(self, results_from_battle):
        parsed_results = self.parse_results(results_from_battle)
        self.save_results_in_db(parsed_results)
        #  если студ запустит этот скрипт, то у него перезапишется рейтинг
        #  и когда студ будет делать МР в базу - рейтинги будут в конфликте :(
        #  надо что-то придумать. что бы рейтинг не перезаписывался. видимо по умолчанию
        #  писать в файл из .gitignore, а куратор будет может указать реальный файл
        self.write_results_in_file(self.get_results_from_db(), 'RATING_2019.md')


if __name__ == '__main__':
    #  тут добавить argparse что бы можно было указать:
    #  файл с результатами игры - если указан не запускать битву
    parser = argparse.ArgumentParser(description='results')
    parser.add_argument('result_file', type=str, help='path to file with results')
    args = parser.parse_args(['test'])
    if args.result_file:
        res_from_battle = {'kharit': 1, 'vinog': 0.5}
    else:
        drones = battle.players_choose()
        res_from_battle = battle.run_battle(drones, asteroids_count=10)
    astro_rating = RatingUpdater(db_url='sqlite:///{}/astro.sqlite'.format(PROJECT_PATH))
    astro_rating.update_table_and_database(res_from_battle)
