import logging
from User import User
from helpers import to_digit
from datetime import datetime

from configparser import ConfigParser
from pprint import pprint as pp
import psycopg2


logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    datefmt='%d-%b-%y %H:%M:%S'
)

class Db:

    def __init__(self):
        self.check_tables()
        self.fetch_users()

    def config(self, filename='database.ini', section='postgresql'):
        parser = ConfigParser()
        parser.read(filename)
        db = {}
        if parser.has_section(section):
            params = parser.items(section)
            for param in params:
                db[param[0]] = param[1]
        else:
            raise Exception('Section {0} not found in the {1} file'.format(section, filename))
        return db

    def connect(self):
        conn = None
        try:
            params = self.config()
            print('Connection to the PostgreSQL database...')
            conn = psycopg2.connect(**params)
            return conn

        except (Exception, psycopg2.DatabaseError) as error:
            raise error

    def check_tables(self):
        logging.info("db.check_tables()")
        try:
            connection = self.connect()

            cursor = connection.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY NOT NULL,
                    link_name TEXT,
                    full_name TEXT,
                    last_visit TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS coins (
                    id TEXT PRIMARY KEY NOT NULL,
                    name TEXT NOT NULL,
                    code TEXT NOT NULL
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_coins (
                    id SERIAL PRIMARY KEY NOT NULL,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    coin_id TEXT NOT NULL
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_watchlist (
                    id SERIAL PRIMARY KEY NOT NULL,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    coin_id TEXT NOT NULL,
                    start_value TEXT NOT NULL,
                    rule TEXT NOT NULL,
                    watch_value TEXT NOT NULL,
                    from_time TEXT NOT NULL,
                    once TEXT
                )
            ''')

            connection.commit()

        except Exception as e:
            logging.exception("db.check_tables()")

        finally:
            if connection:
                connection.close()

    def fetch_users(self):
        logging.info('db.fetch_users():')
        try:
            connection = self.connect()

            cursor = connection.cursor()

            cursor.execute("SELECT id FROM users")

            while row := cursor.fetchone():
                user_id = row[0]
                cursor_jr = connection.cursor()
                cursor_jr.execute(f"SELECT * FROM users WHERE id = {user_id}")
                if row := cursor_jr.fetchone():
                    id, link_name, full_name, last_visit = row
                    user = User(*row)

                    cursor_jr_jr = connection.cursor()
                    cursor_jr_jr.execute(f"SELECT coin_id FROM user_coins WHERE user_id = {user_id} ORDER BY coin_id")
                    user.coins = [row[0] for row in cursor_jr_jr.fetchall()]

                    cursor_jr_jr.execute(f'''
                                    SELECT coin_id, start_value, rule, watch_value, from_time, once
                                    FROM user_watchlist WHERE user_id = %s
                                    ORDER BY coin_id
                    ''', (user_id,))
                    while row := cursor_jr_jr.fetchone():
                        coin_id, start_value, rule, watch_value, from_time, once = row
                        start_value = to_digit(start_value)
                        if watch_value[0] == '[' and watch_value[-1] == ']':
                            watch_value = watch_value.strip('[]').split(', ')
                            watch_value = [to_digit(value) for value in watch_value]
                        else:
                            watch_value = to_digit(watch_value)
                        row = [coin_id, start_value, rule, watch_value, from_time]
                        if once:
                            row.append(once)
                        user.watchlist.append(row)

                    logging.info(user.v)

        except Exception as e:
            logging.exception("db.fetch_users()")

        finally:
            if connection:
                connection.close()

    def save(self, obj):
        class_name = type(obj).__name__
        if class_name == 'User':
            user = obj
            pp(user)
            try:
                connection = self.connect()

                cursor = connection.cursor()

                cursor.execute(f"SELECT * FROM users WHERE id = {user.id}")
                if not cursor.fetchone():
                    cursor.execute(f'''
                            INSERT INTO users (id, link_name, full_name)
                            VALUES (%s, %s, %s)
                    ''', (user.id, user.link_name, user.full_name))
                else:
                    cursor.execute(f'''
                            UPDATE users SET
                                link_name = %s,
                                full_name = %s
                            WHERE id = %s
                    ''', (user.link_name, user.full_name, user.id))
                connection.commit()

                cursor.execute(f"DELETE FROM user_coins WHERE user_id = {user.id}")
                for coin in user.coins:
                    cursor.execute(f'''
                            INSERT INTO user_coins (user_id, coin_id)
                            VALUES (%s, %s)
                    ''', (user.id, coin))
                connection.commit()

                cursor.execute(f"DELETE FROM user_watchlist WHERE user_id = {user.id}")
                for coin_id, start_value, rule, watch_value, from_time, *once in user.watchlist:
                    once = "" if not once else once[0]
                    cursor.execute(f'''
                            INSERT INTO user_watchlist (user_id, coin_id, start_value, rule, watch_value, from_time, once)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''', (user.id, coin_id, str(start_value), rule, str(watch_value), str(from_time), once))
                connection.commit()

            except Exception as e:
                logging.exception(f"db.save(<{user.id}>)")

            finally:
                if connection:
                    connection.close()

    def check_in(self, user):
        user_id = user.id
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            connection = self.connect()
            cursor = connection.cursor()
            cursor.execute(f"UPDATE users SET last_visit = %s WHERE id = %s", (now, user_id))
            connection.commit()

        except Exception as e:
            logging.exception(f"db.check_in(<{user.id}>)")

        finally:
            if connection:
                connection.close()
