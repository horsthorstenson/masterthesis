import sys, getopt,subprocess, os, errno 

def main(argv):
       
	if (len(argv) != 2):
		print 'usage: restore.py <image offset> <disk name>'	 	
		exit(2)
	vol_offset = argv[0]
	img_name = argv[1]
	error = "Cannot determine file system type"
	try:
		journal_inum = subprocess.check_output(["ifind", "-n", ".journal", "-o", vol_offset , img_name]).strip()
	except: 
		exit(2)
	try:
		j = subprocess.check_output(["icat", "-o", vol_offset, img_name, journal_inum]).strip()
	except:
		exit(2)
	length = len(j) - 148
	
	#check Journal Header magic and endian
	if(	ord(j[0]) != 0x78 or
		ord(j[1]) != 0x4c or
		ord(j[2]) != 0x4e or
		ord(j[3]) != 0x4a or
		ord(j[4]) != 0x78 or
		ord(j[5]) != 0x56 or
		ord(j[6]) != 0x34 or
		ord(j[7]) != 0x12
		):
		print "Journal header is corrupt!"
		exit(2)

	candidates = []
	block_addr = []
	for i in range(30,length):
	 if(
		#check file and flag
		ord(j[i])   == 0x00 and
		ord(j[i+1]) == 0x02 and
		ord(j[i+2]) == 0x00 and
		ord(j[i+3]) == 0x86 and
		ord(j[i-7]) == 0x2e 
		):
		 if(ord(j[i-7]) == 0x2e or
		    ord(j[i-8]) == 0x2e
		 ):
		 #check if Resource Fork is 0
		  for k in range (168, 248):
		   if(ord(j[i+k]) != 0x00):
		    break
		  adress = conv(j[i+104:i+108])
		  if adress != 0 and adress not in block_addr:
		   candidates.append(i)
		   block_addr.append(adress)

	#candidates: list of possible dates
	dir_name = "files_" + img_name
	create_dirs(dir_name)
	for x in candidates:
		
		file_name = get_file_name(j,x)
		extents = check_extents(j, x)
		data = ''
		#more than one extent
		for k in range (0,extents*8,8):
			start_block = conv(j[x+k+104:x+k+108])
			num_blocks = conv(j[x+k+100:x+k+104])
			#load data from actual extent
			for i in range (0,num_blocks):
				data += subprocess.check_output(["blkcat", "-o", vol_offset, img_name, str(start_block), str(num_blocks)]).strip()
		file_name = get_file_name(j,x)
		if get_block_alloc(vol_offset, img_name, conv(j[x+104:x+108])) == 0:
			os.chdir(dir_name+"/NotAllocated")
		else:
			os.chdir(dir_name+"/Allocated")	
		file = open(file_name, 'w')
		file.write(data)
		file.close
		os.chdir("..")
		os.chdir("..")
		
		
def create_dirs(dir_name):
	try:
		os.makedirs(dir_name)
	except OSError:
		pass
	os.chdir(dir_name)
	try:
		os.makedirs("Allocated")
	except OSError:
		pass
	try:
		os.makedirs("NotAllocated")
	except OSError:
		pass	
	os.chdir("..")
	return 0		

def check_extents(inp, x):
	count = 0
	for i in range (0,64,8):
		if conv(inp[x+i+104:x+i+108]) != 0:
			count += 1
	return count	

def get_file_name(inp,x):
	name = ''
	for i in range(1,30,2):
		if ord(inp[x-i]) > 32 and ord(inp[x-i]) < 122:
			name = (inp[x-i]) + name
		else:
			break	
	return name
	
def conv(inp):
	return int((inp.encode("hex")),16)
	
def get_block_alloc(vol_offset, img_name, addr):
	notall = "Not Allocated"
	b = subprocess.check_output(["blkstat", "-o", vol_offset, img_name, str(addr)]).strip()
	if (b.splitlines()[1] == notall):
		return 0
	else:
		return 1	
	
if __name__ == "__main__":
   main(sys.argv[1:])
