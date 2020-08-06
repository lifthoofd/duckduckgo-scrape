import sys
import os
import requests
import argparse
import re
import shutil
from datetime import datetime
from bs4 import BeautifulSoup
from tqdm import tqdm


class DuckDuckGoImageSearch:
    def __init__(self, query, amount):
        self.query = query
        self.amount = amount
        self.vqd = self._get_vqd(self.query)

    @staticmethod
    def _get_vqd(query):
        url = f'https://duckduckgo.com/?q={query}&iar=images&iaf=size%3ALarge&iax=images&ia=images'
        headers = {'User-Agent': "Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.27 Safari/537.17"}
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print('failed trying to get vqd.. exiting now')
            sys.exit()

        soup = BeautifulSoup(response.content, 'html.parser')
        script = soup.find('head').find('script')
        pattern = re.compile("(\w+)='(.*?)'")
        fields = dict(re.findall(pattern, script.text))
        return fields['vqd']

    def get_results(self, s):
        url = f'https://duckduckgo.com/i.js?q={self.query}&o=json&p=-1&s={s}&u=bing&f=size:Large,,,&l=nl-nl&vqd={self.vqd}&v7exp=a&sltexp=a'
        response = requests.get(url)
        if response.status_code == 200:
            print('request returned results')
            return response.json()['results']
        else:
            print('request returned with status code: {}'.format(response.status_code))
            return None


class ImageDownloader:
    def __init__(self, path):
        self.path = self._make_path(path)
        self.idx = 0

    def download(self, url, sub_path):
        path = self._validate_path(os.path.join(self.path, sub_path))

        file = None
        try:
            file = requests.get(url, timeout=120)
        except requests.exceptions.RequestException as e:
            print("downloading failed with error: \n{}".format(e))

        if file is not None:
            if 'Content-Type' in file.headers:
                file_name = self._get_file_name(file.headers['Content-Type'], self.idx)
            else:
                file_name = None

            if file_name is not None:
                file_size = len(file.content)
                file_path = os.path.join(path, file_name)
                pbar = tqdm(total=file_size, mininterval=0.01, miniters=1, unit='B', unit_scale=True, desc="downloading image from url: {}".format(url))
                with open(file_path, 'wb') as fd:
                    for chunk in file.iter_content(chunk_size=128):
                        fd.write(chunk)
                        pbar.update(128)
                pbar.close()

                self.idx += 1
                print("saved file as: {}".format(file_path))

                return True
            else:
                return False
        else:
            return False

    def reset_count(self):
        self.idx = 0

    @staticmethod
    def _get_file_name(content_type, idx):
        dt = '{0:%Y%m%d_%H%M%S}'.format(datetime.now())
        if content_type == 'image/jpeg':
            return f'{idx}_{dt}.jpg'
        elif content_type == 'image/png':
            return f'{idx}_{dt}.png'
        else:
            return None

    @staticmethod
    def _validate_path(path):
        if not os.path.isdir(path):
            os.makedirs(path)

        return path

    @staticmethod
    def _make_path(path):
        if os.path.isdir(path):
            shutil.rmtree(path)

        os.makedirs(path)
        return path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='DuckDuckGo Image Scraper')
    parser.add_argument('--query', nargs='+', type=str, required=True, help='sets the search query, can be more then one query, usage: --query test1 test2')
    parser.add_argument('--amount', type=int, default=1000, help='sets the amount of images, use multiples of 100')
    parser.add_argument('--outdir', type=str, default='./images', help='sets the output directory, if the directory is not found it will be made')

    args = parser.parse_args()
    img_downloader = ImageDownloader(args.outdir)
    for query in args.query:
        ddgis = DuckDuckGoImageSearch(query, args.amount)
        img_downloader.reset_count()
        for s in range(0, args.amount, 100):
            results = ddgis.get_results(s)
            for result in results:
                img_url = result['image']
                img_downloader.download(img_url, query)


