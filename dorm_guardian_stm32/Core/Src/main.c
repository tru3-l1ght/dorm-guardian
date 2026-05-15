/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Dorm Guardian sensor-only firmware
  ******************************************************************************
  */
/* USER CODE END Header */

#include "main.h"
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

/* Private variables ---------------------------------------------------------*/
I2C_HandleTypeDef hi2c1;
UART_HandleTypeDef huart2;

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_I2C1_Init(void);
static void MX_USART2_UART_Init(void);

/* USER CODE BEGIN 0 */

#define DEVICE_ID "nucleo-f103rb-01"

#define ADDR8(x) ((x) << 1)

/* BH1750 */
#define BH1750_ADDR_7BIT      0x23
#define BH1750_ADDR           ADDR8(BH1750_ADDR_7BIT)
#define BH1750_POWER_ON       0x01
#define BH1750_RESET          0x07
#define BH1750_CONT_H_RES     0x10

/* BME280 */
#define BME_ADDR_76_7BIT      0x76
#define BME_ADDR_77_7BIT      0x77

#define BME_REG_ID            0xD0
#define BME_REG_CTRL_HUM      0xF2
#define BME_REG_CTRL_MEAS     0xF4
#define BME_REG_CONFIG        0xF5
#define BME_REG_PRESS_MSB     0xF7
#define BME_REG_CALIB_00      0x88
#define BME_REG_CALIB_26      0xE1

#define BME280_CHIP_ID        0x60
#define BMP280_CHIP_ID        0x58

typedef struct
{
  uint16_t dig_T1;
  int16_t  dig_T2;
  int16_t  dig_T3;

  uint16_t dig_P1;
  int16_t  dig_P2;
  int16_t  dig_P3;
  int16_t  dig_P4;
  int16_t  dig_P5;
  int16_t  dig_P6;
  int16_t  dig_P7;
  int16_t  dig_P8;
  int16_t  dig_P9;

  uint8_t  dig_H1;
  int16_t  dig_H2;
  uint8_t  dig_H3;
  int16_t  dig_H4;
  int16_t  dig_H5;
  int8_t   dig_H6;
} BME_CalibData;

static BME_CalibData bme_calib;
static int32_t t_fine = 0;

static bool bh1750_ok = false;
static bool bme_ok = false;
static bool has_humidity = false;

static uint8_t bme_addr_7bit = 0;
static uint8_t bme_chip_id = 0;

/* ---------- UART ---------- */

void uart_print(const char *msg)
{
  HAL_UART_Transmit(&huart2, (uint8_t *)msg, strlen(msg), HAL_MAX_DELAY);
}

/* ---------- Helpers ---------- */

static uint16_t u16_le(uint8_t lsb, uint8_t msb)
{
  return (uint16_t)(((uint16_t)msb << 8) | lsb);
}

static int16_t s16_le(uint8_t lsb, uint8_t msb)
{
  return (int16_t)(((uint16_t)msb << 8) | lsb);
}

void format_signed_centi(char *buffer, size_t size, int32_t value)
{
  int32_t whole = value / 100;
  int32_t frac = value % 100;

  if (frac < 0)
  {
    frac = -frac;
  }

  snprintf(buffer, size, "%ld.%02ld", (long)whole, (long)frac);
}

void format_unsigned_centi(char *buffer, size_t size, uint32_t value)
{
  uint32_t whole = value / 100;
  uint32_t frac = value % 100;

  snprintf(buffer, size, "%lu.%02lu", (unsigned long)whole, (unsigned long)frac);
}

/* ---------- I2C Scanner ---------- */

void i2c_scan(void)
{
  char msg[96];
  int found = 0;

  uart_print("\r\n==============================\r\n");
  uart_print("I2C scan starting...\r\n");

  for (uint8_t address = 1; address < 128; address++)
  {
    if (HAL_I2C_IsDeviceReady(&hi2c1, ADDR8(address), 2, 20) == HAL_OK)
    {
      snprintf(msg, sizeof(msg), "Found device at 0x%02X\r\n", address);
      uart_print(msg);
      found++;
    }
  }

  snprintf(msg, sizeof(msg), "I2C scan done. Devices found: %d\r\n", found);
  uart_print(msg);

  uart_print("Expected:\r\n");
  uart_print("BH1750      -> 0x23\r\n");
  uart_print("BME/BMP280  -> 0x76 or 0x77\r\n");
  uart_print("==============================\r\n");
}

/* ---------- BH1750 ---------- */

HAL_StatusTypeDef bh1750_init(void)
{
  uint8_t cmd;

  cmd = BH1750_POWER_ON;
  if (HAL_I2C_Master_Transmit(&hi2c1, BH1750_ADDR, &cmd, 1, 500) != HAL_OK)
  {
    uart_print("ERROR: BH1750 POWER_ON failed.\r\n");
    return HAL_ERROR;
  }

  HAL_Delay(20);

  cmd = BH1750_RESET;
  if (HAL_I2C_Master_Transmit(&hi2c1, BH1750_ADDR, &cmd, 1, 500) != HAL_OK)
  {
    uart_print("ERROR: BH1750 RESET failed.\r\n");
    return HAL_ERROR;
  }

  HAL_Delay(20);

  cmd = BH1750_CONT_H_RES;
  if (HAL_I2C_Master_Transmit(&hi2c1, BH1750_ADDR, &cmd, 1, 500) != HAL_OK)
  {
    uart_print("ERROR: BH1750 continuous mode failed.\r\n");
    return HAL_ERROR;
  }

  HAL_Delay(250);

  bh1750_ok = true;
  uart_print("BH1750 initialized.\r\n");

  return HAL_OK;
}

HAL_StatusTypeDef bh1750_read_lux_centi(uint32_t *lux_centi)
{
  uint8_t data[2];

  if (!bh1750_ok)
  {
    return HAL_ERROR;
  }

  for (int attempt = 0; attempt < 3; attempt++)
  {
    HAL_StatusTypeDef status = HAL_I2C_Master_Receive(&hi2c1, BH1750_ADDR, data, 2, 500);

    if (status == HAL_OK)
    {
      uint16_t raw = ((uint16_t)data[0] << 8) | data[1];

      if (raw == 0xFFFF)
      {
        HAL_Delay(50);
        continue;
      }

      *lux_centi = ((uint32_t)raw * 500U) / 6U;
      return HAL_OK;
    }

    HAL_Delay(50);
  }

  bh1750_init();

  return HAL_ERROR;
}

/* ---------- BME/BMP280 ---------- */

HAL_StatusTypeDef bme_read_calibration(void)
{
  uint8_t c1[26];

  if (HAL_I2C_Mem_Read(&hi2c1, ADDR8(bme_addr_7bit), BME_REG_CALIB_00,
                       I2C_MEMADD_SIZE_8BIT, c1, 26, 500) != HAL_OK)
  {
    return HAL_ERROR;
  }

  bme_calib.dig_T1 = u16_le(c1[0], c1[1]);
  bme_calib.dig_T2 = s16_le(c1[2], c1[3]);
  bme_calib.dig_T3 = s16_le(c1[4], c1[5]);

  bme_calib.dig_P1 = u16_le(c1[6], c1[7]);
  bme_calib.dig_P2 = s16_le(c1[8], c1[9]);
  bme_calib.dig_P3 = s16_le(c1[10], c1[11]);
  bme_calib.dig_P4 = s16_le(c1[12], c1[13]);
  bme_calib.dig_P5 = s16_le(c1[14], c1[15]);
  bme_calib.dig_P6 = s16_le(c1[16], c1[17]);
  bme_calib.dig_P7 = s16_le(c1[18], c1[19]);
  bme_calib.dig_P8 = s16_le(c1[20], c1[21]);
  bme_calib.dig_P9 = s16_le(c1[22], c1[23]);

  bme_calib.dig_H1 = c1[25];

  if (has_humidity)
  {
    uint8_t c2[7];

    if (HAL_I2C_Mem_Read(&hi2c1, ADDR8(bme_addr_7bit), BME_REG_CALIB_26,
                         I2C_MEMADD_SIZE_8BIT, c2, 7, 500) != HAL_OK)
    {
      return HAL_ERROR;
    }

    bme_calib.dig_H2 = s16_le(c2[0], c2[1]);
    bme_calib.dig_H3 = c2[2];
    bme_calib.dig_H4 = (int16_t)(((int16_t)c2[3] << 4) | (c2[4] & 0x0F));
    bme_calib.dig_H5 = (int16_t)(((int16_t)c2[5] << 4) | (c2[4] >> 4));
    bme_calib.dig_H6 = (int8_t)c2[6];
  }

  return HAL_OK;
}

HAL_StatusTypeDef bme_try_address(uint8_t addr_7bit)
{
  uint8_t chip_id = 0;
  char msg[128];

  if (HAL_I2C_IsDeviceReady(&hi2c1, ADDR8(addr_7bit), 2, 100) != HAL_OK)
  {
    return HAL_ERROR;
  }

  if (HAL_I2C_Mem_Read(&hi2c1, ADDR8(addr_7bit), BME_REG_ID,
                       I2C_MEMADD_SIZE_8BIT, &chip_id, 1, 500) != HAL_OK)
  {
    snprintf(msg, sizeof(msg), "Device 0x%02X present, but chip ID read failed.\r\n", addr_7bit);
    uart_print(msg);
    return HAL_ERROR;
  }

  snprintf(msg, sizeof(msg), "Device 0x%02X chip ID = 0x%02X\r\n", addr_7bit, chip_id);
  uart_print(msg);

  if (chip_id != BME280_CHIP_ID && chip_id != BMP280_CHIP_ID)
  {
    return HAL_ERROR;
  }

  bme_addr_7bit = addr_7bit;
  bme_chip_id = chip_id;
  has_humidity = chip_id == BME280_CHIP_ID;

  if (bme_read_calibration() != HAL_OK)
  {
    uart_print("ERROR: BME/BMP calibration read failed.\r\n");
    return HAL_ERROR;
  }

  if (has_humidity)
  {
    uint8_t ctrl_hum = 0x01;

    if (HAL_I2C_Mem_Write(&hi2c1, ADDR8(bme_addr_7bit), BME_REG_CTRL_HUM,
                          I2C_MEMADD_SIZE_8BIT, &ctrl_hum, 1, 500) != HAL_OK)
    {
      uart_print("ERROR: BME280 humidity config failed.\r\n");
      return HAL_ERROR;
    }
  }

  uint8_t config = 0xA0;
  uint8_t ctrl_meas = 0x27;

  if (HAL_I2C_Mem_Write(&hi2c1, ADDR8(bme_addr_7bit), BME_REG_CONFIG,
                        I2C_MEMADD_SIZE_8BIT, &config, 1, 500) != HAL_OK)
  {
    uart_print("ERROR: BME/BMP config write failed.\r\n");
    return HAL_ERROR;
  }

  if (HAL_I2C_Mem_Write(&hi2c1, ADDR8(bme_addr_7bit), BME_REG_CTRL_MEAS,
                        I2C_MEMADD_SIZE_8BIT, &ctrl_meas, 1, 500) != HAL_OK)
  {
    uart_print("ERROR: BME/BMP ctrl_meas write failed.\r\n");
    return HAL_ERROR;
  }

  HAL_Delay(200);

  bme_ok = true;

  if (has_humidity)
  {
    uart_print("BME280 initialized with humidity.\r\n");
  }
  else
  {
    uart_print("BMP280 initialized. Humidity unavailable.\r\n");
  }

  return HAL_OK;
}

HAL_StatusTypeDef bme_init(void)
{
  if (bme_try_address(BME_ADDR_76_7BIT) == HAL_OK)
  {
    return HAL_OK;
  }

  if (bme_try_address(BME_ADDR_77_7BIT) == HAL_OK)
  {
    return HAL_OK;
  }

  uart_print("ERROR: BME280/BMP280 not initialized.\r\n");
  bme_ok = false;
  return HAL_ERROR;
}

int32_t compensate_temperature(int32_t adc_T)
{
  int32_t var1;
  int32_t var2;
  int32_t T;

  var1 = ((((adc_T >> 3) - ((int32_t)bme_calib.dig_T1 << 1))) *
          ((int32_t)bme_calib.dig_T2)) >> 11;

  var2 = (((((adc_T >> 4) - ((int32_t)bme_calib.dig_T1)) *
            ((adc_T >> 4) - ((int32_t)bme_calib.dig_T1))) >> 12) *
          ((int32_t)bme_calib.dig_T3)) >> 14;

  t_fine = var1 + var2;

  T = (t_fine * 5 + 128) >> 8;

  return T;
}

uint32_t compensate_pressure_pa(int32_t adc_P)
{
  int64_t var1;
  int64_t var2;
  int64_t p;

  var1 = ((int64_t)t_fine) - 128000;
  var2 = var1 * var1 * (int64_t)bme_calib.dig_P6;
  var2 = var2 + ((var1 * (int64_t)bme_calib.dig_P5) << 17);
  var2 = var2 + (((int64_t)bme_calib.dig_P4) << 35);
  var1 = ((var1 * var1 * (int64_t)bme_calib.dig_P3) >> 8) +
         ((var1 * (int64_t)bme_calib.dig_P2) << 12);
  var1 = (((((int64_t)1) << 47) + var1)) * ((int64_t)bme_calib.dig_P1) >> 33;

  if (var1 == 0)
  {
    return 0;
  }

  p = 1048576 - adc_P;
  p = (((p << 31) - var2) * 3125) / var1;
  var1 = (((int64_t)bme_calib.dig_P9) * (p >> 13) * (p >> 13)) >> 25;
  var2 = (((int64_t)bme_calib.dig_P8) * p) >> 19;
  p = ((p + var1 + var2) >> 8) + (((int64_t)bme_calib.dig_P7) << 4);

  return (uint32_t)(p / 256);
}

uint32_t compensate_humidity_centi(int32_t adc_H)
{
  int32_t v_x1;

  v_x1 = t_fine - 76800;

  v_x1 = (((((adc_H << 14) - (((int32_t)bme_calib.dig_H4) << 20) -
             (((int32_t)bme_calib.dig_H5) * v_x1)) + 16384) >> 15) *
          (((((((v_x1 * ((int32_t)bme_calib.dig_H6)) >> 10) *
               (((v_x1 * ((int32_t)bme_calib.dig_H3)) >> 11) + 32768)) >> 10) +
             2097152) * ((int32_t)bme_calib.dig_H2) + 8192) >> 14));

  v_x1 = v_x1 - (((((v_x1 >> 15) * (v_x1 >> 15)) >> 7) *
                  ((int32_t)bme_calib.dig_H1)) >> 4);

  if (v_x1 < 0)
  {
    v_x1 = 0;
  }

  if (v_x1 > 419430400)
  {
    v_x1 = 419430400;
  }

  uint32_t humidity_q1024 = (uint32_t)(v_x1 >> 12);
  return (humidity_q1024 * 100U) / 1024U;
}

HAL_StatusTypeDef bme_read_values(int32_t *temp_centi,
                                  uint32_t *pressure_centi_hpa,
                                  uint32_t *humidity_centi)
{
  if (!bme_ok)
  {
    return HAL_ERROR;
  }

  uint8_t data[8];
  uint8_t len = has_humidity ? 8 : 6;

  HAL_StatusTypeDef status = HAL_I2C_Mem_Read(&hi2c1, ADDR8(bme_addr_7bit), BME_REG_PRESS_MSB,
                                              I2C_MEMADD_SIZE_8BIT, data, len, 500);

  if (status != HAL_OK)
  {
    return status;
  }

  int32_t adc_P = ((int32_t)data[0] << 12) |
                  ((int32_t)data[1] << 4) |
                  ((int32_t)data[2] >> 4);

  int32_t adc_T = ((int32_t)data[3] << 12) |
                  ((int32_t)data[4] << 4) |
                  ((int32_t)data[5] >> 4);

  *temp_centi = compensate_temperature(adc_T);

  uint32_t pressure_pa = compensate_pressure_pa(adc_P);

  *pressure_centi_hpa = pressure_pa;

  if (has_humidity)
  {
    int32_t adc_H = ((int32_t)data[6] << 8) | data[7];
    *humidity_centi = compensate_humidity_centi(adc_H);
  }
  else
  {
    *humidity_centi = 0;
  }

  return HAL_OK;
}

/* USER CODE END 0 */

int main(void)
{
  HAL_Init();

  SystemClock_Config();

  MX_GPIO_Init();
  MX_I2C1_Init();
  MX_USART2_UART_Init();

  HAL_Delay(1000);

  uart_print("\r\nDorm Guardian sensor-only firmware started.\r\n");
  uart_print("USART2 serial ready at 115200 baud.\r\n");

  i2c_scan();

  bh1750_init();
  bme_init();

  uart_print("Starting JSON sensor output...\r\n");

  while (1)
  {
    int32_t temp_centi = 0;
    uint32_t pressure_centi_hpa = 0;
    uint32_t humidity_centi = 0;
    uint32_t light_centi = 0;

    HAL_StatusTypeDef bme_status = bme_read_values(&temp_centi, &pressure_centi_hpa, &humidity_centi);
    HAL_StatusTypeDef light_status = bh1750_read_lux_centi(&light_centi);

    char temp_str[24];
    char pressure_str[24];
    char humidity_str[24];
    char light_str[24];
    char json[384];

    if (bme_status == HAL_OK)
    {
      format_signed_centi(temp_str, sizeof(temp_str), temp_centi);
      format_unsigned_centi(pressure_str, sizeof(pressure_str), pressure_centi_hpa);

      if (has_humidity)
      {
        format_unsigned_centi(humidity_str, sizeof(humidity_str), humidity_centi);
      }
      else
      {
        snprintf(humidity_str, sizeof(humidity_str), "null");
      }
    }
    else
    {
      snprintf(temp_str, sizeof(temp_str), "null");
      snprintf(pressure_str, sizeof(pressure_str), "null");
      snprintf(humidity_str, sizeof(humidity_str), "null");
    }

    if (light_status == HAL_OK)
    {
      format_unsigned_centi(light_str, sizeof(light_str), light_centi);
    }
    else
    {
      snprintf(light_str, sizeof(light_str), "null");
    }

    snprintf(json, sizeof(json),
             "{\"device_id\":\"%s\",\"temperature\":%s,\"humidity\":%s,\"pressure\":%s,\"light\":%s,\"fan_status\":false,\"source\":\"hardware\",\"bme_status\":%d,\"light_status\":%d}\r\n",
             DEVICE_ID,
             temp_str,
             humidity_str,
             pressure_str,
             light_str,
             (int)bme_status,
             (int)light_status);

    uart_print(json);

    HAL_Delay(2000);
  }
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_NONE;

  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK
                              | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_HSI;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_0) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief I2C1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_I2C1_Init(void)
{
  hi2c1.Instance = I2C1;
  hi2c1.Init.ClockSpeed = 100000;
  hi2c1.Init.DutyCycle = I2C_DUTYCYCLE_2;
  hi2c1.Init.OwnAddress1 = 0;
  hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  hi2c1.Init.OwnAddress2 = 0;
  hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;

  if (HAL_I2C_Init(&hi2c1) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief USART2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART2_UART_Init(void)
{
  huart2.Instance = USART2;
  huart2.Init.BaudRate = 115200;
  huart2.Init.WordLength = UART_WORDLENGTH_8B;
  huart2.Init.StopBits = UART_STOPBITS_1;
  huart2.Init.Parity = UART_PARITY_NONE;
  huart2.Init.Mode = UART_MODE_TX_RX;
  huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart2.Init.OverSampling = UART_OVERSAMPLING_16;

  if (HAL_UART_Init(&huart2) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};

  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();

#ifdef FAN_INA_Pin
  HAL_GPIO_WritePin(FAN_INA_GPIO_Port, FAN_INA_Pin, GPIO_PIN_RESET);

  GPIO_InitStruct.Pin = FAN_INA_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(FAN_INA_GPIO_Port, &GPIO_InitStruct);
#endif

#ifdef FAN_INB_Pin
  HAL_GPIO_WritePin(FAN_INB_GPIO_Port, FAN_INB_Pin, GPIO_PIN_RESET);

  GPIO_InitStruct.Pin = FAN_INB_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(FAN_INB_GPIO_Port, &GPIO_InitStruct);
#endif
}

void Error_Handler(void)
{
  __disable_irq();

  while (1)
  {
  }
}

#ifdef USE_FULL_ASSERT
void assert_failed(uint8_t *file, uint32_t line)
{
}
#endif
