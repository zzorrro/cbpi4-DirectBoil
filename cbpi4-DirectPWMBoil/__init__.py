import asyncio
import logging
from cbpi.api import *

@parameters([
    Property.Number(label="Power_Before", configurable=True, default_value=100, description="Power (%) before reaching transition temperature (e.g., 100)"),
    Property.Number(label="Transition_Temp", configurable=True, default_value=98, description="Temperature threshold to switch to boil power (e.g., 98 °C)"),
    Property.Number(label="Power_After", configurable=True, default_value=60, description="Power (%) after reaching transition temperature for steady boil (e.g., 60)")
])
class DirectPWMBoil(CBPiKettleLogic):

    async def on_stop(self):
        """При остановке логики немедленно выключаем нагрев"""
        logging.info(f"DirectPWMBoil: on_stop called for kettle {self.id}")
        try:
            await self.actor_off(self.heater)
            logging.info(f"DirectPWMBoil: Heater {self.heater} turned OFF")
        except Exception as e:
            logging.error(f"DirectPWMBoil: Error turning off heater: {e}")

    async def run(self):
        try:
            self.TEMP_UNIT = self.get_config_value("TEMP_UNIT", "C")
            sample_time = 2  # Проверка каждые 2 секунды
            
            # Получаем параметры
            power_before = int(self.props.get("Power_Before", 100))
            transition_temp = float(self.props.get("Transition_Temp", 98))
            power_after = int(self.props.get("Power_After", 60))
            
            # Корректировка температуры перехода для Фаренгейта
            if self.TEMP_UNIT == "F":
                transition_temp = (transition_temp * 9/5) + 32

            self.kettle = self.get_kettle(self.id)
            self.heater = self.kettle.heater
            
            # Проверяем, что heater настроен
            if self.heater is None:
                logging.error(f"DirectPWMBoil: No heater configured for kettle {self.id}!")
                self.running = False
                return
            
            logging.info(f"DirectPWMBoil: Kettle ID={self.id}, Heater ID={self.heater}")
            logging.info(f"DirectPWMBoil: Power_Before={power_before}%, Transition_Temp={transition_temp}°{self.TEMP_UNIT}, Power_After={power_after}%")
            
            power_old = -1  # Гарантируем первое применение мощности при старте

            # Явно включаем актор с начальной мощностью (как в оригинальном PIDBoil)
            logging.info(f"DirectPWMBoil: Turning ON heater {self.heater} at {power_before}%")
            await self.actor_on(self.heater, power_before)
            power_old = power_before

            logging.info(f"DirectPWMBoil started successfully. Monitoring sensor {self.kettle.sensor}")

            while self.running == True:
                # Получаем текущую температуру
                sensor_data = self.get_sensor_value(self.kettle.sensor)
                if sensor_data is None:
                    logging.warning("DirectPWMBoil: No sensor data, waiting...")
                    await asyncio.sleep(sample_time)
                    continue
                    
                current_temp = float(sensor_data.get("value", 0))
                
                # === ГЛАВНАЯ ЛОГИКА ===
                if current_temp >= transition_temp:
                    target_power = power_after
                else:
                    target_power = power_before
                
                # Применяем мощность ТОЛЬКО если она изменилась
                if target_power != power_old:
                    try:
                        logging.info(f"DirectPWMBoil: Setting power to {target_power}% (Current Temp: {current_temp}°{self.TEMP_UNIT})")
                        await self.actor_set_power(self.heater, target_power)
                        power_old = target_power
                    except Exception as e:
                        logging.error(f"DirectPWMBoil: Failed to set power: {e}")
                
                await asyncio.sleep(sample_time)

        except asyncio.CancelledError:
            logging.info("DirectPWMBoil: Cancelled (normal shutdown)")
            pass
        except Exception as e:
            logging.error(f"DirectPWMBoil Error: {e}")
            import traceback
            logging.error(traceback.format_exc())
        finally:
            logging.info("DirectPWMBoil: Stopping, turning off heater")
            self.running = False
            try:
                await self.actor_off(self.heater)
            except Exception as e:
                logging.error(f"DirectPWMBoil: Error in finally block: {e}")


def setup(cbpi):
    """Регистрация плагина в системе"""
    cbpi.plugin.register("DirectPWMBoil", DirectPWMBoil)
