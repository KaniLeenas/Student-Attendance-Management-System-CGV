"""
Flask Web Application (Module 8)
"""
from flask import Flask, render_template, request, redirect, url_for, flash
import config

app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
