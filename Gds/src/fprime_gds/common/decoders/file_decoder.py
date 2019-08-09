'''
@brief Decoder for file data

This decoder takes in serialized files, parses them, and packages the results
in file_data objects.

@date Created June 12, 2019
@author Blake A. Harriman

@bug No known bugs
'''
from __future__ import print_function
import copy
from struct import *
from enum import Enum
from fprime_gds.common.decoders import decoder
from fprime_gds.common.data_types import file_data
from fprime.common.models.serialize import u32_type
from fprime.common.models.serialize import time_type
from fprime.common.models.serialize.type_exceptions import *
import multiprocessing as mp
from multiprocessing import Process
import threading
import time
import traceback
import datetime
import os
import random

#More info about File packets can be found at fprime-sw/Fw/FilePacket/docs/sdd.md
#Enum class for Packet Types
class PacketType(Enum):
    START = 0
    DATA = 1
    END = 2
    CANCEL = 3

#TestConsumer class for testing the file decoder
class TestConsumer:
    def data_callback(self, data):
        pass
        #new_path = '/home/blake/Documents/' + file_data.StartPacketData(data).fileDest
        #print(new_path)
        #print(new_path)
        #new_file = open(new_path, 'w')
        #new_file.write(str(data))
        #print(type(data))


#Main FileDecoder class
class FileDecoder(decoder.Decoder):
    '''Decoder class for file data'''
    def __init__(self, file_dest_data = '', source_path = '', dest_path = '', timeout_duration = 120.0, first_time = True, timer = threading.Timer, state = 'IDLE'):
        '''
        FileDecoder class constructor

        Args:
            file_dest_data: This is the file which will be written to by the program

            source_path: This is the source path of the file that the user inputs to be downlinked
            
            dest_path: This is the name and path of the file that will be written to
            
            timeout_duration: This is used to keep track of how long the program should wait before throwing
            a timeout exception:
            
            first_time: For the first packet that is sent to be decoded there is a special case where
            this boolean is needed for the downlink to work.
            
            timer: This is used to keep track of whether or not a timeout has occured.  The timer is started
            and then canceled if the next packet is sent before the timer is started.  If the timer is started,
            then that means the program took too long to cancel it and a timeout has occured.
            
            state: The state of the machine.  It can either be in IDLE (the default) or DATA (when data is being
            manipulated and written to the file)

        Returns:
            An initialized FileDecoder object.
        '''
        
        self._file_dest_data = file_dest_data
        self._source_path = source_path
        self._dest_path = dest_path
        self.timeout_duration = timeout_duration
        self.first_time = first_time
        self.timer = timer
        self.state = state

        super(FileDecoder, self).__init__()


    #Getter for the destination file
    def get_file(self):
        return self._file_dest_data

    #Setter for the destination file
    def set_file(self, x):
        self._file_dest_data = x


    def data_callback(self, data):
        '''
        Function called to pass data to the decoder class

        Args:
            data: Binary data to decode and pass to registered consumers
        '''
        #The first time through the loop requires a special case for the timeout to not fail
        if (self.first_time):
            self.timer = threading.Timer(self.timeout_duration, self.check_timeout, args=(time.time(),))
            self.timer.start()
            self.first_time = False

        result = self.decode_api(data)

        # Make sure we don't send None data
        if result != None:
            self.send_to_all(result)


    def decode_api(self, data):
        '''
        Decodes the given data and returns the result.

        This function allows for non-registered code to call the same decoding
        code as is used to parse data passed to the data_callback function.

        Args:
            data: Binary data to decode (array of bytes)

        Returns:
            Parsed version of the file data in the form of a File object
            or None if the data is not decodable
        '''

        #If the program gets to the next packet before reaching the timeout duration, then cancel the timer
        self.timer.cancel()

        #Decode file here
        packetType = PacketType(unpack('B', data[:1])[0]).name
        seqID = unpack('>I', data[1:5])[0]

        #Packet Type determines the variables following the seqID
        if (packetType == 'START'):  #Packet Type is START
            size = unpack('>I', data[5:9])[0]
            lengthSP = unpack('B', data[9])[0] #Length of the source path
            sourcePath = data[10:lengthSP + 10]
            lengthDP = unpack('B', data[lengthSP + 10])[0] #Length of the destination path
            destPath = data[lengthSP + 11: lengthSP + lengthDP + 11]

            if (self.state == 'IDLE'):
                #Create the log file where the soucePath and lengthDP will be placed
                self.create_log_file(sourcePath, lengthDP)

                #Create the destination file where the DATA packet data will be stored
                self.create_dest_file(destPath)

                #Start a timer to check for a timeout error
                self.timer = threading.Timer(self.timeout_duration, self.check_timeout, args=(time.time(),))
                self.timer.start()
                self.state = 'DATA'

                return file_data.StartPacketData(packetType, seqID, size, lengthSP, sourcePath, lengthDP, destPath)
            elif (self.state == 'DATA'):
                print("Warning: Found a START packet in the middle of the file.  Closing current file and opening a new one")
                file_dest = self.get_file()
                file_dest.close()

                #Create the log file where the soucePath and lengthDP will be placed
                self.create_log_file(sourcePath, lengthDP)

                #Create the destination file where the DATA packet data will be stored
                self.create_dest_file(destPath)

                #Start a timer to check for a timeout error
                self.timer = threading.Timer(self.timeout_duration, self.check_timeout, args=(time.time(),))
                self.timer.start()

                return file_data.StartPacketData(packetType, seqID, size, lengthSP, sourcePath, lengthDP, destPath)

            return None

        elif (packetType == 'DATA'):   #Packet Type is DATA
            if (self.state == 'DATA'):
                offset = unpack('>I', data[5:9])[0]
                length = unpack('BB', data[9:11])[0]
                dataVar = data[11:]
                file_dest = self.get_file() #retrieve the file destination
                file_dest.seek(offset, 0)
                file_dest.write(dataVar)    #write the data information to the destination file
                file_dest.flush()

                #Start a timer to check for a timeout error
                self.timer = threading.Timer(self.timeout_duration, self.check_timeout, args=(time.time(),))
                self.timer.start()
                
                return file_data.DataPacketData(packetType, seqID, offset, length, dataVar)
            elif (self.state == 'IDLE'):
                return None

            return None
        elif (packetType == 'END'):   #Packet Type is END
            if (self.state == 'DATA'):
                hashValue = unpack('>I', data[5:9])[0]
                file_dest = self.get_file()
                file_dest.close()
                print("Successfully finished downlink")
                self.first_time = True
                self.state = 'IDLE'

                return file_data.EndPacketData(packetType, seqID, hashValue)
            elif (self.state == 'IDLE'):
                return None
            
            return None
        elif (packetType == 'CANCEL'):   #Packet Type is CANCEL
            #CANCEL Packets have no data
            self.first_time = True
            return file_data.CancelPacketData(packetType, seqID)

        #The data was not determined to be any of the packet types so return none
        return None

    def create_log_file(self, sourcePath, lengthDP):
        '''
        Creates the log file which contains information about the source
        path and length

        This function allows for the decode_api method to use its START
        packets to create log files that are available to be viewed by
        the user.  The log contains the source path the user entered
        as well as the length of the destination path.

        Args:
            sourcePath: the source path that the user has entered into
            the program
            lengthDP: the length of the destination path.

        Returns:
            None
        '''

        #Create the file_decoder_logs folder if it does not already exist
        log_path = os.getcwd() + '/file_decoder_logs'
        if not (os.path.exists(log_path)):
            try:  
                os.makedirs(log_path)
            except OSError:  
                pass
            else:  
                pass

        #Get the current date time to create a new log file folder
        #Use the dates and time as the folder name
        time = datetime.datetime.now()
        log_path = log_path + '/' + str(time.year) + '_' + str(time.month) + '_' + str(time.day) + '_' + str(time.hour) + '_' + str(time.minute)
        try:  
            os.makedirs(log_path)
        except OSError:  
            pass
        else:  
            pass

        #Create a new file to write to
        new_log = log_path + '/log_file'
        new_file = open(new_log, 'a')
        new_file.write('Source Path: ' + str(sourcePath) + '\n')
        new_file.write('Destination Size: ' + str(lengthDP))
        new_file.flush()
        new_file.close()


    def create_dest_file(self, destPath):
        '''
        Creates the destination file that contains the contents of
        the data varaible
        
        This function creates the file that the decode_api function
        can write to.  The method also creates the folder and path
        that the file will be put into.  It also creates and opens
        the appendable file to be used

        Args:
            destPath: the destination path the user inputs which is
            used to create the folder path and file

        Returns:
            None
        '''

        #First, create the file_downlink folder if it does not already exist
        log_path = os.getcwd() + '/file_downlink/'
        if not (os.path.exists(log_path)):
            try:
                os.makedirs(log_path)
            except OSError:
                pass
            else:
                pass

        #Get rid of all the leading '/'
        for x in str(destPath[0:]):
            if (str(destPath[0]) == '/'):
                destPath = destPath[1:]

        #Figure out where the last '/' is in the file path (if any)
        location = 0
        x = 0
        new_dest_path = log_path + destPath
        for x in range(len(str(new_dest_path[0:]))):
            if str(new_dest_path[x]) == '/':
                location = x

        #We need to create the directory first before we create/open the file so make a temp string
        #without the file at the end of it
        temp_dest_path = new_dest_path[0:location + 1]

        #Create the directory if it does not already exist and then create/open the file
        if not (os.path.exists(temp_dest_path)):
            try:
                os.makedirs(temp_dest_path)
            except OSError:
                pass
            else:
                pass
        
        #Create/open the new file
        data_file = open(new_dest_path, 'w+')

        #Set the file using the setter for other functions to be able to use the new file
        self.set_file(data_file)
    

    #Small function that is called to check if the decoder has timed out
    def check_timeout(self, start_time):
        print("Timeout Error: The state machine has been reset to idle")
        file_dest = self.get_file()
        file_dest.close()
        self.state = 'IDLE'




if __name__ == "__main__":
    pass