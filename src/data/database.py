import pandas as pd
from pymongo import MongoClient

from data.config import Config

class MongoDBConnection:
    def __init__(self, host='localhost', 
                 port=27017, 
                 username=None, 
                 password=None, 
                 db_name='mydatabase'):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.db_name = db_name
        self.client = None
        self.db = None

    def connect(self):
        if self.username and self.password:
            self.client = MongoClient(f'mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.db_name}')
        else:
            self.client = MongoClient(f'mongodb://{self.host}:{self.port}/')
        self.db = self.client[self.db_name]
        print(f'Connected to MongoDB database: {self.db_name}')

    def close(self):
        if self.client:
            self.client.close()
            print('Connection to MongoDB closed.')

    def get_collection(self, collection_name):
        if not self.db:
            raise Exception('No database connection. Call connect() method first.')
        return self.db[collection_name]

# Function to load data from CSV to MongoDB
def load_csv_to_mongodb(db):
    # Load data from csv
    user_data = pd.read_csv('../data/raw/frappe_dataset.csv', sep="\t")
    item_data = pd.read_csv('../data/raw/meta.csv', sep="\t")

    # Select distinct user and store to db
    users = user_data[['user']].drop_duplicates().reset_index(drop=True)
    user_docs = users.to_dict(orient='record')
    db.users.insert_many(user_docs)

    # Select distict item and store to db
    items = item_data.drop_duplicates().reset_index(drop=True)
    item_docs = items.to_dict(orient='record')
    db.items.insert_many(item_docs)

    # Select distinct of each context type and store to db
    context_columns = ['daytime', 'weekday', 'isweekend', 'homework', 'cost', 'weather', 'country', 'city']
    for column in context_columns:
        context_data = user_data[[column]].drop_duplicates().reset_index(drop=True)
        context_docs = context_data.to_dict(orient='record')
        # save_data = {column : context_docs}
        db[column].insert_many(context_docs)

    # Store interaction to db
    interactions = user_data[['user', 'item', 'cnt', 'daytime', 'weekday', 'isweekend', 'homework', 'cost', 'weather', 'country', 'city']]
    interaction_docs = interactions.to_dict(orient='record')
    db.interactions.insert_many(interaction_docs)


def update_items(db):
    item_data = pd.read_csv('data/raw/meta.csv', sep="\t")
    # item_features = ['item', 'package', 'descriptions','category', 'downloads', 'developer', 'language', 'price', 'rating']
    items = item_data.drop_duplicates().reset_index(drop=True)
    item_docs = items.to_dict(orient='records')
    db.items.drop()
    
    # Insert new documents into 'items' collection
    db.items.insert_many(item_docs)

# Usage example
if __name__ == "__main__":
    mongo_conn = MongoDBConnection(host=Config.MONGO_HOST, 
                                   port=Config.MONGO_PORT, 
                                   db_name=Config.MONGO_DB_NAME)
    mongo_conn.connect()
    db = mongo_conn.db
    # Call the function to load data into MongoDB
    load_csv_to_mongodb(db)
    # update_items(db)
    
    mongo_conn.close()
