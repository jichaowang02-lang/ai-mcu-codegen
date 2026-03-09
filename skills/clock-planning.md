---
name: clock-planning
description: 负责推导 STM32 的时钟树、PLL、HCLK、PCLK 与外部晶振假设。
keywords: 时钟,频率,pll,sysclk,hclk,pclk,晶振,外部时钟,rcc
always_on: false
---
你需要根据用户需求补全 RCC 和时钟配置建议。

规则：
1. 优先保证配置是可解释的，而不是假装完全准确。
2. 如果用户没有提供外部晶振频率，请显式写入 assumptions。
3. 如果 SYSCLK / AHB / APB 分频需要假设，要把计算逻辑体现在说明文档里。
4. `.ioc` 中至少补充 RCC、时钟源、PLL 倍频或分频相关键值草稿。
