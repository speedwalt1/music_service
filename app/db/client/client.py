import sqlalchemy
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

class MySQLConnection:

    def __init__(self, host, port, user, password, db_name, rebuild_db=False):
        self.host = host
        self.port = port

        self.user = user
        self.password = password
        self.db_name = db_name
        self.rebuild_db = rebuild_db

        self.connection = self.connect()
        session = sessionmaker(
            bind=self.connection.engine,
            autoflush=True,
            enable_baked_queries=False,# два параметра ниже отвечает за актуальность данных в бд для данной сессии
            expire_on_commit=True,
        )
        self.session = session()
        self.inspect = sqlalchemy.inspect(self.connection.engine)

    # odb коннектор к базе данных
    def get_connection(self, db_created=False):
        engine = sqlalchemy.create_engine(
        f'mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name if db_created else ""}'
        )
        return engine.connect()
    def connect(self):
        connection = self.get_connection()
        if self.rebuild_db:
            connection.execute(text(f'DROP DATABASE IF EXISTS {self.db_name}'))
            connection.execute(text(f'CREATE DATABASE {self.db_name}'))
        return self.get_connection(db_created=True)

    def get_request(self,query):
        res = self.connection.execute(text(query))
        return res
