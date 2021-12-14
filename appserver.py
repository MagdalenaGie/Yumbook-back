from fastapi import FastAPI, Request
import recommender
import atexit

uri = "neo4j+s://c26040a7.databases.neo4j.io"
user = "neo4j"
password = "StRixU7CKjzP9lmyQhQe-ezbmk2UmaXC6PsK5Fapcfs"

neo_db = recommender.Recommender(uri, user, password)

def exit_application():
    neo_db.close()

atexit.register(exit_application)

app = FastAPI()

@app.get('/get-friends/{person}')
async def get_friends(person):
    result = neo_db.find_friend(person)
    return result

@app.get('/get-restaurants')
async def get_restaurants(param='', value=''):
    result = neo_db.find_restaurants(param, value)
    return result

@app.get('/get-rcommendations')
async def get_recommendations(person=''):
    result = neo_db.find_recommendations(person)
    return result

@app.get('/get-credentials')
async def get_credentials(login=''):
    result = neo_db.login(login)
    return result

@app.post('/like/{person}/{restaurant}')
async def like_restaurant(person, restaurant):
    result = neo_db.like_restaurant(person, restaurant)
    return result

@app.post('/dislike/{person}/{restaurant}')
async def like_restaurant(person, restaurant):
    result = neo_db.dislike_restaurant(person, restaurant)
    return result

@app.post('/create-user')
async def like_restaurant(request: Request):
    body = await request.json()
    result = neo_db.create_user(body['name'], body['login'], body['password'])
    return result

@app.post('/make-friends/{p1}/{p2}')
async def like_restaurant(p1, p2):
    result = neo_db.make_friends(p1, p2)
    return result

@app.post('/delete-friends/{p1}/{p2}')
async def like_restaurant(p1, p2):
    result = neo_db.delete_friends(p1, p2)
    return result


