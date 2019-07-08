"""
This is an experimental module.
Everything in this module is untested and probably incorrect.
Don't use them.

This is intended to be a place to develop new functions instead of
having an entirely new branch
"""
import pandas as pd 
import numpy as np
from numba import jit, njit
from intake.source.base import DataSource, Schema

@jit
def v_cusum(array):
	"""
	Calcuate cusum - numba version
	array
		numpy array
	returns
		pos and neg arrays
	""" 
	L = len(array)
	pos = [0]
	neg = [0]
	pos_val = 0
	neg_val = 0
	d = np.diff(array)[1:]
	for i in d:
		if i >= 0:
			pos_val += i
		else:
			neg_val += i
		pos.append(pos_val)
		neg.append(neg_val)
	return (pos, neg)

@jit
def sign_change(array):
	"""
	Calcuate the sign change in an array
	If the current value is positive and previous value negative, mark as 1.
	If the current value is negative and previous value positive, mark as -1.
	In case of no change in sign, mark as 0
	"""
	L = len(array)
	arr = np.empty(L)
	arr[0] = 0
	for i in range(1, L):
		# TO DO: Condition not handling edge case
		if (array[i] >= 0) & (array[i-1] < 0):
			arr[i] = 1
		elif (array[i] <= 0) & (array[i-1] > 0):
			arr[i] = -1
		else:
			arr[i] = 0
	return arr


def cusum(array):
	"""
	Calcuate cusum
	array
		a pandas series with a timestamp or datetime index
	The cusum is just an aggregate of positive and negative differences
	returns
		pandas dataframe with positive and negative cumulatives,
		ratio, differences, regime change along with the original index
	"""
	pos = [0]
	neg = [0]
	pos_val = 0
	neg_val = 0
	d = array.diff()[1:]
	for i in d:
		if i >= 0:
			pos_val += i
		else:
			neg_val += i
		pos.append(pos_val)
		neg.append(neg_val)
	df = pd.DataFrame({'pos': pos, 'neg': neg}, index=array.index)
	df['neg'] = df['neg'].abs()
	df['d'] = df['pos'] - df['neg']
	df['reg'] = sign_change(df.d.values)
	df['ratio'] = df['pos'] / df['neg']
	return df

def percentage_bar(data, step):
	"""
	Generate the number of timesteps taken for each
	equivalent step in price
	data
		numpy 1d array
	step
		step size
	"""
	start = data[0]
	nextStep = start + step
	counter = 0
	steps = [start]
	period = [0]
	for d in data:
		if step >= 0:
			if d > nextStep:
				steps.append(nextStep)
				period.append(counter)
				nextStep += step
				counter = 0
			else:
				counter+=1
		elif step < 0:
			if d < nextStep:
				steps.append(nextStep)
				period.append(counter)
				nextStep += step
				counter = 0
			else:
				counter+=1

	# Final loop exit			
	steps.append(nextStep)
	period.append(counter)
	return (steps, period)		

def high_breach(s):
	"""
	Given a series of values, returns a series
	with consecutive highs as values and timestamp as index
	s
		series with timestamp as index
	"""
	highs = []
	ts = []
	max_val = 0
	index = s.index.values
	for i,v in enumerate(s.values):
		if v > max_val:
			highs.append(v)
			ts.append(index[i])
			max_val = v
	return pd.Series(highs, index=ts)


def low_breach(s):
	"""
	Given a series of values, returns a series
	with consecutive lows as values and timestamp as index
	s
		series with timestamp as index
	"""
	lows = []
	ts = []
	min_val = 1e+9 # Just setting an extreme value
	index = s.index.values
	for i,v in enumerate(s.values):
		if v < min_val:
			lows.append(v)
			ts.append(index[i])
			min_val = v
	return pd.Series(lows, index=ts)



class ExcelSource(DataSource):

	container = 'dataframe'
	name = 'universe'
	version = '0.0.1'
	partition_access = True

	def __init__(self, filename, metadata=None):
		"""
		Initialize with filename and metadata
		"""
		self.filename = filename
		self._source = pd.ExcelFile(self.filename)
		super(ExcelSource, self).__init__(metadata=metadata)

	def _get_schema(self):
		sheets = self._source.sheet_names
		return Schema(
			datashape=None,
			dtype=None,
			shape=None,
			npartitions= len(sheets),
			extra_metadata = {'sheets': sheets}
			)

	def read_partition(self, sheet, **kwargs):
		"""
		Read a specific sheet from the list of sheets
		sheet
			sheet to read
		kwargs
			kwargs to the excel parse function
		"""
		self._load_metadata()
		if sheet in self.metadata.get('sheets', []):
			return self._source.parse(sheet, **kwargs)
		else:
			return 'No such sheet in the Excel File'

	def read(self, **kwargs):
		"""
		Read all sheets into a single dataframe.
		Sheetname is added as a column
		kwargs
			kwargs to the excel parse function
		"""
		self._load_metadata()
		sheets = self.metadata.get('sheets')
		collect = []
		if len(sheets) > 1:
			for sheet in sheets:
				temp = self.read_partition(sheet, **kwargs)
				temp['sheetname'] = sheet
				collect.append(temp)
		return pd.concat(collect, sort=False)

	def _close(self):
		self._source.close()



