#! /usr/bin/env python

import os
import subprocess
from subprocess import Popen, PIPE
from time import gmtime, strftime
import time
import glob
import shutil, errno
import os
import shutil
import subprocess
import shlex
import requests
import sys, traceback
import json
import crypt
from uuid import getnode as get_mac
import time
import imp

class HID_Extend():

    def log(self, string):
        print(time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime()) + ": " + str(string))

    def logfile(self, string):
        target = open('/tmp/log1', 'w')
        target.write(string)

    def read_environment(self):
        self.log('<info> entered HID_Extend::read_environment')
        self.sys_dirname = os.getenv('DIRNAME')
        self.log('<info> exited HID_Extend::read_environment')

    def show_environment(self):
        self.log('<info> entered HID_Converge_Connector::show_environment')
        self.log('DIRNAME : ' + self.sys_dirname)
        self.log('<info> exited HID_Converge_Connector::show_environment')

    def get_plugin_dir(self):
        return os.path.dirname(os.path.realpath(__file__))

    def xor(self, a,b):
        assert len(b) >= len(a)
        return "".join([chr( ord(a[i]) ^ ord(b[i])) for i in range(len(a))])

    def get_python_encryption(self, string_for_encyption):
        value = self.xor(string_for_encyption, crypt.crypt('secret', 'words'))
        return value

    def get_encrypted_string(self, data_for_aes_encryption):
        self.log('<info> entered HID_Extend::get_encrypted_string')
        try:
            #self.read_environment()
            #self.show_environment()
            encrypted_data = ''
            dirname =  os.path.dirname(os.path.realpath(__file__))
            cmd = "java -classpath " + dirname + "/jars/HIDGenotyper.jar:" + dirname + "/jars/* com.lifetech.converge.uber.Main" + " encrypt " + data_for_aes_encryption
            self.log('<cmd> ' + cmd)
            args = shlex.split(str(cmd))
            process = subprocess.Popen(args,stdout = subprocess.PIPE, stderr= subprocess.PIPE)
            output = process.communicate()[0]
            for line in output.split('\n'):
                if 'encrypted string' in line :
                    words = line.split()
                    encrypted_data = words[-1]
            self.log('<info> encrypted string for ' + data_for_aes_encryption + ' is ' + encrypted_data)
            return encrypted_data
        except:
            self.log('<exception> exception occurred while processing HID_Extend::get_encrypted_string')
            traceback.print_exc(file=sys.stdout)
            return 'exception'
        finally:
            self.log('<info> exited HID_Extend::get_encrypted_string')
  
    def get_decrypted_string(self, data_for_aes_decryption):
        self.log('<info> entered HID_Extend::get_decrypted_string')
        try:
            decrypted_data = ''
            dirname =  os.path.dirname(os.path.realpath(__file__))
            cmd = "java -classpath " + dirname + "/jars/HIDGenotyper.jar:" + dirname + "/jars/* com.lifetech.converge.uber.Main" + " decrypt " + data_for_aes_decryption
            self.log('<cmd> ' + cmd)
            args = shlex.split(str(cmd))
            process = subprocess.Popen(args,stdout = subprocess.PIPE, stderr= subprocess.PIPE)
            output = process.communicate()[0]
            for line in output.split('\n'):
                if 'deencrypted string' in line :
                    words = line.split()
                    decrypted_data = words[-1]
            self.log('<info> decrypted string for ' + data_for_aes_decryption + ' is ' + decrypted_data)
            return decrypted_data
        except:
            self.log('<exception> exception occurred while processing HID_Extend::get_decrypted_string')
            traceback.print_exc(file=sys.stdout)
            return 'exception'
        finally:
            self.log('<info> exited HID_Extend::get_encrypted_string')

    def register_with_converge(self, context):
        self.log('<info> entered HID_Extend::register_with_converge')
        try:
            #self.read_environment()
            #self.show_environment()
            str_json = json.dumps(context)
            self.log(' ' + str_json)
            dirname =  os.path.dirname(os.path.realpath(__file__))
            cmd = "java -classpath " + dirname + "/jars/HIDGenotyper.jar:" + dirname + "/jars/*  com.lifetech.converge.uber.Main 'registerWithConverge' '" + str_json + "'"
            self.log('<cmd> ' + cmd)
            subprocess.call(shlex.split(str(cmd)))
            self.log('<info> exited HID_Extend::register_with_converge')
        except:
            self.log('<exception> exception occurred while processing HID_Extend::register_with_converge')
            traceback.print_exc(file=sys.stdout)

def get_display_message(conv_reg_sync_file):
    try:
        if (os.path.exists(conv_reg_sync_file)):
            conv_reg_sync_json = json.load(open(conv_reg_sync_file, 'r'))
        else:
            print('<error> : converge sync file not found')
            raise Exception('file not found exception')
        
        message = 'Registration Failed'
        reason = ''
        if ('loginException' in conv_reg_sync_json.keys()):
            if ('errorMessage' in conv_reg_sync_json['loginException'].keys()):  
                if ('Connection refused'.lower() in conv_reg_sync_json['loginException']['errorMessage'].lower()):
                    reason = ' - Server Unreachable'
                elif ('Name or service not known'.lower()  in conv_reg_sync_json['loginException']['errorMessage'].lower()):
                    reason = ' - Unknown Server'
                elif ('Invalid credentials'.lower() in conv_reg_sync_json['loginException']['errorMessage'].lower()):
                    reason = ' - Invalid credentials'
                elif ('User account has been suspended'.lower() in conv_reg_sync_json['loginException']['errorMessage'].lower()):
                    reason = ' - Account Suspended'
        message = message + reason
        return message
    except:
        print('<exception> exception occurred while processing extend::get_display_message')
        traceback.print_exc(file=sys.stdout)
        return 'Registration Failed'
    
def perform_registration(bucket):
    extend = HID_Extend()
    try:
        response = {}
        params_dict = {}
        req_params_temp = bucket.replace('{','').replace('}','')
        req_params = req_params_temp.split(",")
        for param in req_params:
            words = param.split(":", 1)
            params_dict[words[0].lstrip()] = words[1].lstrip()
        print('<info> params passed for registration - ' + str(params_dict))
        
        cur_time = time.strftime("%H:%M:%S")
        context = {}

        #dirname =  os.path.dirname(os.path.realpath(__file__))
        dirname =  '/results/plugins/scratch'
        conv_reg_sync_file = dirname + '/conv_reg_sync_' + cur_time + '.json'
        cmd = 'touch ' + conv_reg_sync_file
        subprocess.call( shlex.split(str(cmd)) )        

        context['username'] = params_dict['username']
        context['password'] = params_dict['password']
        context['convergeUrl'] = params_dict['host']
        context['macAddress'] = str(get_mac())
        context['convergeSyncFile'] = conv_reg_sync_file
        if (os.getenv('http_proxy') is not None):
            context['proxy_url'] = os.getenv('http_proxy').split(':')[0]
            context['proxy_port'] = os.getenv('http_proxy').split(':')[1]
        print('<info> context : ' + str(context))

        extend.register_with_converge(context)

        if (os.path.exists(conv_reg_sync_file)):
            conv_reg_sync_json = json.load(open(conv_reg_sync_file, 'r'))
        else:
            print('<error> : converge sync file not found')
            raise Exception('file not found exception')
           
        if ('registrationCompleted' in conv_reg_sync_json.keys()): 
            if (conv_reg_sync_json['registrationCompleted'] is True):
                return {'status': 'success', 'errors':'None'}
            else:
                reason = get_display_message(conv_reg_sync_file)
                return {'status': 'failed', 'errors': reason}

        return {'status': 'failed', 'errors':'Registration Failed - Validate the entries'}
    except:
        print('<exception> exception occurred while processing HID_Extend::register')
        traceback.print_exc(file=sys.stdout)
        return {'status': 'failed', 'errors':'Encountered issues with Registration'}
    finally:
        print('<info> exited HID_Extend::register')

def perform_ecryption(data_for_aes_encryption, is_encrypt):
    extend = HID_Extend()
    try:
        #encrypted_string = extend.get_python_encryption(data_for_aes_encryption)
        encrypted_string = extend.get_encrypted_string(data_for_aes_encryption)
        if (encrypted_string is None) or (not encrypted_string):
            return {'status': 'failed', 'result': data_for_aes_encryption, 'errors': 'encryption failed'}
        return {'status': 'success', 'result': encrypted_string, 'errors':'none'}
    except:
        traceback.print_exc(file=sys.stdout)
        return {'status': 'failed', 'result': data_for_aes_encryption, 'errors': 'exception'}
    finally:
        print('<info> exited HID_Extend::encrypt')

def perform_decryption(data_for_aes_decryption, is_encrypt):
    extend = HID_Extend()
    try:
        #encrypted_string = extend.get_python_encryption(data_for_aes_encryption)
        decrypted_string = extend.get_decrypted_string(data_for_aes_decryption)
        if (decrypted_string is None) or (not decrypted_string):
            return {'status': 'failed', 'result': data_for_aes_decryption, 'errors': 'decryption failed'}
        return {'status': 'success', 'result': decrypted_string, 'errors':'none'}
    except:
        traceback.print_exc(file=sys.stdout)
        return {'status': 'failed', 'result': data_for_aes_decryption, 'errors': 'exception'}
    finally:
        print('<info> exited HID_Extend::perform_decryption')

def perform_manual_push(results_dir):
    dirname =  '/results/plugins/scratch'
    cur_time = time.strftime("%H:%M:%S")
    manual_sync_log_file = dirname + '/manual_sync_' + cur_time + '.log'
    try:
        sys.stdout = open(manual_sync_log_file, "w")
        dirname =  os.path.dirname(os.path.realpath(__file__))
        HID_Common_Util = imp.load_source('HID_Common_Util', dirname + '/HID_Common_Util.py')
        HID_Report_Generator = imp.load_source('HID_Report_Generator', dirname + '/HID_Report_Generator.py')
        HID_Converge_Connector = imp.load_source('HID_Converge_Connector', dirname + '/HID_Converge_Connector.py')
        commonUtil = HID_Common_Util.HID_Common_Util()
        commonUtil.set_environment(results_dir)
        convergeConnector = HID_Converge_Connector.HID_Converge_Connector()
        reportGenerator = HID_Report_Generator.HID_Report_Generator()
        convergeConnector.launch_manual_sync()
        response = reportGenerator.re_launch()
        if (response == 'success'):
            return {'status': 'completed', 'errors':'none'}
        else:
            return {'status': 'failed', 'errors':'Auto Sync with Converge Failed'}
    except:
        print('<error> un-expected error during processing HID_Converge_Connector::launch_manual_sync')
        traceback.print_exc(file=sys.stdout)
        return {'status': 'failed', 'errors':'Auto Sync with Converge Failed'}
    finally:
        print('<info> exiting extend::perform_manual_push')
        sys.stdout = sys.__stdout__

def register(bucket):
    if not 'request_get' in bucket:
        return {'failed': 'Expects POST data'}

    try:
        data_to_register = bucket["request_get"].get("data", False)
        return perform_registration(data_to_register)
        
    except Exception, e:
        return {'status': 'failed', 'errors': 'Failed to encrypt: ' + str(e)}

def encrypt(bucket):
    if not 'request_get' in bucket:
        return {'failed': 'Expects POST data'}

    try:
        data_to_encrypt = bucket["request_get"].get("data", False)
        return perform_ecryption(data_to_encrypt, str(0))
    except Exception, e:
        return {'status':'failed', 'errors':'Failed to encrypt: ' + str(e)}

def decrypt(bucket):
    if not 'request_get' in bucket:
        return {'failed': 'Expects POST data'}

    try:
        data_to_decrypt = bucket["request_get"].get("data", False)
        return perform_decryption(data_to_decrypt, str(0))
    except Exception, e:
        return {'status':'failed', 'errors':'Failed to decrypt: ' + str(e)}
    
def manual_sync(bucket):
    if not 'request_get' in bucket:
        return {'failed': 'Expects POST data'}

    try:
        results_dir = bucket["request_get"].get("data", False)
        return perform_manual_push(results_dir)
    except Exception, e:
        return {'status':'failed', 'errors':'synchronization failed : ' + str(e)}

def test_encryption():
    bucket = {}
    bucket['version'] = '2.0'
    bucket['request_get'] = {'data' : 'Converge@15'}
    bucket['request_method'] = 'PUT'
    bucket['user'] = {'User' : 'ionadmin'}
    bucket['config'] = {}
    bucket['name'] = 'HIDGenotyper-r11011'
    input = json.dumps(bucket, indent=4, sort_keys=True)
    print('input : ' + str(input))
    print(' ' + str(encrypt(bucket)))

def test_decryption():
    bucket = {}
    bucket['version'] = '2.0'
    bucket['request_get'] = {'data' : 'zPTTNcpL80XRZ0fOMxqf9Q=='}
    bucket['request_method'] = 'PUT'
    bucket['user'] = {'User' : 'ionadmin'}
    bucket['config'] = {}
    bucket['name'] = 'HIDGenotyper-r11011'
    input = json.dumps(bucket, indent=4, sort_keys=True)
    print('input : ' + str(input))
    print(' ' + str(decrypt(bucket)))
    
def test_registration():
    bucket = {}
    bucket['version'] = '2.0'
    bucket['request_get'] = {'data' : '{host:http://10.43.40.60:9080/, username:converge@hid.com, password:Converge@15}'}
    bucket['request_method'] = 'PUT'
    bucket['user'] = {'User' : 'ionadmin'}
    bucket['config'] = {}
    bucket['name'] = 'HIDGenotyper-r11011'
    input = json.dumps(bucket, indent=4, sort_keys=True)
    print('<info> input request : ' + str(input))
    print('<info> server response : ' + str(register(bucket)))

def test_manualpush():
    bucket = {}
    bucket['version'] = '2.0'
    bucket['request_get'] = {'data' : 'results_dir:/results/analysis/output/Home/TuffStuff_Example_ForDev_042/plugin_out/HIDGenotyper-r11086_out.939'}
    bucket['request_method'] = 'PUT'
    bucket['user'] = {'User' : 'ionadmin'}
    bucket['config'] = {}
    bucket['name'] = 'HIDGenotyper-r11011'
    input = json.dumps(bucket, indent=4, sort_keys=True)
    print('input : ' + str(input))
    print(' ' + str(manual_sync(bucket)))

if __name__ == '__main__':
    #test_encryption()
    #test_decryption()
    test_registration()
    #test_manualpush()
