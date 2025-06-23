from app.db.models.models import Base, User, MusicalComposition
from app.db.client.client import MySQLConnection
from app.db.error.exception import UserNotFoundException, DataIsNotValid, TrackNotFoundException


class DbInteraction:
    def __init__(self, host, port, user, password, db_name, rebuild_db=False):
        self.mysql_connection = MySQLConnection(
            host=host,
            port=port,
            user=user,
            password=password,
            db_name=db_name,
            rebuild_db=rebuild_db
        )

        self.engine = self.mysql_connection.connection.engine
        if rebuild_db:
            self.create_table_users()
            self.create_table_musical_compositions()

    def create_table_users(self):
        if not self.mysql_connection.inspect.has_table('users'):
            Base.metadata.tables['users'].create(self.engine)#создание таблицы users
        else:
            self.mysql_connection.get_request('DROP TABLE IF EXISTS users')#удаление таблицы
            Base.metadata.tables['users'].create(self.engine)   #создание таблицы

    def create_table_musical_compositions(self):
        if not self.mysql_connection.inspect.has_table('musical_compositions'):
            Base.metadata.tables['musical_compositions'].create(self.engine)
        else:
            self.mysql_connection.get_request('DROP TABLE IF EXISTS musical_compositions')
            Base.metadata.tables['musical_compositions'].create(self.engine)
        #Добавление пользователя в базу данных
    def add_user(self, username, email,password):
        #создание объекта пользователя c помощью созданной модели в файле models
        user = User(
            username=username,
            email=email,
            password=password,
        )
        #Добавление нашего пользователя в базу данных
        self.mysql_connection.session.add(user)
        return self.get_user_info(user)
     #Получение информации о пользователе
    def get_user_info(self, username):
        #Ищем пользователя
        user = self.mysql_connection.session.query(User).filter_by(username=username).first()
        #Если найден генерируем информацию о пользователе в словарь
        if user:
            self.mysql_connection.session.expire_all()
            return {'username':user.username, 'email':user.email, 'password':user.password}
        else:
            #Если пользователь не найден то выкидываем созданную ошибку в файле error
            raise UserNotFoundException('User not found')

    def edit_user_info(self, username, new_username=None, email=None, password=None):
        user = self.mysql_connection.session.query(User).filter_by(username=username).first()
        if user:
            if new_username is not None and len(new_username)<=50:
                user.username = new_username
            if password is not None and len(new_username)<=300:
                user.password = password
            if email is not None and len(new_username)<=50:
                user.email = email
            else:
                raise DataIsNotValid("Data is not Valid")
            return self.get_user_info(username if username is None else new_username)
        else:
            raise UserNotFoundException('User not found')

    def delete_user(self, username):
        """Удаление пользователя и всех его музыкальных композиций"""
        user = self.mysql_connection.session.query(User).filter_by(username=username).first()
        if user:
            # Сохраняем информацию о пользователе для возврата
            user_info = {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }

            # Удаляем все музыкальные композиции пользователя
            compositions = self.mysql_connection.session.query(MusicalComposition).filter_by(user_id=user.id).all()
            deleted_compositions_count = len(compositions)

            for composition in compositions:
                self.mysql_connection.session.delete(composition)

            # Удаляем пользователя
            self.mysql_connection.session.delete(user)
            self.mysql_connection.session.commit()

            return {
                'deleted_user': user_info,
                'deleted_compositions_count': deleted_compositions_count
            }
        else:
            raise UserNotFoundException('User not found')

        # МЕТОДЫ ДЛЯ РАБОТЫ С МУЗЫКАЛЬНЫМИ КОМПОЗИЦИЯМИ

    def add_musical_composition(self, username, title, artist=None, url=None):
        """Добавление музыкальной композиции для пользователя"""
        # Сначала найдем пользователя
        user = self.mysql_connection.session.query(User).filter_by(username=username).first()
        if not user:
            raise UserNotFoundException('User not found')

        # Создаем новую композицию
        composition = MusicalComposition(
            user_id=user.id,
            title=title,
            artist=artist,
            url=url
        )

        # Добавляем в базу данных
        self.mysql_connection.session.add(composition)
        self.mysql_connection.session.commit()

        return self.get_musical_composition_info(composition.id)

    def get_musical_composition_info(self, composition_id):
        """Получение информации о музыкальной композиции по ID"""
        composition = self.mysql_connection.session.query(MusicalComposition).filter_by(id=composition_id).first()
        if composition:
            self.mysql_connection.session.expire_all()
            return {
                'id': composition.id,
                'user_id': composition.user_id,
                'title': composition.title,
                'artist': composition.artist,
                'url': composition.url,
                'username': composition.user.username
            }
        else:
            raise TrackNotFoundException('Musical composition not found')

    def get_user_musical_compositions(self, username):
        """Получение всех музыкальных композиций пользователя"""
        user = self.mysql_connection.session.query(User).filter_by(username=username).first()
        if not user:
            raise UserNotFoundException('User not found')

        compositions = self.mysql_connection.session.query(MusicalComposition).filter_by(user_id=user.id).all()
        result = []
        for composition in compositions:
            result.append({
                'id': composition.id,
                'title': composition.title,
                'artist': composition.artist,
                'url': composition.url
            })

        self.mysql_connection.session.expire_all()
        return result

    def delete_musical_composition(self, composition_id, username):
        """Удаление музыкальной композиции (только владелец может удалить)"""
        # Найдем пользователя
        user = self.mysql_connection.session.query(User).filter_by(username=username).first()
        if not user:
            raise UserNotFoundException('User not found')

        # Найдем композицию
        composition = self.mysql_connection.session.query(MusicalComposition).filter_by(
            id=composition_id,
            user_id=user.id
        ).first()

        if not composition:
            raise TrackNotFoundException('Musical composition not found or you do not have permission to delete it')

        # Сохраним информацию о композиции для возврата
        composition_info = {
            'id': composition.id,
            'title': composition.title,
            'artist': composition.artist,
            'url': composition.url
        }

        # Удаляем композицию
        self.mysql_connection.session.delete(composition)
        self.mysql_connection.session.commit()

        return composition_info

    def edit_musical_composition(self, composition_id, username, title=None, artist=None, url=None):
        """Редактирование музыкальной композиции"""
        # Найдем пользователя
        user = self.mysql_connection.session.query(User).filter_by(username=username).first()
        if not user:
            raise UserNotFoundException('User not found')

        # Найдем композицию
        composition = self.mysql_connection.session.query(MusicalComposition).filter_by(
            id=composition_id,
            user_id=user.id
        ).first()

        if not composition:
            raise TrackNotFoundException('Musical composition not found or you do not have permission to edit it')

        # Обновляем поля
        if title is not None and len(title) <= 200:
            composition.title = title
        if artist is not None and len(artist) <= 200:
            composition.artist = artist
        if url is not None and len(url) <= 100:
            composition.url = url

        self.mysql_connection.session.commit()

        return self.get_musical_composition_info(composition_id)




