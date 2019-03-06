import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
    render_template, flash
from contextlib import closing

import requests
import urllib.parse
import time

# print ("time.time(): %f " % time.time())
# print (time.localtime(time.time()))
# specify what colour is in what grid before post request
named_tuple = time.localtime() # get struct_time
#the_current_time = time.strftime("%d/%m/%Y, %H:%M:%S", named_tuple)
the_current_time = time.strftime("%H:%M:%S", named_tuple)
#the_current_time = (time.asctime(time.localtime(time.time())))


app = Flask(__name__) # creates applications instance
app.config.from_object(__name__) # loads configuration from this file, flaskr.py

# loads default config, overrides config from an enviroment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'flaskr.db'),
    SECRET_KEY='YOUR_SECRET_KEY_GOES_HERE', # required to keep client-side session secure
    USERNAME='YOUR_USERNAME_GOES_HERE',
    PASSWORD='YOUR_PASSWORD_GOES_HERE'
))
app.config.from_envvar('FLASKR_SETTINGS', silent=True)

print(the_current_time)

# Handles dark and light theme depending on user's system clock
if the_current_time > '18:38:00' or the_current_time < '08:59:59':# Need to figure out how to work this method out with just the time
#    '<style>color:#fff !important; background-color:#000000 !important</style>'
    bgcolour = '#000000'
    textcol = '#FFFFFF'
    pagecol = '#333333'
elif the_current_time > '09:00:00' or the_current_time < '18:38:00':
    bgcolour = '#D3D3D3'
    textcol = '#000000'
    pagecol = '#EEEEEE'

# may need SQLite3.Row
def connect_db():
    # Connects to specific database in this case SQLite3
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv

# initilises database, closing() helper function keeps connection open
def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

#def init_db():
    #db = get_db()
    # open_resouce() method of app object is helper function that opens resouce that app provides
    #opens the file from resource location flaskr/flaskr folder and allows you to read from it, used to execute script on db connection
    #with app.open_resource('schema.sql', mode='r') as f:
        #db.cursor().executescript(f.read())
    #db.commit()

# called before request is made, passes no arguments, db connection is stored on g object
@app.before_request
def before_request():
    g.db = connect_db()


# When the command executes, Flask will automatically create an application context which is bound to the right application. Within the function, you can then access flask.g and other things as you might expect. When the script ends, the application context tears down and the database connection is released
@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()
    print('Initialized the database.')

# Database file path
DATABASE = '/flaskr.db'

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


# show entries, passing entries to show_entries.html template, returned rendered entry
@app.route('/')
def show_entries():
#    if request.button['switch_theme']:

    db = get_db()
    cur = db.execute('select url, CampaignMedium, CampaignSource, CampaignName, CampaignContent, CampaignTerms from entries order by id desc')
    entries = cur.fetchall()
    flash('entries are listed')
    return render_template('show_entries.html', entries=entries, bgcolour=bgcolour, textcol=textcol, the_current_time=the_current_time, pagecol=pagecol) # replace with whats required for utm

# Displays predined text in text boxes for relevent fields
sources = ["", "", "" ""] # Data displayed in the text input fields, auto complete should be pulled from db SELECT * FROM DBTABLE WHERE sources
mediums = ["", "", ""] # variables defined with data stored in an array
campaigns = ["", "", ""] #
terms = ["", "", ""]
contents = ["", "", ""]

@app.route('/')
def show_entries_in_ddmenu():
    if not session.get('logged_in'):
        abort(401)
    if request.method == 'POST':
        db = get_db()
        db.execute('select url from entries')
        request.select['url']


# Allows adding new entries if logged in only responding to POST requests, flash displays message to next request then redirects to show entries page
# This view checks a logged in user if logged_in key is valid and present, and returns true
@app.route('/add', methods=['POST'])
def add_entry():
    utm_link = None # variable named utm_link equal to none
    if not session.get('logged_in'):
        abort(401)
    if request.method == 'POST':
        db = get_db()
        db.execute('insert into entries (url, CampaignMedium, CampaignSource, CampaignName, CampaignContent, CampaignTerms) values (?, ?, ?, ?, ?, ?)',
                    [request.form['url'], request.form['CampaignSource'], request.form['CampaignMedium'], request.form['CampaignName'], request.form['CampaignContent'], request.form['CampaignTerms']])
        db.commit()
        utm_link = "{0}?utm_source={1}&utm_medium={2}&utm_campaignName={3}".format(
            request.form["url"], request.form['CampaignSource'], request.form['CampaignMedium'], request.form["CampaignName"]
        )
        if "CampaignTerms" in request.form: # term and content optional
            if request.form["CampaignTerms"]:
                utm_link = "{0}&utm_CampaignTerms={1}".format(utm_link, request.form["CampaignTerms"])
        if "CampaignContent" in request.form:
            if request.form["CampaignContent"]:
                utm_link = "{0}&utm_CampaignContent={1}".format(utm_link, request.form["CampaignContent"])
    flash('New entry was successfully posted')
    print(utm_link)
    # After this, the entered url which would be stored in the utm_link variable will be passed into the longurl variable, a request is made to bitly to shorten the url then passed ontoqrserver to generate a qrcode with the shortened url
    longurl = utm_link
    urlencodee = urllib.parse.quote('' + longurl + '')
    r = requests.get(
        'https://api-ssl.bitly.com/v3/shorten?access_token=YOUR_BITLY_ACCESS_TOCKEN_GOES_HERE&longUrl=http%3A%2F%2F' + urlencodee + '%2F&format=txt')
    json_object_qrcodeimg = r.text
    print(json_object_qrcodeimg, urlencodee, longurl)
    #       r = requests.get('https://api.qrserver.com/v1/create-qr-code/?data='+json_object+'&size=175x175&format=svg')
    qr_r = requests.get('https://api.qrserver.com/v1/create-qr-code/?data=' + json_object_qrcodeimg + '&size=175x175&format=svg')
    print(qr_r)
    #        return '<html><body><img src="https://api.qrserver.com/v1/create-qr-code/?data='+json_object+'&size=175x175&format=svg" alt="" title="" /></body></html>'
    #        return qr_r.content
    return render_template('show_entries.html', sources=sources, mediums=mediums, ## Returns a Render template looks for templates in a "templates" folder variables - -sources, mediums-- are pulled from array listed above -- line9, which would inturn pull that data from the SQL Database. The String being whatever is contained in index.html file in templates directory
                           campaigns=campaigns, terms=terms, contents=contents, utm_link=utm_link, json_object_qrcodeimg=json_object_qrcodeimg,  bgcolour=bgcolour, textcol=textcol, the_current_time=the_current_time, pagecol=pagecol)



# Lists Entry for non admin user
@app.route('/list', methods=['POST'])
def list_entry():
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    db.execute('select * from entries (url, CampaignTerms, CampaignMedium, CampaignSource, CampaignName, CampaignContent) values (?, ?, ?, ?, ?, ?)',
               request.form['url'], [request.form['CampaignSource'], request.form['CampaignMedium'], request.form['CampaignName'], request.form['CampaignTerms'], request.form['CampaignContent']])
    db.commit()
    flash('entry listed')
    return redirect(url_for('show_entries'))


## IMPORTANT - use sql question marks when writing statements overwise SQL will be vunverable to SQL Injection

## Login

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
    #Takes the username & password from whatever is in app config above. An alternative method would be REQUIRED if on a live enviroment
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid Username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid Password'
        else:
            session['logged_in'] = True

            flash('You were logged in')
            return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)

# log out - removes session key with pop() method

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))

@app.route('/urltoshortandqrcode', methods=['GET', 'POST'])
def shorten_url():
#    longurl = request.form['longurl']
#    r = requests.get('https://api-ssl.bitly.com/v3/shorten?access_token=ACCESS_TOKEN&longUrl='+longurl+'')
#    json_object = r.json
#    return longurl
    return render_template('urlshort_qr_form.html')


# Code below shortens a url with bitly api removing the &format=txt at the end of the get request shows all json data need url formating checks as currently 1234 will shorten to a bitly url
@app.route('/urlshort_qr', methods=['POST'])
def shorten_url_and_generate_qrcode():
        longurl = request.form['longurl']
        urlencodee = urllib.parse.quote(''+longurl+'')
        r = requests.get('https://api-ssl.bitly.com/v3/shorten?access_token=a82fa916e7dacdade9055f6e034a0b430a1b057d&longUrl=http%3A%2F%2F'+urlencodee+'%2F&format=txt')
        json_object = r.text
        print(json_object, urlencodee, longurl)
#       r = requests.get('https://api.qrserver.com/v1/create-qr-code/?data='+json_object+'&size=175x175&format=svg')
        qr_r = requests.get('https://api.qrserver.com/v1/create-qr-code/?data='+json_object+'&size=175x175&format=svg')
        print(qr_r)
#        return '<html><body><img src="https://api.qrserver.com/v1/create-qr-code/?data='+json_object+'&size=175x175&format=svg" alt="" title="" /></body></html>'
#        return qr_r.content
        return render_template('show_entries.html', json_object=json_object)
#       return redirect(url_for('show_entries', r=r.content))

if __name__ == '__main__':
    app.run(debug=True)
