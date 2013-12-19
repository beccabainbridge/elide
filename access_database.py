import os
import db_queries as db

DATABASE = os.environ["ELIDE_DATABASE"]
SCHEMA = os.environ["ELIDE_SCHEMA"]

def init_db():
    db.init_db(DATABASE, SCHEMA)

def add_to_db(url, short_url, user):
    """add new entry for given url, short_url, and user to database"""
    if get_short_url(url, user):
        return
    query = "INSERT INTO urls (url, short_url, clicks, user) VALUES (?, ?, ?, ?)"
    db.insert(DATABASE, query, (url, short_url, 0, user))

def get_user_urls(user, base_url):
    """return urls for given user"""
    entries = db.select_from_db(DATABASE, items=['url', 'short_url', 'clicks'],
                                table='urls', where={'user':user}, get_first=False)
    urls = [(url, base_url + short_url, short_url, clicks) for url, short_url, clicks  in entries]
    return urls

def get_url(short_url, user):
    """return url for given short url"""
    return db.select_from_db(DATABASE, items=['url'], table='urls',
                             where={'short_url':short_url,'user':user})

def get_short_url(url, user):
    """return short_url for given url"""
    return db.select_from_db(DATABASE, items=['short_url'], table='urls',
                             where={'url':url,'user':user})

def get_usernames():
    """return all usernames"""
    entries =  db.select_from_db(DATABASE, items=['username'], table='users',
                             get_first=False)
    return [entry[0] for entry in entries]

def get_password(username):
    """return password hash for given username"""
    return db.select_from_db(DATABASE, items=['pw_hash'], table='users',
                             where={'username':username})

def add_user(username, pw_hash):
    """add new user to db with given username and password hash"""
    query = "INSERT INTO users (username, pw_hash) VALUES (?,?)"
    db.insert(DATABASE, query, (username, pw_hash))

def update_clicks(short_url, prev_url, date, browser):
    """increment clicks each time url is accessed"""
    update_query = "UPDATE urls SET clicks=clicks+1 WHERE short_url=?"
    db.update(DATABASE, update_query, (short_url,))
    url_id = get_id(short_url)
    insert_query = "INSERT INTO clicks (urlid, previousurl, date, browser) VALUES (?,?,?,?)"
    db.insert(DATABASE, insert_query, (url_id, prev_url, date, browser))

def get_click_data(short_url):
    """return previous url, date, and browser data for clicks on a given short url"""
    url_id = get_id(short_url)
    click_entries = db.select_from_db(DATABASE, items=['previousurl, date, browser'],
                                      table='clicks', where={'urlid':url_id}, get_first=False)
    click_data = {i: dict(prev_url=u, date=d, browser=b) for i, (u, d, b) in enumerate(click_entries)}
    return click_data

def get_clicks(short_url):
    """return number of clicks for given short url"""
    return db.select_from_db(DATABASE, items=['clicks'], table='urls',
                             where={'short_url':short_url})

def get_id(short_url):
    """return id for given short_url"""
    return db.select_from_db(DATABASE, items=['id'], table='urls',
                             where={'short_url':short_url})
