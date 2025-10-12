# youtrack-analysis

YouTrack task visualizer. It enables you to answer questions such as:
* Why is a particular task taking so long to complete?
* Why is the recorded "Spent Time" only 2 days while the task seems to have taken 2 weeks?
* Which team member took an unusually long time to complete a review?

and more.


## Features

* Interactive timeline with the issue history
* Tables with detailed information
    * Pivot table (person / spent time by state)
    * Spent time by person
    * Comments
    * On-Hold Periods (with actual and working hours only)
    * Subtasks (and spent time in them)
* Anomaly detector
    * Deadline violation
    * Too long review
    * Too long review with on-hold
    * Exceeding the Scope
    * Increasing the Scope


## Getting Started
1. (For security reasons, optional) Create separate YouTrack account with read-only rights (refer to the [YouTrack account setup](#account-setup) section)
2. Clone the latest release
3. Activate your virtual environment (or any equivalent environment management tool)
4. Install the dependencies: `pip install requirement.txt`
5. Create a configuration file (refer to the [Configuration File](#configuration) section)
6. Launch the server:
    * With default config: `uvicorn app.main:app`
    * Or custom settings: `uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 4` (the complete set of available options can be found [here](https://uvicorn.dev/deployment/#running-from-the-command-line))


## Account Setup

For the security reasons I strongly recommend using this app only with a separate YouTrack account that has read-only permissions. I haven't tested the tool with each permission individually, so therefore I recommend to enable all `Read *` (eg. `Read Issue`, `Read Issue Comment`, etc.) permissions and disable everything else.

The following articles from the official documentation may be helpful:
* [Manage Permissions](https://www.jetbrains.com/help/youtrack/server/manage-permissions.html) — how to change permissions for the account;
* [YouTrack Permissions](https://www.jetbrains.com/help/youtrack/server/youtrack-permissions-reference.html) — a list of all permissions and their description.

Warning! If you are using the application with an account that doesn't have sufficient permissions, it may not cause any errors, but you may not receive the data you want.


## Configuration

Before running the app you should create the `instance.json` file in the project dir. Below, you will find examples of a minimal and an extended configuration:


Minimal `instance.json` example
```
{
    "host": "my_yt.myjetbrains.com",
    "api-key": "Bearer perm:E3Cs3mlbaO==.1TotMTc=.md874yTflsfdcbEzO9wr0JQelqxKfP",
    "support-person": "John Doe"
}
```


Extended `instance.json` example
```
{
    "host": "my_yt.myjetbrains.com",
    "api-key": "Bearer perm:E3Cs3mlbaO==.1TotMTc=.md874yTflsfdcbEzO9wr0JQelqxKfP",
    "support-person": "John Doe",
    "debug": true,
    "projects": {
        "id": {
            "default_values": {
                "scope": "3d"
            }
        }
    }
}
```

**Parameters description:**

* `host`: The hostname of your YouTrack instance (only the hostname is required).
* `api-key`: The API key required for YouTrack API access. Refer to the [official documentation](https://www.jetbrains.com/help/youtrack/devportal/Manage-Permanent-Token.html) for details on obtaining this key.
* `support-person`: The name to be displayed on the error page in case of issues.
* `debug` (optional): Enables debug mode for detailed logging and debugging support (default is `false`).
* `projects` (optional): Various project processing settings (default is empty).
* `projects[N].default_values`: Specifies to use these values instead of empty ones when processing project's custom fields.
