<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

This project consists of a PWM peripheral controlled via SPI. The design operates at 10 MHz, with ~100kHz SPI communication to configure registers controlling output enables, PWM enables, and duty cycles. There are two main modules: an SPI Peripheral to manage registers, and PWM Peripheral to generate signals.
There are 16 output bits, with corresponding 16 output registers and 16 PWM registers that work to individually apply PWM to each output bit.

## How to test

Explain how to use your project
To be filled.

## External hardware

List external hardware used in your project (e.g. PMOD, LED display, etc), if any
Tentatively, no external hardware is used.
