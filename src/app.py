from flask import Flask, request, render_template, jsonify 
from pymongo import MongoClient
from data.config import Config
from data.database import MongoDBConnection
from service.recommendations import RecommendationService  # Adjust import based on your project structure

app = Flask(__name__, template_folder='ui/templates', static_folder='ui/static')

connection = MongoDBConnection(host=Config.MONGO_HOST, 
                       port=Config.MONGO_PORT, 
                       db_name=Config.MONGO_DB_NAME)
connection.connect()
db = connection.db


@app.route('/recommend', methods=['POST'])
def recommend():
    user_id = request.form.get('userId')
    context = [
        {'type': 'daytime', 'value': request.form.get('daytime')},
        {'type': 'weekday', 'value': request.form.get('weekday')},
        {'type': 'isweekend', 'value': request.form.get('isweekend')},
        {'type': 'homework', 'value': request.form.get('homework')},
        # {'type': 'cost', 'value': request.form.get('cost')},
        {'type': 'weather', 'value': request.form.get('weather')},
        {'type': 'country', 'value': request.form.get('country')},
        {'type': 'city', 'value': int(request.form.get('city'))}
    ]
    rs = RecommendationService(db)

    recommendations = rs.get_recommendations(user_id, context)
    return render_template('recommend.html', items = recommendations)


@app.route('/', methods=['GET'])
def index():

    context_fields = ['daytime', 'weekday', 'isweekend', 'homework', 'cost', 'weather', 'country', 'city']
    context_data = {}
    for field in context_fields:
        context_data[field] = []
        field_data = list(db[field].find())
        for data in field_data:
            # print(data)
            context_data[field].append(data.get(field))
        # context_data[field] = list(db[field].find())
    return render_template('index.html', data=context_data)


if __name__ == '__main__':
    app.run(debug=True)
