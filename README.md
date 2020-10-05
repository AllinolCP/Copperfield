# Magician-Python
A Club Penguin Rewritten private server written in Python 3

# Set up

Drag this into your kitsune folder & then edit world.php to include html5 = true, once done that you should be good. thank you

Ok! So step 1

open the kitsune folder 
open the database.xml
on line 8 add

'<structure>html5=true</structure>

save

open "Events.php"

add a new line at the bottom saying

	public static function GetHTML5Events() {
		return self::$HTML5Events;
	}
  
  Save and exit.

Now lastly, open World.php. 

Change all "http://media1.clubpenguin.com" to CPREWRITTEN.net

AFTER THIS you start the html5 servers & the kitsune php servers. 

You will now have a fully functional html5 cpps. It even has Card Jitsu Snow!
