import praw
import tweepy
import configparser
from requests import get
from pathlib import Path
from gfycat.client import GfycatClient
import imageio
import os
import time
from random import choice
import schedule


config = configparser.ConfigParser()
config.read('conf.ini')
reddit_user = config['REDDIT']['reddit_user']
reddit_pass = config['REDDIT']['reddit_pass']
reddit_client_id = config['REDDIT']['reddit_client_id']
reddit_client_secret = config['REDDIT']['reddit_client_secret']
gfycat_client_id = config['GFYCAT']['gfycat_client_id']
gfycat_client_secret = config['GFYCAT']['gfycat_client_secret']
twitter_consumer_key = config['TWITTER']['consumer_key']
twitter_consumer_secret = config['TWITTER']['consumer_secret']
twitter_access_token = config['TWITTER']['access_token']
twitter_access_token_secret = config['TWITTER']['access_token_secret']
target_subreddits = config['SETTINGS']['target_subreddits']
target_subreddits = [t.strip() for t in config.get(
    'SETTINGS', 'target_subreddits').split(',')]
min_sleep = int(config['SETTINGS']['min_sleep'])
max_sleep = int(config['SETTINGS']['max_sleep'])
allow_nsfw = config['SETTINGS'].getboolean('allow_nsfw')
hashtags = config['SETTINGS'].getboolean('hashtags')
test_mode = config['SETTINGS'].getboolean('test_mode')


reddit = praw.Reddit(
    username=reddit_user,
    password=reddit_pass,
    client_id=reddit_client_id,
    client_secret=reddit_client_secret,
    user_agent='RedTwit (by u/impshum)'
)

auth = tweepy.OAuthHandler(twitter_consumer_key, twitter_consumer_secret)
auth.set_access_token(twitter_access_token, twitter_access_token_secret)
api = tweepy.API(auth, wait_on_rate_limit=True,
                 wait_on_rate_limit_notify=True)

gfycat_client = GfycatClient(gfycat_client_id, gfycat_client_secret)


class C:
    W, G, R, P, Y, C = '\033[0m', '\033[92m', '\033[91m', '\033[95m', '\033[93m', '\033[36m'


class TargetFormat(object):
    GIF = ".gif"
    MP4 = ".mp4"
    AVI = ".avi"


def convertFile(inputpath, targetFormat):
    outputpath = os.path.splitext(inputpath)[0] + targetFormat
    reader = imageio.get_reader(inputpath)
    fps = reader.get_meta_data()['fps']
    writer = imageio.get_writer(outputpath, fps=fps)
    for i, im in enumerate(reader):
        writer.append_data(im)
    writer.close()


def get_img(url):
    if 'v.redd.it' in url:
        vid = get(url).content
        fname = f'data/img.mp4'
        with open(fname, 'wb') as f:
            f.write(vid)
        convertFile(fname, TargetFormat.GIF)
        return fname

    if 'gfycat' in url:
        gfycat_query = url.split('/')[-1].split('-')[0]
        gfycat_response = gfycat_client.query_gfy(gfycat_query)
        url = gfycat_response['gfyItem']['max2mbGif']

    try:
        img = get(url).content
        ext = Path(url).suffix
        fname = f'data/img{ext}'
        with open(fname, 'wb') as f:
            f.write(img)
        return fname
    except Exception as e:
        print(e)


def runner():
    target_subreddit = choice(target_subreddits)
    for submission in reddit.subreddit(target_subreddit).hot(limit=None):
        if not submission.is_self and not submission.saved:
            if submission.over_18 and not allow_nsfw:
                continue
            title = submission.title
            url = submission.url
            saved = submission.saved
            if not saved:
                if 'v.redd.it' in url:
                    url = submission.secure_media['reddit_video']['fallback_url'].replace(
                        '?source=fallback', '')
                fname = get_img(url)
                if fname:
                    if hashtags:
                        tag = ' #{}'.format(target_subreddit.lower())
                        title += tag
                    if not test_mode:
                        api.update_with_media(filename=fname, status=title)

                    now = time.strftime("%d/%m/%y %H:%M")
                    print(f'{C.C}{now} {C.G}Tweeted {title}{C.W}')
                    submission.save()
                    break


def main():
    print(f"""{C.Y}
╦═╗╔═╗╔╦╗╔╦╗╦ ╦╦╔╦╗
╠╦╝║╣  ║║ ║ ║║║║ ║  {C.P}{min_sleep}-{max_sleep} hrs{C.Y}
╩╚═╚═╝═╩╝ ╩ ╚╩╝╩ ╩  {C.C}v1.0 {C.G}impshum{C.W}
    """)
    runner()
    schedule.every(min_sleep).to(max_sleep).hours.do(runner)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    main()
