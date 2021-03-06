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

# This is a sample application that "records" and replays transmissions for testing.

from __future__ import print_function
from twisted.internet import reactor
from binascii import b2a_hex as ahex

import sys, time
from dmrlink import IPSC, systems
from dmr_utils.utils import int_id, hex_str_3

__author__      = 'Cortney T. Buffington, N0MJS'
__copyright__   = 'Copyright (c) 2014 Cortney T. Buffington, N0MJS and the K0USY Group'
__credits__     = 'Adam Fast, KC0YLK; Dave Kierzkowski, KD8EYF'
__license__     = 'GNU GPLv3'
__maintainer__  = 'Cort Buffington, N0MJS'
__email__       = 'n0mjs@me.com'


try:
    from playback_config import *
except ImportError:
    sys.exit('Configuration file not found or invalid')

HEX_TGID    = hex_str_3(TGID)
HEX_SUB     = hex_str_3(SUB)
BOGUS_SUB   = '\xFF\xFF\xFF'

class playbackIPSC(IPSC):
    def __init__(self, _name, _config, _logger):
        IPSC.__init__(self, _name, _config, _logger)
        self.CALL_DATA = []
        
        if GROUP_SRC_SUB:
            self._logger.info('Playback: USING SUBSCRIBER ID: %s FOR GROUP REPEAT', GROUP_SRC_SUB)
            self.GROUP_SRC_SUB = hex_str_3(GROUP_SRC_SUB)
        
        if GROUP_REPEAT:
            self._logger.info('Playback: GROUP REPEAT ENABLED')
            
        if PRIVATE_REPEAT:
            self._logger.info('Playback: PRIVATE REPEAT ENABLED')
        
    #************************************************
    #     CALLBACK FUNCTIONS FOR USER PACKET TYPES
    #************************************************
    #
    if GROUP_REPEAT:
        def group_voice(self, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
            if HEX_TGID == _dst_sub and _ts in GROUP_TS:
                if not _end:
                    if not self.CALL_DATA:
                        self._logger.info('(%s) Receiving transmission to be played back from subscriber: %s', self._system, int_id(_src_sub))
                    _tmp_data = _data
                    #_tmp_data = dmr_nat(_data, _src_sub, self._config['LOCAL']['RADIO_ID'])
                    self.CALL_DATA.append(_tmp_data)
                if _end:
                    self.CALL_DATA.append(_data)
                    time.sleep(2)
                    self._logger.info('(%s) Playing back transmission from subscriber: %s', self._system, int_id(_src_sub))
                    for i in self.CALL_DATA:
                        _tmp_data = i
                        _tmp_data = _tmp_data.replace(_peerid, self._config['LOCAL']['RADIO_ID'])
                        if GROUP_SRC_SUB:
                            _tmp_data = _tmp_data.replace(_src_sub, self.GROUP_SRC_SUB)
                        # Send the packet to all peers in the target IPSC
                        self.send_to_ipsc(_tmp_data)
                        time.sleep(0.06)
                    self.CALL_DATA = []
                
    if PRIVATE_REPEAT:
        def private_voice(self, _src_sub, _dst_sub, _ts, _end, _peerid, _data):
            if HEX_SUB == _dst_sub and _ts in PRIVATE_TS:
                if not _end:
                    if not self.CALL_DATA:
                        self._logger.info('(%s) Receiving transmission to be played back from subscriber: %s, to subscriber: %s', self._system, int_id(_src_sub), int_id(_dst_sub))
                    _tmp_data = _data
                    self.CALL_DATA.append(_tmp_data)
                if _end:
                    self.CALL_DATA.append(_data)
                    time.sleep(1)
                    self._logger.info('(%s) Playing back transmission from subscriber: %s, to subscriber %s', self._system, int_id(_src_sub), int_id(_dst_sub))
                    _orig_src = _src_sub
                    _orig_dst = _dst_sub
                    for i in self.CALL_DATA:
                        _tmp_data = i
                        _tmp_data = _tmp_data.replace(_peerid, self._config['LOCAL']['RADIO_ID'])
                        _tmp_data = _tmp_data.replace(_dst_sub, BOGUS_SUB)
                        _tmp_data = _tmp_data.replace(_src_sub, _orig_dst)
                        _tmp_data = _tmp_data.replace(BOGUS_SUB, _orig_src)
                        # Send the packet to all peers in the target IPSC
                        self.send_to_ipsc(_tmp_data)
                        time.sleep(0.06)
                    self.CALL_DATA = []
        

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

    logger.info('DMRlink \'playback.py\' (c) 2013, 2014 N0MJS & the K0USY Group - SYSTEM STARTING...')
    
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
            systems[system] = playbackIPSC(system, CONFIG, logger)
            reactor.listenUDP(CONFIG['SYSTEMS'][system]['LOCAL']['PORT'], systems[system], interface=CONFIG['SYSTEMS'][system]['LOCAL']['IP'])
    
    reactor.run()
