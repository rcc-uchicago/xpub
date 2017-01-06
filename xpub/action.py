import os
import json
import requests
from datetime import datetime
from prompter import Prompt
import re
import sys
import json
from collections import defaultdict as dd
import subprocess
from pick import pick
import Tkinter
import tkFileDialog

# set config dir based on $XROMM_CONFIG env variable if present
# otherwise look for a `config` dir in current working dir
cwd_config = os.path.join(os.getcwd(), 'config')
if not os.path.isfile(cwd_config):
	pkg_dir = os.path.dirname(os.path.abspath(__file__))
	cwd_config = os.path.join(pkg_dir, 'config')

CONFIG_DIR = os.environ.get('XROMM_CONFIG', cwd_config)

cache_path  = os.path.join(CONFIG_DIR, 'cache.json')    # cached info
cache = json.load(open(cache_path))     # load cached study/trial options


# save/update a json config file (at `path`) with config `data`
def save_json(data, path):
    data['updated_at'] = datetime.now().isoformat() + 'Z'
    with open(path, 'w', 0) as f:
        json.dump(data, f, indent=4)
	f.flush()
	os.fsync(f.fileno())
	f.close()

# possible actions to take with collected input  . . .

def view(results): 
    print json.dumps(results, indent=4)
    print '<<< COLLECTED METADATA'

def save(results):                              
    path = os.path.join(os.getcwd(), 'input.json')
    save_json(results, path)
    print "input saved to", path
    if os.name == 'nt':                             #check for Windows
        print "press any key to exit"
        os.system('pause')                          #allows message reading (Windows/cygwin)

def transferfile(results):
    file_path = results['file_abs_path']
    file_name = results['file_name']
    ####Select and activate source endpoint, using endpoint display name index####
    endpt_cmd = "ssh cli.globusonline.org endpoint-search --scope my-endpoints | grep 'Display Name' | cut -d ':' -f2 | cut -d ' ' -f2"
    endpt_out = subprocess.check_output(endpt_cmd, shell=True)
    endpts = endpt_out.split("\n")
    endpts_i = []
    for i, x in enumerate(endpts):                  # Create index of endpoint with display names
	if x not in ['n/a','']:
		endpts_i.append(i)
    endpts_d = [endpts[i] for i in endpts_i]
    title = 'Select source Globus endpoint and press Enter, then select Midway destination directory: '
    indicator = '=>'
    d_src_endpt, index = pick(endpts_d, title, indicator)
    print "Selected source endpoint: "+d_src_endpt+"\nSelected file to transfer: "+file_name+"\n"
    l_endpt_cmd = "ssh cli.globusonline.org endpoint-search --scope my-endpoints | grep 'Legacy Name' | cut -d ':' -f2 | cut -d ' ' -f2"
    l_endpt_out = subprocess.check_output(l_endpt_cmd, shell=True)
    l_endpts = l_endpt_out.split("\n")
    l_endpts_d = [l_endpts[i] for i in endpts_i]
    src_endpt = l_endpts_d[index]
    activate_src_cmd = "ssh cli.globusonline.org endpoint-activate "+src_endpt
    os.system(activate_src_cmd)
    ####Select destination directory####
    root = Tkinter.Tk()
    root.withdraw() #use to hide tkinter window
    root.update()
    if not cache['dst_path']:
	currdir = os.getcwd()
    else:
	currdir = cache['dst_path']
    dest_full_dir = tkFileDialog.askdirectory(parent=root, initialdir=currdir, title='Select a Midway destination directory')
    if not dest_full_dir:
	raise SystemExit
    cache['src_path'] = results['file_abs_path'].rsplit('/', 1)[0]
    cache['dst_path'] = dest_full_dir
    save_json(cache, cache_path)                    # update cache with destination directory
    if sys.platform == 'darwin':
	dest_dir = dest_full_dir.split('/Volumes')[1]
    if os.name == 'nt':                             # for Windows systems only
	import win32com.client
	from itertools import izip_longest
	def grouper(n, iterable, fillvalue=None):
    		"grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    		args = [iter(iterable)] * n
    		return izip_longest(fillvalue=fillvalue, *args)
	def getDriveMappings():
    		"""
    		Return a dictionary of drive letter to UNC paths as mapped on the
    		system.
    		"""
    		network = win32com.client.Dispatch('WScript.Network')
    		# http://msdn.microsoft.com/en-us/library/t9zt39at%28VS.85%29.aspx
    		drives = network.EnumNetworkDrives()
    		# EnumNetworkDrives returns an even-length array of drive/unc pairs.
    		# Use grouper to convert this to a dictionary.
    		result = dict(grouper(2, drives))
    		# Potentially several UNC paths will be connected but not assigned
    		# to any drive letter. Since only the last will be in the
    		# dictionary, remove it.
    		if '' in result: del result['']
    		return result
	def getUNCForDrive(drive):
    		"""
    		Get the UNC path for a mapped drive.
    		Throws a KeyError if no mapping exists.
    		"""
    		return getDriveMappings()[drive.upper()]
	drive = dest_full_dir.split(':')[0]+':'
	UNCname = getUNCForDrive(drive)
	parentdir = UNCname.rsplit('\\')[-1]
        dest_dir = '/'+parentdir+dest_full_dir.split(':')[1]
	file_path = file_path.replace('\\', '/')
	file_path = '/'+file_path.replace(':','',1)
    print "Destination endpoint: ucrcc#midway \nSelected Midway destination directory: "+dest_dir+"\n"
    results['dst_path'] = dest_dir
    ####Transfer file to destination on Midway####
    if os.name == 'posix':
	transfer_cmd = "echo '" +src_endpt+file_path+" ucrcc#midway"+dest_dir+"/"+file_name+"' | ssh cli.globusonline.org transfer -s 3"
    if os.name == 'nt':
	transfer_cmd = "echo | set /P =" +src_endpt+file_path+" ucrcc#midway"+dest_dir+"/"+file_name+" | ssh cli.globusonline.org transfer -s 3"
    transfer_id = subprocess.check_output(transfer_cmd, shell=True)
    print "Globus Transfer "+transfer_id
    ####Send metadata to XROMM server####
    resource = results['resource']
    version = results['version']
    path = 'studies/'

    if resource.startswith('file'):
        study_trial  = results['data']['study_trial']
        if '/' in study_trial:                      # study/trial
            study, trial = study_trial.split('/')
            path += '{}/trials/{}/'.format(study, trial)
        else:
            study, trial = study_trial, ''          # no trial name
            path += '{}/'.format(study)

    elif resource is 'trial':
        path += results['data']['study'] + '/trials/'

    #url = 'http://xromm.rcc.uchicago/api/v{}/{}'.format(version, path)
    #url = 'http://localhost:8081/{}'.format(path)
    print "sending to", url

    # comment out next two lines when backend service in place!
    url = "http://httpbin.org/post"
    print "\n... actually, we're sending to", url, "for testing purposes!"
    resp = requests.post(url, json=json.dumps(results))
    print(resp.text)
    if os.name == 'nt':                             #check for Windows
        print "press any key to exit"
        os.system('pause')                          #allows message reading (Windows/cygwin)


def send(results): 
    resource = results['resource']
    version = results['version']
    path = 'studies/'

    if resource.startswith('file'):
        study_trial  = results['data']['study_trial']
        if '/' in study_trial:                      # study/trial
            study, trial = study_trial.split('/')
            path += '{}/trials/{}/'.format(study, trial)
        else:
            study, trial = study_trial, ''          # no trial name
            path += '{}/'.format(study)

    elif resource is 'trial':
        path += results['data']['study'] + '/trials/'

    #url = 'http://xromm.rcc.uchicago/api/v{}/{}'.format(version, path)
    #url = 'http://localhost:8081/{}'.format(path)
    #print "sending to", url

    # comment out next two lines when backend service in place!
    url = "http://httpbin.org/post"     
    print "\n... actually, we're sending to", url, "for testing purposes!"
    resp = requests.post(url, json=json.dumps(results))
    print(resp.text)
    if os.name == 'nt':                             #check for Windows
        print "press any key to exit"
        os.system('pause')                          #allows message reading (Windows/cygwin)

def quit(results): 
    raise SystemExit


# dict of possible action choices (keys) and action functions (values)
actions = {
    "view": view,
    "save": save,
    "send": send,
    "quit": quit,
    "transfer": transferfile
}

# prompt configuration, to prompt for an action
config = {  
    "key": "action",
    "text": "What to do with the collected metadata?",
    "info": "What do you want to do with these inputs?",
    "type": "list",
    "options": [
        "view (look it over before doing anything else)",
        "save (save it to a file)",
        "send (send it off to the `xromm` server)",
        "quit (just discard it)"
    ],
    "example": "quit (just discard it)",
    "require": True,
    "store": [],
    "regex": ""
}

file_config = {  
    "key": "action",
    "text": "What to do with the collected metadata?",
    "info": "What do you want to do with these inputs?",
    "type": "list",
    "options": [
        "view (look it over before doing anything else)",
        "save (save it to a file)",
        "send (send it off to the `xromm` server)",
        "quit (just discard it)",
        "transfer file (send metadata to xromm server and data file to Midway)"
    ],
    "example": "quit (just discard it)",
    "require": True,
    "store": [],
    "regex": ""
}

# prompt the user for the action to take on the `results` dict
def prompt_for_action(results, path=None):
    if path:
        results['file_name'] = os.path.basename(path)
        results['file_abs_path'] = os.path.abspath(path)
	config_data = file_config
    else:
	config_data = config
    prompt = Prompt(config_data)                 # create prompt based on config
    input = prompt(fixed=True)              # prompt for input
    choice = input.split(' ')[0]            # get action from input
    actions[choice](results)                # do the chosen action
    if choice == 'view':
        prompt_for_action(results)          # prompt again


if __name__ == '__main__':

    # example results
    results = dict(resource="trial", study="pig-chewing-study")

    # prompt user to select action to take on results and then do it
    prompt_for_action(results)
