<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

This project consists of a PWM peripheral controlled via SPI. The design operates at 10 MHz, with ~100kHz SPI communication to configure registers controlling output enables, PWM enables, and duty cycles. 
There are two main modules: an SPI Peripheral to manage registers, and PWM Peripheral to generate signals.
There are 16 output bits, with 5 control registers that enable the standard/PWM outputs per bit (0x00-0x03) and determine duty cycle (0x04).

## How to test

Testbenches are provided for SPI and PWM modules (PWM WIP).

## External hardware

No external hardware is used in this project.
