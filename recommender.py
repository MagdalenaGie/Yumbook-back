from neo4j import GraphDatabase

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

    def find_restaurants(self, parameter_type, parameter_value):
        with self.driver.session() as session:
            result = session.read_transaction(
                self._find_and_return_restaurants,
                parameter_type,
                parameter_value)
            return {"restaurants": result}

    @staticmethod
    def _find_and_return_restaurants(tx, parameter_type, parameter_value):
        if(parameter_type == "loc"):
            query = (
            """MATCH (restaurant)-[:LOCATED_IN]->(l:Location{name:$parameter_value})
            RETURN restaurant.name AS name"""
            )
        elif(parameter_type == "cui"):
            query = (
                """MATCH (restaurant)-[:SERVES]->(l:Cuisine{name:$parameter_value})
                RETURN restaurant.name AS name"""
            )
        elif(parameter_type == "lik"):
            query = (
                """MATCH (l:Person{name:$parameter_value}) -[:LIKES]->(restaurant)
                RETURN restaurant.name AS name"""
            )
        result = tx.run(query, parameter_value=parameter_value)
        return [record["name"] for record in result]

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