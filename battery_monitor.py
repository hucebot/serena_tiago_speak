import math
import os
import subprocess
import time
# import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import BatteryState
from std_msgs.msg import Int32

# Valid battery_source values: battery_level (Int32 %) or power_status (BatteryState)
SOURCE_BATTERY_LEVEL = 'battery_level'
SOURCE_POWER_STATUS = 'power_status'

class BatteryMonitorNode(Node):
    def __init__(self, config_path='config.ini'):
        super().__init__('battery_monitor_node')

        # Get the directory where this python file is located
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

        # 1. Parse the configuration file
        config_file_path = os.path.join(self.script_dir, config_path)
        self.config = self.load_config(config_file_path)
        
        # 2. Extract parameters
        self.battery_source = self.config.get('battery_source', SOURCE_BATTERY_LEVEL).strip().lower()
        self.battery_level_topic = self.config.get('battery_level_topic', '/power/battery_level')
        self.power_status_topic = self.config.get('power_status_topic', '/power_status')
        self.frequency = float(self.config.get('read_frequency', '0.2'))
        self.can_speak = self.config.get('can_speak', 'true').lower() == 'true'
        self.can_play_sound = self.config.get('can_play_sound', 'true').lower() == 'true'
        
        self.sentence_level = self.config.get('sentence_level', 'Tiago battery is at')
        self.sentence_full = self.config.get('sentence_full', 'Tiago battery fully charged')
        self.sentence_low = self.config.get('sentence_low', 'Tiago battery is low')
        self.voice_type = self.config.get('voice_type', 'kal_diphone')
        
        self.sound_full = self.config.get('sound_full', 'full_charge.wav')
        self.sound_medium = self.config.get('sound_medium', 'battery_level.wav')
        self.sound_low = self.config.get('sound_low', 'urgent_charge2.wav')
        
        if self.battery_source not in (SOURCE_BATTERY_LEVEL, SOURCE_POWER_STATUS):
            self.get_logger().warn(
                f"Unknown battery_source '{self.battery_source}', falling back to {SOURCE_BATTERY_LEVEL}"
            )
            self.battery_source = SOURCE_BATTERY_LEVEL

        # 3. Initialize state variables
        self.current_battery_level = None
        self.last_announced_level = None
        
        self.last_battery_level_stored = None
        self.battery_level_crossed_boundary = False
        
        # 4. Create both subscriptions; only the active source updates the level
        self.battery_level_sub = self.create_subscription(
            Int32,
            self.battery_level_topic,
            self.battery_level_callback,
            10
        )
        self.power_status_sub = self.create_subscription(
            BatteryState,
            self.power_status_topic,
            self.power_status_callback,
            10
        )
        
        # 5. Create Timer to process readings at the specified frequency
        timer_period = 1.0 / self.frequency if self.frequency > 0 else 5.0
        self.timer = self.create_timer(timer_period, self.process_battery_level)
        active_topic = (
            self.battery_level_topic
            if self.battery_source == SOURCE_BATTERY_LEVEL
            else self.power_status_topic
        )
        self.get_logger().info(
            f"Battery Monitor started. Source={self.battery_source} "
            f"(active topic {active_topic}) at {self.frequency} Hz"
        )

    def load_config(self, filepath):
        """Reads key-value pairs from the configuration file."""
        config_dict = {}
        if not os.path.exists(filepath):
            self.get_logger().error(f"Config file {filepath} not found!")
            return config_dict
            
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    config_dict[key.strip()] = value.strip()
        return config_dict

    def _set_battery_level(self, level):
        """Clamp and store an integer battery percentage 0..100."""
        self.current_battery_level = max(0, min(100, int(level)))
        
        if self.last_battery_level_stored is None: 
            self.last_battery_level_stored = self.current_battery_level
            self.get_logger().info(f"Battery level stored: {self.current_battery_level}")
            
        if math.floor(self.current_battery_level / 10) != math.floor(self.last_battery_level_stored / 10):
            self.battery_level_crossed_boundary = True
            self.get_logger().info(f"Battery level crossed boundary: {self.current_battery_level} (vs last stored {self.last_battery_level_stored})")
        
        self.last_battery_level_stored = self.current_battery_level

    def battery_level_callback(self, msg):
        """Updates level from std_msgs/Int32 on /power/battery_level (already 0..100)."""
        if self.battery_source != SOURCE_BATTERY_LEVEL:
            return
        self._set_battery_level(msg.data)

    def power_status_callback(self, msg):
        """Updates level from sensor_msgs/BatteryState.percentage on /power_status."""
        if self.battery_source != SOURCE_POWER_STATUS:
            return
        pct = msg.percentage
        if math.isnan(pct):
            return
        # Spec is 0..1; some publishers send 0..100 — accept both
        level = pct * 100.0 if pct <= 1.0 else pct
        self._set_battery_level(round(level))

    def process_battery_level(self):
        """Timer callback that evaluates the battery level and triggers actions."""
        if self.current_battery_level is None:
            return # No data received yet
            
        level = self.current_battery_level

        # Trigger if level is a multiple of 10, or if it is exactly 99
        is_trigger_level = (level == 99) or self.battery_level_crossed_boundary
        
        if is_trigger_level and level != self.last_announced_level:
            self.last_announced_level = level
            
            # 100 or 99 trigger the "fully charged" logic
            if level >= 99:
                sound_file = self.sound_full
                spoken_text = self.sentence_full
            elif level <= 50:
                sound_file = self.sound_low
                spoken_text = f"{self.sentence_low}. {self.sentence_level} {level}"
                spoken_text += " percent"
            else:
                sound_file = self.sound_medium
                spoken_text = f"{self.sentence_level} {level}"                
                spoken_text += " percent"
                
            self.get_logger().info(f"Battery at {level}%. Triggering alerts.")
                    
            # Execute Actions
            if self.can_play_sound:
                self.play_sound(sound_file)
                
            if self.can_speak:
                time.sleep(1)
                self.speak(spoken_text)

    def play_sound(self, filepath):
        """Plays a WAV file using ALSA aplay."""
        if os.path.exists(filepath):
            # aplay is standard on Ubuntu/Linux. Use -q for quiet output.
            subprocess.Popen(['aplay', '-q', filepath])
        else:
            self.get_logger().warn(f"Sound file not found: {filepath}")

    def speak(self, text):
        """Uses Festival TTS to speak the text with the configured voice."""
        # Festival command to use a specific voice and say the text
        festival_cmd = f'(voice_{self.voice_type}) (SayText "{text}")'
        try:
            process = subprocess.Popen(['festival', '--pipe'], 
                                     stdin=subprocess.PIPE, 
                                     text=True)
            process.communicate(festival_cmd)
        except Exception as e:
            self.get_logger().error(f"Failed to execute Festival TTS: {e}")

def main(args=None):
    rclpy.init(args=args)
    # Ensure config.ini is in the working directory or provide absolute path
    node = BatteryMonitorNode(config_path='config.ini')
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()