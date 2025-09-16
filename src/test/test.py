import os
import sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.data_importer import DataImporter,json_file_path
from db.config import SQLALCHEMY_DATABASE_URI
if __name__ == "__main__":
    importer = DataImporter(SQLALCHEMY_DATABASE_URI)
    importer.import_from_json(json_file_path)