import asyncio
import logging
from cbpi.api import *

@parameters([
    Property.Number(label="Power_Before", configurable=True, default_value=100, description="Power (%) before transition temperature is reached."),
    Property.Number(label="Transition_Temp", configurable=True, default_value=98, description="When this temperature is reached, power will be set to Power_After (default: 98 °C / 208 °F)"),
    Property.Number(label="Power_After", configurable=True, default_value=60, description="Power (%) when Transition Temp is reached.")
])
class DirectPWMBoil(CBPiKettleLogic):

    async def on_stop(self):
        await self.actor_off(self.heater)

    async def run(self):
        try:
            self.TEMP_UNIT = self.get_config_value("TEMP_UNIT", "C")
            sampleTime = 2
            boilthreshold = 98 if self.TEMP_UNIT == "C" else 208

            power_before = int(self.props.get("Power_Before", 100))
            transition_temp = float(self.props.get("Transition_Temp", boilthreshold))
            power_after = int(self.props.get("Power_After", 60))
            
            self.kettle = self.get_kettle(self.id)
            self.heater = self.kettle.heater
            self.heater_actor = self.cbpi.actor.find_by_id(self.heater)
            
            heat_percent_old = power_before
            
            # === НОВЫЕ ПЕРЕМЕННЫЕ ДЛЯ РУЧНОГО УПРАВЛЕНИЯ ===
            self.manual_override_active = False
            self.manual_override_power = 0
            self.last_auto_power = -1

            await self.actor_on(self.heater, power_before)

            while self.running == True:
                # Безопасное получение данных с сенсора
                sensor_data = self.get_sensor_value(self.kettle.sensor)
                if sensor_data is None:
                    await asyncio.sleep(sampleTime)
                    continue
                    
                current_temp = float(sensor_data.get("value", 0))
                target_temp = self.get_kettle_target_temp(self.id)
                current_kettle_power = self.heater_actor.power
                
                # === ГЛАВНАЯ ЛОГИКА ===
                
                # ЗОНА: Достигли или превысили температуру перехода
                if current_temp >= float(transition_temp):
                    
                    # Проверяем, не изменил ли пользователь мощность вручную
                    if not self.manual_override_active:
                        if self.last_auto_power == -1:
                            self.last_auto_power = power_after
                        
                        # Если текущая мощность актора отличается от той, что поставила автоматика (допуск 0.5%)
                        if abs(current_kettle_power - self.last_auto_power) > 0.5:
                            self.manual_override_active = True
                            self.manual_override_power = current_kettle_power
                            self.cbpi.notify("DirectPWMBoil", f"Manual override: {current_kettle_power}% until temp drops", NotificationType.SUCCESS)
                            logging.info(f"DirectPWMBoil: Manual override activated at {current_kettle_power}%")

                    # Применяем мощность: либо ручную, либо автоматическую
                    if self.manual_override_active:
                        heat_percent = self.manual_override_power
                    else:
                        heat_percent = power_after
                        self.last_auto_power = heat_percent
                        
                # ЗОНА: Температура ниже порога перехода
                else:
                    # Если температура упала ниже порога, сбрасываем ручное управление
                    if self.manual_override_active:
                        self.manual_override_active = False
                        self.last_auto_power = -1
                        logging.info("DirectPWMBoil: Temp dropped below transition. Manual override reset.")
                    
                    heat_percent = power_before

                # Применяем мощность только если она изменилась
                if (heat_percent_old != heat_percent) or (heat_percent != current_kettle_power):
                    await self.actor_set_power(self.heater, heat_percent)
                    heat_percent_old = heat_percent
                    
                await asyncio.sleep(sampleTime)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logging.error("DirectPWMBoil Error {}".format(e))
        finally:
            self.running = False
            await self.actor_off(self.heater)


def setup(cbpi):
    cbpi.plugin.register("DirectPWMBoil", DirectPWMBoil)
