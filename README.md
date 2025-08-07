# Microsoft-Comic-Chat-Twitch-Bot
A pyhron bot that can replicate twitch users in Microsoft comic chat.

First set up a local host IRC server 127.0.0.1 . I use ngircd on linux.

Connect Microsoft Comic Chat to the local host server 127.0.0.1. Create 2 rooms . #room1 and #room2

You need to set up Matters bridge search gifthub 42wim/matterbridge . Set up a secondary account on Twitch , connect the secondary account with admin privaledge on your primary Twitch channel to relay the messages from your twitch chat to #room1 on your local host 127.0.0.1 server . 

Run Bbot.py . it will conect to #room1 and #room2 . Need to have the latest python installed in your system . Screen capture #room2 on your broadcasting application. 

