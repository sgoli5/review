#!/usr/bin/python
'''
Created on Jan 2016
@author: golis
'''

import json
from uuid import getnode as get_mac
import inspect
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
from django.conf import settings
from django.template.loader import render_to_string
import socket
import zipfile
from os.path import basename
import HID_Report_Generator
import datetime

class HID_Converge_Connector():
    def __init__(self):
        self.sys_conv_sync_file = None
        self.conv_dir = 'conv'
        self.pluginContext = None
        self.dict_barcodes = None
        self.sys_results_dir = None
        self.sys_analysis_dir = None
        self.sys_tsp_analysis_name = None
        self.sys_barcode_file = None
        self.sys_plugin_name = None
        self.sys_plugin_version = None
        #self.sys_target_file = None
        self.sysDIRNAME = None
        self.proceed = True
        self.sys_ipaddress = None

    def read_environment(self):
        self.log('<info> entered HID_Converge_Connector::read_environment')
        self.sys_analysis_dir = os.getenv('ANALYSIS_DIR') 
        self.sys_results_dir = os.getenv('RESULTS_DIR') 
        self.sys_tsp_analysis_name = os.getenv('TSP_ANALYSIS_NAME') 
        #self.sys_target_file = os.getenv('PLUGINCONFIG__TARGETFILE__FILE')
        self.sys_plugin_name = os.getenv('RUNINFO__PLUGIN_NAME')
        self.sys_plugin_version = os.getenv('RUNINFO__PLUGIN__VERSION')
        self.sys_barcode_file = os.getenv('TSP_URLPATH_BARCODE_TXT')
        self.sysDIRNAME = os.getenv('DIRNAME')
        self.sys_conv_sync_file = self.sys_results_dir + '/' + 'converge_sync.json'
        self.sys_ipaddress = self.get_hostname()
        self.log('<info> exited HID_Converge_Connector::read_environment')

    def show_environment(self):
        self.log('<info> entered HID_Converge_Connector::show_environment')
        self.log('ANALYSIS_DIR : ' + self.sys_analysis_dir)
        self.log('RESULTS_DIR : ' + self.sys_results_dir)
        self.log('TSP_ANALYSIS_NAME : ' + self.sys_analysis_dir)
        #self.log('PLUGINCONFIG__TARGETFILE__FILE : ' + self.sys_target_file)
        self.log('RUNINFO__PLUGIN_NAME : ' +  self.sys_plugin_name)
        self.log('RUNINFO__PLUGIN__VERSION : ' + self.sys_plugin_version)
        self.log('TSP_URLPATH_BARCODE_TXT : ' + self.sys_barcode_file)
        self.log('DIRNAME : ' + self.sysDIRNAME)
        self.log('Host IP Address : ' + self.sys_ipaddress)
        self.log('<info> exited HID_Converge_Connector::show_environment')

    def get_hostname(self):
        hostname = [l
            for l in ([ip
                for ip in socket.gethostbyname_ex(socket.gethostname())[2]
                if not ip.startswith("127.")
            ][: 1], [
                [(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]
            ]) if l
        ][0][0]
        return hostname
		
    def initialize(self): 
        self.log('<info> entered HID_Converge_Connector::initialize')
        try:
            if not os.path.isdir(self.sys_results_dir + '/' + self.conv_dir):
                os.mkdir(self.sys_results_dir + '/' + self.conv_dir)
        except:
            self.log('<exception> exception occurred while processing HID_Converge_Connector::initialize')
            traceback.print_exc(file=sys.stdout)
        self.log('<info> exited HID_Converge_Connector::initialize')
		
    def log(self, string):
        print(time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime()) + ": " + str(string))
        
    def logWithMask(self, string, mask_string):
        if (mask_string is not None and len(mask_string) > 0):
            string = string.replace(mask_string,"**********")
        print(time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime()) + ": " + str(string))
        
    def display_context(self):
        for k,v in self.pluginContext.items():
            self.log(k + '(' + json.dumps(v) + ')')
              
    def set_context(self):
        self.log('<info> entered HID_Converge_Connector::set_context')
        self.pluginContext = self.get_plugin_context()
        self.display_context()       
        self.log('<info> exited HID_Converge_Connector::set_context')

    def fetch_analysis_params(self):
        self.log('<info> entered HID_Converge_Connector::fetch_analysis_params')
        try:
            plugin_config = json.load(open(self.sys_results_dir + '/startplugin.json'))
            analysis_params = plugin_config['pluginconfig']['analysisParams']
            with open(self.sys_results_dir + '/' +  self.conv_dir + '/analysisparams.json', 'w') as f:
                json.dump(analysis_params, f, indent=4, sort_keys=True, default=str )
        except:
            self.log('<exception> exception occurred  while processing HID_Converge_Connector::fetch_analysis_params')
            traceback.print_exc(file=sys.stdout)
        self.log('<info> exited HID_Converge_Connector::fetch_analysis_params')
		
    def api_register_with_converge(self):
        try:
            self.log('<info> entered HID_Converge_Connector::api_register_with_converge')
            self.log('>>>>>converge registration started')
            str_json = json.dumps(self.pluginContext)
            cmd = "java -classpath " + self.sysDIRNAME + "/jars/HIDGenotyper.jar:" + self.sysDIRNAME + "/jars/*  com.lifetech.converge.uber.Main 'registerWithConverge' '" + str_json + "'"
            self.logWithMask('<cmd> ' + cmd, self.pluginContext['password'])
            subprocess.call(shlex.split(str(cmd)))
            self.log('<info> exited HID_Converge_Connector::api_register_with_converge')
        except:
            self.log('<exception> exception occurred while processing HID_Converge_Connector::api_register_with_converge')
            traceback.print_exc(file=sys.stdout)


    def fetch_barcodes_dep(self):
        self.log('<info> entered HID_Converge_Connector::fetch_barcodes_dep')
        BARCODE_FILE = os.getenv('ANALYSIS_DIR') + '/barcodeList.txt'
        bcname = None
        for line in open(BARCODE_FILE, 'r').readlines():
            if not line.startswith('barcode'):
                continue
            fields = line.split(',')
            bcname = fields[1]
        self.log('<info> exited HID_Converge_Connector::fetch_barcodes_dep')
        return bcname
   
    def fetch_barcodes(self):
        self.log('<info> entered HID_Converge_Connector::fetch_barcodes')
        try:
            BARCODE_FILE = os.getenv('RESULTS_DIR') + '/barcodes.json'
            bcname = None
            barcode_file = json.load(open(BARCODE_FILE, 'r'))
            self.dict_barcodes = {}
            for key,val in barcode_file.items():

                # Starting TSS 5.1, 'description' became 'barcode_description'. Watch for both
                self.dict_barcodes[key] = barcode_file[key]['sample'] + ',' + barcode_file[key].get('barcode_description', barcode_file[key].get('description', ''))

                self.log(' ' + key)
            self.log('<info> exited HID_Converge_Connector::fetch_barcodes')
            return json.dumps(self.dict_barcodes)
        except:
            self.log('<exception> exception occurred while processing HID_Converge_Connector::fetch_barcodes')
            traceback.print_exc(file=sys.stdout)

    def api_create_batch(self):
        self.log('<info> entered HID_Converge_Connector::api_create_batch')
        try:
            str_json = json.dumps(self.pluginContext)
            bclist = self.fetch_barcodes()
            self.log(' ' + bclist)
            cmd = "java -classpath " + self.sysDIRNAME + "/jars/HIDGenotyper.jar:" + self.sysDIRNAME + "/jars/*  com.lifetech.converge.uber.Main 'createBatch' '" + str_json + "' '" + bclist + "'"
            self.logWithMask('<cmd> ' + cmd, self.pluginContext['password'])
            subprocess.call(shlex.split(str(cmd)))
        except:
            self.log('<exception> exception occurred while processing HID_Converge_Connector::api_create_batch')
            traceback.print_exc(file=sys.stdout)
        finally:
            self.log('<info> exited HID_Converge_Connector::api_create_batch')

    def api_start_batch(self):
        self.log('<info> entered HID_Converge_Connector::api_start_batch')
        try:
            context = json.dumps(self.pluginContext)
            cmd = "java -classpath " + self.sysDIRNAME + "/jars/HIDGenotyper.jar:" + self.sysDIRNAME + "/jars/*  com.lifetech.converge.uber.Main 'batchStarted' '" + context + "'"
            self.logWithMask('<cmd> ' + cmd, self.pluginContext['password'])
            subprocess.call(shlex.split(str(cmd)))
            
        except:
            self.log('<exception> exception occurred while processing HID_Converge_Connector::api_start_batch')
            traceback.print_exc(file=sys.stdout)
        finally:
            self.log('<info> exited HID_Converge_Connector::api_start_batch')

    def api_complete_batch(self):
        self.log('<info> entered HID_Converge_Connector::api_complete_batch')
        try:
            self.pluginContext['completeProcessingDateForBatch'] = str(datetime.datetime.now())
            context = json.dumps(self.pluginContext)
            cmd = "java -classpath " + self.sysDIRNAME + "/jars/HIDGenotyper.jar:" + self.sysDIRNAME + "/jars/*  com.lifetech.converge.uber.Main 'batchCompleted' '" + context + "'"
            self.logWithMask('<cmd> ' + cmd, self.pluginContext['password'])
            subprocess.call(shlex.split(str(cmd)))
        except:
            self.log('<exception> exception occurred while processing HID_Converge_Connector::api_complete_batch')
            traceback.print_exc(file=sys.stdout)
        finally:
            self.log('<info> exited HID_Converge_Connector::api_complete_batch')
            
    def get_analysis_settings_for_barcode(self, barcode):
        self.log('<info> entered HID_Converge_Connector::get_analysis_settings_for_barcode')
        try:
            dict_analysis_settings = {}
            dict_analysis_settings["ANALYSIS_SETTINGS_FILE_PATH"] = self.sys_results_dir + '/' +  self.conv_dir + '/analysisparams.json'
            dict_analysis_settings["Default Analysis Settings"] = 'Default Analysis Settings'
            dict_analysis_settings["BAM_FILE_PATH"] = self.sys_analysis_dir + '/' + barcode + '_rawlib.bam'
            dict_analysis_settings["barcode"] = barcode
            self.log(' analysis settings for - ' + json.dumps(dict_analysis_settings))
            self.log('<info> exited HID_Converge_Connector::get_analysis_settings_for_barcode')
            return dict_analysis_settings
        except:
            self.log('<exception> exception occurred while processing HID_Converge_Connector::get_analysis_settings_for_barcode')
            traceback.print_exc(file=sys.stdout)
        
    def api_sample_processing_started(self):
        self.log('<info> entered HID_Converge_Connector::api_sample_processing_started')
        try:
            if (self.proceed):
                str_json = json.dumps(self.pluginContext)
                self.log('<info> pluginContext - ' + str_json)
                for k in self.dict_barcodes:
                    bc_analysis_settings = json.dumps(self.get_analysis_settings_for_barcode(k))
                    cmd = "java -classpath " + self.sysDIRNAME + "/jars/HIDGenotyper.jar:" + self.sysDIRNAME + "/jars/*  com.lifetech.converge.uber.Main 'sampleProcessingStarted' '" + str_json + "' '" + bc_analysis_settings + "'"
                    self.logWithMask('<cmd> ' + cmd, self.pluginContext['password'])
                    subprocess.call(shlex.split(str(cmd)))
            else:
                self.log('<info> skipping sample_processing_started with converge')        
        except:
            self.log('<exception> exception occurred while processing HID_Converge_Connector::api_sample_processing_started')
            traceback.print_exc(file=sys.stdout)
        finally:
            self.log('<info> exited HID_Converge_Connector::api_sample_processing_started')
            

    def get_ngs_output_for_sample(self, barcode):
        self.log('<info> entered HID_Converge_Connector::get_ngs_output_for_sample ' +  barcode)
        dict_ngs_result = {}
        dict_ngs_result["sample-cgq"] = 0
        dict_ngs_result["barcode"] = barcode

        no_result_file = self.sys_results_dir + '/startplugin.json'
        str_result_file = self.sys_results_dir + '/str/' + barcode + '/converge_results.json'
        if os.path.isfile(str_result_file) and os.access(str_result_file, os.R_OK):
            self.log('sending - ' + str_result_file)
            results = json.load(open(str_result_file, 'r'))
            dict_ngs_result["str-profile-cgq"] = results['cgq']
            dict_ngs_result["sample-cgq"] |=  results['cgq']
            dict_ngs_result["str-profile-tss-path"] = str_result_file
        else:
            self.log('<error> no result file found for STR analysis for the sample - ' + barcode)
            #dict_ngs_result["str-profile-tss-path"] = no_result_file

        mh_result_file = self.sys_results_dir + '/mh/' + barcode + '/converge_results.json'
        if os.path.isfile(mh_result_file) and os.access(mh_result_file, os.R_OK):
            self.log('sending - ' + mh_result_file)
            #dict_ngs_result["mhp-profile-cgq"] = '1'
            dict_ngs_result["mhp-profile-tss-path"] = mh_result_file
        else:
            self.log('<error> no result file found for MH analysis for the sample - ' + barcode)
            #dict_ngs_result["mhp-profile-tss-path"] = no_result_file

        snp_result_file = self.sys_results_dir + '/snp/' + barcode + '/converge_results.json'
        if os.path.isfile(snp_result_file) and os.access(snp_result_file, os.R_OK):
            self.log('sending - ' + snp_result_file)
            results = json.load(open(snp_result_file, 'r'))
            dict_ngs_result["snp-profile-cgq"] = results['cgq']
            dict_ngs_result["sample-cgq"] |=  results['cgq']
            dict_ngs_result["snp-profile-tss-path"] =  snp_result_file
        else:
            self.log('<error> no result file found for SNP analysis for the sample - ' + barcode)
            #dict_ngs_result["snp-profile-tss-path"] = no_result_file

        self.log('settings for sample_processing_completed - ' + json.dumps(dict_ngs_result))
        self.log('<info> exited HID_Converge_Connector::get_ngs_output_for_sample ')
        return dict_ngs_result
        
    def api_sample_processing_completed(self):
        self.log('<info> entered HID_Converge_Connector::api_sample_processing_completed ')
        try:
            if (self.proceed):
                str_json = json.dumps(self.pluginContext)
                for k in self.dict_barcodes:
                    bc_ngs_result = json.dumps(self.get_ngs_output_for_sample(k))
                    cmd = "java -classpath " + self.sysDIRNAME + "/jars/HIDGenotyper.jar:" + self.sysDIRNAME + "/jars/*  com.lifetech.converge.uber.Main 'sampleProcessingCompleted' '" + str_json + "' '" + bc_ngs_result + "'"
                    self.logWithMask('<cmd> ' + cmd, self.pluginContext['password'])
                    subprocess.call(shlex.split(str(cmd)))
            else:
                self.log('<info> skipping sample_processing_completed')
        except:
            self.log('<exception> exception occurred while processing HID_Converge_Connector::api_sample_processing_completed')
            traceback.print_exc(file=sys.stdout)
        finally:
            self.log('<info> exited HID_Converge_Connector::api_sample_processing_completed ')
            
    def decrypt(self, data_for_aes_encryption):
        self.log('<info> entered HID_Converge_Connector::decrypt')
        try:
            cmd = "java -classpath " + self.sysDIRNAME + "/jars/HIDGenotyper.jar:" + self.sysDIRNAME + "/jars/* com.lifetech.converge.uber.Main" + " decrypt " + data_for_aes_encryption
            self.log(' ' + cmd)
            args = shlex.split(str(cmd))
            process = subprocess.Popen(args,stdout = subprocess.PIPE, stderr= subprocess.PIPE)
            output = process.communicate()[0]
            for line in output.split('\n'):
                if 'deencrypted string' in line :
                    words = line.split()
                    decrypted_data = words[-1]
            return decrypted_data
        except:
            self.log('<exception> exception occurred while processing HID_Converge_Connector::decrypt')
        finally:
            self.log('<info> exiting HID_Converge_Connector::decrypt')

    def get_plugin_context(self):
        self.log('<info> entered HID_Converge_Connector::get_plugin_context ')
        try:
            context = {}
            results_dir = os.getenv('RESULTS_DIR')
            start_plugin_file = results_dir + '/startplugin.json'
            start_plugin_json = json.load(open(start_plugin_file, 'r'))
            if 'pluginconfig' in start_plugin_json['runinfo']['plugin'] and 'converge_url' in start_plugin_json['runinfo']['plugin']['pluginconfig']:
                context['convergeUrl'] = str(start_plugin_json['runinfo']['plugin']['pluginconfig']['converge_url'])
            else:
                context['convergeUrl'] = ''
            #context['convergeUrl'] = 'http://ec2-54-145-140-27.compute-1.amazonaws.com:8080/'
            #context['convergeUrl'] = 'http://ec2-54-144-251-35.compute-1.amazonaws.com:8080/'
            if 'pluginconfig' in start_plugin_json['runinfo']['plugin'] and 'username' in start_plugin_json['runinfo']['plugin']['pluginconfig']:
                context['username'] = str(start_plugin_json['runinfo']['plugin']['pluginconfig']['username'])
            else:
                context['username'] = ''
            if 'pluginconfig' in start_plugin_json['runinfo']['plugin'] and 'password' in start_plugin_json['runinfo']['plugin']['pluginconfig']:
                encrypted_password =  str(start_plugin_json['runinfo']['plugin']['pluginconfig']['password'])
                context['password'] = self.decrypt(encrypted_password)
            else:
                context['password'] = ''
            context['macAddress'] = str(get_mac())
            if (os.getenv('http_proxy') is not None):
                context['proxy_url'] = os.getenv('http_proxy').split(':')[0]
                context['proxy_port'] = os.getenv('http_proxy').split(':')[1]        
            context['planName'] = str(start_plugin_json['expmeta']['run_name'])
            context['pluginRunName'] = str(start_plugin_json['runinfo']['pluginresult'])
            context['reportName'] = str(start_plugin_json['expmeta']['results_name'])
            context['convergeSyncFile'] = self.sys_conv_sync_file
            #context['reportUrl'] = 'http://' + str(self.sys_ipaddress) + '/report/' + str(start_plugin_json['runinfo']['pk'])
            
            hostname = None
            protocol = None
            if 'host' in start_plugin_json['runinfo']['plugin']['pluginconfig'] and 'hostname' in start_plugin_json['runinfo']['plugin']['pluginconfig']['host']:
                hostname = str(start_plugin_json['runinfo']['plugin']['pluginconfig']['host']['hostname'])
            if 'host' in start_plugin_json['runinfo']['plugin']['pluginconfig'] and 'protocol' in start_plugin_json['runinfo']['plugin']['pluginconfig']['host']:
                protocol = str(start_plugin_json['runinfo']['plugin']['pluginconfig']['host']['protocol'])
            
            if (hostname is not None and protocol is not None):
                context['reportUrl'] = protocol + '//' + hostname + '/report/' +  str(start_plugin_json['runinfo']['pk'])
                        
            context['startProcessingDateForBatch'] = str(datetime.datetime.now())
            self.log('<info> exited HID_Converge_Connector::get_plugin_context ')
            return context
        except:
            self.log('<exception> exception occurred while processing HID_Converge_Connector::get_plugin_context')
            traceback.print_exc(file=sys.stdout)
        finally:
            self.log('<info> exiting HID_Converge_Connector::get_plugin_context')

    def api_create_export_for_converge(self, export_path, path_to_mapping_file):
        self.log('<info> entered HID_Converge_Connector::api_create_export_for_converge')
        try:
            cmd = "java -classpath " + self.sysDIRNAME + "/jars/HIDGenotyper.jar:" + self.sysDIRNAME + "/jars/*  com.lifetech.converge.uber.Main 'createExportForConverge' '" + export_path + "' '" + path_to_mapping_file + "'"
            self.log('<cmd> ' + cmd)
            subprocess.call(shlex.split(str(cmd)))
        except:
            self.log('<exception> exception occurred while processing HID_Converge_Connector::api_create_export_for_converge')
            traceback.print_exc(file=sys.stdout)
        finally:
            self.log('<info> exited HID_Converge_Connector::api_create_batch')

    def generate_manual_syncfile_for_conv(self):
        self.log('<info> entered HID_Converge_Connector::generate_manual_syncfile_for_conv ')
        try:
            # create export folder for manual sync
            manual_sync_dir = self.sys_results_dir + '/' + self.conv_dir + '/' + 'export'
            manual_sync_dir_parent = self.sys_results_dir + '/' + self.conv_dir + '/'
            if os.path.isdir(manual_sync_dir):
                shutil.rmtree(manual_sync_dir)

            if not os.path.isdir(manual_sync_dir):
                os.mkdir(manual_sync_dir)
            
            # copy the results file for all the anlaysis
            # identify the analysis involved in the run
            supported_analysis_list = ['str', 'snp', 'mh']
            plugin_config = json.load(open(self.sys_results_dir + '/startplugin.json'))
            analysis_params_list = plugin_config['pluginconfig']['analysisParams']
            involved_analysis_list = []
            for key, val in analysis_params_list.items():
                if key in supported_analysis_list:
                     involved_analysis_list.append(key)
            
            # fetch the barcodes for the current run
            barcode_file = os.getenv('RESULTS_DIR') + '/barcodes.json'
            # BARCODE_FILE = os.getenv('ANALYSIS_DIR') + '/barcodeList.txt'
            fd_barcode_file = json.load(open(barcode_file, 'r'))
            barcodes_list = []
            for key,val in fd_barcode_file.items():
                barcodes_list.append(key)
                
            # generate analysis params file
            analysis_params_file = manual_sync_dir + '/' + 'analysisparams.json'
            analysis_params = plugin_config['pluginconfig']['analysisParams']
            with open(analysis_params_file, 'w') as f:
                json.dump(analysis_params, f, indent=4, sort_keys=True, default=str )

            # copy the converge results files from all the analysis into the export folder
            for analysis in involved_analysis_list:
                for barcode in barcodes_list:
                    source_result_file = self.sys_results_dir + '/' + analysis + '/' + barcode + '/' + 'converge_results.json'
                    dest_file_name = analysis + '_' + barcode + '_' + 'converge_results.json'
                    dest_result_file = manual_sync_dir + '/' + dest_file_name
                    if os.path.isfile(source_result_file) and os.access(source_result_file, os.R_OK):
                        shutil.copy(source_result_file, dest_result_file)
            
            # generate the plugin context
            plugin_context = manual_sync_dir + '/' + 'TSSRunContext.json'
            sync_dict = {}
            sync_dict['pluginCredentials'] = self.pluginContext
            sync_dict['sampleMap'] = self.dict_barcodes
            dictSampleInput = {}
            for barcode in barcodes_list:
                dictSampleInput[barcode] = self.get_analysis_settings_for_barcode(barcode)
            sync_dict['sampleInput'] = dictSampleInput
            dictSampleOutput = {}
            for barcode in barcodes_list:
                dictSampleOutput[barcode] = self.get_ngs_output_for_sample(barcode)
            sync_dict['sampleOutput'] = dictSampleOutput 
            #sync_dict['batchStartTime'] = str(datetime.datetime.now())
            #sync_dict['batchEndTime'] = str(datetime.datetime.now())
            sync_dict['batchStartTime'] = self.pluginContext['startProcessingDateForBatch']
            if key in self.pluginContext:
                sync_dict['batchEndTime'] = self.pluginContext['completeProcessingDateForBatch']
            else:
                sync_dict['batchEndTime'] = str(datetime.datetime.now())

            with open(plugin_context, 'w') as plugin_context:
                json.dump(sync_dict, plugin_context)

            # copy the manifest file to the export folder
            path_to_mapping_file = self.sysDIRNAME + '/resources/'
            mapping_file = self.sysDIRNAME + '/resources/manifest.xml'
            shutil.copy(mapping_file, manual_sync_dir)

            # call the integration api for  generating the converge compatable compressed file
            self.api_create_export_for_converge(manual_sync_dir_parent, path_to_mapping_file)

        except:
            self.log('<exception> exception occurred while processing HID_Converge_Connector::generate_manual_syncfile_for_conv')
            traceback.print_exc(file=sys.stdout)
        finally:
            self.log('<info> exited HID_Converge_Connector::generate_manual_syncfile_for_conv ')

    def generate_manual_syncfile_for_converge(self):
        self.log('<info> entered HID_Converge_Connector::generate_manual_syncfile_for_converge ')
        try:
            zip_name = self.sys_results_dir + '/conv/' + 'converge_tss_sync.zip'
            self.log('<info> zip file - ' + zip_name)
            z = zipfile.ZipFile(zip_name, "w")
            # create folder for manual sync
            manual_sync_dir = self.sys_results_dir + '/' + self.conv_dir + '/' + 'manual_sync'
            if not os.path.isdir(manual_sync_dir):
                os.mkdir(manual_sync_dir)
            
            # create the params file
            params_file = self.sys_results_dir + '/' +  self.conv_dir + '/analysisparams.json'
            if os.path.isfile(params_file) and os.access(params_file, os.R_OK):
                shutil.copy(params_file, manual_sync_dir + '/analysisparams.json')
                z.write(params_file, basename(params_file))
            else:
                plugin_config = json.load(open(self.sys_results_dir + '/startplugin.json'))
                analysis_params = plugin_config['pluginconfig']['analysisParams']
                with open(manual_sync_dir + '/analysisparams.json', 'w') as f:
                    json.dump(analysis_params, f, indent=4, sort_keys=True, default=str )
                z.write(manual_sync_dir + '/analysisparams.json',basename(manual_sync_dir + '/analysisparams.json'))
                    
            # copy the results file for all the anlaysis
            # identify the analysis involved in the run
            supported_analysis_list = ['str', 'snp', 'mh']
            plugin_config = json.load(open(self.sys_results_dir + '/startplugin.json'))
            analysis_params_list = plugin_config['pluginconfig']['analysisParams']
            involved_analysis_list = []
            for key, val in analysis_params_list.items():
                if key in supported_analysis_list:
                     involved_analysis_list.append(key)
            
            # fetch the barcodes in the current run
            barcode_file = os.getenv('RESULTS_DIR') + '/barcodes.json'
            # BARCODE_FILE = os.getenv('ANALYSIS_DIR') + '/barcodeList.txt'
            fd_barcode_file = json.load(open(barcode_file, 'r'))
            barcodes_list = []
            for key,val in fd_barcode_file.items():
                barcodes_list.append(key)
                
            # copy the converge results files from all the analysis
            for analysis in involved_analysis_list:
                for barcode in barcodes_list:
                    source_result_file = self.sys_results_dir + '/' + analysis + '/' + barcode + '/' + 'converge_results.json'
                    dest_file_name = analysis + '_' + barcode + '_' + 'converge_results.json'
                    dest_result_file = self.sys_results_dir + '/' + self.conv_dir + '/' + 'manual_sync' + '/' + dest_file_name
                    if os.path.isfile(source_result_file) and os.access(source_result_file, os.R_OK):
                        shutil.copy(source_result_file, dest_result_file)
                        z.write(dest_result_file,basename(dest_result_file))
            
            # copy the converge sync file
            sync_file = self.sys_results_dir + '/' + 'conv' + self.sys_conv_sync_file
            dest_sync_file = self.sys_results_dir + '/' + 'conv' + '/' + 'manual_sync' + self.sys_conv_sync_file
            
            if os.path.isfile(sync_file) and os.access(sync_file, os.R_OK):
                shutil.copy(sync_file, dest_sync_file)
                z.write(sync_file, basename(dest_sync_file))

            # generate the plugin context
            plugin_context = self.sys_results_dir + '/' + 'conv' + '/' + 'manual_sync' + '/' + 'plugin_context.json'
            with open(plugin_context, 'w') as outfile:
                json.dump(json.dumps(self.pluginContext), outfile)
            z.write(plugin_context, basename(plugin_context))
            
            
            # generate the ngs output map for converge & include this file into the converge summayr zip
            ngs_summary_for_converge = {}
            dest_ngs_summary_for_converge_file = self.sys_results_dir + '/' + 'conv' + '/' + 'manual_sync' + '/' + 'ngs_summary_for_converge.json'
            barcodes_list = []
            barcode_file = json.load(open(barcode_file, 'r'))
            for key,val in barcode_file.items():
                barcodes_list.append(key)
            self.log('barcodes read from the barcodes file - ' + str(barcodes_list))

            for barcode in barcodes_list:
                bc_ngs_results = self.get_ngs_output_for_sample(barcode)
                ngs_summary_for_converge[barcode] = bc_ngs_results

            with open(dest_ngs_summary_for_converge_file, 'wb') as outfile:
                json.dump(ngs_summary_for_converge, outfile)
            z.write(dest_ngs_summary_for_converge_file, basename(dest_ngs_summary_for_converge_file))
        except:
            self.log('<exception> exception occurred while processing HID_Converge_Connector::generate_manual_syncfile_for_converge')
            traceback.print_exc(file=sys.stdout)
        finally:
            self.log('<info> exited HID_Converge_Connector::generate_manual_syncfile_for_converge ')

    def api_syncronize(self):
        self.log('<info> entered HID_Converge_Connector::api_syncronize ')
        
        try:
            if (self.proceed):
                str_json = json.dumps(self.pluginContext)
                cmd = "java -classpath " + self.sysDIRNAME + "/jars/HIDGenotyper.jar:" + self.sysDIRNAME + "/jars/*  com.lifetech.converge.uber.Main 'synchronize' '" + str_json + "'"	
                self.log('<cmd> ' + cmd)
                subprocess.call(shlex.split(str(cmd)))
            else:
                self.log('<info> skipping sample_processing_completed')
        except:
            self.log('<exception> exception occurred while processing HID_Converge_Connector::api_syncronize')
            traceback.print_exc(file=sys.stdout)
        finally:
            self.log('<info> exited HID_Converge_Connector::api_syncronize ')
			
    def launch(self):
        self.log('<info> entered HID_Converge_Connector::launch ')
        try:
            self.read_environment()
            self.show_environment()
            self.initialize()
            self.set_context()
            self.fetch_analysis_params()			
            self.api_register_with_converge()
            self.api_create_batch()
            self.api_start_batch()
        except:
            self.log('<error> communication with converge failed on the last action')
            self.proceed = False
        self.log('<info> exited HID_Converge_Connector::launch ')

    def launch_manual_sync(self):
        self.log('<info> entered HID_Converge_Connector::launch_manual_sync')
        try:
            self.read_environment()
            self.show_environment()
            self.initialize()
            self.set_context()
            self.api_syncronize()            
        except:
            self.log('<error> un-expected error during processing HID_Converge_Connector::launch_manual_sync')
            traceback.print_exc(file=sys.stdout)
        finally:    
            self.log('<info> exited HID_Converge_Connector::launch_manual_sync')            

def manual_push():
    print('<error> entering HID_Converge_Connector::manual_push')
    try:
        convergeConnector = HID_Converge_Connector()
        reportGenerator = HID_Report_Generator()
        print('<info> entered manual_push')
        convergeConnector.launch_manual_sync()
        reportGenerator.generate_response()
        return {'status': 'completed'}
    except:
        print('<error> un-expected error during processing HID_Converge_Connector::launch_manual_sync')
        traceback.print_exc(file=sys.stdout)
    finally:    
        print('<error> exiting HID_Converge_Connector::manual_push')
    
def test_auto_sync():
    convergeConnector = HID_Converge_Connector()
    convergeConnector.read_environment()
    convergeConnector.set_context()
    convergeConnector.fetch_barcodes()
    convergeConnector.generate_manual_syncfile_for_conv()

def test_launch():
    try:
        print('<info> running test_launch')
        if (os.getenv('RESULTS_DIR') is not None):
            converge_sync_file = os.getenv('RESULTS_DIR') + '/converge_sync.json'
            converge_sync_file_saveas = os.getenv('RESULTS_DIR') + '/converge_sync_orig.json'
            converge_sync_file_new = os.getenv('RESULTS_DIR') + '/converge_sync.json'
            converge_sync_file_test = os.getenv('RESULTS_DIR') + '/converge_sync_test.json'

        if os.path.isfile(converge_sync_file) and os.access(converge_sync_file, os.R_OK):
            os.rename(converge_sync_file, converge_sync_file_saveas)
            
        if os.path.isfile(converge_sync_file_test) and os.access(converge_sync_file_test, os.R_OK):
            os.remove(converge_sync_file_test)
                       
        convergeConnector = HID_Converge_Connector()
        convergeConnector.launch()
        convergeConnector.api_sample_processing_started()
        convergeConnector.api_sample_processing_completed()
        convergeConnector.api_complete_batch()
        convergeConnector.generate_manual_syncfile_for_conv()
        
        if os.path.isfile(converge_sync_file_new) and os.access(converge_sync_file_new, os.R_OK):
            os.rename(converge_sync_file_new, converge_sync_file_test)
    except:
        print('<error> un-expected error during processing HID_Converge_Connector::launch_manual_sync')
        traceback.print_exc(file=sys.stdout)
    finally:
        if (os.getenv('RESULTS_DIR') is not None):
            converge_sync_file = os.getenv('RESULTS_DIR') + '/converge_sync.json'
            converge_sync_file_saveas = os.getenv('RESULTS_DIR') + '/converge_sync_orig.json'

        if os.path.isfile(converge_sync_file_saveas) and os.access(converge_sync_file_saveas, os.R_OK):
            os.rename(converge_sync_file_saveas, converge_sync_file)
        
        print('<info> completed test_launch')

""" use the below main method for running the script from command prompt on tss for testing & debugging. """
if __name__ == '__main__':
    #test_auto_sync()
    #test_launch()
    #test_auto_sync()
    test_launch()
