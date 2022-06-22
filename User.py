from datetime import datetime

class User:
    objects = {}

    def __init__(self, user_id, link_name="", full_name="", lastvisit=""):
        self.id = user_id
        self.link_name = link_name
        self.full_name = full_name
        self.coins = []
        self.watchlist = []
        self.last_visit = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.objects[user_id] = self

    def __repr__(self):
        return f'{self.id} {self.link_name} {self.full_name}'

    @property
    def v(self):
        res = '\n\t' + repr(self)
        res += f'\n\t{self.coins}'
        for rule in self.watchlist:
            res += f'\n\t\t{rule}'
        return res
