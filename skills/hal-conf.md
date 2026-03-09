---
name: hal-conf
description: 负责启用 HAL 模块、生成 HAL 配置摘要，并整理中间件/驱动依赖关系。
keywords: hal,库,驱动,模块,初始化,msp,中断,dma
always_on: true
---
你需要把用户需求映射成 HAL 层启用建议。

规则：
1. 说明应启用哪些 HAL 模块，例如 GPIO、RCC、UART、I2C、SPI、ADC、TIM。
2. 生成的头文件中需要有面向应用层的配置摘要。
3. 生成的源文件中需要有结构化注释或常量定义，帮助开发者继续补充 CubeMX 代码。
