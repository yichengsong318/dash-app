# Dash_GCP

Folder structure

- Dash_heroku --- files to deploy on Heroku

- Dash_lastobject_depl -- files to deloy on GCP



- app.py --- main file to run Dash app locally using packages with version specified in requirements.txt
`python app.py`


If you want to new user/password

1. Edit creds_dash.json file in Dash_heroku and Dash_lastobject_depl

2a. For heroku type following commands after logging in

to log in 

`heroku login`  then in browser log in using credentials from pass.txt

`git add .`

`git commit -m 'adding new users of app'`

`git push heroku master`

you can reference from here >>> https://dash.plotly.com/deployment


2b. For GCP

`gcloud app deploy` after loggin in and setting project


