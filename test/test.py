# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import ClockCycles
from cocotb.types import Logic
from cocotb.types import LogicArray

async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")

"""
Scenarios to Test for PWM (from section 2):
        Duty cycle sweep (0x00 to 0xFF).
        Interaction between Output Enable and PWM Enable registers.
        Frequency verification (~3 kHz +/- 1%).
        PWM Duty verification (+/-1%).
"""

@cocotb.test()
async def test_pwm_freq(dut):
    # Write your test here
    """
    Measure the time between two rising edges of the PWM signal (period = t_rising_edge2 - t_rising_edge1).
    Frequency = 1 / period
    Verify 10% tolerances (2970-3030 Hz)
    """
    
    dut._log.info("Start PWM Frequency test")
    
    # Clock and reset from test_spi (10MHz), 100ns period
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())
    
    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)
    
    # Enable all outputs with PWM at 50% duty
    for addr, data in ((0x00, 0xFF), (0x01, 0xFF), (0x02, 0xFF), (0x03, 0xFF), (0x04, 0x80)):
        dut._log.info(f"Write transaction, address {addr:#04x}, data {data:#04x}")
        await send_spi_transaction(dut, 1, addr, data)
    
    # Measure time between two posedges (1 clk cycle = 100 ns)
    # Check both uo_out[0] and uio_out[0] for PWM signal (not doing every single bit, that's overkill)
    for name, output in (("uo_out[0]", dut.uo_out), ("uio_out[0]", dut.uio_out)):
        rising = []
        prev = int(output.value) & 1
        for cycle in range(8000):               # a bit more than 2 PWM periods
            await ClockCycles(dut.clk, 1)
            cur = int(output.value) & 1
            # Detect and track rising edges (new signal cur = 1, prev = 0)
            if cur and not prev:
                rising.append(cycle)
            prev = cur
            # Only need two rising edges for period
            if len(rising) == 2:
                break
        assert len(rising) == 2, f"{name}: expected 2 rising edges, saw {len(rising)}"
 
        period_ns = (rising[1] - rising[0]) * 100
        freq = 1e9 / period_ns
        dut._log.info(f"{name}: period = {period_ns} ns, frequency = {freq:.1f} Hz")
        assert 2970 <= freq <= 3030, f"{name}: {freq:.1f} Hz is outside permissible range of 2970-3030 Hz"
    
    dut._log.info("PWM Frequency test completed successfully")


@cocotb.test()
async def test_pwm_duty(dut):
    # Write your test here
    """
    Measure the time the signal is high (high_time = t_falling_edge - t_rising_edge).
    Duty Cycle = (high_time / period) * 100%
    Test 0%, 50%, and 100% duty cycles
    Ensure tolerance is +-1% of expected duty cycle
    """
    
    dut._log.info("Start PWM duty cycle test")
 
    # Clock and reset from test_spi (10MHz), 100ns period
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())
 
    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)
 
    # Count high cycles over one PWM period, which is (12+1)*256 clk cycles
    # 12+1 is from clk_div_trig (0->12 inclusive), and 256 is from pwm_counter, both in pwm_peripheral.v 
    # Whole number of periods means duty = high_cycles / window, no edge detection needed.
    WINDOW = 13 * 256
 
    # First test: Duty sweep, enable all outputs with PWM
    for addr, data in ((0x00, 0xFF), (0x01, 0xFF), (0x02, 0xFF), (0x03, 0xFF)):
        dut._log.info(f"Write transaction, address {addr:#04x}, data {data:#04x}")
        await send_spi_transaction(dut, 1, addr, data)
 
    # Sweep duty cycle through 0x00, 0x80, and 0xFF (0%, 50%, 100%)
    # 100% is main edge case as normal calculation would be 255/256 = 99.6%, but we treat it as 100%
    duties = [0x00, 0x80, 0xFF]   # 0%, 50%, 100%
    for duty in duties:
        dut._log.info(f"Write transaction, address 0x04, data {duty:#04x}")
        await send_spi_transaction(dut, 1, 0x04, duty)

        # Track high bits for each individual output bit over the window period
        highs = [0] * 16                        
        # bits 0-7 = uo_out, 8-15 = uio_out
        for _ in range(WINDOW):
            await ClockCycles(dut.clk, 1)
            out = (int(dut.uio_out.value) << 8) | int(dut.uo_out.value)
            for b in range(16):
                # b corresponds to output bit, shift masks the other bits, &1 counts and adds if the bit is high
                highs[b] += (out >> b) & 1
 
        # Edge case for duty = 255 which is 100% duty, otherwise calc expected duty as a percentage
        expected = 100.0 if duty == 255 else 100.0 * duty / 256
        for b in range(16):
            measured = 100.0 * highs[b] / WINDOW
            # assertion to check measured duty is within 1% tolerance of expected
            assert abs(measured - expected) <= 1.0, f"duty {duty:#04x}, bit {b}: measured {measured:.2f}%, expected {expected:.2f}%"
        dut._log.info(f"duty {duty:#04x}: all bits ~{expected:.2f}%, tolerance OK")
 
    # Unsure if second test is necessary per section 7 checklist, but it's mentioned in section 2 so keeping for completeness
    # Second test: output enable vs PWM enable (50% duty = 0x80) 
    #   out_en = 0          -> constant 0 (overrides PWM)
    #   out_en = 1, pwm = 0 -> constant 1
    #   out_en = 1, pwm = 1 -> PWM, ~50%
    en_out = 0x3C3C   # Enable range of bits 2-5, 10-13
    en_pwm = 0x0FF0   # Enable PWM bits 4-11 (overlaps en_out on 4,5,10,11; pwm-only on 6-9 (should be 0))
    for addr, data in ((0x00, en_out & 0xFF), (0x01, en_out >> 8),
                       (0x02, en_pwm & 0xFF), (0x03, en_pwm >> 8),
                       (0x04, 0x80)):
        dut._log.info(f"Write transaction, address {addr:#04x}, data {data:#04x}")
        await send_spi_transaction(dut, 1, addr, data)
 
    # Same method as above to count high bits over window period per output bit
    highs = [0] * 16
    for _ in range(WINDOW):
        await ClockCycles(dut.clk, 1)
        out = (int(dut.uio_out.value) << 8) | int(dut.uo_out.value)
        for b in range(16):
            highs[b] += (out >> b) & 1
 
    for b in range(16):
        out_en = (en_out >> b) & 1
        pwm_en = (en_pwm >> b) & 1
        measured = 100.0 * highs[b] / WINDOW
        if not out_en: # should always be 0 when disabled
            assert highs[b] == 0, f"bit {b}: output disabled but was high {measured:.2f}% of the time"
        elif not pwm_en: # should always be high when PWM disabled
            assert highs[b] == WINDOW, f"bit {b}: output enabled, PWM disabled, but high only {measured:.2f}%"
        else: # if both enabled, ensure it fits 50% duty within tolerance
            assert abs(measured - 50.0) <= 1.0, f"bit {b}: PWM duty {measured:.2f}%, expected ~50%"
        dut._log.info(f"bit {b}: out_en={out_en} pwm_en={pwm_en}, high {measured:.2f}% OK")
    
    dut._log.info("PWM Duty Cycle test completed successfully")
