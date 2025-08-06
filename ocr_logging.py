from psycopg2 import connect

DB_PARAMS = {
        'dbname'    :'ocr_log',
        'user'      :'postgres',
        'password'  :'IncSolRe',
        'host'      :'192.168.1.28',
        'port'      :'9232'
        }

def connect_db():
    return connect(**DB_PARAMS)

def log_response(   ip_address, start_time, end_time,
                    duration, method_type, api_url, 
                    status_code, response_body, input_token_count, 
                    output_token_count, ai_cost, ocr_time, 
                    ai_time, file_bin):
    
    with connect_db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(f'''INSERT INTO log (ip_address, start_time, end_time, duration, method_type, api_url, status_code, response_body, input_token_count, output_token_count, ai_cost, ocr_time, ai_time, file_bin)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
    (ip_address, start_time, end_time, duration, method_type, api_url, status_code, response_body, input_token_count, output_token_count, ai_cost, ocr_time, ai_time, file_bin))

