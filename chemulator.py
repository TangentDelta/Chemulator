"""
Chemulator
Version 0.7.0
By TangentDelta

A Space Station 13 ChemiCompiler emulator and chemistry simulator!
Uses some code ported over from the Goonstation 2016 source dump.
"""


"""
Global imports
"""
import sys
import os.path
import yaml

"""
Global immutables
"""
beaker_types = {
	'large':100,
	'normal':50
}

with open('cookbook.yml','r') as cbf:
	cookbook = yaml.load(cbf, Loader=yaml.Loader)

"""
Global classes
"""

class Chemical:
	"""
	Basic chemical class that defines the chemical's name and volume of units in a beaker.
	TODO: Remove entirely in favor of reagent dict in container
	"""
	def __init__(self):
		self.name = ""
		self.temperature = 273
		self.volume = 0

class Beaker:
	"""
	Basic beaker class that holds chemicals
	TODO: Turn this into "Container" class. Make beakers separate classes that extend this class.
	TODO: Move some of the routines to a "ReagenHandler" class to decrease clutter
	"""
	def __init__(self, load_data=None):
		self.name = ""
		self.volume = 50
		self.contents = {}
		self.total_temperature = 0
		self.total_volume = 0

		if load_data:
			self.name = load_data['name']
			if 'beaker' in load_data.keys():
				self.volume = beaker_types[load_data['beaker']]

			if load_data['contents'] != None:
				for chemical_name,volume in load_data['contents'].items():
					self.add_reagent(chemical_name, volume, 273)

	"""
	def handle_reactions_partial(self):
		for reaction_name, reaction in cookbook.items():
			if self.total_temperature < reaction['temp_low']:
				continue
			if 'temp_high' in reaction.keys():
				if not self.total_temperature < reaction['temp_high']:
					continue

			matching_reagents = []
			for reagent_name, volume in reaction['reagents'].items():
				if reagent_name in self.contents.keys():
					if self.contents[reagent_name].volume >= volume:
						matching_reagents.append(self.contents[reagent_name])

			if len(matching_reagents) != len(reaction['reagents'].keys()):
				continue

			#Everything looks good. Let's get cooking!
			limiting_reagent = ''
			reagent_ratios = {}
			least_ratio = 999
			for reagent_name in reaction['reagents'].keys():
				reagent_ratio = self.contents[reagent_name].volume / reaction['reagents'][reagent_name]
				reagent_ratios[reagent_name] = reagent_ratio

				if reagent_ratio < least_ratio:
					least_ratio = reagent_ratio
					limiting_reagent = reagent_name

			print('{}: Limiting reagent: {}'.format(reaction_name, limiting_reagent))
			
			for reagent_name,reagent in self.contents.items():
				reaction_volume = reaction['reagents'][reagent_name]
				self.remove_reagent(reagent_name,reaction_volume*least_ratio)

			self.add_reagent(reaction_name, reaction['volume']*least_ratio, self.total_temperature)
			self.purge_empty_reagents()
	"""

	def handle_reactions(self):
		"""
		Matches behavior used by Goon.
		Reagents are not partially consumed during a reaction.
		"""
		#Set initial flag telling us we have reactions to compute
		reaction_occured = True
		while reaction_occured:
			reaction_occured = False
			for reaction_name, reaction in cookbook.items():
				if 'temp_low' in reaction.keys():
					if self.total_temperature < reaction['temp_low']:
						continue
				if 'temp_high' in reaction.keys():
					if not self.total_temperature < reaction['temp_high']:
						continue

				matching_reagents = []
				for reagent_name, volume in reaction['reagents'].items():
					if reagent_name in self.contents.keys():
						if self.contents[reagent_name].volume >= volume:
							matching_reagents.append(self.contents[reagent_name])

				if len(matching_reagents) != len(reaction['reagents'].keys()):
					continue

				#Everything looks good. Let's get cooking!
				for reagent_name in reaction['reagents'].keys():
					reaction_volume = reaction['reagents'][reagent_name]
					self.remove_reagent(reagent_name,reaction_volume)

				self.add_reagent(reaction_name, reaction['volume'], self.total_temperature)

				reaction_occured = True

		self.purge_empty_reagents()


	def add_reagent(self, reagent_name, reagent_volume, reagent_temperature):
		"""
		Adds a reagent to the container.
		"""
		#Ensure that the container does not overflow!
		volume_free = self.volume - self.total_volume

		if reagent_volume > volume_free:
			reagent_volume = volume_free

		self.total_volume += reagent_volume

		if reagent_name in self.contents.keys():
			existing_reagent = self.contents[reagent_name]
			new_reagent_volume = existing_reagent.volume + reagent_volume
			current_reagent_ratio = existing_reagent.volume/new_reagent_volume
			new_reagent_ratio = reagent_volume/new_reagent_volume
			new_reagent_temp = (existing_reagent.temperature*current_reagent_ratio) + (reagent_temperature*new_reagent_ratio)
			self.contents[reagent_name].temperature = new_reagent_temp
			self.contents[reagent_name].volume += reagent_volume
		else:
			new_reagent = Chemical()
			new_reagent.name = reagent_name
			new_reagent.volume = reagent_volume
			new_reagent.temperature = reagent_temperature
			self.contents[reagent_name] = new_reagent
		
		#Calculate new totals
		self.total_volume = 0
		for reagent in self.contents.values():
			self.total_volume += reagent.volume

		self.total_temperature = 0
		for reagent in self.contents.values():
			reagent_ratio = reagent.volume/self.total_volume
			self.total_temperature += reagent.temperature*reagent_ratio
			

	def remove_reagent(self, target_name, volume):
		"""
		Remove a reagent targeted by its name in [volume] units.
		Does not remove the reagent if its volume reaches 0! Use "purge_empty_reagents" for that.
		"""
		for reagent_name,reagent in self.contents.items():
			if reagent_name == target_name:
				reagent.volume -= volume
				self.total_volume -= volume
			
		


	def transfer_contents_to(self, transfer_target, transfer_volume):
		"""
		Evenly transfers reagents to a target container
		"""
		#Calculate the total amount of volume occupied by reagents
		self.total_volume = 0
		for reagent in self.contents.values():
			self.total_volume += reagent.volume

		if transfer_volume > self.total_volume:
			transfer_volume = self.total_volume

		transfer_ratio = transfer_volume/self.total_volume

		for reagent_name,reagent in self.contents.items():
			transfer_amount = reagent.volume*transfer_ratio
			transfer_target.add_reagent(reagent_name, transfer_amount, reagent.temperature)

			self.remove_reagent(reagent_name, transfer_amount)

		transfer_target.handle_reactions()

		self.purge_empty_reagents()


	def set_temperature(self, new_temperature):
		"""
		Sets the temperature of the container and the reagents contained within it.
		"""
		for reagent in self.contents.values():
			reagent.temperature = new_temperature

		self.total_temperature = new_temperature

		self.handle_reactions()

	def purge_empty_reagents(self):
		"""
		Removes reagents that have a volume of 0 units.
		"""
		purge_list = []

		for reagent_name, reagent in self.contents.items():
			if reagent.volume == 0:
				purge_list.append(reagent_name)

		for reagent_name in purge_list:
			del self.contents[reagent_name]

class ChemiCompiler:
	"""
	ChemiCompiler class. Does all of the magic!
	"""
	def __init__(self):
		self.symbol_routines_dict = {
			'>':self._op_move_pointer_right,
			'<':self._op_move_pointer_left,
			'+':self._op_increment_memory_cell,
			'-':self._op_decrement_memory_cell,
			'[':self._op_while_loop,
			']':self._op_while_loop_backwards,
			'{':self._op_store_sx,
			'}':self._op_load_sx,
			'(':self._op_store_tx,
			')':self._op_load_tx,
			'^':self._op_store_ax,
			'\'':self._op_load_ax,
			'$':self._op_heat_reagent,
			'@':self._op_transfer_reagent
		}

		self.program = ""

		self.ram = [0x00]*1024
		self.reservoirs = [None]*11

		self.ip = 0	#Instruction Pointer
		self.dp = 0	#Data Pointer
		self.sx = 0 #Source Register
		self.tx = 0 #Target Register
		self.ax = 0 #Amount Register

	def load_program(self, program_path):
		with open(program_path, 'r') as ppf:
			self.program = ppf.read()

	def load_reservoir(self, reservoir_path):
		with open(reservoir_path, 'r') as rpf:
			data = yaml.load(rpf, Loader=yaml.Loader)
			for beaker_name,beaker_data in data.items():
				beaker_data['name'] = beaker_name
				new_beaker = Beaker(beaker_data)
				self.reservoirs[int(beaker_data['position'])] = new_beaker

	def execute(self):
		sym = self.program[self.ip]	#Load symbol from PC
		#print("Symbol: {}".format(sym))
		#self._print_nearest_data()
		sym_routine = self.symbol_routines_dict.get(sym,self._op_noop)
		sym_routine()
		self.ip+=1
		if self.ip > (len(self.program)-1):
			print('ChemiCompiler program complete')
			self._print_reservoirs()
			exit(1)

	"""
	Debugging ChemiCompiler routines
	"""
	def _print_registers(self):
		print("IP:{} DP:{}".format(self.ip, self.dp))
		print("SX:{} TX:{} AX:{}".format(self.sx, self.tx, self.ax))

	def _print_nearest_data(self):
		look = ['']*10
		for i in range(0,9):
			look_addr = (self.dp + (i-4)) & 0x3ff

			if look_addr == self.dp:
				look[i] = '['+str(self.ram[look_addr])+']'
			else:
				look[i] = str(self.ram[look_addr])

		print(' '.join(look))

	def _print_reservoirs(self):
		for i in range(0,11):
			if self.reservoirs[i] != None:
				reservoir = self.reservoirs[i]
				print('{}({}):'.format(i,reservoir.name))
				print('\tVolume: {} units'.format(reservoir.volume))
				print('\tTemperature: {}K'.format(reservoir.total_temperature))
				print('\tContents:')
				for reagent_name,reagent in reservoir.contents.items():
					print('\t\t{}: {} units {}K'.format(reagent_name, reagent.volume, reagent.temperature))

	"""
	Utility ChemiCompiler routines
	"""
	def _throw_chem_error(self, error_message):
		print("ChemiCompiler Error")
		print(error_message)
		exit(1)

	def _transfer_reagents(self, source_slot, target_slot, transfer_volume):
		if self.reservoirs[source_slot] == None:
			self._throw_chem_error("Source slot {} has no container!".format(source_slot))
		if self.reservoirs[target_slot] == None:
			self._throw_chem_error("Destination slot {} has no container!".format(target_slot))

		reservoir_target = self.reservoirs[target_slot]
		reservoir_source = self.reservoirs[source_slot]

		reservoir_source.transfer_contents_to(reservoir_target, transfer_volume)

		print("Chemicompiler transfer {} units from {}({}) to {}({})".format(transfer_volume, source_slot, reservoir_source.name, target_slot, reservoir_target.name))

	def _heat_reagents(self, target_slot, target_temperature):
		if self.reservoirs[target_slot] == None:
			self._throw_chem_error("Target slot {} has no container!".format(target_slot))

		self.reservoirs[target_slot].set_temperature(target_temperature)

		print("Chemicompiler heat {} to {}K".format(target_slot, target_temperature))
		self._print_reservoirs()

	"""
	Chemfuck symbol routines
	"""
	def _op_noop(self):
		pass

	def _op_move_pointer_right(self):	#	>
		self.dp = (self.dp + 1) & 0x3ff

	def _op_move_pointer_left(self):	#	<
		self.dp = (self.dp - 1) & 0x3ff

	def _op_increment_memory_cell(self):	#	+
		self.ram[self.dp] = (self.ram[self.dp] + 1) & 0xff

	def _op_decrement_memory_cell(self):	#	-
		self.ram[self.dp] = (self.ram[self.dp] - 1) & 0xff

	def _op_while_loop(self):	#	[
		if self.ram[self.dp] == 0:
			count = 1
			while(self.ip <= len(self.program) and (count > 0)):
				if(self.program[self.ip] == '['):
					count+=1
				if(self.program[self.ip] == ']'):
					count-=1

				self.ip+=1

	def _op_while_loop_backwards(self):	#	]
		if self.ram[self.dp] != 0:
			count = 1
			self.ip-=1
			while(self.ip > 1 and (count > 0)):
				self.ip -=1

				if(self.program[self.ip] == '['):
					count-=1
				if(self.program[self.ip] == ']'):
					count+=1

			if(self.ip == 1 and (count > 0)):
				print("Execution Error")
				print("Instruction Pointer Underflow")
				print("Could not locate matching brace for backwards while loop")
				exit(1)

	def _op_store_sx(self):	#	{
		self.ram[self.dp] = self.sx

	def _op_load_sx(self): #	}
		self.sx = self.ram[self.dp]

	def _op_store_tx(self):	#	(
		self.ram[self.dp] = self.tx

	def _op_load_tx(self): #	)
		self.tx = self.ram[self.dp]

	def _op_store_ax(self):	#	^
		self.ram[self.dp] = self.ax

	def _op_load_ax(self):	#	'
		self.ax = self.ram[self.dp]

	def _op_heat_reagent(self):	#	$
		new_temp = (273 - self.tx) + self.ax
		self._heat_reagents(self.sx, new_temp)

	def _op_transfer_reagent(self):	#	@
		self._transfer_reagents(self.sx, self.tx, self.ax)

"""
Main code
"""
if(len(sys.argv) != 3):
	print("Syntax Error")
	print("Usage: chemulator.py <chemfuck program> <reservoir YAML>")
	exit(1)

if not os.path.exists(sys.argv[1]):
	print("File Error")
	print("Chemfuck file '{}' does not exist.".format(sys.argv[1]))
	exit(1)
else:
	program_path = sys.argv[1]

if not os.path.exists(sys.argv[2]):
	print("File Error")
	print("Reservoir file '{}' does not exist.".format(sys.argv[2]))
	exit(1)
else:
	reservoir_path = sys.argv[2]

chemi_comp = ChemiCompiler()
chemi_comp.load_program(program_path)
chemi_comp.load_reservoir(reservoir_path)

while True:
	chemi_comp.execute()