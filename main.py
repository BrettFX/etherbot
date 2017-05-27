#!/usr/bin/python3

import asyncore
import re
import sqlite3
import cgi
#import http.server
from collections import Counter
from string import punctuation
from math import sqrt
#from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from http.server import BaseHTTPRequestHandler, HTTPServer
from os import curdir, sep

# initialize the connection to the database
connection = sqlite3.connect('bot.sqlite')
cursor = connection.cursor()
B = "Hello"

IPADDR = "192.168.1.124"
PORT_NUMBER = 8080
IPADDR, PORT_NUMBER = input("Local IP: "),int(input("Local port: "))
bts = True

#This class will handles any incoming request from
#the browser 
class myHandler(BaseHTTPRequestHandler):
    #Handler for the GET requests
    def do_GET(self):
        global bts
        if self.path=="/":
            self.path="client.html"
        elif self.path.endswith(".png"):
            print("Image: " + self.path)
        
        try:
			#Check the file extension required and
			#set the right mime type

            sendReply = False
            if self.path.endswith(".html"):
                mimetype='text/html'
                sendReply = True
                bts = False
            if self.path.endswith(".jpg"):
                mimetype='image/jpg'
                sendReply = True
                bts = True
            if self.path.endswith(".png"):
                mimetype='image/png'
                sendReply = True
                bts = True
            if self.path.endswith(".gif"):
                mimetype='image/gif'
                sendReply = True
                bts = True
            if self.path.endswith(".js"):
                mimetype='application/javascript'
                sendReply = True
                bts = False
            if self.path.endswith(".css"):
                mimetype='text/css'
                sendReply = True
                bts = False

            if sendReply == True:
                #Open the static file requested and send it
                if bts:
                    print("Serving bytes: " + curdir + sep + self.path)
                    f = open(curdir + sep + self.path, 'rb')
                else:
                    print("Serving text: " + curdir + sep + self.path)
                    f = open(curdir + sep + self.path)  
                self.send_response(200)
                self.send_header('Content-type',mimetype)
                self.end_headers()
                if bts:
                    self.wfile.write(f.read())
                else:
                    self.wfile.write(f.read().encode('utf-8')) 
                f.close()
            return
        except IOError:
            self.send_error(404,'File Not Found: %s' % self.path)

    def do_POST(self):
        if self.path=="/send":
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD':'POST',
                         'CONTENT_TYPE':self.headers['Content-Type'],
                         })
                
            print("Post: " + form["userinput"].value)
            process_ui(form["userinput"].value)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(B.encode("utf-8"))
            return



class BotHandler(asyncore.dispatcher_with_send):
    
    def handle_read(self):
        data = self.recv(4096).strip()
        if data:
            print(">", data.decode('utf-8'))
            process_ui(data.decode('utf-8'))
            print(">>", B)
            self.send(B.append('\n').encode('utf-8'))

class BotServer(asyncore.dispatcher):
    
    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket()
        self.set_reuse_addr()
        self.bind((host,port))
        self.listen(5)
        
    def handle_accepted(self,sock,addr):
        print('Incoming connection from %s' % repr(addr))
        handler = BotHandler(sock)

def get_id(entityName, text):
    """Retrieve an entity's unique ID from the database, given its associated text.
    If the row is not already present, it is inserted.
    The entity can either be a sentence or a word."""
    tableName = entityName + 's'
    columnName = entityName
    cursor.execute('SELECT rowid FROM ' + tableName + ' WHERE ' + columnName + ' = ?', (text,))
    row = cursor.fetchone()
    if row:
        return row[0]
    else:
        cursor.execute('INSERT INTO ' + tableName + ' (' + columnName + ') VALUES (?)', (text,))
        return cursor.lastrowid
 
def get_words(text):
    """Retrieve the words present in a given string of text.
    The return value is a list of tuples where the first member is a lowercase word,
    and the second member the number of time it is present in the text."""
    wordsRegexpString = '(?:\w+|[' + re.escape(punctuation) + ']+)'
    wordsRegexp = re.compile(wordsRegexpString)
    wordsList = wordsRegexp.findall(text.lower())
    return Counter(wordsList).items()

def process_ui(H):
    global B
    # store the association between the bot's message words and the user's response
    words = get_words(B)
    words_length = sum([n * len(word) for word, n in words])
    sentence_id = get_id('sentence', H)
    for word, n in words:
        word_id = get_id('word', word)
        weight = sqrt(n / float(words_length))
        cursor.execute('INSERT INTO associations VALUES (?, ?, ?)', (word_id, sentence_id, weight))
    connection.commit()
    # retrieve the most likely answer from the database
    cursor.execute('CREATE TEMPORARY TABLE results(sentence_id INT, sentence TEXT, weight REAL)')
    words = get_words(H)
    words_length = sum([n * len(word) for word, n in words])
    for word, n in words:
        weight = sqrt(n / float(words_length))
        cursor.execute('INSERT INTO results SELECT associations.sentence_id, sentences.sentence, ?*associations.weight/(4+sentences.used) FROM words INNER JOIN associations ON associations.word_id=words.rowid INNER JOIN sentences ON sentences.rowid=associations.sentence_id WHERE words.word=?', (weight, word,))
    # if matches were found, give the best one
    cursor.execute('SELECT sentence_id, sentence, SUM(weight) AS sum_weight FROM results GROUP BY sentence_id ORDER BY sum_weight DESC LIMIT 1')
    row = cursor.fetchone()
    cursor.execute('DROP TABLE results')
    # otherwise, just randomly pick one of the least used sentences
    if row is None:
        cursor.execute('SELECT rowid, sentence FROM sentences WHERE used = (SELECT MIN(used) FROM sentences) ORDER BY RANDOM() LIMIT 1')
        row = cursor.fetchone()
    # tell the database the sentence has been used once more, and prepare the sentence
    B = row[1]
    cursor.execute('UPDATE sentences SET used=used+1 WHERE rowid=?', (row[0],)) 

if __name__ == '__main__':
    
    # create the tables needed by the program
    create_table_request_list = [
        'CREATE TABLE words(word TEXT UNIQUE)',
        'CREATE TABLE sentences(sentence TEXT UNIQUE, used INT NOT NULL DEFAULT 0)',
        'CREATE TABLE associations (word_id INT NOT NULL, sentence_id INT NOT NULL, weight REAL NOT NULL)',
    ]
    for create_table_request in create_table_request_list:
        try:
            cursor.execute(create_table_request)
        except:
            pass
    
    try:
        #Create a web server and define the handler to manage the
        #incoming request
        server = HTTPServer((IPADDR, PORT_NUMBER), myHandler)
        print ("Started httpserver on port " , PORT_NUMBER)
        
        #Wait forever for incoming htto requests
        server.serve_forever()

    except KeyboardInterrupt:
        print ("^C received, shutting down the web server")
        server.socket.close()
    
    #HOST, PORT = input("Local IP: "),int(input("Local port: "))
    #server = BotServer(HOST, PORT)
    #asyncore.loop()
