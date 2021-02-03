#! /bin/sh

export FLASK_APP="application.py"

export API_KEY=$(cat API_Key.txt)

flask run
