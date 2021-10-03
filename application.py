from flask import Flask

application = Flask(__name__)


@application.route('/')
def hello():
    return 'Hello, World from kader added complet requirements!'

if __name__ == '__main__':
    application.run(debug=False)