`default_nettype none

module spi_peripheral (
    input  wire       clk,      // clock
    input  wire       rst_n,     // reset_n - low to reset
    input  wire [7:0] a
    input  wire [7:0] b,
    output reg [15:0] out
);

    always @(posedge clk or negedge rst_n) begin
    end

endmodule