import os
import random
import string
import time
import datetime
import sqlite3
import json
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from flaskext.bcrypt import Bcrypt
from contextlib import closing

DEBUG = os.environ["ELIDE_DEBUG"]
SECRET_KEY = os.environ["ELIDE_SECRET_KEY"]
DATABASE = os.environ["ELIDE_DATABASE"]
SCHEMA = os.environ["ELIDE_SCHEMA"]

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config.from_object(__name__)

def connect_db():
    return sqlite3.connect(DATABASE)

def init_db():
    with closing(connect_db()) as db:
        with open(SCHEMA, mode='r') as f:
            db.cursor().executescript(f.read())
            db.commit()

@app.before_request
def before_request():
    g.prev_url = request.referrer
    g.date = str(datetime.datetime.fromtimestamp(time.time()))
    g.browser = request.user_agent.browser

@app.route('/', methods=['GET', 'POST'])
def main():
    if request.method == 'POST':
        url = request.form['url']
        if not valid_url(url):
            flash("invalid url")
            return redirect('/')
        user = get_user(session)
        short_url = in_db(user, url=url)
        if short_url is None:
            short_url = shorten(url, user)
            add_to_db(url, short_url, user)
        base_url = url_for("main", _external=True)
        clicks = get_clicks(short_url)
        return render_template('index.html', full_url=base_url+short_url, short_url=short_url, clicks=clicks)
    return render_template('index.html', short_url=None, clicks=None)

def get_user(session):
    if 'logged_in' in session:
        user = session['username']
    else:
        user = 'public'
    return user

@app.route('/display')
def display():
    return redirect('/display/' + get_user(session))

@app.route('/display/<user>')
def display_user(user):
    base_url = url_for("main", _external=True)
    with closing(connect_db()) as db:
        query = db.execute("SELECT url, short_url, clicks FROM urls WHERE user=?", (user,))
        entries = [(url, base_url + short_url, clicks) for url, short_url, clicks  in query.fetchall()]
    return render_template('display.html', urls=entries)

@app.route('/<short_url>')
def go_to_short_url(short_url):
    url = get_url(short_url)
    if url:
        update_clicks(short_url, g.prev_url, g.date, g.browser)
        if not (url.startswith('http://') or url.startswith('https://')):
            url = 'http://' + url
        return redirect(url)
    else:
        return render_template('invalid_url.html', url=short_url)

@app.route('/clicks')
def clicks():
    short_url = request.args.get("short_url")
    click_data = {"numClicks": get_clicks(short_url), "clickData": get_click_data(short_url)}
    return json.dumps(click_data)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        if username in get_usernames():
            pw_hash = get_password(username)
            if bcrypt.check_password_hash(pw_hash, request.form['password']):
                session['username'] = username
                session['logged_in'] = True
                flash('You were logged in')
                return redirect('/')
            else:
                error = 'Incorrect password'
        else:
            error = 'Invalid username'

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect('/')

@app.route('/create_account', methods=['GET', 'POST'])
def create_user():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_confirm = request.form['password_confirm']
        if password != password_confirm:
            error = "Passwords don't match"
        elif username in get_usernames():
            error = "Username already in use. Please choose another."
        else:
            pw_hash = bcrypt.generate_password_hash(password)
            add_user(username, pw_hash)
            flash('Account created')
            return redirect('login')

    return render_template('create_account.html', error=error)

def shorten(url, user):
    """shorten given url and return value if not already used"""
    s = string.letters+string.digits
    short_url = "".join(random.choice(s) for i in range(5))
    return short_url if not in_db(user, short_url=short_url) else shorten(url, user)

def update_clicks(short_url, prev_url, date, browser):
    """increment clicks each time url is accessed"""
    with closing(connect_db()) as db:
        db.execute('UPDATE urls SET clicks=clicks+1 where short_url=?', (short_url,))
        urlid = db.execute("SELECT id from urls where short_url=?", (short_url,)).fetchone()[0]
        db.execute('INSERT INTO clicks (urlid, previousurl, date, browser) VALUES (?,?,?,?)', \
                   (urlid, prev_url, date, browser))
        db.commit()

def get_clicks(short_url):
    """return number of clicks for given short url"""
    with closing(connect_db()) as db:
        query = db.execute("SELECT clicks FROM urls WHERE short_url=?", (short_url,))
        clicks = query.fetchone()
        return clicks[0] if clicks else None

def get_click_data(short_url):
    """return previous url, date, and browser data for clicks on a given short url"""
    with closing(connect_db()) as db:
        id = db.execute("SELECT id FROM urls WHERE short_url=?", (short_url,)).fetchone()[0]
        query = db.execute("SELECT previousurl, date, browser FROM clicks WHERE urlid=?", (id,))
        click_data = {i: dict(prev_url=u, date=d, browser=b) for i, (u, d, b) in enumerate(query.fetchall())}
        return click_data

def in_db(user, url=None, short_url=None):
    """given url return short_url if url in the database, given short_url return url if in database or return None if not in database """
    if url is not None:
        q = "SELECT short_url FROM urls WHERE url=? and user=?"
        i = url
    elif short_url is not None:
        q = "SELECT url FROM urls WHERE short_url=? and user=?"
        i = short_url
    else:
        return
    with closing(connect_db()) as db:
        try:
            query = db.execute(q, (i, user))
            entry = query.fetchone()
            if entry:
                return entry[0]
            else:
                return None
        except:
            return None

def get_url(short_url):
    """given short_url return url"""
    with closing(connect_db()) as db:
        query = db.execute("SELECT url FROM urls WHERE short_url=?", (short_url,))
        data = query.fetchone()
        return data[0] if data else None

def add_to_db(url, short_url, user):
    """add new entry for given url, short_url, and user to database"""
    with closing(connect_db()) as db:
        if in_db(user, url=url):
            return
        db.execute("INSERT INTO urls (url, short_url, clicks, user) VALUES (?, ?, ?, ?)", (url, short_url, 0, user))
        db.commit()

def valid_url(url):
    if not (url.startswith('http://') or url.startswith('https://')):
        url = 'http://' + url
    try:
        r = requests.head(url).status_code
    except:
        return False
    else:
        return r >= 200 and r < 400

def add_user(username, pw_hash):
    with closing(connect_db()) as db:
        db.execute("INSERT INTO users (username, pw_hash) VALUES (?,?)", (username, pw_hash))
        db.commit()

def get_usernames():
    with closing(connect_db()) as db:
        entries = db.execute("SELECT username from users")
        return [entry[0] for entry in entries.fetchall()]

def get_password(username):
    with closing(connect_db()) as db:
        entries = db.execute("SELECT pw_hash FROM users WHERE username=?", \
                              (username,))
        return entries.fetchone()[0]

if __name__ == '__main__':
    init_db()
    app.run()
