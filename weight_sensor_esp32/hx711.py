"""
HX711 Load Cell Amplifier Library for MicroPython
Compatible with ESP32, RP2040 and other MicroPython boards
"""

import time
from machine import Pin

class HX711:
    def __init__(self, d_out, pd_sck, gain=128):
        self.pd_sck = Pin(pd_sck, Pin.OUT)
        self.d_out = Pin(d_out, Pin.IN)
        
        self.gain = gain
        self.GAIN = 0
        self.REFERENCE_UNIT = 1  # The reference unit for weight
        self.OFFSET = 1
        self.lastVal = 0
        
        self.pd_sck.value(False)
        self.read()
        
        if gain == 128:
            self.GAIN = 1
        elif gain == 64:
            self.GAIN = 3
        elif gain == 32:
            self.GAIN = 2

        self.read()
        
    def is_ready(self):
        return self.d_out.value() == 0
    
    def wait_ready(self, delay_ms=0):
        # Wait for the device to become ready
        while not self.is_ready():
            time.sleep_ms(delay_ms)
            
    def read_raw_data(self):
        # Wait for and read data from hx711
        self.wait_ready()
        
        # Read 24 bits of data
        value = 0
        for i in range(24):
            self.pd_sck.value(True)
            value = value << 1
            self.pd_sck.value(False)
            if self.d_out.value():
                value += 1
                
        # Set gain for next reading
        for i in range(self.GAIN):
            self.pd_sck.value(True)
            self.pd_sck.value(False)
            
        # Convert to signed 24-bit value
        if value & 0x800000:
            value -= 0x1000000
            
        return value
    
    def read(self):
        return self.read_raw_data()
        
    def read_average(self, times=16):
        # Read multiple times and return average
        sum_val = 0
        for i in range(times):
            sum_val += self.read()
        return sum_val / times
    
    def get_value(self, times=16):
        return self.read_average(times) - self.OFFSET
        
    def get_weight(self, times=16):
        value = self.get_value(times)
        return value / self.REFERENCE_UNIT
    
    def tare(self, times=16):
        # Set the OFFSET value for tare weight
        sum_val = self.read_average(times)
        self.set_offset(sum_val)
        
    def set_offset(self, offset):
        self.OFFSET = offset
        
    def get_offset(self):
        return self.OFFSET
        
    def set_reference_unit(self, reference_unit):
        self.REFERENCE_UNIT = reference_unit
        
    def get_reference_unit(self):
        return self.REFERENCE_UNIT
        
    def power_down(self):
        # Put the ADC in sleep mode
        self.pd_sck.value(False)
        self.pd_sck.value(True)
        time.sleep_ms(1)
        
    def power_up(self):
        # Wake up the ADC
        self.pd_sck.value(False)
        time.sleep_ms(1)
        
    def reset(self):
        # Reset the chip
        self.power_down()
        self.power_up()
