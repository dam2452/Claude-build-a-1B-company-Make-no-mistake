from flask import Flask

from .database import init_db, close_db


def create_app() -> Flask:
    app = Flask(__name__)
    app.config['DATABASE'] = '/app/blog.db'
    app.config['TEMPLATES_AUTO_RELOAD'] = True

    with app.app_context():
        init_db()

    from .routes import bp
    app.register_blueprint(bp)
    app.teardown_appcontext(close_db)

    return app
