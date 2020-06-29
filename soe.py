import numpy as np
import random
import time
import sys
from math import sqrt
import matplotlib.pyplot as plt
import matplotlib.animation as anim

class Person:
	def __init__(self,number,location=None):
		self.number = number # some unique number to identify the person [0-n int]
		self.location = location # current location on the grid [[x,y] list]
		self.time_in_proximity = 0 # time spent in proximity of an infected [int]
		self.time_in_treatment = 0 # time spent in treatement/observation [int]
		self.time_in_healing = 0 # time spent in self healing [int]
		self.n_infected = 0 # no of people infected by, while staying infected [int]
		
class Environment:
	def __init__(self,env_limits,infection_probability=0.2,no_symptoms_probability=0.2,infection_radius=1,central_hub=False,threshold=0,quarantine_rate=0.80,fatality_rate=0.3,SDF=0.0,travel_rate=0.002):
		# environment characteristics
		self.env_limits = env_limits # size of the grid [(max_x,max_y) tuple]
		self.infection_probability = infection_probability # probability of infection spread [0-0.99 float]
		self.no_symptoms_probability = no_symptoms_probability # probability of showing no symptoms [0-0.99 float]	
		self.infection_radius = infection_radius * 3 # infection radius [1,1.5,2 float], x3 for plotting and proximity checking convenience
		self.central_hub = central_hub # existence of a central hub [boolean]
		self.threshold = threshold # no. of infected after which restriction will be applied [0:no threshold,n:number of infected int]
		self.quarantine_rate = quarantine_rate # per% of infected being quarantined [0-1 float]
		self.till_quarantine = 0 # time after which infected(ws) will be quarantined [int]
		self.till_selfcure = 0 # time after which infected(wos) become negative(cured) [int/float]
		self.fatality_rate = fatality_rate # fatality rate [0-1 float]
		self.SDF = SDF # social distancing fator [1-5 int]
		self.travel_rate = travel_rate # likeliness of traveling [0-1 float]
		self.ERN = 0 # Effective Reproductive Number calculated constantly [int]
		
		# population information
		self.susceptible = list() # list of susceptible population objects
		self.infected = list() # list of infected population objects
		self.infected_ws = list() # list of infected population objects with symptoms
		self.infected_wos = list() # list of infected population objects without symptoms
		self.new_infected = list() # new infected found every iteration [list]
		self.infected_wos_cured = list() # no. of cured infected(wos) [list]
		self.quarantined = list() # no. of quarantined [list]
		
		# plotting parameters
		self.fig = None # pyplot figure object for plotting and animation
		self.ax = None # 
		self.s_scatter = None # scatter plot object for plotting susceptible population
		self.i_ws_scatter = None # scatter plot object for plotting infected(ws) population
		self.i_ws_prox_scatter = None # scatter plot object for plotting infection radius for infected(ws)
		self.i_wos_scatter = None # scatter plot object for plotting infected(wos) population
		self.i_wos_prox_scatter = None # scatter plot object for plotting infection radius for infected(wos)
		self.i_wos_cured_scatter = None # scatter plot object for plotting cured infected(wos)
		self.proximity_size = None # size of infection radius for plotting
		self.jitter = None # jitter factor for more random movement
		
		# real-time data
		self.infected_per_day = list()

	def init_population(self,uninf_p,inf_p):
		x = self.env_limits[0];y = self.env_limits[1]
		# assign random initial positions to uninfected people
		for i in range(uninf_p):
			self.susceptible.append(Person(i,[random.randint(0,x),random.randint(0,y)]))
		# assign random initial positions to infected people
		for i in range(inf_p):
			self.infected_ws.append(Person(i*-1,[random.randint(0,x),random.randint(0,y)]))
		else:
			del x,y

	# configure plotting parameters
	def config_plot(self):
		self.fig = plt.figure(1)
		self.proximity_size = self.infection_radius * 100
		self.ax = plt.axes(xlim=(0,self.env_limits[0]),ylim=(0,self.env_limits[1]))
		self.s_scatter = self.ax.scatter([],[],s=10)
		self.i_ws_scatter = self.ax.scatter([],[],s=10,c='red')
		self.i_ws_prox_scatter = self.ax.scatter([],[],s=self.proximity_size,c='red',alpha=0.2)
		self.i_wos_scatter = self.ax.scatter([],[],s=10,c='green')
		self.i_wos_prox_scatter = self.ax.scatter([],[],s=self.proximity_size,c='green',alpha=0.2)
		self.i_wos_cured_scatter = self.ax.scatter([],[],s=10,c='grey')

	def config_misc(self,jitter,till_q,till_sc):
		self.jitter = jitter # amount of randomness in movement of people
		self.till_quarantine = till_q
		self.till_selfcure = till_sc
				
	# initialize scatter plot
	def init_plot(self):
		self.s_scatter.set_offsets(np.c_[[],[]])
		self.i_ws_scatter.set_offsets(np.c_[[],[]])
		self.i_ws_prox_scatter.set_offsets(np.c_[[],[]])
		self.i_wos_scatter.set_offsets(np.c_[[],[]])
		self.i_wos_prox_scatter.set_offsets(np.c_[[],[]])
		self.i_wos_cured_scatter.set_offsets(np.c_[[],[]])
		
		return (self.s_scatter,self.i_ws_scatter,self.i_ws_prox_scatter,self.i_wos_scatter,self.i_wos_prox_scatter,self.i_wos_cured_scatter)
			
	# animation function which constantly updates scatter plot values in every iteration
	def animate_plot(self,i):
		self.update_population()
		self.commute()
		self.s_scatter.set_offsets(np.c_[[s.location[0] for s in self.susceptible],[s.location[1] for s in self.susceptible]])
		self.i_ws_scatter.set_offsets(np.c_[[i.location[0] for i in self.infected_ws],[i.location[1] for i in self.infected_ws]])
		self.i_ws_prox_scatter.set_offsets(np.c_[[i.location[0] for i in self.infected_ws],[i.location[1] for i in self.infected_ws]])
		self.i_wos_scatter.set_offsets(np.c_[[i.location[0] for i in self.infected_wos],[i.location[1] for i in self.infected_wos]])
		self.i_wos_prox_scatter.set_offsets(np.c_[[i.location[0] for i in self.infected_wos],[i.location[1] for i in self.infected_wos]])
		self.i_wos_cured_scatter.set_offsets(np.c_[[i.location[0] for i in self.infected_wos_cured],[i.location[1] for i in self.infected_wos_cured]])
		
		return (self.s_scatter,self.i_ws_scatter,self.i_ws_prox_scatter,self.i_wos_scatter,self.i_wos_prox_scatter,self.i_wos_cured_scatter)
	
	# calculate new positions for people every iteration						
	def commute(self):
		# new position for susceptible population
		for p in self.susceptible:
			if random.random() < self.travel_rate and self.central_hub:
					p.location[0] = self.env_limits[0]/2
					p.location[1] = self.env_limits[1]/2
			else:
				for j in range(self.jitter):
					p.location[0] += random.random();p.location[1] += random.random()
					p.location[0] -= random.random();p.location[1] -= random.random()
				else:
					if p.location[0] >= self.env_limits[0] : p.location[0] = random.randint(self.env_limits[0]*0.8,self.env_limits[0]) - random.random()
					elif p.location[0] <= 0	: p.location[0] = random.randint(0,self.env_limits[0]*0.2) - + random.random()
					elif p.location[1] >= self.env_limits[1] : p.location[1] = random.randint(self.env_limits[0]*0.8,self.env_limits[1]) - random.random()
					elif p.location[1] <= 0 : p.location[1] = random.randint(0,self.env_limits[1]*0.2) + random.random()
		# new position for infected population (ws)
		for p in self.infected_ws:
			if random.random() < self.travel_rate and self.central_hub:
					p.location[0] = self.env_limits[0]/2
					p.location[1] = self.env_limits[1]/2
			else:
				for j in range(self.jitter):
					p.location[0] += random.random();p.location[1] += random.random()
					p.location[0] -= random.random();p.location[1] -= random.random()
				else:
					if p.location[0] >= self.env_limits[0] : p.location[0] = random.randint(self.env_limits[0]*0.8,self.env_limits[0]) - random.random()
					elif p.location[0] <= 0	: p.location[0] = random.randint(0,self.env_limits[0]*0.2) - + random.random()
					elif p.location[1] >= self.env_limits[1] : p.location[1] = random.randint(self.env_limits[1]*0.8,self.env_limits[1]) - random.random()
					elif p.location[1] <= 0 : p.location[1] = random.randint(0,self.env_limits[1]*0.2) + random.random()
		# new position for infected population (wos)
		for p in self.infected_wos:
			if random.random() < self.travel_rate and self.central_hub:
					p.location[0] = self.env_limits[0]/2
					p.location[1] = self.env_limits[1]/2
			else:
				for j in range(self.jitter):
					p.location[0] += random.random();p.location[1] += random.random()
					p.location[0] -= random.random();p.location[1] -= random.random()
				else:
					if p.location[0] >= self.env_limits[0] : p.location[0] = random.randint(self.env_limits[0]*0.8,self.env_limits[0]) - random.random()
					elif p.location[0] <= 0	: p.location[0] = random.randint(0,self.env_limits[0]*0.2) - + random.random()
					elif p.location[1] >= self.env_limits[1] : p.location[1] = random.randint(self.env_limits[1]*0.8,self.env_limits[1]) - random.random()
					elif p.location[1] <= 0 : p.location[1] = random.randint(0,self.env_limits[1]*0.2) + random.random()
		# new position for infected population (wos) which got self cured
		for p in self.infected_wos_cured:
			if random.random() < self.travel_rate and self.central_hub:
					p.location[0] = self.env_limits[0]/2
					p.location[1] = self.env_limits[1]/2
			else:
				for j in range(self.jitter):
					p.location[0] += random.random();p.location[1] += random.random()
					p.location[0] -= random.random();p.location[1] -= random.random()
				else:
					if p.location[0] >= self.env_limits[0] : p.location[0] = random.randint(self.env_limits[0]*0.8,self.env_limits[0]) - random.random()
					elif p.location[0] <= 0	: p.location[0] = random.randint(0,self.env_limits[0]*0.2) - + random.random()
					elif p.location[1] >= self.env_limits[1] : p.location[1] = random.randint(self.env_limits[1]*0.8,self.env_limits[1]) - random.random()
					elif p.location[1] <= 0 : p.location[1] = random.randint(0,self.env_limits[1]*0.2) + random.random()
						
	# check if an individual is inside the proximity of an infected
	def check_proximity(self,combo=1):
		# check for vicinity of infected (ws)
		for i in range(len(self.infected_ws)):
			for s in range(len(self.susceptible)):
				# distance formula to find distance from center of proximity
				if sqrt((self.infected_ws[i].location[0] - self.susceptible[s].location[0])**2 + (self.infected_ws[i].location[1] - self.susceptible[s].location[1])**2) < self.infection_radius:
					if self.susceptible[s].time_in_proximity < 1 : self.susceptible[s].time_in_proximity += 0.25
					else: 
						self.new_infected.append(s)
						self.infected_ws[i].n_infected += 1
		# check for vicinity of infected (wos)
		for i in range(len(self.infected_wos)):
			for s in range(len(self.susceptible)):
				if sqrt((self.infected_wos[i].location[0] - self.susceptible[s].location[0])**2 + (self.infected_wos[i].location[1] - self.susceptible[s].location[1])**2) < self.infection_radius:
					if self.susceptible[s].time_in_proximity < 1 : self.susceptible[s].time_in_proximity += 0.25
					else: self.new_infected.append(s)	

	# update newly infected people every iteration, moving susceptibles to infected category	
	def update_infected(self):
		if len(self.new_infected) != 0:
			for n in self.new_infected:
				if random.random() < self.infection_probability:
					if random.random() < self.no_symptoms_probability:
						if n >= len(self.susceptible):pass
						else:
							self.infected_wos.append(self.susceptible[n])
							del self.susceptible[n]
					else:
						if n >= len(self.susceptible):pass
						else:
							self.infected_ws.append(self.susceptible[n])
							del self.susceptible[n]
			else:
				self.new_infected = list()
				
	# quarantine infected after set time as passed, move to quarantined category
	def quarantine_infected_ws(self):
		new_quarantined = list()
		for i in range(len(self.infected_ws)):
			if self.infected_ws[i].time_in_treatment < self.till_quarantine:
				self.infected_ws[i].time_in_treatment += 0.1
			else:
				new_quarantined.append(i)
		if len(new_quarantined) != 0:	
			for q in new_quarantined:
				if q >= len(self.infected_ws) : pass
				else:
					if random.random() < self.quarantine_rate:
						self.quarantined.append(self.infected_ws[q])
						del self.infected_ws[q]
	
	# set status to cured for infected (wos) after set time has passed, move to cured category		
	def cure_infected_wos(self):
		new_cured_wos = list()
		for i in range(len(self.infected_wos)):
			if self.infected_wos[i].time_in_healing < self.till_selfcure:
				self.infected_wos[i].time_in_healing += 0.1
			else:
				new_cured_wos.append(i)
		if len(new_cured_wos) != 0:
			for c in new_cured_wos:
				if c >= len(self.infected_wos) : pass
				else:
					self.infected_wos_cured.append(self.infected_wos[c])
					del self.infected_wos[c]
	
	# calculate Effective Reproductive Number every iteration (day)
	def calc_ERN(self):
		pass
			
	# single function which calls steps (functions) of an epedemic spread in an order
	def update_population(self):
		self.check_proximity()
		self.update_infected()
#		self.calc_ERN()
		self.quarantine_infected_ws()
		self.cure_infected_wos()

	# running animation to simulate
	def run_simulation(self):
		animation = anim.FuncAnimation(self.fig,self.animate_plot,init_func=self.init_plot,frames=len(self.susceptible)+1,interval=1000*0.1,blit=False)
		plt.show()
			
if '__main__' in __name__:
	env = Environment((100,100),no_symptoms_probability=0.2,central_hub=True,quarantine_rate=0.8)
	env.init_population(100,10)
	env.config_plot()
	env.init_plot()
	env.config_misc(2,7,7)
	env.run_simulation()
