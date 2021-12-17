from datetime import timedelta
from flask import Flask, request
from flask_cors import CORS
from neo4j import GraphDatabase
import recommender

uri = "neo4j+s://c26040a7.databases.neo4j.io"
user = "neo4j"
password = "StRixU7CKjzP9lmyQhQe-ezbmk2UmaXC6PsK5Fapcfs"

neo_db = recommender.Recommender(uri, user, password)

def exit_application():
    neo_db.close()

app = Flask(__name__)
app.secret_key = "cii..tajne-haslo!rozdaję ulotki, idz dalej i udawaj ze mnie nie widzisz ;)"
app.permanent_session_lifetime = timedelta(days=5)
CORS(app)

driver = GraphDatabase.driver(uri=uri, auth=(user, password))
driver_session = driver.session()

@app.get('/get-friends')
async def get_friends():
    person = request.args.get('person')
    result = neo_db.find_friend(person)
    return result

@app.get('/get-person')
async def get_person():
    person = request.args.get('person')
    result = neo_db.find_person(person)
    return result

@app.get('/get-restaurants')
async def get_restaurants():
    cuisine = request.args.get('cuisine')
    location = request.args.get('location')
    person = request.args.get('person')
    result = neo_db.find_restaurants(cuisine, location, person)
    print(result)
    return result

@app.get('/get-recommendations')
async def get_recommendations():
    person = request.args.get('person')
    result = neo_db.find_recommendations(person)
    return result

@app.get('/get-best')
async def get_best():
    person_list = request.args.get('person_list')
    location = request.args.get('location')
    cuisine = request.args.get(('cuisine'))
    max = request.args.get(('max'))
    result = neo_db.find_best(cuisine, location, person_list, max)
    return result

@app.get('/get-credentials')
async def get_credentials():
    login = request.args.get('login')
    result = neo_db.login(login)
    return result

@app.post('/like')
async def like_restaurant():
    person = request.form['person']
    restaurant = request.form['restaurant']
    result = neo_db.like_restaurant(person, restaurant)
    return result

@app.post('/dislike')
async def dislike_restaurant():
    person = request.form['person']
    restaurant = request.form['restaurant']
    result = neo_db.dislike_restaurant(person, restaurant)
    return result

@app.post('/create-user')
async def create_user():
    name = request.form['name']
    login = request.form['login']
    password = request.form['password']
    result = neo_db.create_user(name, login, password)
    return result

@app.post('/make-friends')
async def make_friends():
    p1 = request.form['p1']
    p2 = request.form['p2']
    result = neo_db.make_friends(p1, p2)
    return result

@app.post('/delete-friends')
async def delete_friends():
    p1 = request.form['p1']
    p2 = request.form['p2']
    result = neo_db.delete_friends(p1, p2)
    return result


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)


