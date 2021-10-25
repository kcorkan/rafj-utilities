#!/usr/bin/env python
import sys
import argparse
import os
import requests
import json 
import random
import string
import re
from datetime import datetime

## Version 0.1 
## TODO:  add better logging, error handling, usage documentation

SA_AUTH = '{0}/rest/abl/admin/v2/@authentication'
HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}
SA_LISTENERS = '{0}/rest/abl/admin/v2/admin:listeners'
AUTH_STR = 'CALiveAPICreator {0}:1'
SA_APITOKENS = '{0}/rest/abl/admin/v2/apikey:apikeys'
ADM_API_DEF = '{0}/rest/default/orchestrator/v1/mys:api_def'
FILTER_KEY = 'sysfilter'
FILTER_VALUE = 'equal({0}:\'{1}\')'
verify_cert_path = False

def main():
    p = argparse.ArgumentParser()
    p.add_argument('-t', '--target', default="local", help="URL of the host adapter server. If the adapter is listening on a specific port other than the default, include the port.")
    p.add_argument('-p', '--sa_password', default=None)
    p.add_argument('-c', '--Cert_path', default=False, help='Relative path to a CA cert bundle or directory for verification of SSL certificate for HTTPS requests. Requests verifies SSL certificates for HTTPS requests, just like a web browser. By default, SSL verification is enabled, and Requests will throw a SSLError if it’s unable to verify the certificate.')
    p.add_argument('-o','--old_token', default=None)
    p.add_argument('-n','--new_token_name', default=None)
    p.add_argument('-k','--token', default=None)
    p.add_argument('-l','--token_length',default=24)
    
    p.add_argument("command", nargs=1, help="Command to execute:  list | generate | copy | update_adapter | update_config | disable | enable ")
    
    options = p.parse_args()

    #get SA Auth Key 
  

    #steps 

    # generate token
    # copy token 
    # update listeners 
    # update api defs 
    # disable old token 

    if options.command[0] == 'generate':
        token = get_random_string(int(options.token_length)) 
        print (token)
        return  

    print ('options %s ' % options)

    sa_auth_token = get_sa_auth_key(options.target,options.sa_password,verify_cert_path)
    sa_headers = HEADERS.copy()
    sa_headers['Authorization'] = AUTH_STR.format(sa_auth_token)
    if options.command[0] == 'list':
        token_list(options.target, sa_headers)

    if options.command[0] == 'copy':
        token_copy(options.target, sa_headers, options.old_token,options.token,options.new_token_name)

    if options.command[0] == 'update_adapter':
        token_update_adapter(options.target,sa_headers,options.token)

    if options.command[0] == 'update_config':
        token_update_configuration(options.target,options.token)

    if (options.command[0] == 'disable'):
        token_toggle(options.target,sa_headers,options.token,False)

    if (options.command[0] == 'delete'):
        token_delete(options.target,sa_headers,options.token)


    
  
def get_sa_auth_key(t_system, sa_pwd, verify_cert_path):
    cred_data = {
        'username': 'sa',
        'password': sa_pwd
    }
    cred_data = json.JSONEncoder().encode(cred_data)
    auth_response = requests.post(SA_AUTH.format(t_system),headers=HEADERS,data=cred_data,verify=verify_cert_path)
    print (auth_response.text)
    if (auth_response.status_code > 299):
        print ('Error getting auth token: %s' % auth_response.text)
        print ('URL: %s' % SA_AUTH.format(t_system))
        print ('...RETURNING EMPTY AUTH TOKEN')
    else:
        dict_auth = json.loads(auth_response.text)
        return dict_auth['apikey']
    return ""

def token_list(host,headers):
    params = FILTER_VALUE.format('is_created_by_auth_service','false')
    apikey_resp = requests.get(SA_APITOKENS.format(host),headers=headers,params={'sysfilter': params},verify=verify_cert_path)
    apikeys = json.loads(apikey_resp.text)
    if apikey_resp.status_code > 299:
        print ('Error getting auth token: %s' % apikey_resp.text)
    else:      
        for a in apikeys:
            active_str = ""
            if a['is_active'] == True:
                active_str = "** active"
            print ("{0:10} {1:20} {2:20} {3:64} {4}".format(active_str,a['project_url_name'],a['roles'], a['apikey'], a['name']))

def token_copy(host,headers,old_token,new_token, new_token_name):
    if (new_token_name is None):
        new_token_name = ""

     # get the auth tokens 
    apikey_params = FILTER_VALUE.format('apikey',old_token)
    apikey_resp = requests.get(SA_APITOKENS.format(host),headers=headers,params={'sysfilter': apikey_params},verify=verify_cert_path)
    apikeys = json.loads(apikey_resp.text)
    if apikey_resp.status_code > 299:
        print ('Error getting auth tokens: %s' % apikey_resp.text)
    else: 
        print ('apikey_resp: %s ' % apikey_resp.text)

    new_api_keys = []
    for a in apikeys:
        if (new_token_name is None):
            new_token_name = '{0} copied {1}'.format(a['name'],datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
        a['name'] = new_token_name 
        a['apikey'] = new_token 
        del a['@metadata']
        del a['ident']
        a['is_active'] = True
        new_api_keys.append(a)


    new_api_keys = json.JSONEncoder().encode(new_api_keys)
    newkey_upd_resp = requests.post(SA_APITOKENS.format(host),headers=headers,data=new_api_keys,verify=verify_cert_path)
    if newkey_upd_resp.status_code > 299:
        print('error creating new tokens: %s ' % newkey_upd_resp.text)
    else: 
        print('new token created successfully: %s' % new_token)

def token_toggle(host, headers, token, is_active):
    apikey_params = FILTER_VALUE.format('apikey',token)
    apikey_resp = requests.get(SA_APITOKENS.format(host),headers=headers,params={'sysfilter': apikey_params},verify=verify_cert_path)
    apikeys = json.loads(apikey_resp.text)
    if apikey_resp.status_code > 299:
        print('error')
    else: 
        print ('apikey_resp: %s ' % apikey_resp.text)

    for k in apikeys:
        k['is_active'] = is_active 
    # remove old authtoken 
    apikeys = json.JSONEncoder().encode(apikeys)

    oldkey_upd_resp = requests.put(SA_APITOKENS.format(host),headers=headers,data=apikeys,verify=verify_cert_path)
    if oldkey_upd_resp.status_code > 299:
        print('error toggling tokens: %s ' % oldkey_upd_resp.text)
    else: 
        print('tokens toggled successfully to %s ' % is_active)   

def get_random_string(length):
    # With combination of lower and upper case
    result_str = ''.join(random.choice(string.ascii_letters) for i in range(length))
    return result_str

def token_update_adapter(host,headers,token):
     # get the listeners 
    listener_params = FILTER_VALUE.format('name','initializeConfig')
    listeners_resp = requests.get(SA_LISTENERS.format(host),headers=headers,params={'sysfilter': listener_params},verify=verify_cert_path)
    listeners = json.loads(listeners_resp.text)
    if listeners_resp.status_code > 299:
        print('error')
    else: 
        print ('listeners: %s ' % listeners_resp.text)

    for l in listeners:
        #stop listener first 
        l_url = l['@metadata']['href']
        new_auth_str = 'authToken = "{0}"'.format(token)
        auth_str_re = r"authToken = \".*\""
        new_code = re.sub(auth_str_re,new_auth_str,l['code'])
        l['code'] = new_code
        print('new code %s ' % new_code)
        l['is_active'] = False
        l_data = json.JSONEncoder().encode(l)
        l_resp = requests.put(l_url,headers=headers,data=l_data,verify=verify_cert_path)
        if l_resp.status_code > 299:
            print('error setting listener active to 0: %s ' % l_resp.text)
        else: 
            print ('listener inactivated successfully...') 

        l_resp = json.loads(l_resp.text)
        if len(l_resp['txsummary']) > 0:
            l = l_resp['txsummary'][0]
        
        l['is_active'] = True

        l_data = json.JSONEncoder().encode(l)
       
        l_resp = requests.put(l_url,headers=headers,data=l_data,verify=verify_cert_path)
        if l_resp.status_code > 299:
            print('error updatings listeners: %s ' % l_resp.text)
        else: 
            print ('listeners updated successfully..') 

def token_update_configuration(host,token):
    apidefs_headers = HEADERS
    apidefs_headers['Authorization'] = AUTH_STR.format(token)
    apidefs_resp = requests.get(ADM_API_DEF.format(host),headers=apidefs_headers,verify=verify_cert_path)
    apidefs = json.loads(apidefs_resp.text)
    if apidefs_resp.status_code > 299:
        print('apidefs_resp error: %s ' % apidefs_resp.text)
    else: 
        print ('apidefs_resp: %s ' % apidefs_resp.text)    
    
    apidefs = json.JSONEncoder().encode(apidefs)
    apidefs_update_response = requests.put(ADM_API_DEF.format(host),headers=apidefs_headers,data=apidefs, verify=verify_cert_path)
    if apidefs_update_response.status_code > 299:
        print('error updating apidef tokens: %s ' % apidefs_update_response.text)
    else: 
        print('apidef tokens updated successfully')    

def token_delete(host,headers,token):
     # get the auth tokens 
    apikey_params = FILTER_VALUE.format('apikey',token)
    apikey_resp = requests.get(SA_APITOKENS.format(host),headers=headers,params={'sysfilter': apikey_params},verify=verify_cert_path)
    apikeys = json.loads(apikey_resp.text)
    if apikey_resp.status_code > 299:
        print('error')
    else: 
        print ('apikey_resp: %s ' % apikey_resp.text)

    for a in apikeys:
        a_url = a['@metadata']['href']
        checksum = a['@metadata']['checksum']
        del_resp = requests.delete(a_url,headers=headers,params={'checksum': checksum},verify=verify_cert_path)
        if del_resp.status_code > 299:
            print('error creating new tokens: %s ' % del_resp.text)
        else: 
            print('token deleted successfully: %s' % del_resp.text)

        



if (__name__ == "__main__"):
    main()
