from instagrapi import Client
from db import Session, Reel, ReelEncoder
import json
import config
import time
import auth
import helpers as Helper
from requests.exceptions import RetryError
from helpers import print
import os


#Function to fetch reel from given account
def get_reels(account, api):
    max_retries = 5  # Nombre maximum de tentatives
    retry_delay = 10  # Délai en secondes entre les tentatives

    for attempt in range(max_retries):
        try:
            time.sleep(2)  # Ajoute un délai de 2 secondes entre les requêtes pour éviter de surcharger l'API
            user_id = api.user_id_from_username(account)
            medias = api.user_medias(user_id, config.FETCH_LIMIT)
            reels = [item for item in medias if (item.product_type == 'clips', item.media_type == 2)]  # Filtrer pour les reels
            return reels  # Si la requête réussit, sort de la boucle et retourne les reels
        except RetryError as e:
            if hasattr(e, 'response') and e.response.status_code == 429:
                print(f"Received 429 error, attempt {attempt + 1}/{max_retries}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise e
    raise Exception("Max retries exceeded. Please try again later.")

#Function to get file name from URL
def get_file_name_from_url(url):
    path = url.split('/')
    filename = path[-1]
    return filename.split('?')[0]


#Function to get file path
def get_file_path(file_name):
    return config.DOWNLOAD_DIR + file_name


#Magic Starts Here
def main(api):
    Helper.load_all_config()
    session = Session()
    for account in config.ACCOUNTS:

        reels_by_account = get_reels(account, api)

        for reel in reels_by_account:
            if reel.video_url is not None:
                try:
                    print('------------------------------------------------------------------------------------')
                    print('Checking if reel : ' + reel.code + ' already downloaded')
                    exists = session.query(Reel).filter_by(code=reel.code).first()
                    if not exists:
                        filename = reel.code + ".mp4"  # Renommer avec l'identifiant du reel
                        filepath = get_file_path(filename)
                        
                        print('Downloading Reel From : ' + account + ' | Code : ' + reel.code)
                        downloaded_path = api.video_download_by_url(reel.video_url, folder=config.DOWNLOAD_DIR)
                        os.rename(downloaded_path, filepath)  # Renommer le fichier téléchargé
                        print('Downloaded Reel Code : ' + reel.code + ' | Path : ' + filepath)
                        print('<---------Database Insert Start--------->')

                        reel_db = Reel(
                            post_id=reel.id,
                            code=reel.code,
                            account=account,
                            caption=reel.caption_text,
                            file_name=filename,
                            file_path=filepath,
                            data=json.dumps(reel, cls=ReelEncoder),
                            is_posted=False,
                            # posted_at = NULL
                        )
                        session.add(reel_db)
                        session.commit()
                        
                        print('Inserting Record...')
                        print('<---------Database Insert End--------->')
                    print('------------------------------------------------------------------------------------')
                except Exception as e:
                    print(f"An error occurred: {e}")
                    pass
                
    session.close()
    # time.sleep(int(config.SCRAPER_INTERVAL_IN_MIN)*60)
    # main(api)

# if __name__ == "__main__":
#     api = auth.login()
#     main(api)