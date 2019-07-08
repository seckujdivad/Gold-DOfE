import multiprocessing as mp
import sqlite3 as sql
import threading
import time
import os


class DBAccess:
    """
    Flexible SQL database slave
    """
    def __init__(self, path, log = None):
        self.path = path
        self._log = log
        
        self._db_connection = None
        self._running = True
        self._funcs = {'close': self._daemonfuncs_close,
                       'commit': self._daemonfuncs_commit}
        
        self.is_new = not os.path.isfile(self.path)
        
        pipe, self._pipe = mp.Pipe()
        
        threading.Thread(target = self._databased, name = 'Database daemon', args = [pipe], daemon = True).start()
    
    def __getattr__(self, item):
        if item in self._funcs:
            return lambda *args, **kwargs: self._generic_func(item, *args, **kwargs)
        else:
            raise AttributeError(item)
    
    def _generic_func(self, func_name, *args, **kwargs):
        master, slave = mp.Pipe()
        
        self._pipe.send([slave, func_name, args, kwargs])
        
        code, result = master.recv()
        
        if code == 0:
            return result
        elif code == 1:
            raise AttributeError(result)
    
    def _databased(self, pipe):
        self._db_connection = sql.connect(self.path)
        
        while self._running:
            master_pipe, func_name, args, kwargs = pipe.recv()
            
            if func_name in self._funcs:
                master_pipe.send((0, self._funcs[func_name](*args, **kwargs)))
            else:
                master_pipe.send((1, 'Function "{}" not found'.format(func_name)))
            
            self._db_connection.commit()
        self._db_connection.close()
    
    def _log_wrapper(self, text):
        'A wrapper for the database log (if it has been specified)'
        if self._log is not None:
            self._log.add('database', text)
    
    ###in-thread functions - should only be called by daemon
    
    def _daemonfuncs_close(self):
        self._running = False
    
    def _daemonfuncs_commit(self):
        self._db_connection.commit()


class ServerDatabase(DBAccess):
    def __init__(self, path, log = None):
        super().__init__(path, log)
        
        self._funcs['add_user'] = self._daemonfuncs_add_user
        self._funcs['user_connected'] = self._daemonfuncs_user_connected
        self._funcs['match_concluded'] = print
        self._funcs['make'] = self._daemonfuncs_make
        self._funcs['get_user_data'] = self._daemonfuncs_get_user_data
        self._funcs['increment_user'] = self._daemonfuncs_increment_user
        self._funcs['get_leaderboard'] = self._daemonfuncs_get_leaderboard
        self._funcs['purge_inactive'] = self._daemonfuncs_purge_inactive

        if self.is_new:
            self.make()
        
    def _daemonfuncs_add_user(self, username):
        'Add a user to the database if the username doesn\'t already exist'
        if self._daemonfuncs_get_user_data(username) is None:
            self._db_connection.execute("INSERT INTO `users` VALUES ((?), (?), 1500.0, 0, 0, '{}')", (username, time.time()))
            self._log_wrapper('Added user {}'.format(username))
            
        else:
            self._log_wrapper('Couldn\'t add user {} - already exists'.format(username))
    
    def _daemonfuncs_user_connected(self, username):
        'Add a user if they don\'t already exist. Update their last connection time if they do'
        if self._daemonfuncs_get_user_data(username) is None:
            self._daemonfuncs_add_user(username)
        self._db_connection.execute("UPDATE users SET lastconn = (?) WHERE username = (?)", (time.time(), username))
        self._log_wrapper('User {} connected'.format(username))
    
    def _daemonfuncs_get_user_data(self, username):
        'Return all information on a user'
        'Finds the data for a user if they exist. If not, returns None'
        data = self._db_connection.execute("SELECT * FROM users WHERE username = (?)", (username,)).fetchall()
        
        if len(data) == 0:
            self._log_wrapper('Couldn\'t find data for {}'.format(username))
            return None
        
        else:
            self._log_wrapper('Found data for {}, {} entry/entries'.format(username, len(data)))
            return data[0]
    
    def _daemonfuncs_make(self):
        'Make the \'users\' table in the database. Overwrites if it already exists'
        self._db_connection.execute("""CREATE TABLE `users` (
	`username`	TEXT,
	`lastconn`	REAL,
	`elo`	REAL,
	`wins`	INTEGER,
	`losses`	INTEGER,
	`metadata`	TEXT
)""")
    
    def _daemonfuncs_increment_user(self, username, elo = 0, wins = 0, losses = 0):
        if self._daemonfuncs_get_user_data(username) is None:
            self._log_wrapper('Couldn\'t find player "{}" in database'.format(username))
        
        else:
            self._db_connection.execute('UPDATE users SET elo = elo + (?), wins = wins + (?), losses = losses + (?) WHERE username = (?)', (elo, wins, losses, username))
    
    def _daemonfuncs_get_leaderboard(self, num):
        cursor = self._db_connection.execute('SELECT username, elo, wins, losses FROM users ORDER BY elo DESC')

        if num == -1:
            return cursor.fetchall()
        
        else:
            i = 0
            last_result = ''
            output = []
            while i < num and last_result is not None:
                last_result = cursor.fetchone()
                if last_result is not None:
                    output.append(last_result)
                i += 1

            return output
    
    def _daemonfuncs_purge_inactive(self, inactive_seconds):
        self._db_connection.execute('DELETE FROM users WHERE lastconn < (?)', (time.time() - inactive_seconds,))