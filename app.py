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
		DOB = request.form.get('birthday')
		hometown = request.form.get('hometown')
		gender = request.form.get('gender')

	except:
		print "couldn't find all tokens" #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('register'))
	cursor = conn.cursor()
	test =  isEmailUnique(email)
	if test:
		print cursor.execute("INSERT INTO Users (email, password, fname, lname, DOB, hometown, gender) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}')".format(email, password, fname, lname, DOB, hometown, gender))
		conn.commit()
		#log user in
		user = User()
		user.id = email
		flask_login.login_user(user)
		return render_template('welcome.html', name=email, message='Account Created!')
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
	return render_template('welcome.html', name=flask_login.current_user.id, message="Welcome!", users = topUser())

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
		cursor = conn.cursor()
		if CheckAlbumUnique(album_title, uid) == False:
			album_id = getAlbumsID(album_title, uid)
			cursor.execute("INSERT INTO Pictures (imgdata, user_id, caption, album_id) VALUES ('{0}', '{1}', '{2}', '{3}' )".format(photo_data,uid, caption, album_id))
			conn.commit()
			picture_id = cursor.lastrowid
			print(picture_id)
			TagPhoto(tags, picture_id)
			return render_template('You.html', name=getFirstName(uid),Avatar= showAvatar(uid), message='upload successfully')
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
		cursor = conn.cursor()
		cursor.execute("INSERT INTO UserAvatar(imgdata, user_id) VALUES ('{0}', '{1}')".format(photo_data,uid))
		conn.commit()
		return render_template('You.html', Avatar= showAvatar(uid), message='You looks awesome!!')
	else:
		return render_template("You.html")

def showAvatar(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata FROM UserAvatar WHERE user_id = '{0}'".format(uid))
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

def getLastName(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT lname FROM Users WHERE user_id ='{0}'".format(uid))
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
		#pictures = getAlbumPhotos(album_id, uid)
		#for pic in pictures:
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

@app.route("/myPhotos")
@flask_login.login_required
def myP():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	pinfo = []
	for p in getUserPhotos(uid):
		pinfo += [getPinfo(p)]
	return render_template("showPhotos.html", photos=pinfo, user_id=uid)

def getPinfo(p):
	uid = getUserIdFromEmail(flask_login.current_user.id)
	return [p] + [getTag(p[1])] + [getComments(p[1], uid)] + [getLikes(p[1])] + [getUsersLike(p[1])]
 
def getTag(picture_id):
	cursor = conn.cursor()
	cursor.execute("SELECT Tag FROM Tag WHERE picture_id = '{0}'".format(picture_id))
	return cursor.fetchall()

def getComments(picture_id, uid):
	cursor = conn.cursor()
	cursor.execute("SELECT C.comment, U.fname, U.lname FROM Comment C, Users U WHERE C.user_id = U.user_id AND picture_id = '{0}' ORDER BY C.DOC".format(picture_id))
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

@app.route("/showPhotos",methods=['POST', 'GET'])
@flask_login.login_required
def showPhotos():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	if request.method == 'POST':
		if request.form.get("comment"):
			comment = request.form.get("comment")
			picture_id = request.form.get("picture_id")
			addComment(comment, uid, picture_id)
			return render_template("showPhotos.html", photos = allPinfo(), message = "Comment Added Successfully", user_id = uid)
		elif request.form["photo_delete"]:
			picture_id = request.form.get("picture_id")
			print(uid)
			print(picOwnerID(picture_id)[0][0])
			if uid == picOwnerID(picture_id)[0][0]:
				print('it is there')
				deletePhoto(picture_id)
				return render_template("showPhotos.html", photos = allPinfo(), message = "Photo Deleted Successdully", user_id = uid)
			else:
				print('not')
				return render_template("showPhotos.html", photos = allPinfo(), message = "You are not Authorized to delete", user_id = uid)
		else:
			return render_template("showPhotos.html", photos = allPinfo(), message = "All Photos Here", user_id = uid)
	else:
		return render_template("showPhotos.html", photos = allPinfo(), message = "All Photos Here", user_id = uid)

@app.route("/likePhoto",methods=['POST', 'GET'])
@flask_login.login_required
def addLike():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	photos = allPinfo()
	if request.method == 'POST':
		picture_id = request.form.get("picture_id")
		if likeValid(uid, picture_id) == False:
			return render_template("showPhotos.html", photos=photos, message="Already liked bro", user_id = uid)
		else:
			likePic(uid, picture_id)
			photos = allPinfo()
			return render_template("showPhotos.html", photos=photos, message="You liked one picture, you can find more interesting one by exploring", user_id = uid)
	else:
		return render_template("showPhotos.html", photos=photos, message="Something wrong happens here", user_id = uid)


def likePic(uid, picture_id):
	cursor= conn.cursor()
	cursor.execute("INSERT INTO Likes(user_id, picture_id) VALUES('{0}', '{1}')".format(uid, picture_id))
	conn.commit()

def likeValid(uid, picture_id):
	cursor = conn.cursor()
	if cursor.execute("SELECT user_id FROM Likes WHERE user_id ='{0}' AND picture_id='{1}'".format(uid, picture_id)):
		return False
	else:
		return True

#to get all the photos' information including image itself, picture id, cation and name
def allPinfo():
	allPhoto = []
	cursor = conn.cursor()
	cursor.execute("SELECT P.imgdata, P.picture_id, P.caption, A.name FROM Pictures P, Album A WHERE P.album_id = A.album_id")
	photos = cursor.fetchall()
	for p in photos:
		allPhoto += [getPinfo(p)]
	return allPhoto

def addComment(comment, uid, picture_id):
	DOC = time.strftime("%Y-%m-%d")
	cursor = conn.cursor()
	cursor.execute("INSERT INTO Comment(comment, user_id, DOC, picture_id) VALUES ('{0}', '{1}', '{2}', '{3}')".format(comment, uid, DOC, picture_id))
	conn.commit()

def deletePhoto(picture_id):
	cursor = conn.cursor()
	cursor.execute("DELETE FROM Likes where picture_id = '{0}'".format(picture_id))
	conn.commit()
	cursor.execute("DELETE FROM Comment WHERE picture_id='{0}'".format(picture_id))
	conn.commit()
	cursor.execute("DELETE FROM Tag WHERE picture_id='{0}'".format(picture_id))
	conn.commit()
	cursor.execute("DELETE FROM Pictures WHERE picture_id='{0}'".format(picture_id))
	conn.commit()

def picOwnerID(picture_id):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id FROM Pictures WHERE picture_id = '{0}'".format(picture_id))
	return cursor.fetchall()

#tag search, by input is tag name, it will return all the tags
@app.route('/tag_search', methods=["POST", "GET"])
@flask_login.login_required
def searchTags():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	photos = []
	if request.method == "POST":
		if(request.form.get('tag_search')):
			tags = request.form.get('tag_search').split(" ")
			for i in getAllTaggedPhotos(tags):
				photos += [getPinfo(i)]
		else:
			tag = request.form['common_tag']
			for i in getTaggedPhotos(tag):
				photos += [getPinfo(i)]
		if photos:
			return render_template("showPhotos.html", photos=photos, user_id = uid)
		else:
			return render_template("tagSearch.html", common=getMostCommonTags(), message="There's no such tag been uploaded before")
	else:
		return render_template("tagSearch.html", common=getMostCommonTags())

def getTaggedPhotos(tag):
	cursor = conn.cursor()
	cursor.execute("SELECT P.imgdata, P.picture_id, P.caption, A.name FROM Pictures P, Album A, Tag T WHERE T.picture_id = P.picture_id AND P.album_id = A.album_id AND T.Tag = '{0}'".format(tag))
	return cursor.fetchall()


def tagValid(tag):
	cursor = conn.cursor()
	if cursor.execute("SELECT * FROM Tags WHERE Tag = '{0}'".format(tag)):
		return True
	else:
		return False

def getTagQuery(tags):
	query = "SELECT P.imgdata, P.picture_id, P.caption, A.name FROM Pictures P, Album A, Tag T WHERE T.picture_id = P.picture_id AND P.album_id = A.album_id AND T.Tag = '{0}'".format(tags[0])
	for i in range(1, len(tags)):
		query += " AND P.picture_id IN (SELECT P.picture_id  FROM Pictures P, Album A, Tag T WHERE T.picture_id = P.picture_id AND P.album_id = A.album_id AND T.Tag = '{0}')".format(tags[i])
	print(query)
	return query

def getAllTaggedPhotos(tags):
	cursor = conn.cursor()
	if len(tags) == 1:
		return getTaggedPhotos(tags[0])
	else:
		pics = getTaggedPhotos(tags[0])
		for i in pics:
			cursor.execute(getTagQuery(tags))
		return cursor.fetchall()

def getMostCommonTags():
	cursor = conn.cursor()
	cursor.execute("SELECT Tag, COUNT(Tag) FROM Tag GROUP BY Tag ORDER BY COUNT(Tag) DESC LIMIT 5")
	return cursor.fetchall()

@app.route('/my_tag_search', methods=["POST", "GET"])
@flask_login.login_required
def searchMyTags():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	#if it's guest, he can not do search in my tags
	if uid == -1:
		return render_template("showPhotos.html", photos = allPinfo(), message = "Please sign in first to use such functionality", user_id = uid)
	photos = []
	pictures = []
	for i in getUsersPhotos(uid):
		pictures += [getPinfo(i)]
	if request.method == "POST":
		tag = request.form.get('tag_name')
		for i in getUserTaggedPhotos(tag, uid):
			photos += [getPinfo(i)]
		if photos:
			return render_template("showPhotos.html", photos=photos, user_id = uid)
		else:
			return render_template("showPhotos.html", message="no such tag in your repository", user_id = uid)
	else:
		return render_template("showPhotos.html", photos=pictures, user_id = uid)


def getUserTaggedPhotos(tag, uid):
	cursor = conn.cursor()
	cursor.execute("SELECT P.imgdata, P.picture_id, P.caption, A.name FROM Pictures P, Album A, Tag T WHERE T.picture_id = P.picture_id AND P.album_id = A.album_id AND T.Tag = '{0}' AND P.user_id ='{1}'".format(tag, uid))
	return cursor.fetchall()

#deal with friends and adding issue
def getFriendList(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id2 FROM Friendship WHERE user_id = '{0}'".format(uid))
	return cursor.fetchall()

def searchUsers(fname='', lname=''):
	cursor = conn.cursor()
	fname=str(fname)
	lname=str(lname)
	if fname != '' and (lname == ''):
		cursor.execute("SELECT fname, lname, dob, email, user_id FROM Users WHERE fname ='{0}'".format(fname))
	elif lname != '' and (fname == ''):
		cursor.execute("SELECT fname, lname, dob, email, user_id FROM Users WHERE lname ='{0}'".format(lname))
	else:
		cursor.execute("SELECT fname, lname, dob, email, user_id FROM Users WHERE fname = '{0}' AND lname ='{1}'".format(fname, lname))
	return cursor.fetchall()

@app.route('/friends', methods = ['GET', 'POST'])
@flask_login.login_required
def friends():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	friends = getFriendList(uid)
	friends_names = []
	for i in friends:
		UserName = getUserName(i)
		friends_names += [UserName]
	if request.method == 'POST':
		first_name = request.form.get('search_first_name')
		last_name = request.form.get('search_last_name')
		if searchUsers(first_name, last_name):
			return render_template('friends.html', friends=friends_names, users_search=searchUsers(first_name,last_name))
		else:
			return render_template('friends.html', friends=friends_names, message="Can not find user with this name")
	else:
		print('it is here')
		return render_template('friends.html', friends=friends_names)

def addFriend(user_id2):
	uid = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	if cursor.execute("SELECT user_id FROM Users WHERE user_id='{0}'".format(user_id2)):
		cursor.execute("INSERT INTO Friendship(user_id, user_id2) VALUES ('{0}', '{1}')".format(uid, user_id2))
		conn.commit()
		return True
	else:
		return False

@app.route('/add_friends', methods=['GET','POST'])
@flask_login.login_required
def friendsAdd():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	friends_names = []
	if request.method == 'POST':
		email = request.form.get('search_email')
		friend_uid = getUserIdFromEmail(email)
		if uid == friend_uid:
			friends = getFriendList(uid)
			for i in friends:
				friends_names += [getUserName(i)]
			return render_template('friends.html', friends=friends_names, message="You can not add yourself as friend! Please try other choice")
		if addFriend(friend_uid) == True:
			friends = getFriendList(uid)
			for i in friends:
				friends_names += [getUserName(i)]
			return render_template('friends.html', friends=friends_names, message="Friend Added!")
		else:
			friends = getFriendList(uid)
			for i in friends:
				friends_names += [getUserName(i)]
			return render_template('friends.html', friends=friends_names, message="Please pick a valid email")
	else:
		return render_template('add_friends.html')

def getUserName(uid):
	uid = uid[0]
	cursor = conn.cursor()
	cursor.execute("SELECT fname, lname FROM Users where user_id = '{0}'".format(uid))
	return cursor.fetchall()

@app.route("/recommend_tags", methods=["GET", "POST"])
@flask_login.login_required
def recommend():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	if request.method == "POST":
		tags = request.form.get("recommend_tags").split(" ")
		recommended_tags = getRecommendedTags(tags, uid)
		return render_template("upload.html", tags=recommended_tags)
	else:
		return render_template("upload.html", message="hmmm, you have a unique thought, no other tagged something similar before")


def getRecommendedTags(tags, uid):
	cursor = conn.cursor()
	query = "SELECT T.Tag, Count(T.Tag) as tcount FROM Tag T, ("
	for i in tags:
		query += "SELECT P.picture_id, T.Tag FROM Pictures P, Album A, Tag T WHERE T.picture_id = P.picture_id AND P.album_id = A.album_id AND T.Tag = '{0}'".format(i)
		query += " UNION "
	query = query[:-7] +  ") as ReTag WHERE ReTag.picture_id = T.picture_id"
	for i in tags:
		query += " AND T.Tag != '{0}'".format(i)
	query += "GROUP BY T.Tag ORDER BY tcount DESC"
	cursor.execute(query)
	return cursor.fetchall()

@app.route("/explore")
@flask_login.login_required
def mayLike():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	photos = []
	pics = getAlsoLike(uid)
	for i in pics: 
		photos += [getPinfo(i)]
	return render_template("showPhotos.html", message="You may also like", photos=photos, user_id = uid)


def getAlsoLike(uid):
	cursor = conn.cursor()
	common_tags = getCommonTags(uid)
	lst = []
	for i in common_tags:
		lst += [i[0]]
	pics = commonTagsPhoto(lst, uid)
	return pics

def getCommonTags(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT T.Tag, Count(T.picture_id) FROM Tag T, Pictures P WHERE P.picture_id = T.picture_id AND P.user_id = '{0}' GROUP BY Tag ORDER BY Count(T.picture_id) DESC LIMIT 5".format(uid))
	return cursor.fetchall()

def commonTagsPhoto(tags, uid):
	cursor = conn.cursor()
	query = "SELECT CTags.picture_id, Count(CTags.picture_id) as Pcount FROM ("
	for i in tags:
		query += "SELECT P.picture_id, T.Tag, P.user_id FROM Pictures P, Tag T WHERE T.picture_id = P.picture_id AND T.Tag = '{0}'".format(i)
		query += " UNION "
	query = query[:-7] +  ") as CTags WHERE CTags.user_id != '{0}' GROUP BY CTags.picture_id ORDER BY Pcount DESC".format(uid)
	cursor.execute(query)
	suggested_photos_id = cursor.fetchall()
	suggested_photos = []
	for i in suggested_photos_id:
		suggested_photos += getPicfromID(i[0])
	return suggested_photos

def getPicfromID(picture_id):
	cursor = conn.cursor()
	cursor.execute("SELECT P.imgdata, P.picture_id, P.caption, A.name FROM Pictures P, Album A WHERE P.album_id = A.album_id and P.picture_id = '{0}'".format(picture_id))
	return cursor.fetchall()

def topUser():
	cursor = conn.cursor()
	cursor.execute("SELECT U.fname, U.lname FROM Users U, (SELECT user_id, SUM(count) as count FROM (SELECT user_id, count(picture_id) AS count FROM Pictures GROUP BY user_id UNION SELECT user_id, count(comment_id) AS count FROM Comment WHERE user_id != -1 GROUP BY user_id ) AS Temp WHERE user_id != -1 GROUP BY user_id) AS user_id_counts WHERE U.user_id = user_id_counts.user_id ORDER BY user_id_counts.count DESC LIMIT 10")
	#cursor.execute("SELECT fname, lname FROM Users WHERE user_id != -1")
	return cursor.fetchall()

@app.route("/guest", methods=['GET'])
def guestVisiting():
	user = User()
	user.id = "guest@bu.edu"
	flask_login.login_user(user)
	return render_template('guest.html', name=flask_login.current_user.id, message="Welcome!", users = topUser())

#default page  
@app.route("/", methods=['GET'])
def hello():
	return render_template('hello.html', message='photoshare.com', users = topUser())


if __name__ == "__main__":
	#this is invoked when in the shell  you run 
	#$ python app.py 
	app.run(port=5000, debug=True)
