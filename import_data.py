import argparse
import json
import os
from pathlib import Path

from flask import Flask
from flask_pymongo import PyMongo

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('json', type=Path)

    args = parser.parse_args()

    application = Flask(__name__)
    application.config[
        'MONGO_URI'] = f'mongodb://{os.getenv("DB_HOST", "localhost")}:{os.getenv("DB_PORT", "27017")}/wordalign'
    mongo = PyMongo(application)

    with open(args.json) as f:
        data = json.load(f)

    for file in data:
        mongo.db.files.insert_one(file)
