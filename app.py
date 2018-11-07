######################################
# author ben lawson <balawson@bu.edu> 
# Edited by: Craig Einstein <einstein@bu.edu>
# Edited by: Muzi Li <marlonli@bu.edu>
######################################
# Some code adapted from 
# CodeHandBook at http://codehandbook.org/python-web-application-development-using-flask-and-mysql/
# and MaxCountryMan at https://github.com/maxcountryman/flask-login/
# and Flask Offical Tutorial at  http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
# see links for further understanding
###################################################

import flask
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
#import flask.ext.login as flask_login
import flask_login
#for image uploading
from werkzeug import secure_filename
import os, base64
import time

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

#These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'root' #CHANGE THIS TO YOUR MYSQL PASSWORD
app.config['MYSQL_DATABASE_DB'] = 'photoshare'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

#begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email from Users") 
users = cursor.fetchall()

def getUserList():
	cursor = conn.cursor()
	cursor.execute("SELECT email from Users") 
	return cursor.fetchall()

class User(flask_login.UserMixin):
	pass

@login_manager.user_loader
def user_loader(email):
	users = getUserList()
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	return user

@login_manager.request_loader
def request_loader(request):
	users = getUserList()
	email = request.form.get('email')
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	cursor = mysql.connect().cursor()
	cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email))
	data = cursor.fetchall()
	pwd = str(data[0][0] )
	user.is_authenticated = request.form['password'] == pwd
	return user


'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
	return new_page_html
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
	if flask.request.method == 'GET':
		return '''
			   <form action='login' method='POST'>
				<input type='text' name='email' id='email' placeholder='email'></input>
				<input type='password' name='password' id='password' placeholder='password'></input>
				<input type='submit' name='submit'></input>
			   </form></br>
		   <a href='/'>Home</a>
			   '''
	#The request method is POST (page is recieving data)
	email = flask.request.form['email']
	cursor = conn.cursor()
	#check if email is registered
	if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
		data = cursor.fetchall()
		pwd = str(data[0][0] )
		if flask.request.form['password'] == pwd:
			user = User()
			user.id = email
			flask_login.login_user(user) #okay login in user
			return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

	#information did not match
	return "<a href='/login'>Try again</a>\
			</br><a href='/register'>or make an account</a>"

@app.route('/logout')
def logout():
	flask_login.logout_user()
	return render_template('hello.html', message='Logged out') 

@login_manager.unauthorized_handler
def unauthorized_handler():
	return render_template('unauth.html') 

#you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register/", methods=['GET'])
def register():
	return render_template('improved_register.html', supress='True')  

@app.route("/register/", methods=['POST'])
def register_user():
	try:
		email=request.form.get('email')
                print email
		password=request.form.get('password')
		fname = request.form.get('firstname')
		lname = request.form.get('lastname')
		DOB = request.form.get('date')
		hometown = request.form.get('hometown')

	except:
		print "couldn't find all tokens" #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('register'))
	cursor = conn.cursor()
	test =  isEmailUnique(email)
	if test:
		print cursor.execute("INSERT INTO Users (email, password, fname, lname, DOB, hometown) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}')".format(email, password, fname, lname, DOB, hometown))
		conn.commit()
		#log user in
		user = User()
		user.id = email
		flask_login.login_user(user)
		return render_template('hello.html', name=email, message='Account Created!')
	else:
		print "couldn't find all tokens"
		return flask.redirect(flask.url_for('register'))

def getUsersPhotos(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures WHERE user_id = '{0}'".format(uid))
	return cursor.fetchall() #NOTE list of tuples, [(imgdata, pid), ...]

def getUserIdFromEmail(email):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
	return cursor.fetchone()[0]

def isEmailUnique(email):
	#use this to check if a email has already been registered
	cursor = conn.cursor()
	if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)): 
		#this means there are greater than zero entries with that email
		return False
	else:
		return True
#end login code

@app.route('/profile')
@flask_login.login_required
def protected():
	return render_template('hello.html', name=flask_login.current_user.id, message="Here's your profile")

#begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML 
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/uploading', methods=['GET', 'POST'])
@flask_login.login_required
def uploading():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	print('You got them all')
	return render_template('upload.html', albums = showAlbums(uid))

@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		imgfile = request.files['photo']
		caption = request.form.get('caption')
		print caption
		photo_data = base64.standard_b64encode(imgfile.read())
		tags = str(request.form.get('tags')).split(' ')
		album_title = request.form.get('album_title')
		album_id = getAlbumsID(album_title, uid)
		cursor = conn.cursor()
		if CheckAlbumUnique(album_title, uid) == False:
			cursor.execute("INSERT INTO Pictures (imgdata, user_id, caption, album_id) VALUES ('{0}', '{1}', '{2}', '{3}' )".format(photo_data,uid, caption, album_id))
			conn.commit()
			picture_id = cursor.lastrowid
			print(picture_id)
			TagPhoto(tags, picture_id)
			return render_template('You.html', name=getFirstName(uid), message='upload successfully')
		else:
			return render_template('upload.html', message='Not a valid album')
		return render_template('hello.html', name=flask_login.current_user.id, message='Photo uploaded!', photos=getUsersPhotos(uid) )
	#The method is GET so we return a  HTML form to upload the a photo.
	else:
		return render_template('upload.html')
#end photo uploading code 

@app.route('/uploadAvatar', methods=['GET', 'POST'])
@flask_login.login_required
def upload_avatar():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		imgfile = request.files['photo']
		photo_data = base64.standard_b64encode(imgfile.read())
		caption = getFirstName(uid)
		cursor = conn.cursor()
		cursor.execute("INSERT INTO Pictures(imgdata, user_id, caption) VALUES ('{0}', '{1}', '{2}')".format(photo_data,uid, caption))
		conn.commit()
		picture_id = cursor.lastrowid
		addAvatar(uid, picture_id)
		return render_template('You.html', Avatar= showAvatar(uid), message='You looks awesome!!')
	else:
		return render_template("You.html")

def addAvatar(uid, picture_id):
	cursor = conn.cursor()
	cursor.execute("INSERT INTO UserAvatar(user_id, picture_id) VALUES ('{0}', '{1}')".format(uid, picture_id))
	conn.commit()

def showAvatar(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT P.imgdata FROM Pictures P, UserAvatar U WHERE P.picture_id = U.picture_id AND U.user_id = '{0}'".format(uid))
	return cursor.fetchall()

def TagPhoto(tags, picture_id):
	print('adding tag')
	cursor = conn.cursor()
	for t in tags:
		cursor.execute("INSERT INTO Tag (Tag, picture_id) VALUES ('{0}', '{1}')".format(t, picture_id))
	conn.commit()

def getFirstName(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT fname FROM Users WHERE user_id ='{0}'".format(uid))
	return cursor.fetchall()[0][0]

@app.route('/albums', methods=['GET', 'POST'])
@flask_login.login_required
def albums():
	pics = [];
	uid = getUserIdFromEmail(flask_login.current_user.id)
	return render_template('albums.html', albums = showAlbums(uid))

def showAlbums(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT name, album_id, DOC FROM Album WHERE user_id = '{0}'".format(uid))
	return cursor.fetchall()

#create album in order to put photos inside
@app.route('/add_album', methods=['GET', 'POST'])
@flask_login.login_required
def add_album():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		album_title = request.form.get('album_title')
		print(album_title)
		if CheckAlbumUnique(album_title, uid):
			cursor = conn.cursor()
			date = time.strftime("%Y-%m-%d")
			cursor.execute("INSERT INTO Album (name, user_id, DOC) VALUES('{0}', '{1}', '{2}')".format(album_title,uid,date))
			conn.commit()
			return render_template('You.html', name=getFirstName(uid), message='Album Created!!', albums=getAlbums(uid))
		else:
			return render_template('add_album.html', message="Pick a new title!")
	else:
		return render_template('add_album.html')

def getAlbums(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT name, DOC FROM Album WHERE user_id='{0}'".format(uid))
	return cursor.fetchall()

def CheckAlbumUnique(album_title, uid):
	cursor = conn.cursor()
	if cursor.execute("SELECT name FROM Album WHERE name = '{0}' AND user_id = '{1}'".format(album_title, uid)): 
		#if it's 0, then it is true
		return False
	else:
		return True
@app.route("/album_delete", methods=['GET', 'POST'])
@flask_login.login_required
def deleteAlbum():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	if request.method == 'POST':
		album_name = request.form.get('album_name')
		print(album_name)
		album_id = getAlbumsID(album_name, uid)
		print(album_id)
		if(album_id == 0):
			return render_template("albums.html", albums=showAlbums(uid), message="You have no album under such name")
		cursor = conn.cursor()
		#pix = getAlbumPhotos(album_id, uid)
		#for pic in pix:
		#	deletePhoto(pic[1])
		cursor.execute("DELETE FROM Album WHERE album_id='{0}'".format(album_id))
		conn.commit()
		return render_template("albums.html", albums=showAlbums(uid), message="Successfully delete album")
	else:
		return render_template("albums.html", albums=showAlbums(uid), message="Please check you operation of deletion")

def getAlbumsID(album_name, uid):
	cursor = conn.cursor()
	cursor.execute("SELECT album_id FROM Album WHERE name='{0}' AND user_id='{1}'".format(album_name, uid))
	return cursor.fetchall()[0][0]

@app.route('/friends', methods=['GET', 'POST'])
@flask_login.login_required
def friends():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	friends = getUsersFriends(uid)
	friends_names = []
	for i in friends:
		friends_names += [getUserName(i)]
	if request.method == 'POST':
		first_name = request.form.get('search_first_name')
		last_name = request.form.get('search_last_name')
		if searchUsers(first_name, last_name):
			return render_template('friends.html', friends=friends_names, users_search=searchUsers(first_name,last_name))
		else:
			return render_template('friends.html', friends=friends_names, message="No users with that name")
	else:
		return render_template('friends.html', friends=friends_names)

def searchUser(first_name, last_name):
	cursor = conn.cursor()
	first_name=str(first_name)
	last_name=str(last_name)
	if first_name != '' and (last_name == ''):
		cursor.execute("SELECT fname, lname, DOB, email, user_id FROM Users WHERE fname ='{0}'".format(first_name))
	elif last_name != '' and (first_name == ''):
		cursor.execute("SELECT fname, lname, DOB, email, user_id FROM Users WHERE lname ='{0}'".format(last_name))
	else:
		cursor.execute("SELECT fname, lname, DOB, email, user_id FROM Users WHERE fname = '{0}' AND lname ='{1}'".format(first_name, last_name))
	return cursor.fetchall()

@app.route('/You')
@flask_login.login_required
def profile():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	if showAvatar(uid):
		print(uid)
		return render_template('You.html', name=getFirstName(uid), message="Wanna some fresh today?", Avatar = showAvatar(uid))
	else:
		print("no av")
		return render_template('You.html', name=getFirstName(uid), message="Wanna some fresh today?")

def getFirstName(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT fname FROM Users WHERE user_id = '{0}'".format(uid))
	return cursor.fetchall()[0][0]

@app.route("/myPhotos")
@flask_login.login_required
def myP():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	pinfo = []
	for p in getUserPhotos(uid):
		pinfo += [getPinfo(p)]
	return render_template("showPhotos.html", photos=pinfo)

def getPinfo(p):
	uid = getUserIdFromEmail(flask_login.current_user.id)
	return [p] + [getTag(p[1])] + [getComments(p[1], uid)] + [getLikes(p[1])] + [getUsersLike(p[1])]
 
def getTag(picture_id):
	cursor = conn.cursor()
	cursor.execute("SELECT Tag FROM Tag WHERE picture_id = '{0}'".format(picture_id))
	return cursor.fetchall()

def getComments(picture_id, uid):
	cursor = conn.cursor()
	cursor.execute("SELECT comment FROM Comment WHERE picture_id = '{0}' AND  user_id = '{1}'".format(picture_id, uid))
	return cursor.fetchall()

def getLikes(picture_id):
	cursor = conn.cursor()
	cursor.execute("SELECT COUNT(picture_id) FROM Likes WHERE picture_id='{0}'".format(picture_id))
	return cursor.fetchall()

def getUsersLike(picture_id):
	cursor = conn.cursor()
	cursor.execute("SELECT U.fname, U.lname FROM Likes L, Users U WHERE U.user_id = L.user_id AND L.picture_id = '{0}'".format(picture_id))
	return cursor.fetchall()

def getUserPhotos(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT P.imgdata, P.picture_id, P.caption, A.name FROM Pictures P, Album A WHERE P.album_id = A.album_id AND P.user_id = '{0}'".format(uid))
	return cursor.fetchall()

#default page  
@app.route("/", methods=['GET'])
def hello():
	return render_template('hello.html', message='Welcome to Photoshare')


if __name__ == "__main__":
	#this is invoked when in the shell  you run 
	#$ python app.py 
	app.run(port=5000, debug=True)
