import feedparser
from datetime import datetime, timedelta
from raindropio import API, Raindrop
import os
import json
import requests
from requests_oauthlib import OAuth1

# はてなブックマークのRSSフィードからデータを取得する
def get_hatena_bookmarks_of_date():
    # 環境変数からはてなユーザー名を取得
    username = os.environ["HATENA_USERNAME"]
    #前日の日付を計算
    target_date = datetime.now() - timedelta(days=1)
    date_str = target_date.strftime('%Y%m%d')
    
    feed_url = f'https://b.hatena.ne.jp/{username}/rss?date={date_str}'

    feed = feedparser.parse(feed_url)
    bookmarks = []

    for entry in feed.entries:

        # dc:subject には、タグが入っているので、それを取り出す
        subjects = [subject['term'] for subject in entry.get('tags', [])]

        bookmarks.append({
            "title": entry.title,
            "url": entry.link,
            "date": date_str,
            "subjects": subjects,
            "description": entry.get('description', ''),
        })

    return bookmarks

# RainDrop.io にデータを保存する
def post_bookmarks_to_raindropio(bookmarks):
    # Raindrop.ioのAPIトークンを環境変数から取得
    api_token = os.environ["RAINDROP_TOKEN"]
    api = API(api_token)

    # Raindrop.io にコレクションを作成
    for bookmark in bookmarks:
        # タグリストを取得
        tags = bookmark.get('subjects', [])

        # タグリストに '*copy' が含まれている場合、登録処理をスキップ
        if '*copy' in tags:
            print(f"Skipped: {bookmark['title']}")
            continue

        # タグリストに '*copy' タグを追加
        tags.append('*copy')

        # Raindrop.ioにブックマークを投稿
        raindrop = Raindrop.create(
            api,
            link=bookmark['url'],
            title=bookmark['title'],
            tags=tags,
            excerpt=bookmark.get('description', ''),
        )
        print(f"Posted: {raindrop.title}")

# Raindrop.ioからデータを取得する
def get_raindrop_bookmarks_for_last_two_days():
    # Raindrop.ioのAPIトークンを環境変数から取得
    api_token = os.environ["RAINDROP_TOKEN"]
    api = API(api_token)

    # 当日と前日の日付を計算
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    page = 0
    result = []

    while True:
        items = Raindrop.search(api, page=page)

        if not items:
            break

        for item in items:
            # Raindropのcreated_atはUTCでの日付時刻
            item_date = item.created.date()
            item.tags
            if item_date == today or item_date == yesterday:
                result.append({
                    "title": item.title,
                    "url": item.link,
                    "date": item_date.strftime('%Y%m%d'),
                    "subjects": [tag for tag in item.tags],  # Raindropのタグはリストで取得できる
                    "description": item.values['note'] if item.values['note'] else '',
                })
            elif item_date < yesterday:
                return result  # 前日より前の日付の項目が来たらループを抜ける

        page += 1

    return result

# はてなブックマークにデータを保存する
def post_to_hatena_bookmark(bookmarks):
    # はてなブックマークのAPIトークンを環境変数から取得
    consumer_key = os.environ["HATENA_CONSUMER_KEY"]
    consumer_secret = os.environ["HATENA_CONSUMER_SECRET"]
    access_token = os.environ["HATENA_ACCESS_TOKEN"]
    access_token_secret = os.environ["HATENA_ACCESS_TOKEN_SECRET"]
    
    auth = OAuth1(consumer_key, consumer_secret, access_token, access_token_secret)
    bookmark_api_url = "https://bookmark.hatenaapis.com/rest/1/my/bookmark"

    for bookmark in bookmarks:
        #タグに'*copy'が含まれている場合、登録処理をスキップ
        if '*copy' in bookmark.get('subjects', []):
            print(f"Skipped: {bookmark['title']}")
            continue

        params = {'url': bookmark['url']}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        comment_tags = ''.join(['[' + tag + ']' for tag in bookmark.get('subjects', [])]) + '[*copy]'
        comment = comment_tags + '' + bookmark.get('description', '') if comment_tags else bookmark.get('description', '')
        data = {'comment': comment}

        response = requests.post(bookmark_api_url, params=params, auth=auth, headers=headers, data=data)

        if response.status_code == 200:
            print(f"Successfully posted: {bookmark['title']}")
        else:
            print(f"Failed to post: {bookmark['title']} - Status code: {response.status_code}")


# AWS Lambda から呼び出される関数
def lambda_handler(event, context):
    # はてなブックマークのデータを取得
    hatena_bookmarks = get_hatena_bookmarks_of_date()
    # Raindrop.io にデータを保存
    post_bookmarks_to_raindropio(hatena_bookmarks)

    # Raindrop.io からデータを取得
    raindrop_bookmarks = get_raindrop_bookmarks_for_last_two_days()
    # はてなブックマークにデータを保存
    post_to_hatena_bookmark(raindrop_bookmarks)

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
