---
name: peripheral-mapping
description: 负责分析 UART、I2C、SPI、ADC、PWM、GPIO 等外设需求，并给出引脚复用草稿。
keywords: 串口,uart,usart,i2c,spi,adc,pwm,gpio,定时器,timer,can,usb,引脚,外设
always_on: false
---
你需要根据用户需求生成外设启用方案和引脚映射草稿。

规则：
1. 如果用户没指定具体引脚，请选择常见默认映射，并在 warnings 中要求用户复核。
2. `.ioc` 中要体现 GPIO 模式、外设实例、NVIC 或 DMA 的基本意图。
3. 头文件和源文件里要把关键外设初始化参数汇总成便于阅读的宏或结构体。
