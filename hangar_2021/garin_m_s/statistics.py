# -*- coding: utf-8 -*-


class StatisticsMixin:

    team_stat_distance = dict()

    def __init__(self):
        self.stat_distance = dict()

    def stat_get(self, func, data):
        key, value = func
        if key in data:
            data[key] += value
        else:
            data[key] = value

    def stat_distance_get(self):
        self.stat_get(self.distance(), self.stat_distance)

    def distance(self):
        assert False, 'distance must be defined!'

    def team_distance(self):
        for key, value in self.stat_distance.items():
            self.stat_get((key, value), self.team_stat_distance)

    def stat_distance_out(self, data):

        self.percent_get(data)

        indentation = 20
        line = f'+{"-":-^{indentation}}+{"-":-^{indentation}}+{"-":-^{indentation}}+'
        headline = f'|{"Заполненность":^{indentation}}|{"Дистанция":^{indentation}}|{"Процент":^{indentation}}|'

        print(line)
        print(headline)
        print(line)

        for key, value in data.items():
            body = f'|{key:^{indentation}}|{int(value[0]):^{indentation}}|{int(value[1]):^{indentation}}|'
            print(body)

        print(line)

    def percent_get(self, data):
        full = 0
        for value in data.values():
            full += value

        for key, value in data.items():
            percent = int(value * 100 / full)
            data[key] = [value, percent]
