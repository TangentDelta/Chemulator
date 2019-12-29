# Chemulator

 Goonstation ChemiCompiler Emulator and Chemistry Simulator

## Requirements

- Python 3

## Usage

`python3 chemulator.py [your_chemulator_layout_file.yml]`

The actions of the machines are printed to the console. At the end of a run for a machine, the final reservoir layout is printed.

## Chemulator Layour File Format

The chemulator layout file uses YAML.

The data structure is as follows:

```yaml
MachineLabelOne:  #The human-readable label of the machine.
  machine: chemicompiler  #The type of machine (chemicompiler)
  program: path_to_chemfuck_file  #Path to the chemfuck file to run
  reservoirs:
    ReservoirLabel:  #The human-readable label of this reservoir
      beaker: large  #Optional beaker type
      position: 5  #The reagent reservoir slot in the chemicompiler
      contents:  #An optional list of the reagents in the reservoir
        reagent_identifier: 5  #reagent_identifier is the ID of a reagent from the reagents file. The number assigned to it is the volume of that reagent in the reservoir.
        reagent_identifier: 10
        ...
    ReservoirLable:
      beaker: tube-MachineLabelTwo-2  #Attaches a tube from this reservoir slot to the beaker specified in the machine label, at the slot specified after the machine label
      #Syntax: tube-[target machine's label]-[target machine's slot]
MachineLabelTwo:
  machine: chemicompiler
  program: path_to_chemfuck_file
  reservoirs:
    ReservoirLabel:
      position: 2
...

```

## How The Simulation Is Run

Each machine is only allowed to run once. The order in which the machines are run is determined by their order in the Chemulator layout file. Any chemical reactions that occur have their identifier printed, followed by the flavor text. At the end of each machine's run, the reservoir contents are printed.
