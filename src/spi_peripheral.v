`default_nettype none

module spi_peripheral (
    input  wire       clk,       // internal clock
    input  wire       rst_n,     // reset_n - low to reset

    input  wire       sclk,      // ui_in[0] serial clock 
    input  wire       ncs,      // ui_in[1] chip select/slave select (active low)
    input  wire       copi,      // ui_in[2] controller out peripheral in (aka MOSI/SDI), serial data from controller
    // can omit cipo in this project
    /* Register outputs to pwm_peripheral */
    output reg  [7:0] en_reg_out_7_0,
    output reg  [7:0] en_reg_out_15_8,
    output reg  [7:0] en_reg_pwm_7_0,
    output reg  [7:0] en_reg_pwm_15_8,
    output reg  [7:0] pwm_duty_cycle
);

/*
Mode 0: Data sampled on rising edge of SCLK, shifted out on falling edge
No CIPO: Read ops ignored, ONLY write ops are supported
Clock Domain Corssing (CDC): Synchronized using 2-stage flip-flop chain to prevent metastability
Fixed Transaction Length: 16 clk cycles/transaction (1 R(0)/W(1) bit [15], 7 address bits [14:8], 8 data bits [7:0])
- Only commit write if exactly 16 SCLK rising edges seen during low nCS, apply when nCS rises

For synchronizers, N=2 in this design. Samples stored are N+1 for sclk, N for ncs and copi
*/

    localparam max_address = 7'h04; // Not too necessary here, but adds a safety check for addr range. Sized to 7bits to match address size

    /*
    Synchronizers with N=2 (2 flip flops), +1 for sclk edge detection
    */
    reg [2:0] sclk_sync;
    reg [1:0] copi_sync, ncs_sync;
 
    // System clock domain synchronizers
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sclk_sync <= 3'b000;
            ncs_sync  <= 2'b11;     // starts high because nCS is active low
            copi_sync <= 2'b00;
        end else begin
            // Shift in new samples, move old samples to higher bits
            sclk_sync <= {sclk_sync[1:0], sclk};    // bit 3 is an extra copy for edge detection
            ncs_sync  <= {ncs_sync[0], ncs};
            copi_sync <= {copi_sync[0], copi};
        end
    end
    
    // Using the older values in buffer to resolve unstable states
    wire sclk_rise = (sclk_sync[2:1] == 2'b01);  // old bit 0, new 1 indicates rising edge
    wire active    = ~ncs_sync[1];               // active low nCS means active transaction  
    wire copi_s    = copi_sync[1];               // use [1] to align timing with sclk
 
    /*
    Shift register to collect COPI data in 16 bits, MSB first
    Bit counter that saturates at 16 to detect a completed transaction
    */
    reg [15:0] shift;
    reg [4:0]  bit_cnt;                          // counts from 0-16
 
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            shift   <= 16'h0000;
            bit_cnt <= 5'd0;
        end else if (!active) begin
            bit_cnt <= 5'd0;    // reset counter when transaction is inactive
        end else if (sclk_rise && bit_cnt != 5'd16) begin
            // Aligned with SPI clock posedges to shift in data
            shift   <= {shift[14:0], copi_s};
            bit_cnt <= bit_cnt + 5'd1;
        end
        // No action if counter is already 16, wait til nCS goes low
    end
 
    /*
    Writes to registers once 16 bits are captured and nCS goes high (transaction complete)
    */
    // As only writes (shift[15] == 1) do anything, we can just check if it's high
    wire       wr_done = (bit_cnt == 5'd16) && shift[15];
    wire [6:0] addr  = shift[14:8];     // 7-bit address, but we only use 5 registers (0-4)
    wire [7:0] data  = shift[7:0];      // 8-bit data to write to register
 
    wire       valid_addr = (addr <= max_address); // Check if address is within range

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            en_reg_out_7_0  <= 8'h00;
            en_reg_out_15_8 <= 8'h00;
            en_reg_pwm_7_0  <= 8'h00;
            en_reg_pwm_15_8 <= 8'h00;
            pwm_duty_cycle  <= 8'h00;
        end else if (!active && wr_done && valid_addr) begin // Inactive means nCS is high, so commit the write
            case (addr)
                7'h00:   en_reg_out_7_0  <= data;
                7'h01:   en_reg_out_15_8 <= data;
                7'h02:   en_reg_pwm_7_0  <= data;
                7'h03:   en_reg_pwm_15_8 <= data;
                7'h04:   pwm_duty_cycle  <= data;
                default: ;                       // No-op on invalid address
            endcase
        end
    end
 

endmodule