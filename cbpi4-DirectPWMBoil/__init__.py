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
        await self.actor_off(self.heater)

    async def run(self):
        try:
            self.TEMP_UNIT = self.get_config_value("TEMP_UNIT", "C")
            sample_time = 2  # Проверка каждые 2 секунды (достаточно для PWM, не грузит систему)
            
            # Получаем параметры
            power_before = int(self.props.get("Power_Before", 100))
            transition_temp = float(self.props.get("Transition_Temp", 98))
            power_after = int(self.props.get("Power_After", 60))
            
            # Корректировка температуры перехода для Фаренгейта, если используется
            if self.TEMP_UNIT == "F":
                transition_temp = (transition_temp * 9/5) + 32

            self.kettle = self.get_kettle(self.id)
            self.heater = self.kettle.heater
            
            power_old = -1  # Гарантируем первое применение мощности при старте

            logging.info(f"DirectPWMBoil started. Before: {power_before}%, Threshold: {transition_temp}°, After: {power_after}%")

            while self.running == True:
                # Получаем текущую температуру
                sensor_data = self.get_sensor_value(self.kettle.sensor)
                if sensor_data is None:
                    await asyncio.sleep(sample_time)
                    continue
                    
                current_temp = float(sensor_data.get("value", 0))
                
                # === ГЛАВНАЯ ЛОГИКА ===
                if current_temp >= transition_temp:
                    target_power = power_after
                else:
                    target_power = power_before
                
                # Применяем мощность ТОЛЬКО если она изменилась (защита от спама GPIO/API)
                if target_power != power_old:
                    await self.actor_set_power(self.heater, target_power)
                    power_old = target_power
                    logging.info(f"DirectPWMBoil: Power set to {target_power}% (Current Temp: {current_temp}°{self.TEMP_UNIT})")
                
                await asyncio.sleep(sample_time)

        except asyncio.CancelledError:
            # Нормальное завершение при остановке
            pass
        except Exception as e:
            logging.error(f"DirectPWMBoil Error: {e}")
        finally:
            # Гарантированное выключение при любом выходе из цикла
            self.running = False
            await self.actor_off(self.heater)


def setup(cbpi):
    """Регистрация плагина в системе"""
    cbpi.plugin.register("DirectPWMBoil", DirectPWMBoil)