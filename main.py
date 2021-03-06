#!/usr/bin/python3

# Lots of library imports
import asyncore
import re
import sqlite3
import cgi
from collections import Counter
from string import punctuation
from math import sqrt
from http.server import BaseHTTPRequestHandler, HTTPServer
from os import curdir, sep, popen
import platform
import webbrowser

# initialize the connection to the database
connection = sqlite3.connect('bot.sqlite')
cursor = connection.cursor()
# Variable to store the response
B = "Hello"

# Address where the server will listen
IPADDR = "127.0.0.1"
PORT_NUMBER = 8080

# -- OPTIONAL --
# Uncomment the following lines to enable the TCP server. You can chat with your
# bot using telnet! (Or client.py)
# HOST = "127.0.0.1"
# PORT = "8070"
# HOST, PORT = input("Local TCP IP: "),int(input("Local TCP port: "))

# There are another 3 lines at the bottom that you must uncomment to enable
# the TCP server!

#This class will handles any incoming request from
#the browser 
class myHandler(BaseHTTPRequestHandler):
    # Boolean that indicates if the file is binary or not
    bts = True
    #Handler for the GET requests
    def do_GET(self):
        global bts
        if self.path=="/":
            self.path="client.html" # This is our index file
        
        try:
            #Check the file extension required and
            #set the right mime type

            sendReply = False
            if self.path.endswith(".html"):
                mimetype='text/html'
                sendReply = True
                self.bts = False
            if self.path.endswith(".jpg"):
                mimetype='image/jpg'
                sendReply = True
                self.bts = True
            if self.path.endswith(".png"):
                mimetype='image/png'
                sendReply = True
                self.bts = True
            if self.path.endswith(".gif"):
                mimetype='image/gif'
                sendReply = True
                self.bts = True
            if self.path.endswith(".js"):
                mimetype='application/javascript'
                sendReply = True
                self.bts = False
            if self.path.endswith(".css"):
                mimetype='text/css'
                sendReply = True
                self.bts = False

            if sendReply == True:
                #Open the static file requested and send it
                if self.bts:
                    print("Serving bytes: " + curdir + sep + self.path)
                    f = open(curdir + sep + self.path, 'rb')
                else:
                    print("Serving text: " + curdir + sep + self.path)
                    f = open(curdir + sep + self.path)  
                self.send_response(200)
                self.send_header('Content-type',mimetype)
                self.end_headers()
                if self.bts:
                    self.wfile.write(f.read())
                else:
                    self.wfile.write(f.read().encode('utf-8')) 
                f.close()
            return
        # If the file does not exist, post an error
        except IOError:
            self.send_error(404,'File Not Found: %s' % self.path)

    # Handle the POST requests. This is the user input.
    def do_POST(self):
        # "/send" is a virtual path where the information is sent to the bot
        if self.path=="/send":
            # Handle the request
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD':'POST',
                         'CONTENT_TYPE':self.headers['Content-Type'],
                         })
            # Handle the user input
            print("Post: " + form["userinput"].value)
            # This sends the input to the bot
            process_ui(form["userinput"].value)
            # Send the generated response back to the client
            self.send_response(200)
            self.end_headers()
            self.wfile.write(B.encode("utf-8"))
            return


# This is a TCP handler
class BotHandler(asyncore.dispatcher_with_send):
    
    def handle_read(self):
        data = self.recv(4096).strip()
        if data:
            print(">", data.decode('utf-8'))
            process_ui(data.decode('utf-8'))
            print(">>", B)
            self.send((B + '\n').encode('utf-8'))
            
# This is a TCP server
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

# - BOT CODE FUNCTIONS -
# Code based on https://rodic.fr/blog/python-chatbot-1/
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

def get_ip_info():
    # Get ipv4 address based on client OS
    ip_regex = re.compile(r'[0-9]+(?:\.[0-9]+){3}')
    command = "ipconfig | grep -iF 192.168.1." if platform.system() == "Windows" else "ifconfig | grep -iF 192.168.1."
    ip_info = popen(command).read()

    matches = ip_regex.findall(ip_info)
    
    # Should always be the first match
    if matches:
        return matches[0]
    return "127.0.0.1"

# -- MAIN FUNCTION --
if __name__ == '__main__':
    ipv4_address = get_ip_info()

    print("Your IPv4 Address is: {}".format(ipv4_address))
    choice = input("Would you like to connect to {} on port 8080, i.e., {}:8080? (Y/N) ".format(ipv4_address, ipv4_address)).lower()

    IPADDR, PORT_NUMBER = input("Local web IP: ") if choice == "n" else ipv4_address, int(input("Local web port: ")) if choice == "n" else 8080
    
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
    
    # Start the web server
    try:
        #Create a web server and define the handler to manage the
        #incoming request
        server = HTTPServer((IPADDR, PORT_NUMBER), myHandler)
        print ("Started httpserver on port " , PORT_NUMBER)
        
        # Uncomment these lines AND THE LINES AT THE BEGGINING to enable the TCP server
        # tcpserver = BotServer(HOST, PORT)
        # asyncore.loop()
        # print ("Started tcpserver on port " , PORT)

         # Open URL in new window, raising the window if possible.
        webbrowser.open_new("{}:{}".format(IPADDR, PORT_NUMBER))
        
        #Wait forever for incoming htto requests
        server.serve_forever()

    except KeyboardInterrupt:
        print ("^C received, shutting down the web server")
        server.socket.close()
