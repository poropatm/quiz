import os

from flask import Flask
from flask_migrate import Migrate

from config import Config
from models import login_manager, db
from views import views_app, admin_app

app = Flask(__name__)
app.config.from_object(Config)
app.config['ENV'] = os.getenv('FLASK_ENV')

# Inicijalizacija ekstenzija
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
migrate = Migrate(app, db)

# Registracija blueprintova
app.register_blueprint(views_app)
app.register_blueprint(admin_app)

if __name__ == '__main__':
    # Pokretanje servera
    app.run(debug=(app.config['ENV'] == 'development'))


def create_app():
    return Flask(__name__)
