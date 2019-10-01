"""tftp-client.
Usage:
  tftp-client.py 
  <Filename>
  <Mode>
  <Type request>

Options:
  <mode> TFTP transfer mode : "netascii", "octet", or "mail"
  <Type request> TFTP type request : "RRQ" or "WRQ"
"""

import socket
import platform

from os import remove

"""
	opcode  operation
	 1     Read request (RRQ)
	 2     Write request (WRQ)
	 3     Data (DATA)
	 4     Acknowledgment (ACK)
	 5     Error (ERROR)

>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

TFTP Formats

   Type   Op #     Format without header

		  2 bytes    string   1 byte     string   1 byte
		  -----------------------------------------------
   RRQ/  | 01/02 |  Filename  |   0  |    Mode    |   0  |
   WRQ    -----------------------------------------------


		  2 bytes    2 bytes       n bytes
		  ---------------------------------
   DATA  | 03    |   Block #  |    Data    |
		  ---------------------------------


		  2 bytes    2 bytes
		  -------------------
   ACK   | 04    |   Block #  |
		  --------------------


		  2 bytes  2 bytes        string    1 byte
		  ----------------------------------------
   ERROR | 05    |  ErrorCode |   ErrMsg   |   0  |
		  ----------------------------------------

Error Codes

   Value     Meaning

   0         Not defined, see error message (if any).
   1         File not found.
   2         Access violation.
   3         Disk full or allocation exceeded.
   4         Illegal TFTP operation.
   5         Unknown transfer ID.
   6         File already exists.
   7         No such user.

====================
Protocol in action
====================

As shown above the protocol can be seen in action on the last 6 lines or so.

1. Client sends a Read Request specifying a file and mode. [ We can see opcodes for that in RFC ]
2. Server responds with block of data along with block number.
3. Client sends an ACK for the received block
4. Server sends next data with incremented block number and ......

** Normal Termination ** - This excerpt is taken directly from `RFC 1350 <https://tools.ietf.org/html/rfc1350/>`_
  The end of a transfer is marked by a DATA packet that contains
  between 0 and 511 bytes of data (i.e., Datagram length < 512).  This
  packet is acknowledged by an ACK packet like all other DATA packets.
  The host acknowledging the final DATA packet may terminate its side
  of the connection on sending the final ACK.

"""
MAXSIZE = 508
TERMINATING_DATA_LENGTH = 512
MAXS = 512
TFTP_TRANSFER_MODE = b'netascii'

TFTP_OPCODES = {
	'unknown': 0,
	'read': 1,  # RRQ
	'write': 2,  # WRQ
	'data': 3,  # DATA
	'ack': 4,  # ACKNOWLEDGMENT
	'error': 5}  # ERROR

TFTP_MODES = {
	'unknown': 0,
	'netascii': 1,
	'octet': 2,
	'mail': 3} # not used

# Map server error codes to messages [ Taken from RFC-1350 ]
server_error_msg = {
	0: "Not defined, see error message (if any).",
	1: "File not found.",
	2: "Access violation.",
	3: "Disk full or allocation exceeded.",
	4: "Illegal TFTP operation.",
	5: "Unknown transfer ID.",
	6: "File already exists.",
	7: "No such user."
}

ip = 'localHost'

# Create a UDP socket and open the port 69				 # socket.SOCK_DGRAM: type of the connector, DGRAM = UDP , STREAM = TCP
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)	 # socket.AF_INET: the domain of the connector, in this case, an IPv4 connector

def send_rq(filename, mode, typeR):
	"""
	This function constructs the request packet in the format below.
	Demonstrates how we can construct a packet using bytearray.

		Type   Op #     Format without header

			   2 bytes    string   1 byte     string   1 byte
			   -----------------------------------------------
		RRQ/  | 01/02 |  Filename  |   0  |    Mode    |   0  |
		WRQ    -----------------------------------------------

	"""
	request = bytearray()
	
	# First two bytes opcode 
	if (typeR == "RRQ"): # RRQ
		request.append(0)
		request.append(1)

	else:                # WRQ
		request.append(0)
		request.append(2)

	# append the filename you are interested in
	filename = bytearray(filename.encode('utf-8'))
	request += filename

	# append the null terminator
	request.append(0)

	# append the mode of transfer
	form = bytearray(bytes(mode, 'utf-8'))
	request += form

	# append the last byte
	request.append(0)

	server_address = (ip, 69)

	print("Send request")
	sent = sock.sendto(request, server_address)


def send_ack(ack_data, server):
	"""
	This function constructs the ack using the bytearray.

			  2 bytes    2 bytes
			 -------------------
	  ACK   | 04    |   Block #  |
			 --------------------

	"""
	ack = bytearray(ack_data)

	ack[0] = 0
	ack[1] = TFTP_OPCODES['ack']

	sock.sendto(ack, server)


def server_error(data):
	"""
	We are checking if the server is reporting an error
				2 bytes  2 bytes        string    1 byte
			  ----------------------------------------
	   ERROR | 05    |  ErrorCode |   ErrMsg   |   0  |
			  ----------------------------------------

	"""
	opcode = data[:2]
	return int.from_bytes(opcode, byteorder='big') == TFTP_OPCODES['error']


def main():

	typeR = input("insert type request (RRQ or WRQ): ")

	if ( typeR != "RRQ" and typeR != "WRQ" ):
		print("Unknown mode - defaulting to [ RRQ ]")
		typeR = "RRQ"

	mode = input("insert mode (octet or netascii): ")

	if ( mode.lower() not in TFTP_MODES.keys() ):
		print("Unknown mode - defaulting to [ netascii ]")
		mode = "netascii"

	filename = input("insert filename: ")
	
	server_address = (ip, 69)

	if(typeR == "RRQ"):
		# Send request
		send_rq(filename, mode, typeR)

		if(mode == "octet"):
			# Open file locally with the same name as that of the requested file from server
			file = open(filename, "wb")

			print("receiving file", filename)

			while True:
				# Wait for the data from the server
				data, server = sock.recvfrom(600)
				#print(data)

				if (server_error(data)):
					error_code = int.from_bytes(data[2:4], byteorder='big')

					file.close()

					if (error_code == 1):
						remove(filename)

					print(server_error_msg[error_code])
					break

				send_ack(data[0:4], server)

				content = data[4:] 
				file.write(content)

				if (len(data) < TERMINATING_DATA_LENGTH):
					print("Transfer complete")

					file.close()

					break

		elif (mode == "netascii"):
			# Open file locally with the same name as that of the requested file from server
			file = open(filename, "w")
			while True:
				# Wait for the data from the server
				data, server = sock.recvfrom(600)

				if (server_error(data)):
					error_code = int.from_bytes(data[2:4], byteorder='big')

					file.close()

					if (error_code == 1):
						remove(filename)

					print(server_error_msg[error_code])
					break

				send_ack(data[0:4], server)

				content = data[4:].decode()
				
				# Handle the end of line control char
				osType = platform.system()

				if (osType == 'Linux') :
					for item in content :
						if ( item != '\r' ):
							file.write(item)

				elif (osType == 'Windows') :
					file.write(content)

				if len(data) < TERMINATING_DATA_LENGTH:
					print("Transfer complete")

					file.close()

					break

		else: # mail is only for WRQ but for readability it is placed as the same as for netascii

			file = open(filename, "w")

			print("receiving file", filename)

			while True:
				# Wait for the data from the server
				data, server = sock.recvfrom(600)

				if (server_error(data)):

					error_code = int.from_bytes(data[2:4], byteorder='big')

					print(server_error_msg[error_code])
					break

				send_ack(data[0:4], server)
				
				content = data[4:] 
				file.write(content)

				if (len(data) < TERMINATING_DATA_LENGTH):

					print("Transfer complete")

					file.close()

					break

	else: #if is WRQ

		if(mode == "octet"):

			try:
				file = open(filename, "rb")

			except:
				print("ERROR, File not found")
				exit()

			# Send request
			send_rq(filename, mode, typeR)

			print("Sending file")
			data, server_address = sock.recvfrom(MAXS)
			#print(data)

			count = 1 # Block number

			while True: # Send the file in blocks

				block = file.read(MAXS) # read the block

				if not block:

					if (count == 1):

						data = bytearray()

						data.append(0)
						data.append(3)

						b = bytearray(count.to_bytes(2, 'big'))
						data += b

						sent = sock.sendto(data, server_address)

						data, server_address = sock.recvfrom(MAXS)
						
						while( data[0] != 0 and data[1] != 4 and data[2] != b[0] and data[3] != b[1] ): # Wait for ACK
							data, server_address = sock.recvfrom(MAXS)

					print("Transfer complete")

					file.close()
					break

				data = bytearray()

				data.append(0)
				data.append(3)

				b = bytearray(count.to_bytes(2, 'big'))
				data += b

				data += block

				sent = sock.sendto(data, server_address) # Send the data

				data, server_address = sock.recvfrom(MAXS)	

				while( data[0] != 0 and data[1] != 4 and data[2] != b[0] and data[3] != b[1] ): # Wait for ACK
					data, server_address = sock.recvfrom(MAXS)

				if (count + 1 >= 60000):
					count = 0

				else:
					count += 1


		elif(mode == "netascii"):
			try:
				file = open(filename, "r")
			except:
				print("ERROR, File not found")
				exit()

			# Send request
			send_rq(filename, mode, typeR)

			print("Sending file")

			count = 0 # Block number

			while True: # Send the file in blocks

			    ## Note: Change reading to char  by char if want to put /r or not
				block = file.read(MAXS) # read the block

				if not block:

					if (count == 0):
						
						data = bytearray()

						data.append(0)
						data.append(3)

						b = bytearray(count.to_bytes(2, 'big'))
						data += b

						sent = sock.sendto(data, server_address)

						data, server_address = sock.recvfrom(MAXS)
						
						while( data[0] != 0 and data[1] != 4 and data[2] != b[0] and data[3] != b[1] ): # Wait for ACK
							data, server_address = sock.recvfrom(MAXS)

					print("Transfer complete")

					file.close()
					break

				data = bytearray()

				data.append(0)
				data.append(3)

				b = bytearray(count.to_bytes(2, 'big'))
				data += b

				data += block.encode()

				sent = sock.sendto(data, server_address) # Send the data

				data, server_address = sock.recvfrom(MAXS)

				while( data[0] != 0 and data[1] != 4 and data[2] != b[0] and data[3] != b[1] ): # Wait for ACK
					data, server_address = sock.recvfrom(MAXS)

				if (count + 1 >= 60000):
					count = 0

				else:
					count += 1

if __name__ == '__main__':
	main()
