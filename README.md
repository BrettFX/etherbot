# EtherBot
## Your own cleverbot using Python 3!

### How to run EtherBot
First, add execution rights to your main.py module:

> sudo chmod +x main.py

Then run it!

> $ ./main.py

Or in windows:

>python main.py

Then connect to the server using your web browser with the IP and PORT specified. Done!

Remove the file bot.sqlite to create a new database. This database will be autogenerated when you run the server.
When you start a new database, the bot will try to copy what you say rather than generating proper output. This is normal behaviour, just keep replying the best you can until the bot gets the hang of it.

The bot is not very smart but it works OK. Don't get too attached to your bot.

Uncomment the TCP server to enable it. You can later connect to the TCP server using the provided client.py script, or even telnet or a similar program!
