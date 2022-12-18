import requests
from datetime import datetime
import json
from progress.bar import Bar
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import urllib.request
import os


class VKLib:
    url = 'https://api.vk.com/method/'

    def __init__(self, token, version='5.131'):
        self.params = {
            'access_token': token,
            'v': version
        }

    def get_photo_urls(self, album='profile', user_id=None, count=5):
        """return list of dict with names, sizes and urls of photos"""
        get_photo_url = self.url + 'photos.get'
        get_photo_params = {
            'album_id': album,
            'extended': 1,
            'owner_id': user_id,
            'count': count
        }
        response = requests.get(get_photo_url, params={**self.params, **get_photo_params}).json()
        photos_params = []
        dict_likes_count = {}
        for i in response['response']['items']:
            if i['likes']['count'] not in dict_likes_count:
                dict_likes_count[i['likes']['count']] = 1
            else:
                dict_likes_count[i['likes']['count']] += 1
        for item_ph in response['response']['items']:
            max_sized = max(item_ph['sizes'], key=(lambda x: x['height']))
            if dict_likes_count[item_ph['likes']['count']] == 1:
                name = str(item_ph['likes']['count']) + '.jpg'
            else:
                name = f"{item_ph['likes']['count']}" \
                       f"({datetime.utcfromtimestamp(item_ph['date']).strftime('%d%m%Y-%H%M%S')}).jpg"
            photos_params.append({'name': name, 'size': max_sized['type'], 'url': max_sized['url']})
        return photos_params


class YaUploader:
    host = 'https://cloud-api.yandex.net:443/'

    def __init__(self, token: str):
        self.token = token

    def get_headers(self):
        return {'Content-Type': 'application/json', 'Authorization': f'OAuth {self.token}'}

    def create_folder(self, folder_name):
        """Create folder on Yandex Disc"""
        uri = 'v1/disk/resources/'
        url = self.host + uri
        params = {'path': f'/{folder_name}'}
        requests.put(url, headers=self.get_headers(), params=params)

    def upload_from_url(self, file_url, file_name, folder_name):
        """Upload file_url as file_name to folder_name"""
        uri = 'v1/disk/resources/upload/'
        url = self.host + uri
        params = {'path': f'/{folder_name}/{file_name}', 'url': file_url}
        response = requests.post(url, headers=self.get_headers(), params=params)
        if response.status_code == 202:
            print(f" Загрузка файла '{file_name}' прошла успешно")


class GDrive:
    def __init__(self):
        self.g_auth = GoogleAuth()
        self.g_auth.LocalWebserverAuth()
        self.drive = GoogleDrive(self.g_auth)

    def upload_file(self, name, directory_id):
        """Upload file with name to folder with directory_id"""
        params = {'title': name, 'parents': [{'id': directory_id}]}
        file_upload = self.drive.CreateFile(params)
        file_upload.SetContentFile(name)
        file_upload.Upload()
        print(f" Загрузка файла '{name}' прошла успешно")

    def create_dir(self, directory_name):
        """Return folder_id by name if not exist create folder"""
        folder_list = (
            self.drive.ListFile({'q': "mimeType='application/vnd.google-apps.folder' and trashed=false"}).GetList())

        title_list = [x['title'] for x in folder_list]
        if directory_name in title_list:
            for folder in folder_list:
                if folder['title'] == directory_name:
                    return folder['id']

        file_metadata = {
            'title': directory_name,
            'mimeType': 'application/vnd.google-apps.folder',
        }
        file0 = self.drive.CreateFile(file_metadata)
        file0.Upload()
        return file0['id']


if __name__ == '__main__':
    access_token = ...
    reader = VKLib(access_token)
    album_id = input("Укажите album_id (по умолчанию 'profile'): ") or 'profile'
    photo_amount = 5
    while True:
        try:
            photo_amount = int(input("Укажите количество загружаемых фотографий (по умолчанию 5): ") or 5)
            if photo_amount < 1:
                print("Введите положительное число")
                continue
            break
        except ValueError:
            print("Введите положительное число")
            continue
    photos_info = reader.get_photo_urls(album_id, count=photo_amount)
    with Bar('Request photos from VK...', max=len(photos_info)) as bar:
        result = []
        for item in photos_info:
            result.append({'file-name': item['name'], 'size': item['size']})
            bar.next()
    with open("result.json", "w") as file:
        json.dump(result, file)

    while (storage := input("Укажите хранилище для загрузки (1 - Яндекс Диск, 2 - Google Drive): ")) not in ('1', '2'):
        print("Введите только номер опции - 1 или 2")

    dir_name = input("Укажите название папки для загрузки (по умолчанию 'FromVK'): ") or 'FromVK'
    if storage == '1':
        yandex_token = ...
        loader = YaUploader(yandex_token)
        loader.create_folder(dir_name)
        with Bar('Loading to Yandex.Disk...', max=len(photos_info)) as bar:
            for photo in photos_info:
                bar.next()
                loader.upload_from_url(photo['url'], photo['name'], dir_name)
    elif storage == '2':
        loader = GDrive()
        dir_id = loader.create_dir(dir_name)
        with Bar('Loading to Google Drive...', max=len(photos_info)) as bar:
            for photo in photos_info:
                bar.next()
                urllib.request.urlretrieve(photo['url'], photo['name'])
                filename = photo['name']
                loader.upload_file(filename, dir_id)
                os.remove(photo['name'])
