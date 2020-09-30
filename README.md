# Hydro
Simple script to pull hydrological data from weather.gov and send out flood warnings.

Ideally one would want to put this on a cron job to run as often as desired. For my personal use case, I have a raspberry pi 3 set up which runs this script every two days. To automate this on windows, you can use the task scheduler.

On Unix, to set up a cron job create a shell script and copy the following lines of code into it, modifying paths as necessary:

```Bash
#!/bin/bash
. /home/<USER>/.bashrc

/path/to/the/script/Hydro.py
```
Save the script in a convenient location. The same directory as the script is a logical choice.


Then, in the Terminal type crontab -e. Edit the crontab file by entering the following:

```Bash
* * */2 * * /path/to/the/shell/script/<YOUR-FILE-NAME>.sh > /path/to/the/shell/script/cronlog.log 2>&1
```

Save and exit. Your cron job should be operational. The characters * * */2 * * specify the script will run every two days. Feel free to read up on cron to explore other options. The last bit with cronlog.log just creates a log file in the same directory as the shell script that contains any error messages that may be generated when the script runs. Helpful for debugging.
