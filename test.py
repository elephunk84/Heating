#!/bin/python3

from run import *
from app import app

if __name__ == "__main__":
    app.run('0.0.0.0', 80, debug=True)
