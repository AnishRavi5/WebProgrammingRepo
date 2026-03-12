from flask import Flask, redirect, request, url_for
from flask import Response

import requests

from flask import request
from flask import Flask, render_template

from jinja2 import Template
import secrets

import base64
import json
import os

from flask import session

app = Flask(__name__)

app.secret_key = secrets.token_hex()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, ForeignKey, String

from logging.config import dictConfig

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    },
        'file.handler': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'weatherportal.log',
            'maxBytes': 10000000,
            'backupCount': 5,
            'level': 'DEBUG',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['file.handler']
    }
})

# SQLite Database creation
Base = declarative_base()
engine = create_engine("sqlite:///weatherportal.db", echo=True, future=True)
DBSession = sessionmaker(bind=engine)


@app.before_first_request
def create_tables():
    Base.metadata.create_all(engine)


# ─────────────────────────────────────────────
# ORM Table Definitions
# ─────────────────────────────────────────────

class Admin(Base):
    __tablename__ = 'admin'
    id       = Column(Integer, primary_key=True, autoincrement=True)
    name     = Column(String)
    password = Column(String)

    def __repr__(self):
        return "<Admin(name='%s')>" % (self.name)

    def as_dict(self):
        fields = {}
        for c in self.__table__.columns:
            fields[c.name] = getattr(self, c.name)
        return fields


class User(Base):
    __tablename__ = 'user'
    id       = Column(Integer, primary_key=True, autoincrement=True)
    name     = Column(String)
    password = Column(String)

    def __repr__(self):
        return "<User(name='%s')>" % (self.name)

    def as_dict(self):
        fields = {}
        for c in self.__table__.columns:
            fields[c.name] = getattr(self, c.name)
        return fields


class City(Base):
    __tablename__ = 'city'
    id      = Column(Integer, primary_key=True, autoincrement=True)
    adminId = Column(Integer, ForeignKey('admin.id'))
    name    = Column(String)
    url     = Column(String)

    def __repr__(self):
        return "<City(name='%s')>" % (self.name)

    def as_dict(self):
        return {
            'id':      self.id,
            'adminid': self.adminId,
            'name':    self.name,
            'url':     self.url
        }


class UserCity(Base):
    __tablename__ = 'usercity'
    id             = Column(Integer, primary_key=True, autoincrement=True)
    userId         = Column(Integer, ForeignKey('user.id'))
    cityId         = Column(Integer, ForeignKey('city.id'))
    month          = Column(String)
    year           = Column(String)
    weather_params = Column(String)

    def __repr__(self):
        return "<UserCity(userId='%s', cityId='%s')>" % (self.userId, self.cityId)

    def as_dict(self):
        return {
            'id':             self.id,
            'cityId':         self.cityId,
            'userId':         self.userId,
            'month':          self.month,
            'year':           self.year,
            'weather_params': self.weather_params
        }


# ─────────────────────────────────────────────
# Admin REST API
# ─────────────────────────────────────────────

@app.route("/admin", methods=['POST'])
def add_admin():
    app.logger.info("Inside add_admin")
    data = request.json
    app.logger.info("Received request:%s", str(data))
    name     = data['name']
    password = data['password']
    with DBSession() as db:
        existing = db.query(Admin).filter_by(name=name).first()
        if existing:
            return Response(("Admin with {name} already exists.\n").format(name=name), status=400)
        admin = Admin(name=name, password=password)
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return admin.as_dict()


@app.route("/admin", methods=['GET'])
def get_admins():
    app.logger.info("Inside get_admins")
    with DBSession() as db:
        admins     = db.query(Admin).all()
        admin_list = [a.as_dict() for a in admins]
        return {'admins': admin_list}


@app.route("/admin/<id>", methods=['GET'])
def get_admin_by_id(id):
    app.logger.info("Inside get_admin_by_id %s\n", id)
    with DBSession() as db:
        admin = db.get(Admin, id)
        if admin is None:
            return Response(("Admin with id {id} not found.\n").format(id=id), status=404)
        return admin.as_dict()


@app.route("/admin/<id>", methods=['DELETE'])
def delete_admin_by_id(id):
    app.logger.info("Inside delete_admin_by_id %s\n", id)
    with DBSession() as db:
        admin = db.query(Admin).filter_by(id=id).first()
        if admin is None:
            return Response(("Admin with id {id} not found.\n").format(id=id), status=404)
        db.delete(admin)
        db.commit()
        return Response(("Admin with id {id} deleted.\n").format(id=id), status=200)


# ─────────────────────────────────────────────
# User REST API
# ─────────────────────────────────────────────

@app.route("/users", methods=['POST'])
def add_user():
    app.logger.info("Inside add_user")
    data = request.json
    app.logger.info("Received request:%s", str(data))
    name     = data['name']
    password = data['password']
    with DBSession() as db:
        existing = db.query(User).filter_by(name=name).first()
        if existing:
            return Response(("User with {name} already exists.\n").format(name=name), status=400)
        user = User(name=name, password=password)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.as_dict()


@app.route("/users", methods=['GET'])
def get_users():
    app.logger.info("Inside get_users")
    with DBSession() as db:
        users     = db.query(User).all()
        user_list = [u.as_dict() for u in users]
        return {'users': user_list}


@app.route("/users/<id>", methods=['GET'])
def get_user_by_id(id):
    app.logger.info("Inside get_user_by_id %s\n", id)
    with DBSession() as db:
        user = db.get(User, id)
        if user is None:
            return Response(("User with id {id} not found.\n").format(id=id), status=404)
        return user.as_dict()


@app.route("/users/<id>", methods=['DELETE'])
def delete_user_by_id(id):
    app.logger.info("Inside delete_user_by_id %s\n", id)
    with DBSession() as db:
        user = db.query(User).filter_by(id=id).first()
        if user is None:
            return Response(("User with id {id} not found.\n").format(id=id), status=404)
        db.delete(user)
        db.commit()
        return Response(("User with id {id} deleted.\n").format(id=id), status=200)


# ─────────────────────────────────────────────
# Cities REST API  (/admin/<admin_id>/cities)
# ─────────────────────────────────────────────

@app.route("/admin/<admin_id>/cities", methods=['POST'])
def add_city(admin_id):
    app.logger.info("Inside add_city for admin %s\n", admin_id)
    with DBSession() as db:
        admin = db.get(Admin, admin_id)
        if admin is None:
            return Response(("Admin with id {id} not found.\n").format(id=admin_id), status=404)
        data = request.json
        name = data['name']
        url  = data['url']
        city = City(adminId=admin_id, name=name, url=url)
        db.add(city)
        db.commit()
        db.refresh(city)
        return city.as_dict()


@app.route("/admin/<admin_id>/cities", methods=['GET'])
def get_cities(admin_id):
    app.logger.info("Inside get_cities for admin %s\n", admin_id)
    with DBSession() as db:
        admin = db.get(Admin, admin_id)
        if admin is None:
            return Response(("Admin with id {id} not found.\n").format(id=admin_id), status=404)
        cities    = db.query(City).filter_by(adminId=admin_id).all()
        city_list = [c.as_dict() for c in cities]
        return {'cities': city_list}


@app.route("/admin/<admin_id>/cities/<city_id>", methods=['GET'])
def get_city_by_id(admin_id, city_id):
    app.logger.info("Inside get_city_by_id admin:%s city:%s\n", admin_id, city_id)
    with DBSession() as db:
        admin = db.get(Admin, admin_id)
        if admin is None:
            return Response(("Admin with id {id} not found.\n").format(id=admin_id), status=404)
        city = db.query(City).filter_by(id=city_id, adminId=admin_id).first()
        if city is None:
            return Response(("City with id {id} not found.\n").format(id=city_id), status=404)
        return city.as_dict()


@app.route("/admin/<admin_id>/cities/<city_id>", methods=['DELETE'])
def delete_city_by_id(admin_id, city_id):
    app.logger.info("Inside delete_city_by_id admin:%s city:%s\n", admin_id, city_id)
    with DBSession() as db:
        admin = db.get(Admin, admin_id)
        if admin is None:
            return Response(("Admin with id {id} not found.\n").format(id=admin_id), status=404)
        city = db.query(City).filter_by(id=city_id, adminId=admin_id).first()
        if city is None:
            return Response(("City with id {id} not found.\n").format(id=city_id), status=404)
        db.delete(city)
        db.commit()
        return Response(("City with id {id} deleted.\n").format(id=city_id), status=200)


# ─────────────────────────────────────────────
# UserCity REST API  (/users/<user_id>/cities)
# ─────────────────────────────────────────────

@app.route("/users/<user_id>/cities", methods=['POST'])
def add_user_city(user_id):
    app.logger.info("Inside add_user_city for user %s\n", user_id)
    with DBSession() as db:
        user = db.get(User, user_id)
        if user is None:
            return Response(("User with id {id} not found.\n").format(id=user_id), status=404)
        data      = request.json
        city_name = data['name']
        month     = data['month']
        year      = str(data['year'])
        params    = data.get('weather_params') or data.get('params')
        if not year.isdigit() or len(year) != 4:
            return Response("Year needs to be exactly four digits.\n", status=400)
        city = db.query(City).filter_by(name=city_name).first()
        if city is None:
            return Response(("City with name {name} not found.\n").format(name=city_name), status=404)
        usercity = UserCity(userId=user_id, cityId=city.id,
                            month=month, year=year, weather_params=params)
        db.add(usercity)
        db.commit()
        db.refresh(usercity)
        return usercity.as_dict()


@app.route("/users/<user_id>/cities", methods=['GET'])
def get_user_cities(user_id):
    app.logger.info("Inside get_user_cities for user %s\n", user_id)
    with DBSession() as db:
        city_name = request.args.get('name')

        # 4.3 - GET by city name query param
        if city_name:
            city_name = city_name.strip('"').strip("'")
            user = db.get(User, user_id)
            if user is None:
                return Response(("User with id {id} not found.\n").format(id=user_id), status=404)
            city = db.query(City).filter_by(name=city_name).first()
            if city is None:
                return Response(("City with name {name} not found.\n").format(name=city_name), status=404)
            uc = db.query(UserCity).filter_by(userId=user_id, cityId=city.id).first()
            if uc is None:
                return Response(("City with name {name} not being tracked by the user {username}.\n").format(
                    name=city_name, username=user.name), status=404)
            return {
                'name':           city_name,
                'month':          str(uc.month),
                'year':           str(uc.year),
                'weather_params': str(uc.weather_params)
            }

        # 4.2 - GET all user cities
        usercities = db.query(UserCity).filter_by(userId=user_id).all()
        uc_list    = [uc.as_dict() for uc in usercities]
        return {'usercities': uc_list}


# ─────────────────────────────────────────────
# UI Routes
# ─────────────────────────────────────────────

@app.route("/logout", methods=['GET'])
def logout():
    app.logger.info("Logout called.")
    session.pop('username', None)
    app.logger.info("Before returning...")
    return render_template('index.html')


@app.route("/login", methods=['POST'])
def login():
    username = request.form['username'].strip()
    password = request.form['password'].strip()
    app.logger.info("Username:%s", username)
    app.logger.info("Password:%s", password)
    session['username'] = username
    return render_template('welcome.html',
                           welcome_message="Personal Weather Portal",
                           cities=[],
                           name=username,
                           addButton_style="display:none;",
                           addCityForm_style="display:none;",
                           regButton_style="display:inline;",
                           regForm_style="display:inline;",
                           status_style="display:none;")


@app.route("/")
def index():
    return render_template('index.html')


@app.route("/adminlogin", methods=['POST'])
def adminlogin():
    username = request.form['username'].strip()
    password = request.form['password'].strip()
    app.logger.info("Username:%s", username)
    app.logger.info("Password:%s", password)
    session['username'] = username
    return render_template('welcome.html',
                           welcome_message="Personal Weather Portal - Admin Panel",
                           cities=[],
                           name=username,
                           addButton_style="display:inline;",
                           addCityForm_style="display:inline;",
                           regButton_style="display:none;",
                           regForm_style="display:none;",
                           status_style="display:none;")


@app.route("/adminindex")
def adminindex():
    return render_template('adminindex.html')


if __name__ == "__main__":
    app.debug = False
    app.logger.info('Portal started...')
    app.run(host='0.0.0.0', port=5009)
