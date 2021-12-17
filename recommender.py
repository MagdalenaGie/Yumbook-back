from flask import logging, jsonify
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable


class Recommender:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def find_friend(self, person_name):
        with self.driver.session() as session:
            result = session.read_transaction(self._find_and_return_friend, person_name)
            return {"friends": result}

    @staticmethod
    def _find_and_return_friend(tx, person_name):
        query = (
            "MATCH (p:Person {name: $person_name})-[:IS_FRIEND_OF]-(friend) "
            "RETURN friend.name AS name"
        )
        result = tx.run(query, person_name=person_name)
        return [record["name"] for record in result]

    def find_person(self, person_name):
        with self.driver.session() as session:
            result = session.read_transaction(self._find_and_return_person, person_name)
            return {"person": result}

    @staticmethod
    def _find_and_return_person(tx, person_name):
        query = (
            """MATCH (p:Person), (per:Person {name: $person_name}) 
            WHERE NOT (p)-[:IS_FRIEND_OF]->(per) 
            AND NOT (per)-[:IS_FRIEND_OF]->(p) 
            AND NOT p.name = $person_name RETURN p.name AS name"""
        )
        result = tx.run(query, person_name=person_name)
        return [record["name"] for record in result]

    def find_restaurants(self, cuisine, location, person):
        with self.driver.session() as session:
            result = session.read_transaction(
                self._find_and_return_restaurants,
                cuisine,
                location,
                person)
            return {"restaurants": result}

    @staticmethod
    def _find_and_return_restaurants(tx, cuisine, location, person):
        cuisine_string = "(cuisine)" if cuisine == '' else "(cuisine:Cuisine {name: $cuisine})"
        location_string = "(location)" if location == '' else "(location:Location {name: $location})"
        person_string = "(person)" if person == '' else "(person:Person {name: $person})"

        query = '''MATCH (restaurant:Restaurant)-[:LOCATED_IN]->{location_string},
                    (restaurant)-[:SERVES]->{cuisine_string},
                    {person_string}-[:LIKES]->(restaurant)
                    WITH restaurant.name AS name, cuisine.name AS cuisine, location.name AS location, collect(person.name) AS likers
                    RETURN name, cuisine, location, likers'''.format(location_string=location_string, cuisine_string=cuisine_string, person_string=person_string)

        result = tx.run(query, cuisine=cuisine, location=location, person=person)
        try:
            return [{"restaurant": row["name"], "cuisine": row["cuisine"], "location": row["location"], "likers": row["likers"]} for row in result]
        except ServiceUnavailable as exception:
            logging.error("{query} raised an error: \n {exception}".format(query=query, exception=exception))
            raise

    def find_recommendations(self, person):
        with self.driver.session() as session:
            result = session.read_transaction(
                self._find_recommendations,
                person
                )
            return {"recommendations": result}

    @staticmethod
    def _find_recommendations(tx, person):
        query = (
            """MATCH (p:Person {name:$person})-[:IS_FRIEND_OF]->(friend),
            (friend)-[:LIKES]->(restaurant)
            WHERE NOT (p)-[:LIKES]->(restaurant)
            RETURN restaurant.name AS restaurantName, 
            collect(friend.name) AS reccomendedBy, 
            count(*) AS numberOfRecommendations 
            ORDER BY numberOfRecommendations DESC"""
        )
        result = tx.run(query, person=person)
        records = []
        for el in result:
            records.append({
                'name': el['restaurantName'],
                'recommenders': el['reccomendedBy'],
                'count': el['numberOfRecommendations']
            })

        return records


    def find_best(self, cuisine_name, location_name, person_list, max):
        with self.driver.session() as session:
            result = session.read_transaction(self._find_best, cuisine_name, location_name, person_list, max)
            return result

    @staticmethod
    def _find_best(tx, cuisine_name, location_name, person_list, max):
        # simple hack to generalized and parameterized functions into one
        cuisine_string = "(cuisine)" if cuisine_name == '' else "(cuisine:Cuisine {name: $cuisine_name})"
        location_string = "(location)" if location_name == '' else "(location:Location {name: $location_name})"
        person_string = "" if len(person_list) == 0 else "WHERE person.name IN %s" % (str(person_list))

        # if True, return only the restaurants with the highest number of likes by friends
        if (max):
            query = (
                '''MATCH (restaurant:Restaurant)-[:LOCATED_IN]->{location},
                      (restaurant)-[:SERVES]->{cuisine},
                      (person:Person)-[:LIKES]->(restaurant)
                {person}
                WITH restaurant.name AS name, collect(person.name) AS likers, COUNT(*) AS occurence
                WITH MAX(occurence) as max_count
                MATCH (restaurant:Restaurant)-[:LOCATED_IN]->{location},
                    (restaurant)-[:SERVES]->{cuisine},
                    (person:Person)-[:LIKES]->(restaurant)
                {person}
                    WITH restaurant.name AS name, collect(person.name) AS likers, COUNT(*) AS occurence, max_count
                    WHERE occurence = max_count
                    RETURN name, likers, occurence'''.format(location=location_string, cuisine=cuisine_string,
                                                             person=person_string)
                )
        else:
            query = (
                    '''MATCH (restaurant:Restaurant)-[:LOCATED_IN]->%s,
                            (restaurant)-[:SERVES]->%s,
                            (person:Person)-[:LIKES]->(restaurant)
                    %s
                    RETURN restaurant.name AS name, collect(person.name) AS likers, COUNT(*) AS occurence
                    ORDER BY occurence DESC''' % (location_string, cuisine_string, person_string)
            )

        result = tx.run(query, cuisine_name=cuisine_name, location_name=location_name, person_list=person_list)
        try:
            return jsonify([{"restaurant": row["name"], "likers": row["likers"], "occurence": row["occurence"]} for row in result])
        except ServiceUnavailable as exception:
            logging.error("{query} raised an error: \n {exception}".format(query=query, exception=exception))
            raise



    def like_restaurant(self, person_name, restaurant_name):
        with self.driver.session() as session:
            session.write_transaction(
                self._delete_relation_person_restaurant,
                False,
                person_name,
                restaurant_name)
            result = session.write_transaction(
                self._create_relation_person_restaurant,
                True,
                person_name,
                restaurant_name)
            return result

    def dislike_restaurant(self, person_name, restaurant_name):
        with self.driver.session() as session:
            session.write_transaction(
                self._delete_relation_person_restaurant,
                True,
                person_name,
                restaurant_name)
            result = session.write_transaction(
                self._create_relation_person_restaurant,
                False,
                person_name,
                restaurant_name)
            return result

    @staticmethod
    def _create_relation_person_restaurant(tx, like, person_name, restaurant_name):
        if(like):
            query = (
            """MATCH (p:Person), (r:Restaurant)
            WHERE p.name=$person_name AND r.name=$restaurant_name
            CREATE (p)-[:LIKES]->(r)"""
            )
        else:
            query = (
            """MATCH (p:Person), (r:Restaurant)
            WHERE p.name=$person_name AND r.name=$restaurant_name
            CREATE (p)-[:DISLIKES]->(r)"""
            )
        result = tx.run(query, person_name=person_name, restaurant_name=restaurant_name)
        return result

    @staticmethod
    def _delete_relation_person_restaurant(tx, like, person_name, restaurant_name):
        # SHOULD ADD LOGIC TO PREVENT FORM CREATING BOTH LIKE AND DISLAKE REACTION AT THE SAME MOMENT!
        if (like):
            query = (
                """OPTIONAL MATCH (p: Person)-[rel:LIKES]->(r:Restaurant) 
                WHERE p.name=$person_name AND r.name=$restaurant_name
                DELETE rel"""
            )
        else:
            query = (
                """OPTIONAL MATCH (p: Person)-[rel:DISLIKES]->(r:Restaurant) 
                WHERE p.name=$person_name AND r.name=$restaurant_name
                DELETE rel"""
            )
        result = tx.run(query, person_name=person_name, restaurant_name=restaurant_name)
        return result

    def create_user(self, name, login, passw):
        with self.driver.session() as session:
            result = session.write_transaction(
                self._create_node_person,
                name,
                login,
                passw)
            return result

    @staticmethod
    def _create_node_person(tx, name, login, passw):
        query = (
            """CREATE (p:Person {name:$name, login:$login, password:$password})"""
        )
        result = tx.run(query, name=name, login=login, password=passw)
        return result

    def make_friends(self, name1, name2):
        with self.driver.session() as session:
            result = session.write_transaction(
                self._create_or_delete_relation_person_person,
                True,
                name1,
                name2)
            return result

    def delete_friends(self, name1, name2):
        with self.driver.session() as session:
            result = session.write_transaction(
                self._create_or_delete_relation_person_person,
                False,
                name1,
                name2)
            return result

    @staticmethod
    def _create_or_delete_relation_person_person(tx, create, name1, name2):
        if create:
            query = (
                """MATCH (p:Person), (r:Person)
                WHERE p.name=$name1 AND r.name=$name2
                CREATE (p)-[:IS_FRIEND_OF]->(r)"""
            )
        else:
            query = (
                """MATCH (p:Person), (r:Person)
                WHERE p.name=$name1 AND r.name=$name2
                DELETE (p)-[:IS_FRIEND_OF]->(r)"""
            )
        result = tx.run(query, name1=name1, name2=name2)
        return result

    def login(self, login):
        with self.driver.session() as session:
            result = session.read_transaction(
                self._check_password,
                login)
            return {"password": result}

    @staticmethod
    def _check_password(tx, login):
        query = (
            """OPTIONAL MATCH (p:Person{login:$login}) RETURN p.password AS password"""
        )
        result = tx.run(query, login=login)
        return [record["password"] for record in result]

# for testing purpose, can be commented out
if __name__ == "__main__":
    uri = "neo4j+s://c26040a7.databases.neo4j.io"
    user = "neo4j"
    password = "StRixU7CKjzP9lmyQhQe-ezbmk2UmaXC6PsK5Fapcfs"

    app = Recommender(uri, user, password)
    app.close()