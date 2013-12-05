import os
import sqlite3
import random, string
from flask import Flask, render_template, request, redirect, url_for, flash
from contextlib import closing

DEBUG = os.environ["ELIDE_DEBUG"]
SECRET_KEY = os.environ["ELIDE_SECRET_KEY"]
DATABASE = os.environ["ELIDE_DATABASE"]

app = Flask(__name__)
app.config.from_object(__name__)

def connect_db():
    return sqlite3.connect(DATABASE)

@app.route('/', methods=['GET', 'POST'])
def main():
    if request.method == 'POST':
        url = request.form['url']
        if not url:
            flash("invalid url")
            return redirect('/')
        short_url = in_db(url)
        if short_url is None:
            short_url = shorten(url)
            add_to_db(url, short_url)
        base_url = url_for("main", _external=True)
        clicks = get_clicks(url)
        return render_template('index.html', short_url=base_url+short_url, clicks=clicks)
    return render_template('index.html', short_url=None, clicks=None)

@app.route('/display')
def display():
    base_url = url_for("main", _external=True)
    with closing(connect_db()) as db:
        query = db.execute("SELECT url, short_url FROM urls")
        entries = [(url, base_url + short_url) for url, short_url  in query.fetchall()]
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
        query = db.execute("SELECT clicks FROM urls WHERE url=?", (url,))
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
        try:
            query = db.execute("SELECT url FROM urls WHERE short_url=?", (short_url,))
            return query.fetchone()[0]
        except sqlite3.OperationalError:
            return None

def add_to_db(url, short_url):
    """add new entry for given url and short_url to database"""
    with closing(connect_db()) as db:
        try:
            if in_db(url):
                return
            db.execute("INSERT INTO urls (url, short_url, clicks) VALUES (?, ?, ?)", (url, short_url, 0))
        except sqlite3.OperationalError:
            db.execute("CREATE TABLE urls(url, short_url, clicks)")
            db.execute("INSERT INTO urls (url, short_url, clicks) VALUES (?, ?, ?)", (url, short_url, 0))
        db.commit()

if __name__ == '__main__':
    app.run()
