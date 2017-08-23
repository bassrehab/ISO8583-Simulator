

from ISOErrors import *
import struct


class ISO8583:
	"""Main Class to work with ISO8583 packages.
	Used to create, change, send, receive, parse or work with ISO8593 Package version 1993.
	Example:
		from ISO8583.ISO8583 import ISO8583
		from ISO8583.ISOErrors import *
		
		iso = ISO8583()
		try:
			iso.setMTI('0800')
			iso.setBit(2,2)
			iso.setBit(4,4)
			iso.setBit(12,12)
			iso.setBit(21,21)
			iso.setBit(17,17)
			iso.setBit(49,986)
			iso.setBit(99,99)
		except ValueToLarge, e:
				print ('Value too large :( %s' % e)
		except InvalidMTI, i:
				print ('This MTI is wrong :( %s' % i)
				
		print ('The Message Type Indication is = %s' %iso.getMTI()) 
		
		print ('The Bitmap is = %s' %iso.getBitmap()) 
		iso.showIsoBits();
		print ('This is the ISO8583 complete package %s' % iso.getRawIso())
		print ('This is the ISO8583 complete package to sent over the TCPIP network %s' % iso.getNetworkISO())
	
"""
	#Attributes
	# Bitsto be set 00000000 -> _BIT_POSITION_1 ... _BIT_POSITION_8
	_BIT_POSITION_1 = 128 # 10 00 00 00
	_BIT_POSITION_2 = 64 # 01 00 00 00
	_BIT_POSITION_3 = 32 # 00 10 00 00
	_BIT_POSITION_4 = 16 # 00 01 00 00
	_BIT_POSITION_5 = 8 # 00 00 10 00
	_BIT_POSITION_6 = 4 # 00 00 01 00
	_BIT_POSITION_7 = 2 # 00 00 00 10 
	_BIT_POSITION_8 = 1 # 00 00 00 01
	
	#Array to translate bit to position
	_TMP = [0,_BIT_POSITION_8,_BIT_POSITION_1,_BIT_POSITION_2,_BIT_POSITION_3,_BIT_POSITION_4,_BIT_POSITION_5,_BIT_POSITION_6,_BIT_POSITION_7]
	_BIT_DEFAULT_VALUE = 0
	
	#ISO8583 contants
	_BITS_VALUE_TYPE = {}
	# Every _BITS_VALUE_TYPE has:
	# _BITS_VALUE_TYPE[N] = [ X,Y, Z, W,K]
	# N = bitnumber
	# X = smallStr representation of the bit meanning
	# Y = large str representation
	# Z = type of the bit (B, N, A, AN, ANS, LL, LLL)
	#W = size of the information that N need to has
	# K = type os values a, an, n, ansb, b
	_BITS_VALUE_TYPE[1] = ['BME','Bit Map Extended','B',16,'b']
	_BITS_VALUE_TYPE[2] = ['2','Primary account number (PAN)','LL',19,'n']
	_BITS_VALUE_TYPE[3] = ['3','Precessing code','N',6,'n']
	_BITS_VALUE_TYPE[4] = ['4','Amount transaction','N',12,'n']
	_BITS_VALUE_TYPE[5] = ['5','Amount reconciliation','N',12,'n']
	_BITS_VALUE_TYPE[6] = ['6','Amount cardholder billing','N',12,'n']
	_BITS_VALUE_TYPE[7] = ['7','Date and time transmission','N',10,'n']
	_BITS_VALUE_TYPE[8] = ['8','Amount cardholder billing fee','N',8,'n']
	_BITS_VALUE_TYPE[9] = ['9','Conversion rate reconciliation','N',8,'n']
	_BITS_VALUE_TYPE[10] = ['10','Conversion rate cardholder billing','N',8,'n']
	_BITS_VALUE_TYPE[11] = ['11','Systems trace audit number','N',6,'n']
	_BITS_VALUE_TYPE[12] = ['12','Date and time local transaction','N',6,'n']
	_BITS_VALUE_TYPE[13] = ['13','Date effective','N',4,'n']
	_BITS_VALUE_TYPE[14] = ['14','Date expiration','N',4,'n']
	_BITS_VALUE_TYPE[15] = ['15','Date settlement','N',4,'n']
	_BITS_VALUE_TYPE[16] = ['16','Date conversion','N',4,'n']
	_BITS_VALUE_TYPE[17] = ['17','Date capture','N',4,'n']
	_BITS_VALUE_TYPE[18] = ['18','Message error indicator','LLL',4,'n']
	_BITS_VALUE_TYPE[19] = ['19','Country code acquiring institution','N',3,'n']
	_BITS_VALUE_TYPE[20] = ['20','Country code primary account number (PAN)','N',3,'n']
	_BITS_VALUE_TYPE[21] = ['21','Transaction life cycle identification data','ANS',3,'n']
	_BITS_VALUE_TYPE[22] = ['22','Point of service data code','N',3,'n']
	_BITS_VALUE_TYPE[23] = ['23','Card sequence number','N',3,'n']
	_BITS_VALUE_TYPE[24] = ['24','Function code','N',3,'n']
	_BITS_VALUE_TYPE[25] = ['25','Message reason code','N',2,'n']
	_BITS_VALUE_TYPE[26] = ['26','Merchant category code','N',2,'n']
	_BITS_VALUE_TYPE[27] = ['27','Point of service capability','N',1,'n']
	_BITS_VALUE_TYPE[28] = ['28','Date reconciliation','N',8,'n']
	_BITS_VALUE_TYPE[29] = ['29','Reconciliation indicator','N',8,'n']
	_BITS_VALUE_TYPE[30] = ['30','Amounts original','N',8,'n']
	_BITS_VALUE_TYPE[31] = ['31','Acquirer reference number','N',8,'n']
	_BITS_VALUE_TYPE[32] = ['32','Acquiring institution identification code','LL',11,'n']
	_BITS_VALUE_TYPE[33] = ['33','Forwarding institution identification code','LL',11,'n']
	_BITS_VALUE_TYPE[34] = ['34','Electronic commerce data','LL',28,'n']
	_BITS_VALUE_TYPE[35] = ['35','Track 2 data','LL',37,'n']
	_BITS_VALUE_TYPE[36] = ['36','Track 3 data','LLL',104,'n']
	_BITS_VALUE_TYPE[37] = ['37','Retrieval reference number','N',12,'an']
	_BITS_VALUE_TYPE[38] = ['38','Approval code','N',6,'an']
	_BITS_VALUE_TYPE[39] = ['39','Action code','A',2,'an']
	_BITS_VALUE_TYPE[40] = ['40','Service code','N',3,'an']
	_BITS_VALUE_TYPE[41] = ['41','Card acceptor terminal identification','N',8,'ans']
	_BITS_VALUE_TYPE[42] = ['42','Card acceptor identification code','A',15,'ans']
	_BITS_VALUE_TYPE[43] = ['43','Card acceptor name/location','A',40,'asn']
	_BITS_VALUE_TYPE[44] = ['44','Additional response data','LL',25,'an']
	_BITS_VALUE_TYPE[45] = ['45','Track 1 data','LL',76,'an']
	_BITS_VALUE_TYPE[46] = ['46','Amounts fees','LLL',999,'an']
	_BITS_VALUE_TYPE[47] = ['47','Additional data national','LLL',999,'an']
	_BITS_VALUE_TYPE[48] = ['48','Additional data private','LLL',999,'an']
	_BITS_VALUE_TYPE[49] = ['49', 'Currency code, settlement', 'AN', 3, 'an']
	_BITS_VALUE_TYPE[50] = ['50','Currency code, settlement','AN',3,'an']
	_BITS_VALUE_TYPE[51] = ['51','Currency code, cardholder billing','A',3,'a']
	_BITS_VALUE_TYPE[52] = ['52','Personal identification number (PIN) data','B',16,'b']
	_BITS_VALUE_TYPE[53] = ['53','Security related control information','LL',18,'n']
	_BITS_VALUE_TYPE[54] = ['54','Amounts additional','LLL',120,'an']
	_BITS_VALUE_TYPE[55] = ['55','Integrated circuit card (ICC) system related data','LLL',999,'ans']
	_BITS_VALUE_TYPE[56] = ['56','Original data elements','LLL',999,'ans']
	_BITS_VALUE_TYPE[57] = ['57','Authorisation life cycle code','LLL',999,'ans']
	_BITS_VALUE_TYPE[58] = ['58','Authorising agent institution identification code','LLL',999,'ans']
	_BITS_VALUE_TYPE[59] = ['59','Transport data','LLL',999,'ans']
	_BITS_VALUE_TYPE[60] = ['60','Reserved for national use','LL',7,'ans']
	_BITS_VALUE_TYPE[61] = ['61','Reserved for national use','LLL',999,'ans']
	_BITS_VALUE_TYPE[62] = ['62','Reserved for private use','LLL',999,'ans']
	_BITS_VALUE_TYPE[63] = ['63','Reserved for private use','LLL',999,'ans']
	_BITS_VALUE_TYPE[64] = ['64','Message authentication code (MAC) field','B',16,'b']
	_BITS_VALUE_TYPE[65] = ['65','Bitmap tertiary','B',16,'b']
	_BITS_VALUE_TYPE[66] = ['66','Settlement code','N',1,'n']
	_BITS_VALUE_TYPE[67] = ['67','Extended payment data','N',2,'n']
	_BITS_VALUE_TYPE[68] = ['68','Receiving institution country code','N',3,'n']
	_BITS_VALUE_TYPE[69] = ['69','Settlement institution county code','N',3,'n']
	_BITS_VALUE_TYPE[70] = ['70','Network management Information code','N',3,'n']
	_BITS_VALUE_TYPE[71] = ['71','Message number','N',4,'n']
	_BITS_VALUE_TYPE[72] = ['72','Data record','LLL',999,'ans']
	_BITS_VALUE_TYPE[73] = ['73','Date action','N',6,'n']
	_BITS_VALUE_TYPE[74] = ['74','Credits, number','N',10,'n']
	_BITS_VALUE_TYPE[75] = ['75','Credits, reversal number','N',10,'n']
	_BITS_VALUE_TYPE[76] = ['76','Debits, number','N',10,'n']
	_BITS_VALUE_TYPE[77] = ['77','Debits, reversal number','N',10,'n']
	_BITS_VALUE_TYPE[78] = ['78','Transfer number','N',10,'n']
	_BITS_VALUE_TYPE[79] = ['79','Transfer, reversal number','N',10,'n']
	_BITS_VALUE_TYPE[80] = ['80','Inquiries number','N',10,'n']
	_BITS_VALUE_TYPE[81] = ['81','Authorizations, number','N',10,'n']
	_BITS_VALUE_TYPE[82] = ['82','Credits, processing fee amount','N',12,'n']
	_BITS_VALUE_TYPE[83] = ['83','Credits, transaction fee amount','N',12,'n']
	_BITS_VALUE_TYPE[84] = ['84','Debits, processing fee amount','N',12,'n']
	_BITS_VALUE_TYPE[85] = ['85','Debits, transaction fee amount','N',12,'n']
	_BITS_VALUE_TYPE[86] = ['86','Credits, amount','N',15,'n']
	_BITS_VALUE_TYPE[87] = ['87','Credits, reversal amount','N',15,'n']
	_BITS_VALUE_TYPE[88] = ['88','Debits, amount','N',15,'n']
	_BITS_VALUE_TYPE[89] = ['89','Debits, reversal amount','N',15,'n']
	_BITS_VALUE_TYPE[90] = ['90','Original data elements','N',42,'n']
	_BITS_VALUE_TYPE[91] = ['91','File update code','AN',1,'an']
	_BITS_VALUE_TYPE[92] = ['92','File security code','N',2,'n']
	_BITS_VALUE_TYPE[93] = ['93','Response indicator','N',5,'n']
	_BITS_VALUE_TYPE[94] = ['94','Service indicator','AN',7,'an']
	_BITS_VALUE_TYPE[95] = ['95','Replacement amounts','AN',42,'an']
	_BITS_VALUE_TYPE[96] = ['96','Message security code','AN',8,'an']
	_BITS_VALUE_TYPE[97] = ['97','Amount, net settlement','N',16,'n']
	_BITS_VALUE_TYPE[98] = ['98','Payee','ANS',25,'ans']
	_BITS_VALUE_TYPE[99] = ['99','Settlement institution identification code','LL',11,'n']
	_BITS_VALUE_TYPE[100] = ['100','Receiving institution identification code','LL',11,'n']
	_BITS_VALUE_TYPE[101] = ['101','File name','ANS',17,'ans']
	_BITS_VALUE_TYPE[102] = ['102','Account identification 1','LL',28,'ans']
	_BITS_VALUE_TYPE[103] = ['103','Account identification 2','LL',28,'ans']
	_BITS_VALUE_TYPE[104] = ['104','Transaction description','LLL',100,'ans']
	_BITS_VALUE_TYPE[105] = ['105','Reserved for ISO use','LLL',999,'ans']
	_BITS_VALUE_TYPE[106] = ['106','Reserved for ISO use','LLL',999,'ans']
	_BITS_VALUE_TYPE[107] = ['107','Reserved for ISO use','LLL',999,'ans']
	_BITS_VALUE_TYPE[108] = ['108','Reserved for ISO use','LLL',999,'ans']
	_BITS_VALUE_TYPE[109] = ['109','Reserved for ISO use','LLL',999,'ans']
	_BITS_VALUE_TYPE[110] = ['110','Reserved for ISO use','LLL',999,'ans']
	_BITS_VALUE_TYPE[111] = ['111','Reserved for private use','LLL',999,'ans']
	_BITS_VALUE_TYPE[112] = ['112','Reserved for private use','LLL',999,'ans']
	_BITS_VALUE_TYPE[113] = ['113','Reserved for private use','LL',11,'n']
	_BITS_VALUE_TYPE[114] = ['114','Reserved for national use','LLL',999,'ans']
	_BITS_VALUE_TYPE[115] = ['115','Reserved for national use','LLL',999,'ans']
	_BITS_VALUE_TYPE[116] = ['116','Reserved for national use','LLL',999,'ans']
	_BITS_VALUE_TYPE[117] = ['117','Reserved for national use','LLL',999,'ans']
	_BITS_VALUE_TYPE[118] = ['118','Reserved for national use','LLL',999,'ans']
	_BITS_VALUE_TYPE[119] = ['119','Reserved for national use','LLL',999,'ans']
	_BITS_VALUE_TYPE[120] = ['120','Reserved for private use','LLL',999,'ans']
	_BITS_VALUE_TYPE[121] = ['121','Reserved for private use','LLL',999,'ans']
	_BITS_VALUE_TYPE[122] = ['122','Reserved for national use','LLL',999,'ans']
	_BITS_VALUE_TYPE[123] = ['123','Reserved for private use','LLL',999,'ans']
	_BITS_VALUE_TYPE[124] = ['124','Info Text','LLL',255,'ans']
	_BITS_VALUE_TYPE[125] = ['125','Network management information','LL',50,'ans']
	_BITS_VALUE_TYPE[126] = ['126','Issuer trace id','LL',6,'ans']
	_BITS_VALUE_TYPE[127] = ['127','Reserved for private use','LLL',999,'ans']
	_BITS_VALUE_TYPE[128] = ['128','Message authentication code (MAC) field','B',16,'b']

	
	
	################################################################################################
	#Default constructor of the ISO8583 Object
	def __init__(self,iso="", debug=False):
		"""Default Constructor of ISO8583 Package.
		It inicialize a "brand new" ISO8583 package
		Example: To Enable debug you can use:
			pack = ISO8583(debug=True)
		@param: iso a String that represents the ASCII of the package. The same that you need to pass to setIsoContent() method.
		@param: debug (True or False) default False -> Used to print some debug infos. Only use if want that messages! 
		"""
		#Bitmap internal representation
		self.BITMAP = []
		#Values
		self.BITMAP_VALUES = []
		#Bitmap ASCII representantion
		self.BITMAP_HEX = ''
		# MTI
		self.MESSAGE_TYPE_INDICATION = '';
		#Debug ?
		self.DEBUG = debug
		
		self.__inicializeBitmap()
		self.__inicializeBitmapValues()
		
		if iso != "":
			self.setIsoContent(iso)
	################################################################################################
	
	################################################################################################
	#Return bit type
	def getBitType(self,bit):
		"""Method that return the bit Type
		@param: bit -> Bit that will be searched and whose type will be returned
		@return: str that represents the type of the bit
		"""
		return self._BITS_VALUE_TYPE[bit][2]
	################################################################################################
	
	################################################################################################
	#Return bit limit
	def getBitLimit(self,bit):
		"""Method that return the bit limit (Max size)
		@param: bit -> Bit that will be searched and whose limit will be returned
		@return: int that indicate the limit of the bit 
		"""
		return self._BITS_VALUE_TYPE[bit][3]
	################################################################################################
	
	################################################################################################
	#Return bit value type
	def getBitValueType(self,bit):
		"""Method that return the bit value type 
		@param: bit -> Bit that will be searched and whose value type will be returned
		@return: str that indicate the valuye type of the bit 
		"""
		return self._BITS_VALUE_TYPE[bit][4]
	################################################################################################
	
	################################################################################################
	#Return large bit name
	def getLargeBitName(self,bit):
		"""Method that return the large bit name
		@param: bit -> Bit that will be searched and whose name will be returned
		@return: str that represents the name of the bit
		"""
		return self._BITS_VALUE_TYPE[bit][1]
	################################################################################################
	
	
	################################################################################################
	# Set the MTI
	def setTransationType(self,type):
		"""Method that set Transation Type (MTI)
		@param: type -> MTI to be setted
		@raise: ValueToLarge Exception
		"""
		
		type = "%s" %type
		if len(type) > 4:
			type = type[0:3]
			raise ValueToLarge('[ERR] value up to size! MTI limit size = 4')

		typeT = "";
		if len(type) < 4:
			for cont in range(len(type),4):
				typeT += "0"
		
		self.MESSAGE_TYPE_INDICATION = "%s%s" % (typeT,type)
	
	################################################################################################
	
	################################################################################################
	# setMTI too
	def setMTI(self,type):
		"""Method that set Transation Type (MTI) 
		In fact, is an alias to "setTransationType" method
		@param: type -> MTI to be setted
		"""
		self.setTransationType(type)
	
	################################################################################################
	
	################################################################################################
	#Method that put "zeros" inside bitmap
	def __inicializeBitmap(self):
		"""Method that inicialize/reset a internal bitmap representation 
		It's a internal method, so don't call!
		"""
		
		if self.DEBUG == True:
			print ('[DEBUG] Init bitmap')
			
		if len(self.BITMAP) == 16:
			for cont in range(0,16):
				self.BITMAP[cont] = self._BIT_DEFAULT_VALUE
		else:
			for cont in range(0,16):
				self.BITMAP.append(self._BIT_DEFAULT_VALUE)
	################################################################################################

	################################################################################################
	#init with "0" the array of values
	def __inicializeBitmapValues(self):
		"""Method that inicialize/reset a internal array used to save bits and values
		It's a internal method, so don't call!
		"""
		if self.DEBUG == True:
			print ('[DEBUG] Init bitmap_values')
			
		if len(self.BITMAP_VALUES) == 128:
			for cont in range(0,129):
				self.BITMAP_VALUES[cont] = self._BIT_DEFAULT_VALUE
		else:
			for cont in range(0,129):
				self.BITMAP_VALUES.append(self._BIT_DEFAULT_VALUE)
	################################################################################################		
	
	################################################################################################
	# Set a value to a bit
	def setBit(self, bit, value):
		"""Method used to set a bit with a value.
		It's one of the most important method to use when using this library
		@param: bit -> bit number that want to be setted
		@param: value -> the value of the bit
		@return: True/False default True -> To be used in the future!
		@raise: BitInexistent Exception, ValueToLarge Exception
		"""
		if self.DEBUG == True:
			print ('[INFO] Setting bit inside bitmap bit[%s] = %s') % (bit, value)
			
		if bit < 1 or bit > 128:
			raise BitInexistent("[ERR] Bit number %s dosen't exist!" % bit)
			
		# caculate the position insede bitmap
		pos =1
		
		if self.getBitType(bit) == 'LL':
			self.__setBitTypeLL(bit, value)
			
		if self.getBitType(bit) == 'LLL':
			self.__setBitTypeLLL(bit, value)
								
		if self.getBitType(bit) == 'N' :
			self.__setBitTypeN(bit, value)
			
		if self.getBitType(bit) == 'A':
			self.__setBitTypeA(bit, value)	
		
		if self.getBitType(bit) == 'ANS' or self.getBitType(bit) == 'B':
			self.__setBitTypeANS(bit, value)		
		
		if  self.getBitType(bit) == 'B':
			self.__setBitTypeB(bit, value)	

			
		
		#Continuation bit?
		if bit > 64:
			self.BITMAP[0] = self.BITMAP[0] |  self._TMP[2] # need to set bit 1 of first "bit" in bitmap
			
		if (bit % 8) == 0:
			pos = (bit / 8) - 1
		else:
			pos = (bit /8) 

		#need to check if the value can be there .. AN , N ... etc ... and the size
		
		self.BITMAP[pos] = self.BITMAP[pos] | self._TMP[ (bit%8) +1]
		
				
		return True
	################################################################################################	
	
	################################################################################################	
	#print bitmap
	def showBitmap(self):
		"""Method that print the bitmap in ASCII form
		Hint: Try to use getBitmap method and format your own print :) 
		"""
		
		self.__buildBitmap()
		
		# printing		
		print (self.BITMAP_HEX)
	################################################################################################	
	
	################################################################################################	
	#Build a bitmap
	def __buildBitmap(self):
		"""Method that build the bitmap ASCII
		It's a internal method, so don't call!
		"""
		
		self.BITMAP_HEX = ''
		
		for c in range(0,16):
			if (self.BITMAP[0] & self._BIT_POSITION_1) != self._BIT_POSITION_1:
				# Only has the first bitmap
				if self.DEBUG == True:
					print ('[DEBUG] %d Bitmap = %d(Decimal) = %s (hexa) ' %(c, self.BITMAP[c], hex(self.BITMAP[c])))
					
				tm = hex(self.BITMAP[c])[2:]
				if len(tm) != 2:
					tm = '0' + tm
				self.BITMAP_HEX += tm 
				if c == 7:
					break
			else: # second bitmap
				if self.DEBUG == True:
					print ('[DEBUG] %d Bitmap = %d(Decimal) = %s (hexa) ' %(c, self.BITMAP[c], hex(self.BITMAP[c])))
					
				tm = hex(self.BITMAP[c])[2:]
				if len(tm) != 2:
					tm = '0' + tm
				self.BITMAP_HEX += tm 

	################################################################################################	
	
	################################################################################################
	#Get a bitmap from str
	def __getBitmapFromStr(self, bitmap):
		"""Method that receive a bitmap str and transfor it to ISO8583 object readable.
		@param: bitmap -> bitmap str to be readable
		It's a internal method, so don't call!
		"""
		#Need to check if the size is correct etc...
		cont = 0
		
		if self.BITMAP_HEX != '':
			self.BITMAP_HEX = ''
		
		for x in range(0,32,2):
			if (int(bitmap[0:2],16) & self._BIT_POSITION_1) != self._BIT_POSITION_1: # Only 1 bitmap
				if self.DEBUG == True:
					print ('Token[%d] %s converted to int is = %s' %(x, bitmap[x:x+2], int(bitmap[x:x+2],16)))
					
				self.BITMAP_HEX += bitmap[x:x+2]
				self.BITMAP[cont] = int(bitmap[x:x+2],16)
				if x == 14:
					break
			else: # Second bitmap
				if self.DEBUG == True:
					print ('Token[%d] %s converted to int is = %s' %(x, bitmap[x:x+2], int(bitmap[x:x+2],16)))
					
				self.BITMAP_HEX += bitmap[x:x+2]
				self.BITMAP[cont] = int(bitmap[x:x+2],16) 
			cont += 1	
	################################################################################################	
	
	################################################################################################
	# print bit array that is present in the bitmap 
	def showBitsFromBitmapStr(self, bitmap):
		"""Method that receive a bitmap str, process it, and print a array with bits this bitmap string represents.
		Usualy is used to debug things.
		@param: bitmap -> bitmap str to be analized and translated to "bits"
		"""
		bits = self.__inicializeBitsFromBitmapStr(bitmap)
		print ('Bits inside %s  = %s' % (bitmap,bits))	
	################################################################################################	
	
	################################################################################################
	#inicialize a bitmap using ASCII str
	def __inicializeBitsFromBitmapStr(self, bitmap):
		"""Method that receive a bitmap str, process it, and prepare ISO8583 object to understand and "see" the bits and values inside the ISO ASCII package.
		It's a internal method, so don't call!
		@param: bitmap -> bitmap str to be analized and translated to "bits"
		"""
		bits = []
		for c in range(0,16):
			for d in range(1,9):
				if self.DEBUG == True:
					print ('Value (%d)-> %s & %s = %s' % (d,self.BITMAP[c] , self._TMP[d], (self.BITMAP[c] & self._TMP[d]) ))
				if (self.BITMAP[c] & self._TMP[d]) ==  self._TMP[d]:
					if d == 1: #  e o 8 bit
						if self.DEBUG == True:
							print ('Bit %s is present !!!' % ((c +1)* 8))
						bits.append((c +1)* 8)
						self.BITMAP_VALUES[(c +1)* 8] = 'X'
					else:
						if (c == 0) & (d == 2): # Continuation bit
							if self.DEBUG == True:
								print ('Bit 1 is present !!!') 
								
							bits.append(1)
	
						else:
							if self.DEBUG == True:
								print ('Bit %s is present !!!' % (c * 8 + d - 1))
								
							bits.append(c * 8 + d - 1)
							self.BITMAP_VALUES[c * 8 + d - 1] = 'X'
					
		bits.sort()

		return bits	
	################################################################################################	
	
	################################################################################################
	#return a array of bits, when processing the bitmap
	def __getBitsFromBitmap(self):
		"""Method that process the bitmap and return a array with the bits presents inside it.
		It's a internal method, so don't call!
		"""
		bits = []
		for c in range(0,16):
			for d in range(1,9):
				if self.DEBUG == True:
					print ('Value (%d)-> %s & %s = %s' % (d,self.BITMAP[c] , self._TMP[d], (self.BITMAP[c] & self._TMP[d]) ))
				if (self.BITMAP[c] & self._TMP[d]) ==  self._TMP[d]:
					if d == 1: #  e o 8 bit
						if self.DEBUG == True:
							print ('Bit %s is present !!!' % ((c +1)* 8))
							
						bits.append((c +1)* 8)
					else:
						if (c == 0) & (d == 2): # Continuation bit
							if self.DEBUG == True:
								print ('Bit 1 is present !!!') 
	
							bits.append(1)
	
						else:
							if self.DEBUG == True:
								print ('Bit %s is present !!!' % (c * 8 + d - 1))
								
							bits.append(c * 8 + d - 1)
					
		bits.sort()

		return bits	
	################################################################################################	
	
	################################################################################################
	#Set of type LL
	def __setBitTypeLL(self, bit, value):
		"""Method that set a bit with value in form LL
		It put the size in front of the value
		Example: pack.setBit(99,'123') -> Bit 99 is a LL type, so this bit, in ASCII form need to be 03123. To understand, 03 is the size of the information and 123 is the information/value
		@param: bit -> bit to be setted
		@param: value -> value to be setted
		@raise: ValueToLarge Exception
		It's a internal method, so don't call!
		"""
		
		value = "%s" % value
	
		if len(value) > 99:
			#value = value[0:99]
			raise ValueToLarge('Error: value up to size! Bit[%s] of type %s limit size = %s' % (bit,self.getBitType(bit),self.getBitLimit(bit)) )
		if len(value) > self.getBitLimit(bit):
			raise ValueToLarge('Error: value up to size! Bit[%s] of type %s limit size = %s' % (bit,self.getBitType(bit),self.getBitLimit(bit)) )	
			
		size ="%s"% len(value)	
	
		self.BITMAP_VALUES[bit] = "%s%s" %( size.zfill(2), value)
	
	################################################################################################
	
	################################################################################################
	#Set of type LLL
	def __setBitTypeLLL(self, bit, value):
		"""Method that set a bit with value in form LLL
		It put the size in front of the value
		Example: pack.setBit(104,'12345ABCD67890') -> Bit 104 is a LLL type, so this bit, in ASCII form need to be 01412345ABCD67890. 
			To understand, 014 is the size of the information and 12345ABCD67890 is the information/value
		@param: bit -> bit to be setted
		@param: value -> value to be setted
		@raise: ValueToLarge Exception
		It's a internal method, so don't call!
		"""
	
		value = "%s" % value
	
		if len(value) > 999:
			raise ValueToLarge('Error: value up to size! Bit[%s] of type %s limit size = %s' % (bit,self.getBitType(bit),self.getBitLimit(bit)) )
		if len(value) > self.getBitLimit(bit):
			raise ValueToLarge('Error: value up to size! Bit[%s] of type %s limit size = %s' % (bit,self.getBitType(bit),self.getBitLimit(bit)) )	
			
		size ="%s"% len(value)	
				
		self.BITMAP_VALUES[bit] = "%s%s" %( size.zfill(3), value)
	
	################################################################################################
		
	################################################################################################
	# Set of type N, 
	def __setBitTypeN(self, bit, value):
		"""Method that set a bit with value in form N
		It complete the size of the bit with a default value
		Example: pack.setBit(3,'30000') -> Bit 3 is a N type, so this bit, in ASCII form need to has size = 6 (ISO especification) so the value 30000 size = 5 need to receive more "1" number.
			In this case, will be "0" in the left. In the package, the bit will be sent like '030000'
		@param: bit -> bit to be setted
		@param: value -> value to be setted
		@raise: ValueToLarge Exception
		It's a internal method, so don't call!
		"""
		
		value = "%s" % value
	
		if len(value) > self.getBitLimit(bit):
			value = value[0:self.getBitLimit(bit)]
			raise ValueToLarge('Error: value up to size! Bit[%s] of type %s limit size = %s' % (bit,self.getBitType(bit),self.getBitLimit(bit)) )
				
		self.BITMAP_VALUES[bit] = value.zfill(self.getBitLimit(bit))
		
	################################################################################################
	
	################################################################################################
	# Set of type A
	def __setBitTypeA(self, bit, value):
		"""Method that set a bit with value in form A
		It complete the size of the bit with a default value
		Example: pack.setBit(3,'30000') -> Bit 3 is a A type, so this bit, in ASCII form need to has size = 6 (ISO especification) so the value 30000 size = 5 need to receive more "1" number.
			In this case, will be "0" in the left. In the package, the bit will be sent like '030000'
		@param: bit -> bit to be setted
		@param: value -> value to be setted
		@raise: ValueToLarge Exception
		It's a internal method, so don't call!
		"""
		
		value = "%s" % value
	
		if len(value) > self.getBitLimit(bit):
			value = value[0:self.getBitLimit(bit)]
			raise ValueToLarge('Error: value up to size! Bit[%s] of type %s limit size = %s' % (bit,self.getBitType(bit),self.getBitLimit(bit)) )
				
		self.BITMAP_VALUES[bit] = value.zfill(self.getBitLimit(bit))
		
	################################################################################################
	
	################################################################################################
	# Set of type B
	def __setBitTypeB(self, bit, value):
		"""Method that set a bit with value in form B
		It complete the size of the bit with a default value
		Example: pack.setBit(3,'30000') -> Bit 3 is a B type, so this bit, in ASCII form need to has size = 6 (ISO especification) so the value 30000 size = 5 need to receive more "1" number.
			In this case, will be "0" in the left. In the package, the bit will be sent like '030000'
		@param: bit -> bit to be setted
		@param: value -> value to be setted
		@raise: ValueToLarge Exception
		It's a internal method, so don't call!
		"""
		
		value = "%s" % value
	
		if len(value) > self.getBitLimit(bit):
			value = value[0:self.getBitLimit(bit)]
			raise ValueToLarge('Error: value up to size! Bit[%s] of type %s limit size = %s' % (bit,self.getBitType(bit),self.getBitLimit(bit)) )
				
		self.BITMAP_VALUES[bit] = value.zfill(self.getBitLimit(bit))
		
	################################################################################################
	
	################################################################################################
	# Set of type ANS
	def __setBitTypeANS(self, bit, value):
		"""Method that set a bit with value in form ANS
		It complete the size of the bit with a default value
		Example: pack.setBit(3,'30000') -> Bit 3 is a ANS type, so this bit, in ASCII form need to has size = 6 (ISO especification) so the value 30000 size = 5 need to receive more "1" number.
			In this case, will be "0" in the left. In the package, the bit will be sent like '030000'
		@param: bit -> bit to be setted
		@param: value -> value to be setted
		@raise: ValueToLarge Exception
		It's a internal method, so don't call!
		"""
		
		value = "%s" % value
	
		if len(value) > self.getBitLimit(bit):
			value = value[0:self.getBitLimit(bit)]
			raise ValueToLarge('Error: value up to size! Bit[%s] of type %s limit size = %s' % (bit,self.getBitType(bit),self.getBitLimit(bit)) )
				
		self.BITMAP_VALUES[bit] = value.zfill(self.getBitLimit(bit))
		
	################################################################################################
	
	################################################################################################
	# print os bits insede iso
	def showIsoBits(self):
		"""Method that show in detail a list of bits , values and types inside the object
		Example: output to
			(...)
			iso.setBit(2,2)
			iso.setBit(4,4)
			(...)
			iso.showIsoBits()
			(...)
			Bit[2] of type LL has limit 19 = 012
			Bit[4] of type N has limit 12 = 000000000004
			(...)
		"""
		
		for cont in range(0,129):
			if self.BITMAP_VALUES[cont] != self._BIT_DEFAULT_VALUE:
				print("Bit[%s] of type %s has limit %s = %s"%(cont,self.getBitType(cont),self.getBitLimit(cont), self.BITMAP_VALUES[cont]) )
				
				
	################################################################################################
	
	################################################################################################	
	# print Raw iso
	def showRawIso(self):
		"""Method that print ISO8583 ASCII complete representation
		Example: 
		iso = ISO8583()
		iso.setMTI('0800')
		iso.setBit(2,2)
		iso.setBit(4,4)
		iso.setBit(12,12)
		iso.setBit(17,17)
		iso.setBit(99,99)
		iso.showRawIso()
		output (print) -> 0800d010800000000000000000002000000001200000000000400001200170299
		Hint: Try to use getRawIso method and format your own print :) 
		"""
		
		resp = self.getRawIso()
		print(resp)

	
	################################################################################################	
	
	################################################################################################
	# Return raw iso
	def getRawIso(self):
		"""Method that return ISO8583 ASCII complete representation
		Example: 
		iso = ISO8583()
		iso.setMTI('0800')
		iso.setBit(2,2)
		iso.setBit(4,4)
		iso.setBit(12,12)
		iso.setBit(17,17)
		iso.setBit(99,99)
		str = iso.getRawIso()
		print ('This is the ASCII package %s' % str) 
		output (print) -> This is the ASCII package 0800d010800000000000000000002000000001200000000000400001200170299
		
		@return: str with complete ASCII ISO8583
		@raise: InvalidMTI Exception
		"""
		
		self.__buildBitmap()
			
		if self.MESSAGE_TYPE_INDICATION == '':
			raise InvalidMTI('Check MTI! Do you set it?')

		resp = "";
		
		resp += self.MESSAGE_TYPE_INDICATION
		resp += self.BITMAP_HEX
		
		for cont in range(0,129):
			if self.BITMAP_VALUES[cont] != self._BIT_DEFAULT_VALUE:
				resp = "%s%s"%(resp, self.BITMAP_VALUES[cont]) 
		
		return resp

	
	################################################################################################	

	################################################################################################
	#Redefine a bit
	def redefineBit(self,bit, smallStr, largeStr, bitType, size, valueType ):
		"""Method that redefine a bit structure in global scope! 
		Can be used to personalize ISO8583 structure to another specification (ISO8583 1987 for example!)
		Hint: If you have a lot of "ValueToLarge Exception" maybe the especification that you are using is different of mine. So you will need to use this method :)
		@param: bit -> bit to be redefined
		@param: smallStr -> a small String representantion of the bit, used to build "user friendly prints", example "2" for bit 2
		@param: largeStr -> a large String representantion of the bit, used to build "user friendly prints" and to be used to inform the "main use of the bit", 
			example "Primary account number (PAN)" for bit 2
		@param: bitType -> type the bit, used to build the values, example "LL" for bit 2. Need to be one of (B, N, AN, ANS, LL, LLL)	
		@param: size -> limit size the bit, used to build/complete the values, example "19" for bit 2. 	
		@param: valueType -> value type the bit, used to "validate" the values, example "n" for bit 2. This mean that in bit 2 we need to have only numeric values.
			Need to be one of (a, an, n, ansb, b)
		@raise: BitInexistent Exception, InvalidValueType Exception
		
		"""
		
		if self.DEBUG == True:
			print ('Trying to redefine the bit with (self,%s,%s,%s,%s,%s,%s)' % (bit, smallStr, largeStr, bitType, size, valueType))
		
		#validating bit position
		if bit == 1 or bit == 64 or bit < 0 or bit > 128:
			raise BitInexistent("Error %d cannot be changed because has a invalid number!" % bit)
		
		#need to validate if the type and size is compatible! example slimit = 100 and type = LL
			
		if 	bitType == "B" or bitType == "N" or bitType == "AN" or bitType == "ANS" or bitType == "LL" or bitType == "LLL":
			if 	valueType == "a" or valueType == "n" or valueType == "ansb" or valueType == "ans" or valueType == "b" or valueType == "an" :
				self._BITS_VALUE_TYPE[bit] = [smallStr, largeStr, bitType, size, valueType]
				if self.DEBUG == True:
					print ('Bit %d redefined!' % bit)
				
			else:
				raise InvalidValueType("Error bit %d cannot be changed because %s is not a valid valueType (a, an, n ansb, b)!" % (bit,valueType))
				#return
		else:
			raise InvalidBitType("Error bit %d cannot be changed because %s is not a valid bitType (Hex, N, AN, ANS, LL, LLL)!" % (bit,bitType))
			#return
				
	################################################################################################	
	
	################################################################################################
	#a partir de um trem de string, pega o MTI
	def __setMTIFromStr(self,iso):
		"""Method that get the first 4 characters to be the MTI. 
		It's a internal method, so don't call!
		"""
		
		self.MESSAGE_TYPE_INDICATION = iso[0:4]
		
		if self.DEBUG == True:
			print ('MTI found was %s' % self.MESSAGE_TYPE_INDICATION)
		
		
	################################################################################################
	
	################################################################################################
	#return the MTI
	def getMTI(self):
		"""Method that return the MTI of the package
		@return: str -> with the MTI
		"""
		 
		#Need to validate if the MTI was setted ...etc ...
		return self.MESSAGE_TYPE_INDICATION 
		
		
	################################################################################################
	
	################################################################################################
	#Return the bitmap
	def getBitmap(self):
		"""Method that return the ASCII Bitmap of the package
		@return: str -> with the ASCII Bitmap
		"""
		if self.BITMAP_HEX == '':
			self.__buildBitmap()
	
		return self.BITMAP_HEX
		
		
	################################################################################################
	
	################################################################################################
	#return the Varray of values
	def getValuesArray(self):
		"""Method that return an internal array of the package
		@return: array -> with all bits, presents or not in the bitmap
		"""
		return self.BITMAP_VALUES
		
		
	################################################################################################

	################################################################################################
	#Receive a str and interpret it to bits and values
	def __getBitFromStr(self,strWithoutMtiBitmap):
		"""Method that receive a string (ASCII) without MTI and Bitmaps (first and second), understand it and remove the bits values
		@param: str -> with all bits presents whithout MTI and bitmap
		It's a internal method, so don't call!
		"""
	
		if self.DEBUG == True:
			print ('This is the input string <%s>' % strWithoutMtiBitmap)
			
		offset = 0;
		# jump bit 1 because it was alread defined in the "__inicializeBitsFromBitmapStr"
		for cont in range(2,129):
			if self.BITMAP_VALUES[cont] != self._BIT_DEFAULT_VALUE:
				if self.DEBUG == True:
					print ('String = %s offset = %s bit = %s' % (strWithoutMtiBitmap[offset:],offset,cont))
					
				if self.getBitType(cont) == 'LL':
					valueSize = int(strWithoutMtiBitmap[offset:offset +2])
					if self.DEBUG == True:
						print ('Size of the message in LL = %s' %valueSize)
						
					if valueSize > self.getBitLimit(cont):
						raise ValueToLarge("This bit is larger than the especification!")
					self.BITMAP_VALUES[cont] = strWithoutMtiBitmap[offset:offset+2]  + strWithoutMtiBitmap[offset+2:offset+2+valueSize]
					
					if self.DEBUG == True:
						print ('\tSetting bit %s value %s' % (cont,self.BITMAP_VALUES[cont]))
					
					offset += valueSize + 2
					
				if self.getBitType(cont) == 'LLL':
					valueSize = int(strWithoutMtiBitmap[offset:offset +3])
					if self.DEBUG == True:
						print ('Size of the message in LLL = %s' %valueSize)
						
					if valueSize > self.getBitLimit(cont):
						raise ValueToLarge("This bit is larger than the especification!")
					self.BITMAP_VALUES[cont] = strWithoutMtiBitmap[offset:offset+3]  + strWithoutMtiBitmap[offset+3:offset+3+valueSize]
					
					if self.DEBUG == True:
						print ('\tSetting bit %s value %s' % (cont,self.BITMAP_VALUES[cont]))
					
					offset += valueSize + 3	
						
				# if self.getBitType(cont) == 'LLLL':
					# valueSize = int(strWithoutMtiBitmap[offset:offset +4])
					# if valueSize > self.getBitLimit(cont):
						# raise ValueToLarge("This bit is larger than the especification!")
					# self.BITMAP_VALUES[cont] = '(' + strWithoutMtiBitmap[offset:offset+4] + ')' + strWithoutMtiBitmap[offset+4:offset+4+valueSize]
					# offset += valueSize + 4	
						
				if self.getBitType(cont) == 'N' or self.getBitType(cont) == 'A' or self.getBitType(cont) == 'ANS' or self.getBitType(cont) == 'B' or self.getBitType(cont) == 'AN' :
					self.BITMAP_VALUES[cont] = strWithoutMtiBitmap[offset:self.getBitLimit(cont)+offset]
					
					if self.DEBUG == True:
						print ('\tSetting bit %s value %s' % (cont,self.BITMAP_VALUES[cont]))
					
					offset += self.getBitLimit(cont)

		
	################################################################################################	
	
	################################################################################################
	#Parse a ASCII iso to object
	def setIsoContent(self,iso):
		"""Method that receive a complete ISO8583 string (ASCII) understand it and remove the bits values
		Example:
			iso = '0210B238000102C080040000000000000002100000000000001700010814465469421614465701081100301000000N399915444303500019991544986020   Value not allowed009000095492'
			i2 = ISO8583()
			# in this case, we need to redefine a bit because default bit 42 is LL and in this especification is "N"
			# the rest remain, so we use "get" :)
			i2.redefineBit(42, '42', i2.getLargeBitName(42), 'N', i2.getBitLimit(42), i2.getBitValueType(42) )
			i2.setIsoContent(iso2)
			print ('Bitmap = %s' %i2.getBitmap()) 
			print ('MTI = %s' %i2.getMTI() )

			print ('This ISO has bits:')
			v3 = i2.getBitsAndValues()
			for v in v3:
				print ('Bit %s of type %s with value = %s' % (v['bit'],v['type'],v['value']))
				
		@param: str -> complete ISO8583 string
		@raise: InvalidIso8583 Exception
		"""
		if len(iso) < 20:
			raise InvalidIso8583('This is not a valid iso!!')
		if self.DEBUG == True:
			print ('ASCII to process <%s>' % iso)
			
		self.__setMTIFromStr(iso)
		isoT = iso[4:]
		self.__getBitmapFromStr(isoT)
		self.__inicializeBitsFromBitmapStr(self.BITMAP_HEX)
		if self.DEBUG == True:
			print ('This is the array of bits (before) %s ' % self.BITMAP_VALUES)
			
		self.__getBitFromStr(iso[4+len(self.BITMAP_HEX):])	
		if self.DEBUG == True:
			print ('This is the array of bits (after) %s ' % self.BITMAP_VALUES)
		
		
	################################################################################################
	
	################################################################################################
	#Method that compare 2 isos
	def __cmp__(self,obj2):
		"""Method that compare two objects in "==", "!=" and other things
		Example:
			p1 = ISO8583()
			p1.setMTI('0800')
			p1.setBit(2,2)
			p1.setBit(4,4)
			p1.setBit(12,12)
			p1.setBit(17,17)
			p1.setBit(99,99)

			#get the rawIso and save in the iso variable
			iso = p1.getRawIso()

			p2 = ISO8583()
			p2.setIsoContent(iso)

			print ('Is equivalent?')
			if p1 == p1:
				print ('Yes :)')
			else:
				print ('Noooooooooo :(')
	
		@param: obj2 -> object that will be compared
		@return: <0 if is not equal, 0 if is equal
		"""
		ret = -1 # By default is different
		if (self.getMTI() == obj2.getMTI()) and (self.getBitmap()  == obj2.getBitmap()) and (self.getValuesArray()  == obj2.getValuesArray()): 
			ret = 0 
				
		return ret
	################################################################################################	
	
	################################################################################################
	# Method that return a array with bits and values inside the iso package
	def getBitsAndValues(self):
		"""Method that return an array of bits, values, types etc.
			Each array value is a dictionary with: {'bit':X ,'type': Y, 'value': Z} Where:
				bit: is the bit number
				type: is the bit type
				value: is the bit value inside this object
			so the Generic array returned is:  [ (...),{'bit':X,'type': Y, 'value': Z}, (...)] 
			
		Example:
			p1 = ISO8583()
			p1.setMTI('0800')
			p1.setBit(2,2)
			p1.setBit(4,4)
			p1.setBit(12,12)
			p1.setBit(17,17)
			p1.setBit(99,99)
			
			v1 = p1.getBitsAndValues()
			for v in v1:
				print ('Bit %s of type %s with value = %s' % (v['bit'],v['type'],v['value']))
	
		@return: array of values.
		"""
		ret = []
		for cont in range(2,129):
			if self.BITMAP_VALUES[cont] != self._BIT_DEFAULT_VALUE:
				_TMP = {}
				_TMP['bit'] =  "%d" % cont
				_TMP['type'] = self.getBitType(cont)
				_TMP['value'] = self.BITMAP_VALUES[cont]
				ret.append(_TMP)
		return ret
		
	################################################################################################	
	
	################################################################################################
	# Method that return a array with bits and values inside the iso package
	def getBit(self,bit):
		"""Return the value of the bit
		@param: bit -> the number of the bit that you want the value
		@raise: BitInexistent Exception, BitNotSet Exception
		"""
		
		if bit < 1 or bit > 128:
			raise BitInexistent("Bit number %s dosen't exist!" % bit)	
			
		#Is that bit set?
		isThere = False
		arr = self.__getBitsFromBitmap()
		
		if self.DEBUG == True:
			print ('This is the array of bits inside the bitmap %s' % arr)
		
		for v in arr:
			if v == bit:
				value = self.BITMAP_VALUES[bit]
				isThere = True
				break
		
		if isThere:
			return value
		else:
			raise BitNotSet("Bit number %s was not set!" % bit)	
		
	################################################################################################	
		
	################################################################################################	
	#Method that return ISO8583 to TCPIP network form, with the size in the beginning.
	def getNetworkISO(self, bigEndian=True):
		"""Method that return ISO8583 ASCII package with the size in the beginning
		By default, it return the package with size represented with big-endian.
		Is the same that:
			import struct
			(...)
			iso = ISO8583()
			iso.setBit(3,'300000')
			(...)
			ascii = iso.getRawIso()
			# Example: big-endian
			# To little-endian, replace '!h' with '<h'
			netIso = struct.pack('!h',len(iso)) 
			netIso += ascii
			# Example: big-endian
			# To little-endian, replace 'iso.getNetworkISO()' with 'iso.getNetworkISO(False)'
			print ('This <%s> the same that <%s>' % (iso.getNetworkISO(),netIso))
		
		@param: bigEndian (True|False) -> if you want that the size be represented in this way. 
		@return: size + ASCII ISO8583 package ready to go to the network!
		@raise: InvalidMTI Exception
		"""
		
		netIso = ""
		asciiIso = self.getRawIso()
		
		if bigEndian:
			netIso = struct.pack('!h',len(asciiIso))
			if self.DEBUG == True:
				print ('Pack Big-endian')
		else:
			netIso = struct.pack('<h',len(asciiIso))
			if self.DEBUG == True:
				print ('Pack Little-endian')

		netIso += asciiIso
		
		return netIso

	################################################################################################		
	
	################################################################################################	
	# Method that recieve a ISO8583 ASCII package in the network form and parse it.
	def setNetworkISO(self,iso, bigEndian=True):
		"""Method that receive sie + ASCII ISO8583 package and transfor it in the ISO8583 object.
			By default, it recieve the package with size represented with big-endian.
			Is the same that:
			import struct
			(...)
			iso = ISO8583()
			iso.setBit(3,'300000')
			(...)
			# Example: big-endian
			# To little-endian, replace 'iso.getNetworkISO()' with 'iso.getNetworkISO(False)'
			netIso = iso.getNetworkISO()
			newIso = ISO8583()
			# Example: big-endian
			# To little-endian, replace 'newIso.setNetworkISO()' with 'newIso.setNetworkISO(False)'
			newIso.setNetworkISO(netIso)
			#Is the same that:
			#size = netIso[0:2]
			## To little-endian, replace '!h' with '<h'
			#size = struct.unpack('!h',size )
			#newIso.setIsoContent(netIso[2:size])
			arr = newIso.getBitsAndValues()
			for v in arr:
				print ('Bit %s Type %s Value = %s' % (v['bit'],v['type'],v['value']))
			
			@param: iso -> str that represents size + ASCII ISO8583 package
			@param: bigEndian (True|False) -> Codification of the size.
			@raise: InvalidIso8583 Exception
		"""
		
		if len(iso) < 24:
			raise InvalidIso8583('This is not a valid iso!!Invalid Size')
		
		size = iso[0:2]
		if bigEndian:
			size = struct.unpack('!h',size)
			if self.DEBUG == True:
				print ('Unpack Big-endian')
		else:
			size = struct.unpack('<h',size)
			if self.DEBUG == True:
				print ('Unpack Little-endian')
		
		if len(iso) != (size[0] + 2):
			raise InvalidIso8583('This is not a valid iso!!The ISO8583 ASCII(%s) is less than the size %s!' % (len(iso[2:]),size[0]))
			
		self.setIsoContent(iso[2:])	
	
	################################################################################################	
