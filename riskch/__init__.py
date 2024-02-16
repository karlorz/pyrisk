import os

from flask import Flask


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",
        API_KEY="dev",
        SOURCE="dev",
        DATABASE=os.path.join(app.instance_path, 'data.sqlite'),
        CSVTMP=os.path.join(app.instance_path, 'trades.csv'),
        DEBUG=True,
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=False )
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!'
    
    # register the database commands
    from riskch import db
    db.init_app(app)

    from riskch import compute
    from riskch import mpool
    from riskch import chart
    
    app.register_blueprint(mpool.bp)
    app.register_blueprint(chart.bp)
    
    app.add_url_rule('/', endpoint='index')
    return app