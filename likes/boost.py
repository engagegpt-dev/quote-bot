import os,threading,tls_client
from colorama import Fore
from time import sleep

if os.name == 'nt':
	os.system("cls")
else:
	os.system("clear")

print(f"{Fore.LIGHTBLUE_EX}Twitter Like/Bookmark Boost {Fore.RESET}v6 | ($ffe)\n")

tweet_id = input(f"{Fore.LIGHTBLUE_EX}Post ID (123): {Fore.RESET}")
boost_delay = float(input(f"{Fore.LIGHTBLUE_EX}Delay (0.2): {Fore.RESET}"))

tokens = open("tokens.txt", "r").read().splitlines()
proxy = open("proxies.txt", "r").read()
total_proxy = len(proxy.splitlines())

print(f"{Fore.YELLOW}\n[!] Loaded {len(tokens)} tokens.{Fore.RESET}\n")

def like(x, tweet_id):

    try:

        proxies_two = f"http://{proxy.split()[x].split(':')[0]}:{proxy.split()[x].split(':')[1]}@{proxy.split()[x].split(':')[2]}:{proxy.split()[x].split(':')[3]}"

        session = tls_client.Session(client_identifier="chrome_112", random_tls_extension_order=True)

        cookies = {
            'auth_token': tokens[x]
        }

        headers = {
            'authority': 'twitter.com',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            'origin': 'https://twitter.com',
            'referer': 'https://twitter.com/home',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5024.121 Safari/537.36',
            'x-twitter-active-user': 'yes',
            'x-twitter-auth-type': 'OAuth2Session',
            'x-twitter-client-language': 'en'
        }

        ct0_response = session.post('https://twitter.com/i/api/1.1/account/update_profile.json', cookies=cookies, headers=headers, proxy=proxies_two)
        ct0 = ct0_response.cookies['ct0']
        cookies['ct0'] = ct0
        headers['x-csrf-token'] = ct0

        payload_like = {
            'variables': {
                'tweet_id': tweet_id,
            },
            'queryId': 'lI07N6Otwv1PhnEgXILM7A',
        }

        response = session.post('https://twitter.com/i/api/graphql/lI07N6Otwv1PhnEgXILM7A/FavoriteTweet', cookies=cookies, headers=headers, json=payload_like, proxy=proxies_two)
        if response.status_code == 200:
            print(f"{Fore.GREEN}[+] {tokens[x]} like{Fore.RESET}")

    except:
        pass

def bookmark(x, tweet_id):

    try:

        proxies_two = f"http://{proxy.split()[x].split(':')[0]}:{proxy.split()[x].split(':')[1]}@{proxy.split()[x].split(':')[2]}:{proxy.split()[x].split(':')[3]}"

        session = tls_client.Session(client_identifier="chrome_112", random_tls_extension_order=True)

        cookies = {
            'auth_token': tokens[x]
        }

        headers = {
            'authority': 'twitter.com',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            'origin': 'https://twitter.com',
            'referer': 'https://twitter.com/home',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5024.121 Safari/537.36',
            'x-twitter-active-user': 'yes',
            'x-twitter-auth-type': 'OAuth2Session',
            'x-twitter-client-language': 'en'
        }

        ct0_response = session.post('https://twitter.com/i/api/1.1/account/update_profile.json', cookies=cookies, headers=headers, proxy=proxies_two)
        ct0 = ct0_response.cookies['ct0']
        cookies['ct0'] = ct0
        headers['x-csrf-token'] = ct0

        if ct0_response.status_code != 401:

            payload_bookmark = {
                'variables': {
                    'tweet_id': tweet_id,
                },
                'queryId': 'aoDbu3RHznuiSkQ9aNM67Q',
            }

            response = session.post('https://twitter.com/i/api/graphql/aoDbu3RHznuiSkQ9aNM67Q/CreateBookmark', cookies=cookies, headers=headers, json=payload_bookmark, proxy=proxies_two)
            if response.status_code == 200:
                print(f"{Fore.GREEN}[+] {tokens[x]} bookmark{Fore.RESET}")

    except:
        pass

threads_like = []
threads_bookmark = []

for x in range(len(tokens)):
    t_like = threading.Thread(target=like, args=(x, tweet_id,))
    t_like.daemon = True
    threads_like.append(t_like)
    t_bookmark = threading.Thread(target=bookmark, args=(x, tweet_id,))
    t_bookmark.daemon = True
    threads_bookmark.append(t_bookmark)

for x in range(len(tokens)):
    threads_like[x].start()
    threads_bookmark[x].start()
    sleep(boost_delay)

for x in range(len(tokens)):
    threads_like[x].join()
    threads_bookmark[x].join()

input(f"\n{Fore.BLUE}DONE{Fore.RESET}\n")