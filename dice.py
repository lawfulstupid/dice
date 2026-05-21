import random
from functools import reduce
from math import ceil, log10

class Die:

	# Creates a Die object from either
	# An integer n -> a standard n-sided die, e.g. d6 = Die(6)
	# A dict -> a die with probability distribution equal to given dict
	# A list -> a die that uniformly picks an item from the list
	def __new__(cls, arg):
		self = super(Die, cls).__new__(cls)

		if isinstance(arg, dict):
			self.pdf = arg
		elif isinstance(arg, Die):
			return arg
		elif isinstance(arg, int):
			return Die(dict.fromkeys(range(1, arg + 1), 1))
		elif isinstance(arg, list):
			return Die(len(arg)).map(lambda n: arg[n-1])
		else:
			raise "unknown pdf type"

		# Make sure PDF is good to use
		if None in self.pdf:
			del self.pdf[None]

		self.totalWeight = sum(self.pdf.values())

		# Flatten PDF if values are dice
		if any(map(lambda val: isinstance(val, Die), self.values())):
			return self.map(lambda x: x)
		else:
			return self

	# A one-sided die that always rolls the given number
	@staticmethod
	def pure(n):
		if n == None:
			return Die({})
		else:
			return Die({n: 1})

	# A die that always rolls a 0
	@staticmethod
	def zero():
		return Die.pure(0)

	@staticmethod
	def wrap(d):
		return d if isinstance(d, Die) else Die.pure(d)

	def __iter__(self):
		return self.pdf.__iter__()

	def __next__(self):
		return self.pdf.__next__()

	# Adds die to itself n times, e.g. Die(6).by(3) = 3d6
	def by(self, n):
		if n == 0:
			return Die.zero()
		else:
			return self + self.by(n-1)

	# Simulates rolling the die
	def roll(self):
		r = random.uniform(0, self.totalWeight)
		s = 0
		for value in self:
			s += self[value]
			if r <= s:
				return value

	# Converts this die to an exploding die (which rerolls and adds to self when it rolls maximum value, recursively)
	def explode(self, limit = 9):
		return self.map(lambda n: Die.pure(n) + (self.explode(limit - 1) if n == self.getMax() and limit > 0 else 0))

	# Get expected value
	def exp(self):
		s = 0
		for value in self:
			s += value * self[value]
		return s

	# Get maximum rollable value
	def getMax(self):
		return max(self.pdf.keys())

	# Get minimum rollable value
	def getMin(self):
		return min(self.pdf.keys())

	# Compute the probability of a given scenario, e.g. Die(6).test(lambda n: n >= 3) = 2/3
	def prob(self, test):
		successes = 0
		failures = 0
		for value in self.pdf:
			result = Die.wrap(test(value))
			successes += self.pdf[value] * result[True]
			failures += self.pdf[value] * result[False]
		return successes / float(successes + failures)

	# Get list of rollable values
	def values(self):
		values = list(self.pdf.keys())
		values.sort()
		return values

	def isTuples(self):
		return isinstance(self.values()[0], tuple)

	# Transform the rollable values, e.g. Die(6).map(lambda n: n * 2)
	def map(self, f, autoUncurry=True):
		if (autoUncurry and self.isTuples()):
			return self.map(uncurry(f), False)
		pdf = {}
		for value in self:
			result = Die.wrap(f(value))
			for newValue in result:
				if (newValue != None):
					pdf[newValue] = pdf.get(newValue, 0) + self[value] * result[newValue]
		return Die(pdf)

	# Accept only values that pass a test e.g. Die(6).filter(lambda n: n >= 3) is equivalent to d4+2
	# Change failValue to a real value to have rejects map to that instead of being removed, e.g. Die(6).filter(lambda n: n >= 5, 0) = Die({ 0: 4, 5: 1, 6: 1})
	def filter(self, test, failValue=None):
		return self.map(lambda x: x if test(x) else failValue)

	# Inverse of above for semantic reasons
	def reroll(self, test):
		return self.filter(lambda x: not(test(x)), None)

	# Generic function to map-reduce two probaility distributions into one
	def __combine(this, that, f):
		pdf = {}
		that = Die.wrap(that)
		for a in this:
			for b in that:
				value = f(a,b)
				pdf[value] = pdf.get(value,0) + this[a]*that[b]
		return Die(pdf)

	# Generic function to cobine rolls with a binary relation
	def __compare(this, that, f):
		return this.__combine(that, lambda a,b: int(f(a,b)))

	# Gets the probability of rolling a particular value
	def __getitem__(self, value):
		return self.pdf.get(value,0) / float(self.totalWeight)

	# Lifts + operator
	def __add__(this, that):
		return this.__combine(that, lambda a,b: a+b)

	# Lifts - operator
	def __sub__(this, that):
		return this.__combine(that, lambda a,b: a-b)

	# Lifts * operator
	def __mul__(this, that):
		return this.__combine(that, lambda a,b: a*b)

	# Overloads / operator to produce floored quotient of two rolls
	def __truediv__(this, that):
		return this // that

	# Lifts // operator
	def __floordiv__(this, that):
		return this.__combine(that, lambda a,b: a // b)

	# Lifts % operator
	def __mod__(this, that):
		return this.__combine(that, lambda a,b: a % b)

	# Lifts ** operator
	def __pow__(this, that):
		return this.__combine(that, lambda a,b: a ** b)

	# Overloads & operator to produce tuple of two rolls
	def __and__(this, that):
		return this.__combine(that, lambda a,b: (*tuplise(a), *tuplise(b)))

	# Overloads | operator to produce max of two rolls
	def __or__(this, that):
		return this.__combine(that, lambda a,b: max(a,b))

	# Lifts == operator
	def __eq__(this, that):
		return this.__compare(that, lambda a,b: a == b)

	# Lifts != operator
	def __ne__(this, that):
		return this.__compare(that, lambda a,b: a != b)

	# Lifts <= operator
	def __le__(this, that):
		return this.__compare(that, lambda a,b: a <= b)

	# Lifts < operator
	def __lt__(this, that):
		return this.__compare(that, lambda a,b: a < b)

	# Lifts >= operator
	def __ge__(this, that):
		return this.__compare(that, lambda a,b: a >= b)

	# Lifts > operator
	def __gt__(this, that):
		return this.__compare(that, lambda a,b: a > b)

	# String representations
	def __repr__(self):
		return reduce(lambda a,b: a + "\n" + b, self.__lines())

	def __str__(self):
		return reduce(lambda a,b: a.strip() + ", " + b.strip(), self.__lines())
	
	# To be usable as dict key
	def __hash__(self):
		return hash(frozenset(self.pdf))

	def __lines(self):
		longestValue = 0
		longestProb = 0
		for value in self:
			longestValue = max(longestValue, len(str(value)))
			longestProb = max(longestProb, 2-ceil(log10(self[value])))
		valueFormat = "{0:>" + str(longestValue) + "s}"
		probFormat = "{1:." + str(longestProb) + "f}"
		format = valueFormat + ": " + probFormat
		return list(map(lambda value: format.format(str(value), self[value]), sorted(self.pdf)))

	# Produce a graph of the probability distribution
	def graph(self, screenWidth=80):
		maxNumWidth = 0
		maxProb = 0
		for n in self:
			maxNumWidth = max(maxNumWidth, len(str(n)))
			maxProb = max(maxProb, self[n])
		for n in self.values():
			print(str(n).rjust(maxNumWidth), end=' | ')
			bar_len = int(round(screenWidth * self[n] / maxProb))
			for i in range(bar_len):
				print('#', end='')
			print()

coin = Die({0: 1, 1: 1})
d2 = Die(2)
d4 = Die(4)
d6 = Die(6)
d8 = Die(8)
d10 = Die(10)
d12 = Die(12)
d20 = Die(20)
d100 = Die(100)
dF = Die({-1: 2, 0: 2, 1: 2}) # FUDGE/FATE dice
fate = dF.by(4) # FATE test roll
char = Die({d4: 4, d6: 3, d8: 2, d10: 1}) # Blood & Sweat characteristic

# Modifies a curried function to accept tuples
def uncurry(f):
	def g(t):
		return f(*t)
	return g

# Packs singleton values into a degenerate tuple
def tuplise(t):
	return t if isinstance(t, tuple) else (t,)

# Utility
class ShowStr:

	def __init__(self, str):
		self.str = str

	def __repr__(self):
		return self.str
