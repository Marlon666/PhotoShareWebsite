CREATE DATABASE photoshare;
USE photoshare;
DROP TABLE Pictures CASCADE;
DROP TABLE Users CASCADE;

CREATE TABLE Users(
    user_id int4  AUTO_INCREMENT,
    email varchar(255) UNIQUE,
    password varchar(255),
    fname varchar(20),
    lname varchar(20),
    DOB varchar(255),
    hometown varchar(255),
    gender varchar(10),
  CONSTRAINT users_pk PRIMARY KEY (user_id)
);

CREATE TABLE Friendship(
    user_id int4,
    user_id2 int4,
    PRIMARY KEY(user_id, user_id2),
    FOREIGN KEY(user_id) REFERENCES Users(user_id),
    FOREIGN KEY(user_id2) REFERENCES Users(user_id)
);

CREATE TABLE Album(
    album_id int4 AUTO_INCREMENT NOT NULL,
    user_id int4 NOT NULL,
    DOC DATE,
    name varchar(255),
    PRIMARY KEY(album_id),
    FOREIGN KEY(user_id) REFERENCES Users(user_id)
);

CREATE TABLE Pictures(
  picture_id int4  AUTO_INCREMENT,
  user_id int4,
  imgdata longblob,
  caption VARCHAR(255),
  INDEX upid_idx (user_id),
  album_id int4,
  CONSTRAINT pictures_pk PRIMARY KEY (picture_id),
  FOREIGN KEY(album_id) REFERENCES Album(album_id)
);

CREATE TABLE Tag(
    Tag varchar(20),
    picture_id int4 NOT NULL,
    FOREIGN KEY(picture_id) REFERENCES Pictures(picture_id)
);

CREATE TABLE Comment(
    comment_id int4 NOT NULL AUTO_INCREMENT,
    user_id int4 NOT NULL,
    picture_id int4,
    comment varchar(1000),
    DOC DATE,
    PRIMARY KEY(comment_id),
    FOREIGN KEY(user_id) REFERENCES Users(user_id),
    FOREIGN KEY(picture_id) REFERENCES Pictures(picture_id)
);

CREATE TABLE Likes(
    picture_id int4,
    user_id int4,
    FOREIGN KEY(picture_id) REFERENCES Pictures(picture_id),
    FOREIGN KEY(user_id) REFERENCES Users(user_id)
);

CREATE TABLE UserAvatar(
    user_id int4,
    imgdata longblob,
    PRIMARY KEY(user_id)
);

INSERT INTO Users (user_id, email, password) VALUES (-1, 'guest@bu.edu', 'test');
INSERT INTO Users (email, password) VALUES ('test1@bu.edu', 'test');
