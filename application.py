from flask import Flask
from flask_restful import Resource, Api, reqparse, abort, fields, marshal_with

application = Flask(__name__)
application.config.from_object(__name__)
api = Api(application)





class HelloWorld(Resource):
    def get(self):
        return {
            'data': 'Hello world!'
        }

class HelloName(Resource):
    def get(self, name):
        return {
            'data': 'Hello {}'.format(name)
        }

todos = {
    1: {"task": "writte an api endpoint", "summary": "write the code with python"}
}

task_post_arg = reqparse.RequestParser()
task_post_arg.add_argument('task', type=str, help="Task is required!", required=True,)
task_post_arg.add_argument('summary', type=str, help="Summary is required!", required=True,)


task_put_arg = reqparse.RequestParser()
task_put_arg.add_argument('task', type=str,)
task_put_arg.add_argument('summary', type=str,)


ressources_fields = {
    'id': fields.Integer,
    'task': fields.String,
    'summary': fields.String
}

class ToDo(Resource):
    @marshal_with(ressources_fields)
    def get(self, todo_id):
        return todos[todo_id]

    @marshal_with(ressources_fields)
    def post(self, todo_id):
        args = task_post_arg.parse_args()
        if todo_id in todos:
            abort(409, 'Task Id already exists')
        todos[todo_id] = {'task': args["task"], "summary": args["summary"]}
        return todos

    def delete(self, todo_id):
        del todos[todo_id]
        return todos

    @marshal_with(ressources_fields)
    def put(self, todo_id):
        args = task_put_arg.parse_args()
        if todo_id not in todos:
            abort(409, 'Task does not exists')

        if args['task']:
            todos[todo_id]['task'] = args['task']

        if args['summary']:
            todos[todo_id]['summary'] = args['summary']
        return todos[todo_id]



class ToDoList(Resource):
    def get(self):
        return todos


@application.route('/')
def hello():
    return 'Hello, World from kader added complet requirements!'

api.add_resource(HelloWorld, '/helloworld')
api.add_resource(HelloName, '/helloworld/<string:name>')
api.add_resource(ToDo, '/todos/<int:todo_id>')
api.add_resource(ToDoList, '/todos')

if __name__ == '__main__':
    application.run(debug=False)