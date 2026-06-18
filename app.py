from flask import Flask
from src.logic.config import Config
from src.routes.main import main_bp  # dashboard
from src.routes.management import management_bp  # add teacher, class, subject
from src.routes.generation import generation_bp  # generate timetable
from src.routes.timetable import timetable_bp  # view timetable
from src.auth.auth import auth_bp  # login, register

app = Flask(__name__, template_folder='frontend/templates', static_folder='frontend/static')
app.config.from_object(Config)

app.register_blueprint(main_bp)
app.register_blueprint(management_bp)
app.register_blueprint(generation_bp)
app.register_blueprint(timetable_bp)
app.register_blueprint(auth_bp)

if __name__ == '__main__':
    app.run(debug=True)
