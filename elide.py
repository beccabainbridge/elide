import os
import random
import string
import sqlite3
import json
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session
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

@app.route('/', methods=['GET', 'POST'])
def main():
    if request.method == 'POST':
        url = request.form['url']
        if not valid_url(url):
            flash("invalid url")
            return redirect('/')
        short_url = in_db(url)
        if short_url is None:
            short_url = shorten(url)
            add_to_db(url, short_url)
        base_url = url_for("main", _external=True)
        clicks = get_clicks(short_url)
        return render_template('index.html', full_url=base_url+short_url, short_url=short_url, clicks=clicks)
    return render_template('index.html', short_url=None, clicks=None)

@app.route('/display')
def display():
    base_url = url_for("main", _external=True)
    with closing(connect_db()) as db:
        query = db.execute("SELECT url, short_url, clicks FROM urls")
        entries = [(url, base_url + short_url, clicks) for url, short_url, clicks  in query.fetchall()]
    return render_template('display.html', urls=entries)

@app.route('/<short_url>')
def go_to_short_url(short_url):
    url = get_url(short_url)
    update_clicks(url)
    if url:
        if not (url.startswith('http://') or url.startswith('https://')):
            url = 'http://' + url
        return redirect(url)
    else:
        return render_template('invalid_url.html', url=short_url)

@app.route('/clicks')
def clicks():
    click_data = {"numClicks": get_clicks(request.args.get("short_url"))}
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

def shorten(url):
    """shorten given url and return value"""
    s = string.letters+string.digits
    short_url = "".join(random.choice(s) for i in range(5))
    return short_url if not in_db(short_url) else shorten(url)

def update_clicks(url):
    """increment clicks each time url is accessed"""
    with closing(connect_db()) as db:
        db.execute('UPDATE urls SET clicks=clicks+1 where url=?', (url,))
        db.commit()

def get_clicks(url):
    """return number of clicks for given url"""
    with closing(connect_db()) as db:
        query = db.execute("SELECT clicks FROM urls WHERE short_url=?", (url,))
        return query.fetchone()[0]

def in_db(url=None, short_url=None):
    """given url return short_url if url in the database, given short_url return url if in database or return None if not in database """
    if url is not None:
        q = "SELECT short_url FROM urls WHERE url=?"
        i = url
    elif short_url is not None:
        q = "SELECT url FROM urls WHERE short_url=?"
        i = short_url
    else:
        return
    with closing(connect_db()) as db:
        try:
            query = db.execute(q, (i,))
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
        return query.fetchone()[0]

def add_to_db(url, short_url):
    """add new entry for given url and short_url to database"""
    with closing(connect_db()) as db:
        if in_db(url):
            return
        db.execute("INSERT INTO urls (url, short_url, clicks) VALUES (?, ?, ?)", (url, short_url, 0))
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
