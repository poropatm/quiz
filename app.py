from flask import Flask
from flask_migrate import Migrate

from config import Config
from models import login_manager, db
from views import views_app, admin_app

app = Flask(__name__)
app.config.from_object(Config)


db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
migrate = Migrate(app, db)

app.register_blueprint(views_app)  # Register the Blueprint
app.register_blueprint(admin_app)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
