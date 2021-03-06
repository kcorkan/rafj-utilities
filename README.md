# rafj utilities 
This repository contains 2 script files: 
1.  rafj.py - utility for migration of configurations from one adapter server to another (same source and target systems)
2.  rafj-token.py - utility for managing apikey tokens in the adapter.


## rafj.py Migration Utility
A script for purging or migrating adapter data.  

This scripts contains 2 primary commands: 
1.  purge
2.  migrate

This script expects that the source and target servers are https and a certificate may been needed for verification.  By default, the script does not verify the SSL certificate.  If this default setting is used, the there will be warnings in the output of the script.  

To pass in a certificate bundle or folder for verification, use the -c flag for either of the commands.  

### Pre-requisites 

#### Get Temporary Tokens for authentication
(1) Api token for authentication in **both** the source and target systems.  This token will be used to do all operations in these scripts.  

To create an API token, see instructions [here](https://techdocs.broadcom.com/us/en/ca-enterprise-software/agile-development-and-management/rally-platform-ca-agile-central/rally/integrating-top/connectors/ppm-integrations/adapter-for-jira/jira-adapter-configuration-guide.html) under Configure the App Settings.  Instead of creating a new Dashboard User, you will need to create a new admin user as you will need full read privileges in the source system and full read-write privileges in the target system.  Alternatve instructions for creating a new admin user/token can also be found [here](https://ca-broadcom.wolkenservicedesk.com/external/article?articleId=219256 ).

To get a token to authenticate to the orchestrator API (used for migration and purging), use the following curl command: 
```
curl -X POST -H "Content-Type: application/json" http://x.x.x.x/rest/default/orchestrator/v1/@authentication -d '{"username":"admin", "password":"adminPassword"}' 
```
This will return a response that includes an apiKey, which can be used as a temporary token for authentication as described below.  

Note that depending on how you are making the rest calls, certain characters in the data may need to be escaped.  Refer to your operating system/REST client documentation for more information.  

(2) Access to and server addresses for source and target servers 

(3) If the server certificate is self-signed or internally signed, you may wish to provide the certificate so that calls to the API endpoints are trusted.  By default, the script does not verify. 

#### Migrate 
The migrate command will migrate data as-is from the source to the target adapter servers.  The expectation is that this will be for migrating data and configurations that are related to the same source and target systems.  Example scenario would be moving the adapter to a new virtual server or implemntation.  This cannot be used for migrating configurations between different staging environments because the source and target systems may differ.  

** note: The migrate command must be used with an empty target database because it also migrates identifiers.**

To migrate configurations from source system to a target system:
```
python3 rafj.py migrate -s https://source.server.com -o sourceauthtoken -t https://target.server.com -k targetauthtoken -e configs 
```
The migration of configurations will read all configuration components from the source server and write them to the target server.  The name and "active" setting will be altered during the migration to avoid a running integration from picking it up before the migration is complete.  When the migration is completed, the name and active field will be updated to the original from the source server.  

All system (including authentication data), sync_cfg and cfg_obj settings are migrated.  
No integration_Settings will be migrated.  

To migrate objects from source system to target system:  
```
python3 rafj.py migrate -s https://source.server.com -o sourceauthtoken -t https://target.server.com -k targetauthtoken -e objs -g 1000
```
The migration of objects will only migrate ac_object and jira_object table contents to maintain the relationship between the objects in both systems.  The ac_field and jira_field tables will not be migrated because as they only act as a cache and will be refreshed when the integration is started.  

If there are many objects (e.g. > 10000), you may wish to increase the pagesize to increase migration performance. 

** note: objects can only be migrated after configs as they depend on configuration records ** 

#### Purge
The purge command will clear out the entities that are specified by the -e flag from the database.  

Note that when purging configuration data from the adapter data store, all dependent object and catalyst/reaction data must be purged before configuration data can be removed.  

To purge transient data from a server (this will remove catalyst and reaction data): 
```
python3 rafj.py purge -t https://target.server.to.purge -k targetserverauthtoken -g 1000 -e catalyst
```
To purge state data/object relationships from a server:
** note: do NOT do this in a production environment as this will delete all state data and will result in duplicate items being created in source and target systems **
```
python3 rafj.py purge -t https://target.server.to.purge -k targetserverauthtoken -g 1000 -e objs
```
To purge configuration data from a server: 

** note: all dependent data (state and transient) must be purged before configurations can be purged due to foreign key constraints in the database **
```
python3 rafj.py purge -t https://target.server.to.purge -k targetserverauthtoken -g 1000 -e configs
```

### Usage

python3 rafj.py purge  -t https://x.x.x.x -g (pagesize) -e (entities) [-c (path to cert public key)]
entities are one of the following:
* configs
* objs
* catalysts
* reactions
* archives

python3 rafj.py migrate -s source server -t target_server -e configs|objs|catalysts|reactions  [-g pagesize] [-o source_token] [-k target_token] [-c /path/to/cert.pem]

## rafj-token.py
A script to manage the apikey tokens in the adapter.  The following commands are available: 

* list - lists all tokens that are not auth tokens 
* generate - generates a random token of desired length (default length = 24 if token_length not specified).  The token is NOT added to the apikeys db 
* copy - duplicates an existing token with the same permissions and settings as the old_token specified.  This will be used for replacing a token.
* disable - disables all instances of a token 
* enable - enables all instances of a token 
* update_adapter - updates the adapter with the new token.  **Note that when the adapter service is restarted, the token will revert to the default and this command will to be rerun to avoid errors (assuming the old token has been disabled)**
* update_configuration - updates the auth token in the api_def table

### Pre-requisites
(1) Access to and Server addresses for source and target servers 
(2) The SA Password (**not** the admin password)
(3) If the server certificate is self-signed or internally signed, you may wish to provide the certificate so that calls to the API endpoints are trusted.  By default, the script does not verify. 

### Changing the internal auth token in the adapter
Changing the internal auth token in the adapter will consist of 5 steps:
1.  Generate a new token to use.  Copy the output for use in subsequent commands 

```
rafj-token.py generate 32
```
2.  Copy the default token (or the current token active in the adapter) 

```
rafj-token.py copy -t http://0.0.0.0:8080 -p mySApassword -o tHEoLDToKeN123 -k myNeWToKeNezMbq23Dlg [-n My New Token Name]
```
3.  Once the new token has been created successfully, update the adapter code with the new token 

```
rafj-token.py update_adapter -t http://0.0.0.0:8080 -p mySAPassword -k myNeWToKeNezMbq23Dlg
```
4.  Update the configuration with the new token 

```
rafj-token.py update_config -t http://0.0.0.0:8080 -k myNeWToKeNezMbq23Dlg
```
5.  Disable the old token 

```
rafj-token.py disable -t http://0.0.0.0:8080 -p mySAPassword -k tHEoLDToKeN123
``` 
6.  Start the adapter and test the adapter to confirm that all works as expected. 
 
8.  [OPTIONAL] If working as expected, delete the old token, if desired: 

```
rafj-token.py delete -t http://0.0.0.0:8080 -p mySAPassword -k tHEoLDToKeN123
```

### Usage 
python3 rafj-token.py list  -t https://x.x.x.x -p mySApassword [-c /path/to/cert.pem]

python3 rafj-token.py generate  [-l desired token length] [-c /path/to/cert.pem]

python3 rafj-token.py copy -t https://x.x.x.x -p mySApassword -o oldToken -k newToken [-n newTokenName] [-c /path/to/cert.pem]

python3 rafj-token.py disable -t https://x.x.x.x -p mySApassword -k tokenToDisable [-c /path/to/cert.pem]

python3 rafj-token.py enable -t https://x.x.x.x -p mySApassword -k tokenToENable [-c /path/to/cert.pem]

python3 rafj-token.py delete -t https://x.x.x.x -p mySApassword -k tokenToDelete [-c /path/to/cert.pem]

python3 rafj-token.py update_adapter -t https://x.x.x.x -p mySApassword -k new_token [-c /path/to/cert.pem]

python3 rafj-token.py update_config -t https://x.x.x.x -p mySApassword -k new_token [-c /path/to/cert.pem]


## Installation
To install this project's package run:
```
pip install /path/to/rafj
```
To install the package in editable mode, use:
```
pip install --editable /path/to/rafj
```


