#!/usr/bin/python

#
# Copyright 2012, 2013 Machinery Science, LLC
#

import sys
import linuxcnc
import math
#import rpdb2
import logging
import json
import subprocess
import hal
import time
import pygraphviz
import os

import warnings

# *****************************************************
# HAL File Parsing and graph generation
# *****************************************************
class HALAnalyzer( object ):
    def __init__(self ):
        self.Graph = pygraphviz.AGraph( directed=True, name='HAL Diagram', rankdir='LR', splines='spline', aspect='1', overlap='false', forcelabels='true', start='regular', mode='hier', pack='true' )
                
    def parse_comps( self ):
        p = subprocess.Popen( ['halcmd', '-s', 'show', 'comp'] , stderr=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=(1024*64) )
        raw = p.communicate()[0].split( '\n' )
        components = [ filter( lambda a: a != '', [x.strip() for x in line(' ')] ) for line in raw ]
        self.component_dict = {}
        for c in components:
            if len(c) == 4:
                c.append( c[3] )
                c[3] = ''
            if ( c[2].find( 'halcmd' ) != 0 ):
                #self.Graph.add_node( c[2] )
                self.component_dict[ c[2] ] = c
           
    def parse_pins( self ):
        p = subprocess.Popen( ['halcmd', '-s', 'show', 'pin'] , stderr=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=(1024*64) )
        raw = p.communicate()[0].split( '\n' )
        pins = [ filter( lambda a: a != '', [x.strip() for x in line.split(' ')] ) for line in raw ]
        self.pin_group_dict = {}
        self.sig_dict = {}
        for p in pins:

            if len(p) > 5:
                pstr = p[4].split('.')
                pin_group_name = pstr[0]
                try:
                    if (len(pstr) > 2) and (int(pstr[1] > -1)):
                        pin_group_name = pstr[0] + '.' + pstr[1]
                except Exception, err:
                    pass
 
                if pin_group_name in self.pin_group_dict:
                    self.pin_group_dict[ pin_group_name ].append( p )
                else:
                    self.pin_group_dict[ pin_group_name ] = [ p ]
                    
            if len(p) > 5:

                # if there is a signal listed on this pin, make sure
                # that signal is in our signal dictionary
                if ( p[6] in self.sig_dict ):
                    self.sig_dict[ p[6] ].append( { 'hal_line':p, 'pingroup':pin_group_name } )
                else:
                    self.sig_dict[ p[6] ] = [ { 'hal_line':p, 'pingroup':pin_group_name } ]
                    self.Graph.add_node( p[6], label=p[6] + " (" + p[3] + ")", shape='box', style='dotted', outputMode='nodesfirst' )
                    # print 'Signal added: ', p[6]



        # Add all the pins into their sub-graphs
        for pin_g_name, pin_g_val_array in self.pin_group_dict.iteritems():

            labelstr = ''
            for pin_g_val in pin_g_val_array:
                if labelstr is not '':
                    labelstr = labelstr + '|'
                labelstr = labelstr + '<' + pin_g_val[4] + '>' + pin_g_val[4]
            
            self.Graph.add_node( pin_g_name, label=labelstr, shape='record', xlabel=pin_g_name )
            #print "Node added: ", pin_g_name, ' : ', labelstr
            
        # Add all the edges to and from signals
        for sig_name, pin_g_val_array in self.sig_dict.iteritems():
            for pin_g_val in pin_g_val_array:
                if (pin_g_val['hal_line'][5] == '==>'):
                    self.Graph.add_edge( pin_g_val['pingroup'], sig_name, tailport=pin_g_val['hal_line'][4]+':', color='darkblue' )
                    #print pin_g_val['pingroup'], '(', pin_g_val['hal_line'][4], ') ', '==>', sig_name
                else:
                    self.Graph.add_edge( sig_name, pin_g_val['pingroup'], headport=pin_g_val['hal_line'][4]+':', color='black' )
                    #print sig_name, ' ==> ', pin_g_val['pingroup'], '(', pin_g_val['hal_line'][4], ') '

    def write_svg( self, filename ):
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore",category=DeprecationWarning)
            self.Graph.draw( path=filename, format='svg', prog='neato' )


if __name__ == "__main__":
    
    logging.basicConfig(filename='linuxcnc_HAL_generator.log',format='%(asctime)sZ pid:%(process)s module:%(module)s %(message)s', level=logging.INFO)
    logging.info("Starting generation of HAL diagram...")

    if len(sys.argv) < 2:
        sys.exit('Usage: MakeHALGraph.py output_file_name.svg')

    analyzer = HALAnalyzer()
    analyzer.parse_pins()
    analyzer.write_svg(sys.argv[1])
    
    logging.info("DONE")
