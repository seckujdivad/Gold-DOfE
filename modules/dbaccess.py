import multiprocessing as mp
import sqlite3 as sql
import threading
import time

class ServerDatabase:
    def __init__(self, path, log = None):
        self.path = path
        self.log = log
        
        pipe, self.pipe = mp.Pipe()
        
        threading.Thread(target = self.databasecontrollerd, name = 'Server database controller daemon', args = [pipe]).start()
    
    def databasecontrollerd(self, input_pipe):
        database_is_new = False
        if not os.path.isfile(self.path):
            database_is_new = True
            
        self.connection = sql.connect(self.path)
        
        if database_is_new:
            self._make()
        
        self._log_wrapper('Connected to SQLite database at {}'.format(self.path))
        
        cont = True
        while cont:
            data = input_pipe.recv()
            
            if len(data) == 2:
                task, arguments = data
                
                self._log_wrapper('Received command #{} with arguments {}'.format(task, arguments))
                
                if task == self.lookup.make:
                    self._make()
                elif task == self.lookup.disconnect:
                    cont = False
                elif task == self.lookup.user_connected:
                    self._user_connected(arguments[0])
                elif task == self.lookup.match_concluded:
                    self._match_concluded(arguments[0], arguments[1])
                elif task == self.lookup.get_user_data:
                    self.output.dictionary[arguments[1]] = self._get_user_data(arguments[0])
                else:
                    self._log_wrapper('Uncaught command #{}'.format(task))
            else:
                self._log_wrapper('Command must be of length 2, not {}'.format(len(data)))
            self.connection.commit()
        self.connection.close()
        
    def _make(self):
        'Make the \'users\' table in the database. Overwrites if it already exists'
        self.connection.execute("""CREATE TABLE `users` (
	`username`	TEXT,
	`lastconn`	REAL,
	`elo`	REAL,
	`wins`	INTEGER,
	`losses`	INTEGER,
	`metadata`	TEXT
)""")
        self._log_wrapper('Made user table')
    
    def _add_user(self, username):
        'Add a user to the database if the username doesn\'t already exist'
        if self._get_user_data(username) == None:
            self.connection.execute("INSERT INTO `users` VALUES ((?), (?), 1500.0, 0, 0, '{}')", (username, time.time()))
            self._log_wrapper('Added user {}'.format(username))
        else:
            self._log_wrapper('Couldn\'t add user {}'.format(username))
            raise ValueError('Username "{}" is already in use'.format(username))
    
    def _user_connected(self, username):
        'Add a user if they don\'t already exist. Update their last connection time if they do'
        if self._get_user_data(username) == None:
            self._add_user(username)
        self.connection.execute("UPDATE users SET lastconn = (?) WHERE username = (?)", (time.time(), username))
        self._log_wrapper('User {} connected'.format(username))
    
    def _match_concluded(self, winner_name, loser_name):
        'Update win/loss records for two users'
        if (not self._get_user_data(winner_name) == None) and (not self._get_user_data(winner_name) == None):
            self.connection.execute('UPDATE users SET wins = wins + 1 WHERE username = (?)', (winner_name,))
            self.connection.execute('UPDATE users SET losses = losses + 1 WHERE username = (?)', (loser_name,))
            self._log_wrapper('{} beat {}, stored in database'.format(winner_name, loser_name))
        else:
            self._log_wrapper('Couldn\'t find either {} or {}'.format(winner_name, loser_name))
            raise ValueError('Either {} or {} do not exist'.format(winner_name, loser_name))
    
    def _get_user_data(self, username):
        'Return all information on a user'
        'Finds the data for a user if they exist. If not, returns None'
        data = self.connection.execute("SELECT * FROM users WHERE username = (?)", (username,)).fetchall()
        
        if len(data) == 0:
            self._log_wrapper('Couldn\'t find data for {}'.format(username))
            return None
        else:
            self._log_wrapper('Found data for {}, {} entry/entries'.format(username, len(data)))
            return data[0]
    
    def _log_wrapper(self, text):
        'A wrapper for the database log (if it has been specified)'
        if not self.log == None:
            self.log.add('database', text)
    
    class lookup:
        make = 0
        disconnect = 1
        user_connected = 2
        match_concluded = 3
        get_user_data = 4
    
    class output:
        ticket = 0
        dictionary = {}
    
    def make(self):
        'Make the \'users\' table in the database. Overwrites if it already exists'
        self.pipe.send([self.lookup.make, []])
    
    def disconnect(self):
        'Disconnect from the database'
        self.pipe.send([self.lookup.disconnect, []])
    
    def user_connected(self, username):
        'Updates the last connection time on a user'
        self.pipe.send([self.lookup.user_connected, [username]])
        print('{} connected'.format(username))
    
    def match_concluded(self, winner_name, loser_name):
        self.pipe.send([self.lookup.match_concluded, [winner_name, loser_name]])
    
    def get_user_data(self, username):
        ticket = str(self.output.ticket)
        self.output.ticket += 1
        
        self.pipe.send([self.lookup.get_user_data, [username, ticket]])
        
        while not ticket in self.output.dictionary:
            time.sleep(0.05)
        return self.output.dictionary.pop(ticket)