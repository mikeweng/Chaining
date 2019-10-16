import requests
import os
import sys
from json.decoder import JSONDecodeError
from collections import defaultdict


class Stat(object):

    def __init__(self):
        self._http_200 = 0
        self._http_err = 0  # non-http 200
        self._prev_num_total = 0

        self._secrets = set()              # Unique Secrets seen till this point
        self._secrets_bucket = defaultdict(int)         # Each checkpoint generates a new bucket
        self._secrets_historic_bucket = []              # Historic checkpoints

    def process_resp(self, resp_code, secret):
        self._secrets.add(secret)       # Add to seen list

        self._secrets_bucket[secret] += 1
        if resp_code == 200:
            self._http_200 += 1
        else:
            self._http_err += 1

    def checkpoint(self):
        total = self._http_200 + self._http_err
        checkpoint_size = total - self._prev_num_total
        os.system('clear')
        print(f"""
Fetch Checkpoint Stats

Total Requests: {total}
> Success (200) Requests: {round(self._http_200 * 100 /total, 2)}%
> Failure (non-200) Requests: {round(self._http_err * 100 /total, 2)}%  

Current Sample Bucket: {self._prev_num_total} ~ {total}

Secrets Seen: {','.join(self._secrets)}
-----------------------------""")
        for k in self._secrets:
            perct = self._secrets_bucket.get(k, 0) * 100 / checkpoint_size
            print('\t', k, perct, '%')

        self._prev_num_total = total
        self._secrets_historic_bucket.append(self._secrets_bucket)
        self._secrets_bucket = defaultdict(int)


def fetch(stat, url):
    if not url.startswith('http'):
        url = f'http://{url}'

    try:
        resp = requests.get(
            url,
            headers={'X-Chain-Fmt': 'json'},
            timeout=2
        )
        r_json = resp.json()
        secret = r_json.get('service_secret', 'n/a')
        resp_code = resp.status_code
    except requests.exceptions.Timeout:
        secret = 'connection_timeout'
        resp_code = 408
    except JSONDecodeError:
        # Upstream error
        secret = 'connection_error'
        resp_code = 503

    stat.process_resp(resp_code, secret)


def forever(url):
    count = 0
    stat = Stat()
    try:
        while True:
            count += 1
            fetch(stat, url)
            if count % 50 == 0:
                stat.checkpoint()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python fetch.py {URL}")
        sys.exit(0)
    forever(sys.argv[1])
