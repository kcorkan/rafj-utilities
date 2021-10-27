#!/usr/bin/env python
import sys
import argparse
import os
import requests
import json 
from urllib import parse

configs = {
    'jsystem': '{0}/rest/default/orchestrator/v1/mys:jira_system',
    'jfield_def': '{0}/rest/default/orchestrator/v1/mys:jira_field_def',
    'jsync_cfg':'{0}/rest/default/orchestrator/v1/mys:jira_sync_cfg',
    'jsync_cfg_fld':'{0}/rest/default/orchestrator/v1/mys:jira_sync_cfg_fld',
    'asystem': '{0}/rest/default/orchestrator/v1/mys:ac_system',
    'afield_def': '{0}/rest/default/orchestrator/v1/mys:ac_field_def',
    'async_cfg': '{0}/rest/default/orchestrator/v1/mys:ac_sync_cfg',
    'async_cfg_fld': '{0}/rest/default/orchestrator/v1/mys:ac_sync_cfg_fld',
    'cfg_obj': '{0}/rest/default/orchestrator/v1/mys:cfg_obj',
    'cfg_obj_fld': '{0}/rest/default/orchestrator/v1/mys:cfg_obj_fld',
    'cfg_obj_fld_map': '{0}/rest/default/orchestrator/v1/mys:cfg_obj_fld_map'
}
objs = {
     'jobject': '{0}/rest/default/orchestrator/v1/mys:jira_object',
     'aobject': '{0}/rest/default/orchestrator/v1/mys:ac_object',
}
catalyst = {
    'catalyst': '{0}/rest/default/orchestrator/v1/mys:catalyst'
}
reactions = {
     'reaction': '{0}/rest/default/orchestrator/v1/mys:reaction'
}
archives = {
    'classifier': '{0}/rest/default/orchestrator/v1/mys:message_classifier',
    'errors_archive': '{0}/rest/default/orchestrator/v1/mys:errors_archive',
    'reactions_archive': '{0}/rest/default/orchestrator/v1/mys:reactions_archive'
}
forbidden_keys = ['@metadata','webhook_id','payloadToObjSpec','catalyst_to_reaction_spec','webhook_to_object_spec']
verify_cert_path = False #'kotsadm.pem'

auth_str = 'CALiveAPICreator {0}:1'

#python3 migrate_cfgs.py purge  -t https://x.x.x.x -g 5000 -e archives

def main():
    p = argparse.ArgumentParser()
    p.add_argument('-s', '--src', default="local", help="URL of the source adapter server if reading data for a migration. If the adapter is listening on a specific port other than the default, include the port.")
    p.add_argument('-t', '--target', default="local", help="URL of the target adapter server. If the adapter is listening on a specific port other than the default, include the port.")
    p.add_argument('-o', '--src_token', help="auth token for the source.  Must have administrative privileges.  To create a new admin token, refer to https://ca-broadcom.wolkenservicedesk.com/external/article?articleId=219256 ")
    p.add_argument('-k', '--target_token', help="auth token for the target.  Must have administrative privileges.   To create a new admin token, refer to https://ca-broadcom.wolkenservicedesk.com/external/article?articleId=219256 ")
    p.add_argument('-g', '--pagesize', default=500, help="Pagesize to use when fetching from the source.")
    p.add_argument('-e', '--entities', help='Entities to run the command on.  Valid options are:\n\nconfigs - will migrate or purge all configuration tables\n\nobjs - all object relationships (ac_object, jira_object)\ncatalyst - contents of the catalyst table (not recommended for migration)\nreactions - contents of the reactions table (not recommended for migration)\narchives - recommended for archive tables')
    p.add_argument('-c', '--cert_path', default=False, help='Relative path to a CA cert bundle or directory for verification of SSL certificate for HTTPS requests. Requests verifies SSL certificates for HTTPS requests, just like a web browser. By default, SSL verification is enabled, and Requests will throw a SSLError if it’s unable to verify the certificate.')

    p.add_argument("command", nargs=1, help="Command to execute:  migrate | purge")
    
    options = p.parse_args()
    pagesize = options.pagesize

    print ('Source %s' % options.src)
    print ('Target %s' % options.target)
    
    src_headers = {
        'Authorization': auth_str.format(options.src_token)
    }
    tgt_headers = { 
        'Authorization': auth_str.format(options.target_token),
        'Content-Type': 'application/json'
    }
  
    entities = options.entities
    if (entities == None):
        print ('Please specify entities for the action')
        return
    if (entities not in globals().keys()):
        print ('Unrecognized entities named: %s' % entities)
        return

    entities_objs = globals()[entities]

    if options.cert_path != False:
        verify_cert_path = options.cert_path
    else: 
        print ("*** Running without SSL Certificate Verification ***")

    if options.command[0] == 'migrate':
        print (entities)
        if entities == 'configs':
            print ("migrate configs")
            migrate_configs(options.src,src_headers,options.target,tgt_headers,pagesize=pagesize)
        else: 
            print ("migrate other")
            migrate_entities(options.src,src_headers,options.target,tgt_headers,pagesize=pagesize,entities=entities_objs)

    if options.command[0] == 'purge':
        clean_tables(options.target,tgt_headers,pagesize=pagesize,entities=entities_objs)


def migrate_entities(s_system, s_headers, t_system, t_headers,pagesize, entities):
    for e in entities:
        print ('Migrating %s ...' % e)
        src = entities[e].format(s_system)
        tgt = entities[e].format(t_system)
        print("FROM %s " % src)
        print("TO %s " % tgt)
        extract_and_load(src,s_headers,tgt,t_headers,pagesize)
        

def migrate_configs(s_system, s_headers, t_system, t_headers,pagesize):
    migrate_entities(s_system, s_headers, t_system, t_headers, pagesize,configs) 
    exclude_fields = ['id','ident']
    #update_table(configs['jfield_def'].format(s_system),s_headers,configs['jfield_def'].format(t_system),t_headers,exclude_fields,[],pagesize)
    #update_table(configs['afield_def'].format(s_system),s_headers,configs['afield_def'].format(t_system),t_headers,exclude_fields,[],pagesize)
    print ("update_table")
    update_table(configs['cfg_obj'].format(s_system),s_headers,configs['cfg_obj'].format(t_system),t_headers,forbidden_keys,['name','active'],pagesize)

def extract_and_load(s_system,s_headers,t_system, t_headers,pagesize):
    next_batch = s_system 
    is_cfg_obj = s_system.find('cfg_obj') > -1
    is_cfg_obj_fld = s_system.find('cfg_obj_fld') > -1

    while next_batch != None:
        next_url = '{0}://{1}{2}'.format(parse.urlsplit(next_batch).scheme, parse.urlsplit(next_batch).netloc, parse.urlsplit(next_batch).path)
        next_params = dict(parse.parse_qsl(parse.urlsplit(next_batch).query))
        next_params['pagesize'] = pagesize
        response = requests.get(next_url,headers=s_headers,params=next_params,verify=verify_cert_path)
        print ('EXTRACT REQUEST: %s' % response.text)
        
        dict_payload = json.loads(response.text)
        if response.status_code > 299:
            print ('Error extracting %s' % response.status_code)
            if dict_payload['errorMessage']: 
                print(dict_payload['errorMessage'])
            return 
    
        next_batch = None
        print ('...found %s records...' % len(dict_payload))
        for o in dict_payload: 
            if '@metadata' in o.keys():
                if 'next_batch' in o['@metadata'].keys():
                    next_batch = o['@metadata']['next_batch']
                    dict_payload.pop()
                    pass 
                else: 
                    del o['@metadata']

            for key in forbidden_keys:
                if key in o.keys():
                    del o[key]

            for e in o:
                if is_cfg_obj and not is_cfg_obj_fld:
                    if e == 'name':
                        o[e] = '__test__{0}'.format(o[e])
                    if e == 'active':
                        o[e] = 0

                if type(o[e]) == str:
                    o[e] = o[e].rstrip() #some of the system fields may have unintended padding on the end.

        str_payload_clean = json.JSONEncoder().encode(dict_payload)
        
        t_response = requests.post(t_system,headers=t_headers,data=str_payload_clean,verify=verify_cert_path)
        print ('LOAD RESPONSE: %s' % t_response.text)
        if (t_response.status_code > 299):
            print (t_response.text)
        else: 
            print ('success! %s records migrated ' % len(dict_payload))
        
def update_table(s_system,s_headers,t_system, t_headers, exclude_fields, include_fields,pagesize):
    next_batch = s_system 
    while next_batch != None:
        next_url = '{0}://{1}{2}'.format(parse.urlsplit(next_batch).scheme, parse.urlsplit(next_batch).netloc, parse.urlsplit(next_batch).path)
        next_params = dict(parse.parse_qsl(parse.urlsplit(next_batch).query))
        next_params['pagesize'] = pagesize
        response = requests.get(next_url,headers=s_headers,params=next_params,verify=verify_cert_path)
        dict_payload = json.loads(response.text)
        if response.status_code > 299:
            print ('Error extracting %s' % response.status_code)
            if dict_payload['errorMessage']: 
                print(dict_payload['errorMessage'])
            return 
    
        next_batch = None
        update_objects  = []
        print ('...found %s field_defs ...' % len(dict_payload))
        for o in dict_payload: 
            if '@metadata' in o.keys():
                if 'next_batch' in o['@metadata'].keys():
                    next_batch = o['@metadata']['next_batch']
                    dict_payload.pop()
                    pass 
                else: 
                    ident = o['ident']
                    t_url = '{0}/{1}'.format(t_system,ident)
                    t_response = requests.get(t_url,headers=t_headers,verify=verify_cert_path)

                    t_obj = json.loads(t_response.text)
                    o['@metadata'] = t_obj[0]['@metadata']
                    del o['@metadata']['links']

                    for f in exclude_fields: #remove fields we don't want to overwrite
                        if f in o.keys():
                            del o[f]
                    n = {}
                    n['@metadata'] = t_obj[0]['@metadata']
                    if len(include_fields) > 0:
                        for f in include_fields:
                            if (f in o.keys()):
                                n[f] = o[f]
                                print (o[f])
                    else:
                        n = o
                    update_objects.append(n)
           
            for e in o:
                if type(o[e]) == str:
                    o[e] = o[e].rstrip() #some of the system fields may have unintended padding on the end.

        str_payload_clean = json.JSONEncoder().encode(update_objects)
        print(str_payload_clean)
        t_response = requests.put(t_system,headers=t_headers,data=str_payload_clean,verify=verify_cert_path)
        if (t_response.status_code > 299):
            print (t_response.text)
        else: 
            print ('success! %s records migrated ' % len(update_objects))
            

def clean_tables(t_system, t_headers,pagesize, entities):
    ordered_entities = dict(reversed(list(entities.items())))
    for c in ordered_entities:
        print ('Cleaning %s ...' % c)
        tgt = ordered_entities[c].format(t_system)
        clean_table(tgt,t_headers, pagesize)

def clean_table(t_system, t_headers, pagesize):
    next_batch = t_system 
    while next_batch != None:
        response = requests.get(t_system,headers=t_headers,params={'pagesize':pagesize},verify=verify_cert_path)
        dict_payload = json.loads(response.text)
        # todo error handle
        next_batch = None
        delete_list = []
        print ('...found %s records...' % len(dict_payload))
        if len(dict_payload) > 0:
            for o in dict_payload:   
                if '@metadata' in o.keys():
                    if 'next_batch' in o['@metadata'].keys():
                        next_batch = o['@metadata']['next_batch']
                    else:
                        o['@metadata']['action'] = 'DELETE'
                        delete_list.append(o)
            delete_data = json.JSONEncoder().encode(delete_list)
            response = requests.put(t_system,headers=t_headers,data=delete_data,verify=verify_cert_path)
            if (response.status_code > 299):
                print (response.text)
            else: 
                print ('success! %s records cleaned ' % len(delete_list))
        

if (__name__ == "__main__"):
    main()
