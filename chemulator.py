"""
Chemulator
Version 0.8.0
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
import re

"""
Global immutables
"""
beaker_types = {
	'large':100,
	'normal':50
}

with open('cookbook.yml','r') as cbf:
	cookbook = yaml.load(cbf, Loader=yaml.Loader)
with open('reagents.yml','r') as rf:
	reagent_book = yaml.load(rf, Loader=yaml.Loader)

"""
Global classes
"""

class World:
	def __init__(self):
		self.machines = []
		self.tube_connections = []

	def load_layout(self, layout_path):
		with open(layout_path, 'r') as f:
			data = yaml.load(f, Loader=yaml.Loader)
			for entry_name, entry in data.items():
				if entry['machine'] == 'chemicompiler':
					chemfuck_data = ''
					chemfuck_path = entry['program']
					if not os.path.exists(chemfuck_path):
						print("File Error")
						print("Chemfuck file '{}' for Chemicompiler '{}' does not exist.".format(chemfuck_path, entry_name))
						exit(1)
					else:
						with open(chemfuck_path,'r') as cff:
							chemfuck_data = cff.read()

					new_chemicompiler = Chemicompiler(self)
					new_chemicompiler.name = entry_name
					new_chemicompiler.program = chemfuck_data
					new_chemicompiler.load_reservoir(entry['reservoirs'])
					self.machines.append(new_chemicompiler)

			#Link the reservoirs together with "tubes"
			for connection in self.tube_connections:
				for machine in self.machines:
					if machine.name != connection['target_name']:
						continue
					del connection['pusher_reservoir']
					connection['pusher'].reservoirs[connection['pusher_slot']] = machine.reservoirs[connection['target_slot']]



	def run(self):
		for machine in self.machines:
			while machine.tick():
				pass

class Reagent:
	"""
	Basic reagent class that defines the reagent's name and volume of units in a beaker.
	"""
	def __init__(self, identifier):
		if identifier not in reagent_book.keys():
			print('Reagent Error')
			print('Reagent ID "{}" not found in list of valid reagents.'.format(identifier))
			exit(1)
		self.identifier = identifier
		self.name = reagent_book[identifier]
		self.possible_reactions = {}

		for reaction_name, reaction in cookbook.items():
			for reagent_identifier in reaction['required_reagents'].keys():
				if reagent_identifier == self.identifier:
					self.possible_reactions[reaction_name] = reaction

		self.volume = 0

class Beaker:
	"""
	Basic beaker class that holds reagents
	TODO: Turn this into "Container" class. Make beakers separate classes that extend this class.
	TODO: Move some of the routines to a "ReagenHandler" class to decrease clutter
	"""
	def __init__(self, parent, load_data=None):
		self.parent = parent
		self.world = self.parent.world
		self.name = ""
		self.volume = 50
		self.contents = {}
		self.total_temperature = 0
		self.total_volume = 0
		self.free_volume = 50

		if load_data:
			self.name = load_data['name']
			for key in load_data.keys():
				if key == 'beaker':
					if load_data['beaker'] in beaker_types.keys():
						self.volume = beaker_types[load_data['beaker']]
					else:
						#Handles machine-to-machine tube connections
						tube_search = re.search(r'tube\-(.+)\-(\d+)', load_data['beaker'])
						if tube_search:
							target_machine_name = tube_search.group(1)
							target_machine_slot = tube_search.group(2)
							self.world.tube_connections.append({
								'pusher': self.parent,
								'pusher_reservoir': self,
								'pusher_slot': int(load_data['position']),
								'target_name': target_machine_name,
								'target_slot': int(target_machine_slot)
							})

				if key == 'contents':
					for reagent_identifier,volume in load_data['contents'].items():
						self.add_reagent(reagent_identifier, volume)

	def handle_reactions(self):
		"""
		Matches reaction handler behavior used by Goon.
		"""
		#Set initial flag telling us we have reactions to compute
		reaction_occured = True
		while reaction_occured:
			reaction_occured = False
			for container_reagent_identifier, container_reagent in list(self.contents.items()):
				for reaction_identifier, reaction in container_reagent.possible_reactions.items():
					#Initial quick and easy checks
					if len(reaction['required_reagents'].keys()) < 1:
						continue
					if reaction['min_temperature'] != None:
						if self.total_temperature < reaction['min_temperature']:
							continue
					if reaction['max_temperature'] != None:
						print(reaction['max_temperature'])
						if not self.total_temperature < reaction['max_temperature']:
							continue
					if len(reaction['inhibitors']) > 0:
						for reagent_identifier in reaction['inhibitors']:
							if reagent_identifier in self.contents.keys():
								continue

					matching_reagents = []
					created_volume = self.volume
					for reagent_identifier, volume in reaction['required_reagents'].items():
						if reagent_identifier in self.contents.keys():
							if self.contents[reagent_identifier].volume >= volume:
								matching_reagents.append(self.contents[reagent_identifier])
								created_volume = min(created_volume, (self.contents[reagent_identifier].volume * reaction['result_amount']) / volume)
							else:
								break

					if len(matching_reagents) != len(reaction['required_reagents'].keys()):
						continue

					print('({}): {}'.format(reaction_identifier,reaction.get('mix_phrase','')))

					#Everything looks good. Let's get cooking!
					
					for reagent_identifier,reagent_volume in reaction['required_reagents'].items():
						self.remove_reagent(reagent_identifier, (reagent_volume * created_volume) / reaction['result_amount'])

					self.add_reagent(reaction['result'], created_volume, self.total_temperature)

					reaction_occured = True
				

	def update_total_volume(self):
		"""
		Updates the total and free volume values.
		Remove any empty reagents.
		"""
		self.total_volume = 0
		for reagent_id,reagent in list(self.contents.items()):
			if reagent.volume == 0:
				del self.contents[reagent_id]
				continue
			self.total_volume += reagent.volume
		self.free_volume = self.volume - self.total_volume

	def add_reagent(self, reagent_identifier, reagent_volume, reagent_temperature=273+20):
		"""
		Adds a reagent to the container.
		"""
		self.update_total_volume()
		if reagent_volume == 0:
			return
		elif reagent_volume > self.free_volume:
			reagent_volume = self.free_volume

		if reagent_identifier in self.contents.keys():
			existing_reagent = self.contents[reagent_identifier]
			new_reagent_volume = existing_reagent.volume + reagent_volume
			self.contents[reagent_identifier].volume += reagent_volume
		else:
			new_reagent = Reagent(reagent_identifier)
			new_reagent.volume = reagent_volume

			new_reagent_volume = reagent_volume
			self.contents[reagent_identifier] = new_reagent

		self.total_temperature = (self.total_temperature * self.total_volume + reagent_temperature * new_reagent_volume) / (self.total_volume + new_reagent_volume)
		self.update_total_volume()
		self.handle_reactions()

	def remove_reagent(self, target_identifier, volume):
		"""
		Remove a reagent targeted by its name in [volume] units.
		"""
		for reagent_identifier,reagent in list(self.contents.items()):
			if reagent_identifier == target_identifier:
				reagent.volume -= volume
				self.total_volume -= volume

				if reagent.volume == 0:
					del self.contents[reagent_identifier]
		


	def transfer_contents_to(self, transfer_target, transfer_volume):
		"""
		Evenly transfers reagents to a target container
		Basically reagents/trans_to combined with reagents/trans_to_direct
		"""

		if transfer_volume > self.total_volume:
			transfer_volume = self.total_volume

		transfer_ratio = transfer_volume/self.total_volume

		for reagent_identifier,reagent in list(self.contents.items()):
			transfer_amount = reagent.volume*transfer_ratio
			transfer_target.add_reagent(reagent_identifier, transfer_amount, self.total_temperature)

			self.remove_reagent(reagent_identifier, transfer_amount)

		self.update_total_volume()
		self.handle_reactions()
		transfer_target.update_total_volume()
		transfer_target.handle_reactions()


	def set_temperature(self, new_temperature):
		"""
		Sets the temperature of the container.
		"""
		self.total_temperature = new_temperature

		self.handle_reactions()

class ChemistryMachine:
	def __init__(self, world):
		self.world = world
		self.type = None

	def tick(self):
		return False

class ReagentReservoir(ChemistryMachine):
	"""
	An unlimited reagent reservoir machine.
	Pushes 100 units of a specified reagent to a connected reagent container.
	"""
	def __init__(self, world):
		super().__init__(world)
		self.type = 'reagent_reservoir'
		self.connected_reagent_container = None
		self.reagent = None

	def tick(self):
		if self.connected_reagent_container:
			self.connected_reagent_container.add_reagent(self.reagent, 100)
		return False

class Chemicompiler(ChemistryMachine):
	"""
	ChemiCompiler class. Does all of the magic!
	"""
	def __init__(self, world):
		super().__init__(world)
		self.type = 'chemicompiler'
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

	def load_reservoir(self, reservoir_data):
		for beaker_name,beaker_data in reservoir_data.items():
			beaker_data['name'] = beaker_name
			new_beaker = Beaker(self, beaker_data)
			self.reservoirs[int(beaker_data['position'])] = new_beaker

	def tick(self):
		return self.execute()

	def execute(self):
		sym = self.program[self.ip]	#Load symbol from PC
		#print("Symbol: {}".format(sym))
		#self._print_nearest_data()
		sym_routine = self.symbol_routines_dict.get(sym,self._op_noop)
		sym_routine()
		self.ip+=1
		if self.ip > (len(self.program)-1):
			#print('ChemiCompiler program complete')
			self._print_reservoirs()
			return False
			#exit(1)
		return True

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
		print('Chemicompiler({}) Reservoirs:'.format(self.name))
		for i in range(0,11):
			if self.reservoirs[i] != None:
				reservoir = self.reservoirs[i]
				if reservoir.parent != self:
					t_machine = reservoir.parent.type
					t_name = reservoir.parent.name
					for j in range(0,11):
						if reservoir.parent.reservoirs[j] == reservoir:
							t_slot = j
							break
					print('\t{}({})-TUBE-{}({})[{}]:'.format(i,reservoir.name,t_machine,t_name,t_slot))
				else:
					print('\t{}({}):'.format(i,reservoir.name))
				print('\t\tVolume: {} units'.format(reservoir.volume))
				print('\t\tTemperature: {}K'.format(reservoir.total_temperature))
				print('\t\tContents:')
				for reagent_name,reagent in reservoir.contents.items():
					print('\t\t\t{}: {} units'.format(reagent_book[reagent_name]['name'], reagent.volume))

	"""
	Utility ChemiCompiler routines
	"""
	def _throw_chem_error(self, error_message):
		print("ChemiCompiler Error")
		print('({}) {}'.format(self.name, error_message))
		exit(1)

	def _transfer_reagents(self, source_slot, target_slot, transfer_volume):
		if self.reservoirs[source_slot] == None:
			self._throw_chem_error("Source slot {} has no container!".format(source_slot))
		if self.reservoirs[target_slot] == None:
			self._throw_chem_error("Destination slot {} has no container!".format(target_slot))
		if self.reservoirs[source_slot].total_volume == 0:
			self._throw_chem_error("Source slot {} is empty!".format(source_slot))

		reservoir_target = self.reservoirs[target_slot]
		reservoir_source = self.reservoirs[source_slot]
		
		print("Chemicompiler({}) transfer {} units from {}({}) to {}({})".format(self.name, transfer_volume, source_slot, reservoir_source.name, target_slot, reservoir_target.name))
		reservoir_source.transfer_contents_to(reservoir_target, transfer_volume)

	def _heat_reagents(self, target_slot, target_temperature):
		if self.reservoirs[target_slot] == None:
			self._throw_chem_error("Target slot {} has no container!".format(target_slot))

		print("Chemicompiler heat {} to {}K".format(target_slot, target_temperature))
		self.reservoirs[target_slot].set_temperature(target_temperature)

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
if(len(sys.argv) != 2):
	print("Syntax Error")
	print("Usage: chemulator.py <layout YAML>")
	exit(1)

if not os.path.exists(sys.argv[1]):
	print("File Error")
	print("Layout file '{}' does not exist.".format(sys.argv[1]))
	exit(1)
else:
	layout_path = sys.argv[1]

world = World()

world.load_layout(layout_path)

world.run()