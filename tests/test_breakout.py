import pytest
import pendulum
import random
from fastbt.models.breakout import Breakout, StockData, HighLow
from pydantic import ValidationError

@pytest.fixture
def base_breakout():
    return Breakout(symbols=['GOOG','AAPL'],
             instrument_map={'GOOG':1010,'AAPL':2100})
    
@pytest.fixture
def sl_breakout():
    ts = Breakout(symbols=['GOOG','AAPL','INTL'],
            instrument_map={'GOOG':1010,'AAPL':2100, 'INTL':3000})
    ts.update_high_low([
            HighLow(symbol='AAPL', high=101, low=98),
            HighLow(symbol='GOOG', high=104, low=100),
            HighLow(symbol='INTL', high=302, low=295),
            ])
    ts._data['AAPL'].ltp = 100
    ts._data['GOOG'].ltp = 104
    ts._data['INTL'].ltp = 300
    return ts

def test_breakout_parent_defaults(base_breakout):
    ts = base_breakout
    assert ts.SYSTEM_START_TIME == pendulum.today(tz='Asia/Kolkata').add(hours=9,minutes=15)
    assert ts.SYSTEM_END_TIME == pendulum.today(tz='Asia/Kolkata').add(hours=15,minutes=15)
    assert ts.env == 'paper'
    assert ts.done is False

def test_stock_data(base_breakout):
    ts = base_breakout
    assert len(ts.data) == 2
    my_data = { 
            'GOOG': StockData(name='GOOG', token=1010),
            'AAPL': StockData(name='AAPL', token=2100)
            }
    assert ts.data == my_data
    assert ts.data['GOOG'].high is None
    assert ts.data['AAPL'].low is None


def test_rev_map(base_breakout):
    ts = base_breakout
    assert ts._rev_map == {1010: 'GOOG', 2100: 'AAPL'} 
    

def test_high_low(base_breakout):
    ts = base_breakout
    ts.update_high_low([
            HighLow(symbol='AAPL', high=150, low=120),
            HighLow(symbol='GOOG', high=150, low=120), 
            ])
    assert ts.data['AAPL'].high == 150
    assert ts.data['GOOG'].low == 120 

def test_high_low_dict(base_breakout):
    ts = base_breakout
    ts.update_high_low([
        {'symbol': 'AAPL', 'high': 150, 'low':120}
        ])
    assert ts.data['AAPL'].high == 150
    
def test_high_low_dict_extra_values(base_breakout):
    ts = base_breakout
    ts.update_high_low([
        {'symbol': 'AAPL', 'high': 150, 'low':120, 'open': 160}
        ])
    assert ts.data['AAPL'].high == 150
    
def test_high_low_dict_no_symbols(base_breakout):
    ts = base_breakout
    ts.update_high_low([
        {'symbol': 'DOW', 'high': 150, 'low':120, 'open': 160} ])
    assert ts.data['AAPL'].high is None
    assert ts.data['GOOG'].low is None

def test_high_low_no_data_raise_error(base_breakout):
    ts = base_breakout
    with pytest.raises(ValidationError):
        ts.update_high_low([
            {'symbol': 'AAPL', 'high':15}
            ])

def test_stop_loss_default(sl_breakout):
    ts = sl_breakout
    sl = ts.stop_loss('AAPL','BUY')
    assert sl == 98
    sl = ts.stop_loss('INTL', 'SELL')
    assert sl == 302 

def test_stop_loss_value(sl_breakout):
    ts = sl_breakout
    sl = ts.stop_loss('AAPL','BUY')
    assert sl == 98
    sl = ts.stop_loss('AAPL','BUY', method='value')
    assert sl == 100
    sl = ts.stop_loss('AAPL','BUY', method='value', stop=1)
    assert sl == 99 
    sl = ts.stop_loss('GOOG','SELL', method='value', stop=1)
    assert sl == 105 

def test_stop_loss_percentage(sl_breakout):
    ts = sl_breakout
    sl = ts.stop_loss('AAPL','BUY')
    assert sl == 98
    sl = ts.stop_loss('AAPL','BUY', method='percent')
    assert sl == 100
    sl = ts.stop_loss('AAPL','BUY', method='percent', stop=1.5)
    assert sl == 98.5 
    sl = ts.stop_loss('INTL','SELL', method='percent', stop=3)
    assert sl == 309 
    
def test_stop_loss_no_symbol(sl_breakout):
    ts = sl_breakout
    sl = ts.stop_loss('SOME', 'BUY')
    assert sl == 0

def test_stop_loss_unknown_mode(sl_breakout):
    ts = sl_breakout
    sl = ts.stop_loss('AAPL','BUY', method='unknown')
    assert sl == 98
       