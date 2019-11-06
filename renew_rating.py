import battle
import sqlite3
from playhouse.db_url import connect
import datetime


class RatingUpdater:

    def __init__(self, table_name='astrobox', db_url='sqlite:///astro.sqlite'):
        self.database = connect(db_url)
        self.cursor = self.database.cursor()
        self.table_name = table_name
        try:
            self.cursor.execute(f"CREATE TABLE {self.table_name} (user_name STRING)")
            self.cursor.execute(f'''
            ALTER TABLE {self.table_name}
            ADD COLUMN rating STRING
            ''')
        except sqlite3.OperationalError:
            print(f"Таблица {self.table_name} уже есть в базе данных")

    def add_new_player_in_db(self, user_name):
        try:
            self.cursor.execute(
                f'''ALTER TABLE {self.table_name}
                ADD COLUMN {user_name} STRING''')
            self.cursor.execute(f"INSERT INTO {self.table_name} (user_name) VALUES ('{user_name}')")
        except sqlite3.OperationalError:
            print(f'{user_name} уже есть в {self.table_name}')

    def save_results_in_db(self, parsed_results):
        for user, user_results in parsed_results.items():
            for column_name, result in user_results.items():
                self.cursor.execute(f"""
                UPDATE {self.table_name}
                SET {column_name} = '{result}'
                WHERE user_name = '{user}'
                """)

    def get_results_from_db(self):
        self.cursor.execute(f"SELECT * FROM {self.table_name}")
        ratings = self.cursor.fetchall()
        print(f'Рейтинговая таблица: {ratings}')
        return ratings

    def get_ratings(self, results):
        players_rating = {}
        for new_user in results:
            self.add_new_player_in_db(new_user)
        for user in results:
            self.cursor.execute(f"""
                    SELECT rating FROM {self.table_name}
                    WHERE user_name = '{user}'""")
            rating = self.cursor.fetchall()
            if rating[0][0] is not None:
                players_rating[user] = rating[0][0]
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

    def write_results_in_file(self, ratings, path_to_file):
        rating_table = {}
        for element in ratings:
            rating_table[element[0]] = element[1]
        rating_list = sorted(rating_table.items(), key=lambda x: x[1], reverse=True)
        with open(path_to_file, 'w') as table:
            table.write(f"Рэйтинг по состоянию на {datetime.date.today().strftime('%d.%m.%Y')}\n\n")
            for index, (name, rating) in enumerate(rating_list):
                table.write(f"{index + 1}. {name} - {rating}\n")

    def update_table_and_database(self, results_from_battle):
        parsed_results = self.parse_results(results_from_battle)
        self.save_results_in_db(parsed_results)
        self.write_results_in_file(self.get_results_from_db(), 'RATING_2019.md')


astro_rating = RatingUpdater(db_url='sqlite:///astro.sqlite')
res_from_battle = battle.drones_choose()
astro_rating.update_table_and_database(res_from_battle)
