import os,threading,tls_client
from colorama import Fore
from time import sleep

if os.name == 'nt':
	os.system("cls")
else:
	os.system("clear")

print(f"{Fore.LIGHTBLUE_EX}Twitter Like/Retweet/Comment Boost {Fore.RESET}v5 | ($ffe)\n")

tweet_id = input(f"{Fore.LIGHTBLUE_EX}Post ID (123): {Fore.RESET}")
boost_delay = float(input(f"{Fore.LIGHTBLUE_EX}Delay (0.1): {Fore.RESET}"))

tokens = open("tokens.txt", "r").read().splitlines()
proxy = open("proxies.txt", "r").read()
total_proxy = len(proxy.splitlines())

comment_tokens = open("comment_tokens.txt", "r").read().splitlines()
comment_proxy = open("comment_proxies.txt", "r").read()
boost_comments = open("boost_comments.txt", "r", encoding="utf-8").read().splitlines()

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

def retweet(x, tweet_id):

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

            payload_retweet = {
                'variables': {
                    'tweet_id': tweet_id,
                    'dark_request': False,
                },
                'queryId': 'ojPdsZsimiJrUGLR1sjUtA',
            }

            response = session.post('https://twitter.com/i/api/graphql/ojPdsZsimiJrUGLR1sjUtA/CreateRetweet', cookies=cookies, headers=headers, json=payload_retweet, proxy=proxies_two)
            if response.status_code == 200:
                print(f"{Fore.GREEN}[+] {tokens[x]} retweet{Fore.RESET}")

    except:
        pass

def comment(x, tweet_id):

    try:

        proxies_two = f"http://{comment_proxy.split()[x].split(':')[0]}:{comment_proxy.split()[x].split(':')[1]}@{comment_proxy.split()[x].split(':')[2]}:{comment_proxy.split()[x].split(':')[3]}"

        session = tls_client.Session(client_identifier="chrome_112", random_tls_extension_order=True)

        cookies = {
            'auth_token': comment_tokens[x]
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

            payload_boost_comment = {
                'variables': {
                    'tweet_text': str(boost_comments[x]).replace("\/", "\n"),
                    'reply': {
                        'in_reply_to_tweet_id': tweet_id,
                        'exclude_reply_user_ids': [],
                    },
                    'media': {
                        'media_entities': [],
                        'possibly_sensitive': False,
                    },
                    'withDownvotePerspective': False,
                    'withReactionsMetadata': False,
                    'withReactionsPerspective': False,
                    'withSuperFollowsTweetFields': True,
                    'withSuperFollowsUserFields': True,
                    'semantic_annotation_ids': [],
                    'dark_request': False,
                },
                'features': {
                    'dont_mention_me_view_api_enabled': True,
                    'responsive_web_uc_gql_enabled': True,
                    'vibe_api_enabled': True,
                    'responsive_web_edit_tweet_api_enabled': True,
                    'graphql_is_translatable_rweb_tweet_is_translatable_enabled': False,
                    'interactive_text_enabled': True,
                    'responsive_web_text_conversations_enabled': False,
                    'standardized_nudges_misinfo': True,
                    'tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled': False,
                    'responsive_web_graphql_timeline_navigation_enabled': False,
                    'responsive_web_enhance_cards_enabled': True,
                },
                'queryId': 'kV0jgNRI3ofhHK_G5yhlZg',
            }

            response = session.post('https://twitter.com/i/api/graphql/kV0jgNRI3ofhHK_G5yhlZg/CreateTweet', cookies=cookies, headers=headers, json=payload_boost_comment, proxy=proxies_two)
            if response.status_code == 200:
                print(f"{Fore.GREEN}[+] {comment_tokens[x]} commented{Fore.RESET}")

    except:
        pass

threads_like = []
threads_retweet = []

for x in range(len(tokens)):
    t_like = threading.Thread(target=like, args=(x, tweet_id,))
    t_like.daemon = True
    threads_like.append(t_like)
    t_retweet = threading.Thread(target=retweet, args=(x, tweet_id,))
    t_retweet.daemon = True
    threads_retweet.append(t_retweet)

for x in range(len(tokens)):
    threads_like[x].start()
    threads_retweet[x].start()
    sleep(boost_delay)

for x in range(len(tokens)):
    threads_like[x].join()
    threads_retweet[x].join()

threads_comment_boost = []

for xyz in range(len(comment_tokens)):
    ttt = threading.Thread(target=comment, args=(xyz, tweet_id,))
    ttt.daemon = True
    threads_comment_boost.append(ttt)

for xyz in range(len(comment_tokens)):
    threads_comment_boost[xyz].start()
    sleep(boost_delay)

for xyz in range(len(comment_tokens)):
    threads_comment_boost[xyz].join()

input(f"\n{Fore.BLUE}DONE{Fore.RESET}\n")