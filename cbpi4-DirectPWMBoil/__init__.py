# -*- coding: utf-8 -*-
import asyncio
import logging
from cbpi.api import *

logger = logging.getLogger(__name__)

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
            
            # Переменные состояния
            self.manual_override_active = False
            self.manual_override_power = 0
            self.current_phase = None # Начинаем без фазы

            logger.info(f"DirectPWMBoil started: before={power_before}%, transition={transition_temp}°C, after={power_after}%")
            await self.actor_on(self.heater, power_before)

            while self.running == True:
                sensor_data = self.get_sensor_value(self.kettle.sensor)
                if sensor_data is None:
                    await asyncio.sleep(sampleTime)
                    continue
                    
                current_temp = float(sensor_data.get("value", 0))
                
                try:
                    current_kettle_power = float(self.heater_actor.power)
                except:
                    current_kettle_power = 0
                
                # === ШАГ 1: Определяем текущую фазу ===
                if current_temp >= float(transition_temp):
                    new_phase = "BOIL"
                    desired_auto_power = power_after
                else:
                    new_phase = "HEAT"
                    desired_auto_power = power_before
                
                # === ШАГ 2: Произошла ли смена фазы? ===
                if self.current_phase != new_phase:
                    # Фаза изменилась! Принудительно сбрасываем ручное управление
                    self.manual_override_active = False
                    self.current_phase = new_phase
                    heat_percent = desired_auto_power
                    logger.info(f"PHASE CHANGE to {new_phase}! Manual override reset. Power set to {desired_auto_power}%")
                else:
                    # Фаза та же. Проверяем ручное вмешательство.
                    if not self.manual_override_active:
                        if abs(current_kettle_power - desired_auto_power) > 0.5:
                            self.manual_override_active = True
                            self.manual_override_power = current_kettle_power
                            logger.info(f"Manual override activated at {current_kettle_power}%")

                    if self.manual_override_active:
                        heat_percent = self.manual_override_power
                    else:
                        heat_percent = desired_auto_power

                # === ШАГ 3: Применяем мощность ===
                if (heat_percent_old != heat_percent) or (heat_percent != current_kettle_power):
                    logger.info(f"DirectPWMBoil: Setting power to {heat_percent}%")
                    await self.actor_set_power(self.heater, heat_percent)
                    heat_percent_old = heat_percent
                    
                await asyncio.sleep(sampleTime)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"DirectPWMBoil Error: {e}")
        finally:
            self.running = False
            await self.actor_off(self.heater)

def setup(cbpi):
    cbpi.plugin.register("DirectPWMBoil", DirectPWMBoil)
