#!flask/bin/python3
from flask import Flask, render_template, request, redirect

app = Flask(__name__, static_url_path='')
from app import views
