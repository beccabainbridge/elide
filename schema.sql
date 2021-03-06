create table if not exists urls (
id integer primary key autoincrement,
url text not null,
short_url text not null,
clicks integer not null,
user text not null
);
create table if not exists clicks (
id integer primary key autoincrement,
urlid integer not null,
previousurl text,
date text,
browser text
);
create table if not exists users (
username text primary key not null,
pw_hash text not null
);
