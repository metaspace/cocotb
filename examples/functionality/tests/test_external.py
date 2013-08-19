#!/usr/bin/env python

''' Copyright (c) 2013 Potential Ventures Ltd
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. '''

"""
A set of tests that demonstrate cocotb functionality

Also used a regression test of cocotb capabilities
"""

import threading
import time
import cocotb
from cocotb.result import ReturnValue, TestFailure
from cocotb.triggers import Timer, Join, RisingEdge, ReadOnly, Edge
from cocotb.clock import Clock
from cocotb.decorators import external

test_count = 0
g_dut = None

# Tests relating to calling convention and operation

@cocotb.function
def decorated_test_read(dut, signal):
    global test_count
    dut.log.info("Inside decorated_test_read")
    test_count = 0
    while test_count is not 5:
        yield RisingEdge(dut.clk)
        test_count += 1

    raise ReturnValue(test_count)

def test_read(dut, signal):
    global test_count
    dut.log.info("Inside test_read")
    while test_count is not 5:
        yield RisingEdge(dut.clk)
        test_count += 1

def hal_read(function):
    global g_dut
    global test_count
    test_count = 0
    function(g_dut, g_dut.stream_out_ready)
    g_dut.log.info("Cycles seen is %d" % test_count)

def create_thread(function):
    """ Create a thread to simulate an external calling entity """
    new_thread = threading.Thread(group=None, target=hal_read, name="Test_thread", args=([function]), kwargs={})
    new_thread.start()

@cocotb.coroutine
def clock_gen(clock):
    """Drive the clock signal"""

    for i in range(10000):
        clock <= 0
        yield Timer(100)
        clock <= 1
        yield Timer(100)

    clock.log.warning("Clock generator finished!")

@cocotb.test(expect_fail=False)
def test_callable(dut):
    """Test ability to call a function that will block but allow other coroutines to continue

    Test creates a thread to simulate another context. This thread will then "block" for
    5 clock cycles. 5 cycles should be seen by the thread
    """
    global g_dut
    global test_count
    g_dut = dut
    create_thread(decorated_test_read)
    dut.log.info("Test thread created")
    clk_gen = Clock(dut.clk,  100)
    clk_gen.start()
    yield Timer(10000)
    clk_gen.stop()
    if test_count is not 5:
        raise TestFailure

@cocotb.test(expect_fail=True, skip=True)
def test_callable_fail(dut):
    """Test ability to call a function that will block but allow other coroutines to continue

    Test creates a thread to simulate another context. This thread will then "block" for
    5 clock cycles but not using the function decorator. No cycls should be seen.
    """
    global g_dut
    global test_count
    g_dut = dut
    create_thread(test_read)
    dut.log.info("Test thread created")
    clk_gen = Clock(dut.clk, 100)
    clk_gen.start()
    yield Timer(10000)
    clk_gen.stop()
    if test_count is not 5:
        raise TestFailure

def test_ext_function(dut):
    #dut.log.info("Sleeping")
    return 2

def test_ext_function_return(dut):
    value = dut.clk.value.value
    #dut.log.info("Sleeping and returning %s" % value)
    #time.sleep(0.2)
    return value

@cocotb.coroutine
def clock_monitor(dut):
    count = 0
    while True:
        yield RisingEdge(dut.clk)
        count += 1

@cocotb.test(expect_fail=False)
def test_ext_call_return(dut):
    """Test ability to yeild on an external non cocotb coroutine decorated function"""
    mon = cocotb.scheduler.queue(clock_monitor(dut))
    clk_gen = Clock(dut.clk, 100)
    clk_gen.start()
    value = yield external(test_ext_function)(dut)
    clk_gen.stop()
    dut.log.info("Value was %d" % value)

@cocotb.test(expect_fail=False)
def test_ext_call_nreturn(dut):
    """Test ability to yeild on an external non cocotb coroutine decorated function"""
    mon = cocotb.scheduler.queue(clock_monitor(dut))
    clk_gen = Clock(dut.clk, 100)
    clk_gen.start()
    yield external(test_ext_function)(dut)
    clk_gen.stop()

@cocotb.test(expect_fail=False)
def test_multiple_externals(dut):
    clk_gen = Clock(dut.clk, 100)
    clk_gen.start()
    yield external(test_ext_function)(dut)
    dut.log.info("First one completed")
    yield external(test_ext_function)(dut)
    dut.log.info("Second one completed")

@cocotb.test(expect_fail=True)
def ztest_ext_exit_error(dut):
    """Test that a premature exit of the sim at it's request still results in the
    clean close down of the sim world"""
    yield external(test_ext_function_return)(dut)
    yield Timer(100)
