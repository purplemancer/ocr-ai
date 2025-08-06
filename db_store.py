from conf_parse import supabase_api_key, supabase_url,statutory_files_storage
from supabase import create_client, Client

def save_file(file, file_name: str):
    url = supabase_url
    key = supabase_api_key
    # Create a Supabase client
    bucket_name = statutory_files_storage
    supabase: Client = create_client(url, key)
   
    try:
        # Upload file to Supabase bucket
        response = supabase.storage.from_(bucket_name).upload(file_name, file)
        print(response)
        if response:
            print(f"File uploaded successfully to {bucket_name}")
        else:
            print(f"Error uploading file")
            
    except Exception as e:
        print(f"An error occurred: {e}")