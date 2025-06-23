import threading
import requests
import argparse
from flask import Flask, request, abort
from sqlalchemy.testing.config import db_url

from app.db.error.exception import UserNotFoundException
from app.db.interaction.interaction import DbInteraction
from utils import get_config


class Server:
    def __init__(self, host, port, db_host, db_port, db_user, db_password, db_name, rebuild_db=False):
        self.host = host
        self.port = port
        self.db_interaction = DbInteraction(
            host=db_host,
            port=db_port,
            password=db_password,
            db_name=db_name,
            user=db_user,
            rebuild_db=rebuild_db,
        )

        self.app = Flask(__name__)

        # Добавим Endpoint для выключения сервера
        self.app.add_url_rule('/shutdown', view_func=self.shut_down)

        # Добавим домашний endpoint /home
        self.app.add_url_rule('/home', view_func=self.get_home)
        self.app.add_url_rule('/', view_func=self.get_home)

        # Endpoints для пользователей
        self.app.add_url_rule('/add_user_info', view_func=self.add_user_info, methods=['POST'])
        self.app.add_url_rule('/get_user_info/<username>', view_func=self.get_user_info, methods=['GET'])
        self.app.add_url_rule('/edit_user_info', view_func=self.edit_user_info, methods=['PUT'])
        self.app.add_url_rule('/delete_user/<username>', view_func=self.delete_user, methods=['DELETE'])

        # Endpoints для треков
        self.app.add_url_rule('/add_track', view_func=self.add_track, methods=['POST'])
        self.app.add_url_rule('/get_track/<int:track_id>', view_func=self.get_track, methods=['GET'])
        self.app.add_url_rule('/get_user_tracks/<username>', view_func=self.get_user_tracks, methods=['GET'])
        self.app.add_url_rule('/delete_track/<int:track_id>', view_func=self.delete_track, methods=['DELETE'])
        self.app.add_url_rule('/edit_track/<int:track_id>', view_func=self.edit_track, methods=['PUT'])

        # Добавим 404 ошибку
        self.app.register_error_handler(404, self.page_not_found)

    def page_not_found(self, err_description):
        return jsonify(error=str(err_description)), 404

    def run_server(self):
        self.server = threading.Thread(target=self.app.run, kwargs={'host': self.host, 'port': self.port})
        self.server.start()
        return self.server

    def get_home(self):
        return 'Music App API - Hello world'

    def add_user_info(self):
        request_body = dict(request.json)
        try:
            user_info = self.db_interaction.add_user(
                username=request_body['username'],
                email=request_body['email'],
                password=request_body['password']
            )
            return jsonify(user_info), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    def get_user_info(self, username):
        try:
            user_info = self.db_interaction.get_user_info(username=username)
            return jsonify(user_info), 200
        except UserNotFoundException:
            abort(404, description='UserNotFound')

    def edit_user_info(self):
        request_body = dict(request.json)
        try:
            user_info = self.db_interaction.edit_user_info(
                username=request_body.get('username', None),
                new_username=request_body.get('new_username', None),
                email=request_body.get('email', None),
                password=request_body.get('password', None)
            )
            return jsonify(user_info), 200
        except UserNotFoundException:
            abort(404, description='UserNotFound')
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    def delete_user(self, username):
        """Удаление пользователя"""
        try:
            result = self.db_interaction.delete_user(username)
            return jsonify({
                'message': 'User deleted successfully',
                'deleted_user': result['deleted_user'],
                'deleted_compositions_count': result['deleted_compositions_count']
            }), 200
        except UserNotFoundException:
            abort(404, description='UserNotFound')
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    def add_track(self):
        """Добавление нового трека"""
        request_body = dict(request.json)
        try:
            track_info = self.db_interaction.add_musical_composition(
                username=request_body['username'],
                title=request_body['title'],
                artist=request_body.get('artist', None),
                url=request_body.get('url', None)
            )
            return jsonify(track_info), 201
        except UserNotFoundException:
            abort(404, description='UserNotFound')
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    def get_track(self, track_id):
        """Получение информации о треке по ID"""
        try:
            track_info = self.db_interaction.get_musical_composition_info(track_id)
            return jsonify(track_info), 200
        except TrackNotFoundException:
            abort(404, description='TrackNotFound')
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    def get_user_tracks(self, username):
        """Получение всех треков пользователя"""
        try:
            tracks = self.db_interaction.get_user_musical_compositions(username)
            return jsonify({'tracks': tracks}), 200
        except UserNotFoundException:
            abort(404, description='UserNotFound')
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    def delete_track(self, track_id):
        """Удаление трека"""
        request_body = dict(request.json)
        try:
            deleted_track = self.db_interaction.delete_musical_composition(
                composition_id=track_id,
                username=request_body['username']
            )
            return jsonify({'message': 'Track deleted successfully', 'deleted_track': deleted_track}), 200
        except (UserNotFoundException, TrackNotFoundException) as e:
            abort(404, description=str(e))
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    def edit_track(self, track_id):
        """Редактирование трека"""
        request_body = dict(request.json)
        try:
            track_info = self.db_interaction.edit_musical_composition(
                composition_id=track_id,
                username=request_body['username'],
                title=request_body.get('title', None),
                artist=request_body.get('artist', None),
                url=request_body.get('url', None)
            )
            return jsonify(track_info), 200
        except (UserNotFoundException, TrackNotFoundException) as e:
            abort(404, description=str(e))
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    def shutdown_server(self):
        request.get(f'http://{self.host}:{self.port}/shutdown')

    def shut_down(self):
        terminate_func = request.environ.get('werkzeug.server.shutdown')
        if terminate_func:
            terminate_func()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, dest='config')
    args = parser.parse_args()
    config = get_config(args.config)

    server = Server(
        host=config['SERVER_HOST'],
        port=int(config['SERVER_PORT']),
        db_name=config['DB_NAME'],
        db_user=config['DB_USER'],
        db_host=config['DB_HOST'],
        db_port=config['DB_PORT'],
        db_password=config['DB_USER_PASS'],
    )
    server.run_server()