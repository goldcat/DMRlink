#!/usr/bin/env python
#
###############################################################################
#   Copyright (C) 2016  Cortney T. Buffington, N0MJS <n0mjs@me.com>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software Foundation,
#   Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA
###############################################################################

# This is a sample application that "records" voice transmissions to
# a datafile... presumably to be played back later.

from __future__ import print_function
from twisted.internet import reactor
from binascii import b2a_hex as h

import sys
import cPickle as pickle
from dmrlink import IPSC, systems
from dmr_utils.utils import hex_str_3, int_id

__author__      = 'Cortney T. Buffington, N0MJS'
__copyright__   = 'Copyright (c) 2014 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__     = 'Adam Fast, KC0YLK; Dave Kierzkowski KD8EYF'
__license__     = 'GNU GPLv3'
__maintainer__  = 'Cort Buffington, N0MJS'
__email__       = 'n0mjs@me.com'


print('This program will record the first matching voice call and exit.\n')

while True:
    tx_type = raw_input('Group (g) or Private voice (p)? ')
    if tx_type == 'g' or tx_type == 'p':
        break
    print('...input must be either \'g\' or \'p\'')

while True:
    ts = raw_input('Which timeslot (1, 2 or \'both\')? ')
    if ts == '1' or ts == '2' or ts =='both':
        if ts == '1':
            ts = (1,)
        if ts == '2':
            ts = (2,)
        if ts == 'both':
            ts = (1,2)
        break
    print('...input must be \'1\', \'2\' or \'both\'')

id = raw_input('Which Group or Subscriber ID to record? ')
id = int(id)
id = hex_str_3(id)

filename = raw_input('Filename to use for this recording? ')

class recordIPSC(IPSC):
    def __init__(self, _name, _config, _logger):
        IPSC.__init__(self, _name, _config, _logger)
        self.CALL_DATA = []
        
    #************************************************
    #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
    #************************************************
    #
    if tx_type == 'g':
	print('Initializing to record GROUP VOICE transmission')
        def group_voice(self, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
            if id == _dst_sub and _ts in ts:
                if not _end:
                    if not self.CALL_DATA:
                        print('({}) Recording transmission from subscriber: {}' .format(self._system, int_id(_src_sub)))
                    self.CALL_DATA.append(_data)
                if _end:
                    self.CALL_DATA.append(_data)
                    print('({}) Transmission ended, writing to disk: {}' .format(self._system, filename))
                    pickle.dump(self.CALL_DATA, open(filename, 'wb'))
                    reactor.stop()
                    print('Recording created, program terminating')
                
    if tx_type == 'p':
	print('Initializing ro record PRIVATE VOICE transmission')
        def private_voice(self, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
            if id == _dst_sub and _ts in ts:
                if not _end:
                    if not self.CALL_DATA:
                        print('({}) Recording transmission from subscriber: {}' .format(self._system, int_id(_src_sub)))
                    self.CALL_DATA.append(_data)
                if _end:
                    self.CALL_DATA.append(_data)
                    print('({}) Transmission ended, writing to disk: {}' .format(self._system, filename))
                    pickle.dump(self.CALL_DATA, open(filename, 'wb'))
                    reactor.stop()
                    print('Recording created, program terminating')


if __name__ == '__main__':
    import argparse
    import os
    import sys
    import signal
    
    import dmrlink_log
    import dmrlink_config
    
    # Change the current directory to the location of the application
    os.chdir(os.path.dirname(os.path.realpath(sys.argv[0])))

    # CLI argument parser - handles picking up the config file from the command line, and sending a "help" message
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', action='store', dest='CFG_FILE', help='/full/path/to/config.file (usually dmrlink.cfg)')
    cli_args = parser.parse_args()

    if not cli_args.CFG_FILE:
        cli_args.CFG_FILE = os.path.dirname(os.path.abspath(__file__))+'/dmrlink.cfg'
    
    # Call the external routine to build the configuration dictionary
    CONFIG = dmrlink_config.build_config(cli_args.CFG_FILE)
    
    # Call the external routing to start the system logger
    logger = dmrlink_log.config_logging(CONFIG['LOGGER'])

    logger.info('DMRlink \'record.py\' (c) 2014 N0MJS & the K0USY Group - SYSTEM STARTING...')
    
    # Shut ourselves down gracefully with the IPSC peers.
    def sig_handler(_signal, _frame):
        logger.info('*** DMRLINK IS TERMINATING WITH SIGNAL %s ***', str(_signal))
    
        for system in systems:
            this_ipsc = systems[system]
            logger.info('De-Registering from IPSC %s', system)
            de_reg_req_pkt = this_ipsc.hashed_packet(this_ipsc._local['AUTH_KEY'], this_ipsc.DE_REG_REQ_PKT)
            this_ipsc.send_to_ipsc(de_reg_req_pkt)
        reactor.stop()

    # Set signal handers so that we can gracefully exit if need be
    for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGQUIT]:
        signal.signal(sig, sig_handler)
    
    
    # INITIALIZE AN IPSC OBJECT (SELF SUSTAINING) FOR EACH CONFIGUED IPSC
    for system in CONFIG['SYSTEMS']:
        if CONFIG['SYSTEMS'][system]['LOCAL']['ENABLED']:
            systems[system] = recordIPSC(system, CONFIG, logger)
            reactor.listenUDP(CONFIG['SYSTEMS'][system]['LOCAL']['PORT'], systems[system], interface=CONFIG['SYSTEMS'][system]['LOCAL']['IP'])
    
    reactor.run()
