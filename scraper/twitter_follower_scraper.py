import httpx,os
from colorama import Fore
from random import choice
from x_client_transaction.utils import handle_x_migration
from x_client_transaction import ClientTransaction

if os.name == 'nt':
	os.system("cls")
else:
	os.system("clear")

print(f"{Fore.LIGHTRED_EX}Twitter Follower Scraper {Fore.RESET}v3 ($ffe)\n")

tokens = open("tokens.txt", "r").read().splitlines()

user_id = input(f"{Fore.RED}User ID (https://tweeterid.com/): {Fore.RESET}")
output_type = input(f"{Fore.RED}Output (username/username2/id): {Fore.RESET}")

cookies = {
    'auth_token': choice(tokens)
}

rotate_counter = 1

headers = {
    "Authority": "x.com",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Referer": "https://x.com",
    'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "X-Twitter-Active-User": "yes",
    'x-twitter-auth-type': 'OAuth2Session',
    "X-Twitter-Client-Language": "en"
}

session = httpx.Client(http2=True)
session.headers = headers
response = handle_x_migration(session)

ct = ClientTransaction(response)
transaction_id = ct.generate_transaction_id(method="GET", path="/i/api/graphql/3q_0KSFxJP1ClQ1qYyOCJA/Followers")
headers['x-client-transaction-id'] = transaction_id

ct0_response = session.post('https://twitter.com/i/api/1.1/account/update_profile.json', cookies=cookies, headers=headers)
ct0 = ct0_response.cookies['ct0']
cookies['ct0'] = ct0
headers['x-csrf-token'] = ct0

if ct0_response.status_code != 401:
    valid = session.get('https://x.com/i/api/1.1/users/email_phone_info.json?include_pending_email=true', cookies=cookies, headers=headers)
    if valid.status_code == 200:

        first_payload = {
            'variables': '{"userId":"' + user_id + '","count":20,"includePromotedContent":false,"withSuperFollowsUserFields":false,"withDownvotePerspective":false,"withReactionsMetadata":false,"withReactionsPerspective":false,"withSuperFollowsTweetFields":false}',
            'features': '{"responsive_web_graphql_timeline_navigation_enabled":false,"unified_cards_ad_metadata_container_dynamic_card_content_query_enabled":false,"dont_mention_me_view_api_enabled":false,"responsive_web_uc_gql_enabled":false,"vibe_api_enabled":false,"responsive_web_edit_tweet_api_enabled":false,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":false,"standardized_nudges_misinfo":false,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":false,"interactive_text_enabled":false,"responsive_web_text_conversations_enabled":false,"responsive_web_enhance_cards_enabled":false}',
        }

        first_response = session.get('https://twitter.com/i/api/graphql/3q_0KSFxJP1ClQ1qYyOCJA/Followers', params=first_payload, cookies=cookies, headers=headers).json()

        e_counter = 0
        total_scraped = 0
        while True:
            try:
                for x in first_response['data']['user']['result']['timeline']['timeline']['instructions'][e_counter]['entries']:
                    if output_type == "username":
                        scraped_username = x['content']['itemContent']['user_results']['result']['legacy']['screen_name']
                        if scraped_username not in open("scraped.txt", "r").read():
                            save = open("scraped.txt", "a")
                            save.write(f"{scraped_username}\n")
                            save.close()
                        total_scraped += 1
                    elif output_type == "username2":
                        scraped_username = x['content']['itemContent']['user_results']['result']['legacy']['screen_name']
                        if scraped_username not in open("scraped.txt", "r").read():
                            save = open("scraped.txt", "a")
                            save.write(f"@{scraped_username}\n")
                            save.close()
                        total_scraped += 1
                    else:
                        scraped_rest_id = x['content']['itemContent']['user_results']['result']['rest_id']
                        if scraped_rest_id not in open("scraped.txt", "r").read():
                            save = open("scraped.txt", "a")
                            save.write(f"{scraped_rest_id}\n")
                            save.close()
                        total_scraped += 1
            except Exception as err:
                e_counter += 1
                if e_counter >= 100:
                    print(f"\n{Fore.GREEN}[+] Total scraped: {total_scraped}{Fore.RESET}")
                    break
                pass

        cursor = 0
        cursor_counter = 0

        while True:

            try:
                find_cursor = first_response['data']['user']['result']['timeline']['timeline']['instructions'][cursor_counter]['entries'][cursor]['content']['value']
                first_value = str(find_cursor).split("|")[0]
                second_value = str(find_cursor).split("|")[1]
                break
            except:
                cursor += 1
                if cursor >= 100:
                    cursor_counter += 1
                    cursor = 0
                pass

        xx = 0

        while True:

            try:

                ct = ClientTransaction(response)
                transaction_id = ct.generate_transaction_id(method="GET", path="/i/api/graphql/3q_0KSFxJP1ClQ1qYyOCJA/Followers")
                headers['x-client-transaction-id'] = transaction_id

                second_payload = {
                    'variables': '{"userId":"' + user_id + '","count":20,"cursor":"' + f"{first_value}|{second_value}" + '","includePromotedContent":false,"withSuperFollowsUserFields":false,"withDownvotePerspective":false,"withReactionsMetadata":false,"withReactionsPerspective":false,"withSuperFollowsTweetFields":false}',
                    'features': '{"responsive_web_graphql_timeline_navigation_enabled":false,"unified_cards_ad_metadata_container_dynamic_card_content_query_enabled":false,"dont_mention_me_view_api_enabled":false,"responsive_web_uc_gql_enabled":false,"vibe_api_enabled":false,"responsive_web_edit_tweet_api_enabled":false,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":false,"standardized_nudges_misinfo":false,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":false,"interactive_text_enabled":false,"responsive_web_text_conversations_enabled":false,"responsive_web_enhance_cards_enabled":false}',
                }

                second_response = session.get('https://twitter.com/i/api/graphql/3q_0KSFxJP1ClQ1qYyOCJA/Followers', params=second_payload, cookies=cookies, headers=headers)

                for x in second_response.json()['data']['user']['result']['timeline']['timeline']['instructions'][0]['entries']:
                    try:
                        if output_type == "username":
                            scraped_username = x['content']['itemContent']['user_results']['result']['legacy']['screen_name']
                            if scraped_username not in open("scraped.txt", "r").read():
                                save = open("scraped.txt", "a")
                                save.write(f"{scraped_username}\n")
                                save.close()
                            total_scraped += 1
                        elif output_type == "username2":
                            scraped_username = x['content']['itemContent']['user_results']['result']['legacy']['screen_name']
                            if scraped_username not in open("scraped.txt", "r").read():
                                save = open("scraped.txt", "a")
                                save.write(f"@{scraped_username}\n")
                                save.close()
                            total_scraped += 1
                        else:
                            scraped_rest_id = x['content']['itemContent']['user_results']['result']['rest_id']
                            if scraped_rest_id not in open("scraped.txt", "r").read():
                                save = open("scraped.txt", "a")
                                save.write(f"{scraped_rest_id}\n")
                                save.close()
                            total_scraped += 1
                    except Exception as err:
                        try:
                            new_value = str(x['content']['value'])
                            if new_value[0] != "-":
                                first_value = str(new_value).split("|")[0]
                                second_value = str(new_value).split("|")[1]
                        except:
                                pass
                        pass

                print(f"\n{Fore.GREEN}[+] Total scraped: {total_scraped}{Fore.RESET}")

            except:

                cookies['auth_token'] = tokens[rotate_counter]
                ct0_response = session.post('https://twitter.com/i/api/1.1/account/update_profile.json', cookies=cookies, headers=headers)
                ct0 = ct0_response.cookies['ct0']
                cookies['ct0'] = ct0
                headers['x-csrf-token'] = ct0

                print(f"\n{Fore.YELLOW}[+] Switching token: {tokens[rotate_counter]}{Fore.RESET}")

                if rotate_counter >= len(tokens)-1:
                    rotate_counter = 0
                else:
                    rotate_counter += 1