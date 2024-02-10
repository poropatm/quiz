import os

from flask.cli import load_dotenv

load_dotenv()

STATIC_FOLDER = 'static'
IMAGES_FOLDER = 'images'


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(os.getcwd(), STATIC_FOLDER, IMAGES_FOLDER)

