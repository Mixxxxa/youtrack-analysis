# youtrack-analysis

Simple YouTrack task visualizer. It enables you to answer questions such as:
* Why is a particular task taking so long to complete?
* Why is the recorded "Spent Time" only 2 days while the task seems to have taken 2 weeks?
* Which team member took an unusually long time to complete a review?

and more.


## Getting Started
1. Activate your virtual environment (or any equivalent environment management tool)
2. Install the dependencies: `pip install requirement.txt`
3. Create a configuration file (refer to the [Configuration File](#configuration) section)
4. Launch the server using the command: `python -m main -c config_name.cfg`
5. Feel free to modify anything
6. Think about security. Launch ` gunicorn -w 4 'main:app'`


## Configuration

The application requires a configuration file in JSON format. Below, you will find examples of a minimal and an extended configuration:


Minimal `.conf` example
```
{
    "host": "my_yt.myjetbrains.com",
    "api-key": "Bearer perm:E3Cs3mlbaO==.1TotMTc=.md874yTflsfdcbEzO9wr0JQelqxKfP",
    "support-person": "John Doe"
}
```


Extended `.conf` example
```
{
    "host": "my_yt.myjetbrains.com",
    "api-key": "Bearer perm:E3Cs3mlbaO==.1TotMTc=.md874yTflsfdcbEzO9wr0JQelqxKfP",
    "support-person": "John Doe",
    "port": 8080,
    "debug": true
}
```

**Parameters description:**

* `host`: The hostname of your YouTrack instance (only the hostname is required).
* `api-key`: The API key required for YouTrack API access. Refer to the [official documentation](https://www.jetbrains.com/help/youtrack/devportal/Manage-Permanent-Token.html) for details on obtaining this key.
* `support-person`: The name to be displayed on the error page in case of issues.
* `port` (optional): The port on which the web server will run (default is `8080`).
* `debug` (optional): Enables debug mode for detailed logging and debugging support (default is `false`).
