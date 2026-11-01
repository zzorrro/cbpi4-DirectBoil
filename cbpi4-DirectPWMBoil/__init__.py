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
        pass

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
            heat_percent_old = power_before
            self.heater_actor = self.cbpi.actor.find_by_id(self.heater)
            
            await self.actor_on(self.heater, power_before)

            while self.running == True:
                current_kettle_power = self.heater_actor.power
                sensor_value = current_temp = self.get_sensor_value(self.kettle.sensor).get("value")
                target_temp = self.get_kettle_target_temp(self.id)
                
                if current_temp >= float(transition_temp):
                    heat_percent = power_after
                else:
                    heat_percent = power_before

                if (heat_percent_old != heat_percent) or (heat_percent != current_kettle_power):
                    await self.actor_set_power(self.heater, heat_percent)
                    heat_percent_old = heat_percent
                await asyncio.sleep(sampleTime)

        except asyncio.CancelledError as e:
            pass
        except Exception as e:
            logging.error("DirectPWMBoil Error {}".format(e))
        finally:
            self.running = False
            await self.actor_off(self.heater)


def setup(cbpi):
    cbpi.plugin.register("DirectPWMBoil", DirectPWMBoil)
