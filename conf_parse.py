import configparser

config = configparser.ConfigParser()

config.read('config.ini')

PADDLEOCR_URL = config.get('app', 'paddleocr_url')
api_key = config.get('app', 'api_key')
model_name = config.get('app', 'model_name')
supabase_url = config.get('app','supabase_url')
supabase_api_key = config.get('app','supabase_api_key')
statutory_files_storage = config.get('app','statutory_files_storage')