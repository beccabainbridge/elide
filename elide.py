import os
import random
import string
import time
import datetime
import json
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from flaskext.bcrypt import Bcrypt
import access_database as db

DEBUG = os.environ["ELIDE_DEBUG"]
SECRET_KEY = os.environ["ELIDE_SECRET_KEY"]

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config.from_object(__name__)

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
        short_url = db.get_short_url(url, user)
        if short_url is None:
            short_url = shorten(url, user)
            db.add_to_db(url, short_url, user)
        base_url = url_for('main', _external=True)
        clicks = db.get_clicks(short_url)
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
    if user != get_user(session):
        return render_template('access_denied.html')
    base_url = url_for("main", _external=True)
    urls = db.get_user_urls(user, base_url)
    return render_template('display.html', urls=urls)

@app.route('/<short_url>')
def go_to_short_url(short_url):
    url = db.get_url(short_url, get_user(session))
    if url:
        db.update_clicks(short_url, g.prev_url, g.date, g.browser)
        if not (url.startswith('http://') or url.startswith('https://')):
            url = 'https://' + url
        return redirect(url)
    else:
        return render_template('invalid_url.html', url=short_url)

@app.route('/clicks')
def clicks():
    short_url = request.args.get("short_url")
    click_data = {"shortUrl": short_url, "numClicks": db.get_clicks(short_url), "clickData": db.get_click_data(short_url)}
    return json.dumps(click_data)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        if username in db.get_usernames():
            pw_hash = db.get_password(username)
            if bcrypt.check_password_hash(pw_hash, request.form['password']):
                session['username'] = username
                session['logged_in'] = True
                flash("You were logged in")
                return redirect('/')
            else:
                error = "Incorrect password"
        else:
            error = "Invalid username"

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash("You were logged out")
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
        elif username in db.get_usernames():
            error = "Username already in use. Please choose another."
        else:
            pw_hash = bcrypt.generate_password_hash(password)
            db.add_user(username, pw_hash)
            flash("Account created")
            return redirect('login')

    return render_template('create_account.html', error=error)

def shorten(url, user):
    """shorten given url and return value if not already used"""
    s = string.letters+string.digits
    short_url = "".join(random.choice(s) for i in range(5))
    return short_url if not db.get_url(short_url, user) else shorten(url, user)

def valid_url(url):
    """access url and return True if valid otherwise return False"""
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url
    try:
        r = requests.head(url).status_code
    except:
        return False
    else:
        return r >= 200 and r < 400

if __name__ == '__main__':
    db.init_db()
    app.run()
