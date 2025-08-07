import irc.bot
import re
import time
import logging
import socket
from threading import Thread
from collections import defaultdict
import datetime

class VirtualUser:
    """Handles message delivery with proper IRC protocol and maintains presence"""
    def __init__(self, username, message):
        self.username = re.sub(r'[^\w]', '', username)[:9]  # IRC-safe nickname
        self.message = message
        self.log = logging.getLogger('VirtualUser')
        self.irc_socket = None
        self.last_activity = datetime.datetime.now()
        self.active = True

    def send(self):
        try:
            # Establish connection
            self.irc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.irc_socket.connect(("127.0.0.1", 6667))
            
            # IRC registration
            self.irc_socket.send(f"NICK {self.username}\r\n".encode())
            self.irc_socket.send(f"USER {self.username} 0 * :{self.username}\r\n".encode())
            time.sleep(1)  # Critical wait
            
            # Join and message
            self.irc_socket.send(f"JOIN #room2\r\n".encode())
            time.sleep(0.5)
            self.irc_socket.send(f"PRIVMSG #room2 :{self.message}\r\n".encode())
            self.last_activity = datetime.datetime.now()
            
            # Start a thread to monitor and clean up after timeout
            Thread(target=self._monitor_presence).start()
            
            self.log.info(f"{self.username} delivered message and is now present")
            return True
            
        except Exception as e:
            self.log.error(f"Failed to send as {self.username}: {str(e)}")
            self._cleanup()
            return False

    def _monitor_presence(self):
        """Monitor the user's presence and clean up after timeout"""
        try:
            while True:
                time.sleep(10)  # Check every 10 seconds
                inactive_time = (datetime.datetime.now() - self.last_activity).total_seconds()
                
                if inactive_time >= 300:  # 5 minutes
                    self.log.info(f"{self.username} inactive for 5 minutes, cleaning up")
                    self._cleanup()
                    break
        except Exception as e:
            self.log.error(f"Error in presence monitor for {self.username}: {str(e)}")
            self._cleanup()

    def _cleanup(self):
        """Clean up the connection"""
        if self.irc_socket:
            try:
                self.irc_socket.send("QUIT :Inactive\r\n".encode())
                time.sleep(0.5)
                self.irc_socket.close()
            except:
                pass
            finally:
                self.irc_socket = None
        self.active = False

class Bbot(irc.bot.SingleServerIRCBot):
    def __init__(self):
        irc.bot.SingleServerIRCBot.__init__(
            self,
            [("127.0.0.1", 6667)],
            "Bbot",
            "Bbot",
            "Virtual User Gateway"
        )
        self.source_channel = "#room1"
        self.active_users = {}  # Track active virtual users
        
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('bbot.log'),
                logging.StreamHandler()
            ]
        )
        self.log = logging.getLogger('Bbot')
        self.rate_limit = 1.0  # Seconds between virtual user creations

    def on_welcome(self, c, e):
        c.join(self.source_channel)
        self.log.info(f"Monitoring {self.source_channel}")

    def on_pubmsg(self, c, e):
        try:
            # Only process messages in #room1
            if e.target.lower() != self.source_channel.lower():
                return
                
            # Parse Matterbridge format
            msg = e.arguments[0]
            match = re.search(r'\[irc\]\s*<([^>]+)>(.*)', msg)
            if not match:
                self.log.debug(f"Ignoring non-Matterbridge message: {msg}")
                return
                
            username, message = match.groups()
            username = username.strip()
            message = message.strip()
            
            if username.lower() == "bbot":
                return
                
            # Check if this user already exists and is active
            if username in self.active_users and self.active_users[username].active:
                self.log.debug(f"User {username} is already active, reusing connection")
                user = self.active_users[username]
                try:
                    user.irc_socket.send(f"PRIVMSG #room2 :{message}\r\n".encode())
                    user.last_activity = datetime.datetime.now()
                    self.log.info(f"Updated message for {username}")
                except Exception as e:
                    self.log.error(f"Failed to update message for {username}, creating new: {str(e)}")
                    user._cleanup()
                    del self.active_users[username]
                    self._create_new_user(username, message)
            else:
                self._create_new_user(username, message)
                
            time.sleep(self.rate_limit)  # Prevent flooding
            
        except Exception as ex:
            self.log.error(f"Error processing message: {str(ex)}")

    def _create_new_user(self, username, message):
        """Create a new virtual user"""
        user = VirtualUser(username, message)
        if user.send():
            self.active_users[username] = user
            self.log.info(f"Successfully delivered as {username}")
        else:
            self.log.warning(f"Failed to deliver as {username}")

if __name__ == "__main__":
    print("Starting Bbot - Virtual User Gateway")
    print("Debug logs: tail -f bbot.log")
    
    try:
        # Verify IRC server connection
        test_sock = socket.socket()
        test_sock.connect(("127.0.0.1", 6667))
        test_sock.close()
        
        bot = Bbot()
        bot.start()
        
    except ConnectionRefusedError:
        print("ERROR: IRC server not responding at 127.0.0.1:6667")
        print("Verify ngIRCd is running with: systemctl status ngircd")
    except Exception as e:
        print(f"Fatal error: {str(e)}")